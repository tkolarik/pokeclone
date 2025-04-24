import pygame
from pygame.locals import *
import tkinter as tk
from tkinter import filedialog, colorchooser
import sys
import os
import json
import copy
import colorsys

# Import the centralized config
import config

# Initialize Tkinter root window and hide it
try:
    root = tk.Tk() # Indent this
    root.withdraw() # Indent this
except tk.TclError as e:
    print(f"Warning: Could not initialize Tkinter (Needed for native dialogs): {e}")
    root = None # Flag that tkinter is unavailable

# Now import and initialize Pygame
pygame.init()

# Constants are now in config.py
# WIDTH, HEIGHT = 1300, 800
# EDITOR_GRID_SIZE = 32 # Visual grid size for editing
# PIXEL_SIZE = 15  # Visual size of each 'pixel' in the editor grid
# NATIVE_SPRITE_RESOLUTION = (32, 32) # Actual resolution of the sprite data
# FPS = 60
# BACKGROUND_WIDTH, BACKGROUND_HEIGHT = 1600, 800
# MAX_BRUSH_SIZE = 20
# PALETTE_COLS = 20
# PALETTE_ROWS = 8

# Setup
screen = pygame.display.set_mode((config.EDITOR_WIDTH, config.EDITOR_HEIGHT))
pygame.display.set_caption("Advanced Pixel Art Sprite Editor with Enhanced Features")
clock = pygame.time.Clock()

# Enhanced color palette generation
def generate_palette():
    """
    Generate an enhanced color palette for the pixel art editor.

    This function creates a wide range of colors, including a variety of hues,
    saturations, and values, as well as grayscale colors. The resulting palette
    is used for painting and color selection in the editor.

    Returns:
        list: A list of RGBA color tuples representing the generated palette.
    """
    PALETTE = [(0, 0, 0, 255)]  # Start with black
    # Generate a wide range of colors
    for h in range(0, 360, 30):  # Hue
        for s in [50, 100]:  # Saturation
            for v in [50, 100]:  # Value
                r, g, b = colorsys.hsv_to_rgb(h/360, s/100, v/100)
                PALETTE.append((int(r*255), int(g*255), int(b*255), 255))
    # Add grayscale
    for i in range(10):
        gray = int(255 * i / 9)
        PALETTE.append((gray, gray, gray, 255))
    return PALETTE

PALETTE = generate_palette()

# Load monster data
def load_monsters():
    """
    Load monster data from the 'monsters.json' file.

    This function reads the 'monsters.json' file, which contains information about
    various monsters, including their names, types, max HP, and moves. The data
    is used to populate the editor with monster sprites and their attributes.

    Returns:
        list: A list of dictionaries, each representing a monster with its attributes.
    """
    # Use path from config
    monsters_file = os.path.join(config.DATA_DIR, "monsters.json")

    try:
        with open(monsters_file, "r") as f:
            monsters = json.load(f)
        if not isinstance(monsters, list):
            raise ValueError("monsters.json should contain a list of monsters.")
        return monsters
    except FileNotFoundError:
        print(f"Error: Could not find monsters.json in {os.path.dirname(monsters_file)}")
        print("Make sure you've created the data directory and added the monsters.json file.")
        pygame.quit()
        sys.exit(1)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: {e}")
        pygame.quit()
        sys.exit(1)

monsters = load_monsters()

# Button Class
class Button:
    """
    A simple button class for the pixel art editor.

    This class represents a clickable button with a text label. It handles drawing
    the button on a surface, checking for mouse clicks, and executing an associated
    action when clicked.

    Attributes:
        rect (pygame.Rect): The rectangle defining the button's position and size.
        text (str): The text label displayed on the button.
        action (callable): The function to be executed when the button is clicked.
        color (tuple): The background color of the button (R, G, B).
        hover_color (tuple): The background color of the button when the mouse is hovering over it (R, G, B).
        font (pygame.font.Font): The font used for rendering the button text.

    Methods:
        draw(surface: pygame.Surface) -> None
        is_clicked(event: pygame.event.Event) -> bool
    """

    def __init__(self, rect, text, action=None, value=None):
        """
        Initialize a new Button instance.

        Args:
            rect (tuple): A tuple representing the button's rectangle (x, y, width, height).
            text (str): The text label to display on the button.
            action (callable, optional): The function to be executed when the button is clicked.
            value (any, optional): The value to be stored with the button.
        """
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action
        self.value = value
        self.color = config.BUTTON_COLOR
        self.hover_color = config.BUTTON_HOVER_COLOR
        self.font = pygame.font.Font(config.DEFAULT_FONT, config.BUTTON_FONT_SIZE)

    def draw(self, surface):
        """
        Draw the button on a given surface.

        Args:
            surface (pygame.Surface): The surface on which to draw the button.
        """
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse_pos)
        color = self.hover_color if is_hover else self.color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, config.BLACK, self.rect, 2)
        text_surf = self.font.render(self.text, True, config.BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, event):
        """
        Check if the button was clicked based on a mouse event.

        Args:
            event (pygame.event.Event): The mouse event to check for a click.

        Returns:
            bool: True if the button was clicked, False otherwise.
        """
        return event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos)

# SpriteEditor Class
class SpriteEditor:
    """ Edits sprites at 32x32 native resolution. """
    def __init__(self, position, name, sprite_dir):
        self.position = position
        self.name = name
        self.sprite_dir = sprite_dir # Store the directory
        # Internal frame stores the actual sprite data at native resolution (32x32)
        self.frame = pygame.Surface(config.NATIVE_SPRITE_RESOLUTION, pygame.SRCALPHA)
        self.frame.fill((*config.BLACK[:3], 0)) # Transparent black
        # Calculate the total display size of the editor grid
        self.display_width = config.EDITOR_GRID_SIZE * config.EDITOR_PIXEL_SIZE
        self.display_height = config.EDITOR_GRID_SIZE * config.EDITOR_PIXEL_SIZE

    def load_sprite(self, monster_name):
        """Loads sprite, checks size, scales to NATIVE_SPRITE_RESOLUTION if needed."""
        self.frame.fill((*config.BLACK[:3], 0)) # Transparent black
        # Use the stored sprite_dir
        filename = os.path.join(self.sprite_dir, f"{monster_name}_{self.name}.png")
        if os.path.exists(filename):
            try:
                loaded_image = pygame.image.load(filename).convert_alpha()
                # Scale to native (32x32) if it doesn't match
                if loaded_image.get_size() != config.NATIVE_SPRITE_RESOLUTION:
                    print(f"Warning: Loaded sprite {filename} size {loaded_image.get_size()} does not match native {config.NATIVE_SPRITE_RESOLUTION}. Scaling down.")
                    loaded_image = pygame.transform.smoothscale(loaded_image, config.NATIVE_SPRITE_RESOLUTION)
                self.frame.blit(loaded_image, (0, 0))
            except pygame.error as e:
                 print(f"Error loading sprite {filename}: {e}")
                 self.frame.fill((*config.RED[:3], 100)) # Semi-transparent red/magenta placeholder
        else:
            print(f"Sprite not found: {filename}. Creating blank.")
            self.frame.fill((*config.BLACK[:3], 0))

    def save_sprite(self, monster_name):
        """Saves the internal 32x32 frame directly, requires monster_name."""
        # config.py should ensure SPRITE_DIR exists

        # Ensure monster_name is provided
        if not monster_name:
            print("Error: Cannot save sprite. Monster name is required.")
            return

        filename = os.path.join(self.sprite_dir, f"{monster_name}_{self.name}.png")
        try:
            pygame.image.save(self.frame, filename)
            print(f"Saved sprite: {filename} at {config.NATIVE_SPRITE_RESOLUTION}")
        except pygame.error as e:
             print(f"Error saving sprite {filename}: {e}")

    def draw_background(self, surface):
        """Draws the checkerboard background for the editor grid."""
        for y in range(config.EDITOR_GRID_SIZE):
            for x in range(config.EDITOR_GRID_SIZE):
                rect = (self.position[0] + x * config.EDITOR_PIXEL_SIZE, 
                        self.position[1] + y * config.EDITOR_PIXEL_SIZE, 
                        config.EDITOR_PIXEL_SIZE, config.EDITOR_PIXEL_SIZE)
                color = config.GRID_COLOR_1 if (x + y) % 2 == 0 else config.GRID_COLOR_2
                pygame.draw.rect(surface, color, rect)

    def draw_pixels(self, surface):
        """Draws the scaled sprite pixels onto the target surface."""
        # Scale the 32x32 native frame up to the display size (e.g., 480x480)
        # Use regular scale for pixel art sharpness
        scaled_display_frame = pygame.transform.scale(self.frame, (self.display_width, self.display_height))
        surface.blit(scaled_display_frame, self.position)

    def draw_highlight(self, surface):
        """Draws the highlight rectangle if this editor is active."""
        # Draw highlight rectangle based on display size (unchanged)
        # This logic is moved from the old draw method
        # Assuming `editor` is accessible globally or passed differently if needed.
        # For now, let's assume it's accessible as before.
        # TODO: Refactor editor access if needed.
        global editor # Temporary fix, consider passing editor instance if refactoring
        if editor.current_sprite == self.name:
            highlight_rect = pygame.Rect(self.position[0] - 10, self.position[1] - 10,
                                         self.display_width + 20, self.display_height + 20)
            pygame.draw.rect(surface, config.SELECTION_HIGHLIGHT_COLOR, highlight_rect, 3)

    def draw(self, surface):
        """Draws the scaled-up sprite editor grid onto the target surface.
           DEPRECATED in favor of draw_background and draw_pixels.
           Kept for compatibility or potential future use, but logic moved.
        """
        # This method is now simplified or can be removed if draw_ui is fully updated.
        # For safety, let's make it call the new methods for now.
        self.draw_background(surface)
        self.draw_pixels(surface)
        # Highlight is drawn separately in draw_ui now.

    def get_grid_position(self, pos):
        """Converts screen coordinates (within display area) to 32x32 grid coordinates."""
        x, y = pos
        # Check if click is within the visual editor bounds
        if not (self.position[0] <= x < self.position[0] + self.display_width and
                self.position[1] <= y < self.position[1] + self.display_height):
            return None

        # Calculate grid coordinates directly from relative position and PIXEL_SIZE
        grid_x = (x - self.position[0]) // config.EDITOR_PIXEL_SIZE
        grid_y = (y - self.position[1]) // config.EDITOR_PIXEL_SIZE

        # Ensure coordinates are within the 32x32 grid bounds
        if 0 <= grid_x < config.EDITOR_GRID_SIZE and 0 <= grid_y < config.EDITOR_GRID_SIZE:
             # Since native is 32x32 and editor grid is 32x32, coords are the same
            return grid_x, grid_y
        return None

    def draw_pixel(self, grid_pos, color):
        """Draws a pixel at the given 32x32 grid coordinates."""
        if 0 <= grid_pos[0] < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= grid_pos[1] < config.NATIVE_SPRITE_RESOLUTION[1]:
            self.frame.set_at(grid_pos, color)

    def get_pixel_color(self, grid_pos):
         """Gets the color of a pixel from the 32x32 grid coordinates."""
         if 0 <= grid_pos[0] < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= grid_pos[1] < config.NATIVE_SPRITE_RESOLUTION[1]:
            return self.frame.get_at(grid_pos)
         return None

