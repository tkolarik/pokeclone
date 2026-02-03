import json
import math
import os
import random
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

import pygame

from src.core import config
from src.core.tileset import TileDefinition, TileSet, list_tileset_files, NPCSprite
from src.overworld.overworld import load_tileset_images
from src.overworld.state import (
    CellOverride,
    Connection,
    EntityDef,
    MapData,
    MapLayer,
    TriggerDef,
)

# Basic colors for UI
PANEL_BG = (40, 40, 50)
PANEL_TEXT = (235, 235, 235)
HIGHLIGHT = (90, 160, 255)

PALETTE_WIDTH = 220
INSPECTOR_WIDTH = 280
CANVAS_MARGIN = 8
TOOLBAR_HEIGHT = 110


def prompt_text(screen: pygame.Surface, font: pygame.font.Font, message: str, default: str = "") -> Optional[str]:
    """Blocking text input prompt rendered over the editor."""
    input_text = default
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return input_text
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if event.unicode:
                        input_text += event.unicode

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        lines = [
            message,
            "> " + input_text,
            "Enter to confirm, Esc to cancel",
        ]
        for idx, line in enumerate(lines):
            surf = font.render(line, True, PANEL_TEXT)
            rect = surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + idx * 24))
            screen.blit(surf, rect)
        pygame.display.flip()
        clock.tick(30)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


