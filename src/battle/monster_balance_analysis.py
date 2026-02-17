from __future__ import annotations

import argparse
import json
import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, Iterator, Mapping, Sequence

from src.battle import engine
from src.core import config
from src.core.runtime_data_validation import (
    RuntimeDataValidationError,
    load_validated_monsters,
    load_validated_moves,
    load_validated_type_chart,
)


OFFENSIVE_SETUP_WEIGHT = 0.12
DEFENSIVE_SETUP_WEIGHT = 0.12
SETUP_MULTIPLIER_CAP = 0.75
EPSILON = 1e-9
DEFAULT_MAX_SETUP_TURNS = 10
DEGENERATE_SETUP_TURNS_ALERT = 6
DEGENERATE_SETUP_GAIN_ALERT = 1.0


@dataclass(frozen=True)
class MoveSpec:
    name: str
    type: str
    power: int
    effect: Mapping[str, Any] | None


@dataclass(frozen=True)
class MonsterProfile:
    name: str
    type: str
    base_stats: Dict[str, int]
    scaled_stats: Dict[str, int]
    learnset: list[dict[str, Any]]
    available_moves: list[str]


def available_moves_for_level(
    learnset: Sequence[dict[str, Any]],
    level: int,
) -> list[str]:
    """Return deduplicated moves available at or below the requested level."""
    flattened = engine.flatten_learnset(learnset)
    if not flattened:
        return []

    clamped_level = engine.clamp_level(level)
    selected = [move_name for req_level, move_name in flattened if req_level <= clamped_level]
    if not selected:
        selected = [move_name for _, move_name in flattened]

    ordered: list[str] = []
    seen = set()
    for move_name in selected:
        if not isinstance(move_name, str):
            continue
        normalized = move_name.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _moveset_size(move_count: int, max_moves_per_set: int) -> int:
    if move_count <= 0:
        return 0
    return min(max_moves_per_set, move_count)


def moveset_count(move_names: Sequence[str], max_moves_per_set: int) -> int:
    size = _moveset_size(len(move_names), max_moves_per_set)
    if size <= 0:
        return 0
    if len(move_names) <= size:
        return 1
    return math.comb(len(move_names), size)


def iter_movesets(
    move_names: Sequence[str],
    max_moves_per_set: int,
) -> Iterator[tuple[str, ...]]:
    size = _moveset_size(len(move_names), max_moves_per_set)
    if size <= 0:
        return
    if len(move_names) <= size:
        yield tuple(move_names)
        return
    for combo in itertools.combinations(move_names, size):
        yield combo


def _load_move_specs(path: str) -> dict[str, MoveSpec]:
    payload = load_validated_moves(path)
    specs: dict[str, MoveSpec] = {}
    for item in payload:
        name = str(item["name"]).strip()
        specs[name] = MoveSpec(
            name=name,
            type=str(item["type"]).strip(),
            power=int(item["power"]),
            effect=item.get("effect"),
        )
    return specs


def _load_monster_profiles(
    path: str,
    *,
    level: int,
    known_types: Iterable[str],
    known_moves: Iterable[str],
) -> tuple[list[MonsterProfile], list[str]]:
    monsters_payload, warnings = load_validated_monsters(
        path,
        strict_conflicts=False,
        known_types=known_types,
        known_moves=known_moves,
    )
    profiles: list[MonsterProfile] = []
    for monster in monsters_payload:
        base_stats = dict(monster["base_stats"])
        learnset = list(monster.get("learnset", []))
        available = available_moves_for_level(learnset, level)
        if not available:
            continue
        profiles.append(
            MonsterProfile(
                name=str(monster["name"]),
                type=str(monster["type"]),
                base_stats=base_stats,
                scaled_stats=engine.scale_stats(base_stats, level),
                learnset=learnset,
                available_moves=available,
            )
        )
    return profiles, warnings


