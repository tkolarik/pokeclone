from __future__ import annotations

import json
import os
from typing import Dict, Iterable, List, Sequence, Tuple

from src.core import config


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_type_options(data_dir: str = config.DATA_DIR) -> List[str]:
    path = os.path.join(data_dir, "type_chart.json")
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict):
        return []
    return sorted([str(key) for key in payload.keys() if str(key).strip()])


def load_move_options(data_dir: str = config.DATA_DIR) -> List[str]:
    path = os.path.join(data_dir, "moves.json")
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    move_names = []
    seen = set()
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str):
            continue
        normalized = name.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        move_names.append(normalized)
    return sorted(move_names)


def normalize_single_selection(value: str, allowed_options: Sequence[str]) -> str | None:
    if value in set(allowed_options):
        return value
    return None


def normalize_multi_selection(
    selected_values: Iterable[str], allowed_options: Sequence[str]
) -> Tuple[List[str], List[str]]:
    allowed = set(allowed_options)
    normalized: List[str] = []
    rejected: List[str] = []
    seen = set()
    for value in selected_values:
        if value in seen:
            continue
        seen.add(value)
        if value in allowed:
            normalized.append(value)
        else:
            rejected.append(value)
    return normalized, rejected


def normalize_learnset_entries(
    rows: Sequence[Dict[str, object]],
    allowed_moves: Sequence[str],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    allowed = set(allowed_moves)
    normalized: List[Dict[str, object]] = []
    rejected: List[Dict[str, object]] = []

    for row in rows:
        if not isinstance(row, dict):
            rejected.append({"row": row, "reason": "not_object"})
            continue
        move = row.get("move")
        if move not in allowed:
            rejected.append({"row": row, "reason": "invalid_move"})
            continue
        try:
            level = int(row.get("level", 1))
        except (TypeError, ValueError):
            rejected.append({"row": row, "reason": "invalid_level"})
            continue
        normalized.append({"level": max(1, level), "move": move})

    return normalized, rejected
