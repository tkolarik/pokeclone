import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.core import config


class Move:
    def __init__(self, name: str, type_: str, power: int, effect: Optional[Dict[str, Any]] = None):
        self.name = name
        self.type = type_
        self.power = power
        self.effect = effect


class Creature:
    def __init__(
        self,
        name: str,
        type_: str,
        max_hp: int,
        attack: int,
        defense: int,
        moves: List[Move],
        sprite: Any,
        level: int = 1,
        base_stats: Optional[Dict[str, int]] = None,
        move_pool: Optional[List[str]] = None,
        learnset: Optional[List[Dict[str, Any]]] = None,
    ):
        self.name = name
        self.type = type_
        self.level = level
        self.base_stats = base_stats or {
            "max_hp": max_hp,
            "attack": attack,
            "defense": defense,
        }
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.attack = attack
        self.defense = defense
        self.moves = moves
        self.move_pool = move_pool or []
        self.learnset = learnset or []
        self.sprite = sprite

    def is_alive(self) -> bool:
        return self.current_hp > 0


def clamp_level(level: Any) -> int:
    try:
        level_value = int(level)
    except (TypeError, ValueError):
        level_value = config.DEFAULT_MONSTER_LEVEL
    return max(config.MIN_MONSTER_LEVEL, min(config.MAX_MONSTER_LEVEL, level_value))


def level_modifier(level: int) -> float:
    return 1 + (clamp_level(level) - 1) * config.LEVEL_STAT_GROWTH


def scale_stat(base_stat: int, level: int) -> int:
    return max(1, int(round(base_stat * level_modifier(level))))


def scale_stats(base_stats: Dict[str, int], level: int) -> Dict[str, int]:
    return {
        "max_hp": scale_stat(base_stats.get("max_hp", 1), level),
        "attack": scale_stat(base_stats.get("attack", 1), level),
        "defense": scale_stat(base_stats.get("defense", 1), level),
    }


def flatten_learnset(learnset: Sequence[Dict[str, Any]]) -> List[Tuple[int, str]]:
    flattened: List[Tuple[int, str]] = []
    for entry in learnset:
        level = entry.get("level", 1)
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = 1
        if "move" in entry:
            flattened.append((level, entry["move"]))
        elif "moves" in entry:
            for move_name in entry["moves"]:
                flattened.append((level, move_name))
    return flattened


def build_moves_for_level(learnset: Sequence[Dict[str, Any]], level: int, moves_dict: Dict[str, Move]) -> List[Move]:
    flattened = flatten_learnset(learnset)
    available = [move_name for lvl, move_name in flattened if lvl <= level]
    if not available:
        available = [move_name for _, move_name in flattened]
    seen = set()
    ordered = []
    for move_name in available:
        if move_name not in seen:
            seen.add(move_name)
            ordered.append(move_name)
    if len(ordered) > config.MAX_BATTLE_MOVES:
        ordered = ordered[-config.MAX_BATTLE_MOVES:]
    return [moves_dict.get(move_name, Move(move_name, "Normal", 50)) for move_name in ordered]


def apply_stat_change(creature: Creature, stat: str, change: int) -> Optional[Dict[str, Any]]:
    if not hasattr(creature, stat):
        return None

    current_stat_value = getattr(creature, stat)
    if change > 0:
        multiplier = 1 + config.STAT_CHANGE_MULTIPLIER / (2 ** (change - 1))
        new_stat_value = int(current_stat_value * multiplier)
    elif change < 0:
        divider = 1 + config.STAT_CHANGE_MULTIPLIER / (2 ** (abs(change) - 1))
        if divider == 0:
            new_stat_value = current_stat_value
        else:
            new_stat_value = int(current_stat_value / divider)
    else:
        new_stat_value = current_stat_value

    setattr(creature, stat, new_stat_value)
    return {
        "kind": "stat_change",
        "creature": creature.name,
        "stat": stat,
        "change": change,
        "before": current_stat_value,
        "after": new_stat_value,
    }


