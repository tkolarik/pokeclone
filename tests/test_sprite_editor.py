import unittest
import pygame
import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Now import the necessary modules
import config
from sprite_editor import SpriteEditor

class TestSpriteEditor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize Pygame minimally if needed for Surface creation
        # We might be able to avoid full pygame.init()
        # pygame.display.init() # <<< REMOVE THIS LINE
        pass # Keep setUpClass structure if needed later

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        # Create a SpriteEditor instance for each test
        # Position doesn't really matter for these unit tests
        self.sprite_editor = SpriteEditor(position=(0, 0), name="test", sprite_dir="./temp_test_sprites")
        # Ensure the temp dir exists if needed for save/load tests later
        # os.makedirs("./temp_test_sprites", exist_ok=True)

    # def tearDown(self):
        # Clean up temp files/dirs if save/load tests are added
        # import shutil
        # if os.path.exists("./temp_test_sprites"):
        #     shutil.rmtree("./temp_test_sprites")

    def test_initialization(self):
        """Test if the SpriteEditor initializes correctly."""
        self.assertEqual(self.sprite_editor.frame.get_size(), config.NATIVE_SPRITE_RESOLUTION, "Frame size should match native resolution")
        # Check if it's transparent initially
        initial_color = self.sprite_editor.frame.get_at((0, 0))
        self.assertEqual(initial_color, (*config.BLACK[:3], 0), "Initial frame should be transparent black")
        self.assertEqual(self.sprite_editor.display_width, config.EDITOR_GRID_SIZE * config.EDITOR_PIXEL_SIZE)
        self.assertEqual(self.sprite_editor.display_height, config.EDITOR_GRID_SIZE * config.EDITOR_PIXEL_SIZE)

    def test_draw_pixel_within_bounds(self):
        """Test drawing a single pixel within the frame boundaries."""
        test_pos = (10, 15)
        test_color = (255, 0, 0, 255) # Opaque Red
        self.sprite_editor.draw_pixel(test_pos, test_color)
        drawn_color = self.sprite_editor.frame.get_at(test_pos)
        self.assertEqual(drawn_color, test_color, "Pixel color should match the drawn color")

    def test_draw_pixel_outside_bounds(self):
        """Test attempting to draw a pixel outside the frame boundaries."""
        # Test outside X
        test_pos_x = (config.NATIVE_SPRITE_RESOLUTION[0], 5)
        # Test outside Y
        test_pos_y = (5, config.NATIVE_SPRITE_RESOLUTION[1])
        test_color = (0, 255, 0, 255) # Opaque Green

        # Get initial color at a known valid position to check against later
        initial_color_check = self.sprite_editor.frame.get_at((0, 0))

        # Try drawing outside bounds - should have no effect
        self.sprite_editor.draw_pixel(test_pos_x, test_color)
        self.sprite_editor.draw_pixel(test_pos_y, test_color)

        # Check if a known valid pixel remained unchanged
        current_color_check = self.sprite_editor.frame.get_at((0, 0))
        self.assertEqual(current_color_check, initial_color_check, "Drawing outside bounds should not change pixels within bounds")
        # Pygame's set_at outside bounds raises IndexError, SpriteEditor handles this check
        # We are implicitly testing that no error is raised

    def test_get_pixel_color_within_bounds(self):
        """Test getting the color of a pixel within bounds."""
        test_pos = (5, 5)
        test_color = (0, 0, 255, 255) # Opaque Blue
        self.sprite_editor.draw_pixel(test_pos, test_color)
        retrieved_color = self.sprite_editor.get_pixel_color(test_pos)
        self.assertEqual(retrieved_color, test_color, "Retrieved color should match drawn color")

    def test_get_pixel_color_transparent(self):
        """Test getting the color of an un-drawn (transparent) pixel."""
        test_pos = (1, 1) # Assume this hasn't been drawn on
        retrieved_color = self.sprite_editor.get_pixel_color(test_pos)
        expected_transparent = (*config.BLACK[:3], 0)
        self.assertEqual(retrieved_color, expected_transparent, "Un-drawn pixel should be transparent black")

    def test_get_pixel_color_outside_bounds(self):
        """Test getting the color of a pixel outside bounds."""
        # Test outside X
        retrieved_color_x = self.sprite_editor.get_pixel_color((config.NATIVE_SPRITE_RESOLUTION[0], 5))
        # Test outside Y
        retrieved_color_y = self.sprite_editor.get_pixel_color((5, config.NATIVE_SPRITE_RESOLUTION[1]))
        self.assertIsNone(retrieved_color_x, "Getting color outside X bounds should return None")
        self.assertIsNone(retrieved_color_y, "Getting color outside Y bounds should return None")

    def test_get_grid_position_within_bounds(self):
        """Test converting screen coordinates within the visual editor bounds."""
        # Top-left corner pixel
        screen_pos_tl = (self.sprite_editor.position[0], self.sprite_editor.position[1])
        grid_pos_tl = self.sprite_editor.get_grid_position(screen_pos_tl)
        self.assertEqual(grid_pos_tl, (0, 0))

        # A position within the first pixel
        screen_pos_in_pixel = (self.sprite_editor.position[0] + config.EDITOR_PIXEL_SIZE // 2, self.sprite_editor.position[1] + config.EDITOR_PIXEL_SIZE // 2)
        grid_pos_in_pixel = self.sprite_editor.get_grid_position(screen_pos_in_pixel)
        self.assertEqual(grid_pos_in_pixel, (0, 0))

        # Center of the editor grid (approx)
        center_x_grid = config.EDITOR_GRID_SIZE // 2
        center_y_grid = config.EDITOR_GRID_SIZE // 2
        screen_pos_center = (self.sprite_editor.position[0] + center_x_grid * config.EDITOR_PIXEL_SIZE, 
                             self.sprite_editor.position[1] + center_y_grid * config.EDITOR_PIXEL_SIZE)
        grid_pos_center = self.sprite_editor.get_grid_position(screen_pos_center)
        self.assertEqual(grid_pos_center, (center_x_grid, center_y_grid))

        # Bottom-right corner pixel (test edge)
        br_x_grid = config.EDITOR_GRID_SIZE - 1
        br_y_grid = config.EDITOR_GRID_SIZE - 1
        screen_pos_br = (self.sprite_editor.position[0] + br_x_grid * config.EDITOR_PIXEL_SIZE, 
                           self.sprite_editor.position[1] + br_y_grid * config.EDITOR_PIXEL_SIZE)
        grid_pos_br = self.sprite_editor.get_grid_position(screen_pos_br)
        self.assertEqual(grid_pos_br, (br_x_grid, br_y_grid))

    def test_get_grid_position_outside_bounds(self):
        """Test converting screen coordinates outside the visual editor bounds."""
        # Just outside left
        screen_pos_left = (self.sprite_editor.position[0] - 1, self.sprite_editor.position[1])
        grid_pos_left = self.sprite_editor.get_grid_position(screen_pos_left)
        self.assertIsNone(grid_pos_left, "Position outside left bound should return None")

        # Just outside right
        screen_pos_right = (self.sprite_editor.position[0] + self.sprite_editor.display_width, self.sprite_editor.position[1])
        grid_pos_right = self.sprite_editor.get_grid_position(screen_pos_right)
        self.assertIsNone(grid_pos_right, "Position outside right bound should return None")

        # Just outside top
        screen_pos_top = (self.sprite_editor.position[0], self.sprite_editor.position[1] - 1)
        grid_pos_top = self.sprite_editor.get_grid_position(screen_pos_top)
        self.assertIsNone(grid_pos_top, "Position outside top bound should return None")

        # Just outside bottom
        screen_pos_bottom = (self.sprite_editor.position[0], self.sprite_editor.position[1] + self.sprite_editor.display_height)
        grid_pos_bottom = self.sprite_editor.get_grid_position(screen_pos_bottom)
        self.assertIsNone(grid_pos_bottom, "Position outside bottom bound should return None")

    # TODO: Add tests for load_sprite (requires mocking os.path.exists, pygame.image.load)
    # TODO: Add tests for save_sprite (requires mocking pygame.image.save, maybe os.makedirs)
    # TODO: Add tests for draw_background, draw_pixels, draw_highlight (verify calls/surface content?)

if __name__ == '__main__':
    unittest.main() 