def _expected_damage(
    attacker: MonsterProfile,
    defender: MonsterProfile,
    move: MoveSpec,
    type_chart: Mapping[str, Mapping[str, float]],
) -> tuple[float, float]:
    if move.power <= 0:
        return 0.0, 1.0
    effectiveness = float(type_chart.get(move.type, {}).get(defender.type, 1.0))
    defender_defense = max(1, int(defender.scaled_stats["defense"]))
    base_damage = (
        config.DAMAGE_ATTACK_FACTOR * attacker.scaled_stats["attack"] * move.power
    ) / (config.DAMAGE_DEFENSE_FACTOR * defender_defense)
    avg_variance = (config.DAMAGE_RANDOM_MIN + config.DAMAGE_RANDOM_MAX) / 2
    expected = (base_damage + config.DAMAGE_BASE_OFFSET) * effectiveness * avg_variance
    if effectiveness > 0 and expected < 1:
        expected = 1.0
    return expected, effectiveness


def _moveset_modifiers(
    moveset: Sequence[str],
    move_specs: Mapping[str, MoveSpec],
) -> tuple[float, float]:
    offensive_stages = 0
    defensive_stages = 0
    for move_name in moveset:
        move = move_specs.get(move_name)
        if move is None or move.power != 0 or not isinstance(move.effect, Mapping):
            continue
        target = str(move.effect.get("target", "")).strip().lower()
        stat = str(move.effect.get("stat", "")).strip().lower()
        raw_change = move.effect.get("change", 0)
        try:
            change = int(raw_change)
        except (TypeError, ValueError):
            continue
        if change <= 0:
            continue

        if target == "self" and stat == "attack":
            offensive_stages += change
        elif target == "opponent" and stat == "defense":
            offensive_stages += change
        elif target == "self" and stat == "defense":
            defensive_stages += change
        elif target == "opponent" and stat == "attack":
            defensive_stages += change

    offensive_mult = 1.0 + min(SETUP_MULTIPLIER_CAP, offensive_stages * OFFENSIVE_SETUP_WEIGHT)
    defensive_mult = 1.0 + min(SETUP_MULTIPLIER_CAP, defensive_stages * DEFENSIVE_SETUP_WEIGHT)
    return offensive_mult, defensive_mult


def _multiplier_for_repeated_uses(change: int, uses: int) -> float:
    if change <= 0 or uses <= 0:
        return 1.0
    effective_uses = min(int(uses), config.SETUP_MOVE_MAX_USES)
    stage = 0
    for _ in range(effective_uses):
        stage = engine.clamp_stat_stage(stage + change)
    return engine.stat_stage_multiplier(stage)


def _setup_change_profile(
    moveset: Sequence[str],
    move_specs: Mapping[str, MoveSpec],
) -> tuple[int, int]:
    """Return strongest offensive and defensive setup change available in this moveset."""
    best_off_change = 0
    best_def_change = 0
    for move_name in moveset:
        move = move_specs.get(move_name)
        if move is None or move.power != 0 or not isinstance(move.effect, Mapping):
            continue
        target = str(move.effect.get("target", "")).strip().lower()
        stat = str(move.effect.get("stat", "")).strip().lower()
        raw_change = move.effect.get("change", 0)
        try:
            change = int(raw_change)
        except (TypeError, ValueError):
            continue
        if change <= 0:
            continue
        if (target == "self" and stat == "attack") or (target == "opponent" and stat == "defense"):
            best_off_change = max(best_off_change, change)
        if (target == "self" and stat == "defense") or (target == "opponent" and stat == "attack"):
            best_def_change = max(best_def_change, change)
    return best_off_change, best_def_change


def _best_damage_for_moveset(
    attacker: MonsterProfile,
    defender: MonsterProfile,
    moveset: Sequence[str],
    move_specs: Mapping[str, MoveSpec],
    type_chart: Mapping[str, Mapping[str, float]],
) -> tuple[float, str, float]:
    best_damage = 0.0
    best_move = "Struggle"
    best_effectiveness = 1.0
    for move_name in moveset:
        move = move_specs.get(move_name)
        if move is None:
            continue
        damage, effectiveness = _expected_damage(attacker, defender, move, type_chart)
        if damage > best_damage:
            best_damage = damage
            best_move = move.name
            best_effectiveness = effectiveness
    if best_damage <= 0:
        return 1.0, best_move, 1.0
    return best_damage, best_move, best_effectiveness


