"""
Safe JSON Writer - Ensures atomic file writes to prevent corruption
"""
import json
import tempfile
import os
import shutil
from pathlib import Path
from typing import Any, Union


def safe_write_json(
    filepath: Union[str, Path],
    data: Any,
    indent: int = 2,
    create_backup: bool = True
) -> None:
    """
    Safely write JSON to a file using atomic operations.
    
    This prevents file corruption from interrupted writes by:
    1. Writing to a temporary file first
    2. Creating a backup of the original file
    3. Moving the temp file to replace the original
    
    Args:
        filepath: Path to the JSON file to write
        data: Python object to serialize as JSON
        indent: JSON indentation level (default: 2)
        create_backup: Whether to create a backup of the original file
    
    Raises:
        IOError: If file operations fail
        json.JSONEncodeError: If data cannot be serialized to JSON
    """
    filepath = Path(filepath)
    
    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Create backup if file exists and create_backup is True
    if filepath.exists() and create_backup:
        backup_path = filepath.with_suffix(filepath.suffix + '.backup')
        shutil.copy2(filepath, backup_path)
    
    # Write to a temporary file in the same directory
    # This ensures we're on the same filesystem for atomic move
    temp_fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent,
        prefix=f'.{filepath.stem}_',
        suffix='.tmp'
    )
    
    try:
        # Write JSON to temp file
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
        
        # Atomically replace the original file
        # On Windows, we need to remove the target first
        if os.path.exists(filepath):
            os.replace(temp_path, filepath)
        else:
            shutil.move(temp_path, filepath)
            
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise IOError(f"Failed to write JSON to {filepath}: {e}") from e


def safe_read_json(filepath: Union[str, Path]) -> Any:
    """
    Safely read JSON from a file.
    
    If the main file is corrupted, attempts to read from backup.
    
    Args:
        filepath: Path to the JSON file to read
        
    Returns:
        Parsed JSON object
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    filepath = Path(filepath)
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        # Try to read from backup
        backup_path = filepath.with_suffix(filepath.suffix + '.backup')
        if backup_path.exists():
            print(f"Warning: Main file corrupted, reading from backup: {backup_path}")
            with open(backup_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        raise


# Example usage:
if __name__ == '__main__':
    # Test the safe writer
    test_data = {
        "name": "Test",
        "rules": [],
        "statistics": {
            "total_rules": 0
        }
    }
    
    test_file = Path(__file__).parent / 'test_safe_json.json'
    
    # Write safely
    safe_write_json(test_file, test_data)
    print(f"✓ Successfully wrote JSON to {test_file}")
    
    # Read safely
    data = safe_read_json(test_file)
    print(f"✓ Successfully read JSON: {data}")
    
    # Clean up
    test_file.unlink()
    if test_file.with_suffix('.json.backup').exists():
        test_file.with_suffix('.json.backup').unlink()
