import json
import os

import pygame

from src.core import config
from src.core.tileset import TileSet
from src.overworld.state import OverworldMap, OverworldState, Player, TileBehavior

TILE_BEHAVIORS = {
    "#": TileBehavior(walkable=False),
    ".": TileBehavior(walkable=True),
    "S": TileBehavior(walkable=False, interaction="A sign reads: Welcome to the overworld."),
    "N": TileBehavior(walkable=False, interaction="A traveler smiles and waves hello."),
    "W": TileBehavior(walkable=False, interaction="The water looks too deep to cross."),
}

TILE_COLORS = {
    "#": (70, 70, 70),
    ".": (120, 190, 120),
    "S": (200, 170, 120),
    "N": (180, 120, 180),
    "W": (70, 110, 190),
}

DEFAULT_MAP = [
    "####################",
    "#..............S...#",
    "#..######..........#",
    "#..#....#..W.......#",
    "#..#....#..........#",
    "#..######.....N....#",
    "#..................#",
    "#....######........#",
    "#....#....#........#",
    "#....#....#........#",
    "#....######........#",
    "#..................#",
    "#..S...............#",
    "#..................#",
    "####################",
]

MESSAGE_PADDING = 10
MESSAGE_HEIGHT = 80


def build_default_state() -> OverworldState:
    map_path = os.path.join(config.MAP_DIR, "demo_tiles.json")
    if os.path.exists(map_path):
        try:
            return load_map_from_json(map_path)
        except Exception as e:
            print(f"Failed to load map '{map_path}', falling back to built-in default: {e}")
    overworld_map = OverworldMap(DEFAULT_MAP, TILE_BEHAVIORS)
    player = Player(x=2, y=2)
    return OverworldState(overworld_map, player)


def load_tileset_images(tileset: TileSet) -> dict:
    """Load tile images (all frames) from disk and scale them to the tileset size."""
    images = {}
    for tile in tileset.tiles:
        frames = []
        total_frames = len(tile.frames) if tile.frames else 1
        for idx in range(total_frames):
            path = tileset.tile_image_path(tile, idx)
            try:
                surf = pygame.image.load(path).convert_alpha()
                if surf.get_size() != (tileset.tile_size, tileset.tile_size):
                    surf = pygame.transform.scale(surf, (tileset.tile_size, tileset.tile_size))
            except pygame.error:
                surf = pygame.Surface((tileset.tile_size, tileset.tile_size))
                surf.fill(config.GRAY_MEDIUM)
            frames.append(surf)
        images[tile.id] = {"frames": frames, "duration": tile.frame_duration_ms}
    return images


def load_map_from_json(path: str) -> OverworldState:
    """Load an overworld map that references a tileset by tile IDs."""
    with open(path, "r") as f:
        data = json.load(f)

    tileset_id = data.get("tilesetId") or config.DEFAULT_TILESET_ID
    tileset_path = os.path.join(config.TILESET_DIR, f"{tileset_id}.json")
    tileset = TileSet.load(tileset_path) if os.path.exists(tileset_path) else None

    tile_size = data.get("tileSize") or (tileset.tile_size if tileset else config.OVERWORLD_TILE_SIZE)
    layers = data.get("layers", [])
    ground_layer = next((layer for layer in layers if layer.get("name") == "ground"), layers[0] if layers else None)
    if not ground_layer:
        raise ValueError("Map JSON must include at least one layer.")
    rows = ground_layer.get("tiles", [])
    behaviors_data = data.get("behaviors", {})

    if tileset:
        for tile in tileset.tiles:
            props = tile.properties or {}
            entry = behaviors_data.setdefault(tile.id, {})
            if "walkable" not in entry and "walkable" in props:
                entry["walkable"] = props.get("walkable", True)
            if "interaction" not in entry and props.get("interaction"):
                entry["interaction"] = props.get("interaction")

    behaviors = {
        tile_id: TileBehavior(walkable=bool(raw.get("walkable", True)), interaction=raw.get("interaction"))
        for tile_id, raw in behaviors_data.items()
    }

    tile_images = load_tileset_images(tileset) if tileset else {}
    overworld_map = OverworldMap(rows, behaviors, tile_size=tile_size, tile_set_id=tileset_id, tile_images=tile_images)

    spawn = data.get("spawn", {"x": 2, "y": 2})
    player = Player(x=spawn.get("x", 2), y=spawn.get("y", 2))
    return OverworldState(overworld_map, player)


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
    box_width = screen.get_width() - (MESSAGE_PADDING * 2)
    box_rect = pygame.Rect(
        MESSAGE_PADDING,
        screen.get_height() - MESSAGE_HEIGHT - MESSAGE_PADDING,
        box_width,
        MESSAGE_HEIGHT,
    )
    overlay = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, box_rect.topleft)

    text_area_width = box_rect.width - (MESSAGE_PADDING * 2)
    lines = wrap_text(message, font, text_area_width)
    max_lines = max(1, box_rect.height // font.get_linesize())
    for i, line in enumerate(lines[:max_lines]):
        text_surf = font.render(line, True, config.WHITE)
        screen.blit(
            text_surf,
            (box_rect.x + MESSAGE_PADDING, box_rect.y + MESSAGE_PADDING + i * font.get_linesize()),
        )


def draw_world(screen: pygame.Surface, state: OverworldState, tile_size: int) -> None:
    tile_size = getattr(state.map, "tile_size", tile_size)
    screen.fill(config.OVERWORLD_BG_COLOR)
    for y, row in enumerate(state.map.tiles):
        for x, tile in enumerate(row):
            rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
            tile_entry = getattr(state.map, "tile_images", {}).get(tile)
            if isinstance(tile_entry, dict) and tile_entry.get("frames"):
                frames = tile_entry["frames"]
                duration = max(1, tile_entry.get("duration", 200))
                frame_idx = (pygame.time.get_ticks() // duration) % len(frames)
                screen.blit(frames[frame_idx], rect)
            elif tile_entry:
                screen.blit(tile_entry, rect)
            else:
                color = TILE_COLORS.get(tile, config.GRAY_MEDIUM)
                pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, config.BLACK, rect, 1)

    player_rect = pygame.Rect(
        state.player.x * tile_size,
        state.player.y * tile_size,
        tile_size,
        tile_size,
    )
    pygame.draw.rect(screen, config.RED, player_rect)
    pygame.draw.rect(screen, config.BLACK, player_rect, 2)


def main() -> None:
    pygame.init()
    state = build_default_state()
    tile_size = getattr(state.map, "tile_size", config.OVERWORLD_TILE_SIZE)
    screen = pygame.display.set_mode((state.map.width * tile_size, state.map.height * tile_size))
    pygame.display.set_caption("Overworld")
    clock = pygame.time.Clock()
    font = pygame.font.Font(config.DEFAULT_FONT, config.OVERWORLD_FONT_SIZE)
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_UP, pygame.K_w):
                    state.move("up")
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    state.move("down")
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    state.move("left")
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    state.move("right")
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    state.interact()

        draw_world(screen, state, tile_size)
        if state.message:
            draw_message(screen, font, state.message)

        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
