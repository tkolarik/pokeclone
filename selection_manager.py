import pygame
import config

# Selection Tool Class
class SelectionTool:
    """"
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
    """"

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

    def end_selection(self, pos, sprite_editor):\n+        """
        End the current selection at the given position on the specified sprite editor.

        Args:\n+            pos (tuple): The ending screen position of the selection rectangle.
            sprite_editor (SpriteEditor): The sprite editor where the selection ended.\n+        """
        grid_pos = sprite_editor.get_grid_position(pos)\n+        if grid_pos:\n+            self.end_pos = grid_pos\n+            self.update_rect()\n+            self.active = True\n+            self.selecting = False\n+            print(f"Selection defined: {self.rect}")\n\n+    def update_rect(self):\n+        """
        Update the selection rectangle based on the start and end positions.\n+        """\
        if self.start_pos and self.end_pos:\n+            x1, y1 = self.start_pos\n+            x2, y2 = self.end_pos\n+            left = min(x1, x2)\n+            top = min(y1, y2)\n+            width = abs(x2 - x1) + 1\n+            height = abs(y2 - y1) + 1\n+            self.rect = pygame.Rect(left, top, width, height)\n+
    def draw(self, surface, sprite_position):\n+        """
        Draw the selection rectangle on a given surface, relative to the sprite's position.\n+
        Args:\n+            surface (pygame.Surface): The surface on which to draw the selection.\n+            sprite_position (tuple): The screen coordinates (x, y) of the top-left corner of the sprite editor.\n+        """
        # Draw selection rectangle while selecting (mouse down) or when selection is active\n+        if (self.selecting and self.start_pos and self.end_pos) or self.active:\n+            x0, y0 = sprite_position\n+            selection_surface = pygame.Surface((self.rect.width * config.EDITOR_PIXEL_SIZE, self.rect.height * config.EDITOR_PIXEL_SIZE), pygame.SRCALPHA)\n+            selection_surface.fill(config.SELECTION_FILL_COLOR)  # Semi-transparent blue\n+            pygame.draw.rect(selection_surface, config.BLUE, selection_surface.get_rect(), 2)\n+            surface.blit(selection_surface, (x0 + self.rect.x * config.EDITOR_PIXEL_SIZE, y0 + self.rect.y * config.EDITOR_PIXEL_SIZE))\n+
    def get_selected_pixels(self, sprite_editor):\n+        """ Get the pixels within the selection rectangle (coords relative to 32x32 grid). """
        if not sprite_editor or not self.active:\n+            return {}\n+
        pixels = {}\n+        # self.rect is relative to the visual grid (0-31 range)\n+        # Native frame is also 32x32, so coords match directly\n+        for x in range(self.rect.width):\n+            for y in range(self.rect.height):\n+                grid_x = self.rect.x + x\n+                grid_y = self.rect.y + y\n+                # Check bounds against native resolution (32x32)\n+                if 0 <= grid_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= grid_y < config.NATIVE_SPRITE_RESOLUTION[1]:\n+                    color = sprite_editor.get_pixel_color((grid_x, grid_y))\n+                    if color is not None:\n+                        pixels[(x, y)] = color # Store relative to selection top-left\n+        return pixels\n+
    def apply_paste(self, sprite_editor, top_left_grid_pos, copy_buffer):\n+        """Pastes the copy_buffer onto the sprite_editor frame."""
        if not copy_buffer or not sprite_editor:\n+            return\n+
        start_x, start_y = top_left_grid_pos\n+        for (rel_x, rel_y), color in copy_buffer.items():\n+            abs_x = start_x + rel_x\n+            abs_y = start_y + rel_y\n+            # Check bounds before attempting to draw\n+            if 0 <= abs_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= abs_y < config.NATIVE_SPRITE_RESOLUTION[1]:\n+                # Only paste non-transparent pixels.\n+                if color[3] > 0:\n+                    sprite_editor.draw_pixel((abs_x, abs_y), color)
import pygame
import config

