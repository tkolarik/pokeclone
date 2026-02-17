from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, Mapping


MOVE_TOP3_SHARE_ALERT = 0.70
MOVE_NORMALIZED_ENTROPY_ALERT = 0.60
WIN_RATE_SKEW_ALERT = 0.65
WIN_RATE_MIN_BATTLES = 3
MATCHUP_DIVERSITY_ALERT = 0.35
MATCHUP_POLARIZATION_ALERT = 0.08
REPEAT_LOOP_STREAK_ALERT = 8
TIMEOUT_RATE_ALERT = 0.01

DEFAULT_POLARIZATION_MIN_CELL_BATTLES = 1
DEFAULT_POLARIZATION_SHRINKAGE_K = 10.0

# Keep hard risk flags quiet on tiny samples; still emit warnings.
RISK_MIN_BATTLES_FOR_FLAGS = 25
RISK_MIN_MOVE_USES_FOR_FLAGS = 120
RISK_MIN_PICK_OPPORTUNITIES_FOR_FLAGS = 240
RISK_MIN_ARCHETYPE_BATTLES_FOR_SKEW = 25
RISK_MIN_POLARIZATION_ELIGIBLE_CELLS = 12
RISK_MIN_POLARIZATION_COVERAGE = 0.50


def load_battle_logs(path: str) -> list[dict[str, Any]]:
    """Load battle logs from JSON array or newline-delimited JSON."""
    text = Path(path).read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        payload = json.loads(stripped)
        if not isinstance(payload, list):
            raise ValueError("Battle log JSON must be an array of objects.")
        return [entry for entry in payload if isinstance(entry, dict)]

    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(stripped.splitlines(), start=1):
        candidate = line.strip()
        if not candidate:
            continue
        payload = json.loads(candidate)
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL record on line {line_number} must be an object.")
        records.append(payload)
    return records


def _iter_move_names(logs: Iterable[dict[str, Any]]) -> Iterable[str]:
    for log in logs:
        moves_used = log.get("moves_used")
        if isinstance(moves_used, list):
            for item in moves_used:
                if isinstance(item, str) and item.strip():
                    yield item.strip()
                elif isinstance(item, dict):
                    name = item.get("move") or item.get("name")
                    if isinstance(name, str) and name.strip():
                        yield name.strip()

        events = log.get("events")
        if isinstance(events, list):
            for event in events:
                if not isinstance(event, dict):
                    continue
                move_name = event.get("move") or event.get("move_name")
                if isinstance(move_name, str) and move_name.strip():
                    yield move_name.strip()


def _iter_move_opportunities(logs: Iterable[dict[str, Any]]) -> Iterable[str]:
    for log in logs:
        opportunities = log.get("move_opportunities")
        if isinstance(opportunities, dict):
            for move_name, count in opportunities.items():
                if not isinstance(move_name, str):
                    continue
                stripped = move_name.strip()
                if not stripped:
                    continue
                if not isinstance(count, int) or count <= 0:
                    continue
                for _ in range(count):
                    yield stripped

        turns = log.get("turns")
        if isinstance(turns, list):
            for turn in turns:
                if not isinstance(turn, dict):
                    continue
                legal = turn.get("legal_moves")
                if isinstance(legal, list):
                    for candidate in legal:
                        if isinstance(candidate, str) and candidate.strip():
                            yield candidate.strip()

        events = log.get("events")
        if isinstance(events, list):
            for event in events:
                if not isinstance(event, dict):
                    continue
                legal = event.get("legal_moves")
                if isinstance(legal, list):
                    for candidate in legal:
                        if isinstance(candidate, str) and candidate.strip():
                            yield candidate.strip()


def _top_share(counts: Dict[str, int], top_n: int) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    ranked = sorted(counts.values(), reverse=True)
    return sum(ranked[: max(1, int(top_n))]) / total


