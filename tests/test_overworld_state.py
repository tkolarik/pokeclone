import os
import sys
import unittest
from unittest.mock import patch


from src.core.tileset import TileDefinition, TileSet
from src.overworld.state import (
    CellOverride,
    Connection,
    EntityDef,
    MapData,
    MapLayer,
    OverworldSession,
    TriggerDef,
)


class FakeAudio:
    def __init__(self):
        self.played = []
        self.stopped = False

    def play_music(self, music_id):
        self.played.append(music_id)

    def stop_music(self):
        self.stopped = True

    def play_sound(self, sound_id):
        self.played.append(f"sound:{sound_id}")


def build_tileset():
    tileset = TileSet("test", "Test", tile_size=32)
    tileset.tiles = [
        TileDefinition(id="floor", name="floor", filename="floor.png", properties={"walkable": True}),
        TileDefinition(id="wall", name="wall", filename="wall.png", properties={"walkable": False}),
    ]
    return tileset


def build_basic_map(map_id="map1", music_id=None):
    return MapData(
        map_id=map_id,
        name=map_id,
        version="1.0.0",
        tile_size=32,
        dimensions=(3, 3),
        tileset_id="test",
        layers=[
            MapLayer(
                name="ground",
                tiles=[
                    ["floor", "floor", "floor"],
                    ["floor", "floor", "floor"],
                    ["floor", "floor", "floor"],
                ],
            ),
            MapLayer(
                name="overlay",
                tiles=[
                    [None, None, None],
                    [None, None, None],
                    [None, None, None],
                ],
            ),
        ],
        connections=[],
        entities=[],
        triggers=[],
        overrides={},
        music_id=music_id,
        spawn={"x": 1, "y": 1},
    )


