import importlib
import os
import sys
import unittest
from unittest.mock import patch

import pygame

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.core import config


class TestButtonPanelScroll(unittest.TestCase):
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

    def _build_editor(self, edit_mode, asset_edit_target="tile"):
        editor = self.Editor.__new__(self.Editor)
        editor.edit_mode = edit_mode
        editor.asset_edit_target = asset_edit_target
        editor.brush_slider = pygame.Rect(0, config.EDITOR_HEIGHT - 40, 200, 20)
        editor.button_panel_rect = None
        editor.button_panel_content_height = 0
        editor.button_scroll_offset = 0
        editor.button_scroll_max = 0
        editor.button_scroll_step = 0
        editor._button_panel_context = None
        return editor

    def _assert_button_panel_visibility(self, editor):
        buttons = editor.create_buttons()
        editor.buttons = buttons
        panel_rect = editor.button_panel_rect
        self.assertIsNotNone(panel_rect)
        self.assertGreater(panel_rect.height, 0)
        self.assertGreaterEqual(panel_rect.top, 0)
        self.assertLessEqual(panel_rect.bottom, config.EDITOR_HEIGHT)
        self.assertLessEqual(panel_rect.right, config.EDITOR_WIDTH)
        self.assertTrue(panel_rect.contains(buttons[0].rect))
        editor._set_button_scroll_offset(buttons, editor.button_scroll_max)
        self.assertTrue(panel_rect.contains(buttons[-1].rect))

    def _assert_modes_visible_for_current_config(self):
        with self.subTest(mode="monster"):
            editor = self._build_editor("monster")
            self._assert_button_panel_visibility(editor)
        with self.subTest(mode="background"):
            editor = self._build_editor("background")
            self._assert_button_panel_visibility(editor)
        with self.subTest(mode="tile-tile"):
            editor = self._build_editor("tile", asset_edit_target="tile")
            self._assert_button_panel_visibility(editor)
        with self.subTest(mode="tile-npc"):
            editor = self._build_editor("tile", asset_edit_target="npc")
            self._assert_button_panel_visibility(editor)

    def test_button_panel_all_modes_visible_with_scroll(self):
        self._assert_modes_visible_for_current_config()

    def test_button_panel_layout_across_screen_sizes(self):
        cases = [
            (1300, 800),
            (1024, 700),
        ]
        for width, height in cases:
            with self.subTest(width=width, height=height):
                start_x = width - config.EDITOR_SIDE_BUTTON_WIDTH - config.EDITOR_SIDE_BUTTON_PADDING
                with patch.multiple(
                    config,
                    EDITOR_WIDTH=width,
                    EDITOR_HEIGHT=height,
                    EDITOR_SIDE_BUTTON_START_X=start_x,
                ):
                    self._assert_modes_visible_for_current_config()


if __name__ == '__main__':
    unittest.main()