def _duel_advantage(
    attacker: MonsterProfile,
    attacker_moveset: Sequence[str],
    defender: MonsterProfile,
    defender_moveset: Sequence[str],
    move_specs: Mapping[str, MoveSpec],
    type_chart: Mapping[str, Mapping[str, float]],
    *,
    max_setup_turns: int,
) -> dict[str, float]:
    atk_off_change, atk_def_change = _setup_change_profile(attacker_moveset, move_specs)
    def_off_change, def_def_change = _setup_change_profile(defender_moveset, move_specs)

    attacker_damage, _, _ = _best_damage_for_moveset(
        attacker, defender, attacker_moveset, move_specs, type_chart
    )
    defender_damage, _, _ = _best_damage_for_moveset(
        defender, attacker, defender_moveset, move_specs, type_chart
    )
    max_setup = max(0, max_setup_turns)

    def _advantage_for_setups(attacker_setup: int, defender_setup: int) -> float:
        atk_off_mult = _multiplier_for_repeated_uses(atk_off_change, attacker_setup)
        atk_def_mult = _multiplier_for_repeated_uses(atk_def_change, attacker_setup)
        def_off_mult = _multiplier_for_repeated_uses(def_off_change, defender_setup)
        def_def_mult = _multiplier_for_repeated_uses(def_def_change, defender_setup)

        adjusted_attacker_damage = attacker_damage * atk_off_mult
        adjusted_defender_damage = defender_damage * def_off_mult
        defender_effective_hp = max(1.0, defender.scaled_stats["max_hp"] * def_def_mult)
        attacker_effective_hp = max(1.0, attacker.scaled_stats["max_hp"] * atk_def_mult)
        turns_to_ko_defender = attacker_setup + (
            defender_effective_hp / max(EPSILON, adjusted_attacker_damage)
        )
        turns_to_ko_attacker = defender_setup + (
            attacker_effective_hp / max(EPSILON, adjusted_defender_damage)
        )
        return turns_to_ko_attacker - turns_to_ko_defender

    baseline_advantage = _advantage_for_setups(0, 0)

    # Conservative equilibrium estimate: attacker maximizes minimum advantage over defender responses.
    best_attacker_setup = 0
    best_counter_setup = 0
    equilibrium_advantage = -float("inf")
    for attacker_setup in range(max_setup + 1):
        worst_advantage = float("inf")
        worst_counter = 0
        for defender_setup in range(max_setup + 1):
            advantage = _advantage_for_setups(attacker_setup, defender_setup)
            if advantage < worst_advantage:
                worst_advantage = advantage
                worst_counter = defender_setup
        if worst_advantage > equilibrium_advantage:
            equilibrium_advantage = worst_advantage
            best_attacker_setup = attacker_setup
            best_counter_setup = worst_counter

    setup_gain = equilibrium_advantage - baseline_advantage
    return {
        "advantage": equilibrium_advantage,
        "baseline_advantage": baseline_advantage,
        "best_setup_turns": float(best_attacker_setup),
        "counter_setup_turns": float(best_counter_setup),
        "setup_gain": setup_gain,
    }


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[float, float, float, float]:
    return (
        float(candidate["average_duel_advantage"]),
        float(candidate["worst_duel_advantage"]),
        float(candidate["favorable_matchup_rate"]),
        float(candidate["average_effectiveness"]),
    )


def _build_pool_damage_matrix(
    profiles: Sequence[MonsterProfile],
    move_specs: Mapping[str, MoveSpec],
    type_chart: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, float]]:
    matrix: dict[str, dict[str, float]] = {profile.name: {} for profile in profiles}
    for attacker in profiles:
        attacker_pool = tuple(attacker.available_moves)
        for defender in profiles:
            if attacker.name == defender.name:
                continue
            damage, _, _ = _best_damage_for_moveset(
                attacker, defender, attacker_pool, move_specs, type_chart
            )
            matrix[attacker.name][defender.name] = max(1.0, damage)
    return matrix


