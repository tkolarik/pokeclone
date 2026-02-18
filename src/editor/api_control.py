"""Command-driven API control layer for the pixel art editor."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from src.core import config
from src.core.runtime_data_validation import (
    RuntimeDataValidationError,
    load_validated_monsters,
    load_validated_moves,
    load_validated_type_chart,
)


class EditorApiError(Exception):
    """Structured API error for editor-control operations."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = int(status_code)
        self.message = str(message)


FEATURE_MATRIX: Dict[str, Any] = {
    "scope": "Monster-mode direct editor control for autonomous agents.",
    "actions": [
        {
            "feature": "Session bootstrap (monster mode)",
            "apiAction": "POST /api/editor/session",
            "notes": "Creates/reset a deterministic editor session and loads monster assets.",
        },
        {
            "feature": "State inspection",
            "apiAction": "GET /api/editor/state",
            "notes": "Returns active tool/mode, selection, color, clipboard, history, and monster context.",
        },
        {
            "feature": "Tool selection (Draw/Eraser/Fill/Select/Paste/Eyedropper)",
            "apiAction": "set_tool",
            "notes": "Mapped via POST /api/editor/action.",
        },
        {
            "feature": "Sprite + monster navigation",
            "apiAction": "set_sprite, switch_sprite, select_monster, next_monster, previous_monster",
            "notes": "Supports both index-based and name-based monster selection.",
        },
        {
            "feature": "Pixel drawing and brush strokes",
            "apiAction": "draw_pixels",
            "notes": "Direct grid-coordinate drawing without UI event simulation.",
        },
        {
            "feature": "Flood fill",
            "apiAction": "fill_at",
            "notes": "Grid-coordinate fill on active sprite canvas.",
        },
        {
            "feature": "Selection rectangle operations",
            "apiAction": "set_selection, clear_selection, copy_selection, paste_at, mirror_selection, rotate_selection",
            "notes": "Supports copy/paste and transform workflows for the active sprite.",
        },
        {
            "feature": "Color and brush controls",
            "apiAction": "set_color, set_brush_size, read_pixel",
            "notes": "RGBA palette control and per-pixel read-back.",
        },
        {
            "feature": "Clipboard controls",
            "apiAction": "clipboard_prev, clipboard_next, clipboard_toggle_favorite",
            "notes": "Matches history/favorite clipboard UI semantics.",
        },
        {
            "feature": "History controls",
            "apiAction": "undo, redo",
            "notes": "Uses editor undo/redo snapshots.",
        },
        {
            "feature": "Monster sprite persistence",
            "apiAction": "save_monster_sprites",
            "notes": "Writes front/back sprites for current monster.",
        },
        {
            "feature": "Reference image controls",
            "apiAction": "load_reference_image, clear_reference_image, set_reference_alpha, set_subject_alpha, set_reference_scale, import_reference_image",
            "notes": "Direct file-path load and deterministic scaling/opacity/import controls.",
        },
    ],
    "intentionalLimitations": [
        "Background-mode workflows are not yet exposed through direct API commands.",
        "Tile/NPC mode workflows are not yet exposed through direct API commands.",
        "OS-native dialogs (Tk color/file pickers) are intentionally bypassed in API mode.",
    ],
}


def _load_monsters_for_api() -> List[Dict[str, Any]]:
    monsters_file = os.path.join(config.DATA_DIR, "monsters.json")
    moves_file = os.path.join(config.DATA_DIR, "moves.json")
    type_chart_file = os.path.join(config.DATA_DIR, "type_chart.json")

    try:
        moves = load_validated_moves(moves_file)
        type_chart = load_validated_type_chart(type_chart_file)
        monsters, _warnings = load_validated_monsters(
            monsters_file,
            strict_conflicts=False,
            known_moves={move["name"] for move in moves},
            known_types=set(type_chart.keys()),
        )
        return monsters
    except (FileNotFoundError, json.JSONDecodeError, RuntimeDataValidationError) as exc:
        raise EditorApiError(500, f"Failed to load monster data for editor API: {exc}") from exc


