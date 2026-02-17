import pytest

from src.core.runtime_data_validation import (
    RuntimeDataValidationError,
    validate_map_payload,
    validate_monsters_payload,
    validate_moves_payload,
    validate_type_chart_payload,
)


def _valid_type_chart_payload():
    return {
        "Fire": {"Fire": 0.5, "Water": 0.5, "Nature": 2.0},
        "Water": {"Fire": 2.0, "Water": 0.5, "Nature": 0.5},
        "Nature": {"Fire": 0.5, "Water": 2.0, "Nature": 0.5},
    }


def _valid_moves_payload():
    return [
        {"name": "Flame Burst", "type": "Fire", "power": 80},
        {"name": "Bubble Wave", "type": "Water", "power": 70},
    ]


def _valid_monsters_payload():
    return [
        {
            "name": "Embercub",
            "type": "Fire",
            "base_stats": {"max_hp": 90, "attack": 65, "defense": 55},
            "learnset": [{"level": 1, "move": "Flame Burst"}],
        }
    ]


def _valid_map_payload():
    return {
        "id": "test_map",
        "name": "Test Map",
        "version": "1.0.0",
        "tileSize": 32,
        "dimensions": {"width": 2, "height": 2},
        "tilesetId": "test_tiles",
        "layers": [
            {"name": "ground", "tiles": [["grass", "grass"], ["grass", "grass"]]},
            {"name": "overlay", "tiles": [[None, None], [None, None]]},
        ],
        "connections": [],
        "entities": [],
        "triggers": [],
        "overrides": {},
        "spawn": {"x": 0, "y": 0},
    }


def test_validate_payloads_accept_valid_inputs():
    type_chart = validate_type_chart_payload(_valid_type_chart_payload())
    moves = validate_moves_payload(_valid_moves_payload())
    monsters, warnings = validate_monsters_payload(
        _valid_monsters_payload(),
        known_types=type_chart.keys(),
        known_moves={move["name"] for move in moves},
    )
    map_payload = validate_map_payload(_valid_map_payload())

    assert not warnings
    assert monsters[0]["name"] == "Embercub"
    assert map_payload["id"] == "test_map"


def test_validate_moves_rejects_missing_required_field():
    payload = [{"name": "Flame Burst", "type": "Fire"}]

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_moves_payload(payload, source="moves.json")

    assert "[0].power" in str(exc_info.value)


def test_validate_moves_rejects_wrong_type():
    payload = [{"name": "Flame Burst", "type": "Fire", "power": [90]}]

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_moves_payload(payload, source="moves.json")

    assert "[0].power" in str(exc_info.value)


def test_validate_moves_rejects_invalid_numeric_bounds():
    payload = [{"name": "Flame Burst", "type": "Fire", "power": -1}]

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_moves_payload(payload, source="moves.json")

    assert "[0].power" in str(exc_info.value)


def test_validate_monsters_rejects_missing_fields():
    payload = [{"type": "Fire", "base_stats": {"max_hp": 1, "attack": 1, "defense": 1}}]

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_monsters_payload(payload, source="monsters.json")

    assert "[0].name" in str(exc_info.value)


def test_validate_monsters_rejects_unknown_type_and_move_references():
    payload = _valid_monsters_payload()
    payload[0]["type"] = "UnknownType"
    payload[0]["learnset"] = [{"level": 1, "move": "UnknownMove"}]

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_monsters_payload(
            payload,
            source="monsters.json",
            known_types={"Fire", "Water"},
            known_moves={"Flame Burst"},
        )

    message = str(exc_info.value)
    assert "[0].type" in message
    assert "[0].learnset[0].move" in message


def test_validate_monsters_rejects_invalid_numeric_bounds():
    payload = _valid_monsters_payload()
    payload[0]["base_stats"]["max_hp"] = 0

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_monsters_payload(payload, source="monsters.json")

    assert "[0].base_stats.max_hp" in str(exc_info.value)


def test_validate_type_chart_rejects_invalid_multiplier_bounds():
    payload = _valid_type_chart_payload()
    payload["Fire"]["Water"] = 5.0

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_type_chart_payload(payload, source="type_chart.json")

    assert "Type chart value for Fire->Water must be between 0 and 4.0." in str(exc_info.value)


def test_validate_map_rejects_invalid_bounds():
    payload = _valid_map_payload()
    payload["spawn"] = {"x": 3, "y": 0}

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_map_payload(payload, source="map.json")

    assert "spawn must be within map bounds" in str(exc_info.value)


def test_validate_map_rejects_invalid_layer_shape():
    payload = _valid_map_payload()
    payload["layers"][0]["tiles"] = [["grass"], ["grass"]]

    with pytest.raises(RuntimeDataValidationError) as exc_info:
        validate_map_payload(payload, source="map.json")

    assert "layers[0].tiles[0]" in str(exc_info.value)