class TestOverworldSession(unittest.TestCase):
    def test_random_music_fallback_on_map_load(self):
        world = build_basic_map(music_id=None)
        audio = FakeAudio()
        with patch("src.overworld.state.config.OVERWORLD_MUSIC_TRACKS", ["track_a.ogg", "track_b.ogg"]), \
             patch("src.overworld.state.random.choice", return_value="track_b.ogg") as mock_choice:
            session = OverworldSession(world, tileset=build_tileset(), audio_controller=audio)

        mock_choice.assert_called_once()
        self.assertEqual(session.current_music_id, "track_b.ogg")
        self.assertEqual(audio.played[-1], "track_b.ogg")

    def test_music_id_overrides_random_fallback(self):
        world = build_basic_map(music_id="explicit_song.ogg")
        audio = FakeAudio()
        with patch("src.overworld.state.config.OVERWORLD_MUSIC_TRACKS", ["track_a.ogg"]), \
             patch("src.overworld.state.random.choice") as mock_choice:
            session = OverworldSession(world, tileset=build_tileset(), audio_controller=audio)

        mock_choice.assert_not_called()
        self.assertEqual(session.current_music_id, "explicit_song.ogg")
        self.assertEqual(audio.played[-1], "explicit_song.ogg")

    def test_random_music_refreshes_on_set_map(self):
        audio = FakeAudio()
        map_one = build_basic_map("map_one", music_id=None)
        map_two = build_basic_map("map_two", music_id=None)
        with patch("src.overworld.state.config.OVERWORLD_MUSIC_TRACKS", ["track_a.ogg", "track_b.ogg"]), \
             patch("src.overworld.state.random.choice", side_effect=["track_a.ogg", "track_b.ogg"]) as mock_choice:
            session = OverworldSession(map_one, tileset=build_tileset(), audio_controller=audio)
            session.set_map(map_two, tileset=build_tileset())

        self.assertEqual(mock_choice.call_count, 2)
        self.assertEqual(audio.played[0], "track_a.ogg")
        self.assertEqual(audio.played[-1], "track_b.ogg")

    def test_collision_and_override(self):
        tileset = build_tileset()
        world = build_basic_map()
        world.layers[0].tiles[0][1] = "wall"
        session = OverworldSession(world, tileset=tileset, audio_controller=FakeAudio())

        moved = session.move("up")  # into wall at (1,0)
        self.assertFalse(moved, "Movement should block on non-walkable tile.")
        # Make wall walkable via override
        world.set_override(1, 0, CellOverride(walkable=True))
        moved = session.move("up")
        self.assertTrue(moved, "Override should allow movement.")
        self.assertEqual((session.player.x, session.player.y), (1, 0))

    def test_entity_then_trigger_order(self):
        tileset = build_tileset()
        world = build_basic_map()
        world.entities.append(
            EntityDef(
                id="npc1",
                type="npc",
                name="NPC",
                sprite_id="npc_sprite",
                position={"x": 1, "y": 0},
                actions=[{"kind": "showText", "text": "Entity first"}],
            )
        )
        world.triggers.append(
            TriggerDef(
                id="t1",
                type="onInteract",
                position={"x": 1, "y": 0},
                actions=[{"kind": "showText", "text": "Trigger second"}],
                repeatable=True,
            )
        )
        session = OverworldSession(world, tileset=tileset, audio_controller=FakeAudio())
        session.player.x, session.player.y, session.player.facing = 1, 1, "up"

        session.interact()
        self.assertEqual(session.active_message, "Entity first")
        session.acknowledge_message()
        self.assertEqual(session.active_message, "Trigger second")

    def test_on_enter_trigger_consumes_repeatable(self):
        tileset = build_tileset()
        world = build_basic_map()
        world.triggers.append(
            TriggerDef(
                id="enter_once",
                type="onEnter",
                position={"x": 1, "y": 0},
                actions=[{"kind": "showText", "text": "Hello"}],
                repeatable=False,
            )
        )
        session = OverworldSession(world, tileset=tileset, audio_controller=FakeAudio())
        session.player.x, session.player.y = 1, 1
        session.move("up")
        self.assertEqual(session.active_message, "Hello")
        session.acknowledge_message()
        session.move("down")
        session.move("up")
        self.assertIsNone(session.active_message, "Non-repeatable trigger should not fire twice.")

    def test_edge_connection_switches_map_and_music(self):
        tileset = build_tileset()
        map_one = build_basic_map("map_one", music_id="song1")
        map_two = build_basic_map("map_two", music_id="song2")
        map_one.connections.append(
            Connection(
                id="north_exit",
                type="edge",
                from_ref="up",
                to={"mapId": "map_two", "spawn": {"x": 1, "y": 2}, "facing": "south"},
                condition=None,
                extra={},
            )
        )

        # Persist maps to disk so the loader path in session works
        map_one.save()
        map_two.save()

        audio = FakeAudio()
        session = OverworldSession(map_one, tileset=tileset, audio_controller=audio)
        session.player.x, session.player.y = 1, 0  # Move off north edge
        moved = session.move("up")

        self.assertTrue(moved, "Edge connection should allow movement to target map.")
        self.assertEqual(session.map.id, "map_two")
        self.assertEqual((session.player.x, session.player.y), (1, 2))
        self.assertEqual(audio.played[0], "song1")
        self.assertEqual(audio.played[-1], "song2")

    def test_edge_connection_routes_by_source_edge_coordinate(self):
        tileset = build_tileset()
        source = build_basic_map("source", music_id="song_source")
        target_left = build_basic_map("target_left", music_id="song_left")
        target_right = build_basic_map("target_right", music_id="song_right")

        source.connections.extend(
            [
                Connection(
                    id="auto_up_target_left_0",
                    type="edge",
                    from_ref="up",
                    to={"mapId": "target_left", "spawn": {"x": 0, "y": 2}, "facing": "south"},
                    condition=None,
                    extra={"auto": "world", "sourceEdgeCoord": 0},
                ),
                Connection(
                    id="auto_up_target_right_2",
                    type="edge",
                    from_ref="up",
                    to={"mapId": "target_right", "spawn": {"x": 2, "y": 2}, "facing": "south"},
                    condition=None,
                    extra={"auto": "world", "sourceEdgeCoord": 2},
                ),
            ]
        )

        loaded_maps = {
            "target_left": target_left,
            "target_right": target_right,
        }

        with patch("src.overworld.state.MapData.load", side_effect=lambda map_id: loaded_maps[map_id].clone()), \
             patch("src.overworld.state.os.path.exists", return_value=False):
            left_session = OverworldSession(source.clone(), tileset=tileset, audio_controller=FakeAudio())
            left_session.player.x, left_session.player.y = 0, 0
            self.assertTrue(left_session.move("up"))
            self.assertEqual(left_session.map.id, "target_left")
            self.assertEqual((left_session.player.x, left_session.player.y), (0, 2))

            right_session = OverworldSession(source.clone(), tileset=tileset, audio_controller=FakeAudio())
            right_session.player.x, right_session.player.y = 2, 0
            self.assertTrue(right_session.move("up"))
            self.assertEqual(right_session.map.id, "target_right")
            self.assertEqual((right_session.player.x, right_session.player.y), (2, 2))

    def test_edge_connection_with_scoped_routes_blocks_unmapped_coordinate(self):
        tileset = build_tileset()
        source = build_basic_map("source")
        source.connections.extend(
            [
                Connection(
                    id="auto_up_target_left_0",
                    type="edge",
                    from_ref="up",
                    to={"mapId": "target_left", "spawn": {"x": 0, "y": 2}, "facing": "south"},
                    condition=None,
                    extra={"auto": "world", "sourceEdgeCoord": 0},
                ),
                Connection(
                    id="auto_up_target_right_2",
                    type="edge",
                    from_ref="up",
                    to={"mapId": "target_right", "spawn": {"x": 2, "y": 2}, "facing": "south"},
                    condition=None,
                    extra={"auto": "world", "sourceEdgeCoord": 2},
                ),
            ]
        )

        with patch("src.overworld.state.MapData.load") as mock_load:
            session = OverworldSession(source, tileset=tileset, audio_controller=FakeAudio())
            session.player.x, session.player.y = 1, 0
            moved = session.move("up")

        self.assertFalse(moved)
        self.assertEqual(session.map.id, "source")
        self.assertEqual((session.player.x, session.player.y), (1, 0))
        mock_load.assert_not_called()

    def test_edge_connection_auto_id_suffix_fallback_routes_correctly(self):
        tileset = build_tileset()
        source = build_basic_map("source")
        target_a = build_basic_map("target_a")
        target_b = build_basic_map("target_b")
        source.connections.extend(
            [
                Connection(
                    id="auto_up_target_a_0",
                    type="edge",
                    from_ref="up",
                    to={"mapId": "target_a", "spawn": {"x": 0, "y": 2}, "facing": "south"},
                    condition=None,
                    extra={"auto": "world"},
                ),
                Connection(
                    id="auto_up_target_b_2",
                    type="edge",
                    from_ref="up",
                    to={"mapId": "target_b", "spawn": {"x": 2, "y": 2}, "facing": "south"},
                    condition=None,
                    extra={"auto": "world"},
                ),
            ]
        )

        loaded_maps = {"target_a": target_a, "target_b": target_b}
        with patch("src.overworld.state.MapData.load", side_effect=lambda map_id: loaded_maps[map_id].clone()), \
             patch("src.overworld.state.os.path.exists", return_value=False):
            session = OverworldSession(source, tileset=tileset, audio_controller=FakeAudio())
            session.player.x, session.player.y = 2, 0
            moved = session.move("up")

        self.assertTrue(moved)
        self.assertEqual(session.map.id, "target_b")
        self.assertEqual((session.player.x, session.player.y), (2, 2))


if __name__ == "__main__":
    unittest.main()