def _default_editor_factory() -> Any:
    # API mode is headless and non-interactive by design.
    os.environ.setdefault("POKECLONE_DISABLE_TK", "1")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    import pygame

    from src.editor.pixle_art_editor import Editor

    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()

    if pygame.display.get_surface() is None:
        try:
            pygame.display.set_mode((1, 1))
        except pygame.error as exc:
            raise EditorApiError(500, f"Failed to initialize headless editor display: {exc}") from exc

    monsters = _load_monsters_for_api()
    editor = Editor(monsters=monsters, skip_initial_dialog=True)
    editor._set_edit_mode_and_continue("monster")
    return editor


def _as_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EditorApiError(400, f"Field '{field}' must be a non-empty string.")
    return value.strip()


def _as_int(
    value: Any,
    field: str,
    *,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EditorApiError(400, f"Field '{field}' must be an integer.")
    if minimum is not None and value < minimum:
        raise EditorApiError(400, f"Field '{field}' must be >= {minimum}.")
    if maximum is not None and value > maximum:
        raise EditorApiError(400, f"Field '{field}' must be <= {maximum}.")
    return value


def _as_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise EditorApiError(400, f"Field '{field}' must be a boolean.")
    return value


def _as_rgba(value: Any, field: str = "color") -> Tuple[int, int, int, int]:
    if not isinstance(value, (list, tuple)) or len(value) not in (3, 4):
        raise EditorApiError(400, f"Field '{field}' must be an RGB or RGBA array.")

    channels: List[int] = []
    for index, item in enumerate(value):
        channels.append(_as_int(item, f"{field}[{index}]", minimum=0, maximum=255))
    if len(channels) == 3:
        channels.append(255)
    return (channels[0], channels[1], channels[2], channels[3])


def _as_point(value: Any, field: str = "point") -> Tuple[int, int]:
    if isinstance(value, Mapping):
        x = _as_int(value.get("x"), f"{field}.x")
        y = _as_int(value.get("y"), f"{field}.y")
        return x, y
    if isinstance(value, (list, tuple)) and len(value) == 2:
        x = _as_int(value[0], f"{field}[0]")
        y = _as_int(value[1], f"{field}[1]")
        return x, y
    raise EditorApiError(400, f"Field '{field}' must be an object with x/y or a two-item array.")


class EditorApiController:
    """Stateful command API for deterministic editor control."""

    def __init__(self, *, editor_factory: Optional[Callable[[], Any]] = None) -> None:
        self._editor_factory = editor_factory or _default_editor_factory
        self._editor: Optional[Any] = None
        self._session_id = 0
        self._lock = threading.RLock()
        self._actions: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "set_edit_mode": self._action_set_edit_mode,
            "select_monster": self._action_select_monster,
            "next_monster": self._action_next_monster,
            "previous_monster": self._action_previous_monster,
            "set_sprite": self._action_set_sprite,
            "switch_sprite": self._action_switch_sprite,
            "set_tool": self._action_set_tool,
            "set_color": self._action_set_color,
            "set_brush_size": self._action_set_brush_size,
            "draw_pixels": self._action_draw_pixels,
            "fill_at": self._action_fill_at,
            "set_selection": self._action_set_selection,
            "clear_selection": self._action_clear_selection,
            "copy_selection": self._action_copy_selection,
            "paste_at": self._action_paste_at,
            "mirror_selection": self._action_mirror_selection,
            "rotate_selection": self._action_rotate_selection,
            "clear_canvas": self._action_clear_canvas,
            "undo": self._action_undo,
            "redo": self._action_redo,
            "save_monster_sprites": self._action_save_monster_sprites,
            "load_reference_image": self._action_load_reference_image,
            "clear_reference_image": self._action_clear_reference_image,
            "set_reference_alpha": self._action_set_reference_alpha,
            "set_subject_alpha": self._action_set_subject_alpha,
            "set_reference_scale": self._action_set_reference_scale,
            "import_reference_image": self._action_import_reference_image,
            "clipboard_prev": self._action_clipboard_prev,
            "clipboard_next": self._action_clipboard_next,
            "clipboard_toggle_favorite": self._action_clipboard_toggle_favorite,
            "read_pixel": self._action_read_pixel,
        }

    def start_session(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = payload or {}
        if not isinstance(payload, dict):
            raise EditorApiError(400, "Session payload must be a JSON object.")

        with self._lock:
            self._editor = self._editor_factory()
            self._session_id += 1
            self._ensure_monster_mode()

            if "monsterName" in payload and "monsterIndex" in payload:
                raise EditorApiError(
                    400,
                    "Provide only one of 'monsterName' or 'monsterIndex' when starting a session.",
                )

            if "monsterName" in payload:
                self._select_monster_by_name(_as_non_empty_string(payload["monsterName"], "monsterName"))
            elif "monsterIndex" in payload:
                self._select_monster_by_index(_as_int(payload["monsterIndex"], "monsterIndex", minimum=0))

            if "sprite" in payload:
                self._set_sprite(_as_non_empty_string(payload["sprite"], "sprite"))

            return {
                "status": "started",
                "sessionId": self._session_id,
                "state": self._build_state(),
            }

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            self._require_editor_started()
            return self._build_state()

    def get_feature_matrix(self) -> Dict[str, Any]:
        return FEATURE_MATRIX

    def execute_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise EditorApiError(400, "Action payload must be a JSON object.")

        action = _as_non_empty_string(payload.get("action"), "action")
        handler = self._actions.get(action)
        if handler is None:
            supported = ", ".join(sorted(self._actions.keys()))
            raise EditorApiError(400, f"Unknown action '{action}'. Supported actions: {supported}")

        with self._lock:
            self._require_editor_started()
            result = handler(payload)
            return {
                "status": "ok",
                "sessionId": self._session_id,
                "action": action,
                "result": result,
                "state": self._build_state(),
            }

    def _require_editor_started(self) -> Any:
        if self._editor is None:
            raise EditorApiError(
                409,
                "Editor session is not initialized. Call POST /api/editor/session first.",
            )
        return self._editor

    def _require_monster_mode(self) -> Any:
        editor = self._require_editor_started()
        if editor.edit_mode != "monster":
            raise EditorApiError(
                409,
                "Current session is not in monster edit mode. Use action 'set_edit_mode' with mode='monster'.",
            )
        return editor

    def _ensure_monster_mode(self) -> None:
        editor = self._require_editor_started()
        if editor.edit_mode != "monster":
            editor._set_edit_mode_and_continue("monster")

    def _grid_bounds(self) -> Tuple[int, int]:
        return config.NATIVE_SPRITE_RESOLUTION

    def _validate_grid_point(self, x: int, y: int, *, field: str = "point") -> Tuple[int, int]:
        width, height = self._grid_bounds()
        if not (0 <= x < width and 0 <= y < height):
            raise EditorApiError(
                400,
                f"Field '{field}' must be within sprite bounds 0..{width - 1} x 0..{height - 1}.",
            )
        return x, y

    def _current_monster_name(self) -> Optional[str]:
        editor = self._require_editor_started()
        if not editor.monsters:
            return None
        if editor.current_monster_index < 0 or editor.current_monster_index >= len(editor.monsters):
            return None
        return editor.monsters[editor.current_monster_index].get("name")

    def _set_sprite(self, sprite_name: str) -> None:
        editor = self._require_monster_mode()
        if sprite_name not in {"front", "back"}:
            raise EditorApiError(400, "Field 'sprite' must be 'front' or 'back'.")
        editor.current_sprite = sprite_name
        editor.selection.active = False
        editor.selection.selecting = False

    def _select_monster_by_index(self, monster_index: int) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        if not isinstance(editor.monsters, list) or not editor.monsters:
            raise EditorApiError(409, "Monster list is empty; cannot select monster.")
        if monster_index >= len(editor.monsters):
            raise EditorApiError(
                400,
                f"monsterIndex out of range. Must be between 0 and {len(editor.monsters) - 1}.",
            )
        editor.current_monster_index = monster_index
        editor.load_monster()
        editor.selection.active = False
        editor.selection.selecting = False
        return {
            "monsterIndex": editor.current_monster_index,
            "monsterName": self._current_monster_name(),
        }

    def _select_monster_by_name(self, monster_name: str) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        if not isinstance(editor.monsters, list) or not editor.monsters:
            raise EditorApiError(409, "Monster list is empty; cannot select monster.")
        for index, monster in enumerate(editor.monsters):
            if monster.get("name") == monster_name:
                return self._select_monster_by_index(index)
        raise EditorApiError(404, f"Monster '{monster_name}' was not found in loaded monster data.")

    def _active_tool_label(self, editor: Any) -> str:
        active = editor.tool_manager.active_tool_name
        if active == "draw" and editor.eraser_mode:
            return "eraser"
        if editor.mode == "select":
            return "select"
        return active

    def _selection_payload(self, editor: Any) -> Dict[str, Any]:
        rect = editor.selection.rect
        return {
            "active": bool(editor.selection.active),
            "selecting": bool(editor.selection.selecting),
            "x": int(rect.x),
            "y": int(rect.y),
            "width": int(rect.width),
            "height": int(rect.height),
        }

    def _build_state(self) -> Dict[str, Any]:
        editor = self._require_editor_started()
        width, height = self._grid_bounds()
        active_entry = editor.clipboard.get_active_entry()
        return {
            "sessionId": self._session_id,
            "editMode": editor.edit_mode,
            "activeTool": self._active_tool_label(editor),
            "mode": editor.mode,
            "currentColor": [int(c) for c in editor.current_color],
            "brushSize": int(editor.brush_size),
            "sprite": editor.current_sprite,
            "monster": {
                "index": int(editor.current_monster_index),
                "name": self._current_monster_name(),
                "count": len(editor.monsters) if isinstance(editor.monsters, list) else 0,
            },
            "selection": self._selection_payload(editor),
            "canvas": {"width": width, "height": height},
            "clipboard": {
                "historySize": len(editor.clipboard.history),
                "activeIndex": editor.clipboard.active_index,
                "hasCopyBuffer": bool(editor.copy_buffer),
                "copyBufferPixels": len(editor.copy_buffer or {}),
                "activeFavorite": bool(active_entry.favorite) if active_entry else False,
            },
            "history": {
                "undoDepth": len(editor.undo_stack),
                "redoDepth": len(editor.redo_stack),
            },
            "reference": {
                "path": editor.reference_image_path,
                "alpha": int(editor.reference_alpha),
                "subjectAlpha": int(editor.subject_alpha),
                "scale": float(editor.ref_img_scale),
            },
        }

    def _action_set_edit_mode(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mode = _as_non_empty_string(payload.get("mode"), "mode")
        if mode != "monster":
            raise EditorApiError(
                400,
                "Only mode='monster' is supported by this API revision.",
            )
        self._ensure_monster_mode()
        return {"editMode": "monster"}

    def _action_select_monster(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if "monsterName" in payload and "monsterIndex" in payload:
            raise EditorApiError(400, "Provide only one of 'monsterName' or 'monsterIndex'.")
        if "monsterName" in payload:
            return self._select_monster_by_name(
                _as_non_empty_string(payload.get("monsterName"), "monsterName")
            )
        if "monsterIndex" in payload:
            return self._select_monster_by_index(
                _as_int(payload.get("monsterIndex"), "monsterIndex", minimum=0)
            )
        raise EditorApiError(400, "Action 'select_monster' requires 'monsterName' or 'monsterIndex'.")

    def _action_next_monster(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        before = editor.current_monster_index
        editor.next_monster()
        return {"fromIndex": before, "toIndex": editor.current_monster_index}

    def _action_previous_monster(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        before = editor.current_monster_index
        editor.previous_monster()
        return {"fromIndex": before, "toIndex": editor.current_monster_index}

    def _action_set_sprite(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        sprite_name = _as_non_empty_string(payload.get("sprite"), "sprite")
        self._set_sprite(sprite_name)
        return {"sprite": sprite_name}

    def _action_switch_sprite(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        before = editor.current_sprite
        editor.switch_sprite()
        return {"fromSprite": before, "toSprite": editor.current_sprite}

    def _action_set_tool(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        tool = _as_non_empty_string(payload.get("tool"), "tool").lower()
        if tool == "draw":
            editor._set_draw_mode(eraser=False)
        elif tool == "eraser":
            editor._set_draw_mode(eraser=True)
        elif tool == "fill":
            editor._set_fill_mode()
        elif tool == "select":
            editor._enter_selection_mode()
        elif tool == "paste":
            if not editor.copy_buffer:
                raise EditorApiError(409, "Paste tool requires a non-empty clipboard selection.")
            editor._set_paste_mode()
        elif tool == "eyedropper":
            editor.activate_eyedropper()
        else:
            raise EditorApiError(
                400,
                "Field 'tool' must be one of: draw, eraser, fill, select, paste, eyedropper.",
            )
        return {"tool": self._active_tool_label(editor)}

    def _action_set_color(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        color = _as_rgba(payload.get("color"), "color")
        editor.select_color(color)
        return {"color": [int(c) for c in editor.current_color]}

    def _action_set_brush_size(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        brush_size = _as_int(
            payload.get("brushSize"),
            "brushSize",
            minimum=1,
            maximum=config.MAX_BRUSH_SIZE,
        )
        editor.brush_size = brush_size
        return {"brushSize": brush_size}

    def _action_draw_pixels(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        points_raw = payload.get("points")
        if not isinstance(points_raw, list) or not points_raw:
            raise EditorApiError(400, "Action 'draw_pixels' requires a non-empty 'points' array.")

        points: List[Tuple[int, int]] = []
        for index, point_raw in enumerate(points_raw):
            x, y = _as_point(point_raw, f"points[{index}]")
            points.append(self._validate_grid_point(x, y, field=f"points[{index}]"))

        if "color" in payload:
            editor.select_color(_as_rgba(payload["color"], "color"))

        if "brushSize" in payload:
            editor.brush_size = _as_int(
                payload.get("brushSize"),
                "brushSize",
                minimum=1,
                maximum=config.MAX_BRUSH_SIZE,
            )

        if "eraser" in payload:
            eraser = _as_bool(payload.get("eraser"), "eraser")
            editor._set_draw_mode(eraser=eraser)
        else:
            editor._set_draw_mode(eraser=editor.eraser_mode)

        editor.save_state()
        sprite_editor = editor.sprites.get(editor.current_sprite)
        draw_tool = editor.tool_manager.tools["draw"]
        for point in points:
            draw_tool._draw_on_sprite(editor, sprite_editor, point)

        return {"drawnPoints": len(points), "sprite": editor.current_sprite}

    def _action_fill_at(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        x = _as_int(payload.get("x"), "x")
        y = _as_int(payload.get("y"), "y")
        self._validate_grid_point(x, y)

        if "color" in payload:
            editor.select_color(_as_rgba(payload["color"], "color"))

        editor._set_fill_mode()
        editor.save_state()
        sprite_editor = editor.sprites.get(editor.current_sprite)
        fill_tool = editor.tool_manager.tools["fill"]
        fill_tool._flood_fill_sprite(sprite_editor, (x, y), editor.current_color)
        return {"filledFrom": {"x": x, "y": y}}

    def _action_set_selection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        x = _as_int(payload.get("x"), "x", minimum=0)
        y = _as_int(payload.get("y"), "y", minimum=0)
        width = _as_int(payload.get("width"), "width", minimum=1)
        height = _as_int(payload.get("height"), "height", minimum=1)

        max_w, max_h = self._grid_bounds()
        if x + width > max_w or y + height > max_h:
            raise EditorApiError(
                400,
                f"Selection rectangle ({x}, {y}, {width}, {height}) exceeds sprite bounds {max_w}x{max_h}.",
            )

        editor.selection.start_pos = (x, y)
        editor.selection.end_pos = (x + width - 1, y + height - 1)
        editor.selection.update_rect()
        editor.selection.selecting = False
        editor.selection.active = True
        editor.mode = "select"
        return self._selection_payload(editor)

    def _action_clear_selection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        editor.selection.active = False
        editor.selection.selecting = False
        editor.selection.start_pos = None
        editor.selection.end_pos = None
        editor.selection.rect = editor.selection.rect.__class__(0, 0, 0, 0)
        editor.mode = "draw"
        return self._selection_payload(editor)

    def _action_copy_selection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        if not editor.selection.active:
            raise EditorApiError(409, "Copy requires an active selection.")
        before_size = len(editor.clipboard.history)
        editor.copy_selection()
        if not editor.copy_buffer:
            raise EditorApiError(409, "Copy did not produce clipboard data.")
        return {
            "copiedPixels": len(editor.copy_buffer),
            "historySizeBefore": before_size,
            "historySizeAfter": len(editor.clipboard.history),
        }

    def _action_paste_at(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        if not editor.copy_buffer:
            raise EditorApiError(409, "Paste requires a non-empty clipboard selection.")
        x = _as_int(payload.get("x"), "x")
        y = _as_int(payload.get("y"), "y")
        self._validate_grid_point(x, y)
        editor.save_state()
        paste_tool = editor.tool_manager.tools["paste"]
        sprite_editor = editor.sprites.get(editor.current_sprite)
        paste_tool._apply_paste_sprite(editor, sprite_editor, (x, y))
        return {"pasteTopLeft": {"x": x, "y": y}}

    def _action_mirror_selection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        if not editor.selection.active:
            raise EditorApiError(409, "Mirror requires an active selection.")
        editor.mirror_selection()
        return {"selectionMirrored": True}

    def _action_rotate_selection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        if not editor.selection.active:
            raise EditorApiError(409, "Rotate requires an active selection.")
        editor.rotate_selection()
        return {"selectionRotated": True}

    def _action_clear_canvas(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        editor.clear_current()
        return {"cleared": True, "sprite": editor.current_sprite}

    def _action_undo(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        before = len(editor.undo_stack)
        editor.undo()
        return {"undoDepthBefore": before, "undoDepthAfter": len(editor.undo_stack)}

    def _action_redo(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        before = len(editor.redo_stack)
        editor.redo()
        return {"redoDepthBefore": before, "redoDepthAfter": len(editor.redo_stack)}

    def _action_save_monster_sprites(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        monster_name = self._current_monster_name()
        if not monster_name:
            raise EditorApiError(409, "Cannot save sprites without a valid current monster.")
        editor.save_current_monster_sprites()
        return {"savedMonster": monster_name}

    def _action_load_reference_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        file_path = _as_non_empty_string(payload.get("path"), "path")
        if not os.path.exists(file_path):
            raise EditorApiError(404, f"Reference image not found: {file_path}")
        editor._load_selected_reference_callback(file_path)
        if editor.reference_image_path != file_path:
            raise EditorApiError(500, f"Reference image failed to load: {file_path}")
        return {"referencePath": editor.reference_image_path}

    def _action_clear_reference_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        editor.clear_reference_image()
        return {"referencePath": None}

    def _action_set_reference_alpha(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        alpha = _as_int(payload.get("alpha"), "alpha", minimum=0, maximum=255)
        editor.set_reference_alpha(alpha)
        return {"referenceAlpha": editor.reference_alpha}

    def _action_set_subject_alpha(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        alpha = _as_int(payload.get("alpha"), "alpha", minimum=0, maximum=255)
        editor.set_subject_alpha(alpha)
        return {"subjectAlpha": editor.subject_alpha}

    def _action_set_reference_scale(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        scale = payload.get("scale")
        if isinstance(scale, bool) or not isinstance(scale, (int, float)):
            raise EditorApiError(400, "Field 'scale' must be a numeric value.")
        editor.set_reference_scale(float(scale))
        return {"referenceScale": editor.ref_img_scale}

    def _action_import_reference_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        if editor.reference_image is None:
            raise EditorApiError(409, "Reference import requires a loaded reference image.")
        editor.import_reference_to_canvas()
        return {"imported": True}

    def _action_clipboard_prev(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        if not editor.clipboard.history:
            raise EditorApiError(409, "Clipboard history is empty.")
        editor.select_previous_clipboard_item()
        return {"activeIndex": editor.clipboard.active_index}

    def _action_clipboard_next(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        if not editor.clipboard.history:
            raise EditorApiError(409, "Clipboard history is empty.")
        editor.select_next_clipboard_item()
        return {"activeIndex": editor.clipboard.active_index}

    def _action_clipboard_toggle_favorite(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        del payload
        editor = self._require_monster_mode()
        if not editor.clipboard.history:
            raise EditorApiError(409, "Clipboard history is empty.")
        editor.toggle_current_clipboard_favorite()
        active = editor.clipboard.get_active_entry()
        return {"activeFavorite": bool(active.favorite) if active else False}

    def _action_read_pixel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        editor = self._require_monster_mode()
        x = _as_int(payload.get("x"), "x")
        y = _as_int(payload.get("y"), "y")
        self._validate_grid_point(x, y)

        sprite_name = payload.get("sprite")
        if sprite_name is None:
            sprite = editor.sprites.get(editor.current_sprite)
            sprite_name = editor.current_sprite
        else:
            sprite_name = _as_non_empty_string(sprite_name, "sprite")
            if sprite_name not in {"front", "back"}:
                raise EditorApiError(400, "Field 'sprite' must be 'front' or 'back'.")
            sprite = editor.sprites.get(sprite_name)

        color = sprite.get_pixel_color((x, y))
        if color is None:
            raise EditorApiError(500, f"Failed to read pixel ({x}, {y}).")
        return {
            "sprite": sprite_name,
            "x": x,
            "y": y,
            "color": [int(color[0]), int(color[1]), int(color[2]), int(color[3])],
        }
