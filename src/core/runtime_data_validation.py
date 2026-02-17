from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Sequence, Tuple

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from src.core import config
from src.core.monster_schema import normalize_monsters

MAX_STAT_VALUE = 9999
MAX_MOVE_POWER = 300
MAX_TYPE_MULTIPLIER = 4.0
MAX_MAP_DIMENSION = 512
OVERRIDE_COORD_RE = re.compile(r"^\d+,\d+$")


class RuntimeDataValidationError(ValueError):
    """Raised when runtime JSON payloads fail strict schema validation."""

    def __init__(self, source: str, errors: Sequence[Dict[str, Any]]) -> None:
        self.source = source
        self.errors = [self._normalize_error(error) for error in errors]
        super().__init__(self._build_message())

    @staticmethod
    def _normalize_error(error: Dict[str, Any]) -> Dict[str, Any]:
        loc = error.get("loc", ())
        if not isinstance(loc, tuple):
            if isinstance(loc, list):
                loc = tuple(loc)
            else:
                loc = (loc,)
        msg = str(error.get("msg", "Unknown validation error."))
        return {"loc": loc, "msg": msg}

    @staticmethod
    def _format_loc(loc: Tuple[Any, ...]) -> str:
        if not loc:
            return "<root>"
        parts = []
        for item in loc:
            if isinstance(item, int):
                parts.append(f"[{item}]")
            else:
                text = str(item)
                if not parts:
                    parts.append(text)
                else:
                    parts.append(f".{text}")
        return "".join(parts)

    def _build_message(self) -> str:
        lines = [f"{self.source} validation failed ({len(self.errors)} error(s))."]
        for error in self.errors:
            lines.append(f"- {self._format_loc(error['loc'])}: {error['msg']}")
        return "\n".join(lines)

    @classmethod
    def from_pydantic(cls, source: str, exc: ValidationError) -> "RuntimeDataValidationError":
        return cls(source=source, errors=exc.errors())


class _SchemaModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class _RawBaseStatsModel(_SchemaModel):
    max_hp: int = Field(ge=1, le=MAX_STAT_VALUE)
    attack: int = Field(ge=1, le=MAX_STAT_VALUE)
    defense: int = Field(ge=1, le=MAX_STAT_VALUE)


