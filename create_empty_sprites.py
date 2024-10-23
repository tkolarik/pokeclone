import pygame
import json
import os

# Initialize Pygame (required for surface creation)
pygame.init()

# Constants (ensure these match your game settings)
GRID_SIZE = 32
PIXEL_SIZE = 15
BACKGROUND_WIDTH, BACKGROUND_HEIGHT = 1200, 600

# Load monster data
with open("data/monsters.json", "r") as f:
    monsters = json.load(f)

# Get the names of all monsters in the JSON file
monster_names = {monster['name'] for monster in monsters}

# Ensure the sprites directory exists
if not os.path.exists("sprites"):
    os.makedirs("sprites")

# Ensure the backgrounds directory exists
if not os.path.exists("backgrounds"):
    os.makedirs("backgrounds")

# Remove sprites that don't match any monsters in monsters.json
for filename in os.listdir("sprites"):
    if filename.endswith(".png"):
        sprite_name = filename.split('_')[0]
        if sprite_name not in monster_names:
            os.remove(os.path.join("sprites", filename))
            print(f"Removed sprite: {filename}")

# Create empty transparent sprites for all monsters
for monster in monsters:
    for sprite_type in ['front', 'back']:
        filename = f"sprites/{monster['name']}_{sprite_type}.png"
        if not os.path.exists(filename):
            surface = pygame.Surface((GRID_SIZE * PIXEL_SIZE, GRID_SIZE * PIXEL_SIZE), pygame.SRCALPHA)
            pygame.image.save(surface, filename)
            print(f"Created empty sprite: {filename}")
        else:
            print(f"Sprite already exists: {filename}")

# Create an empty background if none exists
background_files = [f for f in os.listdir("backgrounds") if f.endswith('.png')]
if not background_files:
    empty_background = pygame.Surface((BACKGROUND_WIDTH, BACKGROUND_HEIGHT))
    empty_background.fill((255, 255, 255))  # White background
    pygame.image.save(empty_background, "backgrounds/empty_background.png")
    print("Created empty background: backgrounds/empty_background.png")
else:
    print("Background(s) already exist.")

print("All unnecessary sprites have been removed, new empty sprites created where needed, and an empty background created if none existed.")
