import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pygame


from src.core import config


class TestEditorToolIndicator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()
        pygame.font.init()
        with patch("pygame.display.set_mode", return_value=pygame.Surface((10, 10))):
            cls.editor_module = importlib.import_module("src.editor.pixle_art_editor")
        cls.Editor = cls.editor_module.Editor

    @classmethod
    def tearDownClass(cls):
        pygame.font.quit()
        pygame.display.quit()

    def _build_editor(self):
        editor = self.Editor.__new__(self.Editor)
        editor.edit_mode = "monster"
        editor.asset_edit_target = "tile"
        editor.tool_manager = MagicMock()
        editor.eraser_mode = False
        editor.mode = "draw"
        editor.selection = MagicMock()
        editor.brush_slider = pygame.Rect(0, config.EDITOR_HEIGHT - 40, 200, 20)
        editor.button_panel_rect = None
        editor.button_panel_content_height = 0
        editor.button_scroll_offset = 0
        editor.button_scroll_max = 0
        editor.button_scroll_step = 0
        editor._button_panel_context = None
        return editor

    def test_fill_button_active(self):
        editor = self._build_editor()
        editor.tool_manager.active_tool_name = "fill"
        buttons = editor.create_buttons()
        fill_button = next(button for button in buttons if button.text == "Fill")
        self.assertTrue(fill_button.is_active())

    def test_eraser_button_active(self):
        editor = self._build_editor()
        editor.tool_manager.active_tool_name = "draw"
        editor.eraser_mode = True
        buttons = editor.create_buttons()
        eraser_button = next(button for button in buttons if button.text == "Eraser")
        self.assertTrue(eraser_button.is_active())

    def test_select_button_active(self):
        editor = self._build_editor()
        editor.tool_manager.active_tool_name = "draw"
        editor.mode = "select"
        buttons = editor.create_buttons()
        select_button = next(button for button in buttons if button.text == "Select")
        self.assertTrue(select_button.is_active())


if __name__ == "__main__":
    unittest.main()