def calculate_damage(
    attacker: Creature,
    defender: Creature,
    move: Move,
    *,
    type_chart: Dict[str, Dict[str, float]],
    rng_uniform: Optional[Callable[[float, float], float]] = None,
    stat_change_fn: Optional[Callable[[Creature, str, int], Any]] = None,
) -> Tuple[int, float]:
    if rng_uniform is None:
        rng_uniform = random.uniform
    if stat_change_fn is None:
        stat_change_fn = apply_stat_change

    if move.power == 0:
        effect = move.effect or {}
        target = effect.get("target")
        stat = effect.get("stat")
        change = effect.get("change", 0)
        if target and stat and change != 0:
            if target == "self":
                stat_change_fn(attacker, stat, change)
            else:
                stat_change_fn(defender, stat, -change)
        return 0, 1

    effectiveness = type_chart.get(move.type, {}).get(defender.type, 1)
    defender_defense = max(1, defender.defense)
    base_damage = (
        config.DAMAGE_ATTACK_FACTOR * attacker.attack * move.power
    ) / (config.DAMAGE_DEFENSE_FACTOR * defender_defense)
    damage = int(
        (base_damage + config.DAMAGE_BASE_OFFSET)
        * effectiveness
        * rng_uniform(config.DAMAGE_RANDOM_MIN, config.DAMAGE_RANDOM_MAX)
    )
    if effectiveness > 0 and move.power > 0 and damage <= 0:
        damage = 1
    return damage, effectiveness


def _expected_damage(attacker: Creature, defender: Creature, move: Move, type_chart: Dict[str, Dict[str, float]]) -> Tuple[float, float]:
    effectiveness = type_chart.get(move.type, {}).get(defender.type, 1)
    defender_defense = max(1, defender.defense)
    base_damage = (
        config.DAMAGE_ATTACK_FACTOR * attacker.attack * move.power
    ) / (config.DAMAGE_DEFENSE_FACTOR * defender_defense)
    avg_variance = (config.DAMAGE_RANDOM_MIN + config.DAMAGE_RANDOM_MAX) / 2
    expected = (base_damage + config.DAMAGE_BASE_OFFSET) * effectiveness * avg_variance
    return expected, effectiveness


def _stat_move_score(attacker: Creature, defender: Creature, move: Move) -> float:
    if not move.effect:
        return 0
    target = move.effect.get("target")
    stat = move.effect.get("stat")
    change = move.effect.get("change", 0)
    if not target or not stat or change == 0:
        return 0

    if target == "self":
        base = attacker.base_stats.get(stat, getattr(attacker, stat, 0))
        current = getattr(attacker, stat, base)
        if current < base * 1.2:
            score = 8 * change
        elif current < base * 1.5:
            score = 4 * change
        else:
            score = 1 * change
    else:
        base = defender.base_stats.get(stat, getattr(defender, stat, 0))
        current = getattr(defender, stat, base)
        if current > base * 1.2:
            score = 7 * change
        elif current > base * 1.05:
            score = 3 * change
        else:
            score = 1 * change

    attacker_hp_ratio = attacker.current_hp / attacker.max_hp if attacker.max_hp else 0
    defender_hp_ratio = defender.current_hp / defender.max_hp if defender.max_hp else 0
    if attacker_hp_ratio < 0.35:
        score *= 0.5
    if defender_hp_ratio < 0.3:
        score *= 0.25
    return score


def opponent_choose_move(
    attacker: Creature,
    defender: Creature,
    *,
    type_chart: Dict[str, Dict[str, float]],
    choice_fn: Optional[Callable[[Sequence[Move]], Move]] = None,
) -> Optional[Move]:
    if not attacker.moves:
        return None
    if choice_fn is None:
        choice_fn = random.choice

    scored_moves: List[Tuple[float, Move]] = []
    for move in attacker.moves:
        if move.power > 0:
            expected, effectiveness = _expected_damage(attacker, defender, move, type_chart)
            score = expected
            if expected >= defender.current_hp:
                score += 50
            if effectiveness > 1:
                score += 10
            elif effectiveness == 0:
                score -= 20
        else:
            score = _stat_move_score(attacker, defender, move)
        scored_moves.append((score, move))

    scored_moves.sort(key=lambda item: item[0], reverse=True)
    best_score = scored_moves[0][0]
    if best_score == 0:
        return choice_fn(attacker.moves)

    threshold = best_score * 0.95
    top_moves = [move for score, move in scored_moves if score >= threshold]
    return choice_fn(top_moves)


