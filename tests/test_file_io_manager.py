import unittest
from unittest.mock import MagicMock, patch

from src.editor.file_io import FileIOManager


class TestFileIOManager(unittest.TestCase):
    @patch("src.editor.file_io.pygame.image.load")
    @patch("src.editor.file_io.os.listdir")
    def test_load_backgrounds_filters_png(self, mock_listdir, mock_load):
        mock_listdir.return_value = ["a.png", "b.txt"]
        dummy_surface = MagicMock()
        mock_load.return_value.convert_alpha.return_value = dummy_surface

        manager = FileIOManager(editor=None)
        backgrounds = manager.load_backgrounds()

        self.assertEqual(backgrounds, [("a.png", dummy_surface)])
        mock_load.assert_called_once()

    @patch("src.editor.file_io.pygame.image.save")
    def test_save_background_returns_path(self, mock_save):
        manager = FileIOManager(editor=None)
        dummy_surface = MagicMock()
        with patch("src.editor.file_io.config.BACKGROUND_DIR", "/tmp"):
            saved_path = manager.save_background(dummy_surface, "test_bg")

        self.assertEqual(saved_path, "/tmp/test_bg.png")
        mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
