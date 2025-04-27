import pygame
# from ..core import config # Relative import
from src.core import config # Absolute import

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
        get_selected_pixels(sprite_editor) -> dict
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

    def start(self, pos, sprite_editor):
        """
        Start a new selection at the given position on the specified sprite editor.

        Args:
            pos (tuple): The starting screen position of the selection rectangle.
            sprite_editor (SpriteEditor): The sprite editor where the selection is starting.
        """
        grid_pos = sprite_editor.get_grid_position(pos)
        if grid_pos:
            self.start_pos = grid_pos
            self.end_pos = grid_pos
            self.update_rect()
            print(f"Selection started at: {self.start_pos}")

    def update(self, pos, sprite_editor):
        """
        Update the selection rectangle based on the given position on the specified sprite editor.

        Args:
            pos (tuple): The current screen position of the mouse.
            sprite_editor (SpriteEditor): The sprite editor where the selection is active.
        """
        grid_pos = sprite_editor.get_grid_position(pos)
        if grid_pos:
            self.end_pos = grid_pos
            self.update_rect()
            print(f"Selection updated to: {self.end_pos}")

    def end_selection(self, pos, sprite_editor):
        """
        End the current selection at the given position on the specified sprite editor.

        Args:
            pos (tuple): The ending screen position of the selection rectangle.
            sprite_editor (SpriteEditor): The sprite editor where the selection ended.
        """
        grid_pos = sprite_editor.get_grid_position(pos)
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

    def draw(self, surface, sprite_position):
        """
        Draw the selection rectangle on a given surface, relative to the sprite's position.

        Args:
            surface (pygame.Surface): The surface on which to draw the selection.
            sprite_position (tuple): The screen coordinates (x, y) of the top-left corner of the sprite editor.
        """
        # Draw selection rectangle while selecting (mouse down) or when selection is active
        if (self.selecting and self.start_pos and self.end_pos) or self.active:
            x0, y0 = sprite_position
            selection_surface = pygame.Surface((self.rect.width * config.EDITOR_PIXEL_SIZE, self.rect.height * config.EDITOR_PIXEL_SIZE), pygame.SRCALPHA)
            selection_surface.fill(config.SELECTION_FILL_COLOR)  # Semi-transparent blue
            pygame.draw.rect(selection_surface, config.BLUE, selection_surface.get_rect(), 2)
            surface.blit(selection_surface, (x0 + self.rect.x * config.EDITOR_PIXEL_SIZE, y0 + self.rect.y * config.EDITOR_PIXEL_SIZE))

    def get_selected_pixels(self, sprite_editor):
        """ Get the pixels within the selection rectangle (coords relative to 32x32 grid). """
        if not sprite_editor or not self.active:
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

    def apply_paste(self, sprite_editor, top_left_grid_pos, copy_buffer):
        """Pastes the copy_buffer onto the sprite_editor frame."""
        if not copy_buffer or not sprite_editor:
            return

        start_x, start_y = top_left_grid_pos
        for (rel_x, rel_y), color in copy_buffer.items():
            abs_x = start_x + rel_x
            abs_y = start_y + rel_y
            # Check bounds before attempting to draw
            if 0 <= abs_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= abs_y < config.NATIVE_SPRITE_RESOLUTION[1]:
                # Only paste non-transparent pixels.
                if color[3] > 0:
                    sprite_editor.draw_pixel((abs_x, abs_y), color)