@dataclass
class BattleTurnResult:
    actor: str
    move: Optional[Move]
    damage: int
    effectiveness: float
    stat_events: List[Dict[str, Any]] = field(default_factory=list)
    attacker_hp_after: int = 0
    defender_hp_after: int = 0
    defender_fainted: bool = False
    winner: Optional[str] = None


class BattleEngine:
    """Pure battle engine with deterministic, turn-resolution APIs."""

    def __init__(
        self,
        player: Creature,
        opponent: Creature,
        *,
        type_chart: Optional[Dict[str, Dict[str, float]]] = None,
        rng: Any = None,
    ) -> None:
        self.player = player
        self.opponent = opponent
        self.type_chart = type_chart or {}
        self.rng = rng or random
        self.turn = "player"
        self.winner: Optional[str] = None

    def _uniform(self, low: float, high: float) -> float:
        return self.rng.uniform(low, high)

    def _choice(self, items: Sequence[Move]) -> Move:
        return self.rng.choice(list(items))

    def _resolve_turn(self, actor: str, move: Optional[Move]) -> BattleTurnResult:
        if self.winner:
            attacker = self.player if actor == "player" else self.opponent
            defender = self.opponent if actor == "player" else self.player
            return BattleTurnResult(
                actor=actor,
                move=move,
                damage=0,
                effectiveness=1,
                attacker_hp_after=attacker.current_hp,
                defender_hp_after=defender.current_hp,
                defender_fainted=not defender.is_alive(),
                winner=self.winner,
            )

        if self.turn != actor:
            raise RuntimeError(f"It is {self.turn}'s turn, not {actor}'s turn.")

        attacker = self.player if actor == "player" else self.opponent
        defender = self.opponent if actor == "player" else self.player

        if move is None:
            self.turn = "opponent" if actor == "player" else "player"
            return BattleTurnResult(
                actor=actor,
                move=None,
                damage=0,
                effectiveness=1,
                attacker_hp_after=attacker.current_hp,
                defender_hp_after=defender.current_hp,
                defender_fainted=not defender.is_alive(),
                winner=None,
            )

        stat_events: List[Dict[str, Any]] = []

        def _track_stat_change(target_creature: Creature, stat: str, change: int) -> None:
            event = apply_stat_change(target_creature, stat, change)
            if event:
                stat_events.append(event)

        damage, effectiveness = calculate_damage(
            attacker,
            defender,
            move,
            type_chart=self.type_chart,
            rng_uniform=self._uniform,
            stat_change_fn=_track_stat_change,
        )
        defender.current_hp = max(0, defender.current_hp - damage)

        defender_fainted = not defender.is_alive()
        winner = actor if defender_fainted else None
        if winner:
            self.winner = winner
        else:
            self.turn = "opponent" if actor == "player" else "player"

        return BattleTurnResult(
            actor=actor,
            move=move,
            damage=damage,
            effectiveness=effectiveness,
            stat_events=stat_events,
            attacker_hp_after=attacker.current_hp,
            defender_hp_after=defender.current_hp,
            defender_fainted=defender_fainted,
            winner=winner,
        )

    def resolve_player_turn(self, move: Optional[Move]) -> BattleTurnResult:
        return self._resolve_turn("player", move)

    def resolve_opponent_turn(self, move: Optional[Move] = None) -> BattleTurnResult:
        selected_move = move
        if selected_move is None:
            selected_move = opponent_choose_move(
                self.opponent,
                self.player,
                type_chart=self.type_chart,
                choice_fn=self._choice,
            )
        return self._resolve_turn("opponent", selected_move)

    def resolve_round(self, player_move: Optional[Move], opponent_move: Optional[Move] = None) -> List[BattleTurnResult]:
        results = [self.resolve_player_turn(player_move)]
        if self.winner is None:
            results.append(self.resolve_opponent_turn(opponent_move))
        return results
