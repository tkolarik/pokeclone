# config.py
import os

# General
FPS = 60

# Screen Dimensions
EDITOR_WIDTH = 1300
EDITOR_HEIGHT = 800
BATTLE_WIDTH = 1200
BATTLE_HEIGHT = 600

# Sprite Configuration
NATIVE_SPRITE_RESOLUTION = (32, 32)
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
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SPRITE_DIR = os.path.join(PROJECT_ROOT, "sprites")
BACKGROUND_DIR = os.path.join(PROJECT_ROOT, "backgrounds")
SOUNDS_DIR = os.path.join(PROJECT_ROOT, "sounds") # For POKE-13
SONGS_DIR = os.path.join(PROJECT_ROOT, "songs")

# Battle Mechanics
STAT_CHANGE_MULTIPLIER = 0.66

# UI Elements Fonts (Using None uses default pygame font)
DEFAULT_FONT = None # Pygame default
BATTLE_FONT_SIZE = 30
EDITOR_INFO_FONT_SIZE = 16
PALETTE_FONT_SIZE = 14
BUTTON_FONT_SIZE = 14

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
HP_BAR_COLOR = GREEN
BUTTON_COLOR = GRAY_LIGHT
BUTTON_HOVER_COLOR = GRAY_MEDIUM
SELECTION_HIGHLIGHT_COLOR = RED
SELECTION_FILL_COLOR = (*BLUE, 50) # Semi-transparent blue
GRID_COLOR_1 = GRAY_LIGHT
GRID_COLOR_2 = WHITE
TRANSPARENT_INDICATOR_COLOR = RED # For palette

# Panning Speed
PAN_SPEED_PIXELS = 20 # Pixels to shift per pan action

# Ensure data directory exists (optional nice-to-have)
if not os.path.exists(DATA_DIR):
    print(f"Warning: Data directory '{DATA_DIR}' not found. Creating it.")
    os.makedirs(DATA_DIR)

# Ensure asset directories exist
for dir_path in [SPRITE_DIR, BACKGROUND_DIR, SOUNDS_DIR, SONGS_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Created missing directory: {dir_path}")

print("Configuration loaded.") 