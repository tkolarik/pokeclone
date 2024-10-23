import pygame
from pygame.locals import *
import tkinter as tk
from tkinter import filedialog, colorchooser
import sys
import os
import json
import copy
import colorsys

# Initialize Tkinter first
root = tk.Tk()
root.withdraw()

# Now import and initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1300, 800  # Reduced window size
GRID_SIZE = 32
PIXEL_SIZE = 15  # Reduced pixel size for smaller sprite editing windows
FPS = 60
BACKGROUND_WIDTH, BACKGROUND_HEIGHT = 1600, 800  # Adjusted background size
MAX_BRUSH_SIZE = 20  # Reduced max brush size
PALETTE_COLS = 20  # Increased number of columns in the palette
PALETTE_ROWS = 8  # Reduced number of rows to display at once

# Setup
screen = pygame.display.set_mode((WIDTH, HEIGHT))
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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    monsters_file = os.path.join(script_dir, "data", "monsters.json")

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
    the button on a surface, checking for mouse clicks, and exe
    cuting an associated
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

    def __init__(self, rect, text, action=None):
        """
        Initialize a new Button instance.

        Args:
            rect (tuple): A tuple representing the button's rectangle (x, y, width, height).
            text (str): The text label to display on the button.
            action (callable, optional): The function to be executed when the button is clicked.
        """
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action
        self.color = (200, 200, 200)
        self.hover_color = (170, 170, 170)
        self.font = pygame.font.Font(None, 24)

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
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
        text_surf = self.font.render(self.text, True, (0, 0, 0))
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
    """
    A sophisticated sprite editing component for pixel art creation and manipulation.

    This class encapsulates the functionality for editing individual sprite frames
    within a larger pixel art editor system. It provides methods for loading, saving,
    and manipulating sprite data, as well as rendering the sprite to a surface.

    Attributes:
        position (tuple): The (x, y) position of the sprite editor on the screen.
        name (str): The identifier for this sprite (e.g., 'front', 'back').
        frame (pygame.Surface): The actual sprite data as a Pygame surface.

    Methods:
        load_sprite(monster_name: str) -> None
        save_sprite() -> None
        draw(surface: pygame.Surface) -> None
        get_grid_position(pos: tuple) -> tuple | None
    """

    def __init__(self, position, name):
        """
        Initialize a new SpriteEditor instance.

        Args:
            position (tuple): The (x, y) position of the sprite editor on the screen.
            name (str): The identifier for this sprite (e.g., 'front', 'back').
        """
        self.position = position  # (x, y) position on screen
        self.name = name
        self.frame = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)

    def load_sprite(self, monster_name):
        """
        Load a sprite from file for a given monster.

        This method attempts to load a sprite image file corresponding to the given
        monster name and the sprite's own name (e.g., 'front' or 'back'). If the file
        exists, it is loaded and scaled to fit the editor's grid size. If the file
        is not found, a message is printed to the console.

        Args:
            monster_name (str): The name of the monster whose sprite should be loaded.

        Returns:
            None

        Side effects:
            - Modifies the `frame` attribute of the SpriteEditor instance.
            - Prints a message to the console if the sprite file is not found.
        """
        self.frame.fill((0, 0, 0, 0))
        filename = f"sprites/{monster_name}_{self.name}.png"
        if os.path.exists(filename):
            loaded_image = pygame.image.load(filename).convert_alpha()
            if loaded_image.get_size() != (GRID_SIZE, GRID_SIZE):
                loaded_image = pygame.transform.scale(loaded_image, (GRID_SIZE, GRID_SIZE))
            self.frame.blit(loaded_image, (0, 0))
        else:
            print(f"Sprite not found: {filename}")

    def save_sprite(self):
        """
        Save the current sprite frame to a file.

        This method saves the current sprite frame as a PNG image file. The filename
        is constructed using the current monster's name and the sprite's name (e.g.,
        'front' or 'back'). The sprite is scaled up before saving to preserve pixel
        fidelity.

        Returns:
            None

        Side effects:
            - Creates a 'sprites' directory if it doesn't exist.
            - Writes a PNG file to the 'sprites' directory.
        """
        if not os.path.exists("sprites"):
            os.makedirs("sprites")
        scaled_frame = pygame.transform.scale(self.frame, (GRID_SIZE * PIXEL_SIZE, GRID_SIZE * PIXEL_SIZE))
        filename = f"sprites/{monsters[editor.current_monster_index]['name']}_{self.name}.png"
        pygame.image.save(scaled_frame, filename)

    def draw(self, surface):
        """
        Render the sprite editor and its current sprite frame to a surface.

        This method draws a checkerboard pattern as a background for transparency,
        then overlays the current sprite frame on top. If this sprite is currently
        selected in the editor, a red highlight rectangle is drawn around it.

        Args:
            surface (pygame.Surface): The surface on which to draw the sprite editor.

        Returns:
            None

        Side effects:
            - Modifies the provided surface by drawing on it.
        """
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                rect = (self.position[0] + x * PIXEL_SIZE, self.position[1] + y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE)
                color = (200, 200, 200) if (x + y) % 2 == 0 else (255, 255, 255)
                pygame.draw.rect(surface, color, rect)

        scaled_frame = pygame.transform.scale(self.frame, (GRID_SIZE * PIXEL_SIZE, GRID_SIZE * PIXEL_SIZE))
        surface.blit(scaled_frame, self.position)

        if editor.current_sprite == self.name:
            highlight_rect = pygame.Rect(self.position[0] - 10, self.position[1] - 10,
                                         GRID_SIZE * PIXEL_SIZE + 20, GRID_SIZE * PIXEL_SIZE + 20)
            pygame.draw.rect(surface, (255, 0, 0), highlight_rect, 3)

    def get_grid_position(self, pos):
        """
        Convert screen coordinates to grid coordinates within the sprite.

        This method takes a screen position (typically from a mouse event) and
        converts it to grid coordinates within the sprite, if the position falls
        within the sprite's boundaries.

        Args:
            pos (tuple): A (x, y) tuple representing screen coordinates.

        Returns:
            tuple | None: A (grid_x, grid_y) tuple if the position is within the
                          sprite's boundaries, or None if it's outside.
        """
        x, y = pos
        grid_x = (x - self.position[0]) // PIXEL_SIZE
        grid_y = (y - self.position[1]) // PIXEL_SIZE
        if 0 <= grid_x < GRID_SIZE and 0 <= grid_y < GRID_SIZE:
            return grid_x, grid_y
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
        self.font = pygame.font.Font(None, 20)  # Smaller font
        self.scroll_offset = 0
        self.colors_per_page = PALETTE_COLS * PALETTE_ROWS
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
            col = index % PALETTE_COLS
            row = index // PALETTE_COLS
            rect = pygame.Rect(
                x0 + col * (self.block_size + self.padding),
                y0 + row * (self.block_size + self.padding),
                self.block_size,
                self.block_size
            )

            if color[3] == 0:  # Transparent color
                pygame.draw.rect(surface, (200, 200, 200), rect)
                pygame.draw.line(surface, (255, 0, 0), rect.topleft, rect.bottomright, 2)
                pygame.draw.line(surface, (255, 0, 0), rect.topright, rect.bottomleft, 2)
            else:
                pygame.draw.rect(surface, color[:3], rect)

            if color == editor.current_color:
                pygame.draw.rect(surface, (255, 0, 0), rect.inflate(4, 4), 2)

        # Palette label
        label = self.font.render("Palette", True, (0, 0, 0))
        surface.blit(label, (x0, y0 - 30))

        # Scroll indicators
        if self.total_pages > 1:
            up_arrow = self.font.render("↑", True, (0, 0, 0))
            down_arrow = self.font.render("↓", True, (0, 0, 0))
            surface.blit(up_arrow, (x0 + PALETTE_COLS * (self.block_size + self.padding) + 10, y0))
            surface.blit(down_arrow, (x0 + PALETTE_COLS * (self.block_size + self.padding) + 10, y0 + PALETTE_ROWS * (self.block_size + self.padding) - 20))

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
        scroll_area_x = x0 + PALETTE_COLS * (self.block_size + self.padding) + 10
        if x >= scroll_area_x and x <= scroll_area_x + 20:
            if y <= self.position[1] + PALETTE_ROWS * (self.block_size + self.padding):
                # Up arrow
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
            elif y >= self.position[1] + PALETTE_ROWS * (self.block_size + self.padding) - 20:
                # Down arrow
                if self.scroll_offset < self.total_pages - 1:
                    self.scroll_offset += 1
            return

        # Determine which color was clicked
        for index, color in enumerate(PALETTE[self.scroll_offset * self.colors_per_page:(self.scroll_offset + 1) * self.colors_per_page]):
            col = index % PALETTE_COLS
            row = index // PALETTE_COLS
            rect = pygame.Rect(
                x0 + col * (self.block_size + self.padding),
                y0 + row * (self.block_size + self.padding),
                self.block_size,
                self.block_size
            )
            if rect.collidepoint(x, y):
                editor.select_color(color)
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

        This method toggles the selection tool's activation state and deactivates
        the selection if it was active.
        """
        self.selecting = not self.selecting
        if not self.selecting:
            self.active = False
            self.rect = pygame.Rect(0, 0, 0, 0)
            print("Selection mode deactivated.")

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

        Args:
            surface (pygame.Surface): The surface on which to draw the selection rectangle.
        """
        if self.active and self.rect.width > 0 and self.rect.height > 0:
            sprite = self.editor.sprites[self.editor.current_sprite]
            x0, y0 = sprite.position
            selection_surface = pygame.Surface((self.rect.width * PIXEL_SIZE, self.rect.height * PIXEL_SIZE), pygame.SRCALPHA)
            selection_surface.fill((0, 0, 255, 50))  # Semi-transparent blue
            pygame.draw.rect(selection_surface, (0, 0, 255), selection_surface.get_rect(), 2)
            surface.blit(selection_surface, (x0 + self.rect.x * PIXEL_SIZE, y0 + self.rect.y * PIXEL_SIZE))

    def get_selected_pixels(self):
        """
        Get the pixels within the selection rectangle.

        Returns:
            dict: A dictionary mapping pixel positions to their corresponding colors.
        """
        sprite = self.editor.sprites[self.editor.current_sprite]
        pixels = {}
        for x in range(self.rect.width):
            for y in range(self.rect.height):
                pixel_pos = (self.rect.x + x, self.rect.y + y)
                if 0 <= pixel_pos[0] < GRID_SIZE and 0 <= pixel_pos[1] < GRID_SIZE:
                    color = sprite.frame.get_at(pixel_pos)
                    pixels[(x, y)] = color
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
            'front': SpriteEditor((50, 110), 'front'),
            'back': SpriteEditor((575, 110), 'back')  # Adjusted position
        }
        self.palette = Palette((50, HEIGHT - 180))  # Adjusted position
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
            self.canvas_rect = pygame.Rect(50, 100, BACKGROUND_WIDTH, BACKGROUND_HEIGHT)
            if self.backgrounds:
                self.current_background = self.backgrounds[0][1].copy()
            else:
                self.create_new_background()
        else:
            self.current_background = pygame.Surface((BACKGROUND_WIDTH, BACKGROUND_HEIGHT))
            self.current_background.fill((255, 255, 255))  # White background

        # Load the first monster's art
        self.load_monster()

        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []

        # Create buttons after setting edit_mode
        self.buttons = self.create_buttons()

        # Add this line to create a font
        self.font = pygame.font.Font(None, 24)  # None uses the default font, 24 is the font size

        self.brush_slider = pygame.Rect(50, HEIGHT - 40, 200, 20)  # Add this line

    def choose_edit_mode(self):
        """
        Choose the editing mode (monster or background).

        This method allows the user to choose between editing monster sprites
        or background images. It returns the chosen mode as a string.

        Returns:
            str: The chosen editing mode ('monster' or 'background').
        """
        # For now, let's default to 'monster' mode
        # You can implement a dialog to choose between 'monster' and 'background' later
        return 'monster'

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
        start_x = WIDTH - button_width - padding
        start_y = 50

        all_buttons = [
            ("Save", self.save_current),
            ("Load", self.load_background),  # Changed to load_background
            ("Clear", self.clear_current),
            ("Color Picker", self.open_color_picker),  # Re-added Color Picker button
            ("Eraser", self.toggle_eraser),
            ("Fill", self.toggle_fill),
            ("Select", self.toggle_selection_mode),
            ("Copy", self.copy_selection),
            ("Paste", self.paste_selection),
            ("Mirror", self.mirror_selection),
            ("Rotate", self.rotate_selection),
            ("Undo", self.undo),
            ("Redo", self.redo),
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

    def open_color_picker(self):
        """
        Open the color picker dialog.
        """
        color_code = colorchooser.askcolor(title="Choose Color")
        if color_code and color_code[0]:
            r, g, b = map(int, color_code[0])
            self.select_color((r, g, b, 255))

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
        if not os.path.exists('backgrounds'):
            os.makedirs('backgrounds')
        for filename in os.listdir('backgrounds'):
            if filename.endswith('.png'):
                path = os.path.join('backgrounds', filename)
                try:
                    bg = pygame.image.load(path).convert_alpha()
                    backgrounds.append((filename, bg))
                except pygame.error as e:
                    print(f"Failed to load background {filename}: {e}")
        return backgrounds

    def show_edit_mode_dialog(self):
        """
        Display a dialog to choose the editing mode (monster or background).

        This method creates a Tkinter dialog that allows the user to choose
        between editing monster sprites or background images. It returns
        the selected mode as a string.

        Returns:
            str: The chosen editing mode ('monster' or 'background').
        """
        # Create a new Tkinter top-level window
        dialog = tk.Toplevel(root)
        dialog.title("Choose Edit Mode")
        dialog.geometry("300x200")
        dialog.resizable(False, False)

        # Variable to store the selected option
        selected_mode = tk.StringVar(value="monster")

        # Radio buttons for selection
        tk.Label(dialog, text="Choose Edit Mode:", font=("Arial", 14)).pack(pady=20)
        tk.Radiobutton(dialog, text="Monster", variable=selected_mode, value="monster", font=("Arial", 12)).pack(anchor='w', padx=50)
        tk.Radiobutton(dialog, text="Background", variable=selected_mode, value="background", font=("Arial", 12)).pack(anchor='w', padx=50)

        # Function to handle the selection
        def confirm_selection():
            dialog.destroy()

        tk.Button(dialog, text="OK", command=confirm_selection, font=("Arial", 12)).pack(pady=20)

        # Wait for the user to close the dialog
        root.wait_window(dialog)

        return selected_mode.get()

    def show_background_action_dialog(self):
        """
        Display a dialog to choose the background action (new or edit).

        This method creates a Tkinter dialog that allows the user to choose
        whether to create a new background or edit an existing one. It returns
        the selected action as a string.

        Returns:
            str: The chosen background action ('new' or 'edit').
        """
        dialog = tk.Toplevel(root)
        dialog.title("Background Action")
        dialog.geometry("300x200")
        dialog.resizable(False, False)

        selected_action = tk.StringVar(value="new")

        tk.Label(dialog, text="Choose Background Action:", font=("Arial", 14)).pack(pady=20)
        tk.Radiobutton(dialog, text="New", variable=selected_action, value="new", font=("Arial", 12)).pack(anchor='w', padx=50)
        tk.Radiobutton(dialog, text="Edit", variable=selected_action, value="edit", font=("Arial", 12)).pack(anchor='w', padx=50)

        def confirm_selection():
            dialog.destroy()

        tk.Button(dialog, text="OK", command=confirm_selection, font=("Arial", 12)).pack(pady=20)

        root.wait_window(dialog)

        return selected_action.get()

    def choose_edit_mode(self):
        """
        Choose the editing mode (monster or background) and handle background actions.

        This method displays a dialog to choose the editing mode (monster or background)
        and handles background-specific actions (new or edit) if the background mode
        is chosen. It returns the chosen editing mode as a string.

        Returns:
            str: The chosen editing mode ('monster' or 'background').
        """
        mode = self.show_edit_mode_dialog()
        if mode == 'background':
            self.choose_background_action()
            return 'background'
        else:
            return 'monster'

    def choose_background_action(self):
        """
        Handle background-specific actions (new or edit).

        This method displays a dialog to choose whether to create a new background
        or edit an existing one. It performs the appropriate action based on the
        user's selection.
        """
        if not self.backgrounds:
            print("No existing backgrounds. Creating a new one.")
            self.create_new_background()
        else:
            action = self.show_background_action_dialog()
            if action == 'new':
                self.create_new_background()
            elif action == 'edit' and self.backgrounds:
                self.current_background_index = 0
                self.current_background = self.backgrounds[self.current_background_index][1].copy()
                print(f"Editing background: {self.backgrounds[self.current_background_index][0]}")
            else:
                print("Invalid action. Creating a new background.")
                self.create_new_background()

    def create_new_background(self):
        """
        Create a new background image.

        This method prompts the user to choose a filename for the new background
        image and initializes it as a white surface. It saves the new background
        to the 'backgrounds' directory and updates the background list.
        """
        filename = filedialog.asksaveasfilename(
            title="New Background",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")]
        )
        if filename:
            if not filename.endswith('.png'):
                filename += '.png'
            self.current_background = pygame.Surface((BACKGROUND_WIDTH, BACKGROUND_HEIGHT), pygame.SRCALPHA)
            self.current_background.fill((255, 255, 255, 255))  # Set to white with full opacity
            pygame.image.save(self.current_background, filename)
            print(f"Saved background as {filename}")
            self.backgrounds = self.load_backgrounds()
            self.current_background_index = next(
                (i for i, (name, _) in enumerate(self.backgrounds) if name == os.path.basename(filename)),
                -1
            )
        else:
            print("No filename provided. Using default white background.")
            self.current_background = pygame.Surface((BACKGROUND_WIDTH, BACKGROUND_HEIGHT), pygame.SRCALPHA)
            self.current_background.fill((255, 255, 255, 255))  # White background
            self.current_background_index = -1

    def save_background(self, filename=None):
        """
        Save the current background image.

        This method saves the current background image to a file. If no filename
        is provided, it prompts the user to choose one. It updates the background
        list and the current background index.

        Args:
            filename (str, optional): The filename to save the background as.
        """
        if not filename:
            if self.current_background_index >= 0 and self.backgrounds:
                filename = self.backgrounds[self.current_background_index][0]
            else:
                filename = filedialog.asksaveasfilename(
                    title="Save Background",
                    defaultextension=".png",
                    filetypes=[("PNG files", "*.png")]
                )

        if filename:
            if not filename.endswith('.png'):
                filename += '.png'
            full_path = os.path.join("backgrounds", filename)
            pygame.image.save(self.current_background, full_path)
            print(f"Saved background as {filename}")
            self.backgrounds = self.load_backgrounds()
            self.current_background_index = next(
                (i for i, (name, _) in enumerate(self.backgrounds) if name == filename),
                -1
            )

    def load_monster(self):
        """
        Load the current monster's sprites.

        This method loads the sprites for the currently selected monster. It updates
        the sprite frames and prints a status message.
        """
        monster_name = monsters[self.current_monster_index]['name']
        for sprite in self.sprites.values():
            sprite.load_sprite(monster_name)
        print(f"Loaded monster: {monster_name}")

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
            print(f"Switched to previous monster: {monsters[self.current_monster_index]['name']}")
        else:
            print("Already at the first monster.")

    def next_monster(self):
        """
        Switch to the next monster in the list.

        This method increments the current monster index and loads the next
        monster's sprites. It prints a status message.
        """
        if self.current_monster_index < len(monsters) - 1:
            self.current_monster_index += 1
            self.load_monster()
            print(f"Switched to next monster: {monsters[self.current_monster_index]['name']}")
        else:
            print("Already at the last monster.")

    def previous_background(self):
        """
        Switch to the previous background in the list.

        This method decrements the current background index and updates the
        current background. It prints a status message.
        """
        if self.backgrounds:
            self.current_background_index = (self.current_background_index - 1) % len(self.backgrounds)
            self.current_background = self.backgrounds[self.current_background_index][1].copy()
            self.center_canvas()
            print(f"Switched to background: {self.backgrounds[self.current_background_index][0]}")
        else:
            print("No backgrounds available to switch.")

    def next_background(self):
        """
        Switch to the next background in the list.

        This method increments the current background index and updates the
        current background. It prints a status message.
        """
        if self.backgrounds:
            self.current_background_index = (self.current_background_index + 1) % len(self.backgrounds)
            self.current_background = self.backgrounds[self.current_background_index][1].copy()
            self.center_canvas()
            print(f"Switched to background: {self.backgrounds[self.current_background_index][0]}")
        else:
            print("No backgrounds available to switch.")

    def update_buttons(self):
        """
        Update the dynamic button texts.

        This method updates the texts of buttons that change based on the current
        editor state, such as the eraser and fill buttons.
        """
        # Update dynamic button texts
        for button in self.buttons:
            if button.text.startswith("Eraser"):
                button.text = "Eraser" if self.eraser_mode else "Brush"
            elif button.text.startswith("Fill"):
                button.text = "Fill" if self.fill_mode else "Draw"
            elif button.text.startswith("Sprite:"):
                button.text = f"Sprite: {self.current_sprite.capitalize()}"

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
            print(f"Selected color: {color}")

    def open_color_picker(self):
        """
        Open the color picker dialog.

        This method opens a Tkinter color picker dialog and selects the chosen
        color if a valid color code is returned.
        """
        color_code = colorchooser.askcolor(title="Choose Color")
        if color_code and color_code[0]:
            r, g, b = map(int, color_code[0])
            self.select_color((r, g, b, 255))

    def handle_drawing(self, grid_pos, sprite_name):
        """
        Handle drawing on the sprite or background.

        This method handles drawing on the sprite or background based on the
        provided grid position and sprite name. It saves the current state
        before drawing.

        Args:
            grid_pos (tuple): The grid position to draw at.
            sprite_name (str): The name of the sprite to draw on.
        """
        x, y = grid_pos
        color = self.get_current_color()
        self.save_state()
        if self.edit_mode == 'monster':
            self.sprites[sprite_name].frame.set_at((x, y), color)
            print(f"Drew at ({x}, {y}) with color {color} on sprite {sprite_name}")
        elif self.edit_mode == 'background':
            self.draw_on_background_position((x, y))

    def get_current_color(self):
        """
        Get the current color based on the editor state.

        This method returns the current color based on the editor state, taking
        into account the eraser mode and the validity of the current color.

        Returns:
            tuple: The RGBA color tuple.
        """
        if self.eraser_mode:
            return (0, 0, 0, 0)
        elif isinstance(self.current_color, tuple) and len(self.current_color) == 4:
            return self.current_color
        elif isinstance(self.current_color, tuple) and len(self.current_color) == 3:
            return (*self.current_color, 255)
        else:
            return (0, 0, 0, 255)  # Default to black if color is invalid

    def fill(self, grid_pos, sprite_name):
        """
        Fill an area with the current color.

        This method performs a flood fill operation starting from the provided
        grid position and sprite name. It saves the current state before filling.

        Args:
            grid_pos (tuple): The starting grid position for the fill operation.
            sprite_name (str): The name of the sprite to fill.
        """
        x, y = grid_pos
        frame = self.sprites[sprite_name].frame
        target_color = frame.get_at((x, y))
        fill_color = self.get_current_color()

        if target_color == fill_color:
            return

        self.save_state()
        stack = [(x, y)]
        filled_pixels = set()

        while stack:
            px, py = stack.pop()
            if (px, py) in filled_pixels:
                continue
            if 0 <= px < GRID_SIZE and 0 <= py < GRID_SIZE:
                current_pixel_color = frame.get_at((px, py))
                if current_pixel_color == target_color:
                    frame.set_at((px, py), fill_color)
                    filled_pixels.add((px, py))
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        stack.append((px + dx, py + dy))
        print(f"Filled area starting at ({x}, {y}) with color {fill_color} on sprite {sprite_name}")

    def save_monster(self):
        """
        Save the current monster's sprites.

        This method saves the current monster's sprites to files. It prints a
        status message.
        """
        for sprite in self.sprites.values():
            sprite.save_sprite()
        print(f"Saved {monsters[self.current_monster_index]['name']}")

    def clear_sprite(self):
        """
        Clear the current sprite.

        This method clears the current sprite by filling it with transparent
        pixels. It saves the current state before clearing.
        """
        self.save_state()
        self.sprites[self.current_sprite].frame.fill((0, 0, 0, 0))
        print(f"Cleared sprite: {self.current_sprite}")

    def draw_ui(self):
        """
        Draw the editor UI on the screen.

        This method draws the editor UI on the screen, including the sprites,
        background, buttons, palette, and other elements.

        Returns:
            None
        """
        screen.fill((200, 200, 200))

        if self.edit_mode == 'monster':
            # Draw sprites
            for sprite_name, sprite in self.sprites.items():
                sprite.draw(screen)

            # Draw monster info at the bottom
            monster = monsters[self.current_monster_index]
            info_text = [
                f"Name: {monster['name']}",
                f"Type: {monster['type']}",
                f"Max HP: {monster['max_hp']}",
                "Moves: " + ", ".join(monster['moves'])
            ]
            info_y = HEIGHT - 100
            for i, line in enumerate(info_text):
                text_surface = self.font.render(line, True, (0, 0, 0))
                screen.blit(text_surface, (50, info_y + i * 20))

        elif self.edit_mode == 'background':
            # Draw background with current zoom
            scaled_background = pygame.transform.scale(
                self.current_background,
                (self.canvas_rect.width, self.canvas_rect.height)
            )
            screen.blit(scaled_background, self.canvas_rect.topleft)
            pygame.draw.rect(screen, (255, 0, 0), self.canvas_rect, 2)  # Red bounding box

            # Draw brush preview
            mouse_pos = pygame.mouse.get_pos()
            if self.canvas_rect.collidepoint(mouse_pos):
                preview_size = max(1, int(self.brush_size))
                pygame.draw.circle(screen, (128, 128, 128, 128), mouse_pos, preview_size, 1)

        # Draw editing mode info at the bottom
        info_text = [
            f"Edit Mode: {self.edit_mode.capitalize()}",
            f"Current Sprite: {self.current_sprite}" if self.edit_mode == 'monster' else f"Background: {self.current_background_index}",
            f"Brush Size: {self.brush_size}",
            f"Eraser Mode: {'On' if self.eraser_mode else 'Off'}",
            f"Fill Mode: {'On' if self.fill_mode else 'Off'}",
            f"Selection Mode: {'On' if self.selection.selecting else 'Off'}",
            f"Zoom: {self.editor_zoom:.1f}x",
        ]
        info_y = HEIGHT - 160
        for i, line in enumerate(info_text):
            text_surface = self.font.render(line, True, (0, 0, 0))
            screen.blit(text_surface, (WIDTH - 250, info_y + i * 20))

        # Draw buttons
        for button in self.buttons:
            button.draw(screen)

        # Draw palette
        self.palette.draw(screen)

        self.selection.draw(screen)

        pygame.display.flip()

    def handle_event(self, event):
        """
        Process and respond to a single Pygame event.

        This method is the central event handler for the editor. It interprets
        user inputs (mouse and keyboard events) and triggers appropriate actions
        such as drawing, selecting colors, changing tools, or manipulating the canvas.

        Args:
            event (pygame.event.Event): The Pygame event to process.

        Returns:
            bool: True if the main loop should continue, False if the application
                  should exit.

        Side effects:
            - May modify various attributes of the Editor instance based on user input.
            - May trigger drawing operations on sprite or background surfaces.
            - May change the current tool or color selection.
        """
        if event.type == pygame.QUIT:
            return False  # Signal to exit main loop

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left-click
                x, y = event.pos
                # Check if any button is clicked
                for button in self.buttons:
                    if button.is_clicked(event):
                        button.action()
                        return True  # Exit event handling to prevent further processing
                # Check if palette is clicked
                self.palette.handle_click((x, y))

                # Check if brush slider is clicked
                if self.edit_mode == 'background' and self.brush_slider.collidepoint(event.pos):
                    self.adjusting_brush = True
                    self.update_brush_size(event.pos[0])
                    return True

                # Check if in select mode
                if self.mode == 'select':
                    self.selection.start(event.pos)
                else:
                    # Check if drawing on sprites
                    for sprite_name, sprite in self.sprites.items():
                        grid_pos = sprite.get_grid_position((x, y))
                        if grid_pos:
                            self.current_sprite = sprite_name
                            if self.fill_mode:
                                self.fill(grid_pos, sprite_name)
                            else:
                                self.drawing = True
                                self.handle_drawing(grid_pos, sprite_name)
                            break

                # Handle paste mode
                if self.paste_mode:
                    for sprite_name, sprite in self.sprites.items():
                        grid_pos = sprite.get_grid_position((x, y))
                        if grid_pos:
                            self.current_sprite = sprite_name
                            self.paste_selection_at(grid_pos)
                            self.paste_mode = False
                            break

                if self.edit_mode == 'background':
                    if self.fill_mode:
                        self.fill_background_position(event.pos)
                    else:
                        self.drawing = True
                        self.draw_on_background(event.pos)

            elif event.button == 3:  # Right-click for eraser
                self.eraser_mode = True
                self.fill_mode = False
                print("Eraser mode activated.")

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:  # Left-click release
                if self.drawing:
                    self.drawing = False
                if self.mode == 'select' and self.selection.selecting:
                    self.selection.end_selection(event.pos)
                self.adjusting_brush = False
            elif event.button == 3:  # Right-click release
                self.eraser_mode = False
                print("Eraser mode deactivated.")

        elif event.type == pygame.MOUSEMOTION:
            if self.drawing and not self.fill_mode:
                x, y = event.pos
                if self.edit_mode == 'monster':
                    sprite = self.sprites[self.current_sprite]
                    grid_pos = sprite.get_grid_position((x, y))
                    if grid_pos:
                        self.handle_drawing(grid_pos, self.current_sprite)
                else:
                    self.draw_on_background(event.pos)
            if self.mode == 'select' and self.selection.selecting:
                self.selection.update(event.pos)
            if self.adjusting_brush:
                self.update_brush_size(event.pos[0])

        elif event.type == pygame.KEYDOWN:
            # Handle keyboard shortcuts
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                if event.key == pygame.K_z:
                    self.undo()
                elif event.key == pygame.K_y:
                    self.redo()
                elif event.key == pygame.K_s:
                    self.save_current()
                elif event.key == pygame.K_o:
                    self.load_background()  # Changed to load_background
                elif event.key == pygame.K_c:
                    self.copy_selection()
                elif event.key == pygame.K_v:
                    self.paste_mode = True
                    print("Paste mode activated. Click where to paste.")
                elif event.key == pygame.K_m:
                    self.mirror_selection()
                elif event.key == pygame.K_r:
                    self.rotate_selection()

            # Handle other keys
            if event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                self.increase_brush_size()
            elif event.key == pygame.K_MINUS:
                self.decrease_brush_size()
            elif event.key == pygame.K_ESCAPE:
                if self.mode == 'select':
                    self.mode = 'draw'
                    self.selection.toggle()
                    print("Exited selection mode.")

        elif event.type == pygame.MOUSEWHEEL:
            # Use MOUSEWHEEL exclusively for panning, remove zoom functionality
            pan_speed = 20  # Adjust this value to change panning sensitivity
            self.pan_background(-event.x * pan_speed, -event.y * pan_speed)
            print(f"Panned background by ({-event.x * pan_speed}, {-event.y * pan_speed})")

        return True  # Continue main loop

    def save_current(self):
        """
        Save the current work in progress.

        This method saves either the current monster sprite or the current background,
        depending on the active edit mode. It triggers the appropriate save method
        and provides user feedback.

        Returns:
            None

        Side effects:
            - May create or modify files on the disk.
            - Prints a status message to the console.
        """
        if self.edit_mode == 'monster':
            self.save_monster()
        else:
            self.save_background()

    def load_background(self):
        """
        Load a background image file.
        """
        filename = filedialog.askopenfilename(
            title="Load Background",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if filename:
            self.load_background_file(filename)

    def load_background_file(self, filename):
        """
        Load a background image and set it as the current background.
        """
        if os.path.exists(filename):
            self.current_background = pygame.image.load(filename).convert_alpha()
            self.current_background = pygame.transform.scale(self.current_background, (BACKGROUND_WIDTH, BACKGROUND_HEIGHT))
            self.editor_zoom = 1.0
            self.canvas_rect = pygame.Rect(0, 0, BACKGROUND_WIDTH, BACKGROUND_HEIGHT)
            self.center_canvas()
            self.backgrounds = self.load_backgrounds()  # Reload the list of backgrounds
            self.current_background_index = self.backgrounds.index((os.path.basename(filename), self.current_background))
            print(f"Loaded background: {filename}")
        else:
            print(f"Background file not found: {filename}")

    def previous_background(self):
        """
        Switch to the previous background in the list.
        """
        if self.backgrounds:
            self.current_background_index = (self.current_background_index - 1) % len(self.backgrounds)
            self.current_background = self.backgrounds[self.current_background_index][1].copy()
            self.center_canvas()
            print(f"Switched to background: {self.backgrounds[self.current_background_index][0]}")
        else:
            print("No backgrounds available to switch.")

    def next_background(self):
        """
        Switch to the next background in the list.
        """
        if self.backgrounds:
            self.current_background_index = (self.current_background_index + 1) % len(self.backgrounds)
            self.current_background = self.backgrounds[self.current_background_index][1].copy()
            self.center_canvas()
            print(f"Switched to background: {self.backgrounds[self.current_background_index][0]}")
        else:
            print("No backgrounds available to switch.")

    def clear_current(self):
        """
        Clear the current sprite or background.

        This method clears either the current monster sprite or the current background,
        depending on the active edit mode. It provides user feedback.

        Returns:
            None

        Side effects:
            - Modifies the current sprite or background data.
            - Prints a status message to the console.
        """
        if self.edit_mode == 'monster':
            self.clear_sprite()
        else:
            self.create_new_background()

    def toggle_eraser(self):
        """
        Toggle the eraser tool.

        This method toggles the eraser tool on or off. It provides user feedback.

        Returns:
            None

        Side effects:
            - Modifies the eraser_mode attribute.
            - Prints a status message to the console.
        """
        self.eraser_mode = not self.eraser_mode
        self.fill_mode = False
        print("Eraser mode toggled.")

    def toggle_fill(self):
        """
        Toggle the fill tool.

        This method toggles the fill tool on or off. It provides user feedback.

        Returns:
            None

        Side effects:
            - Modifies the fill_mode attribute.
            - Prints a status message to the console.
        """
        self.fill_mode = not self.fill_mode
        self.eraser_mode = False
        print("Fill mode toggled.")

    def toggle_selection_mode(self):
        """
        Toggle the selection mode.

        This method toggles the selection mode on or off. It provides user feedback.

        Returns:
            None

        Side effects:
            - Modifies the selection mode attribute.
            - Prints a status message to the console.
        """
        self.selection.toggle()
        if self.selection.selecting:
            self.mode = 'select'
            print("Selection mode activated. Click and drag to select an area.")
        else:
            self.mode = 'draw'
            print("Selection mode deactivated.")

    def copy_selection(self):
        """
        Copy the currently selected pixels.

        This method copies the pixels within the current selection to the copy buffer.
        It provides user feedback.

        Returns:
            None

        Side effects:
            - Modifies the copy_buffer attribute.
            - Prints a status message to the console.
        """
        if not self.selection.active:
            print("No selection to copy.")
            return
        self.copy_buffer = self.selection.get_selected_pixels()
        print("Selection copied.")

    def paste_selection(self):
        """
        Paste the copied pixels.

        This method activates paste mode, allowing the user to click where to paste
        the copied pixels. It provides user feedback.

        Returns:
            None

        Side effects:
            - Activates paste mode.
            - Prints a status message to the console.
        """
        if self.copy_buffer is None:
            print("No copied selection to paste.")
            return
        self.paste_mode = True
        print("Paste mode activated. Click where to paste.")

    def paste_selection_at(self, grid_pos):
        """
        Paste the copied pixels at the specified grid position.

        This method pastes the copied pixels at the specified grid position. It provides
        user feedback.

        Args:
            grid_pos (tuple): The grid position to paste the pixels at.

        Returns:
            None

        Side effects:
            - Modifies the current sprite or background data.
            - Prints a status message to the console.
        """
        if self.copy_buffer is None:
            print("No copied selection to paste.")
            return
        x0, y0 = grid_pos
        self.save_state()
        for (x, y), color in self.copy_buffer.items():
            target_x = x0 + x
            target_y = y0 + y
            if 0 <= target_x < GRID_SIZE and 0 <= target_y < GRID_SIZE:
                self.sprites[self.current_sprite].frame.set_at((target_x, target_y), color)
        print("Selection pasted.")

    def mirror_selection(self):
        """
        Mirror the copied selection horizontally.

        This method mirrors the copied selection horizontally. It provides user feedback.

        Returns:
            None

        Side effects:
            - Modifies the copy_buffer attribute.
            - Prints a status message to the console.
        """
        if self.copy_buffer is None:
            print("No copied selection to mirror.")
            return
        width = max(x for x, y in self.copy_buffer.keys()) + 1
        mirrored_buffer = { (width - 1 - x, y): color for (x, y), color in self.copy_buffer.items() }
        self.copy_buffer = mirrored_buffer
        print("Selection mirrored horizontally.")

    def rotate_selection(self):
        """
        Rotate the copied selection 90 degrees clockwise.

        This method rotates the copied selection 90 degrees clockwise. It provides
        user feedback.

        Returns:
            None

        Side effects:
            - Modifies the copy_buffer attribute.
            - Prints a status message to the console.
        """
        if self.copy_buffer is None:
            print("No copied selection to rotate.")
            return
        width = max(x for x, y in self.copy_buffer.keys()) + 1
        height = max(y for x, y in self.copy_buffer.keys()) + 1
        rotated_buffer = { (y, width - 1 - x): color for (x, y), color in self.copy_buffer.items() }
        if width != height:
            print("Warning: Rotation may distort non-square selections.")
        self.copy_buffer = rotated_buffer
        print("Selection rotated 90 degrees clockwise.")

    def draw_on_background(self, pos):
        """
        Draw on the background at the specified position.

        This method accurately translates screen coordinates to background coordinates,
        taking into account zoom level and panning offsets.

        Args:
            pos (tuple): The screen position to draw at.

        Returns:
            None

        Side effects:
            - Modifies the current background data.
            - Prints a status message to the console.
        """
        x, y = pos
        if self.canvas_rect.collidepoint(x, y):
            color = self.get_current_color()
            # Adjust for zoom and panning
            rel_x = int((x - self.canvas_rect.x) / self.editor_zoom)
            rel_y = int((y - self.canvas_rect.y) / self.editor_zoom)
            
            # Ensure drawing within bounds
            if 0 <= rel_x < BACKGROUND_WIDTH and 0 <= rel_y < BACKGROUND_HEIGHT:
                self.save_state()
                # Correct brush size scaling with zoom
                scaled_brush_size = max(1, int(self.brush_size * self.editor_zoom))
                
                # Draw the brush centered on the cursor position
                pygame.draw.circle(self.current_background, color, (rel_x, rel_y), scaled_brush_size)
                
                print(f"Drew on background at ({rel_x}, {rel_y}) with color {color}")

        # Draw a cursor indicator on the screen
        pygame.draw.circle(screen, (255, 0, 0), pos, 2)  # Small red dot at cursor position

    def fill_background_position(self, pos):
        """
        Fill the background with the current color starting from the specified position.

        This method performs a flood fill operation on the background, starting from
        the specified position and filling with the current color. It provides user
        feedback.

        Args:
            pos (tuple): The screen position to start the fill operation at.

        Returns:
            None

        Side effects:
            - Modifies the current background data.
            - Prints a status message to the console.
        """
        x, y = pos
        rel_x = int((x - self.canvas_rect.x) * BACKGROUND_WIDTH / self.canvas_rect.width)
        rel_y = int((y - self.canvas_rect.y) * BACKGROUND_HEIGHT / self.canvas_rect.height)
        target_color = self.current_background.get_at((rel_x, rel_y))
        fill_color = self.get_current_color()

        if target_color == fill_color:
            return

        self.save_state()
        # Implement flood fill or other fill logic as needed
        # For simplicity, filling the entire background with the fill color
        self.current_background.fill(fill_color)
        print("Background filled with color.")

    def draw_on_background_position(self, grid_pos):
        """
        Draw on the background at the specified grid position.

        This method is a placeholder for drawing on the background at a specific
        grid position. It is not currently implemented.

        Args:
            grid_pos (tuple): The grid position to draw at.

        Returns:
            None
        """
        # Implement specific drawing based on grid position if needed
        # Placeholder for actual implementation
        pass

    def zoom_in(self):
        """
        Zoom in on the editor.

        This method increases the zoom level of the editor and updates the view.

        Returns:
            None

        Side effects:
            - Modifies the editor_zoom attribute.
            - Updates the background view.
            - Prints a status message to the console.
        """
        if self.edit_mode == 'background':
            old_zoom = self.editor_zoom
            self.editor_zoom = min(self.editor_zoom * 1.1, 3.0)
            self.adjust_zoom_center(old_zoom)
            self.update_background_view()
            print(f"Zoomed in to: {self.editor_zoom:.1f}x")

    def zoom_out(self):
        """
        Zoom out on the editor.

        This method decreases the zoom level of the editor and updates the view.

        Returns:
            None

        Side effects:
            - Modifies the editor_zoom attribute.
            - Updates the background view.
            - Prints a status message to the console.
        """
        if self.edit_mode == 'background':
            old_zoom = self.editor_zoom
            self.editor_zoom = max(self.editor_zoom / 1.1, 0.5)
            self.adjust_zoom_center(old_zoom)
            self.update_background_view()
            print(f"Zoomed out to: {self.editor_zoom:.1f}x")

    def adjust_zoom_center(self, old_zoom):
        """
        Adjust the center of the zoom to keep the view centered on the same point.

        Args:
            old_zoom (float): The previous zoom level.

        Returns:
            None

        Side effects:
            - Modifies the canvas_rect attribute to adjust the view center.
        """
        # Calculate the center of the view relative to the background
        view_center_x = self.canvas_rect.width / 2
        view_center_y = self.canvas_rect.height / 2
        
        # Calculate the new canvas size
        new_width = int(BACKGROUND_WIDTH * self.editor_zoom)
        new_height = int(BACKGROUND_HEIGHT * self.editor_zoom)
        
        # Calculate the new top-left corner to keep the center point the same
        new_left = int(view_center_x - (new_width / 2))
        new_top = int(view_center_y - (new_height / 2))
        
        # Update the canvas_rect
        self.canvas_rect = pygame.Rect(new_left, new_top, new_width, new_height)

    def update_background_view(self):
        """
        Update the background view based on the current zoom level and panning.

        This method adjusts the canvas_rect based on the current zoom level
        and ensures that the view stays within the background bounds.

        Returns:
            None

        Side effects:
            - Modifies the canvas_rect attribute.
        """
        # Ensure the view stays within the screen bounds
        self.canvas_rect.left = max(0, min(self.canvas_rect.left, WIDTH - self.canvas_rect.width))
        self.canvas_rect.top = max(0, min(self.canvas_rect.top, HEIGHT - self.canvas_rect.height))

    def pan_background(self, dx, dy):
        """
        Pan the background view.

        Args:
            dx (int): The amount to pan horizontally.
            dy (int): The amount to pan vertically.

        Returns:
            None

        Side effects:
            - Modifies the canvas_rect attribute to adjust the view position.
        """
        self.canvas_rect.x -= dx
        self.canvas_rect.y -= dy

        # Clamp the canvas_rect to stay within the background boundaries
        self.canvas_rect.x = max(WIDTH - self.canvas_rect.width, min(self.canvas_rect.x, 0))
        self.canvas_rect.y = max(HEIGHT - self.canvas_rect.height, min(self.canvas_rect.y, 0))

        print(f"Canvas position updated to ({self.canvas_rect.x}, {self.canvas_rect.y})")

    def update_brush_size(self, x):
        """
        Update the brush size based on the slider position.

        Args:
            x (int): The x-coordinate of the mouse position.

        Returns:
            None

        Side effects:
            - Modifies the brush_size attribute.
            - Prints a status message to the console.
        """
        relative_x = x - self.brush_slider.x
        relative_x = max(0, min(relative_x, self.brush_slider.width))
        self.brush_size = max(1, min(int((relative_x / self.brush_slider.width) * MAX_BRUSH_SIZE), MAX_BRUSH_SIZE))
        print(f"Brush size set to: {self.brush_size}")

    def draw_ui(self):
        """
        Draw the editor UI on the screen.

        This method draws the editor UI on the screen, including the sprites,
        background, buttons, palette, and other elements.

        Returns:
            None
        """
        screen.fill((200, 200, 200))

        if self.edit_mode == 'monster':
            # Draw sprites
            for sprite_name, sprite in self.sprites.items():
                sprite.draw(screen)

            # Draw monster info at the bottom
            monster = monsters[self.current_monster_index]
            info_text = [
                f"Name: {monster['name']}",
                f"Type: {monster['type']}",
                f"Max HP: {monster['max_hp']}",
                "Moves: " + ", ".join(monster['moves'])
            ]
            info_y = HEIGHT - 100
            for i, line in enumerate(info_text):
                text_surface = self.font.render(line, True, (0, 0, 0))
                screen.blit(text_surface, (50, info_y + i * 20))

        elif self.edit_mode == 'background':
            # Draw background with current zoom
            scaled_background = pygame.transform.scale(
                self.current_background,
                (self.canvas_rect.width, self.canvas_rect.height)
            )
            screen.blit(scaled_background, self.canvas_rect.topleft)
            pygame.draw.rect(screen, (255, 0, 0), self.canvas_rect, 2)  # Red bounding box

            # Draw brush preview
            mouse_pos = pygame.mouse.get_pos()
            if self.canvas_rect.collidepoint(mouse_pos):
                preview_size = max(1, int(self.brush_size))
                pygame.draw.circle(screen, (128, 128, 128, 128), mouse_pos, preview_size, 1)

        # Draw editing mode info at the bottom
        info_text = [
            f"Edit Mode: {self.edit_mode.capitalize()}",
            f"Current Sprite: {self.current_sprite}" if self.edit_mode == 'monster' else f"Background: {self.current_background_index}",
            f"Brush Size: {self.brush_size}",
            f"Eraser Mode: {'On' if self.eraser_mode else 'Off'}",
            f"Fill Mode: {'On' if self.fill_mode else 'Off'}",
            f"Selection Mode: {'On' if self.selection.selecting else 'Off'}",
            f"Zoom: {self.editor_zoom:.1f}x",
        ]
        info_y = HEIGHT - 160
        for i, line in enumerate(info_text):
            text_surface = self.font.render(line, True, (0, 0, 0))
            screen.blit(text_surface, (WIDTH - 250, info_y + i * 20))

        # Draw buttons
        for button in self.buttons:
            button.draw(screen)

        # Draw palette
        self.palette.draw(screen)

        self.selection.draw(screen)

        pygame.display.flip()

    def save_state(self):
        """
        Save the current state for undo/redo functionality.

        This method saves the current state of the sprites and background to the
        undo stack. It also clears the redo stack.

        Returns:
            None

        Side effects:
            - Modifies the undo_stack and redo_stack attributes.
            - Prints a status message to the console.
        """
        # Save current state for undo
        state = {
            'sprites': {name: sprite.frame.copy() for name, sprite in self.sprites.items()},
            'background': self.current_background.copy()
        }
        self.undo_stack.append(state)
        if len(self.undo_stack) > 20:  # Limit undo history
            self.undo_stack.pop(0)
        self.redo_stack.clear()
        print("State saved for undo.")

    def undo(self):
        """
        Revert the last editing action.

        This method restores the previous state of the sprites or background
        from the undo stack. It manages the undo/redo stacks to allow for
        multiple levels of undo and subsequent redo operations.

        Returns:
            None

        Side effects:
            - Modifies the current sprite or background data.
            - Updates the undo and redo stacks.
            - Prints a status message to the console.
        """
        if self.undo_stack:
            last_state = self.undo_stack.pop()
            # Save current state to redo stack
            current_state = {
                'sprites': {name: sprite.frame.copy() for name, sprite in self.sprites.items()},
                'background': self.current_background.copy()
            }
            self.redo_stack.append(current_state)
            # Restore last state
            for name, sprite in self.sprites.items():
                sprite.frame = last_state['sprites'][name].copy()
            self.current_background = last_state['background'].copy()
            print("Undo performed.")
        else:
            print("No actions to undo.")

    def redo(self):
        """
        Reapply a previously undone editing action.

        This method restores a state from the redo stack, effectively "redoing"
        an action that was undone. It manages the undo/redo stacks to maintain
        a consistent editing history.

        Returns:
            None

        Side effects:
            - Modifies the current sprite or background data.
            - Updates the undo and redo stacks.
            - Prints a status message to the console.
        """
        if self.redo_stack:
            next_state = self.redo_stack.pop()
            # Save current state to undo stack
            current_state = {
                'sprites': {name: sprite.frame.copy() for name, sprite in self.sprites.items()},
                'background': self.current_background.copy()
            }
            self.undo_stack.append(current_state)
            # Restore next state
            for name, sprite in self.sprites.items():
                sprite.frame = next_state['sprites'][name].copy()
            self.current_background = next_state['background'].copy()
            print("Redo performed.")
        else:
            print("No actions to redo.")

    def increase_brush_size(self):
        """
        Increase the brush size.

        This method increases the brush size by 1, up to the maximum brush size.
        It provides user feedback.

        Returns:
            None

        Side effects:
            - Modifies the brush_size attribute.
            - Prints a status message to the console.
        """
        self.brush_size = min(self.brush_size + 1, MAX_BRUSH_SIZE)
        print(f"Brush size increased to {self.brush_size}")

    def decrease_brush_size(self):
        """
        Decrease the brush size.

        This method decreases the brush size by 1, down to a minimum of 1.
        It provides user feedback.

        Returns:
            None

        Side effects:
            - Modifies the brush_size attribute.
            - Prints a status message to the console.
        """
        self.brush_size = max(self.brush_size - 1, 1)
        print(f"Brush size decreased to {self.brush_size}")

    def load_background(self, filename):
        """
        Load a background image and set it as the current background.
        """
        if os.path.exists(filename):
            self.current_background = pygame.image.load(filename).convert_alpha()
            self.current_background = pygame.transform.scale(self.current_background, (BACKGROUND_WIDTH, BACKGROUND_HEIGHT))
            self.editor_zoom = 1.0
            self.canvas_rect = pygame.Rect(0, 0, BACKGROUND_WIDTH, BACKGROUND_HEIGHT)
            self.center_canvas()
            print(f"Loaded background: {filename}")
        else:
            print(f"Background file not found: {filename}")

    def center_canvas(self):
        """
        Center the canvas on the screen.
        """
        self.canvas_rect.centerx = WIDTH // 2
        self.canvas_rect.centery = HEIGHT // 2

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
        start_x = WIDTH - button_width - padding
        start_y = 50

        all_buttons = [
            ("Save", self.save_current),
            ("Load", self.load_background),
            ("Clear", self.clear_current),
            ("Color Picker", self.open_color_picker),  # Re-added Color Picker button
            ("Eraser", self.toggle_eraser),
            ("Fill", self.toggle_fill),
            ("Select", self.toggle_selection_mode),
            ("Copy", self.copy_selection),
            ("Paste", self.paste_selection),
            ("Mirror", self.mirror_selection),
            ("Rotate", self.rotate_selection),
            ("Undo", self.undo),
            ("Redo", self.redo),
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

    def open_color_picker(self):
        """
        Open the color picker dialog.
        """
        color_code = colorchooser.askcolor(title="Choose Color")
        if color_code and color_code[0]:
            r, g, b = map(int, color_code[0])
            self.select_color((r, g, b, 255))

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
            print(f"Selected color: {color}")

    def draw_on_background(self, pos):
        """
        Draw on the background at the specified position.

        This method accurately translates screen coordinates to background coordinates,
        taking into account zoom level and panning offsets.

        Args:
            pos (tuple): The screen position to draw at.

        Returns:
            None

        Side effects:
            - Modifies the current background data.
            - Prints a status message to the console.
        """
        x, y = pos
        if self.canvas_rect.collidepoint(x, y):
            color = self.get_current_color()
            # Adjust for zoom and panning
            rel_x = int((x - self.canvas_rect.x) / self.editor_zoom)
            rel_y = int((y - self.canvas_rect.y) / self.editor_zoom)
            
            # Ensure drawing within bounds
            if 0 <= rel_x < BACKGROUND_WIDTH and 0 <= rel_y < BACKGROUND_HEIGHT:
                self.save_state()
                # Correct brush size scaling with zoom
                scaled_brush_size = max(1, int(self.brush_size * self.editor_zoom))
                
                # Draw the brush centered on the cursor position
                pygame.draw.circle(self.current_background, color, (rel_x, rel_y), scaled_brush_size)
                
                print(f"Drew on background at ({rel_x}, {rel_y}) with color {color}")

        # Draw a cursor indicator on the screen
        pygame.draw.circle(screen, (255, 0, 0), pos, 2)  # Small red dot at cursor position

# Main execution
editor = Editor()

def main():
    """
    The main function for the pixel art editor application.

    This function initializes the Pygame window, creates the Editor instance,
    and enters the main event loop. It handles user input events and updates
    the display.

    Returns:
        None
    """
    running = True
    while running:
        for event in pygame.event.get():
            if not editor.handle_event(event):
                running = False  # Exit main loop

        # Draw UI
        editor.draw_ui()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
