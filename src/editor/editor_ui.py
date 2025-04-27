import pygame
# from ..core import config # Relative import
from src.core import config # Absolute import
import colorsys # <<< Add import for palette generation

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

# Add other UI classes here later (Palette, SpriteEditor visualization part, etc.)

# --- Palette Generation --- 
def generate_palette():
    """
    Generate an enhanced color palette for the pixel art editor.

    This function creates a wide range of colors, including a variety of hues,
    saturations, and values, as well as grayscale colors. The resulting palette
    is used for painting and color selection in the editor.

    Returns:
        list: A list of RGBA color tuples representing the generated palette.
    """
    # Use constants from config if available, otherwise use defaults
    palette_hues_step = getattr(config, 'PALETTE_HUES_STEP', 30)
    palette_saturations = getattr(config, 'PALETTE_SATURATIONS', [50, 100])
    palette_values = getattr(config, 'PALETTE_VALUES', [50, 100])
    palette_grayscale_steps = getattr(config, 'PALETTE_GRAYSCALE_STEPS', 10)

    _PALETTE = [(0, 0, 0, 255)]  # Start with black
    # Generate a wide range of colors
    for h in range(0, 360, palette_hues_step):
        for s in palette_saturations:
            for v in palette_values:
                r, g, b = colorsys.hsv_to_rgb(h/360, s/100, v/100)
                _PALETTE.append((int(r*255), int(g*255), int(b*255), 255))
    # Add grayscale
    # Ensure at least 2 steps for division
    grayscale_denom = max(1, palette_grayscale_steps -1) 
    for i in range(palette_grayscale_steps):
        gray = int(255 * i / grayscale_denom)
        _PALETTE.append((gray, gray, gray, 255))
    return _PALETTE

PALETTE = generate_palette()

# --- Palette Class --- 
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
        draw(surface: pygame.Surface, current_color: tuple) -> None
        handle_click(pos: tuple, editor: Editor) -> None # Need editor reference for select_color
    """

    def __init__(self, position):
        """
        Initialize a new Palette instance.

        Args:
            position (tuple): The (x, y) position of the palette on the screen.
        """
        self.position = position  # (x, y) starting position on screen
        # Use constants from config for layout
        self.block_size = getattr(config, 'PALETTE_BLOCK_SIZE', 15)
        self.padding = getattr(config, 'PALETTE_PADDING', 2)
        self.gap = getattr(config, 'PALETTE_GAP', 5)
        self.font = pygame.font.Font(config.DEFAULT_FONT, config.PALETTE_FONT_SIZE)
        self.scroll_offset = 0
        self.colors_per_page = config.PALETTE_COLS * config.PALETTE_ROWS
        # Reference the PALETTE defined in this module
        self.total_pages = (len(PALETTE) + self.colors_per_page - 1) // self.colors_per_page 

    def draw(self, surface, current_color):
        """
        Draw the palette on a given surface.

        Args:
            surface (pygame.Surface): The surface on which to draw the palette.
            current_color (tuple): The currently selected color in the editor for highlighting.
        """
        x0, y0 = self.position
        current_page = self.scroll_offset
        start_index = current_page * self.colors_per_page
        end_index = start_index + self.colors_per_page
        # Reference the PALETTE defined in this module
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
                # Use constants from config for colors
                gray_light = getattr(config, 'GRAY_LIGHT', (211, 211, 211))
                indicator_color = getattr(config, 'TRANSPARENT_INDICATOR_COLOR', (255, 0, 0))
                pygame.draw.rect(surface, gray_light, rect)
                pygame.draw.line(surface, indicator_color, rect.topleft, rect.bottomright, 2)
                pygame.draw.line(surface, indicator_color, rect.topright, rect.bottomleft, 2)
            else:
                pygame.draw.rect(surface, color[:3], rect)

            # Use the passed current_color for comparison
            if color == current_color:
                 highlight_color = getattr(config, 'SELECTION_HIGHLIGHT_COLOR', (0, 255, 0))
                 pygame.draw.rect(surface, highlight_color, rect.inflate(4, 4), 2)

        # Palette label
        label_color = getattr(config, 'BLACK', (0,0,0))
        label = self.font.render("Palette", True, label_color)
        surface.blit(label, (x0, y0 - 30))

        # Scroll indicators
        if self.total_pages > 1:
            up_arrow = self.font.render("↑", True, label_color)
            down_arrow = self.font.render("↓", True, label_color)
            surface.blit(up_arrow, (x0 + config.PALETTE_COLS * (self.block_size + self.padding) + 10, y0))
            surface.blit(down_arrow, (x0 + config.PALETTE_COLS * (self.block_size + self.padding) + 10, y0 + config.PALETTE_ROWS * (self.block_size + self.padding) - 20))

    def handle_click(self, pos, editor):
        """
        Handle a mouse click event on the palette.

        This method checks if a color block was clicked and selects the corresponding
        color in the editor. It also handles scrolling through the palette using
        the scroll indicators.

        Args:
            pos (tuple): The (x, y) position of the mouse click.
            editor (Editor): The main editor instance to call select_color on.
        """
        x0, y0 = self.position
        x, y = pos
        # Check for scroll buttons
        scroll_area_x = x0 + config.PALETTE_COLS * (self.block_size + self.padding) + 10
        if x >= scroll_area_x and x <= scroll_area_x + 20:
            scroll_area_y_top = self.position[1]
            # Calculate approx height of scroll area - bit imprecise but should work
            scroll_area_height = config.PALETTE_ROWS * (self.block_size + self.padding)
            scroll_area_y_bottom = scroll_area_y_top + scroll_area_height

            if scroll_area_y_top <= y < scroll_area_y_top + scroll_area_height / 2: # Approx top half for UP
                # Up arrow
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
            elif scroll_area_y_top + scroll_area_height / 2 <= y < scroll_area_y_bottom: # Approx bottom half for DOWN
                # Down arrow
                if self.scroll_offset < self.total_pages - 1:
                    self.scroll_offset += 1
            return

        # Determine which color was clicked
        # Reference the PALETTE defined in this module
        start_index = self.scroll_offset * self.colors_per_page
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
            if rect.collidepoint(x, y):
                # Call the select_color method on the passed editor instance
                editor.select_color(color) 
                # --- Manually add this line below ---
                editor.paste_mode = False 
                # --- End of line to add ---
                if editor.mode == 'select':
                    editor.mode = 'draw'
                    editor.selection.selecting = False
                    editor.selection.active = False
                return 
