import json
import os
import struct
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.core import config


@dataclass
class TileDefinition:
    """Metadata for a single tile in a tileset."""
    id: str
    name: str
    filename: str
    frames: List[str] = field(default_factory=list)
    frame_duration_ms: int = 200
    properties: Dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "TileDefinition":
        filename = data.get("filename", f"{data.get('id', 'tile')}.png")
        frames = data.get("frames") or []
        if not frames:
            frames = [filename]
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "") or data.get("id", ""),
            filename=filename,
            frames=frames,
            frame_duration_ms=data.get("frameDurationMs", 200),
            properties=data.get("properties", {}) or {},
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "filename": self.filename,
            "frames": self.frames,
            "frameDurationMs": self.frame_duration_ms,
            "properties": self.properties,
        }


@dataclass
class NPCSprite:
    """NPC sprite set with multiple states and angles."""
    id: str
    name: str
    frame_duration_ms: int = 200
    # states[state][angle] = [frame filenames]
    states: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "NPCSprite":
        states = data.get("states", {}) or {}
        # Normalize legacy angle keys to canonical names used by the editor.
        angle_map = {"down": "south", "up": "north", "left": "west", "right": "east"}
        normalized_states: Dict[str, Dict[str, List[str]]] = {}
        for state, angles in states.items():
            normalized_states[state] = {}
            for angle, frames in (angles or {}).items():
                normalized_angle = angle_map.get(angle, angle)
                normalized_states[state].setdefault(normalized_angle, [])
                normalized_states[state][normalized_angle].extend(frames or [])
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "") or data.get("id", ""),
            frame_duration_ms=data.get("frameDurationMs", 200),
            states=normalized_states,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "frameDurationMs": self.frame_duration_ms,
            "states": self.states,
        }


def _write_solid_color_png(path: str, size: int, rgba: List[int]) -> None:
    """Write a minimal RGBA PNG using only the standard library."""
    width = height = size
    r, g, b, a = rgba
    # Each row starts with filter byte 0
    row = bytes([0] + [r, g, b, a] * width)
    raw_data = row * height

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack("!I", len(data))
            + tag
            + data
            + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(
        b"IHDR",
        struct.pack("!IIBBBBB", width, height, 8, 6, 0, 0, 0),
    )
    idat = _chunk(b"IDAT", zlib.compress(raw_data))
    iend = _chunk(b"IEND", b"")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(header + ihdr + idat + iend)


