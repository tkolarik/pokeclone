import os
import sys
from typing import Dict, Optional

import pygame

from src.core import config
from src.core.tileset import TileSet
from src.overworld.state import MapData, MapLayer, OverworldSession


class OverworldAudio:
    """Simple audio controller that respects map music ids."""

    def __init__(self) -> None:
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error:
                # Audio not available; fall back to silent controller
                self.disabled = True
                return
        self.disabled = False

    def play_music(self, music_id: Optional[str]) -> None:
        if self.disabled or not music_id:
            return
        path = os.path.join(config.SONGS_DIR, music_id)
        if not os.path.splitext(path)[1]:
            # Try common extensions if not provided
            for ext in (".mp3", ".ogg", ".wav"):
                candidate = f"{path}{ext}"
                if os.path.exists(candidate):
                    path = candidate
                    break
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play(-1)
        except pygame.error:
            return

    def stop_music(self) -> None:
        if self.disabled:
            return
        pygame.mixer.music.stop()

    def play_sound(self, sound_id: Optional[str]) -> None:
        if self.disabled or not sound_id:
            return
        path = os.path.join(config.SOUNDS_DIR, sound_id)
        if not os.path.exists(path):
            return
        try:
            sound = pygame.mixer.Sound(path)
            sound.play()
        except pygame.error:
            return


def load_tileset_images(tileset: Optional[TileSet], tile_size: int) -> Dict[str, Dict[str, object]]:
    """Load tile images (all frames) from disk and scale them to the tileset size."""
    images: Dict[str, Dict[str, object]] = {}
    if not tileset:
        return images
    for tile in tileset.tiles:
        frames = []
        frame_names = tile.frames or [tile.filename]
        total_frames = len(frame_names)
        for idx in range(total_frames):
            path = tileset.tile_image_path(tile, idx)
            try:
                surf = pygame.image.load(path).convert_alpha()
            except pygame.error:
                surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                color = tile.properties.get("color", [170, 170, 170, 255])
                pygame.draw.rect(surf, color, surf.get_rect())
            if surf.get_size() != (tile_size, tile_size):
                surf = pygame.transform.scale(surf, (tile_size, tile_size))
            frames.append(surf)
        images[tile.id] = {"frames": frames, "duration": max(1, tile.frame_duration_ms)}
    return images


def load_npc_images(tileset: Optional[TileSet], tile_size: int) -> Dict[str, Dict[str, object]]:
    """Load NPC sprites (all states/angles/frames) from disk and scale them to the tileset size."""
    images: Dict[str, Dict[str, object]] = {}
    if not tileset:
        return images
    for npc in tileset.npcs:
        npc_entry: Dict[str, object] = {"duration": max(1, npc.frame_duration_ms), "states": {}}
        for state, angles in npc.states.items():
            state_entry: Dict[str, list] = {}
            for angle, frames in angles.items():
                frame_list = []
                frame_names = frames or [f"{npc.id}_{state}_{angle}.png"]
                for idx in range(len(frame_names)):
                    path = tileset.npc_image_path(npc, state, angle, idx)
                    try:
                        surf = pygame.image.load(path).convert_alpha()
                    except pygame.error:
                        surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                        pygame.draw.rect(surf, config.BLUE, surf.get_rect())
                    if surf.get_size() != (tile_size, tile_size):
                        surf = pygame.transform.scale(surf, (tile_size, tile_size))
                    frame_list.append(surf)
                state_entry[angle] = frame_list
            npc_entry["states"][state] = state_entry
        images[npc.id] = npc_entry
    return images


def _normalize_facing(facing: Optional[str]) -> str:
    if not facing:
        return "south"
    return {
        "down": "south",
        "up": "north",
        "left": "west",
        "right": "east",
    }.get(facing, facing)


def _select_npc_frame(npc_images: Dict[str, Dict[str, object]], npc_id: str, state: str, angle: str) -> Optional[pygame.Surface]:
    entry = npc_images.get(npc_id)
    if not entry:
        return None
    states = entry.get("states", {})
    state_entry = states.get(state) or (next(iter(states.values()), {}) if states else {})
    if not state_entry:
        return None
    angle_entry = state_entry.get(angle) or (next(iter(state_entry.values()), []) if state_entry else [])
    if not angle_entry:
        return None
    duration = max(1, entry.get("duration", 200))
    frame_idx = (pygame.time.get_ticks() // duration) % len(angle_entry)
    return angle_entry[frame_idx]


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list:
    words = text.split()
    if not words:
        return []
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_message(screen: pygame.Surface, font: pygame.font.Font, message: str) -> None:
    if not message:
        return
    padding = 10
    box_height = 90
    box_width = screen.get_width() - (padding * 2)
    box_rect = pygame.Rect(padding, screen.get_height() - box_height - padding, box_width, box_height)
    overlay = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, box_rect.topleft)

    text_area_width = box_rect.width - (padding * 2)
    lines = wrap_text(message, font, text_area_width)
    for i, line in enumerate(lines):
        text_surf = font.render(line, True, config.WHITE)
        screen.blit(text_surf, (box_rect.x + padding, box_rect.y + padding + i * font.get_linesize()))


