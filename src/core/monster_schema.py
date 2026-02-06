from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple


LEGACY_STAT_KEYS = ("max_hp", "attack", "defense")
LEGACY_MOVES_KEY = "moves"
LEGACY_MOVE_POOL_KEY = "move_pool"
CANONICAL_KEYS = ("name", "type", "base_stats", "learnset")


def _normalize_stat_value(value: Any, stat_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid stat value for '{stat_name}': {value!r}")
    return max(1, normalized)


def _normalize_move_list(values: Any, field_name: str) -> List[str]:
    if values is None:
        return []
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{field_name} must be a list of move names.")
    ordered: List[str] = []
    seen = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError(f"Invalid move name in {field_name}: {value!r}")
        name = value.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _expand_learnset_entries(entries: Sequence[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid learnset entry: {entry!r}")

        try:
            level = int(entry.get("level", 1))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid learnset level: {entry.get('level')!r}")
        level = max(1, level)

        if "move" in entry:
            move = entry.get("move")
            if not isinstance(move, str) or not move.strip():
                raise ValueError(f"Invalid learnset move: {move!r}")
            normalized.append({"level": level, "move": move.strip()})
            continue

        if "moves" in entry:
            moves = entry.get("moves")
            if not isinstance(moves, Sequence) or isinstance(moves, (str, bytes)):
                raise ValueError(f"Invalid learnset 'moves' entry: {moves!r}")
            for move in moves:
                if not isinstance(move, str) or not move.strip():
                    raise ValueError(f"Invalid learnset move entry: {move!r}")
                normalized.append({"level": level, "move": move.strip()})
            continue

        raise ValueError(f"Learnset entry missing 'move' or 'moves': {entry!r}")

    return normalized


def _derived_learnset(move_pool: List[str]) -> List[Dict[str, Any]]:
    return [{"level": 1, "move": move} for move in move_pool]


def derive_move_pool_from_learnset(learnset: Sequence[Dict[str, Any]]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for entry in learnset:
        if not isinstance(entry, dict):
            continue
        move_name = entry.get("move")
        if isinstance(move_name, str):
            normalized = move_name.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                ordered.append(normalized)
        moves = entry.get("moves")
        if isinstance(moves, Sequence) and not isinstance(moves, (str, bytes)):
            for move in moves:
                if not isinstance(move, str):
                    continue
                normalized = move.strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    ordered.append(normalized)
    return ordered


def _normalize_base_stats(base_stats: Any) -> Dict[str, int]:
    if not isinstance(base_stats, dict):
        raise ValueError("base_stats must be an object.")
    return {
        "max_hp": _normalize_stat_value(base_stats.get("max_hp", 1), "max_hp"),
        "attack": _normalize_stat_value(base_stats.get("attack", 1), "attack"),
        "defense": _normalize_stat_value(base_stats.get("defense", 1), "defense"),
    }


def normalize_monster(
    monster: Dict[str, Any], *, strict_conflicts: bool = False
) -> Tuple[Dict[str, Any], List[str]]:
    """Normalize a monster record to canonical schema.

    Canonical schema:
    - name (str)
    - type (str)
    - base_stats ({max_hp, attack, defense})
    - learnset ([{level, move}])

    Legacy duplicate fields (`max_hp`, `attack`, `defense`, `move_pool`, `moves`)
    are supported for backward compatibility and stripped from the normalized output.
    """
    if not isinstance(monster, dict):
        raise ValueError(f"Monster record must be an object, got: {type(monster).__name__}")

    warnings: List[str] = []

    name = monster.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Monster 'name' must be a non-empty string.")
    name = name.strip()

    monster_type = monster.get("type")
    if not isinstance(monster_type, str) or not monster_type.strip():
        raise ValueError(f"Monster '{name}' has invalid 'type'.")
    monster_type = monster_type.strip()

    legacy_stats_present = any(key in monster for key in LEGACY_STAT_KEYS)
    if "base_stats" in monster and monster.get("base_stats") is not None:
        normalized_base_stats = _normalize_base_stats(monster["base_stats"])
    else:
        normalized_base_stats = {
            "max_hp": _normalize_stat_value(monster.get("max_hp", 1), "max_hp"),
            "attack": _normalize_stat_value(monster.get("attack", 1), "attack"),
            "defense": _normalize_stat_value(monster.get("defense", 1), "defense"),
        }
        if legacy_stats_present:
            warnings.append(f"Monster '{name}' used legacy root stat fields.")

    if legacy_stats_present:
        legacy_stats = {
            stat: _normalize_stat_value(monster.get(stat, normalized_base_stats[stat]), stat)
            for stat in LEGACY_STAT_KEYS
            if stat in monster
        }
        conflicts = [
            stat
            for stat, legacy_value in legacy_stats.items()
            if normalized_base_stats[stat] != legacy_value
        ]
        if conflicts:
            message = (
                f"Monster '{name}' has conflicting duplicated stat fields: "
                + ", ".join(conflicts)
            )
            if strict_conflicts:
                raise ValueError(message)
            warnings.append(message)

    learnset: List[Dict[str, Any]] = []
    raw_learnset = monster.get("learnset")
    if raw_learnset is not None:
        if not isinstance(raw_learnset, Sequence) or isinstance(raw_learnset, (str, bytes)):
            raise ValueError(f"Monster '{name}' has invalid learnset.")
        learnset = _expand_learnset_entries(raw_learnset)

    legacy_move_pool_present = LEGACY_MOVE_POOL_KEY in monster
    legacy_moves_present = LEGACY_MOVES_KEY in monster
    legacy_move_pool = _normalize_move_list(monster.get(LEGACY_MOVE_POOL_KEY), LEGACY_MOVE_POOL_KEY)
    legacy_moves = _normalize_move_list(monster.get(LEGACY_MOVES_KEY), LEGACY_MOVES_KEY)

    if legacy_move_pool and legacy_moves and legacy_move_pool != legacy_moves:
        message = f"Monster '{name}' has conflicting duplicated legacy move fields."
        if strict_conflicts:
            raise ValueError(message)
        warnings.append(message)

    if not legacy_move_pool and legacy_moves:
        legacy_move_pool = legacy_moves

    if learnset:
        canonical_move_pool = derive_move_pool_from_learnset(learnset)
        if (legacy_move_pool_present or legacy_moves_present) and legacy_move_pool != canonical_move_pool:
            message = f"Monster '{name}' has conflicting duplicated move progression fields."
            if strict_conflicts:
                raise ValueError(message)
            warnings.append(message)
        elif legacy_move_pool_present or legacy_moves_present:
            warnings.append(f"Monster '{name}' included redundant legacy move fields.")
    elif legacy_move_pool:
        learnset = _derived_learnset(legacy_move_pool)
        if legacy_move_pool_present:
            warnings.append(f"Monster '{name}' used legacy 'move_pool' field.")
        if legacy_moves_present:
            warnings.append(f"Monster '{name}' used legacy 'moves' field.")

    normalized_monster: Dict[str, Any] = {
        "name": name,
        "type": monster_type,
        "base_stats": normalized_base_stats,
        "learnset": learnset,
    }

    handled = set(CANONICAL_KEYS) | set(LEGACY_STAT_KEYS) | {LEGACY_MOVES_KEY, LEGACY_MOVE_POOL_KEY}
    for key, value in monster.items():
        if key in handled:
            continue
        normalized_monster[key] = value

    return normalized_monster, warnings


def normalize_monsters(
    monsters: Any, *, strict_conflicts: bool = False
) -> Tuple[List[Dict[str, Any]], List[str]]:
    if not isinstance(monsters, list):
        raise ValueError("monsters.json should contain a list of monsters.")

    normalized: List[Dict[str, Any]] = []
    warnings: List[str] = []
    for index, monster in enumerate(monsters):
        try:
            normalized_monster, monster_warnings = normalize_monster(
                monster, strict_conflicts=strict_conflicts
            )
        except ValueError as exc:
            raise ValueError(f"Monster at index {index}: {exc}")
        normalized.append(normalized_monster)
        warnings.extend(monster_warnings)

    return normalized, warnings
