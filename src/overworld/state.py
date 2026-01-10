from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from src.core import config

DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}


@dataclass(frozen=True)
class TileBehavior:
    walkable: bool
    interaction: Optional[str] = None


class OverworldMap:
    def __init__(
        self,
        rows: Iterable[str],
        behaviors: Dict[str, TileBehavior],
        tile_size: int = config.OVERWORLD_TILE_SIZE,
        tile_set_id: Optional[str] = None,
        tile_images: Optional[Dict[str, object]] = None,
    ) -> None:
        self.tiles = [list(row) for row in rows]
        if not self.tiles:
            raise ValueError("Overworld map must have at least one row.")
        width = len(self.tiles[0])
        if any(len(row) != width for row in self.tiles):
            raise ValueError("All overworld map rows must be the same width.")
        self.width = width
        self.height = len(self.tiles)
        self.behaviors = behaviors
        self.tile_size = tile_size
        self.tile_set_id = tile_set_id
        # tile_images is a mapping of tile_id -> pygame.Surface, but keep typing loose to avoid pygame import here
        self.tile_images = tile_images or {}

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile_at(self, x: int, y: int) -> Optional[str]:
        if not self.in_bounds(x, y):
            return None
        return self.tiles[y][x]

    def tile_behavior(self, x: int, y: int) -> Optional[TileBehavior]:
        tile = self.tile_at(x, y)
        if tile is None:
            return None
        return self.behaviors.get(tile)

    def is_walkable(self, x: int, y: int) -> bool:
        behavior = self.tile_behavior(x, y)
        return bool(behavior and behavior.walkable)

    def interaction_at(self, x: int, y: int) -> Optional[str]:
        behavior = self.tile_behavior(x, y)
        if not behavior:
            return None
        return behavior.interaction


@dataclass
class Player:
    x: int
    y: int
    facing: str = "down"


class OverworldState:
    def __init__(self, overworld_map: OverworldMap, player: Player) -> None:
        self.map = overworld_map
        self.player = player
        self.message: Optional[str] = None

    def move(self, direction: str) -> bool:
        if direction not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        dx, dy = DIRECTIONS[direction]
        self.player.facing = direction
        new_x = self.player.x + dx
        new_y = self.player.y + dy
        if self.map.is_walkable(new_x, new_y):
            self.player.x = new_x
            self.player.y = new_y
            self.message = None
            return True
        return False

    def interact(self) -> Optional[str]:
        dx, dy = DIRECTIONS[self.player.facing]
        target_x = self.player.x + dx
        target_y = self.player.y + dy
        self.message = self.map.interaction_at(target_x, target_y)
        return self.message
