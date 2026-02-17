import json

from src.editor.constrained_fields import (
    load_move_options,
    load_type_options,
    normalize_learnset_entries,
    normalize_multi_selection,
    normalize_single_selection,
)


def test_load_type_options_reads_canonical_type_chart_keys(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "type_chart.json").write_text(
        json.dumps({"Water": {}, "Fire": {}, "Nature": {}}),
        encoding="utf-8",
    )

    assert load_type_options(str(data_dir)) == ["Fire", "Nature", "Water"]


def test_load_move_options_reads_unique_sorted_move_ids(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "moves.json").write_text(
        json.dumps(
            [
                {"name": "Flame Burst", "type": "Fire", "power": 80},
                {"name": "Bubble Wave", "type": "Water", "power": 70},
                {"name": "Flame Burst", "type": "Fire", "power": 80},
            ]
        ),
        encoding="utf-8",
    )

    assert load_move_options(str(data_dir)) == ["Bubble Wave", "Flame Burst"]


def test_selection_normalization_rejects_invalid_values():
    allowed = ["Fire", "Water"]
    assert normalize_single_selection("Fire", allowed) == "Fire"
    assert normalize_single_selection("Ghost", allowed) is None

    normalized, rejected = normalize_multi_selection(
        ["Fire", "Ghost", "Water", "Water"],
        allowed,
    )
    assert normalized == ["Fire", "Water"]
    assert rejected == ["Ghost"]


def test_learnset_normalization_preserves_valid_selected_values():
    rows = [
        {"level": 5, "move": "Flame Burst"},
        {"level": "7", "move": "Bubble Wave"},
        {"level": "bad", "move": "Flame Burst"},
        {"level": 2, "move": "Unknown Move"},
    ]
    normalized, rejected = normalize_learnset_entries(
        rows,
        ["Flame Burst", "Bubble Wave"],
    )

    assert normalized == [
        {"level": 5, "move": "Flame Burst"},
        {"level": 7, "move": "Bubble Wave"},
    ]
    assert len(rejected) == 2
