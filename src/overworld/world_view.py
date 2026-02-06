import json
import os
from typing import Dict, List, Optional, Tuple
import math

import pygame

from src.core import config
from src.core.tileset import TileSet
from src.overworld.state import Connection, MapData, MapLayer

LAYOUT_FILE = os.path.join(config.MAP_DIR, "world_layout.json")
AUTO_FLAG = "world"
SNAP_STEP = 1  # tiles
EPS = 0.5


def list_maps() -> List[str]:
    if not os.path.isdir(config.MAP_DIR):
        return []
    return sorted([f[:-5] for f in os.listdir(config.MAP_DIR) if f.endswith(".json")])


def load_layout() -> Dict[str, Dict[str, int]]:
    if not os.path.exists(LAYOUT_FILE):
        return {}
    try:
        with open(LAYOUT_FILE, "r") as f:
            data = json.load(f)
        return data.get("maps", {})
    except Exception:
        return {}


def save_layout(layout: Dict[str, Dict[str, int]]) -> None:
    os.makedirs(config.MAP_DIR, exist_ok=True)
    with open(LAYOUT_FILE, "w") as f:
        json.dump({"maps": layout}, f, indent=2)


def _tile_walkable(map_data: MapData, tileset: Optional[TileSet], x: int, y: int) -> bool:
    x = int(x)
    y = int(y)
    if not map_data.in_bounds(x, y):
        return False
    walkable = True
    for layer in map_data.layers:
        tile_id = layer.tiles[y][x]
        if tile_id is None:
            continue
        if tileset:
            tile_def = next((t for t in tileset.tiles if t.id == tile_id), None)
            if tile_def and tile_def.properties.get("walkable") is False:
                walkable = False
    override = map_data.get_override(x, y)
    if override and override.walkable is not None:
        walkable = override.walkable
    return walkable


def _make_preview(map_data: MapData, tileset: Optional[TileSet]) -> pygame.Surface:
    """Tiny color-coded preview (1px per tile) scaled later."""
    surf = pygame.Surface((max(1, map_data.width), max(1, map_data.height)))
    for y in range(map_data.height):
        for x in range(map_data.width):
            color = (60, 60, 60)
            tile_id = map_data.get_tile("ground", x, y)
            if tileset and tile_id:
                tile_def = next((t for t in tileset.tiles if t.id == tile_id), None)
                if tile_def:
                    color = tuple(tile_def.properties.get("color", (120, 120, 120, 255))[:3])
            if not _tile_walkable(map_data, tileset, x, y):
                color = (80, 40, 40)
            surf.set_at((x, y), color)
    return surf


def _load_map_bundle(map_id: str):
    path = os.path.join(config.MAP_DIR, f"{map_id}.json")
    map_data = MapData.load(path)
    tileset_path = os.path.join(config.TILESET_DIR, f"{map_data.tileset_id}.json")
    tileset = TileSet.load(tileset_path) if os.path.exists(tileset_path) else None
    preview = _make_preview(map_data, tileset)
    return map_data, tileset, preview


