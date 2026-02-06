import zlib
from typing import Any, Optional, Tuple

import pygame

from src.core import config


class UndoRedoManager:
    """Stores compressed canvas snapshots to reduce undo/redo memory usage."""

    def __init__(self, editor):
        self.editor = editor

    def _snapshot_surface(self, surface: pygame.Surface) -> Optional[dict]:
        if surface is None:
            return None
        try:
            raw = pygame.image.tostring(surface, "RGBA")
            compressed = zlib.compress(raw, level=6)
            return {"size": surface.get_size(), "pixels": compressed}
        except (pygame.error, ValueError, TypeError, zlib.error) as e:
            print(f"Undo snapshot failed: {e}")
            return None

    def _restore_surface(self, snapshot: Any) -> Optional[pygame.Surface]:
        if snapshot is None:
            return None
        if isinstance(snapshot, pygame.Surface):
            return snapshot.copy()
        if not isinstance(snapshot, dict):
            return None
        size = snapshot.get("size")
        pixels = snapshot.get("pixels")
        if not size or not pixels:
            return None
        try:
            raw = zlib.decompress(pixels)
            return pygame.image.fromstring(raw, tuple(size), "RGBA")
        except (pygame.error, ValueError, TypeError, zlib.error) as e:
            print(f"Undo restore failed: {e}")
            return None

    def _capture_active_state(self) -> Optional[Tuple]:
        editor = self.editor
        snapshot = None

        if editor.edit_mode == 'monster':
            sprite = editor.sprites.get(editor.current_sprite)
            if sprite:
                snapshot = self._snapshot_surface(sprite.frame)
                if snapshot:
                    return ('monster', editor.current_sprite, snapshot)
        elif editor.edit_mode == 'background':
            if editor.current_background:
                snapshot = self._snapshot_surface(editor.current_background)
                if snapshot:
                    return ('background', editor.current_background_index, snapshot)
        elif editor.edit_mode == 'tile':
            if editor.asset_edit_target == 'tile' and editor.current_tile():
                snapshot = self._snapshot_surface(editor.tile_canvas.frame)
                if snapshot:
                    return ('tile', editor.current_tile().id, snapshot, editor.current_tile_frame_index)
            elif editor.asset_edit_target == 'npc' and editor.current_npc():
                snapshot = self._snapshot_surface(editor.tile_canvas.frame)
                if snapshot:
                    return (
                        'npc',
                        editor.current_npc().id,
                        snapshot,
                        (editor.current_npc_state, editor.current_npc_angle, editor.current_npc_frame_index),
                    )
        return None

    def _push_limited(self, stack, value):
        stack.append(value)
        if len(stack) > config.UNDO_REDO_MAX_STATES:
            del stack[0]

    def save_state(self):
        """Save the current state of the active canvas to the undo stack."""
        editor = self.editor
        current_state = self._capture_active_state()
        if current_state:
            self._push_limited(editor.undo_stack, current_state)
            editor.redo_stack.clear()

    def undo(self):
        """Revert to the previous state from the undo stack."""
        editor = self.editor
        if not editor.undo_stack:
            print("Nothing to undo.")
            return

        state_to_restore = editor.undo_stack.pop()
        if len(state_to_restore) == 4:
            state_type, state_id, state_snapshot, state_meta = state_to_restore
        else:
            state_type, state_id, state_snapshot = state_to_restore
            state_meta = None

        current_state_for_redo = self._capture_active_state()
        if current_state_for_redo:
            self._push_limited(editor.redo_stack, current_state_for_redo)

        restored_surface = self._restore_surface(state_snapshot)
        if restored_surface is None:
            print("Undo failed: could not restore surface snapshot.")
            return

        if state_type == 'monster':
            sprite = editor.sprites.get(state_id)
            if sprite:
                sprite.frame = restored_surface
                editor.current_sprite = state_id
                editor.edit_mode = 'monster'
                print(f"Undid action for sprite: {state_id}")
            else:
                print(f"Undo failed: Could not find sprite editor '{state_id}'.")
        elif state_type == 'background':
            editor.current_background = restored_surface
            editor.current_background_index = state_id
            editor.edit_mode = 'background'
            print(f"Undid action for background index: {state_id}")
        elif state_type == 'tile':
            editor.edit_mode = 'tile'
            editor.asset_edit_target = 'tile'
            editor.tile_canvas.frame = restored_surface
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
            editor.tile_canvas.frame = restored_surface
            print(f"Undid action for npc: {state_id}")
        else:
            print("Undo failed: Unknown state type.")
            return

        editor.buttons = editor.create_buttons()

    def redo(self):
        """Reapply the last undone action from the redo stack."""
        editor = self.editor
        if not editor.redo_stack:
            print("Nothing to redo.")
            return

        state_to_restore = editor.redo_stack.pop()
        if len(state_to_restore) == 4:
            state_type, state_id, state_snapshot, state_meta = state_to_restore
        else:
            state_type, state_id, state_snapshot = state_to_restore
            state_meta = None

        current_state_for_undo = self._capture_active_state()
        if current_state_for_undo:
            self._push_limited(editor.undo_stack, current_state_for_undo)

        restored_surface = self._restore_surface(state_snapshot)
        if restored_surface is None:
            print("Redo failed: could not restore surface snapshot.")
            return

        if state_type == 'monster':
            sprite = editor.sprites.get(state_id)
            if sprite:
                sprite.frame = restored_surface
                editor.current_sprite = state_id
                editor.edit_mode = 'monster'
                print(f"Redid action for sprite: {state_id}")
            else:
                print(f"Redo failed: Could not find sprite editor '{state_id}'.")
        elif state_type == 'background':
            editor.current_background = restored_surface
            editor.current_background_index = state_id
            editor.edit_mode = 'background'
            print(f"Redid action for background index: {state_id}")
        elif state_type == 'tile':
            editor.edit_mode = 'tile'
            editor.asset_edit_target = 'tile'
            editor.tile_canvas.frame = restored_surface
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
            editor.tile_canvas.frame = restored_surface
            print(f"Redid action for npc: {state_id}")
        else:
            print("Redo failed: Unknown state type.")
            return

        editor.buttons = editor.create_buttons()