def draw_world(
    screen: pygame.Surface,
    session: OverworldSession,
    tile_images: Dict[str, Dict[str, object]],
    npc_images: Dict[str, Dict[str, object]],
    font_small: pygame.font.Font,
    debug: bool = False,
) -> None:
    tile_size = session.map.tile_size
    screen.fill(config.OVERWORLD_BG_COLOR)

    map_pixel_w = session.map.width * tile_size
    map_pixel_h = session.map.height * tile_size
    screen_w, screen_h = screen.get_size()

    center_x = session.player.x * tile_size + tile_size // 2
    center_y = session.player.y * tile_size + tile_size // 2
    camera_x = max(0, min(center_x - screen_w // 2, map_pixel_w - screen_w))
    camera_y = max(0, min(center_y - screen_h // 2, map_pixel_h - screen_h))

    start_tile_x = int(camera_x // tile_size)
    start_tile_y = int(camera_y // tile_size)
    offset_x = -(camera_x - start_tile_x * tile_size)
    offset_y = -(camera_y - start_tile_y * tile_size)

    visible_tiles_x = screen_w // tile_size + 2
    visible_tiles_y = screen_h // tile_size + 2

    ground_layers = [layer for layer in session.map.layers if layer.name != "overlay"]
    overlay_layers = [layer for layer in session.map.layers if layer.name == "overlay"]

    def _draw_tile(layer_tiles, map_x, map_y, dest_x, dest_y) -> None:
        tile_id = layer_tiles[map_y][map_x]
        if tile_id is None:
            return
        tile_entry = tile_images.get(tile_id)
        dest_rect = pygame.Rect(dest_x, dest_y, tile_size, tile_size)
        if isinstance(tile_entry, dict) and tile_entry.get("frames"):
            frames = tile_entry["frames"]
            duration = max(1, tile_entry.get("duration", 200))
            frame_idx = (pygame.time.get_ticks() // duration) % len(frames)
            screen.blit(frames[frame_idx], dest_rect)
        elif tile_entry:
            screen.blit(tile_entry, dest_rect)
        else:
            pygame.draw.rect(screen, config.GRAY_MEDIUM, dest_rect)

    for y in range(visible_tiles_y):
        map_y = start_tile_y + y
        if map_y >= session.map.height:
            continue
        for x in range(visible_tiles_x):
            map_x = start_tile_x + x
            if map_x >= session.map.width:
                continue
            dest_x = offset_x + x * tile_size
            dest_y = offset_y + y * tile_size
            for layer in ground_layers:
                _draw_tile(layer.tiles, map_x, map_y, dest_x, dest_y)

    # Entities and player (depth sort by y)
    renderables = []
    for entity in session.map.entities:
        if entity.hidden:
            continue
        renderables.append(("entity", entity.position.get("x", 0), entity.position.get("y", 0), entity))
    renderables.append(("player", session.player.x, session.player.y, session.player))
    renderables.sort(key=lambda item: item[2])

    for kind, map_x, map_y, obj in renderables:
        dest_x = offset_x + (map_x - start_tile_x) * tile_size
        dest_y = offset_y + (map_y - start_tile_y) * tile_size
        if dest_x + tile_size < 0 or dest_y + tile_size < 0 or dest_x > screen_w or dest_y > screen_h:
            continue
        rect = pygame.Rect(dest_x, dest_y, tile_size, tile_size)
        if kind == "player":
            facing = _normalize_facing(getattr(obj, "facing", None))
            sprite = _select_npc_frame(npc_images, "player", "standing", facing)
            if sprite:
                screen.blit(sprite, rect)
            else:
                pygame.draw.rect(screen, config.RED, rect)
                pygame.draw.rect(screen, config.BLACK, rect, 2)
        else:
            facing = _normalize_facing(getattr(obj, "facing", None))
            sprite_id = getattr(obj, "sprite_id", None) or getattr(obj, "id", None)
            state = "standing"
            if hasattr(obj, "properties") and isinstance(obj.properties, dict):
                state = obj.properties.get("state", state)
            if hasattr(obj, "extra") and isinstance(obj.extra, dict):
                state = obj.extra.get("state", state)
            sprite = _select_npc_frame(npc_images, sprite_id, state, facing) if sprite_id else None
            if sprite:
                screen.blit(sprite, rect)
            else:
                pygame.draw.rect(screen, config.BLUE, rect)
                pygame.draw.rect(screen, config.BLACK, rect, 1)
                if getattr(obj, "name", None):
                    label = font_small.render(str(obj.name)[:4], True, config.WHITE)
                    screen.blit(label, (rect.x + 2, rect.y + 2))

    # Overlay layers after entities/player
    for y in range(visible_tiles_y):
        map_y = start_tile_y + y
        if map_y >= session.map.height:
            continue
        for x in range(visible_tiles_x):
            map_x = start_tile_x + x
            if map_x >= session.map.width:
                continue
            dest_x = offset_x + x * tile_size
            dest_y = offset_y + y * tile_size
            for layer in overlay_layers:
                _draw_tile(layer.tiles, map_x, map_y, dest_x, dest_y)

    # Grid
    for x in range(visible_tiles_x + 1):
        gx = offset_x + x * tile_size
        pygame.draw.line(screen, config.GRAY_DARK, (gx, 0), (gx, screen_h), 1)
    for y in range(visible_tiles_y + 1):
        gy = offset_y + y * tile_size
        pygame.draw.line(screen, config.GRAY_DARK, (0, gy), (screen_w, gy), 1)

    if debug:
        _draw_debug_overlays(screen, session, start_tile_x, start_tile_y, visible_tiles_x, visible_tiles_y, offset_x, offset_y, tile_size)


def _draw_debug_overlays(screen: pygame.Surface, session: OverworldSession, start_x: int, start_y: int, tiles_x: int, tiles_y: int, offset_x: float, offset_y: float, tile_size: int) -> None:
    screen_w, screen_h = screen.get_size()
    for y in range(tiles_y):
        map_y = start_y + y
        if map_y >= session.map.height:
            continue
        for x in range(tiles_x):
            map_x = start_x + x
            if map_x >= session.map.width:
                continue
            dest_x = offset_x + x * tile_size
            dest_y = offset_y + y * tile_size
            rect = pygame.Rect(dest_x, dest_y, tile_size, tile_size)
            if not session.map.in_bounds(map_x, map_y):
                continue
            if not session._cell_walkable(map_x, map_y):
                overlay = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                overlay.fill((255, 0, 0, 80))
                screen.blit(overlay, rect.topleft)
            triggers = session.map.find_triggers_at(map_x, map_y, None)
            if triggers:
                pygame.draw.circle(screen, config.BLUE, rect.center, max(4, tile_size // 8))
            if session.map.portal_at(map_x, map_y):
                pygame.draw.circle(screen, config.GREEN, rect.center, max(4, tile_size // 6), 1)


def load_default_map() -> MapData:
    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.exists(target):
            return MapData.load(target)
        target_path = os.path.join(config.MAP_DIR, f"{target}.json")
        if os.path.exists(target_path):
            return MapData.load(target)
    default_path = os.path.join(config.MAP_DIR, "demo_tiles.json")
    if os.path.exists(default_path):
        return MapData.load(default_path)
    return MapData(
        map_id="blank",
        name="Blank",
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


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((config.OVERWORLD_WIDTH, config.OVERWORLD_HEIGHT))
    pygame.display.set_caption("Overworld")
    clock = pygame.time.Clock()

    map_data = load_default_map()
    tileset_path = os.path.join(config.TILESET_DIR, f"{map_data.tileset_id}.json")
    tileset = TileSet.load(tileset_path) if os.path.exists(tileset_path) else None
    tile_images = load_tileset_images(tileset, map_data.tile_size)
    npc_images = load_npc_images(tileset, map_data.tile_size)
    audio = OverworldAudio()
    session = OverworldSession(map_data, tileset=tileset, audio_controller=audio)

    font = pygame.font.Font(config.DEFAULT_FONT, config.OVERWORLD_FONT_SIZE)
    font_small = pygame.font.Font(config.DEFAULT_FONT, 14)
    debug_overlay = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    session.move("up")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    session.move("down")
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    session.move("left")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    session.move("right")
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    session.interact()
                elif event.key == pygame.K_r:
                    # Hot reload current map from disk
                    map_data = MapData.load(map_data.id)
                    tileset_path = os.path.join(config.TILESET_DIR, f"{map_data.tileset_id}.json")
                    tileset = TileSet.load(tileset_path) if os.path.exists(tileset_path) else None
                    tile_images = load_tileset_images(tileset, map_data.tile_size)
                    npc_images = load_npc_images(tileset, map_data.tile_size)
                    session.set_map(map_data, tileset=tileset)
                elif event.key == pygame.K_F1:
                    debug_overlay = not debug_overlay

        draw_world(screen, session, tile_images, npc_images, font_small, debug=debug_overlay)
        hud = font_small.render(f"Map: {session.map.id}  Facing: {session.player.facing}", True, config.BLACK)
        screen.blit(hud, (8, 8))
        if session.active_message:
            draw_message(screen, font, session.active_message)

        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