# Selection Tool Class
class SelectionTool:
    """"
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
    """"

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
            self.end_pos = grid_pos\n+            self.update_rect()
            print(f"Selection updated to: {self.end_pos}")

    def end_selection(self, pos, sprite_editor):\n+        """
        End the current selection at the given position on the specified sprite editor.

        Args:\n+            pos (tuple): The ending screen position of the selection rectangle.
            sprite_editor (SpriteEditor): The sprite editor where the selection ended.\n+        """
        grid_pos = sprite_editor.get_grid_position(pos)\n+        if grid_pos:\n+            self.end_pos = grid_pos\n+            self.update_rect()\n+            self.active = True\n+            self.selecting = False\n+            print(f"Selection defined: {self.rect}")\n\n+    def update_rect(self):\n+        """
        Update the selection rectangle based on the start and end positions.\n+        """\
        if self.start_pos and self.end_pos:\n+            x1, y1 = self.start_pos\n+            x2, y2 = self.end_pos\n+            left = min(x1, x2)\n+            top = min(y1, y2)\n+            width = abs(x2 - x1) + 1\n+            height = abs(y2 - y1) + 1\n+            self.rect = pygame.Rect(left, top, width, height)\n+
    def draw(self, surface, sprite_position):\n+        """
        Draw the selection rectangle on a given surface, relative to the sprite's position.\n+
        Args:\n+            surface (pygame.Surface): The surface on which to draw the selection.\n+            sprite_position (tuple): The screen coordinates (x, y) of the top-left corner of the sprite editor.
        """
        # Draw selection rectangle while selecting (mouse down) or when selection is active\n+        if (self.selecting and self.start_pos and self.end_pos) or self.active:\n+            x0, y0 = sprite_position\n+            selection_surface = pygame.Surface((self.rect.width * config.EDITOR_PIXEL_SIZE, self.rect.height * config.EDITOR_PIXEL_SIZE), pygame.SRCALPHA)\n+            selection_surface.fill(config.SELECTION_FILL_COLOR)  # Semi-transparent blue\n+            pygame.draw.rect(selection_surface, config.BLUE, selection_surface.get_rect(), 2)\n+            surface.blit(selection_surface, (x0 + self.rect.x * config.EDITOR_PIXEL_SIZE, y0 + self.rect.y * config.EDITOR_PIXEL_SIZE))\n+
    def get_selected_pixels(self, sprite_editor):\n+        """ Get the pixels within the selection rectangle (coords relative to 32x32 grid). """
        if not sprite_editor or not self.active:\n+            return {}\n+
        pixels = {}\n+        # self.rect is relative to the visual grid (0-31 range)\n+        # Native frame is also 32x32, so coords match directly\n+        for x in range(self.rect.width):\n+            for y in range(self.rect.height):\n+                grid_x = self.rect.x + x\n+                grid_y = self.rect.y + y\n+                # Check bounds against native resolution (32x32)\n+                if 0 <= grid_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= grid_y < config.NATIVE_SPRITE_RESOLUTION[1]:\n+                    color = sprite_editor.get_pixel_color((grid_x, grid_y))\n+                    if color is not None:\n+                        pixels[(x, y)] = color # Store relative to selection top-left\n+        return pixels\n+
    def apply_paste(self, sprite_editor, top_left_grid_pos, copy_buffer):\n+        """Pastes the copy_buffer onto the sprite_editor frame."""
        if not copy_buffer or not sprite_editor:\n+            return\n+
        start_x, start_y = top_left_grid_pos\n+        for (rel_x, rel_y), color in copy_buffer.items():\n+            abs_x = start_x + rel_x\n+            abs_y = start_y + rel_y\n+            # Check bounds before attempting to draw\n+            if 0 <= abs_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= abs_y < config.NATIVE_SPRITE_RESOLUTION[1]:\n+                # Only paste non-transparent pixels.\n+                if color[3] > 0:\n+                    sprite_editor.draw_pixel((abs_x, abs_y), color)
