class UndoRedoManager:
    def __init__(self, editor):
        self.editor = editor

    def save_state(self):
        """Save the current state of the active canvas to the undo stack."""
        current_state = None
        editor = self.editor

        if editor.edit_mode == 'monster':
            sprite = editor.sprites.get(editor.current_sprite)
            if sprite:
                current_state = ('monster', editor.current_sprite, sprite.frame.copy())
        elif editor.edit_mode == 'background':
            if editor.current_background:
                current_state = ('background', editor.current_background_index, editor.current_background.copy())
        elif editor.edit_mode == 'tile':
            if editor.asset_edit_target == 'tile' and editor.current_tile():
                current_state = ('tile', editor.current_tile().id, editor.tile_canvas.frame.copy(), editor.current_tile_frame_index)
            elif editor.asset_edit_target == 'npc' and editor.current_npc():
                current_state = (
                    'npc',
                    editor.current_npc().id,
                    editor.tile_canvas.frame.copy(),
                    (editor.current_npc_state, editor.current_npc_angle, editor.current_npc_frame_index),
                )

        if current_state:
            editor.undo_stack.append(current_state)
            editor.redo_stack.clear()

    def undo(self):
        """Revert to the previous state from the undo stack."""
        editor = self.editor
        if not editor.undo_stack:
            print("Nothing to undo.")
            return

        state_to_restore = editor.undo_stack.pop()
        if len(state_to_restore) == 4:
            state_type, state_id, state_surface, state_meta = state_to_restore
        else:
            state_type, state_id, state_surface = state_to_restore
            state_meta = None

        current_state_for_redo = None
        if editor.edit_mode == 'monster':
            sprite = editor.sprites.get(editor.current_sprite)
            if sprite:
                current_state_for_redo = ('monster', editor.current_sprite, sprite.frame.copy())
        elif editor.edit_mode == 'background':
            if editor.current_background:
                current_state_for_redo = ('background', editor.current_background_index, editor.current_background.copy())
        elif editor.edit_mode == 'tile':
            if editor.asset_edit_target == 'tile' and editor.current_tile():
                current_state_for_redo = ('tile', editor.current_tile().id, editor.tile_canvas.frame.copy(), editor.current_tile_frame_index)
            elif editor.asset_edit_target == 'npc' and editor.current_npc():
                current_state_for_redo = (
                    'npc',
                    editor.current_npc().id,
                    editor.tile_canvas.frame.copy(),
                    (editor.current_npc_state, editor.current_npc_angle, editor.current_npc_frame_index),
                )

        if current_state_for_redo:
            editor.redo_stack.append(current_state_for_redo)

        if state_type == 'monster':
            sprite = editor.sprites.get(state_id)
            if sprite:
                sprite.frame = state_surface.copy()
                editor.current_sprite = state_id
                editor.edit_mode = 'monster'
                print(f"Undid action for sprite: {state_id}")
            else:
                print(f"Undo failed: Could not find sprite editor '{state_id}' to restore state.")
                editor.undo_stack.append(state_to_restore)
                if editor.redo_stack:
                    editor.redo_stack.pop()
        elif state_type == 'background':
            editor.current_background = state_surface.copy()
            editor.current_background_index = state_id
            editor.edit_mode = 'background'
            print(f"Undid action for background index: {state_id}")
        elif state_type == 'tile':
            editor.edit_mode = 'tile'
            editor.asset_edit_target = 'tile'
            editor.tile_canvas.frame = state_surface.copy()
            if editor.tile_set:
                editor.select_tile_by_id(state_id)
            if state_meta is not None:
                editor.current_tile_frame_index = state_meta
            print(f"Undid action for tile: {state_id}")
        elif state_type == 'npc':
            editor.edit_mode = 'tile'
            editor.asset_edit_target = 'npc'
            editor.selected_npc_id = state_id
            if state_meta:
                editor.current_npc_state, editor.current_npc_angle, editor.current_npc_frame_index = state_meta
            editor.tile_canvas.frame = state_surface.copy()
            print(f"Undid action for npc: {state_id}")
        else:
            print("Undo failed: Unknown state type in stack.")
            editor.undo_stack.append(state_to_restore)
            if editor.redo_stack:
                editor.redo_stack.pop()

        editor.buttons = editor.create_buttons()

    def redo(self):
        """Reapply the last undone action from the redo stack."""
        editor = self.editor
        if not editor.redo_stack:
            print("Nothing to redo.")
            return

        state_to_restore = editor.redo_stack.pop()
        if len(state_to_restore) == 4:
            state_type, state_id, state_surface, state_meta = state_to_restore
        else:
            state_type, state_id, state_surface = state_to_restore
            state_meta = None

        current_state_for_undo = None
        if editor.edit_mode == 'monster':
            sprite = editor.sprites.get(editor.current_sprite)
            if sprite:
                current_state_for_undo = ('monster', editor.current_sprite, sprite.frame.copy())
        elif editor.edit_mode == 'background':
            if editor.current_background:
                current_state_for_undo = ('background', editor.current_background_index, editor.current_background.copy())
        elif editor.edit_mode == 'tile':
            if editor.asset_edit_target == 'tile' and editor.current_tile():
                current_state_for_undo = ('tile', editor.current_tile().id, editor.tile_canvas.frame.copy(), editor.current_tile_frame_index)
            elif editor.asset_edit_target == 'npc' and editor.current_npc():
                current_state_for_undo = (
                    'npc',
                    editor.current_npc().id,
                    editor.tile_canvas.frame.copy(),
                    (editor.current_npc_state, editor.current_npc_angle, editor.current_npc_frame_index),
                )

        if current_state_for_undo:
            editor.undo_stack.append(current_state_for_undo)

        if state_type == 'monster':
            sprite = editor.sprites.get(state_id)
            if sprite:
                sprite.frame = state_surface.copy()
                editor.current_sprite = state_id
                editor.edit_mode = 'monster'
                print(f"Redid action for sprite: {state_id}")
            else:
                print(f"Redo failed: Could not find sprite editor '{state_id}' to restore state.")
                editor.redo_stack.append(state_to_restore)
                if editor.undo_stack:
                    editor.undo_stack.pop()
        elif state_type == 'background':
            editor.current_background = state_surface.copy()
            editor.current_background_index = state_id
            editor.edit_mode = 'background'
            print(f"Redid action for background index: {state_id}")
        elif state_type == 'tile':
            editor.edit_mode = 'tile'
            editor.asset_edit_target = 'tile'
            editor.tile_canvas.frame = state_surface.copy()
            if editor.tile_set:
                editor.select_tile_by_id(state_id)
            if state_meta is not None:
                editor.current_tile_frame_index = state_meta
            print(f"Redid action for tile: {state_id}")
        elif state_type == 'npc':
            editor.edit_mode = 'tile'
            editor.asset_edit_target = 'npc'
            editor.selected_npc_id = state_id
            if state_meta:
                editor.current_npc_state, editor.current_npc_angle, editor.current_npc_frame_index = state_meta
            editor.tile_canvas.frame = state_surface.copy()
            print(f"Redid action for npc: {state_id}")
        else:
            print("Redo failed: Unknown state type in stack.")
            editor.redo_stack.append(state_to_restore)
            if editor.undo_stack:
                editor.undo_stack.pop()

        editor.buttons = editor.create_buttons()
