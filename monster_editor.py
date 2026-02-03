#!/usr/bin/env python3
import os
import sys
import runpy

# Ensure the project root directory is in the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

if __name__ == "__main__":
    print("Running monster editor from root script...")
    try:
        runpy.run_module("src.editor.monster_editor", run_name="__main__", alter_sys=True)
    except ImportError as e:
        print("Error: Could not run the monster editor module. Make sure you are in the project root directory.")
        print(f"Details: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
