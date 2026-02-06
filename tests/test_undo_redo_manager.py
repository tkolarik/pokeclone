import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.editor.undo_redo_manager import UndoRedoManager


class TestUndoRedoManager(unittest.TestCase):
    def _make_editor(self):
        sprite = SimpleNamespace(frame="A")
        return SimpleNamespace(
            edit_mode="monster",
            current_sprite="front",
            sprites={"front": sprite},
            undo_stack=[],
            redo_stack=[],
            buttons=[],
            create_buttons=lambda: [],
            current_background=None,
            current_background_index=-1,
            asset_edit_target="tile",
            tile_canvas=SimpleNamespace(frame=None),
            current_tile=lambda: None,
            current_npc=lambda: None,
            current_npc_state="standing",
            current_npc_angle="south",
            current_npc_frame_index=0,
        )

    def test_save_state_pushes_snapshot(self):
        editor = self._make_editor()
        manager = UndoRedoManager(editor)
        with patch.object(manager, "_snapshot_surface", return_value={"surface": "A"}):
            manager.save_state()
        self.assertEqual(len(editor.undo_stack), 1)
        self.assertEqual(editor.undo_stack[0][0], "monster")

    def test_undo_and_redo_restore_frames(self):
        editor = self._make_editor()
        manager = UndoRedoManager(editor)

        with patch.object(manager, "_snapshot_surface", side_effect=lambda surface: {"surface": surface}):
            manager.save_state()  # snapshot of "A"
            editor.sprites["front"].frame = "B"
            with patch.object(manager, "_restore_surface", side_effect=lambda snapshot: snapshot["surface"]):
                manager.undo()
                self.assertEqual(editor.sprites["front"].frame, "A")
                self.assertEqual(len(editor.redo_stack), 1)

                manager.redo()
                self.assertEqual(editor.sprites["front"].frame, "B")
                self.assertEqual(len(editor.undo_stack), 1)


if __name__ == "__main__":
    unittest.main()
