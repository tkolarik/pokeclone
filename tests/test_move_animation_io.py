import json
import os

import pygame

from src.editor.move_animation_io import (
    load_move_animation,
    save_move_animation,
)


def test_load_save_roundtrip_preserves_unknown_fields_and_generates_placeholders(tmp_path):
    pygame.init()
    data_dir = tmp_path / "data"
    sprite_dir = tmp_path / "sprites"
    (data_dir / "move_animations").mkdir(parents=True)
    (sprite_dir / "move_animations").mkdir(parents=True)

    payload = {
        "version": "1.0.0",
        "id": "ember_strike",
        "name": "Ember Strike",
        "canvas": {"w": 16, "h": 16, "customCanvas": "keep"},
        "frames": [
            {"durationMs": 100, "extraTimeline": 1},
            {"durationMs": 150},
        ],
        "objects": [
            {
                "id": "proj",
                "name": "Projectile",
                "anchor": "attacker",
                "size": {"w": 16, "h": 16, "customSize": "keep"},
                "frames": [
                    {"image": "proj/frame_000.png", "x": 2, "y": 3, "customFrame": "keep"},
                    {"x": 5, "y": 7},
                ],
                "customObject": "keep",
            }
        ],
        "preview": {"background": "backgrounds/arena.png"},
        "customTopLevel": "keep",
    }
    json_path = data_dir / "move_animations" / "ember_strike.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    state, surfaces = load_move_animation(
        str(json_path),
        data_dir=str(data_dir),
        sprite_dir=str(sprite_dir),
        generate_placeholders=True,
    )

    assert state.extra["customTopLevel"] == "keep"
    assert state.canvas_extra["customCanvas"] == "keep"
    obj = state.objects[0]
    assert obj.extra["customObject"] == "keep"
    assert obj.size_extra["customSize"] == "keep"
    assert obj.frames[0].extra["customFrame"] == "keep"
    assert obj.frames[1].image == "proj/frame_001.png"

    placeholder_0 = sprite_dir / "move_animations" / "ember_strike" / "proj" / "frame_000.png"
    placeholder_1 = sprite_dir / "move_animations" / "ember_strike" / "proj" / "frame_001.png"
    assert placeholder_0.exists()
    assert placeholder_1.exists()
    assert surfaces[("proj", 0)].get_size() == (16, 16)

    obj.frames[1].x = 11
    save_path = save_move_animation(state, surfaces, data_dir=str(data_dir), sprite_dir=str(sprite_dir))
    assert save_path.endswith("ember_strike.json")

    saved_payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved_payload["customTopLevel"] == "keep"
    assert saved_payload["canvas"]["customCanvas"] == "keep"
    assert saved_payload["objects"][0]["customObject"] == "keep"
    assert saved_payload["objects"][0]["size"]["customSize"] == "keep"
    assert saved_payload["objects"][0]["frames"][0]["customFrame"] == "keep"
    assert saved_payload["objects"][0]["frames"][1]["x"] == 11
    assert os.path.exists(placeholder_0)
    assert os.path.exists(placeholder_1)
