#!/usr/bin/env python3
import sys
import os

# Ensure the project root directory is in the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
# src_path = os.path.join(project_root, 'src') # Old
if project_root not in sys.path:
    sys.path.insert(0, project_root) # Insert project root

# Import and run the main function using the full path from src
# from battle.battle_simulator import main # Old
from src.battle.battle_simulator import main # Import using src package

if __name__ == "__main__":
    main() 