def analyze_monster_balance(
    monsters: Sequence[dict[str, Any]],
    moves: Sequence[dict[str, Any]],
    type_chart: Mapping[str, Mapping[str, float]],
    *,
    level: int = 100,
    max_moves_per_set: int = config.MAX_BATTLE_MOVES,
    top_movesets_per_monster: int = 3,
    max_setup_turns: int = DEFAULT_MAX_SETUP_TURNS,
) -> dict[str, Any]:
    """Analyze level-gated learnsets and moveset combinations for dominance risk."""
    clamped_level = engine.clamp_level(level)
    if max_moves_per_set <= 0:
        raise ValueError("max_moves_per_set must be at least 1")
    if top_movesets_per_monster <= 0:
        raise ValueError("top_movesets_per_monster must be at least 1")

    move_specs: dict[str, MoveSpec] = {}
    for item in moves:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        move_specs[name] = MoveSpec(
            name=name,
            type=str(item.get("type", "Normal")).strip() or "Normal",
            power=int(item.get("power", 0)),
            effect=item.get("effect"),
        )

    profiles: list[MonsterProfile] = []
    for monster in monsters:
        name = str(monster.get("name", "")).strip()
        if not name:
            continue
        learnset = list(monster.get("learnset", []))
        available = [move for move in available_moves_for_level(learnset, clamped_level) if move in move_specs]
        if not available:
            continue
        base_stats = dict(monster.get("base_stats", {}))
        if not {"max_hp", "attack", "defense"}.issubset(base_stats):
            continue
        profiles.append(
            MonsterProfile(
                name=name,
                type=str(monster.get("type", "")).strip() or "Normal",
                base_stats={key: int(base_stats[key]) for key in ("max_hp", "attack", "defense")},
                scaled_stats=engine.scale_stats(base_stats, clamped_level),
                learnset=learnset,
                available_moves=available,
            )
        )

    if len(profiles) < 2:
        return {
            "level": clamped_level,
            "max_moves_per_set": max_moves_per_set,
            "monster_count": len(profiles),
            "move_count": len(move_specs),
            "monster_analyses": [],
            "ranked_monsters": [],
            "dominance_summary": {},
        }

    pool_damage = _build_pool_damage_matrix(profiles, move_specs, type_chart)

    analyses_by_name: dict[str, dict[str, Any]] = {}
    selected_movesets: dict[str, tuple[str, ...]] = {}
    selected_scores: dict[str, float] = {}

    for profile in profiles:
        combination_total = moveset_count(profile.available_moves, max_moves_per_set)
        if combination_total <= 0:
            continue

        top_candidates: list[dict[str, Any]] = []
        best_candidate: dict[str, Any] | None = None

        for moveset in iter_movesets(profile.available_moves, max_moves_per_set):
            offensive_mult, defensive_mult = _moveset_modifiers(moveset, move_specs)
            duel_scores: list[float] = []
            effectiveness_scores: list[float] = []
            setup_turns_list: list[float] = []
            setup_gain_list: list[float] = []
            best_moves_vs_opponents: dict[str, str] = {}

            for opponent in profiles:
                if opponent.name == profile.name:
                    continue
                outgoing_damage, best_move, effectiveness = _best_damage_for_moveset(
                    profile, opponent, moveset, move_specs, type_chart
                )
                outgoing_damage *= offensive_mult
                duel_result = _duel_advantage(
                    profile,
                    moveset,
                    opponent,
                    tuple(opponent.available_moves[: max_moves_per_set]),
                    move_specs,
                    type_chart,
                    max_setup_turns=max_setup_turns,
                )
                duel_scores.append(float(duel_result["advantage"]))
                setup_turns_list.append(float(duel_result["best_setup_turns"]))
                setup_gain_list.append(float(duel_result["setup_gain"]))
                effectiveness_scores.append(effectiveness)
                best_moves_vs_opponents[opponent.name] = best_move

            candidate = {
                "moveset": list(moveset),
                "average_duel_advantage": mean(duel_scores),
                "worst_duel_advantage": min(duel_scores),
                "favorable_matchup_rate": (
                    sum(1 for score in duel_scores if score > 0) / len(duel_scores)
                    if duel_scores
                    else 0.0
                ),
                "average_effectiveness": mean(effectiveness_scores) if effectiveness_scores else 1.0,
                "offensive_multiplier": offensive_mult,
                "defensive_multiplier": defensive_mult,
                "average_best_setup_turns": mean(setup_turns_list) if setup_turns_list else 0.0,
                "max_best_setup_turns": max(setup_turns_list) if setup_turns_list else 0.0,
                "average_setup_gain": mean(setup_gain_list) if setup_gain_list else 0.0,
                "degenerate_setup_matchup_rate": (
                    sum(
                        1
                        for turns, gain in zip(setup_turns_list, setup_gain_list)
                        if turns >= DEGENERATE_SETUP_TURNS_ALERT and gain >= DEGENERATE_SETUP_GAIN_ALERT
                    )
                    / len(setup_turns_list)
                    if setup_turns_list
                    else 0.0
                ),
                "best_move_by_opponent": best_moves_vs_opponents,
            }

            if best_candidate is None or _candidate_sort_key(candidate) > _candidate_sort_key(best_candidate):
                best_candidate = candidate

            top_candidates.append(candidate)
            top_candidates.sort(key=_candidate_sort_key, reverse=True)
            if len(top_candidates) > top_movesets_per_monster:
                top_candidates.pop()

        if best_candidate is None:
            continue

        selected_movesets[profile.name] = tuple(best_candidate["moveset"])
        selected_scores[profile.name] = float(best_candidate["average_duel_advantage"])
        analyses_by_name[profile.name] = {
            "name": profile.name,
            "type": profile.type,
            "base_stats": profile.base_stats,
            "scaled_stats": profile.scaled_stats,
            "available_move_count": len(profile.available_moves),
            "available_moves": profile.available_moves,
            "moveset_count": combination_total,
            "best_moveset": best_candidate["moveset"],
            "best_moveset_metrics": {
                "average_duel_advantage": best_candidate["average_duel_advantage"],
                "worst_duel_advantage": best_candidate["worst_duel_advantage"],
                "favorable_matchup_rate": best_candidate["favorable_matchup_rate"],
                "average_effectiveness": best_candidate["average_effectiveness"],
                "offensive_multiplier": best_candidate["offensive_multiplier"],
                "defensive_multiplier": best_candidate["defensive_multiplier"],
                "average_best_setup_turns": best_candidate["average_best_setup_turns"],
                "max_best_setup_turns": best_candidate["max_best_setup_turns"],
                "average_setup_gain": best_candidate["average_setup_gain"],
                "degenerate_setup_matchup_rate": best_candidate["degenerate_setup_matchup_rate"],
            },
            "top_movesets": top_candidates,
            "pairwise": {},
        }

    names = sorted(selected_movesets.keys())
    pairwise_adv: dict[str, list[float]] = {name: [] for name in names}
    wins: dict[str, int] = {name: 0 for name in names}
    losses: dict[str, int] = {name: 0 for name in names}
    ties: dict[str, int] = {name: 0 for name in names}

    profiles_by_name = {profile.name: profile for profile in profiles}
    for name_a in names:
        for name_b in names:
            if name_a == name_b:
                continue
            profile_a = profiles_by_name[name_a]
            profile_b = profiles_by_name[name_b]
            advantage = _duel_advantage(
                profile_a,
                selected_movesets[name_a],
                profile_b,
                selected_movesets[name_b],
                move_specs,
                type_chart,
                max_setup_turns=max_setup_turns,
            )
            pairwise_value = float(advantage["advantage"])
            pairwise_adv[name_a].append(pairwise_value)
            analyses_by_name[name_a]["pairwise"][name_b] = pairwise_value

        for name_b in names:
            if name_a >= name_b:
                continue
            adv_ab = analyses_by_name[name_a]["pairwise"][name_b]
            if adv_ab > 0:
                wins[name_a] += 1
                losses[name_b] += 1
            elif adv_ab < 0:
                wins[name_b] += 1
                losses[name_a] += 1
            else:
                ties[name_a] += 1
                ties[name_b] += 1

    ranked: list[dict[str, Any]] = []
    for name in names:
        opponents = max(1, len(names) - 1)
        win_rate = (wins[name] + 0.5 * ties[name]) / opponents
        avg_adv = mean(pairwise_adv[name]) if pairwise_adv[name] else 0.0
        analyses_by_name[name]["pairwise_summary"] = {
            "wins": wins[name],
            "losses": losses[name],
            "ties": ties[name],
            "win_rate": win_rate,
            "average_duel_advantage": avg_adv,
        }
        ranked.append(
            {
                "name": name,
                "type": analyses_by_name[name]["type"],
                "win_rate": win_rate,
                "average_duel_advantage": avg_adv,
                "moveset_count": analyses_by_name[name]["moveset_count"],
                "best_moveset": analyses_by_name[name]["best_moveset"],
                "best_moveset_score": selected_scores[name],
            }
        )

    ranked.sort(
        key=lambda item: (
            float(item["win_rate"]),
            float(item["average_duel_advantage"]),
            float(item["best_moveset_score"]),
        ),
        reverse=True,
    )

    win_rates = [item["win_rate"] for item in ranked]
    top_win_rate = win_rates[0] if win_rates else 0.0
    second_win_rate = win_rates[1] if len(win_rates) > 1 else 0.0
    median_win_rate = median(win_rates) if win_rates else 0.0
    monster_analyses = [analyses_by_name[name] for name in sorted(analyses_by_name.keys())]
    dominance_summary = {
        "top_monster": ranked[0]["name"] if ranked else None,
        "top_win_rate": top_win_rate,
        "second_win_rate": second_win_rate,
        "median_win_rate": median_win_rate,
        "top_vs_second_gap": top_win_rate - second_win_rate,
        "top_vs_median_gap": top_win_rate - median_win_rate,
        "potentially_dominant": bool(
            ranked
            and top_win_rate >= 0.70
            and (top_win_rate - second_win_rate) >= 0.15
        ),
        "high_setup_reliance_monsters": [
            analysis["name"]
            for analysis in monster_analyses
            if analysis["best_moveset_metrics"]["degenerate_setup_matchup_rate"] >= 0.40
        ],
    }
    return {
        "level": clamped_level,
        "max_moves_per_set": max_moves_per_set,
        "monster_count": len(monster_analyses),
        "move_count": len(move_specs),
        "monster_analyses": monster_analyses,
        "ranked_monsters": ranked,
        "dominance_summary": dominance_summary,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze monster dominance from base stats and all legal move combinations "
            "available at a target level."
        )
    )
    parser.add_argument(
        "--level",
        type=int,
        default=100,
        help="Target level used to gate learnsets and scale stats (default: 100).",
    )
    parser.add_argument(
        "--max-moves-per-set",
        type=int,
        default=config.MAX_BATTLE_MOVES,
        help=f"Maximum moves per evaluated moveset (default: {config.MAX_BATTLE_MOVES}).",
    )
    parser.add_argument(
        "--top-movesets-per-monster",
        type=int,
        default=3,
        help="How many top movesets to keep per monster in the report (default: 3).",
    )
    parser.add_argument(
        "--max-setup-turns",
        type=int,
        default=DEFAULT_MAX_SETUP_TURNS,
        help=(
            "Maximum repeated setup turns to evaluate for degenerate strategies "
            f"(default: {DEFAULT_MAX_SETUP_TURNS})."
        ),
    )
    parser.add_argument(
        "--monsters",
        default=str(Path(config.DATA_DIR) / "monsters.json"),
        help="Path to monsters.json (default: data/monsters.json).",
    )
    parser.add_argument(
        "--moves",
        default=str(Path(config.DATA_DIR) / "moves.json"),
        help="Path to moves.json (default: data/moves.json).",
    )
    parser.add_argument(
        "--type-chart",
        default=str(Path(config.DATA_DIR) / "type_chart.json"),
        help="Path to type_chart.json (default: data/type_chart.json).",
    )
    parser.add_argument(
        "--out",
        help="Optional output path for JSON report.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        move_specs = _load_move_specs(args.moves)
        type_chart = load_validated_type_chart(args.type_chart)
        profiles, warnings = _load_monster_profiles(
            args.monsters,
            level=args.level,
            known_types=type_chart.keys(),
            known_moves=move_specs.keys(),
        )
    except (OSError, json.JSONDecodeError, RuntimeDataValidationError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2

    monsters_payload = [
        {
            "name": profile.name,
            "type": profile.type,
            "base_stats": profile.base_stats,
            "learnset": profile.learnset,
        }
        for profile in profiles
    ]
    report = analyze_monster_balance(
        monsters_payload,
        [
            {
                "name": move.name,
                "type": move.type,
                "power": move.power,
                "effect": dict(move.effect) if isinstance(move.effect, Mapping) else move.effect,
            }
            for move in move_specs.values()
        ],
        type_chart,
        level=args.level,
        max_moves_per_set=args.max_moves_per_set,
        top_movesets_per_monster=args.top_movesets_per_monster,
        max_setup_turns=args.max_setup_turns,
    )
    report["schema_warnings"] = warnings

    serialized = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
