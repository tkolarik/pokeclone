from __future__ import annotations

from src.battle.monster_balance_analysis import (
    analyze_monster_balance,
    available_moves_for_level,
    iter_movesets,
    moveset_count,
)


def test_available_moves_for_level_applies_level_gating():
    learnset = [
        {"level": 1, "move": "Quick Jab"},
        {"level": 20, "moves": ["Heavy Slam", "Guard Up"]},
        {"level": 50, "move": "Meteor Punch"},
    ]

    assert available_moves_for_level(learnset, 1) == ["Quick Jab"]
    assert available_moves_for_level(learnset, 20) == [
        "Quick Jab",
        "Heavy Slam",
        "Guard Up",
    ]
    assert available_moves_for_level(learnset, 100) == [
        "Quick Jab",
        "Heavy Slam",
        "Guard Up",
        "Meteor Punch",
    ]


def test_iter_movesets_enumerates_all_combinations():
    move_pool = ["A", "B", "C", "D", "E"]
    combos = list(iter_movesets(move_pool, max_moves_per_set=4))
    assert moveset_count(move_pool, 4) == 5
    assert len(combos) == 5
    assert ("A", "B", "C", "D") in combos
    assert ("B", "C", "D", "E") in combos


def test_analyze_monster_balance_ranks_dominant_monster():
    monsters = [
        {
            "name": "Titan",
            "type": "Metal",
            "base_stats": {"max_hp": 160, "attack": 140, "defense": 120},
            "learnset": [
                {"level": 1, "move": "Heavy Slam"},
                {"level": 1, "move": "Flare Beam"},
                {"level": 1, "move": "Hydro Crush"},
                {"level": 1, "move": "Guard Up"},
                {"level": 60, "move": "Spirit Strike"},
            ],
        },
        {
            "name": "Scout",
            "type": "Wind",
            "base_stats": {"max_hp": 100, "attack": 80, "defense": 70},
            "learnset": [
                {"level": 1, "move": "Flare Beam"},
                {"level": 1, "move": "Hydro Crush"},
                {"level": 1, "move": "Spirit Strike"},
                {"level": 1, "move": "Guard Up"},
            ],
        },
        {
            "name": "Sprout",
            "type": "Nature",
            "base_stats": {"max_hp": 95, "attack": 75, "defense": 65},
            "learnset": [
                {"level": 1, "move": "Spirit Strike"},
                {"level": 1, "move": "Flare Beam"},
                {"level": 1, "move": "Hydro Crush"},
                {"level": 1, "move": "Guard Up"},
            ],
        },
    ]
    moves = [
        {"name": "Heavy Slam", "type": "Metal", "power": 120},
        {"name": "Flare Beam", "type": "Fire", "power": 95},
        {"name": "Hydro Crush", "type": "Water", "power": 95},
        {"name": "Spirit Strike", "type": "Nature", "power": 95},
        {
            "name": "Guard Up",
            "type": "Normal",
            "power": 0,
            "effect": {"target": "self", "stat": "defense", "change": 2},
        },
    ]
    # Neutral chart keeps the test deterministic and focused on stats + learnset combos.
    type_chart = {
        "Metal": {"Metal": 1.0, "Wind": 1.0, "Nature": 1.0},
        "Fire": {"Metal": 1.0, "Wind": 1.0, "Nature": 1.0},
        "Water": {"Metal": 1.0, "Wind": 1.0, "Nature": 1.0},
        "Nature": {"Metal": 1.0, "Wind": 1.0, "Nature": 1.0},
        "Normal": {"Metal": 1.0, "Wind": 1.0, "Nature": 1.0},
    }

    report = analyze_monster_balance(monsters, moves, type_chart, level=100, max_moves_per_set=4)
    ranked = report["ranked_monsters"]

    assert report["monster_count"] == 3
    assert ranked[0]["name"] == "Titan"
    assert ranked[0]["moveset_count"] == 5
    assert report["dominance_summary"]["top_monster"] == "Titan"
    assert report["dominance_summary"]["potentially_dominant"] is True
    titan = next(item for item in report["monster_analyses"] if item["name"] == "Titan")
    assert titan["best_moveset_metrics"]["average_best_setup_turns"] >= 0.0
    assert "high_setup_reliance_monsters" in report["dominance_summary"]
