import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pygame

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)


class TestEditorDrawUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()
        with patch("pygame.display.set_mode", return_value=pygame.Surface((10, 10))):
            cls.editor_module = importlib.import_module("src.editor.pixle_art_editor")
        cls.Editor = cls.editor_module.Editor

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()

    def setUp(self):
        self.screen_patcher = patch.object(self.editor_module, "screen", new=MagicMock())
        self.mock_screen = self.screen_patcher.start()
        self.mock_screen.fill = MagicMock()

    def tearDown(self):
        self.screen_patcher.stop()

    def _make_editor(self):
        editor = self.Editor.__new__(self.Editor)
        editor.dialog_mode = None
        editor.edit_mode = None
        editor.draw_dialog = MagicMock()
        editor._draw_loading_state = MagicMock()
        editor._draw_monster_ui = MagicMock()
        editor._draw_background_ui = MagicMock()
        editor._draw_tile_ui = MagicMock()
        editor._draw_common_ui = MagicMock()
        return editor

    def test_draw_ui_dialog_mode_calls_draw_dialog_only(self):
        editor = self._make_editor()
        editor.dialog_mode = "choose_edit_mode"
        editor.edit_mode = "monster"

        editor.draw_ui()

        editor.draw_dialog.assert_called_once_with(self.mock_screen)
        editor._draw_monster_ui.assert_not_called()
        editor._draw_background_ui.assert_not_called()
        editor._draw_tile_ui.assert_not_called()
        editor._draw_common_ui.assert_not_called()

    def test_draw_ui_loading_state(self):
        editor = self._make_editor()
        editor.edit_mode = None

        editor.draw_ui()

        editor._draw_loading_state.assert_called_once_with(self.mock_screen)
        editor._draw_common_ui.assert_not_called()

    def test_draw_ui_monster_mode_calls_helpers(self):
        editor = self._make_editor()
        editor.edit_mode = "monster"

        editor.draw_ui()

        editor._draw_monster_ui.assert_called_once_with(self.mock_screen)
        editor._draw_common_ui.assert_called_once_with(self.mock_screen)
        editor._draw_background_ui.assert_not_called()
        editor._draw_tile_ui.assert_not_called()

    def test_draw_ui_background_mode_calls_helpers(self):
        editor = self._make_editor()
        editor.edit_mode = "background"

        editor.draw_ui()

        editor._draw_background_ui.assert_called_once_with(self.mock_screen)
        editor._draw_common_ui.assert_called_once_with(self.mock_screen)
        editor._draw_monster_ui.assert_not_called()
        editor._draw_tile_ui.assert_not_called()

    def test_draw_ui_tile_mode_calls_helpers(self):
        editor = self._make_editor()
        editor.edit_mode = "tile"

        editor.draw_ui()

        editor._draw_tile_ui.assert_called_once_with(self.mock_screen)
        editor._draw_common_ui.assert_called_once_with(self.mock_screen)
        editor._draw_monster_ui.assert_not_called()
        editor._draw_background_ui.assert_not_called()


if __name__ == '__main__':
    unittest.main()
