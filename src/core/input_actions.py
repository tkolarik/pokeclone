from __future__ import annotations

import json
import os
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import pygame

from src.core import config


ActionBindings = Dict[str, Tuple[int, ...]]


DEFAULT_ACTION_BINDINGS: ActionBindings = {
    "confirm": (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER),
    "cancel": (pygame.K_ESCAPE,),
    "backspace": (pygame.K_BACKSPACE,),
    "up": (pygame.K_UP,),
    "down": (pygame.K_DOWN,),
    "left": (pygame.K_LEFT,),
    "right": (pygame.K_RIGHT,),
    "move_up": (pygame.K_UP, pygame.K_w),
    "move_down": (pygame.K_DOWN, pygame.K_s),
    "move_left": (pygame.K_LEFT, pygame.K_a),
    "move_right": (pygame.K_RIGHT, pygame.K_d),
    "page_next": (pygame.K_RIGHTBRACKET,),
    "page_prev": (pygame.K_LEFTBRACKET,),
    "clear": (pygame.K_c,),
    "done": (pygame.K_d,),
    "reload": (pygame.K_r,),
    "debug_toggle": (pygame.K_F1,),
    "interact": (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER),
}

EXCLUSIVE_ACTION_GROUPS: Tuple[Tuple[str, ...], ...] = (
    ("up", "down"),
    ("left", "right"),
    ("move_up", "move_down"),
    ("move_left", "move_right"),
    ("confirm", "cancel"),
    ("page_next", "page_prev"),
)


def _resolve_key_code(raw_key: object) -> Optional[int]:
    if isinstance(raw_key, int):
        return raw_key
    if not isinstance(raw_key, str):
        return None
    token = raw_key.strip()
    if not token:
        return None
    if token.startswith("K_"):
        token = token[2:]
    try:
        return pygame.key.key_code(token.lower())
    except (ValueError, TypeError):
        return None


def _normalize_keys(raw_keys: Sequence[object]) -> Tuple[int, ...]:
    normalized: List[int] = []
    seen: Set[int] = set()
    for raw_key in raw_keys:
        key_code = _resolve_key_code(raw_key)
        if key_code is None or key_code in seen:
            continue
        seen.add(key_code)
        normalized.append(key_code)
    return tuple(normalized)


class InputActionMap:
    """Maps physical input (currently keyboard) to logical game actions."""

    def __init__(self, bindings: Optional[Mapping[str, Sequence[object]]] = None) -> None:
        source = dict(DEFAULT_ACTION_BINDINGS)
        if bindings:
            for action, raw_keys in bindings.items():
                source[action] = tuple(raw_keys)
        self._bindings: ActionBindings = {
            action: _normalize_keys(raw_keys) for action, raw_keys in source.items()
        }

    @property
    def bindings(self) -> ActionBindings:
        return dict(self._bindings)

    def keys_for_action(self, action: str) -> Tuple[int, ...]:
        return self._bindings.get(action, ())

    def actions_for_key(self, key_code: int) -> Set[str]:
        matches: Set[str] = set()
        for action, keys in self._bindings.items():
            if key_code in keys:
                matches.add(action)
        return matches

    def actions_for_event(self, event: pygame.event.Event) -> Set[str]:
        if event.type != pygame.KEYDOWN:
            return set()
        return self.actions_for_key(event.key)

    def matches(self, event: pygame.event.Event, action: str) -> bool:
        return action in self.actions_for_event(event)

    def bind(self, action: str, keys: Sequence[object]) -> None:
        self._bindings[action] = _normalize_keys(keys)

    def detect_conflicts(
        self, exclusive_groups: Sequence[Sequence[str]] = EXCLUSIVE_ACTION_GROUPS
    ) -> List[Tuple[int, Tuple[str, ...]]]:
        key_to_actions: Dict[int, Set[str]] = {}
        for action, keys in self._bindings.items():
            for key in keys:
                key_to_actions.setdefault(key, set()).add(action)

        conflicts: List[Tuple[int, Tuple[str, ...]]] = []
        for key_code, actions in key_to_actions.items():
            for group in exclusive_groups:
                overlap = sorted(actions.intersection(group))
                if len(overlap) > 1:
                    conflicts.append((key_code, tuple(overlap)))
                    break
        return conflicts


def _load_binding_overrides(path: str) -> Dict[str, Tuple[int, ...]]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}

    overrides: Dict[str, Tuple[int, ...]] = {}
    for action, raw_keys in data.items():
        if not isinstance(action, str):
            continue
        if not isinstance(raw_keys, list):
            continue
        overrides[action] = _normalize_keys(raw_keys)
    return overrides


def load_action_map(path: Optional[str] = None) -> InputActionMap:
    binding_path = path or os.path.join(config.DATA_DIR, "input_bindings.json")
    overrides = _load_binding_overrides(binding_path)
    return InputActionMap(overrides)
