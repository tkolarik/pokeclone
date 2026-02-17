import json

import pytest

from src.battle.balance_metrics import (
    compute_archetype_win_rates,
    compute_balance_report,
    compute_matchup_polarization,
    compute_matchup_diversity,
    compute_move_usage_metrics,
    compute_replicator_dynamics,
    compute_report_deltas,
    evaluate_threshold_rules,
    load_battle_logs,
    normalized_entropy_from_counts,
    shannon_entropy_from_counts,
)


def _fixture_logs():
    with open("tests/fixtures/balance_logs/sample_battle_logs.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_entropy_helpers_cover_empty_and_populated_counts():
    assert shannon_entropy_from_counts({}) == 0.0
    assert normalized_entropy_from_counts({}) == 0.0

    counts = {"A": 6, "B": 3, "C": 2, "D": 1}
    assert shannon_entropy_from_counts(counts) == pytest.approx(1.7295739, rel=1e-6)
    assert normalized_entropy_from_counts(counts) == pytest.approx(0.8647869, rel=1e-6)


def test_move_usage_metrics_match_fixture_distribution():
    logs = _fixture_logs()
    metrics = compute_move_usage_metrics(logs)

    assert metrics["total_uses"] == 158
    assert metrics["unique_moves"] == 4
    assert metrics["counts"] == {
        "Bubble Wave": 46,
        "Flame Burst": 43,
        "Guard Up": 37,
        "Leaf Cut": 32,
    }
    assert metrics["by_actor_counts"] == {
        "opponent": {"Bubble Wave": 17, "Flame Burst": 13, "Guard Up": 16, "Leaf Cut": 12},
        "player": {"Bubble Wave": 29, "Flame Burst": 30, "Guard Up": 21, "Leaf Cut": 20},
    }
    assert metrics["top_1_share"] == pytest.approx(0.2911392405, rel=1e-6)
    assert metrics["top_3_share"] == pytest.approx(0.7974683544, rel=1e-6)
    assert metrics["herfindahl_index"] == pytest.approx(0.2546867489, rel=1e-6)
    assert metrics["pick_rate_metrics"]["distribution"]["total"] == 316
    assert metrics["pick_rate_metrics"]["pick_rates"]["Flame Burst"] == pytest.approx(0.5733333333, rel=1e-6)
    assert metrics["pick_rate_metrics"]["pick_rates"]["Guard Up"] == pytest.approx(0.4457831325, rel=1e-6)


def test_archetype_and_matchup_metrics_are_deterministic():
    logs = _fixture_logs()
    archetype_rates = compute_archetype_win_rates(logs)
    matchup_metrics = compute_matchup_diversity(logs)
    polarization = compute_matchup_polarization(logs)

    assert archetype_rates["control"]["win_rate"] == pytest.approx(1.0)
    assert archetype_rates["offense"]["win_rate"] == pytest.approx(0.6153846154, rel=1e-6)
    assert archetype_rates["stall"]["win_rate"] == pytest.approx(0.0, rel=1e-6)
    assert archetype_rates["tempo"]["win_rate"] == pytest.approx(1 / 3, rel=1e-6)
    assert archetype_rates["offense"]["win_rate_ci_95"]["high"] > 0.77

    assert matchup_metrics["counts"] == {
        "control vs offense": 10,
        "control vs stall": 8,
        "control vs tempo": 8,
        "offense vs stall": 8,
        "offense vs tempo": 8,
        "stall vs tempo": 8,
    }
    assert matchup_metrics["unique_ratio"] == pytest.approx(0.12)
    assert matchup_metrics["normalized_entropy"] == pytest.approx(0.9978754, rel=1e-6)
    assert matchup_metrics["effective_matchups"] == pytest.approx(5.9523809, rel=1e-6)
    assert polarization["polarization_index"] == pytest.approx(0.0218820861, abs=1e-9)
    assert polarization["sample_floor"]["eligible_cells"] == 12
    assert len(polarization["top_polarized_matchups"]) > 0


def test_balance_report_regression_snapshot():
    logs = _fixture_logs()
    report = compute_balance_report(logs, include_replicator=True)

    assert report["sample_size"] == 50
    assert report["move_usage"]["entropy_bits"] == pytest.approx(1.9862933, rel=1e-6)
    assert report["move_usage"]["normalized_entropy"] == pytest.approx(0.9931466, rel=1e-6)
    assert report["risk_flags"]["move_usage_concentration"] is True
    assert report["risk_flags"]["move_pick_rate_concentration"] is True
    assert report["risk_flags"]["win_rate_skew"] is True
    assert report["risk_flags"]["matchup_diversity_low"] is True
    assert report["risk_flags"]["matchup_polarization_high"] is False
    assert report["risk_flags"]["sample_sufficiency"]["move_usage"] is True
    assert len(report["risk_flags"]["warnings"]) == 0
    assert report["risk_flags"]["win_rate_spread"] == pytest.approx(1.0, rel=1e-6)
    assert report["risk_flags"]["max_qualified_win_rate"] == pytest.approx(1.0)
    assert report["replicator_dynamics"]["dominant_strategy"] == "control"
    assert report["replicator_dynamics"]["dominant_share"] >= 0.99
    assert report["replicator_dynamics"]["cycle_detected"] is True
    assert "converged" in report["replicator_dynamics"]
    assert report["turn_length_metrics"]["available"] is True
    assert report["turn_length_metrics"]["p90"] == pytest.approx(4.0)
    assert report["tempo_metrics"]["available"] is True
    assert report["tempo_metrics"]["mean_final_hp_delta"] == pytest.approx(0.02, rel=1e-6)
    assert report["log_metadata"]["sample_size"] == 50
    assert report["log_metadata"]["sampler"] == "scripted"
    assert len(report["log_metadata"]["seed_values"]) == 50


def test_load_battle_logs_supports_jsonl(tmp_path):
    jsonl_path = tmp_path / "battle_logs.jsonl"
    jsonl_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "winner": "player",
                        "player_archetype": "offense",
                        "opponent_archetype": "stall",
                        "moves_used": ["Flame Burst"],
                    }
                ),
                json.dumps(
                    {
                        "winner": "opponent",
                        "player_archetype": "stall",
                        "opponent_archetype": "control",
                        "moves_used": ["Bubble Wave"],
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    logs = load_battle_logs(str(jsonl_path))

    assert len(logs) == 2
    assert logs[0]["winner"] == "player"
    assert logs[1]["moves_used"] == ["Bubble Wave"]


def test_opportunity_conditioned_pick_rates_are_computed():
    logs = [
        {
            "winner": "player",
            "player_archetype": "offense",
            "opponent_archetype": "stall",
            "moves_used": ["Flame Burst", "Flame Burst", "Guard Up"],
            "move_opportunities": {"Flame Burst": 4, "Guard Up": 6, "Bubble Wave": 2},
        },
        {
            "winner": "opponent",
            "player_archetype": "stall",
            "opponent_archetype": "offense",
            "moves_used": ["Bubble Wave"],
            "move_opportunities": {"Flame Burst": 1, "Guard Up": 1, "Bubble Wave": 2},
        },
    ]

    metrics = compute_move_usage_metrics(logs)
    pick_rates = metrics["pick_rate_metrics"]["pick_rates"]

    assert pick_rates["Flame Burst"] == pytest.approx(2 / 5, rel=1e-6)
    assert pick_rates["Guard Up"] == pytest.approx(1 / 7, rel=1e-6)
    assert pick_rates["Bubble Wave"] == pytest.approx(1 / 4, rel=1e-6)
    assert metrics["pick_rate_metrics"]["distribution"]["total"] > 0


def test_threshold_rules_apply_absolute_and_delta_constraints():
    report = compute_balance_report(_fixture_logs())
    baseline = compute_balance_report(_fixture_logs()[:3])
    deltas = compute_report_deltas(report, baseline)
    assert "move_usage.top_1_share" in deltas

    relaxed = {
        "absolute_max": {"move_usage.top_1_share": 0.9},
        "delta_max": {"move_usage.top_1_share": 0.5},
    }
    assert evaluate_threshold_rules(report, relaxed, baseline_report=baseline) == []

    strict = {
        "absolute_max": {"move_usage.top_1_share": 0.25},
        "delta_min": {"matchup_diversity.unique_ratio": 0.01},
    }
    failures = evaluate_threshold_rules(report, strict, baseline_report=baseline)
    assert any("move_usage.top_1_share" in item for item in failures)


def test_threshold_rules_respect_min_sample_guards():
    report = compute_balance_report(
        [
            {
                "winner": "player",
                "player_archetype": "offense",
                "opponent_archetype": "stall",
                "moves_used": ["Flame Burst"],
                "move_opportunities": {"Flame Burst": 1},
            }
        ]
    )
    rules = {
        "absolute_max": {"move_usage.pick_rate_metrics.distribution.top_1_share": 0.1},
        "min_total_battles": 5,
        "min_opportunities_per_move": 10,
    }
    assert evaluate_threshold_rules(report, rules) == []


def test_replicator_dynamics_handles_empty_inputs():
    result = compute_replicator_dynamics([])
    assert result["strategies"] == []
    assert result["dominant_strategy"] is None
    assert result["dominant_share"] == 0.0


def test_report_metadata_captures_single_and_multiple_values():
    logs = [
        {
            "winner": "player",
            "player_archetype": "offense",
            "opponent_archetype": "stall",
            "moves_used": ["Flame Burst"],
            "commit": "abc123",
            "sampler": "scripted",
            "seed": 42,
        },
        {
            "winner": "opponent",
            "player_archetype": "stall",
            "opponent_archetype": "offense",
            "moves_used": ["Guard Up"],
            "commit": "abc123",
            "sampler": "random",
            "seed": 42,
        },
    ]
    report = compute_balance_report(logs)
    metadata = report["log_metadata"]
    assert metadata["commit"] == "abc123"
    assert metadata["seed"] == 42
    assert sorted(metadata["sampler_values"]) == ["random", "scripted"]


def test_balance_report_defaults_replicator_to_optional_field():
    report = compute_balance_report(_fixture_logs())
    assert report["replicator_dynamics"] is None


def test_missing_turn_and_tempo_data_are_marked_unavailable():
    report = compute_balance_report(
        [
            {
                "winner": "player",
                "player_archetype": "offense",
                "opponent_archetype": "stall",
                "moves_used": ["Flame Burst"],
            }
        ]
    )
    assert report["turn_length_metrics"]["available"] is False
    assert report["turn_length_metrics"]["p90"] is None
    assert report["tempo_metrics"]["available"] is False
    assert report["tempo_metrics"]["mean_final_hp_delta"] is None
