from unittest.mock import patch

import pygame

from src.core.resource_manager import ResourceManager, SilentSound


def test_image_requests_are_cached_and_loaded_once():
    calls = {"count": 0}

    def fake_image_loader(_path):
        calls["count"] += 1
        return pygame.Surface((8, 8), pygame.SRCALPHA)

    manager = ResourceManager(image_loader=fake_image_loader, path_exists=lambda _path: True)
    first = manager.get_image("/tmp/test.png", size=(16, 16))
    second = manager.get_image("/tmp/test.png", size=(16, 16))

    assert calls["count"] == 1
    assert first is second
    assert first.get_size() == (16, 16)


def test_missing_image_returns_placeholder_instead_of_raising():
    manager = ResourceManager(path_exists=lambda _path: False)
    surface = manager.get_image(
        "/tmp/missing.png",
        size=(12, 10),
        fallback_color=(5, 10, 15, 255),
    )
    assert surface.get_size() == (12, 10)
    assert surface.get_at((1, 1))[:3] == (5, 10, 15)


def test_sound_requests_are_cached_and_load_once_when_audio_available():
    calls = {"count": 0}
    fake_sound = object()

    def fake_sound_loader(_path):
        calls["count"] += 1
        return fake_sound

    manager = ResourceManager(sound_loader=fake_sound_loader, path_exists=lambda _path: True)
    with patch("pygame.mixer.get_init", return_value=(44100, -16, 2)):
        first = manager.get_sound("/tmp/effect.wav")
        second = manager.get_sound("/tmp/effect.wav")

    assert calls["count"] == 1
    assert first is second
    assert first is fake_sound


def test_missing_sound_uses_silent_fallback():
    manager = ResourceManager(path_exists=lambda _path: False)
    sound = manager.get_sound("/tmp/missing.wav")
    assert isinstance(sound, SilentSound)
    assert sound.play() is None


def test_font_requests_are_cached():
    calls = {"count": 0}

    class DummyFont:
        pass

    def fake_font_loader(_path, _size):
        calls["count"] += 1
        return DummyFont()

    manager = ResourceManager(font_loader=fake_font_loader)
    first = manager.get_font(None, 18)
    second = manager.get_font(None, 18)

    assert calls["count"] == 1
    assert first is second
