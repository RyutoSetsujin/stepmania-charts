import os
import re
import glob
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import argparse

@dataclass
class ChartMetadata:
    title: str
    subtitle: str
    artist: str
    credit: str
    difficulty: str
    meter: int
    bpms: List[Tuple[float, float]]
    stops: List[Tuple[float, float]]
    warps: List[Tuple[float, float]]
    fakes: List[Tuple[float, float]]
    speeds: List[Tuple[float, float, float]]  # beat, multiplier, duration
    scrolls: List[Tuple[float, float]]  # beat, new_scroll_speed

@dataclass
class Note:
    beat: float
    column: int
    type: str  # "tap", "hold_head", "hold_tail", "mine", "roll_head", "roll_tail", "fake", "lift"
    hold_length: float = 0
    is_fake: bool = False

class ChartVisualizer:
    NOTE_TYPES = {
        "1": "tap",
        "2": "hold_head",
        "3": "hold_tail",
        "M": "mine",
        "4": "roll_head",
        "3": "roll_tail",
        "0": "none",
        "F": "fake",
        "L": "lift"
    }
    
    COLORS = {
        "tap": (255, 255, 255),
        "hold": (0, 255, 255),
        "roll": (255, 165, 0),
        "mine": (255, 0, 0),
        "fake": (128, 128, 128),
        "lift": (255, 192, 203),
        "measure": (50, 50, 50),
        "beat": (30, 30, 30),
        "bpm": (0, 255, 0),
        "stop": (255, 0, 255),
        "warp": (255, 255, 0),
        "speed": (0, 255, 255),
        "scroll": (255, 128, 0),
        "background": (0, 0, 0),
        "text": (255, 255, 255)
    }

    def __init__(self, sm_file: str):
        self.sm_file = sm_file
        self.metadata = None
        self.notes = []
        self.parse_sm_file()

    def parse_sm_file(self) -> List[Dict]:
        with open(self.sm_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract basic metadata first
        base_metadata = {
            'title': self._extract_tag(content, "TITLE"),
            'subtitle': self._extract_tag(content, "SUBTITLE"),
            'artist': self._extract_tag(content, "ARTIST"),
            'credit': self._extract_tag(content, "CREDIT"),
            'bpms': self._parse_bpms(content),
            'stops': self._parse_stops(content),
            'warps': self._parse_warps(content),
            'fakes': self._parse_fakes(content),
            'speeds': self._parse_speeds(content),
            'scrolls': self._parse_scrolls(content)
        }

        # Find all NOTES sections
        charts = []
        notes_sections = re.finditer(
            r'#NOTES:\s*([^:]*):([^:]*):([^:]*):([^:]*):([^:]*):([^;]*);',
            content
        )

        for section in notes_sections:
            chart_type, desc, diff_class, diff_meter, groove_radar, notes_data = section.groups()
            
            # Skip non-dance-single and non-dance-double charts if specified
            if chart_type.strip() not in ['dance-single', 'dance-double']:
                continue

            # Create metadata for this chart
            chart_metadata = ChartMetadata(
                **base_metadata,
                difficulty=diff_class.strip(),
                meter=int(diff_meter.strip())
            )

            # Parse notes for this chart
            notes = self._parse_notes(notes_data.strip())
            
            charts.append({
                'metadata': chart_metadata,
                'notes': notes,
                'type': chart_type.strip()
            })

        return charts

    def _parse_warps(self, content: str) -> List[Tuple[float, float]]:
        warps = []
        match = re.search(r'#WARPS:([^;]*);', content)
        if match:
            warp_data = match.group(1).strip()
            for warp in warp_data.split(','):
                if '=' in warp:
                    beat, length = warp.split('=')
                    warps.append((float(beat), float(length)))
        return sorted(warps)

    def _parse_fakes(self, content: str) -> List[Tuple[float, float]]:
        fakes = []
        match = re.search(r'#FAKES:([^;]*);', content)
        if match:
            fake_data = match.group(1).strip()
            for fake in fake_data.split(','):
                if '=' in fake:
                    beat, length = fake.split('=')
                    fakes.append((float(beat), float(length)))
        return sorted(fakes)

    def _parse_speeds(self, content: str) -> List[Tuple[float, float, float]]:
        speeds = []
        match = re.search(r'#SPEEDS:([^;]*);', content)
        if match:
            speed_data = match.group(1).strip()
            for speed in speed_data.split(','):
                if '=' in speed:
                    beat, data = speed.split('=')
                    multiplier, duration = data.split(',')
                    speeds.append((float(beat), float(multiplier), float(duration)))
        return sorted(speeds)

    def _parse_scrolls(self, content: str) -> List[Tuple[float, float]]:
        scrolls = []
        match = re.search(r'#SCROLLS:([^;]*);', content)
        if match:
            scroll_data = match.group(1).strip()
            for scroll in scroll_data.split(','):
                if '=' in scroll:
                    beat, value = scroll.split('=')
                    scrolls.append((float(beat), float(value)))
        return sorted(scrolls)

    def _extract_tag(self, content: str, tag: str) -> str:
        match = re.search(f'#{tag}:([^;]*);', content)
        return match.group(1).strip() if match else ""

    def _parse_bpms(self, content: str) -> List[Tuple[float, float]]:
        bpms = []
        match = re.search(r'#BPMS:([^;]*);', content)
        if match:
            bpm_data = match.group(1).strip()
            for bpm in bpm_data.split(','):
                if '=' in bpm:
                    beat, value = bpm.split('=')
                    bpms.append((float(beat), float(value)))
        return sorted(bpms)

    def _parse_stops(self, content: str) -> List[Tuple[float, float]]:
        stops = []
        match = re.search(r'#STOPS:([^;]*);', content)
        if match:
            stop_data = match.group(1).strip()
            for stop in stop_data.split(','):
                if '=' in stop:
                    beat, value = stop.split('=')
                    stops.append((float(beat), float(value)))
        return sorted(stops)

    def _parse_notes(self, notes_data: str):
        measures = notes_data.strip().split(',')
        current_beat = 0.0
        
        for measure_idx, measure in enumerate(measures):
            rows = [row.strip() for row in measure.strip().split('\n') if row.strip()]
            if not rows:
                continue
                
            beats_per_row = 4 / len(rows)
            
            for row_idx, row in enumerate(rows):
                if len(row) not in [4, 8]:  # Support both singles and doubles
                    continue
                    
                beat = current_beat + (row_idx * beats_per_row)
                
                for col, note_type in enumerate(row):
                    if note_type in self.NOTE_TYPES and note_type != "0":
                        self.notes.append(Note(
                            beat=beat,
                            column=col,
                            type=self.NOTE_TYPES[note_type]
                        ))
            
            current_beat += 4

        # Process holds and rolls
        self._process_holds()

    def _process_holds(self):
        # Match hold heads with their tails
        hold_heads = [i for i, note in enumerate(self.notes) 
                     if note.type in ['hold_head', 'roll_head']]
        
        for head_idx in hold_heads:
            head = self.notes[head_idx]
            # Find the next tail in the same column
            for note in self.notes[head_idx + 1:]:
                if (note.column == head.column and 
                    note.type in ['hold_tail', 'roll_tail']):
                    head.hold_length = note.beat - head.beat
                    break

    def generate_visualization(self, chart_data: Dict, output_file: str, measures: int = None):
        # Calculate dimensions
        padding = 40
        note_size = 20
        pixels_per_beat = 60
        column_width = note_size + 4
        
        if not measures:
            max_beat = max(note.beat for note in chart_data['notes'])
            measures = int(max_beat / 4) + 1
        
        width = (padding * 2) + (len(chart_data['notes'][0].type) * column_width)
        height = (padding * 2) + (measures * 4 * pixels_per_beat)
        
        # Create image
        img = Image.new('RGB', (width, height), self.COLORS["background"])
        draw = ImageDraw.Draw(img)
        
        # Try to load font (fallback to default if not found)
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()

        # Draw measure lines and beat lines
        for measure in range(measures + 1):
            y = height - padding - (measure * 4 * pixels_per_beat)
            # Measure line
            draw.line([(padding, y), (width - padding, y)],
                     fill=self.COLORS["measure"], width=2)
            
            # Beat lines
            for beat in range(1, 4):
                beat_y = y - (beat * pixels_per_beat)
                draw.line([(padding, beat_y), (width - padding, beat_y)],
                         fill=self.COLORS["beat"], width=1)

        # Draw BPM changes
        for beat, bpm in chart_data['metadata'].bpms:
            y = height - padding - (beat * pixels_per_beat)
            draw.text((padding - 35, y), f"{bpm:.0f}", 
                     fill=self.COLORS["bpm"], font=font)

        # Draw stops
        for beat, stop in chart_data['metadata'].stops:
            y = height - padding - (beat * pixels_per_beat)
            draw.text((width - padding + 5, y), f"Stop\n{stop:.2f}s", 
                     fill=self.COLORS["stop"], font=font)

        # Draw warps
        for beat, length in chart_data['metadata'].warps:
            y = height - padding - (beat * pixels_per_beat)
            draw.text((width - padding + 5, y), f"Warp\n{length:.2f}b", 
                     fill=self.COLORS["warp"], font=font)

        # Draw speed changes
        for beat, multiplier, duration in chart_data['metadata'].speeds:
            y = height - padding - (beat * pixels_per_beat)
            draw.text((padding - 35, y), f"{multiplier}x\n{duration:.1f}", 
                     fill=self.COLORS["speed"], font=font)

        # Draw scroll changes
        for beat, value in chart_data['metadata'].scrolls:
            y = height - padding - (beat * pixels_per_beat)
            draw.text((padding - 35, y), f"Scroll\n{value:.1f}", 
                     fill=self.COLORS["scroll"], font=font)

        # Draw notes
        for note in chart_data['notes']:
            x = padding + (note.column * column_width)
            y = height - padding - (note.beat * pixels_per_beat)
            
            if note.type in ['hold_head', 'roll_head']:
                # Draw hold/roll body
                hold_color = self.COLORS["hold"] if note.type == 'hold_head' else self.COLORS["roll"]
                hold_end_y = y - (note.hold_length * pixels_per_beat)
                draw.rectangle([x, hold_end_y, x + note_size, y],
                             fill=hold_color)
            
            # Draw note
            color = self.COLORS["mine"] if note.type == "mine" else self.COLORS["tap"]
            draw.rectangle([x, y - note_size, x + note_size, y],
                         fill=color, outline=(255, 255, 255))

        # Draw metadata
        metadata_text = f"{chart_data['metadata'].title} - {chart_data['metadata'].artist}\n"
        metadata_text += f"Chart: {chart_data['metadata'].difficulty} {chart_data['metadata'].meter}\n"
        metadata_text += f"Credit: {chart_data['metadata'].credit}"
        draw.text((padding, padding), metadata_text, 
                 fill=self.COLORS["text"], font=font)

        # Save image
        img.save(output_file)

def process_sm_file(sm_file: str, output_dir: Optional[str] = None, measures: Optional[int] = None):
    visualizer = ChartVisualizer(sm_file)
    charts = visualizer.parse_sm_file()
    
    # Create output directory if specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Process each chart
    for chart in charts:
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(sm_file))[0]
        diff_name = chart['metadata'].difficulty.lower()
        chart_type = 'S' if chart['type'] == 'dance-single' else 'D'
        
        output_name = f"{base_name}_{chart_type}_{diff_name}.png"
        if output_dir:
            output_path = os.path.join(output_dir, output_name)
        else:
            output_path = os.path.join(os.path.dirname(sm_file), output_name)
        
        # Generate visualization
        visualizer.generate_visualization(chart, output_path, measures)
        print(f"Generated {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate visualization for StepMania charts')
    parser.add_argument('input', help='Path to .sm file or directory')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--measures', '-m', type=int, help='Number of measures to show')
    parser.add_argument('--recursive', '-r', action='store_true', help='Search for .sm files recursively')
    
    args = parser.parse_args()
    
    # Process single file or directory
    if os.path.isfile(args.input):
        process_sm_file(args.input, args.output, args.measures)
    else:
        # Find all .sm files
        pattern = '**/*.sm' if args.recursive else '*.sm'
        sm_files = glob.glob(os.path.join(args.input, pattern), recursive=args.recursive)
        
        for sm_file in sm_files:
            print(f"\nProcessing {sm_file}...")
            process_sm_file(sm_file, args.output, args.measures)

if __name__ == "__main__":
    main() 