import unittest
from unittest.mock import patch

from src.battle.battle_simulator import Creature, Move, opponent_choose_move


class TestBattleAI(unittest.TestCase):
    def _make_creature(self, name, type_, attack=50, defense=50, hp=100, moves=None, base_stats=None):
        if base_stats is None:
            base_stats = {"attack": attack, "defense": defense, "max_hp": hp}
        if moves is None:
            moves = []
        # sprite can be None for these tests
        creature = Creature(name, type_, hp, attack, defense, moves, sprite=None, base_stats=base_stats)
        creature.current_hp = hp
        return creature

    @patch("src.battle.battle_simulator.random.choice", side_effect=lambda moves: moves[0])
    def test_prefers_super_effective_move(self, _mock_choice):
        attacker = self._make_creature("Attacker", "Fire")
        defender = self._make_creature("Defender", "Nature")
        move_super = Move("FireBlast", "Fire", 90)
        move_weak = Move("WaterSplash", "Water", 90)
        attacker.moves = [move_super, move_weak]

        chosen = opponent_choose_move(attacker, defender)
        self.assertIs(chosen, move_super)

    @patch("src.battle.battle_simulator.random.choice", side_effect=lambda moves: moves[0])
    def test_prefers_stat_move_when_beneficial(self, _mock_choice):
        base_stats = {"attack": 50, "defense": 50, "max_hp": 100}
        attacker = self._make_creature("Attacker", "Normal", attack=30, base_stats=base_stats)
        defender = self._make_creature("Defender", "Normal")
        stat_move = Move("Focus", "Normal", 0, effect={"target": "self", "stat": "attack", "change": 1})
        damage_move = Move("Tackle", "Normal", 20)
        attacker.moves = [stat_move, damage_move]

        chosen = opponent_choose_move(attacker, defender)
        self.assertIs(chosen, stat_move)

    @patch("src.battle.battle_simulator.random.choice", side_effect=lambda moves: moves[0])
    def test_avoids_stat_move_when_low_hp(self, _mock_choice):
        base_stats = {"attack": 50, "defense": 50, "max_hp": 100}
        attacker = self._make_creature("Attacker", "Normal", attack=30, base_stats=base_stats)
        attacker.current_hp = 30  # Low HP triggers stat move penalty
        defender = self._make_creature("Defender", "Normal")
        stat_move = Move("Focus", "Normal", 0, effect={"target": "self", "stat": "attack", "change": 1})
        damage_move = Move("Tackle", "Normal", 20)
        attacker.moves = [stat_move, damage_move]

        chosen = opponent_choose_move(attacker, defender)
        self.assertIs(chosen, damage_move)


if __name__ == "__main__":
    unittest.main()
