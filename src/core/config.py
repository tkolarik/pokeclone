# config.py
import os

# General
FPS = 60

# Screen Dimensions
EDITOR_WIDTH = 1300
EDITOR_HEIGHT = 800
BATTLE_WIDTH = 1200
BATTLE_HEIGHT = 600
MENU_WIDTH = 800
MENU_HEIGHT = 600

# Sprite Configuration
NATIVE_SPRITE_RESOLUTION = (32, 32)
# Overworld Configuration
OVERWORLD_TILE_SIZE = NATIVE_SPRITE_RESOLUTION[0]
OVERWORLD_GRID_WIDTH = 20
OVERWORLD_GRID_HEIGHT = 15
OVERWORLD_WIDTH = OVERWORLD_TILE_SIZE * OVERWORLD_GRID_WIDTH
OVERWORLD_HEIGHT = OVERWORLD_TILE_SIZE * OVERWORLD_GRID_HEIGHT
# Default tileset to fall back on for overworld/tile editor
DEFAULT_TILESET_ID = "basic_overworld"
# Factor to scale native sprites for battle display
BATTLE_SPRITE_SCALE_FACTOR = 6
BATTLE_SPRITE_DISPLAY_SIZE = (
    NATIVE_SPRITE_RESOLUTION[0] * BATTLE_SPRITE_SCALE_FACTOR,
    NATIVE_SPRITE_RESOLUTION[1] * BATTLE_SPRITE_SCALE_FACTOR
)

# Editor Specific Configuration
# Visual grid matches native width
EDITOR_GRID_SIZE = NATIVE_SPRITE_RESOLUTION[0]
# Magnification factor for display in editor
EDITOR_PIXEL_SIZE = 15
MAX_BRUSH_SIZE = 20
PALETTE_COLS = 20
PALETTE_ROWS = 8

# Background Configuration
# Default size used by editor if creating new or no background exists
DEFAULT_BACKGROUND_WIDTH = 1600
DEFAULT_BACKGROUND_HEIGHT = 800
# Note: Battle sim scales loaded backgrounds to BATTLE_WIDTH, BATTLE_HEIGHT

# Directory Paths (relative to project root)
# Use absolute paths based on this file's location for robustness
# Go up two levels: src/core -> src -> project_root
# PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Previous attempt

# Calculate paths based on this file's location
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__)) # .../pokeclone/src/core
SRC_DIR = os.path.dirname(CONFIG_DIR) # .../pokeclone/src
PROJECT_ROOT = os.path.dirname(SRC_DIR) # .../pokeclone

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MAP_DIR = os.path.join(DATA_DIR, "maps")
TILESET_DIR = os.path.join(DATA_DIR, "tilesets")
TILE_IMAGE_DIR = os.path.join(PROJECT_ROOT, "tiles")
SPRITE_DIR = os.path.join(PROJECT_ROOT, "sprites")
BACKGROUND_DIR = os.path.join(PROJECT_ROOT, "backgrounds")
SOUNDS_DIR = os.path.join(PROJECT_ROOT, "sounds") # For POKE-13
SONGS_DIR = os.path.join(PROJECT_ROOT, "songs")
REFERENCE_IMAGE_DIR = os.path.join(PROJECT_ROOT, "references")

# Battle Mechanics
STAT_CHANGE_MULTIPLIER = 0.66
MIN_MONSTER_LEVEL = 1
MAX_MONSTER_LEVEL = 100
DEFAULT_MONSTER_LEVEL = 25
LEVEL_STAT_GROWTH = 0.02
MAX_BATTLE_MOVES = 4
DEFAULT_TEAM_SIZE = 6
DEFAULT_TEAM_LEVEL = 50

# UI Elements Fonts (Using None uses default pygame font)
DEFAULT_FONT = None # Pygame default
BATTLE_FONT_SIZE = 30
EDITOR_INFO_FONT_SIZE = 16
PALETTE_FONT_SIZE = 14
BUTTON_FONT_SIZE = 14
MENU_TITLE_FONT_SIZE = 48
MENU_OPTION_FONT_SIZE = 28
OVERWORLD_FONT_SIZE = 20

# Colors (Define common colors here)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY_LIGHT = (200, 200, 200)
GRAY_MEDIUM = (170, 170, 170)
GRAY_DARK = (100, 100, 100)

EDITOR_BG_COLOR = GRAY_LIGHT
BATTLE_BG_COLOR = WHITE
OVERWORLD_BG_COLOR = (90, 140, 90)

# Overworld music fallback (when maps omit musicId). Filenames live in songs/.
OVERWORLD_MUSIC_TRACKS = ["Overworld-1.wav", "Overworld-2.wav", "Overworld-3.wav"]
HP_BAR_COLOR = GREEN
BUTTON_COLOR = GRAY_LIGHT
BUTTON_HOVER_COLOR = GRAY_MEDIUM
BUTTON_ACTIVE_COLOR = (240, 220, 140)
BUTTON_ACTIVE_TEXT_COLOR = BLACK
SELECTION_HIGHLIGHT_COLOR = RED
SELECTION_FILL_COLOR = (*BLUE, 50) # Semi-transparent blue
GRID_COLOR_1 = GRAY_LIGHT
GRID_COLOR_2 = WHITE
TRANSPARENT_INDICATOR_COLOR = RED # For palette
MENU_BG_COLOR = GRAY_LIGHT
MENU_TEXT_COLOR = BLACK
MENU_HIGHLIGHT_COLOR = GREEN

# Panning Speed
PAN_SPEED_PIXELS = 20 # Pixels to shift per pan action

# Ensure data directory exists (optional nice-to-have)
if not os.path.exists(DATA_DIR):
    print(f"Warning: Data directory '{DATA_DIR}' not found. Creating it.")
    os.makedirs(DATA_DIR)

# Ensure asset directories exist
for dir_path in [SPRITE_DIR, BACKGROUND_DIR, SOUNDS_DIR, SONGS_DIR, REFERENCE_IMAGE_DIR, MAP_DIR, TILESET_DIR, TILE_IMAGE_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Created missing directory: {dir_path}")

print("Configuration loaded.") 
