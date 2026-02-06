from __future__ import annotations

import os
from typing import Callable, Dict, Optional, Tuple

import pygame

from src.core import config


class SilentSound:
    """No-op sound fallback used when audio files/devices are unavailable."""

    def play(self, *args, **kwargs):  # pragma: no cover - trivial no-op
        return None

    def stop(self):  # pragma: no cover - trivial no-op
        return None


class ResourceManager:
    def __init__(
        self,
        *,
        image_loader: Callable[[str], pygame.Surface] = pygame.image.load,
        sound_loader: Callable[[str], pygame.mixer.Sound] = pygame.mixer.Sound,
        font_loader: Callable[[Optional[str], int], pygame.font.Font] = pygame.font.Font,
        path_exists: Callable[[str], bool] = os.path.exists,
    ) -> None:
        self._image_loader = image_loader
        self._sound_loader = sound_loader
        self._font_loader = font_loader
        self._path_exists = path_exists

        self._image_cache: Dict[Tuple[str, Tuple[int, int] | None], pygame.Surface] = {}
        self._sound_cache: Dict[str, object] = {}
        self._font_cache: Dict[Tuple[Optional[str], int], pygame.font.Font] = {}
        self.silent_sound = SilentSound()

    def clear(self) -> None:
        self._image_cache.clear()
        self._sound_cache.clear()
        self._font_cache.clear()

    def get_image(
        self,
        path: str,
        *,
        size: Tuple[int, int] | None = None,
        fallback_size: Tuple[int, int] | None = None,
        fallback_color: Tuple[int, int, int, int] = (255, 0, 255, 255),
    ) -> pygame.Surface:
        cache_key = (os.path.abspath(path), size)
        if cache_key in self._image_cache:
            return self._image_cache[cache_key]

        image: Optional[pygame.Surface] = None
        if self._path_exists(path):
            try:
                image = self._image_loader(path)
                if hasattr(image, "convert_alpha"):
                    try:
                        image = image.convert_alpha()
                    except pygame.error:
                        pass
            except (pygame.error, OSError):
                image = None

        if image is None:
            resolved_size = size or fallback_size or config.NATIVE_SPRITE_RESOLUTION
            image = pygame.Surface(resolved_size, pygame.SRCALPHA)
            image.fill(fallback_color)
            pygame.draw.rect(image, config.BLACK, image.get_rect(), 1)

        if size and image.get_size() != size:
            image = pygame.transform.scale(image, size)

        self._image_cache[cache_key] = image
        return image

    def get_sound(self, path: str) -> object:
        cache_key = os.path.abspath(path)
        if cache_key in self._sound_cache:
            return self._sound_cache[cache_key]

        sound: object = self.silent_sound
        if self._path_exists(path) and pygame.mixer.get_init() is not None:
            try:
                sound = self._sound_loader(path)
            except (pygame.error, OSError):
                sound = self.silent_sound

        self._sound_cache[cache_key] = sound
        return sound

    def get_font(self, path: Optional[str], size: int) -> pygame.font.Font:
        cache_key = (path, int(size))
        if cache_key in self._font_cache:
            return self._font_cache[cache_key]

        if not pygame.font.get_init():
            pygame.font.init()

        try:
            font = self._font_loader(path, int(size))
        except (pygame.error, OSError, TypeError):
            font = self._font_loader(None, int(size))

        self._font_cache[cache_key] = font
        return font


_RESOURCE_MANAGER: Optional[ResourceManager] = None


def get_resource_manager() -> ResourceManager:
    global _RESOURCE_MANAGER
    if _RESOURCE_MANAGER is None:
        _RESOURCE_MANAGER = ResourceManager()
    return _RESOURCE_MANAGER
