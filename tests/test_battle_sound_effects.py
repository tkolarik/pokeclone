import unittest
from unittest.mock import MagicMock, patch

from src.battle.battle_simulator import Move, _resolve_sfx_path, play_battle_sfx


class TestBattleSoundEffects(unittest.TestCase):
    def test_resolve_prefers_move_specific_sound(self):
        move = Move("Flame Burst", "Fire", 90)

        def exists_side_effect(path):
            return path.endswith("sounds/moves/Flame Burst.mp3")

        with patch("src.battle.battle_simulator.os.path.exists", side_effect=exists_side_effect):
            path = _resolve_sfx_path("attack", move=move)

        self.assertTrue(path.endswith("sounds/moves/Flame Burst.mp3"))

    def test_resolve_uses_event_sound_fallback(self):
        move = Move("Unknown Move", "Fire", 90)

        def exists_side_effect(path):
            return path.endswith("sounds/events/attack.mp3")

        with patch("src.battle.battle_simulator.os.path.exists", side_effect=exists_side_effect):
            path = _resolve_sfx_path("attack", move=move)

        self.assertTrue(path.endswith("sounds/events/attack.mp3"))

    @patch("src.battle.battle_simulator._is_audio_ready", return_value=False)
    @patch("src.battle.battle_simulator._load_sfx")
    def test_play_sfx_noop_when_audio_unavailable(self, mock_load, _mock_ready):
        play_battle_sfx("attack")
        mock_load.assert_not_called()

    @patch("src.battle.battle_simulator._is_audio_ready", return_value=True)
    @patch("src.battle.battle_simulator._resolve_sfx_path", return_value="/tmp/test.wav")
    @patch("src.battle.battle_simulator._load_sfx")
    def test_play_sfx_plays_loaded_sound(self, mock_load, _mock_resolve, _mock_ready):
        sound = MagicMock()
        mock_load.return_value = sound

        play_battle_sfx("attack")

        sound.play.assert_called_once()


if __name__ == "__main__":
    unittest.main()
