import os
import sys
import unittest

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.overworld.state import OverworldMap, OverworldState, Player, TileBehavior


class TestOverworldState(unittest.TestCase):
    def setUp(self):
        self.behaviors = {
            "#": TileBehavior(walkable=False),
            ".": TileBehavior(walkable=True),
            "S": TileBehavior(walkable=True, interaction="Hello there."),
        }
        self.rows = [
            "#####",
            "#...#",
            "#.S.#",
            "#...#",
            "#####",
        ]
        self.map = OverworldMap(self.rows, self.behaviors)

    def test_map_walkability_and_bounds(self):
        self.assertTrue(self.map.is_walkable(1, 1))
        self.assertFalse(self.map.is_walkable(0, 0))
        self.assertFalse(self.map.is_walkable(-1, 0))
        self.assertFalse(self.map.is_walkable(5, 5))

    def test_move_updates_position_and_facing(self):
        state = OverworldState(self.map, Player(x=1, y=1))
        moved = state.move("right")
        self.assertTrue(moved)
        self.assertEqual((state.player.x, state.player.y), (2, 1))
        self.assertEqual(state.player.facing, "right")

    def test_move_blocks_walls_but_updates_facing(self):
        state = OverworldState(self.map, Player(x=1, y=1))
        moved = state.move("left")
        self.assertFalse(moved)
        self.assertEqual((state.player.x, state.player.y), (1, 1))
        self.assertEqual(state.player.facing, "left")

    def test_interaction_reads_sign(self):
        state = OverworldState(self.map, Player(x=2, y=3, facing="up"))
        message = state.interact()
        self.assertEqual(message, "Hello there.")
        self.assertEqual(state.message, "Hello there.")

    def test_interaction_clears_message_on_empty_tile(self):
        state = OverworldState(self.map, Player(x=1, y=1, facing="right"))
        state.message = "Old message"
        message = state.interact()
        self.assertIsNone(message)
        self.assertIsNone(state.message)

    def test_move_clears_message_on_successful_move(self):
        state = OverworldState(self.map, Player(x=1, y=1))
        state.message = "Old message"
        moved = state.move("right")
        self.assertTrue(moved)
        self.assertIsNone(state.message)

