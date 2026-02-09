from __future__ import annotations

import json
import os
from typing import Iterable

import pygame

from src.core import config
from src.editor.move_animation_state import (
    DEFAULT_CANVAS_SIZE,
    MoveAnimationState,
    default_frame_image_path,
)

SurfaceMap = dict[tuple[str, int], pygame.Surface]


def move_animation_data_dir(data_dir: str = config.DATA_DIR) -> str:
    if data_dir == config.DATA_DIR:
        return config.MOVE_ANIMATION_DATA_DIR
    return os.path.join(data_dir, "move_animations")


def move_animation_sprite_dir(sprite_dir: str = config.SPRITE_DIR) -> str:
    if sprite_dir == config.SPRITE_DIR:
        return config.MOVE_ANIMATION_SPRITE_DIR
    return os.path.join(sprite_dir, "move_animations")


def animation_json_path(animation_id: str, *, data_dir: str = config.DATA_DIR) -> str:
    return os.path.join(move_animation_data_dir(data_dir), f"{animation_id}.json")


def animation_sprite_root(animation_id: str, *, sprite_dir: str = config.SPRITE_DIR) -> str:
    return os.path.join(move_animation_sprite_dir(sprite_dir), animation_id)


def list_move_animation_files(*, data_dir: str = config.DATA_DIR) -> list[str]:
    root = move_animation_data_dir(data_dir)
    if not os.path.exists(root):
        return []
    return sorted(
        os.path.join(root, name)
        for name in os.listdir(root)
        if name.endswith(".json") and os.path.isfile(os.path.join(root, name))
    )


def list_move_animation_ids(*, data_dir: str = config.DATA_DIR) -> list[str]:
    ids: list[str] = []
    for path in list_move_animation_files(data_dir=data_dir):
        stem = os.path.splitext(os.path.basename(path))[0]
        ids.append(stem)
    return ids


def _resolve_json_path(animation_ref: str, *, data_dir: str) -> str:
    if animation_ref.endswith(".json") or os.path.sep in animation_ref or os.path.isabs(animation_ref):
        return animation_ref
    return animation_json_path(animation_ref, data_dir=data_dir)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _normalize_image_path(path: str) -> str:
    return str(path or "").replace("\\", "/").lstrip("/")


def _blank_surface(size: tuple[int, int]) -> pygame.Surface:
    w = max(1, int(size[0]))
    h = max(1, int(size[1]))
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    return surface


def _convert_alpha_safe(surface: pygame.Surface) -> pygame.Surface:
    try:
        if pygame.display.get_surface() is not None:
            return surface.convert_alpha()
    except pygame.error:
        pass
    return surface


def _load_surface(path: str, *, expected_size: tuple[int, int]) -> pygame.Surface:
    loaded = pygame.image.load(path)
    loaded = _convert_alpha_safe(loaded)
    expected_w = max(1, int(expected_size[0]))
    expected_h = max(1, int(expected_size[1]))
    if loaded.get_size() != (expected_w, expected_h):
        loaded = pygame.transform.scale(loaded, (expected_w, expected_h))
    return loaded


def _ensure_object_frame_surfaces(
    state: MoveAnimationState,
    *,
    sprite_root: str,
    surfaces: SurfaceMap,
    generate_placeholders: bool,
) -> None:
    for obj in state.objects:
        object_size = (obj.size_w or DEFAULT_CANVAS_SIZE[0], obj.size_h or DEFAULT_CANVAS_SIZE[1])
        for frame_index, frame in enumerate(obj.frames):
            image_rel = _normalize_image_path(frame.image) or default_frame_image_path(obj.object_id, frame_index)
            frame.image = image_rel
            image_abs = os.path.join(sprite_root, image_rel)
            key = (obj.object_id, frame_index)

            if os.path.exists(image_abs):
                try:
                    surfaces[key] = _load_surface(image_abs, expected_size=object_size)
                    continue
                except pygame.error:
                    pass

            surfaces[key] = _blank_surface(object_size)
            if generate_placeholders:
                _ensure_dir(os.path.dirname(image_abs))
                pygame.image.save(surfaces[key], image_abs)


def create_new_move_animation(
    animation_id: str,
    *,
    name: str | None = None,
    canvas_size: tuple[int, int] = DEFAULT_CANVAS_SIZE,
    object_count: int = 1,
) -> tuple[MoveAnimationState, SurfaceMap]:
    state = MoveAnimationState.new(
        animation_id=animation_id,
        name=name,
        canvas_size=canvas_size,
        object_count=object_count,
    )
    surfaces: SurfaceMap = {}
    for obj in state.objects:
        for frame_index, _ in enumerate(obj.frames):
            surfaces[(obj.object_id, frame_index)] = _blank_surface((obj.size_w, obj.size_h))
    return state, surfaces


def load_move_animation(
    animation_ref: str,
    *,
    data_dir: str = config.DATA_DIR,
    sprite_dir: str = config.SPRITE_DIR,
    generate_placeholders: bool = True,
) -> tuple[MoveAnimationState, SurfaceMap]:
    json_path = _resolve_json_path(animation_ref, data_dir=data_dir)
    with open(json_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    state = MoveAnimationState.from_dict(payload)
    sprite_root = animation_sprite_root(state.animation_id, sprite_dir=sprite_dir)
    _ensure_dir(sprite_root)

    surfaces: SurfaceMap = {}
    _ensure_object_frame_surfaces(
        state,
        sprite_root=sprite_root,
        surfaces=surfaces,
        generate_placeholders=generate_placeholders,
    )
    return state, surfaces


def _iter_surface_targets(state: MoveAnimationState) -> Iterable[tuple[str, int, str, tuple[int, int]]]:
    for obj in state.objects:
        size = (obj.size_w, obj.size_h)
        for frame_index, frame in enumerate(obj.frames):
            image_rel = _normalize_image_path(frame.image) or default_frame_image_path(obj.object_id, frame_index)
            frame.image = image_rel
            yield obj.object_id, frame_index, image_rel, size


def save_move_animation(
    state: MoveAnimationState,
    surfaces: SurfaceMap,
    *,
    data_dir: str = config.DATA_DIR,
    sprite_dir: str = config.SPRITE_DIR,
) -> str:
    state.ensure_alignment()
    data_root = move_animation_data_dir(data_dir)
    sprite_root = animation_sprite_root(state.animation_id, sprite_dir=sprite_dir)
    _ensure_dir(data_root)
    _ensure_dir(sprite_root)

    for object_id, frame_index, image_rel, size in _iter_surface_targets(state):
        key = (object_id, frame_index)
        frame_surface = surfaces.get(key)
        if frame_surface is None:
            frame_surface = _blank_surface(size)
        elif frame_surface.get_size() != size:
            frame_surface = pygame.transform.scale(frame_surface, size)
        surfaces[key] = frame_surface

        image_abs = os.path.join(sprite_root, image_rel)
        _ensure_dir(os.path.dirname(image_abs))
        pygame.image.save(frame_surface, image_abs)

    json_path = animation_json_path(state.animation_id, data_dir=data_dir)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(state.to_dict(), handle, indent=2)
    return json_path
