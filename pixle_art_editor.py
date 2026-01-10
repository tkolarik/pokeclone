#!/usr/bin/env python3
import sys
import os
import runpy

# Ensure the project root directory is in the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    print("Running editor from root script...")
    # Use runpy to execute the main editor module correctly
    # This ensures its own __name__ == "__main__" block runs
    try:
        runpy.run_module("src.editor.pixle_art_editor", run_name="__main__", alter_sys=True)
    except ImportError as e:
        print(f"Error: Could not run the editor module. Make sure you are in the project root directory.")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)