class _RawLearnsetEntryModel(_SchemaModel):
    level: int = Field(default=1, ge=config.MIN_MONSTER_LEVEL, le=config.MAX_MONSTER_LEVEL)
    move: str | None = None
    moves: list[str] | None = None

    @field_validator("move")
    @classmethod
    def _strip_move(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("move must be a non-empty string.")
        return stripped

    @field_validator("moves")
    @classmethod
    def _validate_moves(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        normalized: list[str] = []
        for index, move_name in enumerate(value):
            if not isinstance(move_name, str):
                raise ValueError(f"moves[{index}] must be a string.")
            stripped = move_name.strip()
            if not stripped:
                raise ValueError(f"moves[{index}] must be a non-empty string.")
            normalized.append(stripped)
        return normalized

    @model_validator(mode="after")
    def _require_move_or_moves(self) -> "_RawLearnsetEntryModel":
        if self.move is None and not self.moves:
            raise ValueError("learnset entry must include 'move' or 'moves'.")
        return self


class _RawMonsterModel(_SchemaModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    base_stats: _RawBaseStatsModel | None = None

    max_hp: int | None = Field(default=None, ge=1, le=MAX_STAT_VALUE)
    attack: int | None = Field(default=None, ge=1, le=MAX_STAT_VALUE)
    defense: int | None = Field(default=None, ge=1, le=MAX_STAT_VALUE)

    learnset: list[_RawLearnsetEntryModel] | None = None
    move_pool: list[str] | None = None
    moves: list[str] | None = None

    @field_validator("name", "type")
    @classmethod
    def _strip_required_str(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must be a non-empty string.")
        return stripped

    @field_validator("move_pool", "moves")
    @classmethod
    def _validate_legacy_move_lists(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        normalized: list[str] = []
        for index, move_name in enumerate(value):
            if not isinstance(move_name, str):
                raise ValueError(f"[{index}] must be a string.")
            stripped = move_name.strip()
            if not stripped:
                raise ValueError(f"[{index}] must be a non-empty string.")
            normalized.append(stripped)
        return normalized

    @model_validator(mode="after")
    def _require_stats(self) -> "_RawMonsterModel":
        if self.base_stats is None:
            if self.max_hp is None or self.attack is None or self.defense is None:
                raise ValueError(
                    "Monster must provide 'base_stats' or legacy 'max_hp'/'attack'/'defense' fields."
                )
        return self


class _RawMonsterListModel(RootModel[list[_RawMonsterModel]]):
    pass


class _CanonicalLearnsetEntryModel(_SchemaModel):
    level: int = Field(ge=config.MIN_MONSTER_LEVEL, le=config.MAX_MONSTER_LEVEL)
    move: str = Field(min_length=1)

    @field_validator("move")
    @classmethod
    def _strip_move(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("move must be a non-empty string.")
        return stripped


class _CanonicalMonsterModel(_SchemaModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    base_stats: _RawBaseStatsModel
    learnset: list[_CanonicalLearnsetEntryModel] = Field(default_factory=list)

    @field_validator("name", "type")
    @classmethod
    def _strip_required_str(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must be a non-empty string.")
        return stripped


class _CanonicalMonsterListModel(RootModel[list[_CanonicalMonsterModel]]):
    pass


class _MoveEffectModel(_SchemaModel):
    target: str = Field(min_length=1)
    stat: str = Field(min_length=1)
    change: int

    @field_validator("target", "stat")
    @classmethod
    def _strip_required_str(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must be a non-empty string.")
        return stripped


class _MoveModel(_SchemaModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    power: int = Field(ge=0, le=MAX_MOVE_POWER)
    effect: _MoveEffectModel | None = None

    @field_validator("name", "type")
    @classmethod
    def _strip_required_str(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must be a non-empty string.")
        return stripped


class _MoveListModel(RootModel[list[_MoveModel]]):
    pass


class _TypeChartModel(RootModel[dict[str, dict[str, float]]]):
    @field_validator("root")
    @classmethod
    def _validate_chart(cls, value: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        for attacker_type, row in value.items():
            if not attacker_type.strip():
                raise ValueError("Type chart keys must be non-empty strings.")
            for defender_type, multiplier in row.items():
                if not defender_type.strip():
                    raise ValueError(
                        f"Type chart row '{attacker_type}' contains an empty defender type key."
                    )
                if multiplier < 0 or multiplier > MAX_TYPE_MULTIPLIER:
                    raise ValueError(
                        f"Type chart value for {attacker_type}->{defender_type} "
                        f"must be between 0 and {MAX_TYPE_MULTIPLIER}."
                    )
        return value


class _MapDimensionsModel(_SchemaModel):
    width: int = Field(ge=1, le=MAX_MAP_DIMENSION)
    height: int = Field(ge=1, le=MAX_MAP_DIMENSION)


class _MapCoordModel(_SchemaModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class _MapLayerModel(_SchemaModel):
    name: str = Field(min_length=1)
    tiles: list[list[str | None]]

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Layer name must be a non-empty string.")
        return stripped


class _MapConnectionTargetModel(_SchemaModel):
    mapId: str = Field(min_length=1)
    spawn: _MapCoordModel | None = None
    facing: str | None = None

    @field_validator("mapId")
    @classmethod
    def _strip_map_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Connection target mapId must be non-empty.")
        return stripped


class _MapConnectionModel(_SchemaModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    from_ref: Any = Field(alias="from")
    to: _MapConnectionTargetModel
    condition: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @field_validator("id", "type")
    @classmethod
    def _strip_required_str(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must be a non-empty string.")
        return stripped


class _MapEntityModel(_SchemaModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    name: str = ""
    spriteId: str = ""
    position: _MapCoordModel
    facing: str = "down"
    collision: bool = True
    dialog: Any = None
    dialogId: str | None = None
    actions: list[dict[str, Any]] = Field(default_factory=list)
    conditions: dict[str, Any] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    hidden: bool = False

    @field_validator("id", "type")
    @classmethod
    def _strip_required_str(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must be a non-empty string.")
        return stripped


class _MapTriggerModel(_SchemaModel):
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    position: dict[str, Any]
    actions: list[dict[str, Any]] = Field(default_factory=list)
    repeatable: bool = True
    conditions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id", "type")
    @classmethod
    def _strip_required_str(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must be a non-empty string.")
        return stripped

    @field_validator("position")
    @classmethod
    def _validate_position(cls, value: dict[str, Any]) -> dict[str, Any]:
        if "x" in value:
            x = value["x"]
            if not isinstance(x, int) or x < 0:
                raise ValueError("position.x must be a non-negative integer.")
        if "y" in value:
            y = value["y"]
            if not isinstance(y, int) or y < 0:
                raise ValueError("position.y must be a non-negative integer.")
        return value


class _MapOverrideModel(_SchemaModel):
    walkable: bool | None = None
    flags: list[str] = Field(default_factory=list)

    @field_validator("flags")
    @classmethod
    def _validate_flags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for index, flag in enumerate(value):
            if not isinstance(flag, str):
                raise ValueError(f"flags[{index}] must be a string.")
            stripped = flag.strip()
            if not stripped:
                raise ValueError(f"flags[{index}] must be a non-empty string.")
            normalized.append(stripped)
        return normalized


class _MapPayloadModel(_SchemaModel):
    id: str = Field(min_length=1)
    name: str | None = None
    version: str = "1.0.0"
    tileSize: int = Field(ge=1)
    dimensions: _MapDimensionsModel
    tilesetId: str = Field(min_length=1)
    layers: list[_MapLayerModel]
    connections: list[_MapConnectionModel] = Field(default_factory=list)
    entities: list[_MapEntityModel] = Field(default_factory=list)
    triggers: list[_MapTriggerModel] = Field(default_factory=list)
    overrides: dict[str, _MapOverrideModel] = Field(default_factory=dict)
    musicId: str | None = None
    spawn: _MapCoordModel | None = None

    @field_validator("id", "version", "tilesetId")
    @classmethod
    def _strip_required_str(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value must be a non-empty string.")
        return stripped

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        return stripped or None

    @field_validator("layers")
    @classmethod
    def _validate_layers_shape(
        cls, layers: list[_MapLayerModel], info: ValidationInfo
    ) -> list[_MapLayerModel]:
        dimensions: _MapDimensionsModel | None = info.data.get("dimensions")
        if dimensions is None:
            return layers
        expected_width = dimensions.width
        expected_height = dimensions.height
        if len(layers) == 0:
            raise ValueError("At least one map layer is required.")
        for layer_index, layer in enumerate(layers):
            row_count = len(layer.tiles)
            if row_count != expected_height:
                raise ValueError(
                    f"layers[{layer_index}].tiles must contain {expected_height} rows "
                    f"(got {row_count})."
                )
            for row_index, row in enumerate(layer.tiles):
                if len(row) != expected_width:
                    raise ValueError(
                        f"layers[{layer_index}].tiles[{row_index}] must contain "
                        f"{expected_width} columns (got {len(row)})."
                    )
        return layers

    @field_validator("overrides")
    @classmethod
    def _validate_override_keys(
        cls, overrides: dict[str, _MapOverrideModel], info: ValidationInfo
    ) -> dict[str, _MapOverrideModel]:
        dimensions: _MapDimensionsModel | None = info.data.get("dimensions")
        for key in overrides.keys():
            if not OVERRIDE_COORD_RE.match(key):
                raise ValueError(
                    f"Invalid override key '{key}'. Expected coordinate format 'x,y'."
                )
            if dimensions is not None:
                x_str, y_str = key.split(",")
                x = int(x_str)
                y = int(y_str)
                if x >= dimensions.width or y >= dimensions.height:
                    raise ValueError(
                        f"Override coordinate '{key}' is outside map bounds "
                        f"{dimensions.width}x{dimensions.height}."
                    )
        return overrides

    @model_validator(mode="after")
    def _validate_bounds(self) -> "_MapPayloadModel":
        width = self.dimensions.width
        height = self.dimensions.height

        if self.spawn is not None and (
            self.spawn.x >= width or self.spawn.y >= height
        ):
            raise ValueError(
                "spawn must be within map bounds "
                f"(width={width}, height={height})."
            )

        for index, entity in enumerate(self.entities):
            if entity.position.x >= width or entity.position.y >= height:
                raise ValueError(
                    f"entities[{index}].position is outside map bounds "
                    f"(width={width}, height={height})."
                )

        for index, trigger in enumerate(self.triggers):
            x = trigger.position.get("x")
            y = trigger.position.get("y")
            if isinstance(x, int) and isinstance(y, int):
                if x >= width or y >= height:
                    raise ValueError(
                        f"triggers[{index}].position is outside map bounds "
                        f"(width={width}, height={height})."
                    )

        for index, connection in enumerate(self.connections):
            source = connection.from_ref
            if isinstance(source, dict) and "x" in source and "y" in source:
                x = source.get("x")
                y = source.get("y")
                if not isinstance(x, int) or not isinstance(y, int):
                    raise ValueError(
                        f"connections[{index}].from must use integer x/y coordinates."
                    )
                if x < 0 or y < 0 or x >= width or y >= height:
                    raise ValueError(
                        f"connections[{index}].from is outside map bounds "
                        f"(width={width}, height={height})."
                    )

        return self


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_model(model: Any, payload: Any, *, source: str) -> Any:
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise RuntimeDataValidationError.from_pydantic(source, exc) from exc


def validate_type_chart_payload(payload: Any, *, source: str = "type_chart.json") -> Dict[str, Dict[str, float]]:
    validated = _validate_model(_TypeChartModel, payload, source=source)
    return dict(validated.root)


def load_validated_type_chart(path: str) -> Dict[str, Dict[str, float]]:
    payload = _read_json(path)
    return validate_type_chart_payload(payload, source=path)


def validate_moves_payload(payload: Any, *, source: str = "moves.json") -> list[dict[str, Any]]:
    validated = _validate_model(_MoveListModel, payload, source=source)
    return [move.model_dump(exclude_none=True) for move in validated.root]


def load_validated_moves(path: str) -> list[dict[str, Any]]:
    payload = _read_json(path)
    return validate_moves_payload(payload, source=path)


def validate_monsters_payload(
    payload: Any,
    *,
    source: str = "monsters.json",
    strict_conflicts: bool = False,
    known_types: Iterable[str] | None = None,
    known_moves: Iterable[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    _validate_model(_RawMonsterListModel, payload, source=source)
    normalized_monsters, warnings = normalize_monsters(
        payload, strict_conflicts=strict_conflicts
    )
    validated = _validate_model(
        _CanonicalMonsterListModel, normalized_monsters, source=source
    )
    monsters = [
        monster.model_dump(exclude_none=True) for monster in validated.root
    ]

    extra_errors: list[dict[str, Any]] = []
    allowed_types = (
        {str(value).strip() for value in known_types if str(value).strip()}
        if known_types is not None
        else None
    )
    allowed_moves = (
        {str(value).strip() for value in known_moves if str(value).strip()}
        if known_moves is not None
        else None
    )

    for monster_index, monster in enumerate(monsters):
        monster_type = monster.get("type", "")
        if allowed_types is not None and monster_type not in allowed_types:
            extra_errors.append(
                {
                    "loc": (monster_index, "type"),
                    "msg": (
                        f"Unknown monster type '{monster_type}'. "
                        "Type must exist in type_chart.json."
                    ),
                }
            )
        if allowed_moves is not None:
            for learnset_index, entry in enumerate(monster.get("learnset", [])):
                move_name = entry.get("move", "")
                if move_name not in allowed_moves:
                    extra_errors.append(
                        {
                            "loc": (monster_index, "learnset", learnset_index, "move"),
                            "msg": (
                                f"Unknown move '{move_name}'. "
                                "Move must exist in moves.json."
                            ),
                        }
                    )

    if extra_errors:
        raise RuntimeDataValidationError(source=source, errors=extra_errors)

    return monsters, warnings


def load_validated_monsters(
    path: str,
    *,
    strict_conflicts: bool = False,
    known_types: Iterable[str] | None = None,
    known_moves: Iterable[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    payload = _read_json(path)
    return validate_monsters_payload(
        payload,
        source=path,
        strict_conflicts=strict_conflicts,
        known_types=known_types,
        known_moves=known_moves,
    )


def validate_map_payload(payload: Any, *, source: str = "map.json") -> dict[str, Any]:
    validated = _validate_model(_MapPayloadModel, payload, source=source)
    return validated.model_dump(by_alias=True, exclude_none=True)


def load_validated_map(path: str) -> dict[str, Any]:
    payload = _read_json(path)
    return validate_map_payload(payload, source=path)
