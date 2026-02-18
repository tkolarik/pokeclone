import io
import json
from pathlib import Path

import pytest

import server
from src.core import config
from src.editor.api_control import EditorApiController, EditorApiError


def _build_handler(path, payload_bytes=b"", content_length_header=None):
    handler = server.KanbanHandler.__new__(server.KanbanHandler)
    handler.path = path
    handler.headers = {}
    if content_length_header is not None:
        handler.headers["Content-Length"] = content_length_header
    handler.rfile = io.BytesIO(payload_bytes)
    responses = []
    handler._send_json = lambda code, payload: responses.append((code, payload))
    return handler, responses


def test_editor_state_route_returns_controller_payload(monkeypatch):
    class FakeController:
        def get_state(self):
            return {"state": "ok"}

    monkeypatch.setattr(server, "get_editor_api_controller", lambda: FakeController())

    handler, responses = _build_handler("/api/editor/state")
    handler.do_GET()

    assert responses == [(200, {"state": "ok"})]


def test_editor_action_route_returns_structured_client_error(monkeypatch):
    class FakeController:
        def execute_action(self, _payload):
            raise EditorApiError(400, "bad action payload")

    monkeypatch.setattr(server, "get_editor_api_controller", lambda: FakeController())
    body = json.dumps({"action": "draw_pixels"}).encode("utf-8")
    handler, responses = _build_handler(
        "/api/editor/action",
        payload_bytes=body,
        content_length_header=str(len(body)),
    )

    handler.do_POST()

    assert responses == [(400, {"error": "bad action payload"})]


@pytest.fixture
def controller(tmp_path, monkeypatch):
    # Keep editor API tests isolated from repository sprite assets.
    sprite_dir = tmp_path / "sprites"
    sprite_dir.mkdir()
    monkeypatch.setenv("POKECLONE_DISABLE_TK", "1")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setattr(config, "SPRITE_DIR", str(sprite_dir))
    monkeypatch.setattr(config, "CLIPBOARD_FAVORITES_FILE", str(tmp_path / "clipboard_favorites.json"))
    return EditorApiController()


def test_editor_api_requires_session_before_actions(controller):
    with pytest.raises(EditorApiError) as error:
        controller.execute_action({"action": "read_pixel", "x": 0, "y": 0})

    assert error.value.status_code == 409
    assert "POST /api/editor/session" in error.value.message


def test_editor_api_draw_read_undo_redo_cycle(controller):
    controller.start_session({})
    controller.execute_action({"action": "clear_canvas"})
    controller.execute_action({"action": "set_color", "color": [9, 120, 211, 255]})
    controller.execute_action({"action": "draw_pixels", "points": [{"x": 3, "y": 4}]})

    read_after_draw = controller.execute_action({"action": "read_pixel", "x": 3, "y": 4})
    assert read_after_draw["result"]["color"] == [9, 120, 211, 255]

    controller.execute_action({"action": "undo"})
    read_after_undo = controller.execute_action({"action": "read_pixel", "x": 3, "y": 4})
    assert read_after_undo["result"]["color"] == [0, 0, 0, 0]

    controller.execute_action({"action": "redo"})
    read_after_redo = controller.execute_action({"action": "read_pixel", "x": 3, "y": 4})
    assert read_after_redo["result"]["color"] == [9, 120, 211, 255]


def test_editor_api_selection_copy_and_paste(controller):
    controller.start_session({})
    controller.execute_action({"action": "clear_canvas"})
    controller.execute_action({"action": "set_color", "color": [255, 0, 0, 255]})
    controller.execute_action({"action": "draw_pixels", "points": [{"x": 1, "y": 1}]})
    controller.execute_action(
        {"action": "set_selection", "x": 1, "y": 1, "width": 1, "height": 1}
    )
    controller.execute_action({"action": "copy_selection"})
    controller.execute_action({"action": "paste_at", "x": 2, "y": 2})

    pasted = controller.execute_action({"action": "read_pixel", "x": 2, "y": 2})
    assert pasted["result"]["color"] == [255, 0, 0, 255]

    state = controller.get_state()
    assert state["selection"]["active"] is True
    assert state["clipboard"]["historySize"] >= 1


def test_editor_api_rejects_invalid_draw_coordinates(controller):
    controller.start_session({})

    with pytest.raises(EditorApiError) as error:
        controller.execute_action(
            {"action": "draw_pixels", "points": [{"x": -1, "y": 0}]}
        )

    assert error.value.status_code == 400
    assert "sprite bounds" in error.value.message


def test_editor_api_save_monster_sprites_writes_files(controller):
    controller.start_session({})
    state = controller.get_state()
    monster_name = state["monster"]["name"]
    assert monster_name

    controller.execute_action({"action": "save_monster_sprites"})

    front_path = Path(config.SPRITE_DIR) / f"{monster_name}_front.png"
    back_path = Path(config.SPRITE_DIR) / f"{monster_name}_back.png"
    assert front_path.exists()
    assert back_path.exists()