def shannon_entropy_from_counts(counts: Dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in counts.values():
        if value <= 0:
            continue
        p = value / total
        entropy -= p * math.log2(p)
    return entropy


def normalized_entropy_from_counts(counts: Dict[str, int]) -> float:
    positive = [value for value in counts.values() if value > 0]
    if len(positive) <= 1:
        return 0.0
    entropy = shannon_entropy_from_counts(counts)
    return entropy / math.log2(len(positive))


def herfindahl_index_from_counts(counts: Dict[str, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    return sum((value / total) ** 2 for value in counts.values() if value > 0)


def _convert_pick_rates_to_counts(
    pick_rates: Mapping[str, float], scale: int = 10000
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for move_name, pick_rate in pick_rates.items():
        if pick_rate <= 0:
            continue
        counts[move_name] = max(1, int(round(pick_rate * scale)))
    return counts


def _build_distribution_metrics(counts: Dict[str, int]) -> dict[str, Any]:
    total = sum(counts.values())
    return {
        "counts": dict(sorted(counts.items())),
        "total": total,
        "unique": len(counts),
        "entropy_bits": shannon_entropy_from_counts(counts),
        "normalized_entropy": normalized_entropy_from_counts(counts),
        "top_1_share": _top_share(counts, 1),
        "top_3_share": _top_share(counts, 3),
        "herfindahl_index": herfindahl_index_from_counts(counts),
    }


def compute_move_pick_rates(logs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    use_counts = Counter(_iter_move_names(logs))
    opportunity_counts = Counter(_iter_move_opportunities(logs))
    pick_rates: dict[str, float] = {}
    for move_name in sorted(opportunity_counts.keys()):
        opportunities = opportunity_counts[move_name]
        if opportunities <= 0:
            continue
        pick_rates[move_name] = use_counts.get(move_name, 0) / opportunities

    unweighted_counts = _convert_pick_rates_to_counts(pick_rates)
    weighted_counts = {
        move_name: count
        for move_name, count in sorted(opportunity_counts.items())
        if count > 0 and move_name in pick_rates
    }

    top_by_pick_rate = sorted(
        (
            {
                "move": move_name,
                "pick_rate": pick_rates[move_name],
                "uses": use_counts.get(move_name, 0),
                "eligible_opportunities": opportunity_counts.get(move_name, 0),
            }
            for move_name in pick_rates
        ),
        key=lambda item: item["pick_rate"],
        reverse=True,
    )[:5]
    top_by_uses = sorted(
        (
            {
                "move": move_name,
                "uses": use_counts[move_name],
                "pick_rate": pick_rates.get(move_name, 0.0),
                "eligible_opportunities": opportunity_counts.get(move_name, 0),
            }
            for move_name in use_counts
        ),
        key=lambda item: item["uses"],
        reverse=True,
    )[:5]

    return {
        "opportunity_counts": dict(sorted(opportunity_counts.items())),
        "pick_rates": pick_rates,
        "distribution": _build_distribution_metrics(weighted_counts),
        "unweighted_distribution": _build_distribution_metrics(unweighted_counts),
        "top_by_pick_rate": top_by_pick_rate,
        "top_by_uses": top_by_uses,
    }


def compute_move_usage_by_actor(logs: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    by_actor: dict[str, Counter[str]] = defaultdict(Counter)
    for log in logs:
        used_event_data = False
        events = log.get("events")
        if isinstance(events, list):
            for event in events:
                if not isinstance(event, dict):
                    continue
                move_name = event.get("move") or event.get("move_name")
                if not isinstance(move_name, str) or not move_name.strip():
                    continue
                actor = event.get("actor") or event.get("side") or event.get("source") or "unknown"
                actor_name = str(actor).strip() or "unknown"
                by_actor[actor_name][move_name.strip()] += 1
                used_event_data = True

        if used_event_data:
            continue

        moves_by_side = log.get("moves_used_by_side")
        if isinstance(moves_by_side, dict):
            for side, moves in moves_by_side.items():
                if not isinstance(moves, list):
                    continue
                side_name = str(side).strip() or "unknown"
                for move_name in moves:
                    if isinstance(move_name, str) and move_name.strip():
                        by_actor[side_name][move_name.strip()] += 1

    return {
        actor: dict(sorted(counter.items()))
        for actor, counter in sorted(by_actor.items(), key=lambda item: item[0])
    }


def compute_move_usage_metrics(logs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    logs_list = list(logs)
    counts = Counter(_iter_move_names(logs_list))
    opportunities = compute_move_pick_rates(logs_list)
    actor_counts = compute_move_usage_by_actor(logs_list)
    base_metrics = _build_distribution_metrics(dict(counts))
    return {
        "counts": base_metrics["counts"],
        "by_actor_counts": actor_counts,
        "total_uses": base_metrics["total"],
        "unique_moves": base_metrics["unique"],
        "entropy_bits": base_metrics["entropy_bits"],
        "normalized_entropy": base_metrics["normalized_entropy"],
        "top_1_share": base_metrics["top_1_share"],
        "top_3_share": base_metrics["top_3_share"],
        "herfindahl_index": base_metrics["herfindahl_index"],
        "pick_rate_metrics": opportunities,
    }


def _normalize_archetype(value: Any) -> str:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return "unknown"


def _extract_archetype_pair(log: dict[str, Any]) -> tuple[str, str]:
    player = _normalize_archetype(
        log.get("player_archetype", log.get("playerArchetype"))
    )
    opponent = _normalize_archetype(
        log.get("opponent_archetype", log.get("opponentArchetype"))
    )
    return player, opponent


def wilson_interval(wins: int, battles: int, z: float = 1.96) -> tuple[float, float]:
    if battles <= 0:
        return 0.0, 0.0
    p = wins / battles
    denominator = 1 + (z * z / battles)
    center = (p + (z * z) / (2 * battles)) / denominator
    margin = (
        z
        * math.sqrt((p * (1 - p) / battles) + ((z * z) / (4 * battles * battles)))
        / denominator
    )
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return low, high


def compute_archetype_win_rates(logs: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"wins": 0, "battles": 0})
    for log in logs:
        player_arch, opponent_arch = _extract_archetype_pair(log)
        stats[player_arch]["battles"] += 1
        stats[opponent_arch]["battles"] += 1

        winner = str(log.get("winner", "")).strip().lower()
        if winner == "player":
            stats[player_arch]["wins"] += 1
        elif winner == "opponent":
            stats[opponent_arch]["wins"] += 1

    normalized: dict[str, dict[str, Any]] = {}
    for archetype in sorted(stats.keys()):
        battles = stats[archetype]["battles"]
        wins = stats[archetype]["wins"]
        win_rate = (wins / battles) if battles else 0.0
        low_95, high_95 = wilson_interval(wins, battles)
        normalized[archetype] = {
            "wins": wins,
            "battles": battles,
            "win_rate": win_rate,
            "win_rate_ci_95": {"low": low_95, "high": high_95},
        }
    return normalized


def compute_matchup_polarization(
    logs: Iterable[dict[str, Any]],
    *,
    min_cell_battles: int = DEFAULT_POLARIZATION_MIN_CELL_BATTLES,
    shrinkage_k: float = DEFAULT_POLARIZATION_SHRINKAGE_K,
) -> dict[str, Any]:
    directed: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "battles": 0}
    )
    for log in logs:
        player_arch, opponent_arch = _extract_archetype_pair(log)
        key = (player_arch, opponent_arch)
        directed[key]["battles"] += 1
        winner = str(log.get("winner", "")).strip().lower()
        if winner == "player":
            directed[key]["wins"] += 1

    directed_out: dict[str, dict[str, Any]] = {}
    weighted_sum = 0.0
    total_weight = 0
    contributors: list[dict[str, Any]] = []
    eligible_cells = 0

    for (src, dst), stats in sorted(directed.items()):
        wins = stats["wins"]
        battles = stats["battles"]
        raw_wr = (wins / battles) if battles else 0.5
        shrunk_wr = (wins + (shrinkage_k * 0.5)) / (battles + shrinkage_k) if battles else 0.5
        deviation_sq = (shrunk_wr - 0.5) ** 2
        eligible = battles >= min_cell_battles
        if eligible:
            eligible_cells += 1
            weighted_sum += deviation_sq * battles
            total_weight += battles
            contributors.append(
                {
                    "matchup": f"{src} -> {dst}",
                    "battles": battles,
                    "raw_win_rate": raw_wr,
                    "shrunk_win_rate": shrunk_wr,
                    "deviation_sq": deviation_sq,
                    "weighted_contribution": deviation_sq * battles,
                }
            )

        directed_out[f"{src} -> {dst}"] = {
            "wins": wins,
            "battles": battles,
            "win_rate": raw_wr,
            "shrunk_win_rate": shrunk_wr,
            "eligible": eligible,
        }

    polarization_index = (weighted_sum / total_weight) if total_weight > 0 else 0.0
    top_contributors = sorted(
        contributors,
        key=lambda item: item["weighted_contribution"],
        reverse=True,
    )[:5]

    total_cells = len(directed_out)
    return {
        "directed_matchups": directed_out,
        "polarization_index": polarization_index,
        "sample_floor": {
            "min_cell_battles": min_cell_battles,
            "shrinkage_k": shrinkage_k,
            "eligible_cells": eligible_cells,
            "total_cells": total_cells,
            "coverage": (eligible_cells / total_cells) if total_cells else 0.0,
        },
        "top_polarized_matchups": top_contributors,
    }


def _directed_win_rate_table(
    logs: Iterable[dict[str, Any]],
    *,
    shrinkage_k: float,
) -> dict[tuple[str, str], dict[str, float]]:
    tallies: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "battles": 0}
    )
    for log in logs:
        player_arch, opponent_arch = _extract_archetype_pair(log)
        key = (player_arch, opponent_arch)
        tallies[key]["battles"] += 1
        winner = str(log.get("winner", "")).strip().lower()
        if winner == "player":
            tallies[key]["wins"] += 1

    rates: dict[tuple[str, str], dict[str, float]] = {}
    for key, stats in tallies.items():
        battles = stats["battles"]
        wins = stats["wins"]
        raw = (wins / battles) if battles else 0.5
        shrunk = (wins + (shrinkage_k * 0.5)) / (battles + shrinkage_k) if battles else 0.5
        rates[key] = {
            "wins": float(wins),
            "battles": float(battles),
            "raw": raw,
            "shrunk": shrunk,
        }
    return rates


def _simulate_replicator(
    archetypes: list[str],
    payoff: list[list[float]],
    *,
    iterations: int,
    learning_rate: float,
    convergence_epsilon: float,
    convergence_patience: int,
    cycle_window: int,
) -> dict[str, Any]:
    n = len(archetypes)
    x = [1.0 / n for _ in range(n)]
    history: list[list[float]] = [list(x)]
    converged_at: int | None = None
    cycle_detected = False

    for step in range(1, max(0, iterations) + 1):
        fitness = []
        for i in range(n):
            score = 0.0
            for j in range(n):
                score += payoff[i][j] * x[j]
            fitness.append(score)
        avg_fitness = sum(x[i] * fitness[i] for i in range(n))
        next_x = []
        for i in range(n):
            value = x[i] * (1.0 + learning_rate * (fitness[i] - avg_fitness))
            next_x.append(max(0.0, value))
        total = sum(next_x)
        if total <= 0:
            next_x = [1.0 / n for _ in range(n)]
        else:
            next_x = [value / total for value in next_x]

        history.append(list(next_x))

        if step >= convergence_patience:
            recent = history[-convergence_patience:]
            if len(recent) >= 2:
                max_delta = max(
                    sum(abs(recent[idx][i] - recent[idx - 1][i]) for i in range(n))
                    for idx in range(1, len(recent))
                )
                if max_delta < convergence_epsilon and converged_at is None:
                    converged_at = step

        if len(history) > cycle_window + 1:
            probe = history[-1]
            for candidate in history[-(cycle_window + 1) : -1]:
                cycle_l1 = sum(abs(probe[i] - candidate[i]) for i in range(n))
                if cycle_l1 < convergence_epsilon:
                    cycle_detected = True
                    break
            if cycle_detected:
                break

        x = next_x

    final_distribution = {archetypes[i]: history[-1][i] for i in range(n)}
    dominant_strategy = max(final_distribution, key=final_distribution.get)
    return {
        "final_distribution": final_distribution,
        "dominant_strategy": dominant_strategy,
        "dominant_share": final_distribution[dominant_strategy],
        "iterations_executed": len(history) - 1,
        "converged": converged_at is not None,
        "converged_at_iteration": converged_at,
        "cycle_detected": cycle_detected,
    }


def compute_replicator_dynamics(
    logs: Iterable[dict[str, Any]],
    *,
    iterations: int = 400,
    learning_rate: float = 0.5,
    shrinkage_k: float = DEFAULT_POLARIZATION_SHRINKAGE_K,
    sensitivity_k: float | None = None,
    min_cell_battles: int = DEFAULT_POLARIZATION_MIN_CELL_BATTLES,
    convergence_epsilon: float = 1e-6,
    convergence_patience: int = 8,
    cycle_window: int = 20,
) -> dict[str, Any]:
    logs_list = list(logs)
    archetypes = sorted(
        {
            archetype
            for log in logs_list
            for archetype in _extract_archetype_pair(log)
        }
    )
    n = len(archetypes)
    if n == 0:
        return {
            "strategies": [],
            "iterations_requested": iterations,
            "initial_distribution": {},
            "final_distribution": {},
            "dominant_strategy": None,
            "dominant_share": 0.0,
            "converged": False,
            "converged_at_iteration": None,
            "cycle_detected": False,
            "coverage": 0.0,
            "observed_cell_count": 0,
            "eligible_cell_count": 0,
            "missing_cells": 0,
            "sensitivity": None,
        }

    win_table = _directed_win_rate_table(logs_list, shrinkage_k=shrinkage_k)
    index_by_strategy = {name: idx for idx, name in enumerate(archetypes)}
    payoff = [[0.5 for _ in range(n)] for _ in range(n)]
    observed_cell_count = 0
    eligible_cell_count = 0

    for i_name in archetypes:
        for j_name in archetypes:
            i = index_by_strategy[i_name]
            j = index_by_strategy[j_name]
            if i == j:
                payoff[i][j] = 0.5
                continue
            direct = win_table.get((i_name, j_name))
            reverse = win_table.get((j_name, i_name))
            if direct is not None:
                observed_cell_count += 1
                if direct["battles"] >= min_cell_battles:
                    eligible_cell_count += 1
                payoff[i][j] = direct["shrunk"]
            elif reverse is not None:
                observed_cell_count += 1
                if reverse["battles"] >= min_cell_battles:
                    eligible_cell_count += 1
                payoff[i][j] = 1.0 - reverse["shrunk"]
            else:
                payoff[i][j] = 0.5

    base = _simulate_replicator(
        archetypes,
        payoff,
        iterations=iterations,
        learning_rate=learning_rate,
        convergence_epsilon=convergence_epsilon,
        convergence_patience=convergence_patience,
        cycle_window=cycle_window,
    )

    if sensitivity_k is None:
        sensitivity_k = max(1.0, shrinkage_k * 2.0)
    sensitivity: dict[str, Any] | None = None
    if sensitivity_k != shrinkage_k:
        alt_table = _directed_win_rate_table(logs_list, shrinkage_k=sensitivity_k)
        alt_payoff = [[0.5 for _ in range(n)] for _ in range(n)]
        for i_name in archetypes:
            for j_name in archetypes:
                i = index_by_strategy[i_name]
                j = index_by_strategy[j_name]
                if i == j:
                    alt_payoff[i][j] = 0.5
                    continue
                direct = alt_table.get((i_name, j_name))
                reverse = alt_table.get((j_name, i_name))
                if direct is not None:
                    alt_payoff[i][j] = direct["shrunk"]
                elif reverse is not None:
                    alt_payoff[i][j] = 1.0 - reverse["shrunk"]
                else:
                    alt_payoff[i][j] = 0.5
        alt = _simulate_replicator(
            archetypes,
            alt_payoff,
            iterations=iterations,
            learning_rate=learning_rate,
            convergence_epsilon=convergence_epsilon,
            convergence_patience=convergence_patience,
            cycle_window=cycle_window,
        )
        base_dom = base["dominant_strategy"]
        sensitivity = {
            "base_k": shrinkage_k,
            "alt_k": sensitivity_k,
            "base_dominant_strategy": base_dom,
            "alt_dominant_strategy": alt["dominant_strategy"],
            "base_dominant_share": base["dominant_share"],
            "alt_dominant_share": alt["dominant_share"],
            "dominant_share_delta": (
                alt["dominant_share"] - base["dominant_share"]
            ),
            "same_dominant_strategy": alt["dominant_strategy"] == base_dom,
        }

    total_possible = n * (n - 1)
    coverage = (eligible_cell_count / total_possible) if total_possible else 0.0
    missing_cells = max(0, total_possible - observed_cell_count)

    return {
        "strategies": archetypes,
        "iterations_requested": iterations,
        "initial_distribution": {name: 1.0 / n for name in archetypes},
        "final_distribution": base["final_distribution"],
        "dominant_strategy": base["dominant_strategy"],
        "dominant_share": base["dominant_share"],
        "iterations_executed": base["iterations_executed"],
        "converged": base["converged"],
        "converged_at_iteration": base["converged_at_iteration"],
        "cycle_detected": base["cycle_detected"],
        "coverage": coverage,
        "observed_cell_count": observed_cell_count,
        "eligible_cell_count": eligible_cell_count,
        "missing_cells": missing_cells,
        "shrinkage_k": shrinkage_k,
        "min_cell_battles": min_cell_battles,
        "sensitivity": sensitivity,
    }


def _canonical_matchup(player_arch: str, opponent_arch: str) -> str:
    ordered = sorted([player_arch, opponent_arch])
    return f"{ordered[0]} vs {ordered[1]}"


def compute_matchup_diversity(logs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    matchup_counts = Counter()
    total = 0
    for log in logs:
        player_arch, opponent_arch = _extract_archetype_pair(log)
        matchup_counts[_canonical_matchup(player_arch, opponent_arch)] += 1
        total += 1
    counts_dict = dict(sorted(matchup_counts.items()))
    unique = len(matchup_counts)
    hhi = herfindahl_index_from_counts(counts_dict)
    effective_matchups = (1.0 / hhi) if hhi > 0 else 0.0
    return {
        "counts": counts_dict,
        "total_battles": total,
        "unique_matchups": unique,
        "unique_ratio": (unique / total) if total else 0.0,
        "entropy_bits": shannon_entropy_from_counts(counts_dict),
        "normalized_entropy": normalized_entropy_from_counts(counts_dict),
        "herfindahl_index": hhi,
        "effective_matchups": effective_matchups,
    }


def _extract_turn_count(log: dict[str, Any]) -> int | None:
    for key in ("turn_count", "num_turns", "turns_taken"):
        value = log.get(key)
        if isinstance(value, int) and value > 0:
            return value
    turns = log.get("turns")
    if isinstance(turns, int) and turns > 0:
        return turns
    if isinstance(turns, list) and turns:
        return len(turns)
    return None


def compute_turn_length_metrics(logs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    turn_counts = [value for value in (_extract_turn_count(log) for log in logs) if value]
    if not turn_counts:
        return {
            "available": False,
            "sample_size": 0,
            "mean": None,
            "median": None,
            "p90": None,
            "max": None,
        }
    ordered = sorted(turn_counts)
    p90_index = min(len(ordered) - 1, math.ceil(len(ordered) * 0.9) - 1)
    return {
        "available": True,
        "sample_size": len(ordered),
        "mean": mean(ordered),
        "median": median(ordered),
        "p90": float(ordered[p90_index]),
        "max": ordered[-1],
    }


def _extract_event_sequence(log: dict[str, Any]) -> list[tuple[str, str]]:
    sequence: list[tuple[str, str]] = []
    events = log.get("events")
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            move_name = event.get("move") or event.get("move_name")
            actor = event.get("actor") or event.get("side") or event.get("source")
            if not isinstance(move_name, str) or not move_name.strip():
                continue
            actor_name = str(actor).strip() if actor is not None else "unknown"
            sequence.append((actor_name or "unknown", move_name.strip()))
        if sequence:
            return sequence

    moves_used = log.get("moves_used")
    if isinstance(moves_used, list):
        for item in moves_used:
            if isinstance(item, str) and item.strip():
                sequence.append(("unknown", item.strip()))
            elif isinstance(item, dict):
                move_name = item.get("move") or item.get("name")
                actor = item.get("actor") or item.get("side") or "unknown"
                if isinstance(move_name, str) and move_name.strip():
                    sequence.append((str(actor).strip() or "unknown", move_name.strip()))
    return sequence


def compute_repeat_loop_metrics(logs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    max_streak_global = 0
    streaks: list[int] = []
    flagged_battles = 0
    total_battles = 0
    for log in logs:
        sequence = _extract_event_sequence(log)
        if not sequence:
            continue
        total_battles += 1
        best_streak = 1
        current_streak = 1
        prev_actor, prev_move = sequence[0]
        for actor, move_name in sequence[1:]:
            if actor == prev_actor and move_name == prev_move:
                current_streak += 1
            else:
                current_streak = 1
                prev_actor, prev_move = actor, move_name
            best_streak = max(best_streak, current_streak)
        max_streak_global = max(max_streak_global, best_streak)
        streaks.append(best_streak)
        if best_streak >= REPEAT_LOOP_STREAK_ALERT:
            flagged_battles += 1
    return {
        "sample_size": total_battles,
        "max_streak": max_streak_global,
        "avg_max_streak": mean(streaks) if streaks else 0.0,
        "battles_with_streak_ge_8": flagged_battles,
        "battles_with_streak_ge_8_rate": (flagged_battles / total_battles)
        if total_battles
        else 0.0,
    }


def compute_non_decision_metrics(logs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    counters = Counter()
    total = 0
    for log in logs:
        total += 1
        result = str(log.get("result", "")).strip().lower()
        winner = str(log.get("winner", "")).strip().lower()
        ended_by = str(log.get("ended_by", "")).strip().lower()
        if result in {"timeout", "time_out"} or ended_by == "timeout":
            counters["timeout"] += 1
        if winner == "draw" or result == "draw":
            counters["draw"] += 1
        if result == "surrender" or ended_by == "surrender":
            counters["surrender"] += 1
    timeout_rate = (counters["timeout"] / total) if total else 0.0
    draw_rate = (counters["draw"] / total) if total else 0.0
    surrender_rate = (counters["surrender"] / total) if total else 0.0
    return {
        "sample_size": total,
        "timeout_rate": timeout_rate,
        "draw_rate": draw_rate,
        "surrender_rate": surrender_rate,
        "counts": dict(counters),
    }


def compute_tempo_metrics(logs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    deltas: list[float] = []
    for log in logs:
        player_hp = log.get("player_final_hp")
        opponent_hp = log.get("opponent_final_hp")
        if player_hp is None or opponent_hp is None:
            final_hp = log.get("final_hp")
            if isinstance(final_hp, dict):
                player_hp = final_hp.get("player")
                opponent_hp = final_hp.get("opponent")
        if isinstance(player_hp, (int, float)) and isinstance(opponent_hp, (int, float)):
            deltas.append(float(player_hp) - float(opponent_hp))
    if not deltas:
        return {"available": False, "sample_size": 0, "mean_final_hp_delta": None}
    return {"available": True, "sample_size": len(deltas), "mean_final_hp_delta": mean(deltas)}


def compute_report_metadata(logs: Iterable[dict[str, Any]]) -> dict[str, Any]:
    logs_list = list(logs)
    tracked_keys = (
        "commit",
        "content_hash",
        "ruleset",
        "seed",
        "sampler",
        "agent_config",
    )
    metadata: dict[str, Any] = {"sample_size": len(logs_list)}
    for key in tracked_keys:
        values = []
        for log in logs_list:
            if key in log:
                values.append(log.get(key))
        if not values:
            continue
        unique_serialized = sorted(
            {
                json.dumps(value, sort_keys=True)
                for value in values
            }
        )
        if len(unique_serialized) == 1:
            metadata[key] = json.loads(unique_serialized[0])
        else:
            metadata[f"{key}_values"] = [json.loads(value) for value in unique_serialized]
    return metadata


def evaluate_centralization_risk(report: dict[str, Any]) -> dict[str, Any]:
    move_metrics = report["move_usage"]
    archetypes = report["archetype_win_rates"]
    matchup_metrics = report["matchup_diversity"]
    pick_rate_distribution = move_metrics["pick_rate_metrics"]["distribution"]
    matchup_polarization = report["matchup_polarization"]
    repeat_loop_metrics = report["repeat_loop_metrics"]
    non_decision_metrics = report["non_decision_metrics"]
    total_battles = int(report.get("sample_size", 0))
    total_move_uses = int(move_metrics.get("total_uses", 0))
    total_pick_opportunities = int(
        sum(move_metrics.get("pick_rate_metrics", {}).get("opportunity_counts", {}).values())
    )
    max_archetype_battles = max(
        (int(values.get("battles", 0)) for values in archetypes.values()),
        default=0,
    )
    polarization_sample = matchup_polarization.get("sample_floor", {})
    polarization_eligible_cells = int(polarization_sample.get("eligible_cells", 0))
    polarization_coverage = float(polarization_sample.get("coverage", 0.0))

    qualified_rates = [
        data["win_rate"]
        for data in archetypes.values()
        if data["battles"] >= WIN_RATE_MIN_BATTLES
    ]
    win_rate_spread = (
        (max(qualified_rates) - min(qualified_rates))
        if len(qualified_rates) >= 2
        else 0.0
    )
    max_qualified_rate = max(qualified_rates) if qualified_rates else 0.0

    raw_move_flag = (
        move_metrics["top_3_share"] >= MOVE_TOP3_SHARE_ALERT
        or move_metrics["normalized_entropy"] <= MOVE_NORMALIZED_ENTROPY_ALERT
    )
    raw_move_pick_rate_flag = (
        pick_rate_distribution["top_3_share"] >= MOVE_TOP3_SHARE_ALERT
        or pick_rate_distribution["normalized_entropy"] <= MOVE_NORMALIZED_ENTROPY_ALERT
    ) if pick_rate_distribution["total"] > 0 else False
    raw_win_rate_flag = max_qualified_rate >= WIN_RATE_SKEW_ALERT
    raw_matchup_flag = matchup_metrics["unique_ratio"] <= MATCHUP_DIVERSITY_ALERT
    raw_polarization_flag = (
        matchup_polarization["polarization_index"] >= MATCHUP_POLARIZATION_ALERT
    )
    raw_repeat_loop_flag = repeat_loop_metrics["battles_with_streak_ge_8_rate"] > 0.0
    raw_timeout_flag = non_decision_metrics["timeout_rate"] >= TIMEOUT_RATE_ALERT

    sufficiency = {
        "move_usage": (
            total_battles >= RISK_MIN_BATTLES_FOR_FLAGS
            and total_move_uses >= RISK_MIN_MOVE_USES_FOR_FLAGS
        ),
        "move_pick_rate": (
            total_battles >= RISK_MIN_BATTLES_FOR_FLAGS
            and total_pick_opportunities >= RISK_MIN_PICK_OPPORTUNITIES_FOR_FLAGS
        ),
        "win_rate_skew": (
            total_battles >= RISK_MIN_BATTLES_FOR_FLAGS
            and max_archetype_battles >= RISK_MIN_ARCHETYPE_BATTLES_FOR_SKEW
        ),
        "matchup_diversity": total_battles >= RISK_MIN_BATTLES_FOR_FLAGS,
        "matchup_polarization": (
            total_battles >= RISK_MIN_BATTLES_FOR_FLAGS
            and polarization_eligible_cells >= RISK_MIN_POLARIZATION_ELIGIBLE_CELLS
            and polarization_coverage >= RISK_MIN_POLARIZATION_COVERAGE
        ),
        "repeat_loop": total_battles >= RISK_MIN_BATTLES_FOR_FLAGS,
        "timeout_rate": total_battles >= RISK_MIN_BATTLES_FOR_FLAGS,
    }
    warnings: list[str] = []
    if not sufficiency["move_usage"]:
        warnings.append(
            f"move_usage_concentration below sample floor: battles={total_battles}, uses={total_move_uses}"
        )
    if not sufficiency["move_pick_rate"]:
        warnings.append(
            "move_pick_rate_concentration below sample floor: "
            f"battles={total_battles}, opportunities={total_pick_opportunities}"
        )
    if not sufficiency["win_rate_skew"]:
        warnings.append(
            "win_rate_skew below sample floor: "
            f"battles={total_battles}, max_archetype_battles={max_archetype_battles}"
        )
    if not sufficiency["matchup_polarization"]:
        warnings.append(
            "matchup_polarization below sample floor: "
            f"battles={total_battles}, eligible_cells={polarization_eligible_cells}, "
            f"coverage={polarization_coverage:.3f}"
        )

    return {
        "move_usage_concentration": raw_move_flag and sufficiency["move_usage"],
        "move_pick_rate_concentration": raw_move_pick_rate_flag and sufficiency["move_pick_rate"],
        "win_rate_skew": raw_win_rate_flag and sufficiency["win_rate_skew"],
        "matchup_diversity_low": raw_matchup_flag and sufficiency["matchup_diversity"],
        "matchup_polarization_high": raw_polarization_flag and sufficiency["matchup_polarization"],
        "repeat_loop_high": raw_repeat_loop_flag and sufficiency["repeat_loop"],
        "timeout_rate_high": raw_timeout_flag and sufficiency["timeout_rate"],
        "win_rate_spread": win_rate_spread,
        "max_qualified_win_rate": max_qualified_rate,
        "sample_sufficiency": sufficiency,
        "warnings": warnings,
    }


def compute_balance_report(
    logs: Iterable[dict[str, Any]],
    *,
    include_replicator: bool = False,
) -> dict[str, Any]:
    logs_list = list(logs)
    report = {
        "sample_size": len(logs_list),
        "move_usage": compute_move_usage_metrics(logs_list),
        "archetype_win_rates": compute_archetype_win_rates(logs_list),
        "matchup_diversity": compute_matchup_diversity(logs_list),
        "matchup_polarization": compute_matchup_polarization(logs_list),
        "replicator_dynamics": compute_replicator_dynamics(logs_list)
        if include_replicator
        else None,
        "turn_length_metrics": compute_turn_length_metrics(logs_list),
        "repeat_loop_metrics": compute_repeat_loop_metrics(logs_list),
        "non_decision_metrics": compute_non_decision_metrics(logs_list),
        "tempo_metrics": compute_tempo_metrics(logs_list),
        "log_metadata": compute_report_metadata(logs_list),
    }
    report["risk_flags"] = evaluate_centralization_risk(report)
    return report


def _flatten_numeric_values(
    value: Any,
    *,
    prefix: str = "",
) -> dict[str, float]:
    flattened: dict[str, float] = {}
    if isinstance(value, dict):
        for key, nested in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten_numeric_values(nested, prefix=path))
        return flattened
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        flattened[prefix] = float(value)
    return flattened


def compute_report_deltas(
    report: dict[str, Any], baseline_report: dict[str, Any]
) -> dict[str, float]:
    current = _flatten_numeric_values(report)
    baseline = _flatten_numeric_values(baseline_report)
    deltas: dict[str, float] = {}
    for key, current_value in current.items():
        if key not in baseline:
            continue
        deltas[key] = current_value - baseline[key]
    return deltas


def _parse_rule_entries(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    parsed: dict[str, float] = {}
    for key, threshold in value.items():
        if isinstance(key, str) and isinstance(threshold, (int, float)):
            parsed[key] = float(threshold)
    return parsed


def _rule_min_samples_met(report: dict[str, Any], metric_key: str, rules: dict[str, Any]) -> bool:
    min_total_battles = rules.get("min_total_battles")
    if isinstance(min_total_battles, int) and min_total_battles > 0:
        if int(report.get("sample_size", 0)) < min_total_battles:
            return False

    min_cell_battles = rules.get("min_cell_battles")
    if isinstance(min_cell_battles, int) and min_cell_battles > 0 and metric_key.startswith(
        "matchup_polarization."
    ):
        matchups = report.get("matchup_polarization", {}).get("directed_matchups", {})
        eligible = 0
        if isinstance(matchups, dict):
            for cell in matchups.values():
                battles = cell.get("battles") if isinstance(cell, dict) else None
                if isinstance(battles, (int, float)) and battles >= min_cell_battles:
                    eligible += 1
        if eligible == 0:
            return False

    min_opportunities = rules.get("min_opportunities_per_move")
    if isinstance(min_opportunities, int) and min_opportunities > 0 and (
        metric_key.startswith("move_usage.pick_rate_metrics.")
        or metric_key.startswith("risk_flags.move_pick_rate")
    ):
        opportunities = report.get("move_usage", {}).get("pick_rate_metrics", {}).get(
            "opportunity_counts", {}
        )
        if isinstance(opportunities, dict):
            if not any(
                isinstance(v, (int, float)) and v >= min_opportunities
                for v in opportunities.values()
            ):
                return False
    return True


def evaluate_threshold_rules(
    report: dict[str, Any],
    rules: dict[str, Any],
    *,
    baseline_report: dict[str, Any] | None = None,
) -> list[str]:
    numeric = _flatten_numeric_values(report)
    deltas = (
        compute_report_deltas(report, baseline_report) if baseline_report is not None else {}
    )
    failures: list[str] = []

    for key, threshold in _parse_rule_entries(rules.get("absolute_max")).items():
        if not _rule_min_samples_met(report, key, rules):
            continue
        value = numeric.get(key)
        if value is not None and value > threshold:
            failures.append(f"{key}={value:.6f} exceeded absolute_max={threshold:.6f}")
    for key, threshold in _parse_rule_entries(rules.get("absolute_min")).items():
        if not _rule_min_samples_met(report, key, rules):
            continue
        value = numeric.get(key)
        if value is not None and value < threshold:
            failures.append(f"{key}={value:.6f} fell below absolute_min={threshold:.6f}")
    for key, threshold in _parse_rule_entries(rules.get("delta_max")).items():
        if not _rule_min_samples_met(report, key, rules):
            continue
        delta = deltas.get(key)
        if delta is not None and delta > threshold:
            failures.append(f"{key} delta={delta:.6f} exceeded delta_max={threshold:.6f}")
    for key, threshold in _parse_rule_entries(rules.get("delta_min")).items():
        if not _rule_min_samples_met(report, key, rules):
            continue
        delta = deltas.get(key)
        if delta is not None and delta < threshold:
            failures.append(f"{key} delta={delta:.6f} fell below delta_min={threshold:.6f}")

    return failures


def build_violation_explanations(report: dict[str, Any], violations: Iterable[str]) -> dict[str, Any]:
    archetype_rates = report.get("archetype_win_rates", {})
    sorted_archetypes = sorted(
        (
            {
                "archetype": name,
                "win_rate": values.get("win_rate", 0.0),
                "battles": values.get("battles", 0),
                "ci_95": values.get("win_rate_ci_95", {}),
            }
            for name, values in archetype_rates.items()
            if isinstance(values, dict)
        ),
        key=lambda item: item["win_rate"],
        reverse=True,
    )

    return {
        "violations": list(violations),
        "top_moves_by_pick_rate": report.get("move_usage", {})
        .get("pick_rate_metrics", {})
        .get("top_by_pick_rate", []),
        "top_moves_by_uses": report.get("move_usage", {})
        .get("pick_rate_metrics", {})
        .get("top_by_uses", []),
        "top_polarized_matchups": report.get("matchup_polarization", {}).get(
            "top_polarized_matchups", []
        ),
        "win_rate_extremes": {
            "top": sorted_archetypes[:3],
            "bottom": sorted_archetypes[-3:],
        },
        "degeneracy_drivers": {
            "turn_length_p90": report.get("turn_length_metrics", {}).get("p90"),
            "repeat_loop_rate": report.get("repeat_loop_metrics", {}).get(
                "battles_with_streak_ge_8_rate", 0.0
            ),
            "timeout_rate": report.get("non_decision_metrics", {}).get("timeout_rate", 0.0),
        },
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze battle logs for move centralization and archetype skew."
    )
    parser.add_argument(
        "log_path",
        help="Path to a battle log file (JSON array or JSONL).",
    )
    parser.add_argument(
        "--baseline",
        help="Optional baseline report JSON path for delta calculations.",
    )
    parser.add_argument(
        "--fail-on",
        help=(
            "Optional threshold rules JSON path. "
            "Supported keys: absolute_max, absolute_min, delta_max, delta_min, "
            "min_total_battles, min_cell_battles, min_opportunities_per_move."
        ),
    )
    parser.add_argument(
        "--out",
        help="Optional file path to write the computed report JSON.",
    )
    parser.add_argument(
        "--include-replicator",
        action="store_true",
        help="Enable replicator dynamics diagnostics (recommended for nightly runs).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logs = load_battle_logs(args.log_path)
    report = compute_balance_report(logs, include_replicator=args.include_replicator)

    baseline_report = None
    if args.baseline:
        baseline_payload = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        if isinstance(baseline_payload, dict):
            baseline_report = baseline_payload
            report["baseline_deltas"] = compute_report_deltas(report, baseline_report)

    violations: list[str] = []
    if args.fail_on:
        rules_payload = json.loads(Path(args.fail_on).read_text(encoding="utf-8"))
        if isinstance(rules_payload, dict):
            violations = evaluate_threshold_rules(
                report,
                rules_payload,
                baseline_report=baseline_report,
            )
    report["violations"] = violations
    if violations:
        report["violation_explanations"] = build_violation_explanations(report, violations)

    if args.out:
        Path(args.out).write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