class MapEditor:
    def __init__(self, map_path: Optional[str] = None) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((config.EDITOR_WIDTH, config.EDITOR_HEIGHT))
        pygame.display.set_caption("Overworld Map Editor")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(config.DEFAULT_FONT, 16)
        self.font_small = pygame.font.Font(config.DEFAULT_FONT, 13)

        self.map = self._load_initial_map(map_path)
        self.tileset = self._load_tileset(self.map.tileset_id)
        self.tile_images = load_tileset_images(self.tileset, self.map.tile_size)
        self._ensure_all_npc_frames()

        self.mode = "tiles"  # tiles, entities, triggers, connections, overrides
        self.tool = "brush"  # brush, fill, rect, line, erase, eyedropper
        self.active_layer = "ground"
        self.selected_tile = self.tileset.tiles[0].id if self.tileset and self.tileset.tiles else None
        self.selected_npc = self.tileset.npcs[0].id if self.tileset and self.tileset.npcs else None
        self.palette_mode = "tiles"
        self.status_message = "Loaded map."
        self.zoom = 1.0
        self.camera = [0.0, 0.0]
        self.dragging = False
        self.drag_start: Optional[Tuple[int, int]] = None
        self.dragging_npc_id: Optional[str] = None
        self.dragging_entity: Optional[EntityDef] = None
        self.drag_origin_cell: Optional[Tuple[int, int]] = None
        self.drag_preview_pos: Optional[Tuple[int, int]] = None
        self.line_start: Optional[Tuple[int, int]] = None
        self.hover_cell: Optional[Tuple[int, int]] = None
        self.selected_entity: Optional[EntityDef] = None
        self.selected_trigger: Optional[TriggerDef] = None
        self.selected_connection: Optional[Connection] = None
        self.help_mode = False
        self.tool_button_rects: List[Tuple[pygame.Rect, str]] = []
        self.mode_button_rects: List[Tuple[pygame.Rect, str]] = []
        self.layer_button_rects: List[Tuple[pygame.Rect, str]] = []
        self.help_button_rect: Optional[pygame.Rect] = None
        self.world_view_button_rect: Optional[pygame.Rect] = None
        self.add_button_rects: List[Tuple[pygame.Rect, str]] = []
        self.palette_tab_rects: List[Tuple[pygame.Rect, str]] = []
        self.new_map_button_rect: Optional[pygame.Rect] = None

        self.history: List[MapData] = []
        self.redo_stack: List[MapData] = []

    # Loading helpers ------------------------------------------------------
    def _load_initial_map(self, map_path: Optional[str]) -> MapData:
        if map_path and os.path.exists(map_path):
            return MapData.load(map_path)
        default_path = os.path.join(config.MAP_DIR, "demo_tiles.json")
        if os.path.exists(default_path):
            return MapData.load(default_path)
        return MapData(
            map_id="new_map",
            name="New Map",
            version="1.0.0",
            tile_size=config.OVERWORLD_TILE_SIZE,
            dimensions=(config.OVERWORLD_GRID_WIDTH, config.OVERWORLD_GRID_HEIGHT),
            tileset_id=config.DEFAULT_TILESET_ID,
            layers=[
                MapLayer(
                    name="ground",
                    tiles=[[None for _ in range(config.OVERWORLD_GRID_WIDTH)] for _ in range(config.OVERWORLD_GRID_HEIGHT)],
                ),
                MapLayer(
                    name="overlay",
                    tiles=[[None for _ in range(config.OVERWORLD_GRID_WIDTH)] for _ in range(config.OVERWORLD_GRID_HEIGHT)],
                ),
            ],
            connections=[],
            entities=[],
            triggers=[],
            overrides={},
        )

    def _load_tileset(self, tileset_id: str) -> Optional[TileSet]:
        path = os.path.join(config.TILESET_DIR, f"{tileset_id}.json")
        if os.path.exists(path):
            return TileSet.load(path)
        available = list_tileset_files()
        if available:
            return TileSet.load(available[0])
        return None

    # Undo/redo ------------------------------------------------------------
    def push_history(self):
        self.history.append(self.map.clone())
        # Limit history size to avoid large memory use
        if len(self.history) > 30:
            self.history.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.history:
            return
        previous = self.history.pop()
        self.redo_stack.append(self.map.clone())
        self.map = previous
        self.status_message = "Undo."

    def redo(self):
        if not self.redo_stack:
            return
        next_state = self.redo_stack.pop()
        self.history.append(self.map.clone())
        self.map = next_state
        self.status_message = "Redo."

    # Event handling -------------------------------------------------------
    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    self._handle_key(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_down(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self._handle_mouse_up(event)
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_mouse_motion(event)

            self._draw()
            pygame.display.flip()
            self.clock.tick(config.FPS)

        pygame.quit()

    def _handle_key(self, event: pygame.event.Event) -> None:
        mods = pygame.key.get_mods()
        ctrl = mods & pygame.KMOD_CTRL
        if ctrl and event.key == pygame.K_s:
            self._save_map()
            return
        if ctrl and event.key == pygame.K_o:
            self._load_map_prompt()
            return
        if ctrl and event.key == pygame.K_z:
            self.undo()
            return
        if ctrl and event.key == pygame.K_y:
            self.redo()
            return

        if event.key == pygame.K_1:
            self.active_layer = "ground"
        elif event.key == pygame.K_2:
            self.active_layer = "overlay"
        elif event.key == pygame.K_b:
            self.tool = "brush"
        elif event.key == pygame.K_f:
            self.tool = "fill"
        elif event.key == pygame.K_r:
            self.tool = "rect"
        elif event.key == pygame.K_l:
            self.tool = "line"
        elif event.key == pygame.K_e:
            self.tool = "erase"
        elif event.key == pygame.K_i:
            self.tool = "eyedropper"
        elif event.key == pygame.K_t:
            self.mode = "tiles"
        elif event.key == pygame.K_n:
            self.mode = "entities"
        elif event.key == pygame.K_g:
            self.mode = "triggers"
        elif event.key == pygame.K_c:
            self.mode = "connections"
        elif event.key == pygame.K_o:
            self.mode = "overrides"
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_RIGHTBRACKET):
            self.zoom = clamp(self.zoom + 0.1, 0.5, 3.0)
        elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS, pygame.K_LEFTBRACKET):
            self.zoom = clamp(self.zoom - 0.1, 0.5, 3.0)
        elif event.key == pygame.K_a and self.mode == "entities" and self.hover_cell:
            self._add_entity(self.hover_cell)
        elif event.key == pygame.K_a and self.mode == "triggers" and self.hover_cell:
            self._add_trigger(self.hover_cell)
        elif event.key == pygame.K_a and self.mode == "connections" and self.hover_cell:
            self._add_connection(self.hover_cell)
        elif event.key == pygame.K_m:
            self._edit_metadata()

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        if event.button == 1:
            if self._handle_help_or_buttons(event.pos):
                return
            if self._palette_rect().collidepoint(event.pos):
                self._handle_palette_click(event.pos)
                return
        keys = pygame.key.get_pressed()
        if event.button == 2 or (event.button == 1 and keys[pygame.K_SPACE]):
            self.dragging = True
            self.drag_start = event.pos
            return
        if event.button == 1:
            if self.mode == "entities":
                cell = self._cell_from_mouse(event.pos)
                if cell:
                    entities = self.map.find_entities_at(cell[0], cell[1])
                    if entities:
                        self.dragging_entity = entities[0]
                        self.selected_entity = entities[0]
                        self.drag_origin_cell = cell
                        self.drag_preview_pos = event.pos
                        self.status_message = f"Selected entity {entities[0].id}"
                        return
            cell = self._cell_from_mouse(event.pos)
            if cell:
                self._apply_primary_action(cell)
        if event.button == 3:
            cell = self._cell_from_mouse(event.pos)
            if cell:
                self._apply_secondary_action(cell)

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button == 1 and (self.dragging_npc_id or self.dragging_entity):
            cell = self._cell_from_mouse(event.pos)
            if cell and self.mode == "entities":
                entities_here = self.map.find_entities_at(cell[0], cell[1])
                if self.dragging_entity:
                    if entities_here and entities_here[0] is not self.dragging_entity:
                        self.status_message = "Cell occupied. Entity not moved."
                    elif cell != (self.drag_origin_cell or cell):
                        self.push_history()
                        self.dragging_entity.position = {"x": cell[0], "y": cell[1]}
                        self.status_message = f"Moved entity {self.dragging_entity.id}"
                else:
                    if entities_here:
                        self.selected_entity = entities_here[0]
                        self.status_message = f"Selected entity {entities_here[0].id}"
                    else:
                        self._place_entity_with_npc(cell, self.dragging_npc_id)
            self.dragging_npc_id = None
            self.dragging_entity = None
            self.drag_origin_cell = None
            self.drag_preview_pos = None
            return
        if event.button == 2 or (event.button == 1 and self.dragging):
            self.dragging = False
            self.drag_start = None
        if self.tool in ("rect", "line") and self.line_start and event.button == 1:
            cell = self._cell_from_mouse(event.pos)
            if cell:
                self._apply_shape(self.line_start, cell)
            self.line_start = None

    def _handle_mouse_motion(self, event: pygame.event.Event) -> None:
        if self.dragging_npc_id or self.dragging_entity:
            self.drag_preview_pos = event.pos
            self.hover_cell = self._cell_from_mouse(event.pos)
            return
        if self.dragging and self.drag_start:
            dx = event.pos[0] - self.drag_start[0]
            dy = event.pos[1] - self.drag_start[1]
            self.camera[0] -= dx
            self.camera[1] -= dy
            self.drag_start = event.pos
        else:
            self.hover_cell = self._cell_from_mouse(event.pos)

    def _handle_help_or_buttons(self, pos: Tuple[int, int]) -> bool:
        # Help toggle
        if self.help_button_rect and self.help_button_rect.collidepoint(pos):
            self.help_mode = not self.help_mode
            self.status_message = "Help mode on: click a control to learn more." if self.help_mode else "Help mode off."
            return True
        # Tool buttons
        for rect, key in self.tool_button_rects + self.mode_button_rects + self.layer_button_rects + self.add_button_rects:
            if rect.collidepoint(pos):
                if self.help_mode:
                    self.status_message = self._tooltip_for(key)
                else:
                    if key in ("brush", "fill", "rect", "line", "erase", "eyedropper"):
                        self.tool = key
                    elif key in ("tiles", "entities", "triggers", "connections", "overrides"):
                        self.mode = key
                    elif key in ("ground", "overlay"):
                        self.active_layer = key
                    elif key == "add_tile":
                        self._add_tile()
                    elif key == "add_npc":
                        self._add_npc()
                return True
        for rect, key in self.palette_tab_rects:
            if rect.collidepoint(pos):
                self.palette_mode = key
                self.status_message = f"Palette: {key}"
                return True
        if self.new_map_button_rect and self.new_map_button_rect.collidepoint(pos):
            if self.help_mode:
                self.status_message = self._tooltip_for("new_map")
            else:
                self._new_map_dialog()
            return True
        if self.world_view_button_rect and self.world_view_button_rect.collidepoint(pos):
            if self.help_mode:
                self.status_message = self._tooltip_for("world_view")
            else:
                self._open_world_view()
            return True
        return False

    # Coordinate helpers ---------------------------------------------------
    def _canvas_rect(self) -> pygame.Rect:
        top = CANVAS_MARGIN + TOOLBAR_HEIGHT
        return pygame.Rect(
            PALETTE_WIDTH + CANVAS_MARGIN,
            top,
            self.screen.get_width() - PALETTE_WIDTH - INSPECTOR_WIDTH - CANVAS_MARGIN * 2,
            self.screen.get_height() - top - CANVAS_MARGIN,
        )

    def _palette_rect(self) -> pygame.Rect:
        return pygame.Rect(0, 0, PALETTE_WIDTH, self.screen.get_height())

    def _cell_from_mouse(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        canvas = self._canvas_rect()
        if not canvas.collidepoint(pos):
            return None
        tile_px = int(self.map.tile_size * self.zoom)
        world_x = (pos[0] - canvas.x) + self.camera[0]
        world_y = (pos[1] - canvas.y) + self.camera[1]
        x = int(world_x // tile_px)
        y = int(world_y // tile_px)
        if not self.map.in_bounds(x, y):
            return None
        return x, y

    # Actions --------------------------------------------------------------
    def _apply_primary_action(self, cell: Tuple[int, int]) -> None:
        if self.mode == "tiles":
            if self.tool in ("rect", "line"):
                self.line_start = cell
                return
            if self.tool == "fill":
                self.push_history()
                self._flood_fill(cell, self.selected_tile)
            elif self.tool == "eyedropper":
                tile = self.map.get_tile(self.active_layer, cell[0], cell[1])
                if tile:
                    self.selected_tile = tile
            else:
                self.push_history()
                self._set_tile(cell, self.selected_tile)
        elif self.mode == "entities":
            entities = self.map.find_entities_at(cell[0], cell[1])
            if entities:
                self._select_entity(cell)
            else:
                if self.selected_entity:
                    self.push_history()
                    self.selected_entity.position = {"x": cell[0], "y": cell[1]}
                    self.status_message = f"Moved entity {self.selected_entity.id}"
                else:
                    self._place_entity(cell)
        elif self.mode == "triggers":
            self._select_trigger(cell)
        elif self.mode == "connections":
            if self._select_connection(cell):
                return
            self._add_connection(cell)
        elif self.mode == "overrides":
            self.push_history()
            self._cycle_override(cell)

    def _apply_secondary_action(self, cell: Tuple[int, int]) -> None:
        mods = pygame.key.get_mods()
        if self.mode == "tiles":
            tile = self.map.get_tile(self.active_layer, cell[0], cell[1])
            if tile and not (mods & pygame.KMOD_SHIFT):
                self._open_art_editor("tile", tile)
                return
            self.push_history()
            self._set_tile(cell, None)
        elif self.mode == "entities":
            entities = self.map.find_entities_at(cell[0], cell[1])
            if entities and not (mods & pygame.KMOD_SHIFT):
                self._open_art_editor("npc", entities[0].sprite_id)
                return
            if entities:
                self.push_history()
                self.map.entities.remove(entities[0])
                self.status_message = f"Removed entity {entities[0].id}"
        elif self.mode == "overrides":
            self.push_history()
            self.map.overrides.pop(cell, None)

    def _apply_shape(self, start: Tuple[int, int], end: Tuple[int, int]) -> None:
        self.push_history()
        if self.tool == "rect":
            x1, y1 = start
            x2, y2 = end
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for x in range(min(x1, x2), max(x1, x2) + 1):
                    self._set_tile((x, y), self.selected_tile)
        elif self.tool == "line":
            for x, y in self._bresenham_line(start, end):
                self._set_tile((x, y), self.selected_tile)

    def _set_tile(self, cell: Tuple[int, int], tile_id: Optional[str]) -> None:
        x, y = cell
        self.map.set_tile(self.active_layer, x, y, tile_id)

    def _flood_fill(self, start: Tuple[int, int], new_tile: Optional[str]) -> None:
        layer = self.map.layer(self.active_layer)
        if not layer:
            return
        width, height = self.map.width, self.map.height
        target = layer.tiles[start[1]][start[0]]
        if target == new_tile:
            return
        stack = [start]
        while stack:
            x, y = stack.pop()
            if not (0 <= x < width and 0 <= y < height):
                continue
            if layer.tiles[y][x] != target:
                continue
            layer.tiles[y][x] = new_tile
            stack.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    def _cycle_override(self, cell: Tuple[int, int]) -> None:
        existing = self.map.get_override(cell[0], cell[1]) or CellOverride()
        current = existing.walkable
        if current is None:
            existing.walkable = False
        elif current is False:
            existing.walkable = True
        else:
            existing.walkable = None
        # Toggle spawn flag with Shift
        if pygame.key.get_mods() & pygame.KMOD_SHIFT:
            if "spawn" in existing.flags:
                existing.flags.remove("spawn")
            else:
                existing.flags.append("spawn")
        if existing.walkable is None and not existing.flags:
            self.map.overrides.pop(cell, None)
        else:
            self.map.set_override(cell[0], cell[1], existing)

    def _select_entity(self, cell: Tuple[int, int]) -> None:
        entities = self.map.find_entities_at(cell[0], cell[1])
        self.selected_entity = entities[0] if entities else None
        if self.selected_entity:
            self.status_message = f"Selected entity {self.selected_entity.id}"

    def _place_entity(self, cell: Tuple[int, int]) -> None:
        npc_id = self.selected_npc
        if not npc_id:
            self.status_message = "Select an NPC first."
            return
        self._place_entity_with_npc(cell, npc_id)

    def _place_entity_with_npc(self, cell: Tuple[int, int], npc_id: Optional[str]) -> None:
        if not npc_id:
            self.status_message = "Select an NPC first."
            return
        entity_id = self._unique_entity_id(npc_id)
        entity = EntityDef(
            id=entity_id,
            type="npc",
            name=entity_id,
            sprite_id=npc_id,
            position={"x": cell[0], "y": cell[1]},
            facing="down",
            collision=True,
        )
        self.push_history()
        self.map.entities.append(entity)
        self.selected_entity = entity
        self.status_message = f"Placed NPC {npc_id} at {cell[0]},{cell[1]}"

    def _unique_entity_id(self, base_id: str) -> str:
        """Generate a unique entity id based on the NPC id."""
        existing = {entity.id for entity in self.map.entities}
        if base_id not in existing:
            return base_id
        counter = 2
        while True:
            candidate = f"{base_id}_{counter}"
            if candidate not in existing:
                return candidate
            counter += 1

    def _select_trigger(self, cell: Tuple[int, int]) -> None:
        triggers = self.map.find_triggers_at(cell[0], cell[1], None)
        self.selected_trigger = triggers[0] if triggers else None
        if self.selected_trigger:
            self.status_message = f"Selected trigger {self.selected_trigger.id}"

    def _select_connection(self, cell: Tuple[int, int]) -> bool:
        connection = self.map.portal_at(cell[0], cell[1])
        if not connection:
            direction = None
            x, y = cell
            if x == 0:
                direction = "left"
            elif x == self.map.width - 1:
                direction = "right"
            elif y == 0:
                direction = "up"
            elif y == self.map.height - 1:
                direction = "down"
            if direction:
                connection = self.map.connection_for_edge(direction)
        self.selected_connection = connection
        if connection:
            self.status_message = f"Selected connection {connection.id}"
            return True
        return False

    def _add_entity(self, cell: Tuple[int, int]) -> None:
        base_id = prompt_text(self.screen, self.font, "Entity id:", "entity_1")
        if not base_id:
            return
        name = prompt_text(self.screen, self.font, "Entity name:", base_id)
        sprite_id = prompt_text(self.screen, self.font, "Sprite id:", "npc")
        dialog = prompt_text(self.screen, self.font, "Dialog (comma separated for multiple lines):", "")
        dialog_value = dialog.split(",") if dialog else []
        entity = EntityDef(
            id=base_id,
            type="npc",
            name=name or base_id,
            sprite_id=sprite_id or "",
            position={"x": cell[0], "y": cell[1]},
            facing="down",
            collision=True,
            dialog=dialog_value if dialog_value else None,
        )
        self.push_history()
        self.map.entities.append(entity)
        self.selected_entity = entity
        self.status_message = f"Added entity {entity.id}"

    def _add_trigger(self, cell: Tuple[int, int]) -> None:
        trig_id = prompt_text(self.screen, self.font, "Trigger id:", "trigger_1")
        if not trig_id:
            return
        trig_type = prompt_text(self.screen, self.font, "Type (onEnter/onInteract):", "onEnter") or "onEnter"
        action_text = prompt_text(self.screen, self.font, "Action JSON (default showText):", "")
        actions = [{"kind": "showText", "text": "Hello"}]
        if action_text:
            try:
                parsed = json.loads(action_text)
                if isinstance(parsed, list):
                    actions = parsed
                elif isinstance(parsed, dict):
                    actions = [parsed]
            except json.JSONDecodeError:
                pass
        trigger = TriggerDef(
            id=trig_id,
            type=trig_type,
            position={"x": cell[0], "y": cell[1]},
            actions=actions,
            repeatable=True,
        )
        self.push_history()
        self.map.triggers.append(trigger)
        self.selected_trigger = trigger
        self.status_message = f"Added trigger {trigger.id}"

    def _add_connection(self, cell: Tuple[int, int]) -> None:
        x, y = cell
        is_edge = x == 0 or y == 0 or x == self.map.width - 1 or y == self.map.height - 1
        conn_id = prompt_text(self.screen, self.font, "Connection id:", "conn_1")
        if not conn_id:
            return
        target_map = prompt_text(self.screen, self.font, "Target map id:", "map_id")
        if not target_map:
            return
        spawn_x = prompt_text(self.screen, self.font, "Spawn x:", "0")
        spawn_y = prompt_text(self.screen, self.font, "Spawn y:", "0")
        facing = prompt_text(self.screen, self.font, "Facing (optional):", "")
        try:
            spawn = {"x": int(spawn_x or 0), "y": int(spawn_y or 0)}
        except ValueError:
            spawn = {"x": 0, "y": 0}
        if is_edge:
            direction = "left" if x == 0 else "right" if x == self.map.width - 1 else "up" if y == 0 else "down"
            connection = Connection(
                id=conn_id,
                type="edge",
                from_ref=direction,
                to={"mapId": target_map, "spawn": spawn, "facing": facing or None},
                condition=None,
                extra={},
            )
        else:
            connection = Connection(
                id=conn_id,
                type="portal",
                from_ref={"x": x, "y": y},
                to={"mapId": target_map, "spawn": spawn, "facing": facing or None},
                condition=None,
                extra={},
            )
        self.push_history()
        self.map.connections.append(connection)
        self.selected_connection = connection
        self.status_message = f"Added connection {connection.id}"

    # Drawing --------------------------------------------------------------
    def _draw(self) -> None:
        self.screen.fill((20, 20, 25))
        self._draw_toolbar()
        self._draw_palette()
        self._draw_inspector()
        self._draw_canvas()
        self._draw_status()

    def _draw_palette(self) -> None:
        panel = pygame.Rect(0, 0, PALETTE_WIDTH, self.screen.get_height())
        pygame.draw.rect(self.screen, PANEL_BG, panel)
        # Tabs
        self.palette_tab_rects = []
        tab_y = 8
        for idx, (label, key) in enumerate([("Tiles", "tiles"), ("NPCs", "npcs")]):
            rect = pygame.Rect(10 + idx * 70, tab_y, 64, 24)
            active = self.palette_mode == key
            pygame.draw.rect(self.screen, HIGHLIGHT if active else config.GRAY_DARK, rect, 2 if active else 1)
            text = self.font_small.render(label, True, PANEL_TEXT)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)
            self.palette_tab_rects.append((rect, key))

        if not self.tileset:
            return

        if self.palette_mode == "tiles":
            self._draw_tile_palette(panel)
        else:
            self._draw_npc_palette(panel)

        # Action buttons
        self.add_button_rects = []
        btn_y = panel.height - 120
        for label, key in (("Add Tile", "add_tile"), ("Add NPC", "add_npc")):
            rect = pygame.Rect(10, btn_y, PALETTE_WIDTH - 20, 28)
            pygame.draw.rect(self.screen, HIGHLIGHT if key == "add_tile" else config.GRAY_DARK, rect, 1)
            text = self.font_small.render(label, True, PANEL_TEXT)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)
            self.add_button_rects.append((rect, key))
            btn_y += 36

    def _handle_palette_click(self, pos: Tuple[int, int]) -> None:
        if not self.tileset:
            return
        # Tab click handled elsewhere
        if self.palette_mode == "tiles":
            tile_px = 48
            padding = 8
            local_x, local_y = pos[0], pos[1]
            local_y -= 40
            if local_y >= 0:
                col = local_x // (tile_px + padding)
                row = local_y // (tile_px + padding)
                idx = int(row * 3 + col)
                if 0 <= idx < len(self.tileset.tiles):
                    self.selected_tile = self.tileset.tiles[idx].id
                    self.status_message = f"Selected tile {self.selected_tile}"
        else:
            # NPC list rows
            start_y = 40
            row_height = 36
            idx = (pos[1] - start_y) // row_height
            if 0 <= idx < len(self.tileset.npcs):
                npc = self.tileset.npcs[idx]
                self.selected_npc = npc.id
                self.status_message = f"Selected NPC {npc.id}"
                if self.mode == "entities":
                    self.dragging_npc_id = npc.id
                    self.drag_preview_pos = pos

        for rect, key in self.add_button_rects:
            if rect.collidepoint(pos):
                if self.help_mode:
                    self.status_message = self._tooltip_for(key)
                elif key == "add_tile":
                    self._add_tile()
                elif key == "add_npc":
                    self._add_npc()

    def _draw_inspector(self) -> None:
        panel = pygame.Rect(self.screen.get_width() - INSPECTOR_WIDTH, 0, INSPECTOR_WIDTH, self.screen.get_height())
        pygame.draw.rect(self.screen, PANEL_BG, panel)
        lines = [
            f"Mode: {self.mode}",
            f"Tool: {self.tool}",
            f"Layer: {self.active_layer}",
            f"Tile: {self.selected_tile or 'None'}",
            f"Map: {self.map.id} {self.map.width}x{self.map.height}",
            f"Tileset: {self.map.tileset_id}",
            f"Zoom: {self.zoom:.2f}",
        ]
        y = 10
        for line in lines:
            surf = self.font.render(line, True, PANEL_TEXT)
            self.screen.blit(surf, (panel.x + 10, y))
            y += 22

        y += 10
        if self.hover_cell:
            hx, hy = self.hover_cell
            hover_lines = [
                f"Hover: {hx},{hy}",
                f"Ground: {self.map.get_tile('ground', hx, hy)}",
                f"Overlay: {self.map.get_tile('overlay', hx, hy)}",
            ]
            ov = self.map.get_override(hx, hy)
            if ov:
                hover_lines.append(f"Override walkable={ov.walkable} flags={','.join(ov.flags)}")
            entities = self.map.find_entities_at(hx, hy)
            if entities:
                hover_lines.append(f"Entity: {entities[0].id}")
            triggers = self.map.find_triggers_at(hx, hy, None)
            if triggers:
                hover_lines.append(f"Trigger: {triggers[0].id}")
            portal = self.map.portal_at(hx, hy)
            if portal:
                hover_lines.append(f"Portal: {portal.id}")
            for line in hover_lines:
                surf = self.font_small.render(line, True, PANEL_TEXT)
                self.screen.blit(surf, (panel.x + 10, y))
                y += 18

        y += 10
        self.screen.blit(self.font.render("Shortcuts", True, PANEL_TEXT), (panel.x + 10, y))
        y += 20
        shortcuts = [
            "1/2: layer",
            "B/F/R/L/E/I: tools",
            "T/N/G/C/O: modes",
            "Ctrl+S: Save",
            "Ctrl+O: Load",
            "Ctrl+Z/Y: Undo/Redo",
            "+/-: Zoom",
            "A: add (mode)",
        ]
        for sc in shortcuts:
            surf = self.font_small.render(sc, True, PANEL_TEXT)
            self.screen.blit(surf, (panel.x + 10, y))
            y += 16

    def _draw_canvas(self) -> None:
        canvas = self._canvas_rect()
        pygame.draw.rect(self.screen, config.GRAY_DARK, canvas)
        tile_px = int(self.map.tile_size * self.zoom)
        start_x = int(self.camera[0] // tile_px)
        start_y = int(self.camera[1] // tile_px)
        offset_x = -(self.camera[0] - start_x * tile_px) + canvas.x
        offset_y = -(self.camera[1] - start_y * tile_px) + canvas.y
        visible_x = canvas.width // tile_px + 2
        visible_y = canvas.height // tile_px + 2

        ground_layers = [layer for layer in self.map.layers if layer.name != "overlay"]
        overlay_layers = [layer for layer in self.map.layers if layer.name == "overlay"]

        for y in range(visible_y):
            map_y = start_y + y
            if map_y >= self.map.height or map_y < 0:
                continue
            for x in range(visible_x):
                map_x = start_x + x
                if map_x >= self.map.width or map_x < 0:
                    continue
                dest_x = offset_x + x * tile_px
                dest_y = offset_y + y * tile_px
                rect = pygame.Rect(dest_x, dest_y, tile_px, tile_px)
                for layer in ground_layers:
                    tile_id = layer.tiles[map_y][map_x]
                    self._blit_tile(tile_id, rect, tile_px)
                for entity in self.map.find_entities_at(map_x, map_y):
                    if entity.hidden:
                        continue
                    pygame.draw.rect(self.screen, (120, 200, 255), rect.inflate(-4, -4))
                    label = self.font_small.render(entity.id, True, config.BLACK)
                    self.screen.blit(label, (rect.x + 2, rect.y + 2))
                for trigger in self.map.find_triggers_at(map_x, map_y, None):
                    pygame.draw.circle(self.screen, (255, 220, 80), rect.center, max(4, tile_px // 8))
                portal = self.map.portal_at(map_x, map_y)
                if portal:
                    pygame.draw.circle(self.screen, (80, 255, 120), rect.center, max(5, tile_px // 6), 2)
                for layer in overlay_layers:
                    tile_id = layer.tiles[map_y][map_x]
                    self._blit_tile(tile_id, rect, tile_px)
                pygame.draw.rect(self.screen, config.BLACK, rect, 1)

        if self.hover_cell:
            hx, hy = self.hover_cell
            if self.map.in_bounds(hx, hy):
                dest_x = offset_x + (hx - start_x) * tile_px
                dest_y = offset_y + (hy - start_y) * tile_px
                rect = pygame.Rect(dest_x, dest_y, tile_px, tile_px)
                pygame.draw.rect(self.screen, HIGHLIGHT, rect, 2)

        if self.drag_preview_pos and (self.dragging_npc_id or self.dragging_entity):
            cell = self._cell_from_mouse(self.drag_preview_pos)
            if cell and self.map.in_bounds(cell[0], cell[1]):
                dest_x = offset_x + (cell[0] - start_x) * tile_px
                dest_y = offset_y + (cell[1] - start_y) * tile_px
                rect = pygame.Rect(dest_x, dest_y, tile_px, tile_px)
                pygame.draw.rect(self.screen, (180, 220, 255), rect, 2)
                label_text = self.dragging_npc_id or (self.dragging_entity.sprite_id if self.dragging_entity else "")
                if label_text:
                    label = self.font_small.render(label_text, True, config.BLACK)
                    self.screen.blit(label, (rect.x + 2, rect.y + 2))

    def _blit_tile(self, tile_id: Optional[str], rect: pygame.Rect, tile_px: int) -> None:
        if tile_id is None:
            return
        img_entry = self.tile_images.get(tile_id)
        if img_entry and img_entry.get("frames"):
            frame = img_entry["frames"][0]
            frame_scaled = pygame.transform.scale(frame, (tile_px, tile_px))
            self.screen.blit(frame_scaled, rect)
        else:
            pygame.draw.rect(self.screen, config.GRAY_MEDIUM, rect)

    def _draw_status(self) -> None:
        bar_rect = pygame.Rect(PALETTE_WIDTH, self.screen.get_height() - 24, self.screen.get_width() - PALETTE_WIDTH - INSPECTOR_WIDTH, 24)
        pygame.draw.rect(self.screen, PANEL_BG, bar_rect)
        text = self.font_small.render(self.status_message, True, PANEL_TEXT)
        self.screen.blit(text, (bar_rect.x + 6, bar_rect.y + 4))

    def _draw_toolbar(self) -> None:
        toolbar = pygame.Rect(
            PALETTE_WIDTH + CANVAS_MARGIN,
            CANVAS_MARGIN,
            self.screen.get_width() - PALETTE_WIDTH - INSPECTOR_WIDTH - CANVAS_MARGIN * 2,
            TOOLBAR_HEIGHT - 10,
        )
        pygame.draw.rect(self.screen, PANEL_BG, toolbar)
        self.tool_button_rects = []
        self.mode_button_rects = []
        self.layer_button_rects = []
        start_x = toolbar.x + 10
        y = toolbar.y + 8
        tool_right_reserved = 260  # space for world/new/help buttons
        btn_width = 86

        def draw_button(label: str, key: str, collection: List[Tuple[pygame.Rect, str]]) -> None:
            nonlocal start_x, y
            rect = pygame.Rect(start_x, y, btn_width, 26)
            if collection is self.tool_button_rects and start_x + rect.width > toolbar.right - tool_right_reserved:
                start_x = toolbar.x + 10
                y += 30
                rect.topleft = (start_x, y)
            active = (
                (collection is self.tool_button_rects and self.tool == key)
                or (collection is self.mode_button_rects and self.mode == key)
                or (collection is self.layer_button_rects and self.active_layer == key)
            )
            pygame.draw.rect(self.screen, HIGHLIGHT if active else config.GRAY_DARK, rect, 2 if active else 1)
            text = self.font_small.render(label, True, PANEL_TEXT)
            text_rect = text.get_rect(center=rect.center)
            self.screen.blit(text, text_rect)
            collection.append((rect, key))
            start_x += rect.width + 8

        # Tool row
        for label, key in [("Brush", "brush"), ("Fill", "fill"), ("Rect", "rect"), ("Line", "line"), ("Erase", "erase"), ("Eye", "eyedropper")]:
            draw_button(label, key, self.tool_button_rects)

        # Mode row
        start_x = toolbar.x + 10
        y += 30
        for label, key in [("Tiles", "tiles"), ("Entities", "entities"), ("Triggers", "triggers"), ("Connect", "connections"), ("Overrides", "overrides")]:
            draw_button(label, key, self.mode_button_rects)

        # Layer row
        start_x = toolbar.x + 10
        y += 30
        for label, key in [("Ground", "ground"), ("Overlay", "overlay")]:
            draw_button(label, key, self.layer_button_rects)

        # Help toggle and new map buttons on right
        self.help_button_rect = pygame.Rect(toolbar.right - 80, toolbar.y + 8, 70, 26)
        self.new_map_button_rect = pygame.Rect(toolbar.right - 160, toolbar.y + 8, 70, 26)
        self.world_view_button_rect = pygame.Rect(toolbar.right - 240, toolbar.y + 8, 70, 26)
        pygame.draw.rect(self.screen, (200, 150, 60) if self.help_mode else config.GRAY_DARK, self.help_button_rect, 0)
        label = "Help?" if not self.help_mode else "Help On"
        text = self.font_small.render(label, True, PANEL_TEXT)
        text_rect = text.get_rect(center=self.help_button_rect.center)
        self.screen.blit(text, text_rect)

        pygame.draw.rect(self.screen, HIGHLIGHT, self.new_map_button_rect, 1)
        text = self.font_small.render("New Map", True, PANEL_TEXT)
        text_rect = text.get_rect(center=self.new_map_button_rect.center)
        self.screen.blit(text, text_rect)

        pygame.draw.rect(self.screen, HIGHLIGHT, self.world_view_button_rect, 1)
        text = self.font_small.render("World", True, PANEL_TEXT)
        text_rect = text.get_rect(center=self.world_view_button_rect.center)
        self.screen.blit(text, text_rect)

    def _tooltip_for(self, key: str) -> str:
        tips = {
            "brush": "Brush: paint the selected tile on a single cell.",
            "fill": "Fill: flood-fill the active layer starting from the clicked cell.",
            "rect": "Rect: drag to fill a rectangle with the selected tile.",
            "line": "Line: drag to draw a straight line of the selected tile.",
            "erase": "Erase: clear the tile from the active layer.",
            "eyedropper": "Eyedropper: pick the tile under the cursor.",
            "tiles": "Tiles mode: edit ground/overlay tiles.",
            "entities": "Entities mode: select or add NPC/object entries.",
            "triggers": "Triggers mode: select or add onEnter/onInteract triggers.",
            "connections": "Connections mode: add portals or edge transfers between maps.",
            "overrides": "Overrides mode: toggle walkable/spawn flags per cell.",
            "ground": "Ground layer: base tiles the player walks on.",
            "overlay": "Overlay layer: decorative tiles drawn above entities.",
            "add_tile": "Add a new tile to the tileset with autogenerated placeholder art.",
            "add_npc": "Add a new NPC sprite to the tileset with autogenerated frames.",
            "new_map": "Create a new map and optionally connect it to the current map.",
            "world_view": "Open world view to arrange maps, zoom, and auto-connect edges.",
        }
        return tips.get(key, "No help available.")

    def _add_tile(self) -> None:
        if not self.tileset:
            self.status_message = "No tileset loaded."
            return
        new_id = prompt_text(self.screen, self.font, "New tile id:", "tile_new")
        if not new_id:
            return
        name = prompt_text(self.screen, self.font, "Tile name:", new_id) or new_id
        filename = f"{new_id}.png"
        color = [random.randint(50, 230) for _ in range(3)] + [255]
        tile = TileDefinition(
            id=new_id,
            name=name,
            filename=filename,
            frames=[filename],
            frame_duration_ms=200,
            properties={"walkable": True, "color": color},
        )
        self.tileset.add_or_update_tile(tile)
        self.tileset.save()
        self.tileset.ensure_assets()
        self.tile_images = load_tileset_images(self.tileset, self.map.tile_size)
        self.selected_tile = new_id
        self.status_message = f"Added tile '{new_id}' (auto-colored)."

    def _add_npc(self) -> None:
        if not self.tileset:
            self.status_message = "No tileset loaded."
            return
        new_id = prompt_text(self.screen, self.font, "New NPC id:", "npc_new")
        if not new_id:
            return
        name = prompt_text(self.screen, self.font, "NPC name:", new_id) or new_id
        color = [random.randint(50, 230) for _ in range(3)] + [255]
        npc = NPCSprite(
            id=new_id,
            name=name,
            frame_duration_ms=200,
            states=self._build_default_npc_states(new_id),
        )
        self.tileset.add_or_update_npc(npc)
        self.tileset.save()
        self.tileset.ensure_assets()
        self.selected_npc = new_id
        self.status_message = f"Added NPC '{new_id}' with placeholder art."

    # Save/load ------------------------------------------------------------
    def _save_map(self) -> None:
        if not self.tileset:
            self.status_message = "Cannot save: no tileset."
            return
        errors, warnings = self.map.validate(self.tileset)
        if errors:
            self.status_message = f"Validation failed: {errors[0]}"
            return
        self.map.save()
        self.status_message = "Map saved."

    def _load_map_prompt(self) -> None:
        new_id = prompt_text(self.screen, self.font, "Map id to load:", self.map.id)
        if not new_id:
            return
        path = os.path.join(config.MAP_DIR, f"{new_id}.json")
        if not os.path.exists(path):
            self.status_message = f"Map {new_id} not found."
            return
        self.map = MapData.load(path)
        self.tileset = self._load_tileset(self.map.tileset_id)
        self.tile_images = load_tileset_images(self.tileset, self.map.tile_size)
        if self.tileset and self.tileset.tiles:
            self.selected_tile = self.tileset.tiles[0].id
        if self.tileset and self.tileset.npcs:
            self.selected_npc = self.tileset.npcs[0].id
        self.status_message = f"Loaded map {self.map.id}"

    def _edit_metadata(self) -> None:
        new_id = prompt_text(self.screen, self.font, "Map id:", self.map.id) or self.map.id
        new_name = prompt_text(self.screen, self.font, "Map name:", self.map.name) or self.map.name
        new_tileset = prompt_text(self.screen, self.font, "Tileset id:", self.map.tileset_id) or self.map.tileset_id
        width_text = prompt_text(self.screen, self.font, "Width:", str(self.map.width))
        height_text = prompt_text(self.screen, self.font, "Height:", str(self.map.height))
        tile_size_text = prompt_text(self.screen, self.font, "Tile size:", str(self.map.tile_size))
        music_id = prompt_text(self.screen, self.font, "Music id (optional):", self.map.music_id or "") or None
        try:
            new_width = max(1, int(width_text or self.map.width))
            new_height = max(1, int(height_text or self.map.height))
            new_tile_size = max(1, int(tile_size_text or self.map.tile_size))
        except ValueError:
            self.status_message = "Invalid dimensions."
            return
        self.push_history()
        self.map.id = new_id
        self.map.name = new_name
        self.map.tileset_id = new_tileset
        self.map.width = new_width
        self.map.height = new_height
        self.map.tile_size = new_tile_size
        self.map.music_id = music_id
        # Trim overrides out of bounds
        for coord in list(self.map.overrides.keys()):
            if not self.map.in_bounds(*coord):
                self.map.overrides.pop(coord, None)
        self.map._normalize_layers()
        self.tileset = self._load_tileset(self.map.tileset_id)
        self.tile_images = load_tileset_images(self.tileset, self.map.tile_size)
        if self.tileset and self.tileset.tiles:
            self.selected_tile = self.tileset.tiles[0].id
        self.status_message = "Updated metadata."

    # Utility --------------------------------------------------------------
    def _bresenham_line(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        x1, y1 = start
        x2, y2 = end
        points = []
        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        while True:
            points.append((x1, y1))
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x1 += sx
            if e2 <= dx:
                err += dx
                y1 += sy
        return points

    # Palette helpers -----------------------------------------------------
    def _draw_tile_palette(self, panel: pygame.Rect) -> None:
        tile_px = 48
        padding = 8
        for idx, tile in enumerate(self.tileset.tiles):
            col = idx % 3
            row = idx // 3
            x = 10 + col * (tile_px + padding)
            y = 40 + row * (tile_px + padding)
            rect = pygame.Rect(x, y, tile_px, tile_px)
            selected = tile.id == self.selected_tile
            pygame.draw.rect(self.screen, HIGHLIGHT if selected else config.GRAY_DARK, rect, 2 if selected else 1)
            img_entry = self.tile_images.get(tile.id)
            if img_entry and img_entry.get("frames"):
                frame = img_entry["frames"][0]
                frame_scaled = pygame.transform.scale(frame, (tile_px - 6, tile_px - 6))
                self.screen.blit(frame_scaled, (x + 3, y + 3))
            else:
                pygame.draw.rect(self.screen, config.GRAY_MEDIUM, rect.inflate(-6, -6))
            label = self.font_small.render(tile.id, True, PANEL_TEXT)
            self.screen.blit(label, (x, y + tile_px + 2))

    def _draw_npc_palette(self, panel: pygame.Rect) -> None:
        start_y = 40
        row_h = 36
        for idx, npc in enumerate(self.tileset.npcs):
            rect = pygame.Rect(10, start_y + idx * row_h, PALETTE_WIDTH - 20, row_h - 6)
            selected = npc.id == self.selected_npc
            pygame.draw.rect(self.screen, HIGHLIGHT if selected else config.GRAY_DARK, rect, 2 if selected else 1)
            label = self.font_small.render(npc.id, True, PANEL_TEXT)
            self.screen.blit(label, (rect.x + 8, rect.y + 8))

    # NPC helpers ---------------------------------------------------------
    def _build_default_npc_states(self, npc_id: str) -> Dict[str, Dict[str, List[str]]]:
        states: Dict[str, Dict[str, List[str]]] = {}
        for state in ["standing", "walking"]:
            states[state] = {}
            for angle in ["south", "west", "east", "north"]:
                states[state][angle] = [f"{npc_id}_{state}_{angle}.png"]
        return states

    def _ensure_npc_frames(self, npc: NPCSprite) -> None:
        desired_states = self._build_default_npc_states(npc.id)
        updated = False
        for state, angles in desired_states.items():
            npc.states.setdefault(state, {})
            for angle, frames in angles.items():
                if not npc.states[state].get(angle):
                    npc.states[state][angle] = frames
                    updated = True
        if updated:
            self.tileset.add_or_update_npc(npc)
            self.tileset.save()
            self.tileset.ensure_assets()

    def _ensure_all_npc_frames(self) -> None:
        if not self.tileset:
            return
        for npc in self.tileset.npcs:
            self._ensure_npc_frames(npc)

    # External editor -----------------------------------------------------
    def _open_art_editor(self, kind: str, identifier: str) -> None:
        editor_path = os.path.join(config.PROJECT_ROOT, "pixle_art_editor.py")
        if not os.path.exists(editor_path):
            self.status_message = "Pixel editor entrypoint not found."
            return
        if kind == "npc" and self.tileset:
            for npc in self.tileset.npcs:
                if npc.id == identifier:
                    self._ensure_npc_frames(npc)
                    break
        try:
            subprocess.Popen([sys.executable, editor_path])
            self.status_message = f"Opening pixel editor for {kind} '{identifier}'..."
        except Exception as e:
            self.status_message = f"Failed to open editor: {e}"

    def _open_world_view(self) -> None:
        world_view_path = os.path.join(config.PROJECT_ROOT, "src", "overworld", "world_view.py")
        if not os.path.exists(world_view_path):
            self.status_message = "World view not found."
            return
        try:
            subprocess.Popen([sys.executable, world_view_path])
            self.status_message = "Opened world view."
        except Exception as e:
            self.status_message = f"Failed to open world view: {e}"

    # Map creation --------------------------------------------------------
    def _new_map_dialog(self) -> None:
        new_id = prompt_text(self.screen, self.font, "New map id:", f"{self.map.id}_new")
        if not new_id:
            return
        width = prompt_text(self.screen, self.font, "Width:", str(self.map.width)) or str(self.map.width)
        height = prompt_text(self.screen, self.font, "Height:", str(self.map.height)) or str(self.map.height)
        try:
            w = max(1, int(width))
            h = max(1, int(height))
        except ValueError:
            self.status_message = "Invalid width/height."
            return
        connect = prompt_text(self.screen, self.font, "Connect to current? (edge/portal/none):", "none") or "none"
        new_map = MapData(
            map_id=new_id,
            name=new_id,
            version="1.0.0",
            tile_size=self.map.tile_size,
            dimensions=(w, h),
            tileset_id=self.map.tileset_id,
            layers=[
                MapLayer(name="ground", tiles=[[None for _ in range(w)] for _ in range(h)]),
                MapLayer(name="overlay", tiles=[[None for _ in range(w)] for _ in range(h)]),
            ],
            connections=[],
            entities=[],
            triggers=[],
            overrides={},
        )
        if connect.lower() in ("edge", "portal"):
            self._connect_new_map(new_map, connect.lower())
        new_map.save()
        self.map = new_map
        self.tile_images = load_tileset_images(self.tileset, self.map.tile_size)
        self.status_message = f"Created and opened new map '{new_id}'."

    def _connect_new_map(self, new_map: MapData, mode: str) -> None:
        if mode == "edge":
            direction = prompt_text(self.screen, self.font, "Direction from current (north/east/south/west):", "north") or "north"
            spawn_x = int(prompt_text(self.screen, self.font, "New map spawn x:", "1") or 1)
            spawn_y = int(prompt_text(self.screen, self.font, "New map spawn y:", "1") or 1)
            facing = prompt_text(self.screen, self.font, "Facing on arrival:", "south") or "south"
            conn_id = f"{direction}_to_{new_map.id}"
            connection = Connection(
                id=conn_id,
                type="edge",
                from_ref=direction,
                to={"mapId": new_map.id, "spawn": {"x": spawn_x, "y": spawn_y}, "facing": facing},
                condition=None,
                extra={},
            )
            self.map.connections.append(connection)
            # Reciprocal
            opposite = {"north": "south", "south": "north", "east": "west", "west": "east"}.get(direction, "south")
            new_map.connections.append(
                Connection(
                    id=f"{opposite}_to_{self.map.id}",
                    type="edge",
                    from_ref=opposite,
                    to={"mapId": self.map.id, "spawn": {"x": self.map.spawn_point()[0], "y": self.map.spawn_point()[1]}, "facing": direction},
                    condition=None,
                    extra={},
                )
            )
        elif mode == "portal":
            portal_x = int(prompt_text(self.screen, self.font, "Portal X on current map:", "0") or 0)
            portal_y = int(prompt_text(self.screen, self.font, "Portal Y on current map:", "0") or 0)
            spawn_x = int(prompt_text(self.screen, self.font, "New map spawn x:", "1") or 1)
            spawn_y = int(prompt_text(self.screen, self.font, "New map spawn y:", "1") or 1)
            conn_id = f"portal_to_{new_map.id}"
            connection = Connection(
                id=conn_id,
                type="portal",
                from_ref={"x": portal_x, "y": portal_y},
                to={"mapId": new_map.id, "spawn": {"x": spawn_x, "y": spawn_y}},
                condition=None,
                extra={},
            )
            self.map.connections.append(connection)
            new_map.connections.append(
                Connection(
                    id=f"portal_to_{self.map.id}",
                    type="portal",
                    from_ref={"x": 0, "y": 0},
                    to={"mapId": self.map.id, "spawn": {"x": self.map.spawn_point()[0], "y": self.map.spawn_point()[1]}},
                    condition=None,
                    extra={},
                )
            )


def main() -> None:
    map_path = sys.argv[1] if len(sys.argv) > 1 else None
    editor = MapEditor(map_path)
    editor.run()


if __name__ == "__main__":
    main()
