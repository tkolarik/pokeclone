import os
import sys
import unittest

import importlib
from unittest.mock import patch

import pygame


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

    def _assert_sliders_within_window_bounds(self, width, height, brush_x, brush_width, ref_x, ref_width):
        editor = self.Editor.__new__(self.Editor)
        editor.reference_alpha = 128
        editor.subject_alpha = 255

        with patch.multiple(
            config,
            EDITOR_WIDTH=width,
            EDITOR_HEIGHT=height,
            EDITOR_BRUSH_SLIDER_X=brush_x,
            EDITOR_BRUSH_SLIDER_WIDTH=brush_width,
            EDITOR_REF_SLIDER_X=ref_x,
            EDITOR_REF_SLIDER_WIDTH=ref_width,
        ):
            editor._configure_sliders()

        for rect in (
            editor.brush_slider,
            editor.ref_alpha_slider_rect,
            editor.subj_alpha_slider_rect,
            editor.ref_alpha_knob_rect,
            editor.subj_alpha_knob_rect,
        ):
            self.assertGreaterEqual(rect.left, 0)
            self.assertGreaterEqual(rect.top, 0)
            self.assertLessEqual(rect.right, width)
            self.assertLessEqual(rect.bottom, height)

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

    def test_slider_layout_for_multiple_screen_sizes(self):
        cases = [
            (1300, 800, 50, 200, 300, 150),
            (1024, 700, 24, 220, 280, 220),
        ]
        for width, height, brush_x, brush_width, ref_x, ref_width in cases:
            with self.subTest(width=width, height=height):
                self._assert_sliders_within_window_bounds(
                    width,
                    height,
                    brush_x,
                    brush_width,
                    ref_x,
                    ref_width,
                )


if __name__ == "__main__":
    unittest.main()
