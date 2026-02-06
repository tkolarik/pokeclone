from src.overworld import map_editor
from src.overworld.map_editor import MapEditor
from src.overworld.state import MapData, MapLayer


def _build_map(map_id: str, width: int = 4, height: int = 4) -> MapData:
    return MapData(
        map_id=map_id,
        name=map_id,
        version="1.0.0",
        tile_size=16,
        dimensions=(width, height),
        tileset_id="basic_overworld",
        layers=[
            MapLayer(name="ground", tiles=[[None for _ in range(width)] for _ in range(height)]),
            MapLayer(name="overlay", tiles=[[None for _ in range(width)] for _ in range(height)]),
        ],
        connections=[],
        entities=[],
        triggers=[],
        overrides={},
    )


def _build_editor(current_map_id: str = "current") -> MapEditor:
    editor = MapEditor.__new__(MapEditor)
    editor.screen = object()
    editor.font = object()
    editor.tileset = None
    editor.tile_images = {}
    editor.status_message = ""
    editor.map = _build_map(current_map_id)
    return editor


def _set_prompt_sequence(monkeypatch, responses):
    values = iter(responses)

    def _fake_prompt_text(screen, font, message, default=""):
        return next(values)

    monkeypatch.setattr(map_editor, "prompt_text", _fake_prompt_text)


def test_connection_dialog_rejects_non_numeric_spawn(monkeypatch):
    editor = _build_editor()
    original_map = editor.map
    saved_ids = []

    def _fake_save(self, path_or_id=None):
        saved_ids.append(self.id)
        return f"/tmp/{self.id}.json"

    monkeypatch.setattr(MapData, "save", _fake_save)
    monkeypatch.setattr(map_editor, "load_tileset_images", lambda tileset, tile_size: {})
    _set_prompt_sequence(
        monkeypatch,
        ["new_map", "4", "4", "edge", "north", "not-a-number"],
    )

    editor._new_map_dialog()

    assert editor.map.id == original_map.id
    assert original_map.connections == []
    assert saved_ids == []
    assert "Invalid numeric input for new map spawn x." in editor.status_message


def test_connection_dialog_rejects_empty_numeric_input(monkeypatch):
    editor = _build_editor()
    original_map = editor.map
    saved_ids = []

    def _fake_save(self, path_or_id=None):
        saved_ids.append(self.id)
        return f"/tmp/{self.id}.json"

    monkeypatch.setattr(MapData, "save", _fake_save)
    monkeypatch.setattr(map_editor, "load_tileset_images", lambda tileset, tile_size: {})
    _set_prompt_sequence(
        monkeypatch,
        ["new_map", "4", "4", "portal", ""],
    )

    editor._new_map_dialog()

    assert editor.map.id == original_map.id
    assert original_map.connections == []
    assert saved_ids == []
    assert "Invalid numeric input for portal x on current map." in editor.status_message


def test_connected_new_map_persists_both_maps(monkeypatch):
    editor = _build_editor()
    source_map = editor.map
    saved_ids = []

    def _fake_save(self, path_or_id=None):
        saved_ids.append(self.id)
        return f"/tmp/{self.id}.json"

    monkeypatch.setattr(MapData, "save", _fake_save)
    monkeypatch.setattr(map_editor, "load_tileset_images", lambda tileset, tile_size: {"ok": True})
    _set_prompt_sequence(
        monkeypatch,
        ["connected", "6", "5", "edge", "east", "2", "3", "west"],
    )

    editor._new_map_dialog()

    assert saved_ids == ["current", "connected"]
    assert editor.map.id == "connected"
    assert source_map.connections
    assert source_map.connections[0].to["mapId"] == "connected"
    assert editor.map.connections
    assert editor.map.connections[0].to["mapId"] == "current"
    assert "Created and opened new map 'connected'." == editor.status_message


def test_failed_source_map_save_surfaces_error_and_restores_state(monkeypatch):
    editor = _build_editor()
    original_map_id = editor.map.id
    saved_ids = []

    def _fake_save(self, path_or_id=None):
        if self.id == original_map_id:
            raise OSError("source save failed")
        saved_ids.append(self.id)
        return f"/tmp/{self.id}.json"

    monkeypatch.setattr(MapData, "save", _fake_save)
    monkeypatch.setattr(map_editor, "load_tileset_images", lambda tileset, tile_size: {})
    _set_prompt_sequence(
        monkeypatch,
        ["connected", "6", "5", "edge", "east", "2", "3", "west"],
    )

    editor._new_map_dialog()

    assert editor.map.id == original_map_id
    assert editor.map.connections == []
    assert saved_ids == []
    assert "Failed to save current map" in editor.status_message


def test_failed_new_map_save_rolls_back_source_map_changes(monkeypatch):
    editor = _build_editor()
    original_map_id = editor.map.id
    saved_ids = []

    def _fake_save(self, path_or_id=None):
        if self.id == "connected":
            raise OSError("new map save failed")
        saved_ids.append(self.id)
        return f"/tmp/{self.id}.json"

    monkeypatch.setattr(MapData, "save", _fake_save)
    monkeypatch.setattr(map_editor, "load_tileset_images", lambda tileset, tile_size: {})
    _set_prompt_sequence(
        monkeypatch,
        ["connected", "6", "5", "edge", "east", "2", "3", "west"],
    )

    editor._new_map_dialog()

    assert editor.map.id == original_map_id
    assert editor.map.connections == []
    assert saved_ids.count(original_map_id) >= 1
    assert "Failed to save new map 'connected'" in editor.status_message
