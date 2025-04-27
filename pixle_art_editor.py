#!/usr/bin/env python3
import sys
import os

# Ensure the project root directory is in the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
# src_path = os.path.join(project_root, 'src') # Old
if project_root not in sys.path:
    sys.path.insert(0, project_root) # Insert project root

# Import the Editor class and necessary setup items using full path from src
# from editor.pixle_art_editor import Editor, load_monsters, config, tk_root, monsters # Old
from src.editor.pixle_art_editor import Editor, load_monsters, config, tk_root, monsters # Import using src package

if __name__ == "__main__":
    # Replicate the necessary setup from the original __main__ block
    if not os.path.exists(config.SPRITE_DIR):
        os.makedirs(config.SPRITE_DIR)
        print(f"Created missing directory: {config.SPRITE_DIR}")
    if not os.path.exists(config.BACKGROUND_DIR):
        os.makedirs(config.BACKGROUND_DIR)
        print(f"Created missing directory: {config.BACKGROUND_DIR}")
    if not os.path.exists(config.DATA_DIR):
         os.makedirs(config.DATA_DIR)
         print(f"Created missing directory: {config.DATA_DIR}")

    # Ensure monster data is loaded appropriately (Original loads globally)
    # Check if the global `monsters` imported is already populated
    if 'monsters' not in globals() or not monsters:
        print("Reloading monster data for entry point...")
        try:
            # Re-assign to the global imported `monsters` variable is tricky.
            # Instead, load and set config.monsters as the original did.
            loaded_monsters = load_monsters()
            if not loaded_monsters:
                 print("Fatal: Could not load monster data. Exiting.")
                 sys.exit(1)
            config.monsters = loaded_monsters # Set the config attribute
        except Exception as e:
             print(f"Fatal: Could not load monster data. {e}. Exiting.")
             sys.exit(1)
    else:
        # If the imported `monsters` global *was* populated, still need to set config.monsters
        print("Using pre-loaded monster data for entry point...")
        config.monsters = monsters # Ensure config.monsters is set even if module loaded it

    # Ensure Tkinter root is initialized (original does this globally via import)
    if tk_root is None:
        print("Warning: Tkinter root failed to initialize during import.")
        # Editor might handle this internally, or we could exit:
        # sys.exit(1)

    # Instantiate and run the editor
    editor = Editor()
    editor.run() 