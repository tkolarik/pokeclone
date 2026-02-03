import unittest

from src.editor.editor_state import EditorState


class TestEditorState(unittest.TestCase):
    def test_setters_update_state(self):
        state = EditorState()
        state.set_color((1, 2, 3, 4))
        self.assertEqual(state.current_color, (1, 2, 3, 4))

        state.set_mode("select")
        self.assertEqual(state.mode, "select")

        state.set_edit_mode("monster")
        self.assertEqual(state.edit_mode, "monster")

    def test_reset_view(self):
        state = EditorState(editor_zoom=2.5, view_offset_x=10, view_offset_y=20, panning=True)
        state.reset_view()
        self.assertEqual(state.editor_zoom, 1.0)
        self.assertEqual(state.view_offset_x, 0)
        self.assertEqual(state.view_offset_y, 0)
        self.assertFalse(state.panning)


if __name__ == "__main__":
    unittest.main()