# Palette Class with Scrollable Feature
class Palette:
    """
    A scrollable color palette for the pixel art editor.

    This class represents a scrollable color palette that allows users to select
    colors for painting and drawing in the editor. It supports scrolling through
    a large number of colors and provides a visual representation of each color.

    Attributes:
        position (tuple): The (x, y) position of the palette on the screen.
        block_size (int): The size of each color block in the palette.
        padding (int): The padding between color blocks.
        gap (int): The gap between the palette and other UI elements.
        font (pygame.font.Font): The font used for rendering the palette label.
        scroll_offset (int): The current scroll offset within the palette.
        colors_per_page (int): The number of colors displayed per page.
        total_pages (int): The total number of pages in the palette.

    Methods:
        draw(surface: pygame.Surface) -> None
        handle_click(pos: tuple) -> None
    """

    def __init__(self, position):
        """
        Initialize a new Palette instance.

        Args:
            position (tuple): The (x, y) position of the palette on the screen.
        """
        self.position = position  # (x, y) starting position on screen
        self.block_size = 15  # Reduced block size
        self.padding = 2  # Reduced padding
        self.gap = 5
        self.font = pygame.font.Font(config.DEFAULT_FONT, config.PALETTE_FONT_SIZE)
        self.scroll_offset = 0
        self.colors_per_page = config.PALETTE_COLS * config.PALETTE_ROWS
        self.total_pages = (len(PALETTE) + self.colors_per_page - 1) // self.colors_per_page

    def draw(self, surface):
        """
        Draw the palette on a given surface.

        Args:
            surface (pygame.Surface): The surface on which to draw the palette.
        """
        x0, y0 = self.position
        current_page = self.scroll_offset
        start_index = current_page * self.colors_per_page
        end_index = start_index + self.colors_per_page
        visible_palette = PALETTE[start_index:end_index]

        for index, color in enumerate(visible_palette):
            col = index % config.PALETTE_COLS
            row = index // config.PALETTE_COLS
            rect = pygame.Rect(
                x0 + col * (self.block_size + self.padding),
                y0 + row * (self.block_size + self.padding),
                self.block_size,
                self.block_size
            )

            if color[3] == 0:  # Transparent color
                pygame.draw.rect(surface, config.GRAY_LIGHT, rect)
                pygame.draw.line(surface, config.TRANSPARENT_INDICATOR_COLOR, rect.topleft, rect.bottomright, 2)
                pygame.draw.line(surface, config.TRANSPARENT_INDICATOR_COLOR, rect.topright, rect.bottomleft, 2)
            else:
                pygame.draw.rect(surface, color[:3], rect)

            if color == editor.current_color:
                pygame.draw.rect(surface, config.SELECTION_HIGHLIGHT_COLOR, rect.inflate(4, 4), 2)

        # Palette label
        label = self.font.render("Palette", True, config.BLACK)
        surface.blit(label, (x0, y0 - 30))

        # Scroll indicators
        if self.total_pages > 1:
            up_arrow = self.font.render("↑", True, config.BLACK)
            down_arrow = self.font.render("↓", True, config.BLACK)
            surface.blit(up_arrow, (x0 + config.PALETTE_COLS * (self.block_size + self.padding) + 10, y0))
            surface.blit(down_arrow, (x0 + config.PALETTE_COLS * (self.block_size + self.padding) + 10, y0 + config.PALETTE_ROWS * (self.block_size + self.padding) - 20))

    def handle_click(self, pos):
        """
        Handle a mouse click event on the palette.

        This method checks if a color block was clicked and selects the corresponding
        color in the editor. It also handles scrolling through the palette using
        the scroll indicators.

        Args:
            pos (tuple): The (x, y) position of the mouse click.
        """
        x0, y0 = self.position
        x, y = pos
        # Check for scroll buttons
        scroll_area_x = x0 + config.PALETTE_COLS * (self.block_size + self.padding) + 10
        if x >= scroll_area_x and x <= scroll_area_x + 20:
            if y <= self.position[1] + config.PALETTE_ROWS * (self.block_size + self.padding):
                # Up arrow
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
            elif y >= self.position[1] + config.PALETTE_ROWS * (self.block_size + self.padding) - 20:
                # Down arrow
                if self.scroll_offset < self.total_pages - 1:
                    self.scroll_offset += 1
            return

        # Determine which color was clicked
        for index, color in enumerate(PALETTE[self.scroll_offset * self.colors_per_page:(self.scroll_offset + 1) * self.colors_per_page]):
            col = index % config.PALETTE_COLS
            row = index // config.PALETTE_COLS
            rect = pygame.Rect(
                x0 + col * (self.block_size + self.padding),
                y0 + row * (self.block_size + self.padding),
                self.block_size,
                self.block_size
            )
            if rect.collidepoint(x, y):
                editor.select_color(color)
                # Disable paste mode and select mode when selecting a color
                editor.paste_mode = False
                if editor.mode == 'select':
                    editor.mode = 'draw'
                    editor.selection.selecting = False
                    editor.selection.active = False
                return

# Selection Tool Class
class SelectionTool:
    """
    A selection tool for the pixel art editor.

    This class allows users to select and manipulate a rectangular area of pixels
    within the editor. It supports copying, pasting, mirroring, and rotating
    the selected area.

    Attributes:
        editor (Editor): The main editor instance.
        selecting (bool): Flag indicating if the selection tool is currently active.
        active (bool): Flag indicating if a selection is currently in progress.
        start_pos (tuple): The starting position of the selection rectangle.
        end_pos (tuple): The ending position of the selection rectangle.
        rect (pygame.Rect): The current selection rectangle.

    Methods:
        toggle() -> None
        start(pos: tuple) -> None
        update(pos: tuple) -> None
        end_selection(pos: tuple) -> None
        update_rect() -> None
        draw(surface: pygame.Surface) -> None
        get_selected_pixels() -> dict
    """

    def __init__(self, editor):
        """
        Initialize a new SelectionTool instance.

        Args:
            editor (Editor): The main editor instance.
        """
        self.editor = editor
        self.selecting = False
        self.active = False
        self.start_pos = None
        self.end_pos = None
        self.rect = pygame.Rect(0, 0, 0, 0)

    def toggle(self):
        """
        Toggle the selection tool's activation state.
        """
        self.selecting = True  # Always start fresh selection
        self.active = False  # Reset active state
        self.start_pos = None  # Reset start position
        self.end_pos = None  # Reset end position
        self.rect = pygame.Rect(0, 0, 0, 0)  # Reset rectangle
        print("Selection mode activated.")

    def start(self, pos):
        """
        Start a new selection at the given position.

        Args:
            pos (tuple): The starting position of the selection rectangle.
        """
        sprite = self.editor.sprites[self.editor.current_sprite]
        grid_pos = sprite.get_grid_position(pos)
        if grid_pos:
            self.start_pos = grid_pos
            self.end_pos = grid_pos
            self.update_rect()
            print(f"Selection started at: {self.start_pos}")

    def update(self, pos):
        """
        Update the selection rectangle based on the given position.

        Args:
            pos (tuple): The current position of the mouse.
        """
        sprite = self.editor.sprites[self.editor.current_sprite]
        grid_pos = sprite.get_grid_position(pos)
        if grid_pos:
            self.end_pos = grid_pos
            self.update_rect()
            print(f"Selection updated to: {self.end_pos}")

    def end_selection(self, pos):
        """
        End the current selection at the given position.

        Args:
            pos (tuple): The ending position of the selection rectangle.
        """
        sprite = self.editor.sprites[self.editor.current_sprite]
        grid_pos = sprite.get_grid_position(pos)
        if grid_pos:
            self.end_pos = grid_pos
            self.update_rect()
            self.active = True
            self.selecting = False
            print(f"Selection defined: {self.rect}")

    def update_rect(self):
        """
        Update the selection rectangle based on the start and end positions.
        """
        if self.start_pos and self.end_pos:
            x1, y1 = self.start_pos
            x2, y2 = self.end_pos
            left = min(x1, x2)
            top = min(y1, y2)
            width = abs(x2 - x1) + 1
            height = abs(y2 - y1) + 1
            self.rect = pygame.Rect(left, top, width, height)

    def draw(self, surface):
        """
        Draw the selection rectangle on a given surface.
        """
        # Draw selection rectangle while selecting (mouse down) or when selection is active
        if (self.selecting and self.start_pos and self.end_pos) or self.active:
            sprite = self.editor.sprites[self.editor.current_sprite]
            x0, y0 = sprite.position
            selection_surface = pygame.Surface((self.rect.width * config.EDITOR_PIXEL_SIZE, self.rect.height * config.EDITOR_PIXEL_SIZE), pygame.SRCALPHA)
            selection_surface.fill(config.SELECTION_FILL_COLOR)  # Semi-transparent blue
            pygame.draw.rect(selection_surface, config.BLUE, selection_surface.get_rect(), 2)
            surface.blit(selection_surface, (x0 + self.rect.x * config.EDITOR_PIXEL_SIZE, y0 + self.rect.y * config.EDITOR_PIXEL_SIZE))

    def get_selected_pixels(self):
        """ Get the pixels within the selection rectangle (coords relative to 32x32 grid). """
        sprite_editor = self.editor.sprites.get(self.editor.current_sprite)
        if not sprite_editor:
            return {}
            
        pixels = {}
        # self.rect is relative to the visual grid (0-31 range)
        # Native frame is also 32x32, so coords match directly
        for x in range(self.rect.width):
            for y in range(self.rect.height):
                grid_x = self.rect.x + x
                grid_y = self.rect.y + y
                # Check bounds against native resolution (32x32)
                if 0 <= grid_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= grid_y < config.NATIVE_SPRITE_RESOLUTION[1]:
                    color = sprite_editor.get_pixel_color((grid_x, grid_y))
                    if color is not None:
                        pixels[(x, y)] = color # Store relative to selection top-left
        return pixels


