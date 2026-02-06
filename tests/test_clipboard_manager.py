import os
import tempfile
import unittest

from src.editor.clipboard_manager import ClipboardManager


class TestClipboardManager(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.favorites_file = os.path.join(self.tmpdir.name, "favorites.json")
        self.manager = ClipboardManager(history_limit=3, favorites_path=self.favorites_file)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_push_and_cycle_history(self):
        a = {(0, 0): (1, 2, 3, 255)}
        b = {(1, 1): (4, 5, 6, 255)}
        self.manager.push(a)
        self.manager.push(b)

        active = self.manager.get_active_pixels()
        self.assertEqual(active, b)

        self.manager.cycle(-1)
        self.assertEqual(self.manager.get_active_pixels(), a)

    def test_push_deduplicates_same_pattern(self):
        pixels = {(0, 0): (1, 2, 3, 255)}
        self.manager.push(pixels)
        self.manager.push(pixels)
        self.assertEqual(len(self.manager.history), 1)

    def test_favorites_persist_round_trip(self):
        favorite_pixels = {(2, 3): (10, 20, 30, 255)}
        self.manager.push(favorite_pixels)
        self.manager.toggle_active_favorite()
        self.assertTrue(self.manager.save_favorites())

        second = ClipboardManager(history_limit=3, favorites_path=self.favorites_file)
        loaded = second.load_favorites()
        self.assertEqual(loaded, 1)
        self.assertEqual(second.get_active_pixels(), favorite_pixels)
        self.assertTrue(second.get_active_entry().favorite)


if __name__ == "__main__":
    unittest.main()
