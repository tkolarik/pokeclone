import copy
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple

from src.core import config
from src.core.tileset import TileSet

DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}

OPPOSITE_FACING = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
}
EDGE_NORMALIZE = {"north": "up", "south": "down", "east": "right", "west": "left"}


@dataclass
class TileBehavior:
    walkable: bool = True
    interaction: Optional[str] = None


@dataclass
class MapLayer:
    name: str
    tiles: List[List[Optional[str]]]


@dataclass
class CellOverride:
    walkable: Optional[bool] = None
    flags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Connection:
    id: str
    type: str
    from_ref: Any
    to: Dict[str, Any]
    condition: Optional[Dict[str, Any]] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityDef:
    id: str
    type: str
    name: str
    sprite_id: str
    position: Dict[str, int]
    facing: str = "down"
    collision: bool = True
    dialog: Optional[Any] = None
    dialog_id: Optional[str] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    hidden: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerDef:
    id: str
    type: str
    position: Dict[str, Any]
    actions: List[Dict[str, Any]] = field(default_factory=list)
    repeatable: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Player:
    x: int
    y: int
    facing: str = "down"


def _copy_tiles(tiles: Iterable[Iterable[Optional[str]]]) -> List[List[Optional[str]]]:
    return [list(row) for row in tiles]


