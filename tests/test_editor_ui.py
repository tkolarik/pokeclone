import unittest
from unittest.mock import MagicMock, patch
import pygame
import os
import sys


# Now import the necessary modules
from src.core import config
# Assuming editor_ui contains Button, Palette, PALETTE
from src.editor.editor_ui import Palette, PALETTE, Button # <<< Remove EditorUI
# Need Editor for type hinting and mocking structure
# from src.editor.pixle_art_editor import Editor 
# <<< Remove global initializer import >>>
# from src.editor.pixle_art_editor import _initialize_tkinter_globally 
# <<< Remove tkinter import >>>
# import tkinter
from src.editor.sprite_editor import SpriteEditor

class TestPalette(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Minimal Pygame setup needed for Font
        pygame.font.init()

    @classmethod
    def tearDownClass(cls):
        pygame.font.quit()

    def setUp(self):
        self.palette_pos = (50, 600)
        self.palette = Palette(self.palette_pos)
        # Mock the editor object that Palette.handle_click expects
        self.mock_editor = MagicMock()
        # We might need to mock specific editor attributes if handle_click uses them
        # For now, just mocking the select_color method is the primary need.
        # self.mock_editor.select_color = MagicMock()

    def test_initialization(self):
        """Test if the Palette initializes correctly."""
        self.assertEqual(self.palette.position, self.palette_pos)
        self.assertEqual(self.palette.scroll_offset, 0)
        self.assertTrue(hasattr(self.palette, 'font'))
        # Check if total_pages calculation seems reasonable
        expected_pages = (len(PALETTE) + self.palette.colors_per_page - 1) // self.palette.colors_per_page
        self.assertEqual(self.palette.total_pages, expected_pages)

    def test_handle_click_color_selection_first_page(self):
        """Test selecting a color block on the first page."""
        # Calculate the center position of the first color block (usually black)
        first_block_x = self.palette_pos[0] + self.palette.block_size // 2
        first_block_y = self.palette_pos[1] + self.palette.block_size // 2
        click_pos = (first_block_x, first_block_y)
        expected_color = PALETTE[0] # The first color

        self.palette.handle_click(click_pos, self.mock_editor)

        # Assert that the editor's select_color method was called once with the expected color
        self.mock_editor.select_color.assert_called_once_with(expected_color)

    def test_handle_click_scroll_down(self):
        """Test clicking the scroll down area."""
        initial_offset = self.palette.scroll_offset
        # Calculate a position within the approximate scroll down area
        scroll_x = self.palette_pos[0] + config.PALETTE_COLS * (self.palette.block_size + self.palette.padding) + 15
        scroll_y = self.palette_pos[1] + config.PALETTE_ROWS * (self.palette.block_size + self.palette.padding) - 10 # Near bottom
        click_pos = (scroll_x, scroll_y)

        # Only scroll if possible
        if self.palette.total_pages > 1:
            self.palette.handle_click(click_pos, self.mock_editor)
            self.assertEqual(self.palette.scroll_offset, initial_offset + 1)
            # Ensure select_color was NOT called
            self.mock_editor.select_color.assert_not_called()
        else:
            self.palette.handle_click(click_pos, self.mock_editor)
            self.assertEqual(self.palette.scroll_offset, initial_offset) # Should not change
            self.mock_editor.select_color.assert_not_called()

    def test_handle_click_scroll_up(self):
        """Test clicking the scroll up area."""
        # Force a scrolled state so scroll-up behavior is testable regardless of palette size.
        self.palette.scroll_offset = 1
        initial_offset = self.palette.scroll_offset
        # Calculate a position within the approximate scroll up area
        scroll_x = self.palette_pos[0] + config.PALETTE_COLS * (self.palette.block_size + self.palette.padding) + 15
        scroll_y = self.palette_pos[1] + 10 # Near top
        click_pos = (scroll_x, scroll_y)

        self.palette.handle_click(click_pos, self.mock_editor)
        self.assertEqual(self.palette.scroll_offset, initial_offset - 1)
        self.mock_editor.select_color.assert_not_called()

    def test_handle_click_outside(self):
        """Test clicking outside the palette area."""
        click_pos = (self.palette_pos[0] - 10, self.palette_pos[1] - 10) # Clearly outside
        initial_offset = self.palette.scroll_offset

        self.palette.handle_click(click_pos, self.mock_editor)

        # Assert offset didn't change and select_color wasn't called
        self.assertEqual(self.palette.scroll_offset, initial_offset)
        self.mock_editor.select_color.assert_not_called()

    def test_draw_runs(self):
        """Test that the draw method runs without errors."""
        # We need a surface to draw on
        mock_surface = MagicMock(spec=pygame.Surface)
        # Need to mock surface methods if draw uses them (e.g., blit, draw.rect)
        mock_surface.blit = MagicMock()
        mock_surface.fill = MagicMock() # Palette draw might fill background?
        # Mock pygame.draw directly if needed
        with patch('pygame.draw.rect') as mock_draw_rect, \
             patch('pygame.draw.line') as mock_draw_line:
            try:
                # Pass a sample current color
                self.palette.draw(mock_surface, PALETTE[0])
            except Exception as e:
                self.fail(f"Palette.draw() raised exception unexpectedly: {e}")
            # Optionally, assert that drawing functions were called
            mock_draw_rect.assert_called()
            # mock_draw_line might be called for transparent colors
            # mock_surface.blit.assert_called() # For labels/arrows


# --- Add TestEditorUI Class ---
# <<< REMOVE TestEditorUI Class >>>
# @patch('pygame.draw.rect')
# @patch('pygame.draw.line')
# @patch('pygame.transform.scale')
# class TestEditorUI(unittest.TestCase):
#     @classmethod
#     @patch('tkinter.Tk') # <<< Patch tkinter.Tk for the whole class setup
#     def setUpClass(cls, mock_tk):
#         ...
#     @classmethod
#     def tearDownClass(cls):
#         ...
#     def setUp(self):
#         ...
#     ...
# <<< End Removal >>>

if __name__ == '__main__':
    unittest.main() 
