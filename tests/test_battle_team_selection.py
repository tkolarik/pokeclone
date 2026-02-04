import os
import sys
import unittest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Ensure pygame uses dummy drivers for headless test runs
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from src.battle import battle_simulator


class DummyCreature:
    def __init__(self, name):
        self.name = name


class TestBattleTeamSelection(unittest.TestCase):
    def setUp(self):
        self.creatures = [DummyCreature(name) for name in ["A", "B", "C", "D", "E", "F", "G"]]

    def test_parse_team_env_list(self):
        os.environ["POKECLONE_PLAYER_TEAM"] = '[{"name": "A"}, {"name": "B"}]'
        parsed = battle_simulator.parse_team_env("POKECLONE_PLAYER_TEAM")
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["name"], "A")

    def test_parse_team_env_dict(self):
        os.environ["POKECLONE_PLAYER_TEAM"] = '{"name": "A"}'
        parsed = battle_simulator.parse_team_env("POKECLONE_PLAYER_TEAM")
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["name"], "A")

    def test_parse_team_env_invalid(self):
        os.environ["POKECLONE_PLAYER_TEAM"] = 'not-json'
        parsed = battle_simulator.parse_team_env("POKECLONE_PLAYER_TEAM")
        self.assertIsNone(parsed)

    def test_build_team_entries_truncates(self):
        entries = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        team = battle_simulator.build_team_entries(self.creatures, entries, size=2, default_level=50, fill_random=False)
        self.assertEqual(len(team), 2)
        self.assertEqual([c.name for c, _ in team], ["A", "B"])

    def test_build_team_entries_fills(self):
        entries = [{"name": "A"}]
        team = battle_simulator.build_team_entries(self.creatures, entries, size=3, default_level=50, fill_random=True)
        self.assertEqual(len(team), 3)
        self.assertEqual(team[0][0].name, "A")

    def test_build_team_entries_ignores_unknown(self):
        entries = [{"name": "Z"}]
        team = battle_simulator.build_team_entries(self.creatures, entries, size=2, default_level=50, fill_random=True)
        self.assertEqual(len(team), 2)
        self.assertNotIn("Z", [c.name for c, _ in team])

    def test_build_random_team_size(self):
        team = battle_simulator.build_random_team(self.creatures, size=4, level=50)
        self.assertEqual(len(team), 4)
        self.assertTrue(all(level == 50 for _, level in team))


if __name__ == "__main__":
    unittest.main()
