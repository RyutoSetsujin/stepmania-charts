import json
import jsonschema
import os
import sys
from typing import Dict, List, Optional

def load_schema(schema_path: str) -> Dict:
    """Load the JSON schema from file."""
    with open(schema_path, 'r') as f:
        return json.load(f)

def validate_song_file(file_path: str, schema: Dict) -> List[str]:
    """Validate a single song JSON file against the schema."""
    errors = []
    try:
        with open(file_path, 'r') as f:
            song_data = json.load(f)
        jsonschema.validate(instance=song_data, schema=schema)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in {file_path}: {str(e)}")
    except jsonschema.exceptions.ValidationError as e:
        errors.append(f"Validation error in {file_path}: {str(e)}")
    return errors

def validate_all_songs(songs_dir: str, schema: Dict) -> Dict[str, List[str]]:
    """Validate all song JSON files in the directory."""
    validation_results = {}
    
    # Walk through the songs directory
    for root, _, files in os.walk(songs_dir):
        for file in files:
            if file.endswith('.json') and file != 'index.json':
                file_path = os.path.join(root, file)
                errors = validate_song_file(file_path, schema)
                if errors:
                    validation_results[file_path] = errors
    
    return validation_results

def main():
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python validate_songs.py <songs_directory>")
        sys.exit(1)
    
    songs_dir = sys.argv[1]
    schema_path = "song_schema.json"
    
    # Check if paths exist
    if not os.path.exists(songs_dir):
        print(f"Error: Songs directory '{songs_dir}' does not exist")
        sys.exit(1)
    if not os.path.exists(schema_path):
        print(f"Error: Schema file '{schema_path}' does not exist")
        sys.exit(1)
    
    # Load schema and validate songs
    schema = load_schema(schema_path)
    validation_results = validate_all_songs(songs_dir, schema)
    
    # Print results
    if validation_results:
        print("\nValidation errors found:")
        for file_path, errors in validation_results.items():
            print(f"\n{file_path}:")
            for error in errors:
                print(f"  - {error}")
        sys.exit(1)
    else:
        print("All song files are valid!")
        sys.exit(0)

if __name__ == "__main__":
    main() 