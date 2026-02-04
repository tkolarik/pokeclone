import importlib
import os
import sys
import unittest
from unittest.mock import patch

import pygame

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.tileset import TileDefinition, TileSet, NPCSprite


class TestEditorTilePanelScroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()
        pygame.font.init()
        with patch("pygame.display.set_mode", return_value=pygame.Surface((10, 10))):
            cls.editor_module = importlib.import_module("src.editor.pixle_art_editor")
        cls.Editor = cls.editor_module.Editor

    @classmethod
    def tearDownClass(cls):
        pygame.font.quit()
        pygame.display.quit()

    def _build_editor(self, asset_target):
        editor = self.Editor.__new__(self.Editor)
        editor.edit_mode = "tile"
        editor.asset_edit_target = asset_target
        editor.tile_panel_rect = pygame.Rect(0, 0, 200, 300)
        editor.tile_frame_tray_rect = None
        editor.tile_frame_visible = 0
        editor.tile_list_scroll = 0
        editor.npc_list_scroll = 0
        editor.npc_state_tray_rect = None
        editor.npc_angle_tray_rect = None
        editor.npc_state_visible = 0
        editor.npc_angle_visible = 0
        editor.current_tile_index = 0
        editor.selected_npc_id = None
        editor.current_npc_state = "standing"
        editor.current_npc_angle = "south"
        return editor

    def test_tile_list_scroll_wheel(self):
        editor = self._build_editor("tile")
        tileset = TileSet("test", "Test", tile_size=32)
        for i in range(8):
            tileset.tiles.append(TileDefinition(id=f"tile_{i}", name=f"Tile {i}", filename=f"tile_{i}.png"))
        editor.tile_set = tileset

        scrolled = editor.scroll_tile_panel(-1, (10, 10))
        self.assertTrue(scrolled)
        self.assertEqual(editor.tile_list_scroll, 1)

    def test_npc_list_scroll_wheel(self):
        editor = self._build_editor("npc")
        tileset = TileSet("test", "Test", tile_size=32)
        for i in range(8):
            npc = NPCSprite(id=f"npc_{i}", name=f"NPC {i}", states={"standing": {"south": ["frame.png"]}})
            tileset.npcs.append(npc)
        editor.tile_set = tileset
        editor.selected_npc_id = tileset.npcs[0].id

        scrolled = editor.scroll_tile_panel(-1, (10, 10))
        self.assertTrue(scrolled)
        self.assertEqual(editor.npc_list_scroll, 1)


if __name__ == "__main__":
    unittest.main()
