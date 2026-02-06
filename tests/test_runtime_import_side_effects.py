import importlib
import sys
from unittest.mock import patch


def _fresh_import(module_name: str):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_battle_simulator_import_has_no_runtime_side_effects():
    with patch("pygame.init") as mock_pygame_init, patch(
        "pygame.display.set_mode"
    ) as mock_set_mode, patch("pygame.mixer.init") as mock_mixer_init, patch(
        "pygame.display.set_caption"
    ) as mock_set_caption:
        module = _fresh_import("src.battle.battle_simulator")

    mock_pygame_init.assert_not_called()
    mock_set_mode.assert_not_called()
    mock_mixer_init.assert_not_called()
    mock_set_caption.assert_not_called()
    assert module.SCREEN is None
    assert module.FONT is None
    assert module.AUDIO_ENABLED is False


def test_pixel_editor_import_has_no_runtime_side_effects():
    with patch("pygame.init") as mock_pygame_init, patch(
        "pygame.display.set_mode"
    ) as mock_set_mode, patch("tkinter.Tk") as mock_tk:
        module = _fresh_import("src.editor.pixle_art_editor")

    mock_pygame_init.assert_not_called()
    mock_set_mode.assert_not_called()
    mock_tk.assert_not_called()
    assert module.screen is None
    assert module.clock is None
    assert module.monsters is None