# Editor Class with Enhanced Features
class Editor:
    """
    The main controller class for the pixel art editor application.

    This class orchestrates the entire pixel art editing experience, managing
    sprite editors, color palettes, tool selection, and user interactions. It
    handles both monster sprite editing and background editing modes.

    Attributes:
        current_color (tuple): The currently selected color (R, G, B, A).
        current_monster_index (int): Index of the currently edited monster.
        drawing (bool): Flag indicating if drawing is currently active.
        eraser_mode (bool): Flag for eraser tool activation.
        fill_mode (bool): Flag for fill tool activation.
        current_sprite (str): Identifier of the currently active sprite ('front' or 'back').
        sprites (dict): Dictionary of SpriteEditor instances for each sprite type.
        palette (Palette): The color palette instance.
        brush_size (int): Current brush size for drawing.
        selection (SelectionTool): The selection tool instance.
        copy_buffer (dict): Buffer for copied pixel data.
        mode (str): Current editing mode ('draw' or 'select').
        backgrounds (list): List of available background images.
        edit_mode (str): Current editing mode ('monster' or 'background').
        editor_zoom (float): Current zoom level of the editor.

    Methods:
        handle_event(event: pygame.event.Event) -> bool
        draw_ui() -> None
        save_current() -> None
        load_session() -> None
        undo() -> None
        redo() -> None
        # ... (other methods)
    """

    def __init__(self):
        """
        Initialize a new Editor instance.
        """
        self.current_color = PALETTE[0]
        self.current_monster_index = 0
        self.drawing = False
        self.eraser_mode = False
        self.fill_mode = False
        self.current_sprite = 'front'
        self.sprites = {
            'front': SpriteEditor((50, 110), 'front', config.SPRITE_DIR),
            'back': SpriteEditor((575, 110), 'back', config.SPRITE_DIR)  # Adjusted position, pass SPRITE_DIR
        }
        self.palette = Palette((50, config.EDITOR_HEIGHT - 180))  # Adjusted position
        self.brush_size = 1  # Default brush size
        self.adjusting_brush = False  # Add this line
        self.selection = SelectionTool(self)
        self.copy_buffer = None
        self.paste_mode = False
        self.mode = 'draw'  # 'draw' or 'select'
        self.backgrounds = self.load_backgrounds()
        self.current_background_index = 0 if self.backgrounds else -1
        self.edit_mode = self.choose_edit_mode()
        self.editor_zoom = 1.0  # Initialize zoom level

        if self.edit_mode == 'background':
            self.canvas_rect = pygame.Rect(50, 100, config.DEFAULT_BACKGROUND_WIDTH, config.DEFAULT_BACKGROUND_HEIGHT)
            if self.backgrounds:
                self.current_background = self.backgrounds[0][1].copy()
            else:
                self.create_new_background()
        else:
            self.current_background = pygame.Surface((config.DEFAULT_BACKGROUND_WIDTH, config.DEFAULT_BACKGROUND_HEIGHT))
            self.current_background.fill(config.WHITE)

        # Load the first monster's art
        self.load_monster()

        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []

        # Create buttons after setting edit_mode
        self.buttons = self.create_buttons()

        # Add this line to create a font
        self.font = pygame.font.Font(config.DEFAULT_FONT, config.EDITOR_INFO_FONT_SIZE)

        self.brush_slider = pygame.Rect(50, config.EDITOR_HEIGHT - 40, 200, 20)  # Add this line

        # --- Reference Image Attributes ---
        self.reference_image_path = None
        self.reference_image = None # Original loaded surface
        self.scaled_reference_image = None # Scaled and alpha-applied surface for display
        self.reference_alpha = 128 # Default alpha (50% opaque)
        self.adjusting_alpha = False # Flag for slider interaction

        # Define slider rect (adjust position/size as needed)
        slider_x = 300 # Position next to brush slider for now
        slider_y = config.EDITOR_HEIGHT - 40
        slider_width = 150
        slider_height = 20
        self.ref_alpha_slider_rect = pygame.Rect(slider_x, slider_y, slider_width, slider_height)
        # Initial knob position reflects default alpha
        knob_slider_width = self.ref_alpha_slider_rect.width - 10 # Available track width
        initial_knob_x = self.ref_alpha_slider_rect.x + int((self.reference_alpha / 255) * knob_slider_width)
        self.ref_alpha_knob_rect = pygame.Rect(initial_knob_x, slider_y, 10, slider_height)

        # --- Dialog State ---
        self.dialog_mode = None # e.g., 'choose_edit_mode', 'choose_bg_action', 'save_bg', 'load_bg', 'color_picker', 'input_text'
        self.dialog_prompt = ""
        self.dialog_options = [] # List of tuples: (text, value) or Button objects
        self.dialog_callback = None # Function to call with the chosen value
        self.dialog_input_text = "" # For text input dialogs
        self.dialog_input_active = False # Is the text input active?
        self.dialog_input_rect = None # Rect for the input field
        self.dialog_input_max_length = 50 # Max chars for filename
        self.dialog_file_list = [] # List of files for file browser dialog
        self.dialog_file_scroll_offset = 0 # Scroll offset for file list
        self.dialog_selected_file_index = -1 # Index of selected file in list
        self.dialog_color_picker_hue = 0 # Hue for HSV color picker
        self.dialog_color_picker_sat = 1 # Saturation for HSV
        self.dialog_color_picker_val = 1 # Value for HSV
        self.dialog_color_picker_rects = {} # Rects for color picker elements
        # --- End Dialog State ---

    def choose_edit_mode(self):
        """
        Set up the dialog state to choose the editing mode (monster or background).
        The actual choice will be handled in the main loop via dialog state.
    
        Returns:
            None: Sets the initial dialog state instead of returning the mode directly.
        """
        self.dialog_mode = 'choose_edit_mode'
        self.dialog_prompt = "Choose Edit Mode:"

        # Calculate positions for vertically stacked buttons centered
        dialog_center_x = config.EDITOR_WIDTH // 2
        dialog_center_y = config.EDITOR_HEIGHT // 2
        button_width = 150
        button_height = 40
        button_padding = 10
        monster_button_y = dialog_center_y - button_height - button_padding // 2
        background_button_y = dialog_center_y + button_padding // 2
        button_x = dialog_center_x - button_width // 2

        self.dialog_options = [
            Button(pygame.Rect(button_x, monster_button_y, button_width, button_height), "Monster", value="monster"), # No action, store value
            Button(pygame.Rect(button_x, background_button_y, button_width, button_height), "Background", value="background"), # No action, store value
        ]
        self.dialog_callback = self._set_edit_mode_and_continue

        # Return a default mode temporarily until the dialog is resolved in the main loop
        # The rest of __init__ might depend on a valid edit_mode
        return "monster" # Default to monster initially

    def _set_edit_mode_and_continue(self, mode):
        """Callback after choosing edit mode."""
        print(f"Edit mode chosen: {mode}")
        self.edit_mode = mode
        if mode == 'background':
            # Now trigger the background action choice
            self.choose_background_action()
        else:
            # If monster mode, initialization is complete
            self.load_monster() # Ensure monster is loaded if chosen
            self.buttons = self.create_buttons() # Recreate buttons for the correct mode
            self.dialog_mode = None # Exit dialog

    def _handle_dialog_choice(self, value):
        """Internal handler for dialog button values or direct calls."""
        # If a value was passed (from button click), call the main callback
        if value is not None and self.dialog_callback:
            callback = self.dialog_callback
            # Important: Clear dialog state BEFORE calling callback
            # to prevent infinite loops if callback re-triggers a dialog
            # self.dialog_mode = None # Maybe not here? Callback should set None?
            callback(value)
        # Reset parts of dialog state AFTER callback potentially ran
        # self.dialog_options = [] # Callback might set these again
        # self.dialog_prompt = "" # Callback might set these again
        # self.dialog_callback = None # Callback might set this again

    def refocus_pygame_window(self):
        """
        Refocus the Pygame window - REMOVED as Tkinter is gone.
        """
        # pygame.display.iconify() - REMOVED
        # pygame.display.set_mode((config.EDITOR_WIDTH, config.EDITOR_HEIGHT)) - REMOVED
        # print("Editor window refocused.") - REMOVED
        pass # No longer needed

    def create_buttons(self):
        """
        Create the buttons for the editor UI.

        This method creates the buttons for the editor UI based on the current
        edit mode. It returns a list of Button instances.

        Returns:
            list: A list of Button instances.
        """
        buttons = []
        button_width = 100
        button_height = 30
        padding = 5
        start_x = config.EDITOR_WIDTH - button_width - padding
        start_y = 50

        # Determine the correct save action based on the edit mode
        save_action = None
        if self.edit_mode == 'monster':
            save_action = self.save_current_monster_sprites
        elif self.edit_mode == 'background':
            save_action = self.save_background
        else:
            # Default or error handling if mode is unexpected during init
            print(f"Warning: Unknown edit mode '{self.edit_mode}' during button creation. Save button disabled.")
            save_action = lambda: print("Save disabled.") # No-op action

        all_buttons = [
            ("Save", save_action), # Use the determined action
            ("Load", self.trigger_load_background_dialog if self.edit_mode == 'background' else lambda: print("Load BG only in BG mode")),
            ("Clear", self.clear_current),
            ("Color Picker", self.open_color_picker),
            ("Eraser", self.toggle_eraser),
            ("Fill", self.toggle_fill),
            ("Select", self.toggle_selection_mode),
            ("Copy", self.copy_selection),
            ("Paste", self.paste_selection),
            ("Mirror", self.mirror_selection),
            ("Rotate", self.rotate_selection),
            ("Undo", self.undo),
            ("Redo", self.redo),
            # Add Reference Image Buttons (only relevant in monster mode?)
            ("Load Ref Img", self.load_reference_image if self.edit_mode == 'monster' else lambda: print("Ref Img only in Monster mode")),
            ("Clear Ref Img", self.clear_reference_image if self.edit_mode == 'monster' else lambda: print("Ref Img only in Monster mode")),
        ]

        if self.edit_mode == 'monster':
            all_buttons += [
                ("Prev Monster", self.previous_monster),
                ("Next Monster", self.next_monster),
                ("Switch Sprite", self.switch_sprite),
            ]
        elif self.edit_mode == 'background':
            all_buttons += [
                ("Zoom In", self.zoom_in),
                ("Zoom Out", self.zoom_out),
                ("Brush +", self.increase_brush_size),
                ("Brush -", self.decrease_brush_size),
                ("Prev BG", self.previous_background),
                ("Next BG", self.next_background),
            ]

        for i, (text, action) in enumerate(all_buttons):
            rect = (start_x, start_y + i * (button_height + padding), button_width, button_height)
            buttons.append(Button(rect, text, action))

        return buttons

    def save_current_monster_sprites(self):
        """Saves both front and back sprites for the current monster."""
        try:
            # Ensure monsters list and index are valid
            if not hasattr(config, 'monsters') or not isinstance(config.monsters, list):
                print("Error: Monster data not loaded or invalid. Cannot save.")
                return
            if not (0 <= self.current_monster_index < len(config.monsters)):
                print(f"Error: current_monster_index {self.current_monster_index} out of range. Cannot save.")
                return

            monster_name = config.monsters[self.current_monster_index].get('name')
            if not monster_name:
                print(f"Error: Monster name not found at index {self.current_monster_index}. Cannot save.")
                return

            # Save both front and back sprites
            self.sprites['front'].save_sprite(monster_name)
            self.sprites['back'].save_sprite(monster_name)
            print(f"Saved sprites for {monster_name}")

        except Exception as e:
            print(f"An unexpected error occurred during save_current_monster_sprites: {e}")

    def clear_current(self):
        """Clears the currently active editing area (sprite or background)."""
        self.save_state() # Save state before clearing
        if self.edit_mode == 'monster':
            sprite = self.sprites.get(self.current_sprite)
            if sprite:
                sprite.frame.fill((*config.BLACK[:3], 0)) # Fill with transparent black
                print(f"Cleared {self.current_sprite} sprite.")
            else:
                print(f"Error: Could not find sprite editor for {self.current_sprite} to clear.")
        elif self.edit_mode == 'background':
            if self.current_background:
                # Assuming default background is white, fill with that
                # Or could use a different default clear color if needed
                self.current_background.fill((*config.WHITE, 255)) # Fill with opaque white
                print("Cleared current background.")
            else:
                print("Error: No current background loaded to clear.")
        else:
            print(f"Warning: Unknown edit mode '{self.edit_mode}' for clear operation.")

    def toggle_eraser(self):
        """Toggle eraser mode."""
        self.eraser_mode = not self.eraser_mode
        self.fill_mode = False
        self.paste_mode = False # Corrected indent
        if self.mode == 'select': # Corrected indent
            self.mode = 'draw' # Corrected indent
            self.selection.selecting = False # Corrected indent
            self.selection.active = False # Corrected indent
        print(f"Eraser mode: {self.eraser_mode}")

    def toggle_fill(self):
        """Toggle fill mode."""
        self.fill_mode = not self.fill_mode
        self.eraser_mode = False
        self.paste_mode = False
        if self.mode == 'select':
            self.mode = 'draw'
            self.selection.selecting = False
            self.selection.active = False
        print(f"Fill mode: {self.fill_mode}")

    def toggle_selection_mode(self):
        """Toggle selection mode."""
        if self.mode == 'select':
            self.mode = 'draw'
            self.selection.selecting = False
            self.selection.active = False
            print("Switched to Draw mode.")
        else:
            self.mode = 'select'
            self.selection.toggle() # Activate selection tool logic
            self.eraser_mode = False
            self.fill_mode = False
            self.paste_mode = False
            print("Switched to Select mode.")

    def copy_selection(self):
        """Copy the selected pixels to the buffer."""
        if self.mode == 'select' and self.selection.active:
            self.copy_buffer = self.selection.get_selected_pixels()
            print(f"Copied {len(self.copy_buffer)} pixels.")
        else:
            print("Copy failed: No active selection.")

    def paste_selection(self):
        """Activate paste mode with the buffered pixels."""
        if self.copy_buffer:
            self.paste_mode = True
            self.mode = 'draw' # Exit select mode implicitly
            self.selection.active = False
            self.eraser_mode = False
            self.fill_mode = False
            print("Paste mode activated. Click to place.")
        else:
            print("Paste failed: Copy buffer is empty.")

    def mirror_selection(self):
        """Mirror the selected pixels horizontally in-place."""
        if self.mode != 'select' or not self.selection.active:
            print("Mirror failed: Make an active selection first.")
            return

        sprite_editor = self.sprites.get(self.current_sprite)
        if not sprite_editor:
            print("Mirror failed: Active sprite editor not found.")
            return

        self.save_state() # Save state before modifying
        selection_rect = self.selection.rect

        # Create a subsurface referencing the selected area (no copy needed yet)
        try:
             original_area = sprite_editor.frame.subsurface(selection_rect)
             mirrored_area = pygame.transform.flip(original_area, True, False) # Flip horizontal
        except ValueError as e:
             print(f"Error creating subsurface for mirroring: {e}")
             self.undo_stack.pop() # Remove the state we just saved
             return

        # ---> ADD THIS LINE: Clear the original area first <---
        sprite_editor.frame.fill((*config.BLACK[:3], 0), selection_rect)

        # Blit mirrored surface back onto the main frame
        sprite_editor.frame.blit(mirrored_area, selection_rect.topleft)
        print("Selection mirrored.")
        # Keep selection active

    def rotate_selection(self):
        """Rotate the selected pixels 90 degrees clockwise in-place."""
        if self.mode != 'select' or not self.selection.active:
            print("Rotate failed: Make an active selection first.")
            return

        sprite_editor = self.sprites.get(self.current_sprite)
        if not sprite_editor:
            print("Rotate failed: Active sprite editor not found.")
            return

        self.save_state() # Save state before modifying
        selection_rect = self.selection.rect

        # Create a subsurface and rotate it
        try:
            original_area = sprite_editor.frame.subsurface(selection_rect)
            # Rotating might change dimensions, so handle carefully
            rotated_area = pygame.transform.rotate(original_area, -90) # Clockwise
        except ValueError as e:
            print(f"Error creating subsurface for rotation (maybe 0 size?): {e}")
            return

        # Clear original area ONLY IF rotation doesn't change size AND it fits
        # A simpler approach for now: Overwrite with rotated, centered.
        # Clear original area first
        sprite_editor.frame.fill((*config.BLACK[:3], 0), selection_rect)

        # Blit rotated surface back, centered in the original rect bounds
        blit_pos = rotated_area.get_rect(center=selection_rect.center)
        sprite_editor.frame.blit(rotated_area, blit_pos)
        print("Selection rotated 90 degrees clockwise.")
        # Keep selection active, rect might be slightly off if not square

    def zoom_in(self):
        """Zoom in on the background canvas."""
        # Placeholder - requires implementation
        print("Zoom In - Not Implemented")
        pass

    def zoom_out(self):
        """Zoom out on the background canvas."""
        # Placeholder - requires implementation
        print("Zoom Out - Not Implemented")
        pass

    def increase_brush_size(self):
        """Increase brush size."""
        if self.brush_size < config.MAX_BRUSH_SIZE:
            self.brush_size += 1
            print(f"Brush size: {self.brush_size}")
        else:
             print("Max brush size reached.")

    def decrease_brush_size(self):
        """Decrease brush size."""
        if self.brush_size > 1:
            self.brush_size -= 1
            print(f"Brush size: {self.brush_size}")
        else:
             print("Min brush size reached.")

    def previous_background(self):
        """Switch to the previous background image."""
        if self.edit_mode == 'background' and self.backgrounds:
            if self.current_background_index > 0:
                self.current_background_index -= 1
                self.current_background = self.backgrounds[self.current_background_index][1].copy()
                self.undo_stack = [] # Reset undo/redo for new image
                self.redo_stack = []
                print(f"Switched to previous background: {self.backgrounds[self.current_background_index][0]}")
            else:
                print("Already at the first background.")
        else:
             print("Previous background only available in background mode with existing backgrounds.")

    def next_background(self):
        """Switch to the next background image."""
        if self.edit_mode == 'background' and self.backgrounds:
            if self.current_background_index < len(self.backgrounds) - 1:
                self.current_background_index += 1
                self.current_background = self.backgrounds[self.current_background_index][1].copy()
                self.undo_stack = [] # Reset undo/redo for new image
                self.redo_stack = []
                print(f"Switched to next background: {self.backgrounds[self.current_background_index][0]}")
            else:
                print("Already at the last background.")
        else:
             print("Next background only available in background mode with existing backgrounds.")

    def open_color_picker(self):
        """Open the system's native color picker dialog using Tkinter."""
        if root is None:
            print("Tkinter failed to initialize. Cannot open native color picker.")
            # Fallback: Trigger the old Pygame color picker maybe?
            # self._open_pygame_color_picker() # Need to rename old method
            return

        # Convert current color to Tkinter format (hex string)
        initial_color_hex = "#{:02x}{:02x}{:02x}".format(*self.current_color[:3])

        # Open the dialog
        try:
             chosen_color = colorchooser.askcolor(color=initial_color_hex, title="Select Color")
        except tk.TclError as e:
             print(f"Error opening native color picker: {e}")
             chosen_color = None

        # Bring Pygame window back to focus (experimental)
        # self.refocus_pygame_window() # Might be needed

        if chosen_color and chosen_color[1] is not None: # Check if a color was chosen (result is tuple: ((r,g,b), hex)) or (None, None)
            rgb, _ = chosen_color
            new_color_rgba = (int(rgb[0]), int(rgb[1]), int(rgb[2]), 255) # Add full alpha
            self.select_color(new_color_rgba)
            print(f"Color selected via native picker: {new_color_rgba}")
        else:
            print("Color selection cancelled or failed.")

        # Clear any lingering dialog state from Pygame picker (if we add fallback)
        # self.dialog_mode = None 

    def _get_current_picker_color(self):
        # ... This method is now only relevant for a potential Pygame fallback ...
        pass

    def _color_picker_callback(self, color):
        # ... This method is now only relevant for a potential Pygame fallback ...
        pass

    def select_color(self, color):
        """
        Select a color from the palette.

        This method sets the currently selected color based on the provided color
        tuple. It also deactivates the eraser and fill modes.

        Args:
            color (tuple): The RGBA color tuple to select.
        """
        if color is not None:
            self.current_color = color
            self.eraser_mode = False
            self.fill_mode = False
            # Disable paste mode and select mode when selecting a color
            self.paste_mode = False
            if self.mode == 'select':
                self.mode = 'draw'
                self.selection.selecting = False
                self.selection.active = False
            print(f"Selected color: {color}")

    def load_backgrounds(self):
        """
        Load available background images from the 'backgrounds' directory.

        This method scans the 'backgrounds' directory for PNG files and attempts
        to load them as background images. It returns a list of tuples, where each
        tuple contains the filename and the corresponding Pygame Surface.

        Returns:
            list: A list of tuples, each containing a filename and a Pygame Surface.
        """
        backgrounds = []
        # config should ensure BACKGROUND_DIR exists
        # if not os.path.exists(config.BACKGROUND_DIR):
        #     os.makedirs(config.BACKGROUND_DIR)
        for filename in os.listdir(config.BACKGROUND_DIR):
            if filename.endswith('.png'):
                path = os.path.join(config.BACKGROUND_DIR, filename)
                try:
                    bg = pygame.image.load(path).convert_alpha()
                    backgrounds.append((filename, bg))
                except pygame.error as e:
                    print(f"Failed to load background {filename}: {e}")
        return backgrounds

    def show_edit_mode_dialog(self):
        """
        Display a dialog to choose the editing mode - REMOVED / Replaced by dialog state.
        """
        # REMOVED Tkinter dialog code
        print("DEBUG: show_edit_mode_dialog was called but is replaced by dialog state.")
        return "monster" # Return default, logic moved to choose_edit_mode

    def show_background_action_dialog(self):
        """
        Display a dialog to choose the background action - REMOVED / Replaced by dialog state.
        """
        # REMOVED Tkinter dialog code
        print("DEBUG: show_background_action_dialog was called but is replaced by dialog state.")
        return "new" # Return default, logic moved to choose_background_action

    def choose_background_action(self):
        """
        Handle background-specific actions (new or edit) using dialog state.
        """
        if not self.backgrounds:
            print("No existing backgrounds. Creating a new one.")
            # Trigger the 'new background' dialog/flow directly
            self.create_new_background() # This will need modification for Pygame UI
            self.dialog_mode = None # Assume create_new_background handles its own dialog state or finishes
        else:
            self.dialog_mode = 'choose_bg_action'
            self.dialog_prompt = "Choose Background Action:"
            self.dialog_options = [
                Button(pygame.Rect(0, 0, 150, 40), "New", action=lambda: self._handle_dialog_choice("new")),
                Button(pygame.Rect(0, 0, 150, 40), "Edit Existing", action=lambda: self._handle_dialog_choice("edit")),
            ]
            self.dialog_callback = self._handle_background_action_choice

    def _handle_background_action_choice(self, action):
        """Callback after choosing background action."""
        print(f"Background action chosen: {action}")
        # Corrected Indentation:
        if action == 'new':
            self.create_new_background() # Needs modification for Pygame UI
            # Assuming create_new_background completes or sets its own dialog state
            self.dialog_mode = None
        elif action == 'edit' and self.backgrounds:
            self.current_background_index = 0
            self.current_background = self.backgrounds[self.current_background_index][1].copy()
            print(f"Editing background: {self.backgrounds[self.current_background_index][0]}")
            self.buttons = self.create_buttons() # Recreate buttons for the correct mode
            self.dialog_mode = None # Exit dialog
        else:
            print("Invalid action or no backgrounds to edit. Creating new.")
            self.create_new_background() # Needs modification for Pygame UI
            self.dialog_mode = None

    def create_new_background(self):
        """
        Create a new background image.
        Uses a Pygame input dialog for the filename.
        """
        # Trigger the input dialog
        self.dialog_mode = 'input_text'
        self.dialog_prompt = "Enter filename for new background (.png):"
        self.dialog_input_text = "new_background.png" # Default text
        self.dialog_input_active = True
        self.dialog_options = [
            Button(pygame.Rect(0,0, 100, 40), "Save", action=lambda: self._handle_dialog_choice(self.dialog_input_text)),
            Button(pygame.Rect(0,0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
        ]
        self.dialog_callback = self._create_new_background_callback

    def _create_new_background_callback(self, filename):
        """Callback after getting filename for new background."""
        self.dialog_mode = None # Clear dialog state first
        if filename:
            if not filename.endswith('.png'):
                filename += '.png'
            # Ensure filename is just the base name, save to BACKGROUND_DIR
            base_filename = os.path.basename(filename)
            full_path = os.path.join(config.BACKGROUND_DIR, base_filename)

            self.current_background = pygame.Surface((config.DEFAULT_BACKGROUND_WIDTH, config.DEFAULT_BACKGROUND_HEIGHT), pygame.SRCALPHA)
            self.current_background.fill((*config.WHITE, 255))  # Set to white with full opacity
            try:
                pygame.image.save(self.current_background, full_path)
                print(f"Saved background as {full_path}")
            except pygame.error as e:
                 print(f"Error saving new background {full_path}: {e}")
                 # Handle error, maybe show message? For now, just print.

            # Reload backgrounds to include the new one
            self.backgrounds = self.load_backgrounds()
            self.current_background_index = next(
                (i for i, (name, _) in enumerate(self.backgrounds) if name == base_filename),
                -1 # Should find it if save succeeded
            )
            # Ensure buttons are created/updated for the correct mode
            self.buttons = self.create_buttons()
        else:
            print("New background creation cancelled.")
            # If cancellation happened during initial setup, decide what to do.
            # Maybe default to the first existing background or quit?
            # For now, just print. If edit_mode wasn't fully set, it might be unstable.
            if self.edit_mode == 'background' and self.current_background_index == -1:
                 print("Warning: No background loaded after cancellation.")
                 # Optionally load a default or the first available one
                 if self.backgrounds:
                      self.current_background_index = 0
                      self.current_background = self.backgrounds[0][1].copy()
                      self.buttons = self.create_buttons()
                 else:
                      # Handle case with absolutely no backgrounds - maybe quit or show error message
                      pass

    def save_background(self, filename=None):
        """
        Save the current background image.
        Uses Pygame input dialog if no filename provided or saving new.
        """
        current_filename = None
        # Corrected Indentation:
        if self.current_background_index >= 0 and self.backgrounds:
            current_filename = self.backgrounds[self.current_background_index][0]

        if not filename:
            # Use current filename if available, otherwise prompt
            filename_to_save = current_filename
            if not filename_to_save:
                 # Trigger input dialog for saving a potentially new file
                 self.dialog_mode = 'input_text'
                 self.dialog_prompt = "Enter filename to save background (.png):"
                 self.dialog_input_text = "background.png"
                 self.dialog_input_active = True
                 self.dialog_options = [
                     Button(pygame.Rect(0,0, 100, 40), "Save", action=lambda: self._handle_dialog_choice(self.dialog_input_text)),
                     Button(pygame.Rect(0,0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
                 ]
                 self.dialog_callback = self._save_background_callback
                 return # Exit function, wait for dialog callback
            else:
                 # If we have a current filename, save directly without dialog
                 self._save_background_callback(filename_to_save)
        else:
             # If a specific filename is passed (e.g., for "Save As"), use it
             # This might also need a dialog in a full implementation, but for now save directly
             print(f"Warning: Direct saving to specified filename '{filename}' without dialog.")
             self._save_background_callback(filename)

    def _save_background_callback(self, filename):
        """Callback after getting filename for saving background."""
        self.dialog_mode = None # Clear dialog state
        if filename:
            if not filename.endswith('.png'):
                filename += '.png'
            # Ensure filename is just the base name, save to BACKGROUND_DIR
            base_filename = os.path.basename(filename)
            full_path = os.path.join(config.BACKGROUND_DIR, base_filename)
            try:
                 pygame.image.save(self.current_background, full_path)
                 print(f"Saved background as {full_path}")
            except pygame.error as e:
                 print(f"Error saving background {full_path}: {e}")
                 return # Don't update index if save failed
                 
            # Reload and find index only after successful save
            self.backgrounds = self.load_backgrounds()
            self.current_background_index = next(
                (i for i, (name, _) in enumerate(self.backgrounds) if name == base_filename),
                -1 # Should be found
            )
            # Update buttons if needed (though likely already correct)
            self.buttons = self.create_buttons()
        else:
            print("Background save cancelled.")

    def load_monster(self):
        """
        Load the current monster's sprites.

        This method loads the sprites for the currently selected monster. It updates
        the sprite frames and prints a status message.
        """
        try:
            # Ensure monsters list and index are valid
            if not hasattr(config, 'monsters') or not isinstance(config.monsters, list):
                print("Error: Monster data not loaded or invalid.")
                return
            if not (0 <= self.current_monster_index < len(config.monsters)):
                print(f"Error: current_monster_index {self.current_monster_index} out of range.")
                return

            monster_name = config.monsters[self.current_monster_index]['name']
            # Corrected Indentation:
            for sprite in self.sprites.values():
                sprite.load_sprite(monster_name) # Pass monster_name here
            print(f"Loaded monster: {monster_name}")
        except KeyError:
             print(f"Error: Monster data missing 'name' key at index {self.current_monster_index}.")
        except Exception as e:
             print(f"An unexpected error occurred during load_monster: {e}")

    def switch_sprite(self):
        """
        Switch between the front and back sprites.

        This method toggles between the front and back sprites for the current
        monster. It updates the current sprite and deactivates the selection.
        """
        self.current_sprite = 'back' if self.current_sprite == 'front' else 'front'
        print(f"Switched to sprite: {self.current_sprite}")
        self.selection.active = False  # Deactivate selection on sprite switch

    def previous_monster(self):
        """
        Switch to the previous monster in the list.

        This method decrements the current monster index and loads the previous
        monster's sprites. It prints a status message.
        """
        if self.current_monster_index > 0:
            self.current_monster_index -= 1
            self.load_monster()
            print(f"Switched to previous monster: {config.monsters[self.current_monster_index]['name']}")
        else:
            print("Already at the first monster.")

    def next_monster(self):
        """
        Switch to the next monster in the list.

        This method increments the current monster index and loads the next
        monster's sprites. It prints a status message.
        """
        # Ensure monsters list is loaded and valid
        if not hasattr(config, 'monsters') or not isinstance(config.monsters, list):
            print("Error: Monster data not loaded or invalid. Cannot switch.")
            return
        
        if self.current_monster_index < len(config.monsters) - 1:
            self.current_monster_index += 1
            self.load_monster()
            print(f"Switched to next monster: {config.monsters[self.current_monster_index].get('name', 'Unknown')}")
        else:
            print("Already at the last monster.")

    def _get_background_files(self):
        """Helper to get list of .png files in background directory."""
        try:
            return [f for f in os.listdir(config.BACKGROUND_DIR) if f.endswith('.png')]
        except FileNotFoundError:
            print(f"Warning: Background directory {config.BACKGROUND_DIR} not found.")
            return []

    def trigger_load_background_dialog(self):
        """Initiates the dialog for loading a background file."""
        # Ensure we are in background mode, otherwise this button shouldn't be active/visible
        if self.edit_mode != 'background':
            print("Load background only available in background edit mode.")
            return

        self.dialog_mode = 'load_bg'
        self.dialog_prompt = "Select Background to Load:"
        self.dialog_file_list = self._get_background_files() # Get the list of files
        self.dialog_file_scroll_offset = 0
        self.dialog_selected_file_index = -1

        # Define buttons for the dialog (Load and Cancel)
        # Actions will call _handle_dialog_choice with filename or None
        self.dialog_options = [
            # Buttons are positioned dynamically in draw_dialog
            Button(pygame.Rect(0, 0, 100, 40), "Load", action=lambda: self._handle_dialog_choice(
                self.dialog_file_list[self.dialog_selected_file_index] if 0 <= self.dialog_selected_file_index < len(self.dialog_file_list) else None
            )),
            Button(pygame.Rect(0, 0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
        ]
        self.dialog_callback = self._load_selected_background_callback

    def _load_selected_background_callback(self, filename):
        """Callback after selecting a background file to load."""
        self.dialog_mode = None # Clear dialog state
        if filename:
            full_path = os.path.join(config.BACKGROUND_DIR, filename)
            try:
                loaded_bg = pygame.image.load(full_path).convert_alpha()
                # Find the index in the self.backgrounds list (which contains Surfaces)
                found_index = -1
                for i, (name, _) in enumerate(self.backgrounds):
                    if name == filename:
                        found_index = i
                        break
                
                if found_index != -1:
                    self.current_background_index = found_index
                    self.current_background = self.backgrounds[found_index][1].copy() # Load from pre-loaded list
                    print(f"Loaded background: {filename}")
                else:
                    # If not found in pre-loaded list (shouldn't happen if list is up-to-date)
                    # Load it directly and add it (or maybe just load directly?)
                    self.current_background = loaded_bg
                    # Add to list if desired, or just use the directly loaded one
                    # For simplicity, let's just use the loaded one and reset index
                    self.backgrounds.append((filename, loaded_bg))
                    self.current_background_index = len(self.backgrounds) - 1
                    print(f"Loaded background {filename} directly.")
                
                # Reset undo/redo for the new background
                self.undo_stack = []
                self.redo_stack = []
                # Potentially save initial state for undo here if desired

            except pygame.error as e:
                print(f"Error loading background {full_path}: {e}")
            except FileNotFoundError:
                print(f"Error: Background file {full_path} not found.")
        else:
            print("Background load cancelled.")

    def save_state(self):
        """Save the current state of the active canvas to the undo stack."""
        # Limit stack size if desired (optional)
        # if len(self.undo_stack) > MAX_UNDO_STEPS:
        #     self.undo_stack.pop(0)

        current_state = None
        if self.edit_mode == 'monster':
            sprite = self.sprites.get(self.current_sprite)
            if sprite:
                # Store a copy of the frame and which sprite it belongs to
                current_state = ('monster', self.current_sprite, sprite.frame.copy())
        elif self.edit_mode == 'background':
            if self.current_background:
                current_state = ('background', self.current_background_index, self.current_background.copy())

        if current_state:
            self.undo_stack.append(current_state)
            self.redo_stack.clear() # Clear redo stack on new action
            # print(f"State saved. Undo stack size: {len(self.undo_stack)}") # Debug
        # else: # Debug
            # print("Save state failed: No valid state to save.")

    def undo(self):
        """Revert to the previous state from the undo stack."""
        if not self.undo_stack:
            print("Nothing to undo.")
            return

        # Get the state to restore
        state_to_restore = self.undo_stack.pop()
        state_type, state_id, state_surface = state_to_restore

        # Save current state to redo stack BEFORE restoring
        current_state_for_redo = None
        if self.edit_mode == 'monster':
            sprite = self.sprites.get(self.current_sprite)
            if sprite:
                 current_state_for_redo = ('monster', self.current_sprite, sprite.frame.copy())
        elif self.edit_mode == 'background':
             if self.current_background:
                  current_state_for_redo = ('background', self.current_background_index, self.current_background.copy())
        
        if current_state_for_redo:
             self.redo_stack.append(current_state_for_redo)

        # Restore the popped state
        if state_type == 'monster':
            sprite = self.sprites.get(state_id)
            if sprite:
                sprite.frame = state_surface.copy() # Use copy to avoid issues
                # Ensure the editor is focused on the restored sprite if it changed
                self.current_sprite = state_id 
                self.edit_mode = 'monster' # Ensure mode is correct
                print(f"Undid action for sprite: {state_id}")
            else: # Corrected indent for this else
                 print(f"Undo failed: Could not find sprite editor '{state_id}' to restore state.")
                 # Put the state back on the undo stack? Or discard?
                 self.undo_stack.append(state_to_restore) # Re-add for now
                 # Check if redo_stack is not empty before popping
                 if self.redo_stack: self.redo_stack.pop() # Remove the state we just added
        elif state_type == 'background':
            self.current_background = state_surface.copy() # Use copy
            self.current_background_index = state_id # Restore index too
            self.edit_mode = 'background' # Ensure mode is correct
            print(f"Undid action for background index: {state_id}")
        else:
            print("Undo failed: Unknown state type in stack.")
            self.undo_stack.append(state_to_restore) # Re-add
            if self.redo_stack: self.redo_stack.pop() # Remove corresponding redo

        # Update buttons if mode changed
        self.buttons = self.create_buttons()

    def redo(self):
        """Reapply the last undone action from the redo stack."""
        if not self.redo_stack:
            print("Nothing to redo.")
            return

        # Get the state to restore from redo stack
        state_to_restore = self.redo_stack.pop()
        state_type, state_id, state_surface = state_to_restore

        # Save current state to undo stack BEFORE restoring
        current_state_for_undo = None
        if self.edit_mode == 'monster':
             sprite = self.sprites.get(self.current_sprite)
             if sprite:
                  current_state_for_undo = ('monster', self.current_sprite, sprite.frame.copy())
        elif self.edit_mode == 'background':
             if self.current_background:
                  current_state_for_undo = ('background', self.current_background_index, self.current_background.copy())

        if current_state_for_undo:
             self.undo_stack.append(current_state_for_undo)

        # Restore the popped state from redo stack
        if state_type == 'monster':
            sprite = self.sprites.get(state_id)
            if sprite:
                sprite.frame = state_surface.copy()
                self.current_sprite = state_id
                self.edit_mode = 'monster'
                print(f"Redid action for sprite: {state_id}")
            else:
                 print(f"Redo failed: Could not find sprite editor '{state_id}' to restore state.")
                 self.redo_stack.append(state_to_restore) # Re-add
                 self.undo_stack.pop() # Remove corresponding undo
        elif state_type == 'background':
            self.current_background = state_surface.copy()
            self.current_background_index = state_id
            self.edit_mode = 'background'
            print(f"Redid action for background index: {state_id}")
        else:
            print("Redo failed: Unknown state type in stack.")
            self.redo_stack.append(state_to_restore) # Re-add
            if self.undo_stack: self.undo_stack.pop() # Remove corresponding undo

        # Update buttons if mode changed
        self.buttons = self.create_buttons()

    def _get_sprite_editor_at_pos(self, pos):
        """Return the SpriteEditor instance at the given screen position, or None."""
        if self.edit_mode == 'monster':
            for name, sprite_editor in self.sprites.items():
                editor_rect = pygame.Rect(sprite_editor.position, (sprite_editor.display_width, sprite_editor.display_height))
                if editor_rect.collidepoint(pos):
                    return sprite_editor
        return None

    def _handle_canvas_click(self, pos):
        """Handles drawing, erasing, or filling based on current mode when canvas is clicked/dragged."""
        sprite_editor = self._get_sprite_editor_at_pos(pos)
        if not sprite_editor:
            # TODO: Handle background canvas clicks
            if self.edit_mode == 'background' and self.canvas_rect.collidepoint(pos):
                print("Background canvas click - TBD")
            return

        grid_pos = sprite_editor.get_grid_position(pos)
        if not grid_pos:
            return

        if self.fill_mode:
            # Trigger fill operation (needs implementation)
            target_color = sprite_editor.get_pixel_color(grid_pos)
            if target_color != self.current_color: # Avoid filling with same color
                self.flood_fill(sprite_editor, grid_pos, self.current_color)
            self.fill_mode = False # Typically fill is a one-shot action
        elif self.paste_mode and self.copy_buffer:
            # Paste the buffer at the clicked location
            self.apply_paste(sprite_editor, grid_pos)
            # Keep paste mode active until another tool/color is selected
            # self.paste_mode = False 
        else:
            # Regular draw/erase
            color = (*config.BLACK[:3], 0) if self.eraser_mode else self.current_color
            # Apply brush size
            half_brush = (self.brush_size - 1) // 2
            for dy in range(-half_brush, half_brush + 1):
                for dx in range(-half_brush, half_brush + 1):
                    # Optional: Check for circular brush shape
                    # if dx*dx + dy*dy <= half_brush*half_brush:
                    draw_x = grid_pos[0] + dx
                    draw_y = grid_pos[1] + dy
                    # Ensure drawing stays within bounds
                    if 0 <= draw_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= draw_y < config.NATIVE_SPRITE_RESOLUTION[1]:
                        sprite_editor.draw_pixel((draw_x, draw_y), color)

    def flood_fill(self, sprite_editor, start_pos, fill_color):
        """Perform flood fill on the sprite editor's frame."""
        native_res = config.NATIVE_SPRITE_RESOLUTION
        target_color = sprite_editor.get_pixel_color(start_pos)

        if target_color == fill_color:
            return # No need to fill

        stack = [start_pos]
        visited = {start_pos}

        while stack:
            x, y = stack.pop()
            if sprite_editor.get_pixel_color((x, y)) == target_color:
                sprite_editor.draw_pixel((x, y), fill_color)
                # Check neighbors
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < native_res[0] and 0 <= ny < native_res[1]:
                        neighbor_pos = (nx, ny)
                        if neighbor_pos not in visited:
                             stack.append(neighbor_pos)
                             visited.add(neighbor_pos)
        print("Fill complete.")
        # Don't forget to save state *before* calling fill if you want undo
        # self.save_state() should be called before flood_fill is invoked

    def apply_paste(self, sprite_editor, top_left_grid_pos):
        """Pastes the copy_buffer onto the sprite_editor frame."""
        if not self.copy_buffer:
            return

        start_x, start_y = top_left_grid_pos
        for (rel_x, rel_y), color in self.copy_buffer.items():
            abs_x = start_x + rel_x
            abs_y = start_y + rel_y
            # Check bounds before attempting to draw
            if 0 <= abs_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= abs_y < config.NATIVE_SPRITE_RESOLUTION[1]:
                # Only paste non-transparent pixels.
                if color[3] > 0:
                    sprite_editor.draw_pixel((abs_x, abs_y), color)

    def handle_event(self, event):
        """Process a single Pygame event."""
        # Handle dialog events first
        if self.dialog_mode:
            # Let dialog buttons handle their own clicks via their action lambda
            # Needs modification: Check button value, not action
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                 for option in self.dialog_options:
                      # Check if it's a button AND it was clicked
                      if isinstance(option, Button) and option.rect.collidepoint(event.pos):
                           # Use button's stored value to call the dialog choice handler
                           if option.value is not None:
                                self._handle_dialog_choice(option.value)
                           # If button has direct action AND value, maybe prioritize action?
                           # elif option.action:
                           #      option.action()
                           return True # Handled by dialog button
            # Add specific handling for color picker drags, text input etc. here
            # e.g., if self.dialog_mode == 'color_picker' and event.type == MOUSEMOTION:
            # handle_color_picker_drag(event.pos)

            # Handle KEYDOWN specifically for dialogs that need it
            elif event.type == pygame.KEYDOWN:
                 if self.dialog_mode == 'input_text' and self.dialog_input_active:
                      if event.key == pygame.K_RETURN:
                           self._handle_dialog_choice("save") # Pass 'save' value
                      elif event.key == pygame.K_BACKSPACE:
                           self.dialog_input_text = self.dialog_input_text[:-1]
                      elif event.key == pygame.K_ESCAPE:
                           self._handle_dialog_choice("cancel") # Pass 'cancel' value
                      elif len(self.dialog_input_text) < self.dialog_input_max_length:
                           self.dialog_input_text += event.unicode # Add typed character
                      return True # Consume key event for text input
                 # Add key handling for file list navigation (up/down, enter)
                 elif self.dialog_mode == 'load_bg': # Example for file list
                      if event.key == pygame.K_UP:
                           # Move selection up, handle scrolling
                           if self.dialog_selected_file_index > 0:
                                self.dialog_selected_file_index -= 1
                           # Add scroll logic here if needed
                           return True
                      elif event.key == pygame.K_DOWN:
                           # Move selection down, handle scrolling
                           if self.dialog_selected_file_index < len(self.dialog_file_list) - 1:
                                self.dialog_selected_file_index += 1
                           # Add scroll logic here if needed
                           return True
                      elif event.key == pygame.K_RETURN:
                           # Trigger Load action if a file is selected
                           if self.dialog_selected_file_index != -1:
                                self._handle_dialog_choice("load")
                           return True
                      elif event.key == pygame.K_ESCAPE:
                           self._handle_dialog_choice("cancel")
                           return True
                 # Add key handling for other dialogs if needed (e.g., Escape to cancel)
                 elif event.key == pygame.K_ESCAPE:
                     # Generic cancel for other dialogs? Check type first.
                     if self.dialog_mode in ['choose_edit_mode', 'choose_bg_action']:
                          self._handle_dialog_choice(None) # Or a specific cancel value?
                     return True

            return True # Consume unhandled events while dialog is open

        # --- Normal Event Handling (No Dialog Active) ---
        if event.type == pygame.QUIT:
             return False # Allows the main loop to catch QUIT

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left click
                # 0. Check Alpha Slider Click/Drag Start FIRST <<<<<< MOVED & UPDATED
                if self.ref_alpha_slider_rect.collidepoint(event.pos):
                    self.adjusting_alpha = True
                    # Update alpha based on click position immediately
                    click_x_relative = event.pos[0] - self.ref_alpha_slider_rect.x
                    # Calculate effective width (slider width minus knob width) for ratio calculation
                    slider_width_effective = self.ref_alpha_slider_rect.width - self.ref_alpha_knob_rect.width
                    if slider_width_effective <= 0: slider_width_effective = 1 # Avoid division by zero
                    new_alpha = (click_x_relative / slider_width_effective) * 255
                    self.set_reference_alpha(new_alpha)
                    # Update knob position visually based on relative click
                    # We adjust the knob's center based on the relative click pos within the slider track
                    self.ref_alpha_knob_rect.centerx = self.ref_alpha_slider_rect.x + click_x_relative
                    # Clamp knob position to slider track bounds
                    self.ref_alpha_knob_rect.left = max(self.ref_alpha_slider_rect.left, self.ref_alpha_knob_rect.left)
                    self.ref_alpha_knob_rect.right = min(self.ref_alpha_slider_rect.right - self.ref_alpha_knob_rect.width, self.ref_alpha_knob_rect.left) + self.ref_alpha_knob_rect.width

                    return True # Event handled by slider

                # 1. Check UI Buttons (Existing)
                for button in self.buttons:
                    if button.is_clicked(event):
                        if button.action:
                            button.action() # Call the button's assigned method
                        return True # Event handled by UI button

                # 2. Check Palette Click (Existing)
                palette_rect = pygame.Rect(self.palette.position[0], self.palette.position[1],
                                         config.PALETTE_COLS * (self.palette.block_size + self.palette.padding),
                                           config.PALETTE_ROWS * (self.palette.block_size + self.palette.padding) + 40) # Include scroll area roughly
                if palette_rect.collidepoint(event.pos):
                    self.palette.handle_click(event.pos)
                    return True # Event handled by palette

                # 3. Check Canvas Click (Existing)
                clicked_sprite_editor = self._get_sprite_editor_at_pos(event.pos)
                is_bg_click = self.edit_mode == 'background' and self.canvas_rect.collidepoint(event.pos)

                if clicked_sprite_editor or is_bg_click:
                    self.save_state() # Save state BEFORE the action
                    if self.mode == 'select':
                        if clicked_sprite_editor: # Selection only on sprites for now
                             self.selection.start(event.pos)
                        # else: ignore select start on background?
                    else: # Draw, erase, fill, paste modes
                        self.drawing = True
                        self._handle_canvas_click(event.pos) # Apply first click
                    return True # Event handled by canvas click

            # Handle Right-click, Middle-click, etc. (Existing)
            # ...

        elif event.type == pygame.MOUSEMOTION:
            # Handle alpha slider drag FIRST <<<<<< MOVED & UPDATED
            if self.adjusting_alpha and (event.buttons[0] == 1): # Check if left button is held
                move_x_relative = event.pos[0] - self.ref_alpha_slider_rect.x
                slider_width_effective = self.ref_alpha_slider_rect.width - self.ref_alpha_knob_rect.width
                if slider_width_effective <= 0: slider_width_effective = 1
                new_alpha = (move_x_relative / slider_width_effective) * 255
                self.set_reference_alpha(new_alpha)
                # Update knob position visually
                self.ref_alpha_knob_rect.centerx = self.ref_alpha_slider_rect.x + move_x_relative
                 # Clamp knob position to slider track bounds
                self.ref_alpha_knob_rect.left = max(self.ref_alpha_slider_rect.left, self.ref_alpha_knob_rect.left)
                self.ref_alpha_knob_rect.right = min(self.ref_alpha_slider_rect.right - self.ref_alpha_knob_rect.width, self.ref_alpha_knob_rect.left) + self.ref_alpha_knob_rect.width

                return True # Event handled by slider drag

            # Handle drawing/selection drag (Existing)
            if self.drawing and (event.buttons[0] == 1):
                self._handle_canvas_click(event.pos)
                return True
            elif self.selection.selecting and (event.buttons[0] == 1):
                 self.selection.update(event.pos)
                 return True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1: # Left button release
                 # Stop adjusting alpha slider FIRST <<<<<< MOVED & UPDATED
                if self.adjusting_alpha:
                    self.adjusting_alpha = False
                    return True # Event handled

                # Handle drawing/selection end (Existing)
                if self.drawing:
                    self.drawing = False
                    return True
                elif self.selection.selecting:
                    self.selection.end_selection(event.pos)
                    return True

        # Handle KEYDOWN for shortcuts etc. (Existing)
        elif event.type == pygame.KEYDOWN:
            # Example: Ctrl+Z for undo, Ctrl+Y for redo
            if event.mod & pygame.KMOD_META or event.mod & pygame.KMOD_CTRL: # Cmd on Mac, Ctrl elsewhere
                if event.key == pygame.K_z:
                    self.undo()
                    return True
                if event.key == pygame.K_y:
                    self.redo()
                    return True
                if event.key == pygame.K_c and self.mode == 'select':
                     self.copy_selection()
                     return True
                if event.key == pygame.K_v:
                     self.paste_selection()
                     return True
            # Add other key bindings

        return False # Event not handled by this function

    # Add the new methods here or elsewhere within the class
    def load_reference_image(self):
        """Opens a dialog to select a reference image, loads and scales it."""
        if root is None:
            print("Tkinter failed to initialize. Cannot open file dialog.")
            return

        try:
            file_path = filedialog.askopenfilename(
                title="Select Reference Image",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")]
            )
        except tk.TclError as e:
            print(f"Error opening file dialog: {e}")
            file_path = None

        # Bring Pygame window back to focus might be needed here too if dialog issues persist

        if file_path and os.path.exists(file_path):
            try:
                self.reference_image = pygame.image.load(file_path).convert_alpha()
                self.reference_image_path = file_path
                print(f"Loaded reference image: {file_path}")
                self._scale_reference_image() # Scale and position the image
                self.apply_reference_alpha() # Apply the current alpha (or default if just loaded)
            except pygame.error as e:
                print(f"Error loading image {file_path}: {e}")
                self.reference_image = None
                self.reference_image_path = None
                self.scaled_reference_image = None
            except Exception as e: # Catch other potential errors during loading/scaling
                print(f"An unexpected error occurred during reference image loading: {e}")
                self.reference_image = None
                self.reference_image_path = None
                self.scaled_reference_image = None
        else:
            print("Reference image loading cancelled or file not found.")

    def _scale_reference_image(self):
        """Scales the loaded reference image using Aspect Fit (Option B)
           and prepares it for display behind the active editor."""
        if not self.reference_image:
            self.scaled_reference_image = None
            return

        # Target dimensions are the display size of the sprite editor grid
        # Use the 'front' sprite editor dimensions as reference (assuming both are same size)
        sprite_editor = self.sprites.get('front') # Get dimensions from one editor
        if not sprite_editor:
            print("Error: Cannot scale reference image, sprite editor 'front' not found.")
            self.scaled_reference_image = None
            return

        canvas_w = sprite_editor.display_width
        canvas_h = sprite_editor.display_height
        orig_w, orig_h = self.reference_image.get_size()

        if orig_w == 0 or orig_h == 0:
             print("Warning: Reference image has zero dimension. Cannot scale.")
             self.scaled_reference_image = None
             return

        # Calculate aspect fit scale
        scale_w = canvas_w / orig_w
        scale_h = canvas_h / orig_h
        scale = min(scale_w, scale_h)

        scaled_w = int(orig_w * scale)
        scaled_h = int(orig_h * scale)

        # Prevent scaling to zero size
        if scaled_w <= 0 or scaled_h <= 0:
             print("Warning: Calculated scaled size is zero or negative. Cannot scale.")
             self.scaled_reference_image = None
             return

        try:
            aspect_scaled_surf = pygame.transform.smoothscale(self.reference_image, (scaled_w, scaled_h))

            # Create the final surface matching canvas size, transparent background
            # This surface will have the scaled image centered on it.
            final_display_surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
            final_display_surf.fill((0, 0, 0, 0)) # Fully transparent

            # Calculate centering position
            blit_x = (canvas_w - scaled_w) // 2
            blit_y = (canvas_h - scaled_h) // 2

            # Blit the aspect-scaled image onto the transparent canvas
            final_display_surf.blit(aspect_scaled_surf, (blit_x, blit_y))

            # Store this potentially un-alpha'd surface before applying alpha
            self.scaled_reference_image = final_display_surf

            # Apply the current alpha value (apply_reference_alpha will be called after this, or now)
            self.apply_reference_alpha() # Apply alpha immediately after scaling

        except pygame.error as e:
            print(f"Error during reference image scaling: {e}")
            self.scaled_reference_image = None
        except ValueError as e: # Catch potential issues with smoothscale (e.g., zero dimensions)
            print(f"Error during reference image scaling (ValueError): {e}")
            self.scaled_reference_image = None


    def clear_reference_image(self):
        """Removes the current reference image."""
        self.reference_image_path = None
        self.reference_image = None
        self.scaled_reference_image = None
        print("Reference image cleared.")

    def set_reference_alpha(self, alpha_value):
        """Sets the alpha value (0-255) for the reference image."""
        new_alpha = max(0, min(255, int(alpha_value))) # Clamp value
        if new_alpha != self.reference_alpha:
            self.reference_alpha = new_alpha
            #print(f"Set reference alpha to: {self.reference_alpha}") # Debug
            self.apply_reference_alpha()

    def apply_reference_alpha(self):
        """Applies the current alpha value to the scaled reference image surface."""
        # This logic needs refinement. set_alpha modifies the surface in-place.
        # We need to re-apply alpha if the base scaled image changes or alpha changes.
        # Let's re-scale if the reference_image exists but scaled is None
        if self.reference_image and not self.scaled_reference_image:
             self._scale_reference_image()
             # _scale_reference_image now calls apply_reference_alpha internally at the end
             return # Scaling handles alpha application

        # If scaled image exists, just set its alpha
        if self.scaled_reference_image:
            try:
                # Create a fresh scaled surface if it doesn't exist (should be handled above)
                # if not self.scaled_reference_image: self._scale_reference_image()
                # If still none, exit
                # if not self.scaled_reference_image: return

                # Apply alpha to the existing scaled surface
                self.scaled_reference_image.set_alpha(self.reference_alpha)

                # Update knob position based on new alpha
                slider_width = self.ref_alpha_slider_rect.width - self.ref_alpha_knob_rect.width
                # Ensure slider_width is not zero to avoid division error
                if slider_width > 0:
                    knob_x = self.ref_alpha_slider_rect.x + int((self.reference_alpha / 255) * slider_width)
                    self.ref_alpha_knob_rect.x = knob_x
                else: # Handle edge case where slider is too small
                    self.ref_alpha_knob_rect.x = self.ref_alpha_slider_rect.x

            except pygame.error as e:
                print(f"Error applying alpha to reference image: {e}")
            except AttributeError:
                 # Handle case where scaled_reference_image might be None unexpectedly
                 print("Warning: Tried to apply alpha but scaled_reference_image is None.")

    def draw_ui(self):
        """Draw the entire editor UI onto the screen."""
        screen.fill(config.EDITOR_BG_COLOR)

        # --- Draw Dialog FIRST if active --- 
        if self.dialog_mode:
            self.draw_dialog(screen)
            # Don't draw the rest of the UI while a dialog is fully obscuring it
            # (Except maybe a background blur/tint, already handled by draw_dialog overlay)
            return # Stop drawing here if a dialog is active

        # --- Draw Main UI (Only if no dialog active and mode is set) ---
        if self.edit_mode is None:
             # This state should ideally not persist after the initial dialog
             # If we reach here, something might be wrong with dialog flow
             # Maybe draw a "Loading..." or error message?
             loading_font = pygame.font.Font(config.DEFAULT_FONT, 30)
             loading_surf = loading_font.render("Waiting for mode selection...", True, config.BLACK)
             loading_rect = loading_surf.get_rect(center=screen.get_rect().center)
             screen.blit(loading_surf, loading_rect)
             return # Don't draw buttons etc. if mode not set

        # Draw based on mode
        if self.edit_mode == 'monster':
            # 1. Draw Editor Backgrounds (Checkerboards) for BOTH editors
            for sprite_editor in self.sprites.values():
                sprite_editor.draw_background(screen)

            # 2. Draw Reference Image (if active) behind the ACTIVE editor
            if self.scaled_reference_image:
                active_sprite_editor = self.sprites.get(self.current_sprite)
                if active_sprite_editor:
                    screen.blit(self.scaled_reference_image, active_sprite_editor.position)

            # 3. Draw Sprite Pixels for BOTH editors (on top of checkerboard and ref image)
            for sprite_editor in self.sprites.values():
                sprite_editor.draw_pixels(screen)

            # 4. Draw Highlight for the ACTIVE editor
            active_sprite_editor = self.sprites.get(self.current_sprite)
            if active_sprite_editor:
                active_sprite_editor.draw_highlight(screen)

            # Draw Palette & Info Text (Existing)
            self.palette.draw(screen)
            monster_name = config.monsters[self.current_monster_index].get('name', 'Unknown')
            info_text = f"Editing: {monster_name} ({self.current_sprite})" 
            info_surf = self.font.render(info_text, True, config.BLACK)
            screen.blit(info_surf, (50, 50))

        elif self.edit_mode == 'background':
            # Draw background canvas (implement scaling/panning later)
            if self.current_background:
                 # Placeholder: Draw directly for now
                 screen.blit(self.current_background, self.canvas_rect.topleft)
                 pygame.draw.rect(screen, config.BLACK, self.canvas_rect, 1) # Border
            # Draw Palette
            self.palette.draw(screen)
            # Draw Info Text (current background, brush size, zoom)
            bg_name = self.backgrounds[self.current_background_index][0] if self.current_background_index != -1 else "New BG"
            info_text = f"Editing BG: {bg_name} | Brush: {self.brush_size} | Zoom: {self.editor_zoom:.1f}x"
            info_surf = self.font.render(info_text, True, config.BLACK)
            screen.blit(info_surf, (50, 50))

        # Draw common elements (Buttons, Selection, Slider)
        # Ensure buttons exist before drawing
        if hasattr(self, 'buttons') and self.buttons:
             for button in self.buttons:
                  button.draw(screen)
        else:
             # This case implies mode is set but buttons weren't created - should not happen
             print("Warning: edit_mode is set but self.buttons not found in draw_ui")

        if self.mode == 'select':
            self.selection.draw(screen)

        # Draw Brush Size Slider (Existing)
        pygame.draw.rect(screen, config.GRAY_LIGHT, self.brush_slider)
        pygame.draw.rect(screen, config.BLACK, self.brush_slider, 1)
        # Draw brush size knob/indicator (if needed)
        # Add Label for Brush Slider <<<<<< NEW
        brush_text = f"Brush: {self.brush_size}"
        brush_surf = self.font.render(brush_text, True, config.BLACK)
        brush_rect = brush_surf.get_rect(midleft=(self.brush_slider.right + 10, self.brush_slider.centery))
        screen.blit(brush_surf, brush_rect)

        # --- Draw Reference Alpha Slider --- (Existing)
        # Draw slider track
        pygame.draw.rect(screen, config.GRAY_LIGHT, self.ref_alpha_slider_rect)
        pygame.draw.rect(screen, config.BLACK, self.ref_alpha_slider_rect, 1)
        # Draw slider knob
        pygame.draw.rect(screen, config.BLUE, self.ref_alpha_knob_rect) # Use a distinct color for knob
        # Draw alpha value text near slider
        alpha_text = f"Ref Alpha: {self.reference_alpha}"
        alpha_surf = self.font.render(alpha_text, True, config.BLACK)
        alpha_rect = alpha_surf.get_rect(midleft=(self.ref_alpha_slider_rect.right + 10, self.ref_alpha_slider_rect.centery))
        screen.blit(alpha_surf, alpha_rect)

        # Dialog drawing moved to the top
        # if self.dialog_mode:
        #    self.draw_dialog(screen)

    def draw_dialog(self, surface):
        """Draws the current dialog box overlay."""
        # Placeholder - needs full implementation for different dialog types
        # Basic semi-transparent overlay
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*config.BLACK[:3], 180))
        surface.blit(overlay, (0, 0))

        # Simple box and prompt
        dialog_width = 400
        dialog_height = 300
        dialog_rect = pygame.Rect(0, 0, dialog_width, dialog_height)
        dialog_rect.center = surface.get_rect().center
        pygame.draw.rect(surface, config.WHITE, dialog_rect, border_radius=5)
        pygame.draw.rect(surface, config.BLACK, dialog_rect, 2, border_radius=5)

        prompt_surf = self.font.render(self.dialog_prompt, True, config.BLACK)
        prompt_rect = prompt_surf.get_rect(midtop=(dialog_rect.centerx, dialog_rect.top + 20))
        surface.blit(prompt_surf, prompt_rect)

        # Draw options (buttons) - needs proper layout
        button_y = prompt_rect.bottom + 30
        for i, option in enumerate(self.dialog_options):
             if isinstance(option, Button):
                  # Position buttons dynamically here
                  option.rect.center = (dialog_rect.centerx, button_y + i * (option.rect.height + 10))
                  option.draw(surface)
        # Add rendering for other dialog elements (text input, file list, color picker)

    def run(self):
        """Main application loop."""
        running = True
        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.handle_event(event) # Pass event to editor

            # Drawing
            self.draw_ui()

            # Update display
            pygame.display.flip()

            # Cap frame rate
            clock.tick(config.FPS)

        pygame.quit()

# Main execution block
if __name__ == "__main__":
    # Set up necessary directories if they don't exist
    # (config.py might already do this, but double-check or add here)
    if not os.path.exists(config.SPRITE_DIR):
        os.makedirs(config.SPRITE_DIR)
        print(f"Created missing directory: {config.SPRITE_DIR}")
    if not os.path.exists(config.BACKGROUND_DIR):
        os.makedirs(config.BACKGROUND_DIR)
        print(f"Created missing directory: {config.BACKGROUND_DIR}")
    if not os.path.exists(config.DATA_DIR):
         os.makedirs(config.DATA_DIR)
         print(f"Created missing directory: {config.DATA_DIR}")
         # Optional: Create dummy data files if they are missing and required for startup?
         # e.g., create empty monsters.json if it doesn't exist? Needs careful consideration.

    # Ensure monster data is loaded globally for the Editor
    # Note: load_monsters() is already called at the top level, 
    # assigning to global `monsters`. Ensure this happens before Editor init.
    if 'monsters' not in globals() or not monsters:
         print("Reloading monster data for main execution...")
         monsters = load_monsters() # Reload if it failed earlier or wasn't assigned
         if not monsters:
              print("Fatal: Could not load monster data. Exiting.")
              sys.exit(1)
    # Assign monsters to config for editor access if needed, or ensure editor uses global
    config.monsters = monsters 

    editor = Editor()
    editor.run()
