import os
import sys
import unittest

import importlib
from unittest.mock import patch

import pygame

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core import config


class TestEditorSliderLayout(unittest.TestCase):
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

    def test_sliders_within_window_bounds(self):
        editor = self.Editor.__new__(self.Editor)
        editor.reference_alpha = 128
        editor.subject_alpha = 255
        editor._configure_sliders()

        self.assertLessEqual(editor.brush_slider.bottom, config.EDITOR_HEIGHT)
        self.assertLessEqual(editor.ref_alpha_slider_rect.bottom, config.EDITOR_HEIGHT)
        self.assertLessEqual(editor.subj_alpha_slider_rect.bottom, config.EDITOR_HEIGHT)
        self.assertGreaterEqual(editor.brush_slider.top, 0)
        self.assertGreaterEqual(editor.ref_alpha_slider_rect.top, 0)
        self.assertGreaterEqual(editor.subj_alpha_slider_rect.top, 0)


if __name__ == "__main__":
    unittest.main()