class WorldView:
    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 800))
        pygame.display.set_caption("Overworld World View")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(config.DEFAULT_FONT, 16)
        self.font_small = pygame.font.Font(config.DEFAULT_FONT, 12)
        self.zoom = 4.0  # pixels per tile
        self.offset = [100.0, 80.0]
        self.dragging = False
        self.dragging_map: Optional[str] = None
        self.drag_offset = (0.0, 0.0)
        self.mouse_pan = False

        self.layout = load_layout()
        self.maps: Dict[str, MapData] = {}
        self.tilesets: Dict[str, TileSet] = {}
        self.previews: Dict[str, pygame.Surface] = {}
        self._load_maps()

    def _load_maps(self) -> None:
        self.maps.clear()
        self.tilesets.clear()
        self.previews.clear()
        ids = list_maps()
        for idx, map_id in enumerate(ids):
            map_data, tileset, preview = _load_map_bundle(map_id)
            self.maps[map_id] = map_data
            if tileset:
                self.tilesets[map_id] = tileset
            self.previews[map_id] = preview
            self.layout.setdefault(map_id, {"x": idx * (map_data.width + 4), "y": 0})

    def run(self) -> None:
        running = True
        self.manual_src: Optional[str] = None
        self.manual_dst: Optional[str] = None
        self.manual_mode = False
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False
                    elif event.key == pygame.K_r:
                        self._load_maps()
                    elif event.key == pygame.K_s:
                        save_layout(self.layout)
                    elif event.key == pygame.K_c:
                        self._auto_connect()
                    elif event.key == pygame.K_p:
                        self.manual_mode = not self.manual_mode
                        self.manual_src = None
                        self.manual_dst = None
                    elif event.key == pygame.K_RETURN and self.manual_src and self.manual_dst:
                        self._create_manual_connection()
                    elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                        self.zoom = min(24.0, self.zoom + 0.5)
                    elif event.key == pygame.K_MINUS or event.key == pygame.K_UNDERSCORE:
                        self.zoom = max(1.0, self.zoom - 0.5)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        clicked = self._map_at(event.pos)
                        if self.manual_mode:
                            self._handle_manual_click(clicked)
                        elif clicked:
                            self.dragging_map = clicked
                            map_pos = self._map_screen_rect(clicked).topleft
                            self.drag_offset = (event.pos[0] - map_pos[0], event.pos[1] - map_pos[1])
                        else:
                            self.mouse_pan = True
                            self.drag_offset = event.pos
                    elif event.button == 4:
                        self.zoom = min(24.0, self.zoom + 0.5)
                    elif event.button == 5:
                        self.zoom = max(1.0, self.zoom - 0.5)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        if self.dragging_map:
                            self._snap_map(self.dragging_map)
                        self.dragging_map = None
                        self.mouse_pan = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.dragging_map:
                        mx, my = event.pos
                        rect = self._map_screen_rect(self.dragging_map)
                        dx = mx - rect.x - self.drag_offset[0]
                        dy = my - rect.y - self.drag_offset[1]
                        map_id = self.dragging_map
                        self.layout[map_id]["x"] += dx / self.zoom
                        self.layout[map_id]["y"] += dy / self.zoom
                    elif self.mouse_pan:
                        dx = event.pos[0] - self.drag_offset[0]
                        dy = event.pos[1] - self.drag_offset[1]
                        self.offset[0] += dx
                        self.offset[1] += dy
                        self.drag_offset = event.pos

            self._draw()
            pygame.display.flip()
            self.clock.tick(config.FPS)
        pygame.quit()

    # Drawing --------------------------------------------------------------
    def _draw(self) -> None:
        self.screen.fill((18, 22, 26))
        self._draw_connections()
        # Draw maps
        for map_id, map_data in self.maps.items():
            rect = self._map_screen_rect(map_id)
            preview = self.previews.get(map_id)
            if preview:
                scaled = pygame.transform.scale(preview, rect.size)
                self.screen.blit(scaled, rect)
            pygame.draw.rect(self.screen, (200, 200, 200), rect, 2)
            label = self.font.render(map_id, True, (240, 240, 240))
            self.screen.blit(label, (rect.x + 6, rect.y + 6))
            dims = self.font_small.render(f"{map_data.width}x{map_data.height}", True, (200, 200, 200))
            self.screen.blit(dims, (rect.x + 6, rect.y + 26))

        # HUD
        hud_lines = [
            "World View: drag maps to arrange, wheel to zoom",
            "S: save layout, C: auto-connect, R: reload, Q/Esc: quit",
            f"Zoom: {self.zoom:.1f}px/tile  Maps: {len(self.maps)}",
            "P: manual portal mode (click source, then target, Enter to confirm)",
        ]
        y = 8
        for line in hud_lines:
            surf = self.font.render(line, True, (230, 230, 230))
            self.screen.blit(surf, (10, y))
            y += 22
        if self.manual_mode:
            status = "Manual: click source map" if not self.manual_src else "Manual: click target map" if not self.manual_dst else "Manual: press Enter to create portal"
            note = self.font_small.render(status, True, (200, 220, 255))
            self.screen.blit(note, (10, y + 4))

    def _draw_connections(self) -> None:
        seen = set()
        for map_id, map_data in self.maps.items():
            for conn in map_data.connections:
                target_id = conn.to.get("mapId") if conn.to else None
                if not target_id or target_id not in self.maps:
                    continue
                key = (map_id, conn.id, target_id)
                if key in seen:
                    continue
                seen.add(key)
                if conn.type == "edge":
                    start = self._edge_point(map_id, conn.from_ref or "right")
                    end = self._edge_point(target_id, conn.to.get("facing") or "left", opposite=True)
                    pygame.draw.line(self.screen, (120, 200, 255), start, end, 2)
                    pygame.draw.circle(self.screen, (200, 200, 80), end, 5)
                elif conn.type == "portal":
                    start = self._cell_point(map_id, conn.from_ref or {})
                    end = self._cell_point(target_id, conn.to.get("spawn") or {})
                    pygame.draw.line(self.screen, (200, 140, 255), start, end, 2)
                    pygame.draw.circle(self.screen, (200, 200, 80), end, 5)

    def _map_screen_rect(self, map_id: str) -> pygame.Rect:
        map_data = self.maps[map_id]
        pos = self.layout.get(map_id, {"x": 0, "y": 0})
        x = pos.get("x", 0) * self.zoom + self.offset[0]
        y = pos.get("y", 0) * self.zoom + self.offset[1]
        w = map_data.width * self.zoom
        h = map_data.height * self.zoom
        return pygame.Rect(int(x), int(y), int(w), int(h))

    def _edge_point(self, map_id: str, direction: str, opposite: bool = False) -> Tuple[int, int]:
        rect = self._map_screen_rect(map_id)
        if direction in ("left", "west"):
            return (rect.left, rect.centery)
        if direction in ("right", "east"):
            return (rect.right, rect.centery)
        if direction in ("up", "north"):
            return (rect.centerx, rect.top)
        return (rect.centerx, rect.bottom)

    def _cell_point(self, map_id: str, pos: Dict[str, int]) -> Tuple[int, int]:
        rect = self._map_screen_rect(map_id)
        x = rect.x + int(pos.get("x", 0)) * self.zoom + self.zoom / 2
        y = rect.y + int(pos.get("y", 0)) * self.zoom + self.zoom / 2
        return (int(x), int(y))

    def _map_at(self, pos: Tuple[int, int]) -> Optional[str]:
        for map_id in reversed(list(self.maps.keys())):
            if self._map_screen_rect(map_id).collidepoint(pos):
                return map_id
        return None

    def _snap_map(self, map_id: str) -> None:
        pos = self.layout.get(map_id, {"x": 0, "y": 0})
        pos["x"] = round(pos.get("x", 0) / SNAP_STEP) * SNAP_STEP
        pos["y"] = round(pos.get("y", 0) / SNAP_STEP) * SNAP_STEP
        self.layout[map_id] = pos

    # Auto connection generation ------------------------------------------
    def _auto_connect(self) -> None:
        # Load fresh copies to avoid sharing mutable references
        bundles = {mid: _load_map_bundle(mid) for mid in self.maps.keys()}
        updated: Dict[str, MapData] = {}
        for map_id, (map_data, tileset, _) in bundles.items():
            # drop previous auto connections
            map_data.connections = [c for c in map_data.connections if c.extra.get("auto") != AUTO_FLAG]
            updated[map_id] = map_data

        # Build adjacency based on layout
        ids = sorted(updated.keys())
        for i, a_id in enumerate(ids):
            a_map = updated[a_id]
            a_pos = self.layout.get(a_id, {"x": 0, "y": 0})
            for b_id in ids[i + 1 :]:
                b_map = updated[b_id]
                b_pos = self.layout.get(b_id, {"x": 0, "y": 0})
                self._maybe_connect_pair(a_id, a_map, bundles[a_id][1], a_pos, b_id, b_map, bundles[b_id][1], b_pos)

        # Save + refresh runtime copies
        for map_id, map_data in updated.items():
            map_data.save()
            self.maps[map_id] = map_data
        save_layout(self.layout)

    def _maybe_connect_pair(
        self,
        a_id: str,
        a_map: MapData,
        a_tileset: Optional[TileSet],
        a_pos: Dict[str, float],
        b_id: str,
        b_map: MapData,
        b_tileset: Optional[TileSet],
        b_pos: Dict[str, float],
    ) -> None:
        ax, ay = a_pos.get("x", 0), a_pos.get("y", 0)
        bx, by = b_pos.get("x", 0), b_pos.get("y", 0)

        # Horizontal adjacency (A right to B left)
        if abs((ax + a_map.width) - bx) < EPS:
            overlap_y0 = max(ay, by)
            overlap_y1 = min(ay + a_map.height, by + b_map.height)
            start = int(math.ceil(overlap_y0))
            end = int(math.floor(overlap_y1))
            for gy in range(start, end):
                ay_local = int(round(gy - ay))
                by_local = int(round(gy - by))
                if _tile_walkable(a_map, a_tileset, a_map.width - 1, ay_local) and _tile_walkable(b_map, b_tileset, 0, by_local):
                    self._add_auto_edge(
                        a_map,
                        "right",
                        b_id,
                        {"x": 0, "y": by_local},
                        facing="right",
                        y_tag=ay_local,
                    )
                    self._add_auto_edge(
                        b_map,
                        "left",
                        a_id,
                        {"x": a_map.width - 1, "y": ay_local},
                        facing="left",
                        y_tag=by_local,
                    )
        # Vertical adjacency (A bottom to B top)
        if abs((ay + a_map.height) - by) < EPS:
            overlap_x0 = max(ax, bx)
            overlap_x1 = min(ax + a_map.width, bx + b_map.width)
            start = int(math.ceil(overlap_x0))
            end = int(math.floor(overlap_x1))
            for gx in range(start, end):
                ax_local = int(round(gx - ax))
                bx_local = int(round(gx - bx))
                if _tile_walkable(a_map, a_tileset, ax_local, a_map.height - 1) and _tile_walkable(b_map, b_tileset, bx_local, 0):
                    self._add_auto_edge(
                        a_map,
                        "down",
                        b_id,
                        {"x": bx_local, "y": 0},
                        facing="down",
                        x_tag=ax_local,
                    )
                    self._add_auto_edge(
                        b_map,
                        "up",
                        a_id,
                        {"x": ax_local, "y": a_map.height - 1},
                        facing="up",
                        x_tag=bx_local,
                    )

    def _add_auto_edge(
        self,
        source_map: MapData,
        direction: str,
        target_id: str,
        spawn: Dict[str, int],
        facing: str,
        x_tag: Optional[int] = None,
        y_tag: Optional[int] = None,
    ) -> None:
        tag = x_tag if x_tag is not None else y_tag if y_tag is not None else 0
        extra = {"auto": AUTO_FLAG}
        if x_tag is not None or y_tag is not None:
            extra["sourceEdgeCoord"] = int(tag)
        conn_id = f"auto_{direction}_{target_id}_{tag}"
        source_map.connections.append(
            Connection(
                id=conn_id,
                type="edge",
                from_ref=direction,
                to={"mapId": target_id, "spawn": spawn, "facing": facing},
                condition=None,
                extra=extra,
            )
        )

    # Manual portal creation ----------------------------------------------
    def _handle_manual_click(self, map_id: Optional[str]) -> None:
        if not map_id:
            return
        if not self.manual_src:
            self.manual_src = map_id
        elif not self.manual_dst:
            self.manual_dst = map_id

    def _prompt_text(self, message: str, default: str = "") -> Optional[str]:
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
            overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            lines = [message, "> " + input_text, "Enter to confirm, Esc to cancel"]
            for idx, line in enumerate(lines):
                surf = self.font.render(line, True, (230, 230, 230))
                rect = surf.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() // 2 + idx * 24))
                self.screen.blit(surf, rect)
            pygame.display.flip()
            clock.tick(30)

    def _create_manual_connection(self) -> None:
        if not (self.manual_src and self.manual_dst):
            return
        src = self.manual_src
        dst = self.manual_dst
        try:
            sx = int(self._prompt_text(f"{src} portal X:", "0") or "0")
            sy = int(self._prompt_text(f"{src} portal Y:", "0") or "0")
            tx = int(self._prompt_text(f"{dst} spawn X:", "0") or "0")
            ty = int(self._prompt_text(f"{dst} spawn Y:", "0") or "0")
        except (TypeError, ValueError):
            self.manual_src = None
            self.manual_dst = None
            self.manual_mode = False
            return
        conn = Connection(
            id=f"portal_{src}_to_{dst}_{sx}_{sy}",
            type="portal",
            from_ref={"x": sx, "y": sy},
            to={"mapId": dst, "spawn": {"x": tx, "y": ty}},
            condition=None,
            extra={"manual": True},
        )
        self.maps[src].connections.append(conn)
        # optional reciprocal
        try:
            do_back = self._prompt_text("Add reverse portal? (y/n):", "y")
            if do_back and do_back.lower().startswith("y"):
                back = Connection(
                    id=f"portal_{dst}_to_{src}_{tx}_{ty}",
                    type="portal",
                    from_ref={"x": tx, "y": ty},
                    to={"mapId": src, "spawn": {"x": sx, "y": sy}},
                    condition=None,
                    extra={"manual": True},
                )
                self.maps[dst].connections.append(back)
        except Exception:
            pass
        self.maps[src].save()
        if dst in self.maps:
            self.maps[dst].save()
        self.manual_src = None
        self.manual_dst = None
        self.manual_mode = False


def main() -> None:
    viewer = WorldView()
    viewer.run()


if __name__ == "__main__":
    main()
