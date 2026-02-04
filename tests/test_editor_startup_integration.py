import importlib
import os
import sys
import unittest
from unittest.mock import patch

import pygame


# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)


class TestEditorStartupIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()
        pygame.font.init()

        with patch("pygame.display.set_mode", return_value=pygame.Surface((10, 10))), \
             patch("pygame.display.set_caption", return_value=None):
            module = importlib.import_module("src.editor.pixle_art_editor")
            cls.editor_module = importlib.reload(module)

        cls.Editor = cls.editor_module.Editor

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()
        pygame.font.quit()

    def test_editor_startup_monster_mode(self):
        monsters = self.editor_module.load_monsters()
        self.assertIsInstance(monsters, list)
        self.assertTrue(monsters, "Expected monsters data to be loaded.")

        editor = self.Editor(monsters=monsters, skip_initial_dialog=True)
        editor._set_edit_mode_and_continue("monster")

        self.assertEqual(editor.edit_mode, "monster")
        self.assertEqual(editor.current_monster_index, 0)
        self.assertIn("front", editor.sprites)
        self.assertIn("back", editor.sprites)


if __name__ == "__main__":
    unittest.main()
