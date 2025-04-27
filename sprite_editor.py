import pygame
import os
import config

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
                 # Use a placeholder color from config
                 placeholder_color = (*config.RED[:3], 100) if hasattr(config, 'RED') else (255, 0, 0, 100)
                 self.frame.fill(placeholder_color) # Semi-transparent red/magenta placeholder
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
                # Use checkerboard colors from config
                color1 = config.GRID_COLOR_1 if hasattr(config, 'GRID_COLOR_1') else (200, 200, 200)
                color2 = config.GRID_COLOR_2 if hasattr(config, 'GRID_COLOR_2') else (180, 180, 180)
                color = color1 if (x + y) % 2 == 0 else color2
                pygame.draw.rect(surface, color, rect)

    def draw_pixels(self, surface):
        """Draws the scaled sprite pixels onto the target surface."""
        # Scale the 32x32 native frame up to the display size (e.g., 480x480)
        # Use regular scale for pixel art sharpness
        scaled_display_frame = pygame.transform.scale(self.frame, (self.display_width, self.display_height))
        surface.blit(scaled_display_frame, self.position)

    def draw_highlight(self, surface, current_sprite_name):
        """Draws the highlight rectangle if this editor is active."""
        if current_sprite_name == self.name:
            highlight_rect = pygame.Rect(self.position[0] - 10, self.position[1] - 10,
                                         self.display_width + 20, self.display_height + 20)
            # Use highlight color from config
            highlight_color = config.SELECTION_HIGHLIGHT_COLOR if hasattr(config, 'SELECTION_HIGHLIGHT_COLOR') else (0, 255, 0)
            pygame.draw.rect(surface, highlight_color, highlight_rect, 3)

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