import pygame
import json
import os
import sys # Added sys import

# Add project root to path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the centralized config
# import config # Original
from src.core import config # Updated import

# Initialize Pygame (required for surface creation)
pygame.init()

# Constants from config
# NATIVE_SPRITE_RESOLUTION = (32, 32) # Reverted to 32x32
# BACKGROUND_WIDTH, BACKGROUND_HEIGHT = 1200, 600

# Load monster data using config path
monsters_file = os.path.join(config.DATA_DIR, "monsters.json")
try:
    with open(monsters_file, "r") as f:
        monsters = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
     print(f"Error loading {monsters_file}: {e}. Cannot proceed.")
     pygame.quit()
     exit() # Use exit() instead of sys.exit() if sys not imported

# Get the names of all monsters in the JSON file
monster_names = {monster['name'] for monster in monsters}

# Directory existence checks are now handled in config.py upon import
# # Ensure the sprites directory exists
# if not os.path.exists(config.SPRITE_DIR):
#     os.makedirs(config.SPRITE_DIR)
# 
# # Ensure the backgrounds directory exists
# if not os.path.exists(config.BACKGROUND_DIR):
#     os.makedirs(config.BACKGROUND_DIR)

# Remove sprites that don't match any monsters in monsters.json
# Use config path
print(f"Checking sprites in: {config.SPRITE_DIR}")
try:
    for filename in os.listdir(config.SPRITE_DIR):
        if filename.endswith(".png"):
            parts = filename.split('_')
            if len(parts) >= 2:
                sprite_name = parts[0]
                if sprite_name not in monster_names:
                    try:
                        file_path = os.path.join(config.SPRITE_DIR, filename)
                        os.remove(file_path)
                        print(f"Removed orphaned sprite: {filename}")
                    except OSError as e:
                        print(f"Error removing sprite {filename}: {e}")
            else:
                print(f"Skipping unusually named file in sprites folder: {filename}")
except FileNotFoundError:
     print(f"Warning: Sprite directory {config.SPRITE_DIR} not found during cleanup check.")

# Create empty transparent sprites for all monsters if they don't exist
print("Ensuring sprites exist for all monsters...")
for monster in monsters:
    for sprite_type in ['front', 'back']:
        # Use config path
        filename = os.path.join(config.SPRITE_DIR, f"{monster['name']}_{sprite_type}.png")
        if not os.path.exists(filename):
            # Create surface at native resolution from config
            surface = pygame.Surface(config.NATIVE_SPRITE_RESOLUTION, pygame.SRCALPHA)
            surface.fill((*config.BLACK[:3], 0)) # Ensure it's transparent using config color
            try:
                 pygame.image.save(surface, filename)
                 print(f"Created empty sprite: {filename} at {config.NATIVE_SPRITE_RESOLUTION}")
            except pygame.error as e:
                 print(f"Error saving empty sprite {filename}: {e}")
        # else: # Don't print anything if it exists, reduces noise
        #     print(f"Sprite already exists: {filename}")

# Create an empty background if none exists
# Use config path
print(f"Checking backgrounds in: {config.BACKGROUND_DIR}")
try:
    background_files = [f for f in os.listdir(config.BACKGROUND_DIR) if f.endswith('.png')]
    if not background_files:
        print("No backgrounds found, creating a default one.")
        # Use default dimensions from config
        empty_background = pygame.Surface((config.DEFAULT_BACKGROUND_WIDTH, config.DEFAULT_BACKGROUND_HEIGHT))
        empty_background.fill(config.WHITE)  # Use config color
        
        background_filename = os.path.join(config.BACKGROUND_DIR, "default_background.png")
        try:
            pygame.image.save(empty_background, background_filename)
            print(f"Created empty background: {background_filename}")
        except pygame.error as e:
             print(f"Error saving empty background {background_filename}: {e}")
    else:
        print("Background(s) already exist.")
except FileNotFoundError:
     print(f"Warning: Background directory {config.BACKGROUND_DIR} not found.")

print("Sprite check and creation process complete.")

# Quit Pygame
pygame.quit()
