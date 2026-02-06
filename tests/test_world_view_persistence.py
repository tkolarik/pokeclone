import json

import pytest

from src.overworld.state import MapData, MapLayer
from src.overworld.world_view import LayoutValidationError, WorldView, list_maps, load_layout


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


def test_list_maps_excludes_metadata_and_non_map_json(tmp_path, monkeypatch):
    map_dir = tmp_path / "maps"
    map_dir.mkdir()
    (map_dir / "world_layout.json").write_text(json.dumps({"maps": {"a": {"x": 0, "y": 0}}}))
    (map_dir / "notes.json").write_text(json.dumps({"hello": "world"}))
    (map_dir / "broken.json").write_text("{")
    (map_dir / "valid_map.json").write_text(
        json.dumps(
            {
                "id": "valid_map",
                "name": "Valid",
                "dimensions": {"width": 2, "height": 2},
                "tileSize": 16,
                "tilesetId": "basic_overworld",
                "layers": [
                    {"name": "ground", "tiles": [[None, None], [None, None]]},
                    {"name": "overlay", "tiles": [[None, None], [None, None]]},
                ],
            }
        )
    )

    monkeypatch.setattr("src.overworld.world_view.config.MAP_DIR", str(map_dir))

    assert list_maps() == ["valid_map"]


def test_load_maps_never_loads_world_layout_metadata(tmp_path, monkeypatch):
    map_dir = tmp_path / "maps"
    map_dir.mkdir()
    (map_dir / "world_layout.json").write_text(json.dumps({"maps": {"a": {"x": 0, "y": 0}}}))
    (map_dir / "alpha.json").write_text(
        json.dumps(
            {
                "id": "alpha",
                "name": "Alpha",
                "dimensions": {"width": 2, "height": 2},
                "tileSize": 16,
                "tilesetId": "basic_overworld",
                "layers": [
                    {"name": "ground", "tiles": [[None, None], [None, None]]},
                    {"name": "overlay", "tiles": [[None, None], [None, None]]},
                ],
            }
        )
    )

    monkeypatch.setattr("src.overworld.world_view.config.MAP_DIR", str(map_dir))
    loaded_ids = []

    def _fake_load_bundle(map_id):
        loaded_ids.append(map_id)
        return _build_map(map_id), None, object()

    monkeypatch.setattr("src.overworld.world_view._load_map_bundle", _fake_load_bundle)

    viewer = WorldView.__new__(WorldView)
    viewer.layout = {}
    viewer.status_message = ""
    viewer.status_kind = "info"
    viewer.maps = {}
    viewer.tilesets = {}
    viewer.previews = {}
    viewer._load_maps()

    assert loaded_ids == ["alpha"]
    assert "world_layout" not in loaded_ids


def test_load_layout_rejects_invalid_maps_shape(tmp_path, monkeypatch):
    layout_path = tmp_path / "world_layout.json"
    layout_path.write_text(json.dumps({"maps": []}))
    monkeypatch.setattr("src.overworld.world_view.LAYOUT_FILE", str(layout_path))

    with pytest.raises(LayoutValidationError):
        load_layout()


def test_load_layout_with_feedback_distinguishes_parse_error(monkeypatch):
    viewer = WorldView.__new__(WorldView)
    viewer.layout = {}
    viewer.status_message = ""
    viewer.status_kind = "info"

    def _raise_parse():
        raise json.JSONDecodeError("bad json", "{", 1)

    monkeypatch.setattr("src.overworld.world_view.load_layout", _raise_parse)
    ok = viewer._load_layout_with_feedback()

    assert ok is False
    assert viewer.status_kind == "error"
    assert "Layout parse error:" in viewer.status_message


def test_manual_portal_validation_error_is_explicit():
    viewer = WorldView.__new__(WorldView)
    viewer.maps = {"src": _build_map("src"), "dst": _build_map("dst")}
    viewer.manual_src = "src"
    viewer.manual_dst = "dst"
    viewer.manual_mode = True
    viewer.status_message = ""
    viewer.status_kind = "info"

    answers = iter(["99", "0", "0", "0", "n"])
    viewer._prompt_text = lambda _msg, _default="": next(answers)

    viewer._create_manual_connection()

    assert viewer.status_kind == "error"
    assert "Manual portal validation error:" in viewer.status_message
    assert viewer.maps["src"].connections == []
    assert viewer.maps["dst"].connections == []
    assert viewer.manual_mode is False


def test_manual_portal_save_failure_rolls_back_changes(monkeypatch):
    viewer = WorldView.__new__(WorldView)
    viewer.maps = {"src": _build_map("src"), "dst": _build_map("dst")}
    viewer.manual_src = "src"
    viewer.manual_dst = "dst"
    viewer.manual_mode = True
    viewer.status_message = ""
    viewer.status_kind = "info"

    answers = iter(["1", "1", "1", "1", "y"])
    viewer._prompt_text = lambda _msg, _default="": next(answers)

    save_calls = []

    def _fake_save(self, _path_or_id=None):
        save_calls.append((self.id, len(self.connections)))
        if self.id == "dst" and len(save_calls) == 2:
            raise OSError("disk full")
        return f"/tmp/{self.id}.json"

    monkeypatch.setattr(MapData, "save", _fake_save)

    viewer._create_manual_connection()

    assert viewer.status_kind == "error"
    assert "Manual portal I/O error:" in viewer.status_message
    # src updated save + dst failed save + src rollback save
    assert save_calls[0][0] == "src"
    assert save_calls[1][0] == "dst"
    assert save_calls[2][0] == "src"
    assert viewer.maps["src"].connections == []
    assert viewer.maps["dst"].connections == []
