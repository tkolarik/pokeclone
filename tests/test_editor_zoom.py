import importlib
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import pygame



class TestEditorZoom(unittest.TestCase):
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

    def test_adjust_zoom_keeps_focus_point(self):
        editor = self.Editor.__new__(self.Editor)
        editor.edit_mode = "background"
        editor.canvas_rect = pygame.Rect(100, 100, 200, 200)
        editor.current_background = pygame.Surface((400, 400))
        editor.editor_zoom = 1.0
        editor.view_offset_x = 0
        editor.view_offset_y = 0

        focus_pos = (150, 150)
        world_x_before = (focus_pos[0] - editor.canvas_rect.x + editor.view_offset_x) / editor.editor_zoom
        world_y_before = (focus_pos[1] - editor.canvas_rect.y + editor.view_offset_y) / editor.editor_zoom

        editor.adjust_zoom(2.0, focus_pos=focus_pos)

        world_x_after = (focus_pos[0] - editor.canvas_rect.x + editor.view_offset_x) / editor.editor_zoom
        world_y_after = (focus_pos[1] - editor.canvas_rect.y + editor.view_offset_y) / editor.editor_zoom

        self.assertAlmostEqual(world_x_before, world_x_after, places=4)
        self.assertAlmostEqual(world_y_before, world_y_after, places=4)

    def test_set_reference_scale_clamps_and_rescales(self):
        editor = self.Editor.__new__(self.Editor)
        editor.ref_img_scale = 1.0
        editor._scale_reference_image = MagicMock()

        changed = editor.set_reference_scale(999.0)
        self.assertTrue(changed)
        self.assertEqual(editor.ref_img_scale, self.editor_module.config.EDITOR_REF_MAX_SCALE)
        editor._scale_reference_image.assert_called_once()

        editor._scale_reference_image.reset_mock()
        changed = editor.set_reference_scale(self.editor_module.config.EDITOR_REF_MAX_SCALE)
        self.assertFalse(changed)
        editor._scale_reference_image.assert_not_called()

    def test_adjust_reference_scale_supports_fractional_wheel_delta(self):
        editor = self.Editor.__new__(self.Editor)
        editor.reference_image = pygame.Surface((16, 16), pygame.SRCALPHA)
        editor.ref_img_scale = 1.0
        editor._scale_reference_image = MagicMock()

        changed = editor.adjust_reference_scale(0.5)
        self.assertTrue(changed)
        expected = self.editor_module.config.EDITOR_REF_WHEEL_ZOOM_BASE ** 0.5
        self.assertAlmostEqual(editor.ref_img_scale, expected, places=6)
        editor._scale_reference_image.assert_called_once()

        editor._scale_reference_image.reset_mock()
        previous_scale = editor.ref_img_scale
        changed = editor.adjust_reference_scale(-0.5, fine=True)
        self.assertTrue(changed)
        expected = previous_scale * (self.editor_module.config.EDITOR_REF_WHEEL_FINE_ZOOM_BASE ** -0.5)
        self.assertAlmostEqual(editor.ref_img_scale, expected, places=6)
        editor._scale_reference_image.assert_called_once()


if __name__ == "__main__":
    unittest.main()