class TileSet:
    """Represents a collection of tiles plus metadata and persistence helpers."""

    def __init__(self, tileset_id: str, name: str, tile_size: int = None, version: str = "1.0.0"):
        self.id = tileset_id
        self.name = name
        self.tile_size = tile_size or config.OVERWORLD_TILE_SIZE
        self.version = version
        self.tiles: List[TileDefinition] = []
        self.npcs: List[NPCSprite] = []

    @property
    def image_dir(self) -> str:
        return os.path.join(config.TILE_IMAGE_DIR, self.id)

    @property
    def npc_image_dir(self) -> str:
        return os.path.join(self.image_dir, "npcs")

    def get_tile(self, tile_id: str) -> Optional[TileDefinition]:
        for tile in self.tiles:
            if tile.id == tile_id:
                return tile
        return None

    def add_or_update_tile(self, tile: TileDefinition) -> None:
        existing = self.get_tile(tile.id)
        if existing:
            existing.name = tile.name
            existing.filename = tile.filename
            existing.frames = tile.frames or [tile.filename]
            existing.frame_duration_ms = tile.frame_duration_ms
            existing.properties = tile.properties
        else:
            self.tiles.append(tile)

    def add_or_update_npc(self, npc: NPCSprite) -> None:
        for existing in self.npcs:
            if existing.id == npc.id:
                existing.name = npc.name
                existing.frame_duration_ms = npc.frame_duration_ms
                existing.states = npc.states
                return
        self.npcs.append(npc)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "tileSize": self.tile_size,
            "tiles": [t.to_dict() for t in self.tiles],
            "npcs": [n.to_dict() for n in self.npcs],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "TileSet":
        tileset = cls(
            tileset_id=data.get("id", "tileset"),
            name=data.get("name", "Tileset"),
            tile_size=data.get("tileSize") or config.OVERWORLD_TILE_SIZE,
            version=data.get("version", "1.0.0"),
        )
        for tile_data in data.get("tiles", []):
            tileset.tiles.append(TileDefinition.from_dict(tile_data))
        for npc_data in data.get("npcs", []):
            tileset.npcs.append(NPCSprite.from_dict(npc_data))
        return tileset

    @classmethod
    def load(cls, path: str) -> "TileSet":
        with open(path, "r") as f:
            data = json.load(f)
        tileset = cls.from_dict(data)
        tileset.ensure_assets()
        return tileset

    def save(self, path: Optional[str] = None) -> str:
        target_path = path or os.path.join(config.TILESET_DIR, f"{self.id}.json")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return target_path

    def tile_image_path(self, tile: TileDefinition, frame_index: int = 0) -> str:
        if not tile.frames:
            tile.frames = [tile.filename]
        frame_index = max(0, min(frame_index, len(tile.frames) - 1))
        filename = tile.frames[frame_index]
        return os.path.join(self.image_dir, filename)

    def npc_image_path(self, npc: NPCSprite, state: str, angle: str, frame_index: int = 0) -> str:
        frames = npc.states.get(state, {}).get(angle, [])
        if not frames:
            frames = [f"{npc.id}_{state}_{angle}.png"]
            npc.states.setdefault(state, {})[angle] = frames
        frame_index = max(0, min(frame_index, len(frames) - 1))
        filename = frames[frame_index]
        return os.path.join(self.npc_image_dir, npc.id, filename)

    def ensure_assets(self) -> None:
        """Ensure image directory exists and missing tiles get placeholders."""
        os.makedirs(self.image_dir, exist_ok=True)
        for idx, tile in enumerate(self.tiles):
            if not tile.frames:
                tile.frames = [tile.filename]
            for frame_name in tile.frames:
                img_path = os.path.join(self.image_dir, frame_name)
                if not os.path.exists(img_path):
                    color = tile.properties.get("color")
                    if not color or len(color) != 4:
                        # Derive a deterministic color from the tile id and frame
                        seed = hash(f"{tile.id}:{frame_name}") & 0xFFFFFF
                        color = [
                            (seed >> 16) & 0xFF,
                            (seed >> 8) & 0xFF,
                            seed & 0xFF,
                            255,
                        ]
                    _write_solid_color_png(img_path, self.tile_size, color)

        for npc in self.npcs:
            for state, angles in npc.states.items():
                for angle, frames in angles.items():
                    if not frames:
                        frames[:] = [f"{npc.id}_{state}_{angle}.png"]
                    for frame_name in frames:
                        npc_dir = os.path.join(self.npc_image_dir, npc.id)
                        os.makedirs(npc_dir, exist_ok=True)
                        img_path = os.path.join(npc_dir, frame_name)
                        if not os.path.exists(img_path):
                            seed = hash(f"{npc.id}:{state}:{angle}:{frame_name}") & 0xFFFFFF
                            color = [
                                (seed >> 16) & 0xFF,
                                (seed >> 8) & 0xFF,
                                seed & 0xFF,
                                255,
                            ]
                            _write_solid_color_png(img_path, self.tile_size, color)


def list_tileset_files() -> List[str]:
    """Return a sorted list of available tileset JSON files."""
    if not os.path.isdir(config.TILESET_DIR):
        return []
    return sorted(
        [
            os.path.join(config.TILESET_DIR, name)
            for name in os.listdir(config.TILESET_DIR)
            if name.lower().endswith(".json")
        ]
    )
