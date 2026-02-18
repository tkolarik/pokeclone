import json
from pathlib import Path

import pytest
import pygame

from src.core import config
from src.editor.api_control import EditorApiController
from src.editor.file_io import load_monsters
from src.editor.pixle_art_editor import Editor
from src.mcp.monster_drawing_mcp import MonsterDrawingMcpServer


class FakeController:
    def __init__(self):
        self.calls = []

    def start_session(self, payload):
        self.calls.append(("start_session", payload))
        return {
            "status": "started",
            "sessionId": 1,
            "state": {"monster": {"name": "TestMon", "index": 0}},
        }

    def get_state(self):
        self.calls.append(("get_state", {}))
        return {"monster": {"name": "TestMon", "index": 0}}

    def execute_action(self, payload):
        self.calls.append(("execute_action", payload))
        return {
            "status": "ok",
            "action": payload.get("action"),
            "result": {"echo": payload},
            "state": {"monster": {"name": "TestMon", "index": 0}},
        }


def _rpc_request(request_id, method, params=None):
    payload = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        payload["params"] = params
    return payload


def _build_headless_editor():
    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if not pygame.display.get_init():
        pygame.display.init()
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((1, 1))
    monsters = load_monsters()
    editor = Editor(monsters=monsters, skip_initial_dialog=True)
    editor._set_edit_mode_and_continue("monster")
    return editor


def test_mcp_initialize_and_tools_list():
    server = MonsterDrawingMcpServer(controller=FakeController())

    init_response = server.handle_jsonrpc_message(_rpc_request(1, "initialize", {}))
    assert init_response["id"] == 1
    assert init_response["result"]["protocolVersion"]
    assert init_response["result"]["capabilities"]["tools"]["listChanged"] is False

    list_response = server.handle_jsonrpc_message(_rpc_request(2, "tools/list", {}))
    tools = list_response["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    assert "monster_session_start" in tool_names
    assert "monster_draw_pixels" in tool_names
    assert "monster_save_sprites" in tool_names


def test_mcp_tool_validation_returns_is_error():
    server = MonsterDrawingMcpServer(controller=FakeController())
    response = server.handle_jsonrpc_message(
        _rpc_request(
            3,
            "tools/call",
            {
                "name": "monster_set_color",
                "arguments": {"color": "not-an-array"},
            },
        )
    )

    assert response["id"] == 3
    result = response["result"]
    assert result["isError"] is True
    assert "Invalid arguments" in result["content"][0]["text"]


def test_mcp_draw_pixels_translates_to_editor_action_payload():
    controller = FakeController()
    server = MonsterDrawingMcpServer(controller=controller)

    response = server.handle_jsonrpc_message(
        _rpc_request(
            4,
            "tools/call",
            {
                "name": "monster_draw_pixels",
                "arguments": {
                    "points": [{"x": 2, "y": 3}],
                    "color": [12, 34, 56, 255],
                    "brushSize": 1,
                },
            },
        )
    )

    assert response["result"]["isError"] is False
    assert controller.calls[-1][0] == "execute_action"
    assert controller.calls[-1][1] == {
        "action": "draw_pixels",
        "points": [{"x": 2, "y": 3}],
        "color": [12, 34, 56, 255],
        "brushSize": 1,
    }


def test_mcp_end_to_end_monster_drawing_flow(tmp_path, monkeypatch):
    sprite_dir = tmp_path / "sprites"
    sprite_dir.mkdir()
    monkeypatch.setenv("POKECLONE_DISABLE_TK", "1")
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setattr(config, "SPRITE_DIR", str(sprite_dir))
    monkeypatch.setattr(
        config,
        "CLIPBOARD_FAVORITES_FILE",
        str(tmp_path / "clipboard_favorites.json"),
    )

    server = MonsterDrawingMcpServer(
        controller=EditorApiController(editor_factory=_build_headless_editor)
    )

    start_response = server.handle_jsonrpc_message(
        _rpc_request(
            10,
            "tools/call",
            {"name": "monster_session_start", "arguments": {}},
        )
    )
    assert start_response["result"]["isError"] is False, start_response

    set_color = server.handle_jsonrpc_message(
        _rpc_request(
            11,
            "tools/call",
            {
                "name": "monster_set_color",
                "arguments": {"color": [200, 30, 30, 255]},
            },
        )
    )
    assert set_color["result"]["isError"] is False

    draw_response = server.handle_jsonrpc_message(
        _rpc_request(
            12,
            "tools/call",
            {
                "name": "monster_draw_pixels",
                "arguments": {"points": [{"x": 0, "y": 0}, {"x": 1, "y": 0}]},
            },
        )
    )
    assert draw_response["result"]["isError"] is False

    save_response = server.handle_jsonrpc_message(
        _rpc_request(
            13,
            "tools/call",
            {"name": "monster_save_sprites", "arguments": {}},
        )
    )
    assert save_response["result"]["isError"] is False

    saved_monster = save_response["result"]["structuredContent"]["result"]["savedMonster"]
    assert saved_monster

    front = Path(config.SPRITE_DIR) / f"{saved_monster}_front.png"
    back = Path(config.SPRITE_DIR) / f"{saved_monster}_back.png"
    assert front.exists()
    assert back.exists()

    # Ensure the tool output is structured JSON text, suitable for agent loops.
    rendered_text = save_response["result"]["content"][0]["text"]
    assert json.loads(rendered_text)["result"]["savedMonster"] == saved_monster
