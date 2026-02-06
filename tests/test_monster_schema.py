import json

import pytest

from src.battle import battle_simulator
from src.core import config
from src.core.monster_schema import (
    derive_move_pool_from_learnset,
    normalize_monster,
    normalize_monsters,
)


class _DummySurface:
    def __init__(self, size=(32, 32)):
        self._size = size

    def get_size(self):
        return self._size

    def convert_alpha(self):
        return self

    def fill(self, _color):
        return


def test_normalize_monster_produces_canonical_schema():
    monster = {
        "name": "Canonmon",
        "type": "Fire",
        "base_stats": {"max_hp": 80, "attack": 55, "defense": 45},
        "learnset": [
            {"level": 1, "move": "Flame Burst"},
            {"level": 4, "move": "Power Up"},
        ],
        "notes": "custom field should survive",
    }

    normalized, warnings = normalize_monster(monster, strict_conflicts=True)

    assert warnings == []
    assert "max_hp" not in normalized
    assert "attack" not in normalized
    assert "defense" not in normalized
    assert "moves" not in normalized
    assert "move_pool" not in normalized
    assert normalized["base_stats"] == {"max_hp": 80, "attack": 55, "defense": 45}
    assert derive_move_pool_from_learnset(normalized["learnset"]) == ["Flame Burst", "Power Up"]
    assert normalized["notes"] == "custom field should survive"


def test_normalize_monster_upgrades_legacy_only_fields():
    legacy = {
        "name": "Legacymon",
        "type": "Water",
        "max_hp": 91,
        "attack": 64,
        "defense": 72,
        "moves": ["Bubble Wave", "Guard Up"],
    }

    normalized, warnings = normalize_monster(legacy, strict_conflicts=False)

    assert normalized["base_stats"] == {"max_hp": 91, "attack": 64, "defense": 72}
    assert derive_move_pool_from_learnset(normalized["learnset"]) == ["Bubble Wave", "Guard Up"]
    assert normalized["learnset"] == [
        {"level": 1, "move": "Bubble Wave"},
        {"level": 1, "move": "Guard Up"},
    ]
    assert any("legacy root stat fields" in warning for warning in warnings)
    assert any("legacy 'moves' field" in warning for warning in warnings)


def test_conflicting_duplicate_fields_raise_in_strict_mode():
    duplicated = {
        "name": "Conflictmon",
        "type": "Nature",
        "base_stats": {"max_hp": 70, "attack": 60, "defense": 50},
        "max_hp": 99,  # conflict
        "learnset": [{"level": 1, "move": "Leaf Cut"}],
        "move_pool": ["Leaf Cut", "Poison Dust"],  # conflict with learnset
    }

    with pytest.raises(ValueError, match="conflicting duplicated"):
        normalize_monster(duplicated, strict_conflicts=True)


def test_conflicting_duplicate_fields_are_flagged_in_non_strict_mode():
    duplicated = {
        "name": "Flagmon",
        "type": "Mind",
        "base_stats": {"max_hp": 70, "attack": 60, "defense": 50},
        "attack": 99,  # conflict
        "learnset": [{"level": 1, "move": "Psi Beam"}],
        "move_pool": ["Hypnosis"],  # conflict
    }

    normalized, warnings = normalize_monster(duplicated, strict_conflicts=False)

    assert normalized["base_stats"] == {"max_hp": 70, "attack": 60, "defense": 50}
    assert derive_move_pool_from_learnset(normalized["learnset"]) == ["Psi Beam"]
    assert any("conflicting duplicated stat fields" in warning for warning in warnings)
    assert any("conflicting duplicated move progression fields" in warning for warning in warnings)


def test_load_creatures_supports_canonical_monster_schema(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    sprite_dir = tmp_path / "sprites"
    data_dir.mkdir()
    sprite_dir.mkdir()

    monsters_payload = [
        {
            "name": "CanonLoader",
            "type": "Fire",
            "base_stats": {"max_hp": 88, "attack": 66, "defense": 44},
            "learnset": [
                {"level": 1, "move": "Flame Burst"},
                {"level": 5, "move": "Power Up"},
            ],
        }
    ]
    moves_payload = [
        {"name": "Flame Burst", "type": "Fire", "power": 50},
        {"name": "Power Up", "type": "Normal", "power": 0, "effect": {"target": "self", "stat": "attack", "change": 1}},
    ]

    (data_dir / "monsters.json").write_text(json.dumps(monsters_payload), encoding="utf-8")
    (data_dir / "moves.json").write_text(json.dumps(moves_payload), encoding="utf-8")

    monkeypatch.setattr(config, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(config, "SPRITE_DIR", str(sprite_dir))
    monkeypatch.setattr(battle_simulator, "create_sprite_from_file", lambda _path: _DummySurface())

    creatures = battle_simulator.load_creatures()

    assert len(creatures) == 1
    creature = creatures[0]
    assert creature.name == "CanonLoader"
    assert creature.base_stats == {"max_hp": 88, "attack": 66, "defense": 44}
    assert creature.move_pool == ["Flame Burst", "Power Up"]


def test_normalize_monsters_rejects_invalid_container():
    with pytest.raises(ValueError, match="list of monsters"):
        normalize_monsters({"name": "not a list"}, strict_conflicts=True)