class MapData:
    """Container for map data and helper methods shared by runtime and editor."""

    def __init__(
        self,
        map_id: str,
        name: str,
        version: str,
        tile_size: int,
        dimensions: Tuple[int, int],
        tileset_id: str,
        layers: List[MapLayer],
        connections: List[Connection],
        entities: List[EntityDef],
        triggers: List[TriggerDef],
        overrides: Dict[Tuple[int, int], CellOverride],
        music_id: Optional[str] = None,
        spawn: Optional[Dict[str, int]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = map_id
        self.name = name or map_id
        self.version = version or "1.0.0"
        self.tile_size = tile_size or config.OVERWORLD_TILE_SIZE
        self.width, self.height = dimensions
        self.tileset_id = tileset_id or config.DEFAULT_TILESET_ID
        self.layers = layers
        self.connections = connections
        self.entities = entities
        self.triggers = triggers
        self.overrides = overrides
        self.music_id = music_id
        self.spawn = spawn
        self.extra = extra or {}
        self._normalize_layers()

    # Construction helpers -------------------------------------------------
    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "MapData":
        known_keys = {
            "id",
            "name",
            "version",
            "tileSize",
            "dimensions",
            "tilesetId",
            "layers",
            "connections",
            "entities",
            "triggers",
            "overrides",
            "musicId",
            "spawn",
        }
        extra = {k: v for k, v in raw.items() if k not in known_keys}
        dimensions_raw = raw.get("dimensions") or {}
        layers_raw = raw.get("layers", [])
        inferred_width, inferred_height = cls._infer_dimensions(layers_raw)
        width = dimensions_raw.get("width", inferred_width or config.OVERWORLD_GRID_WIDTH)
        height = dimensions_raw.get("height", inferred_height or config.OVERWORLD_GRID_HEIGHT)

        layers: List[MapLayer] = []
        for layer in layers_raw:
            layers.append(
                MapLayer(
                    name=layer.get("name", "layer"),
                    tiles=_copy_tiles(layer.get("tiles", [])),
                )
            )

        if not any(layer.name == "overlay" for layer in layers):
            overlay_tiles = [[None for _ in range(width)] for _ in range(height)]
            layers.append(MapLayer(name="overlay", tiles=overlay_tiles))

        connections: List[Connection] = []
        for connection in raw.get("connections", []) or []:
            conn_extra = {k: v for k, v in connection.items() if k not in {"id", "type", "from", "to", "condition"}}
            connections.append(
                Connection(
                    id=connection.get("id", ""),
                    type=connection.get("type", "edge"),
                    from_ref=connection.get("from"),
                    to=connection.get("to") or {},
                    condition=connection.get("condition"),
                    extra=conn_extra,
                )
            )

        entities: List[EntityDef] = []
        for entity in raw.get("entities", []) or []:
            entity_extra = {
                k: v
                for k, v in entity.items()
                if k
                not in {
                    "id",
                    "type",
                    "name",
                    "spriteId",
                    "position",
                    "facing",
                    "collision",
                    "dialog",
                    "dialogId",
                    "actions",
                    "conditions",
                    "properties",
                    "hidden",
                }
            }
            entities.append(
                EntityDef(
                    id=entity.get("id", ""),
                    type=entity.get("type", "npc"),
                    name=entity.get("name", ""),
                    sprite_id=entity.get("spriteId", ""),
                    position=entity.get("position") or {"x": 0, "y": 0},
                    facing=entity.get("facing", "down"),
                    collision=bool(entity.get("collision", True)),
                    dialog=entity.get("dialog"),
                    dialog_id=entity.get("dialogId"),
                    actions=entity.get("actions", []) or [],
                    conditions=entity.get("conditions", {}) or {},
                    properties=entity.get("properties", {}) or {},
                    hidden=bool(entity.get("hidden", False)),
                    extra=entity_extra,
                )
            )

        triggers: List[TriggerDef] = []
        for trigger in raw.get("triggers", []) or []:
            trigger_extra = {k: v for k, v in trigger.items() if k not in {"id", "type", "position", "actions", "repeatable", "conditions"}}
            triggers.append(
                TriggerDef(
                    id=trigger.get("id", ""),
                    type=trigger.get("type", "onEnter"),
                    position=trigger.get("position") or {},
                    actions=trigger.get("actions", []) or [],
                    repeatable=bool(trigger.get("repeatable", True)),
                    conditions=trigger.get("conditions", {}) or {},
                    extra=trigger_extra,
                )
            )

        overrides: Dict[Tuple[int, int], CellOverride] = {}
        for key, value in (raw.get("overrides") or {}).items():
            try:
                x_str, y_str = key.split(",")
                coord = (int(x_str), int(y_str))
            except Exception:
                continue
            ov_extra = {k: v for k, v in value.items() if k not in {"walkable", "flags"}}
            overrides[coord] = CellOverride(
                walkable=value.get("walkable"),
                flags=list(value.get("flags", []) or []),
                extra=ov_extra,
            )

        return cls(
            map_id=raw.get("id", "map"),
            name=raw.get("name", raw.get("id", "map")),
            version=raw.get("version", "1.0.0"),
            tile_size=raw.get("tileSize") or config.OVERWORLD_TILE_SIZE,
            dimensions=(width, height),
            tileset_id=raw.get("tilesetId") or config.DEFAULT_TILESET_ID,
            layers=layers,
            connections=connections,
            entities=entities,
            triggers=triggers,
            overrides=overrides,
            music_id=raw.get("musicId"),
            spawn=raw.get("spawn"),
            extra=extra,
        )

    @classmethod
    def load(cls, path_or_id: str) -> "MapData":
        if os.path.isfile(path_or_id):
            path = path_or_id
        else:
            path = os.path.join(config.MAP_DIR, f"{path_or_id}.json")
        with open(path, "r") as f:
            raw = json.load(f)
        return cls.from_dict(raw)

    def to_dict(self) -> Dict[str, Any]:
        raw = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "tileSize": self.tile_size,
            "dimensions": {"width": self.width, "height": self.height},
            "tilesetId": self.tileset_id,
            "layers": [{"name": layer.name, "tiles": _copy_tiles(layer.tiles)} for layer in self.layers],
            "connections": [
                {
                    **{"id": conn.id, "type": conn.type, "from": conn.from_ref, "to": conn.to},
                    **({"condition": conn.condition} if conn.condition is not None else {}),
                    **conn.extra,
                }
                for conn in self.connections
            ],
            "entities": [
                {
                    **{
                        "id": entity.id,
                        "type": entity.type,
                        "name": entity.name,
                        "spriteId": entity.sprite_id,
                        "position": entity.position,
                        "facing": entity.facing,
                        "collision": entity.collision,
                        "dialog": entity.dialog,
                        "dialogId": entity.dialog_id,
                        "actions": entity.actions,
                        "conditions": entity.conditions,
                        "properties": entity.properties,
                        "hidden": entity.hidden,
                    },
                    **entity.extra,
                }
                for entity in self.entities
            ],
            "triggers": [
                {
                    **{
                        "id": trigger.id,
                        "type": trigger.type,
                        "position": trigger.position,
                        "actions": trigger.actions,
                        "repeatable": trigger.repeatable,
                        "conditions": trigger.conditions,
                    },
                    **trigger.extra,
                }
                for trigger in self.triggers
            ],
            "overrides": {
                f"{x},{y}": {
                    **({"walkable": ov.walkable} if ov.walkable is not None else {}),
                    **({"flags": ov.flags} if ov.flags else {}),
                    **ov.extra,
                }
                for (x, y), ov in self.overrides.items()
            },
        }
        if self.music_id is not None:
            raw["musicId"] = self.music_id
        if self.spawn is not None:
            raw["spawn"] = self.spawn
        raw.update(self.extra)
        return raw

    def save(self, path_or_id: Optional[str] = None) -> str:
        if path_or_id is None:
            path = os.path.join(config.MAP_DIR, f"{self.id}.json")
        elif os.path.isdir(path_or_id):
            path = os.path.join(path_or_id, f"{self.id}.json")
        else:
            path = path_or_id
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path

    # Helpers --------------------------------------------------------------
    @staticmethod
    def _infer_dimensions(layers_raw: List[Dict[str, Any]]) -> Tuple[int, int]:
        for layer in layers_raw:
            tiles = layer.get("tiles") or []
            if tiles:
                height = len(tiles)
                width = len(tiles[0]) if tiles[0] else 0
                return width, height
        return 0, 0

    def _normalize_layers(self) -> None:
        """Ensure all layers match map dimensions and fill empty rows/cols with None."""
        for layer in self.layers:
            # Expand rows to map height
            while len(layer.tiles) < self.height:
                layer.tiles.append([None for _ in range(self.width)])
            # Trim extra rows if present
            if len(layer.tiles) > self.height:
                layer.tiles = layer.tiles[: self.height]
            # Normalize each row width
            for y in range(self.height):
                row = layer.tiles[y]
                if len(row) < self.width:
                    row.extend([None] * (self.width - len(row)))
                elif len(row) > self.width:
                    layer.tiles[y] = row[: self.width]

    def clone(self) -> "MapData":
        return copy.deepcopy(self)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def layer(self, name: str) -> Optional[MapLayer]:
        for layer in self.layers:
            if layer.name == name:
                return layer
        return None

    def get_tile(self, layer_name: str, x: int, y: int) -> Optional[str]:
        layer = self.layer(layer_name)
        if not layer or not self.in_bounds(x, y):
            return None
        return layer.tiles[y][x]

    def set_tile(self, layer_name: str, x: int, y: int, value: Optional[str]) -> None:
        layer = self.layer(layer_name)
        if not layer or not self.in_bounds(x, y):
            return
        layer.tiles[y][x] = value

    def get_override(self, x: int, y: int) -> Optional[CellOverride]:
        return self.overrides.get((x, y))

    def set_override(self, x: int, y: int, override: CellOverride) -> None:
        self.overrides[(x, y)] = override

    def find_entities_at(self, x: int, y: int) -> List[EntityDef]:
        return [entity for entity in self.entities if entity.position.get("x") == x and entity.position.get("y") == y]

    def find_triggers_at(self, x: int, y: int, trigger_type: Optional[str] = None) -> List[TriggerDef]:
        matches: List[TriggerDef] = []
        for trigger in self.triggers:
            if trigger_type and trigger.type != trigger_type:
                continue
            position = trigger.position or {}
            if self._position_matches(position, x, y):
                matches.append(trigger)
        return matches

    def get_connection_by_id(self, connection_id: str) -> Optional[Connection]:
        for connection in self.connections:
            if connection.id == connection_id:
                return connection
        return None

    def connection_for_edge(self, direction: str) -> Optional[Connection]:
        for connection in self.connections:
            if connection.type != "edge":
                continue
            from_ref = connection.from_ref
            normalized = EDGE_NORMALIZE.get(from_ref, from_ref)
            if normalized == direction:
                return connection
        return None

    def portal_at(self, x: int, y: int) -> Optional[Connection]:
        for connection in self.connections:
            if connection.type != "portal":
                continue
            source = connection.from_ref or {}
            if isinstance(source, dict) and source.get("x") == x and source.get("y") == y:
                return connection
        return None

    def spawn_point(self) -> Tuple[int, int]:
        if self.spawn and "x" in self.spawn and "y" in self.spawn:
            return int(self.spawn["x"]), int(self.spawn["y"])
        for (x, y), override in self.overrides.items():
            if "spawn" in override.flags:
                return x, y
        return 0, 0

    @staticmethod
    def _position_matches(position: Dict[str, Any], x: int, y: int) -> bool:
        if not position:
            return False
        if "width" in position and "height" in position:
            px = position.get("x", 0)
            py = position.get("y", 0)
            return px <= x < px + position["width"] and py <= y < py + position["height"]
        return position.get("x") == x and position.get("y") == y

    def validate(self, tileset: Optional[TileSet] = None, known_maps: Optional[Set[str]] = None) -> Tuple[List[str], List[str]]:
        errors: List[str] = []
        warnings: List[str] = []

        if self.width <= 0 or self.height <= 0:
            errors.append("Map dimensions must be greater than zero.")

        for layer in self.layers:
            if len(layer.tiles) != self.height:
                errors.append(f"Layer '{layer.name}' height {len(layer.tiles)} does not match map height {self.height}.")
            for row in layer.tiles:
                if len(row) != self.width:
                    errors.append(f"Layer '{layer.name}' row width mismatch (expected {self.width}).")

        for (x, y) in self.overrides.keys():
            if not self.in_bounds(x, y):
                errors.append(f"Override at ({x},{y}) is out of bounds.")

        for entity in self.entities:
            pos = entity.position or {}
            ex, ey = pos.get("x"), pos.get("y")
            if ex is None or ey is None:
                errors.append(f"Entity '{entity.id}' missing position.")
            elif not self.in_bounds(ex, ey):
                errors.append(f"Entity '{entity.id}' at ({ex},{ey}) is out of bounds.")

        for trigger in self.triggers:
            pos = trigger.position or {}
            if "x" in pos and "y" in pos and not self.in_bounds(pos["x"], pos["y"]):
                errors.append(f"Trigger '{trigger.id}' at ({pos['x']},{pos['y']}) is out of bounds.")

        for connection in self.connections:
            if connection.type == "portal" and isinstance(connection.from_ref, dict):
                px, py = connection.from_ref.get("x"), connection.from_ref.get("y")
                if px is None or py is None:
                    errors.append(f"Connection '{connection.id}' portal missing coordinates.")
                elif not self.in_bounds(px, py):
                    errors.append(f"Connection '{connection.id}' portal at ({px},{py}) is out of bounds.")
            to_target = connection.to or {}
            spawn = to_target.get("spawn") or {}
            if "x" in spawn and "y" in spawn:
                sx, sy = spawn.get("x"), spawn.get("y")
                if sx is None or sy is None:
                    errors.append(f"Connection '{connection.id}' spawn missing coordinates.")
                elif sx < 0 or sy < 0:
                    errors.append(f"Connection '{connection.id}' spawn coordinates must be non-negative.")
            target_map_id = to_target.get("mapId")
            if known_maps is not None and target_map_id and target_map_id not in known_maps:
                warnings.append(f"Connection '{connection.id}' references unknown map '{target_map_id}'.")

        if tileset:
            valid_tile_ids = {tile.id for tile in tileset.tiles}
            for layer in self.layers:
                for y, row in enumerate(layer.tiles):
                    for x, tile_id in enumerate(row):
                        if tile_id is None:
                            continue
                        if tile_id not in valid_tile_ids:
                            errors.append(f"Unknown tile id '{tile_id}' at ({x},{y}) in layer '{layer.name}'.")

        return errors, warnings


class NullAudioController:
    """No-op audio controller usable in tests."""

    def play_music(self, music_id: Optional[str]) -> None:
        return

    def stop_music(self) -> None:
        return

    def play_sound(self, sound_id: Optional[str]) -> None:
        return


class OverworldSession:
    """Runtime controller for overworld logic (movement, triggers, connections)."""

    def __init__(
        self,
        map_data: MapData,
        tileset: Optional[TileSet] = None,
        audio_controller: Optional[object] = None,
        battle_launcher: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.map: MapData = map_data
        self.tileset: Optional[TileSet] = tileset
        self.tile_behaviors: Dict[str, TileBehavior] = self._build_tile_behaviors(tileset)
        spawn_x, spawn_y = self.map.spawn_point()
        self.player = Player(x=spawn_x, y=spawn_y)
        self.flags: Set[str] = set()
        self.consumed_triggers: Set[str] = set()
        self.message_queue: List[str] = []
        self.audio = audio_controller or NullAudioController()
        self.current_music_id: Optional[str] = None
        self.battle_launcher = battle_launcher
        self.pending_battle: Optional[Dict[str, Any]] = None
        self._ensure_music()

    # Map + tile handling --------------------------------------------------
    def _build_tile_behaviors(self, tileset: Optional[TileSet]) -> Dict[str, TileBehavior]:
        behaviors: Dict[str, TileBehavior] = {}
        if not tileset:
            return behaviors
        for tile in tileset.tiles:
            behavior = TileBehavior(
                walkable=bool(tile.properties.get("walkable", True)),
                interaction=tile.properties.get("interaction"),
            )
            behaviors[tile.id] = behavior
        return behaviors

    def set_tileset(self, tileset: TileSet) -> None:
        self.tileset = tileset
        self.tile_behaviors = self._build_tile_behaviors(tileset)

    def set_map(self, map_data: MapData, tileset: Optional[TileSet] = None, spawn_override: Optional[Dict[str, int]] = None, facing: Optional[str] = None) -> None:
        self.map = map_data
        if tileset:
            self.set_tileset(tileset)
        spawn_x, spawn_y = map_data.spawn_point()
        if spawn_override:
            spawn_x, spawn_y = spawn_override.get("x", spawn_x), spawn_override.get("y", spawn_y)
        self.player = Player(x=spawn_x, y=spawn_y, facing=facing or self.player.facing)
        self._ensure_music()

    def _ensure_music(self) -> None:
        if self.map.music_id != self.current_music_id:
            if self.map.music_id is not None:
                self.audio.play_music(self.map.music_id)
            else:
                self.audio.stop_music()
            self.current_music_id = self.map.music_id

    # Message handling -----------------------------------------------------
    def queue_message(self, text: Optional[Any]) -> None:
        if text is None:
            return
        if isinstance(text, list):
            for line in text:
                if line is not None:
                    self.message_queue.append(str(line))
        else:
            self.message_queue.append(str(text))

    @property
    def active_message(self) -> Optional[str]:
        return self.message_queue[0] if self.message_queue else None

    def acknowledge_message(self) -> None:
        if self.message_queue:
            self.message_queue.pop(0)
        if not self.message_queue and self.pending_battle:
            payload = self.pending_battle
            self.pending_battle = None
            self._launch_battle(payload)

    # Collision + helpers --------------------------------------------------
    def _cell_walkable(self, x: int, y: int) -> bool:
        if not self.map.in_bounds(x, y):
            return False
        walkable = True
        for layer in self.map.layers:
            tile_id = layer.tiles[y][x]
            if tile_id is None:
                continue
            behavior = self.tile_behaviors.get(tile_id, TileBehavior())
            if not behavior.walkable:
                walkable = False
                break
        override = self.map.get_override(x, y)
        if override and override.walkable is not None:
            walkable = bool(override.walkable)
        for entity in self.map.find_entities_at(x, y):
            if entity.collision and not entity.hidden:
                walkable = False
                break
        return walkable

    def _tile_interaction(self, x: int, y: int) -> Optional[str]:
        if not self.map.in_bounds(x, y):
            return None
        for layer in self.map.layers:
            tile_id = layer.tiles[y][x]
            if tile_id is None:
                continue
            behavior = self.tile_behaviors.get(tile_id)
            if behavior and behavior.interaction:
                return behavior.interaction
        return None

    # Movement + triggers --------------------------------------------------
    def move(self, direction: str) -> bool:
        if direction not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        if self.active_message:
            return False
        dx, dy = DIRECTIONS[direction]
        self.player.facing = direction
        new_x = self.player.x + dx
        new_y = self.player.y + dy

        # Edge connections
        if not self.map.in_bounds(new_x, new_y):
            connection = self.map.connection_for_edge(direction)
            if connection:
                self._execute_connection(connection, attempted_direction=direction)
                return True
            return False

        if not self._cell_walkable(new_x, new_y):
            return False

        self.player.x = new_x
        self.player.y = new_y

        portal = self.map.portal_at(new_x, new_y)
        if portal:
            self._execute_connection(portal, attempted_direction=direction)
            return True

        self._run_triggers_at(new_x, new_y, trigger_type="onEnter")
        return True

    def interact(self) -> Optional[str]:
        if self.active_message:
            self.acknowledge_message()
            return self.active_message

        dx, dy = DIRECTIONS[self.player.facing]
        target_x = self.player.x + dx
        target_y = self.player.y + dy

        entity_ran = False
        entities = self.map.find_entities_at(target_x, target_y)
        if entities:
            self._run_entity_interaction(entities[0])
            entity_ran = True

        self._run_triggers_at(target_x, target_y, trigger_type="onInteract")

        if not self.active_message and not entity_ran:
            interaction_text = self._tile_interaction(target_x, target_y)
            if interaction_text:
                self.queue_message(interaction_text)

        return self.active_message

    # Internal helpers -----------------------------------------------------
    def _conditions_met(self, conditions: Dict[str, Any]) -> bool:
        if not conditions:
            return True
        flags_all = conditions.get("flags") or conditions.get("flagsAll") or []
        flags_any = conditions.get("flagsAny") or []
        flags_not = conditions.get("notFlags") or []
        if flags_all and any(flag not in self.flags for flag in flags_all):
            return False
        if flags_any and not any(flag in self.flags for flag in flags_any):
            return False
        if flags_not and any(flag in self.flags for flag in flags_not):
            return False
        return True

    def _run_entity_interaction(self, entity: EntityDef) -> Optional[str]:
        if entity.hidden or not self._conditions_met(entity.conditions):
            return None
        actions = entity.actions or []
        if actions:
            self._run_actions(actions)
        elif entity.dialog is not None:
            self.queue_message(entity.dialog)
        elif entity.dialog_id:
            self.queue_message(f"[Dialog: {entity.dialog_id}]")
        team = None
        battle_enabled = True
        if entity.properties and isinstance(entity.properties, dict):
            team = entity.properties.get("team") or entity.properties.get("battleTeam")
            battle_enabled = entity.properties.get("battleable", True)
        has_battle_action = any((action.get("kind") or action.get("type")) == "startBattle" for action in actions)
        if team and battle_enabled and not has_battle_action:
            payload = {"team": team, "opponent_id": entity.id, "label": entity.name or entity.id}
            self._schedule_battle(payload)
        return self.active_message

    def _run_triggers_at(self, x: int, y: int, trigger_type: str) -> None:
        triggers = self.map.find_triggers_at(x, y, trigger_type)
        for trigger in triggers:
            if not trigger.repeatable and trigger.id in self.consumed_triggers:
                continue
            if not self._conditions_met(trigger.conditions):
                continue
            self._run_actions(trigger.actions)
            if not trigger.repeatable:
                self.consumed_triggers.add(trigger.id)

    def _run_actions(self, actions: List[Dict[str, Any]]) -> None:
        for action in actions or []:
            kind = action.get("kind") or action.get("type")
            if kind == "showText":
                self.queue_message(action.get("text"))
            elif kind == "setFlag":
                flag = action.get("flag")
                if flag:
                    self.flags.add(flag)
            elif kind == "clearFlag":
                flag = action.get("flag")
                if flag and flag in self.flags:
                    self.flags.remove(flag)
            elif kind == "playSound":
                self.audio.play_sound(action.get("soundId") or action.get("id"))
            elif kind == "playMusic":
                self.current_music_id = None
                self.map.music_id = action.get("musicId")
                self._ensure_music()
            elif kind == "stopMusic":
                self.audio.stop_music()
                self.current_music_id = None
            elif kind == "warp":
                target_map = action.get("mapId")
                spawn = action.get("spawn")
                facing = action.get("facing")
                if target_map:
                    self._load_and_set_map(target_map, spawn_override=spawn, facing=facing)
            elif kind == "runConnection":
                conn_id = action.get("connectionId")
                if conn_id:
                    connection = self.map.get_connection_by_id(conn_id)
                    if connection:
                        self._execute_connection(connection, attempted_direction=None, preserve_facing=action.get("preserveFacing", False))
            elif kind == "toggleEntity":
                entity_id = action.get("entityId") or action.get("id")
                if entity_id:
                    self._toggle_entity(entity_id, action)
            elif kind == "toggleTileOverride":
                position = action.get("position") or {}
                self._toggle_override(position, action)
            elif kind == "startBattle":
                team = action.get("team")
                opponent_id = action.get("opponentId") or action.get("entityId") or action.get("teamId") or action.get("battleId")
                if team is None and opponent_id:
                    for entity in self.map.entities:
                        if entity.id == opponent_id:
                            team = (entity.properties or {}).get("team") if entity.properties else None
                            break
                payload = {
                    "team": team,
                    "opponent_id": opponent_id,
                    "label": action.get("label") or opponent_id or "Encounter",
                }
                self._schedule_battle(payload)

    def _schedule_battle(self, payload: Dict[str, Any]) -> None:
        if self.active_message or self.message_queue:
            self.pending_battle = payload
        else:
            self._launch_battle(payload)

    def _launch_battle(self, payload: Dict[str, Any]) -> None:
        if self.battle_launcher:
            self.battle_launcher(payload)
        else:
            label = payload.get("label") or payload.get("opponent_id") or "Encounter"
            self.queue_message(f"Battle start: {label}")

    def _toggle_entity(self, entity_id: str, action: Dict[str, Any]) -> None:
        for entity in self.map.entities:
            if entity.id != entity_id:
                continue
            if "visible" in action:
                entity.hidden = not bool(action.get("visible", True))
            if "hidden" in action:
                entity.hidden = bool(action["hidden"])
            if "collision" in action:
                entity.collision = bool(action["collision"])
            break

    def _toggle_override(self, position: Dict[str, Any], action: Dict[str, Any]) -> None:
        if "x" not in position or "y" not in position:
            return
        x, y = position["x"], position["y"]
        override = self.map.get_override(x, y) or CellOverride()
        if "walkable" in action:
            override.walkable = action["walkable"]
        flags_to_add = action.get("addFlags") or []
        flags_to_remove = action.get("removeFlags") or []
        override.flags = list(set(override.flags + flags_to_add))
        override.flags = [f for f in override.flags if f not in flags_to_remove]
        self.map.set_override(x, y, override)

    def _execute_connection(self, connection: Connection, attempted_direction: Optional[str], preserve_facing: bool = False) -> None:
        target = connection.to or {}
        spawn = target.get("spawn")
        target_map_id = target.get("mapId")
        target_facing = target.get("facing")
        facing = self.player.facing if preserve_facing else target_facing or OPPOSITE_FACING.get(attempted_direction, self.player.facing)
        if target_map_id:
            self._load_and_set_map(target_map_id, spawn_override=spawn, facing=facing)

    def _load_and_set_map(self, map_id: str, spawn_override: Optional[Dict[str, int]], facing: Optional[str]) -> None:
        new_map = MapData.load(map_id)
        tileset_path = os.path.join(config.TILESET_DIR, f"{new_map.tileset_id}.json")
        tileset = TileSet.load(tileset_path) if os.path.exists(tileset_path) else None
        self.set_map(new_map, tileset=tileset, spawn_override=spawn_override, facing=facing)
        self._run_triggers_at(self.player.x, self.player.y, trigger_type="onEnter")
