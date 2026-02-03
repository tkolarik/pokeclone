import os
import unittest
from unittest.mock import MagicMock

import pygame

from src.editor.dialog_manager import DialogManager


class DummyEditor:
    def __init__(self):
        self._set_edit_mode_and_continue = MagicMock()
        self.backgrounds = []
        self.current_background_index = -1
        self.current_background = None
        self.buttons = []
        self.create_buttons = MagicMock(return_value=[])
        self.file_io = MagicMock()
        self.edit_mode = None
        self.undo_stack = []
        self.redo_stack = []
        self.reference_image = None
        self.reference_image_path = None
        self.scaled_reference_image = None
        self.apply_reference_alpha = MagicMock()
        self._scale_reference_image = MagicMock()
        self.load_tileset = MagicMock()
        self.font = pygame.font.Font(None, 12)


class TestDialogManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()
        pygame.font.init()

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()
        pygame.font.quit()

    def test_choose_edit_mode_sets_dialog_state(self):
        editor = DummyEditor()
        manager = DialogManager(editor)

        manager.choose_edit_mode()

        state = manager.state
        self.assertEqual(state.dialog_mode, "choose_edit_mode")
        self.assertEqual(state.dialog_prompt, "Choose Edit Mode:")
        self.assertEqual(len(state.dialog_options), 3)
        self.assertIs(state.dialog_callback, editor._set_edit_mode_and_continue)

    def test_handle_dialog_choice_calls_callback(self):
        editor = DummyEditor()
        manager = DialogManager(editor)
        called = MagicMock()
        manager.state.dialog_callback = called

        manager._handle_dialog_choice("value")

        called.assert_called_once_with("value")

    def test_handle_dialog_choice_cancel_resets(self):
        editor = DummyEditor()
        manager = DialogManager(editor)
        manager.state.dialog_mode = "input_text"
        manager.state.dialog_prompt = "prompt"
        manager.state.dialog_callback = MagicMock()

        manager._handle_dialog_choice(None)

        self.assertIsNone(manager.state.dialog_mode)
        self.assertEqual(manager.state.dialog_prompt, "")
        self.assertEqual(manager.state.dialog_options, [])


if __name__ == "__main__":
    unittest.main()
