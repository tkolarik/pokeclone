"""Monster-first MCP server for agent-driven sprite drawing workflows."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from src.editor.api_control import EditorApiController, EditorApiError

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603


class McpError(Exception):
    """JSON-RPC / MCP protocol-level error."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = int(code)
        self.message = str(message)


class ToolValidationError(Exception):
    """Input validation error for tool arguments."""

    pass


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]


def _expect_object(value: Any, field_name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ToolValidationError(f"Field '{field_name}' must be an object.")
    return value


def _expect_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(f"Field '{field_name}' must be a non-empty string.")
    return value.strip()


def _expect_int(value: Any, field_name: str, *, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolValidationError(f"Field '{field_name}' must be an integer.")
    if minimum is not None and value < minimum:
        raise ToolValidationError(f"Field '{field_name}' must be >= {minimum}.")
    return value


def _expect_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ToolValidationError(f"Field '{field_name}' must be a boolean.")
    return value


def _expect_rgba(value: Any, field_name: str) -> List[int]:
    if not isinstance(value, list) or len(value) not in (3, 4):
        raise ToolValidationError(f"Field '{field_name}' must be an RGB or RGBA array.")

    channels: List[int] = []
    for index, channel in enumerate(value):
        parsed = _expect_int(channel, f"{field_name}[{index}]", minimum=0)
        if parsed > 255:
            raise ToolValidationError(f"Field '{field_name}[{index}]' must be <= 255.")
        channels.append(parsed)
    if len(channels) == 3:
        channels.append(255)
    return channels


def _expect_point(value: Any, field_name: str) -> Dict[str, int]:
    value_obj = _expect_object(value, field_name)
    unknown = sorted(set(value_obj) - {"x", "y"})
    if unknown:
        raise ToolValidationError(
            f"Field '{field_name}' has unknown key(s): {', '.join(unknown)}."
        )
    if "x" not in value_obj or "y" not in value_obj:
        raise ToolValidationError(f"Field '{field_name}' must include 'x' and 'y'.")
    return {
        "x": _expect_int(value_obj["x"], f"{field_name}.x"),
        "y": _expect_int(value_obj["y"], f"{field_name}.y"),
    }


def _validate_allowed_keys(
    payload: Dict[str, Any],
    *,
    allowed: set[str],
    required: set[str],
    label: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ToolValidationError(
            f"{label} has unknown field(s): {', '.join(unknown)}."
        )

    missing = sorted(field for field in required if field not in payload)
    if missing:
        raise ToolValidationError(
            f"{label} missing required field(s): {', '.join(missing)}."
        )


class MonsterDrawingMcpServer:
    """MCP server that wraps EditorApiController tools for monster drawing."""

    def __init__(
        self,
        *,
        controller: Optional[EditorApiController] = None,
        server_name: str = "pokeclone-monster-drawing-mcp",
        server_version: str = "0.1.0",
    ) -> None:
        self.controller = controller or EditorApiController()
        self.server_name = server_name
        self.server_version = server_version
        self._tools = self._build_tools()

    def _build_tools(self) -> Dict[str, ToolDefinition]:
        tools: List[ToolDefinition] = [
            ToolDefinition(
                name="monster_session_start",
                description="Start/reset a monster editor session and optionally choose monster/sprite.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "monsterName": {"type": "string"},
                        "monsterIndex": {"type": "integer", "minimum": 0},
                        "sprite": {"type": "string", "enum": ["front", "back"]},
                    },
                },
                handler=self._tool_session_start,
            ),
            ToolDefinition(
                name="monster_get_state",
                description="Read current monster editor state for agent control loops.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {},
                },
                handler=self._tool_get_state,
            ),
            ToolDefinition(
                name="monster_select",
                description="Select a monster by name or index.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "monsterName": {"type": "string"},
                        "monsterIndex": {"type": "integer", "minimum": 0},
                    },
                },
                handler=self._tool_select_monster,
            ),
            ToolDefinition(
                name="monster_set_sprite",
                description="Set active sprite side.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["sprite"],
                    "properties": {
                        "sprite": {"type": "string", "enum": ["front", "back"]},
                    },
                },
                handler=self._tool_set_sprite,
            ),
            ToolDefinition(
                name="monster_set_tool",
                description="Set active editing tool (draw/eraser/fill/select/paste/eyedropper).",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["tool"],
                    "properties": {
                        "tool": {
                            "type": "string",
                            "enum": ["draw", "eraser", "fill", "select", "paste", "eyedropper"],
                        }
                    },
                },
                handler=self._tool_set_tool,
            ),
            ToolDefinition(
                name="monster_set_color",
                description="Set current RGBA drawing color.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["color"],
                    "properties": {
                        "color": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 4,
                            "items": {"type": "integer", "minimum": 0, "maximum": 255},
                        }
                    },
                },
                handler=self._tool_set_color,
            ),
            ToolDefinition(
                name="monster_draw_pixels",
                description="Draw one or more grid points using current/provided color.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["points"],
                    "properties": {
                        "points": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": ["x", "y"],
                                "properties": {
                                    "x": {"type": "integer"},
                                    "y": {"type": "integer"},
                                },
                            },
                        },
                        "color": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 4,
                            "items": {"type": "integer", "minimum": 0, "maximum": 255},
                        },
                        "brushSize": {"type": "integer", "minimum": 1},
                        "eraser": {"type": "boolean"},
                    },
                },
                handler=self._tool_draw_pixels,
            ),
            ToolDefinition(
                name="monster_stamp_pattern",
                description="Stamp an ASCII pattern where each token maps to a color entry.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["topLeft", "pattern", "palette"],
                    "properties": {
                        "topLeft": {
                            "type": "object",
                            "required": ["x", "y"],
                            "properties": {
                                "x": {"type": "integer"},
                                "y": {"type": "integer"},
                            },
                        },
                        "pattern": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                        "palette": {"type": "object"},
                        "transparentToken": {"type": "string"},
                    },
                },
                handler=self._tool_stamp_pattern,
            ),
            ToolDefinition(
                name="monster_fill",
                description="Flood-fill from a specific grid position.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["x", "y"],
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "color": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 4,
                            "items": {"type": "integer", "minimum": 0, "maximum": 255},
                        },
                    },
                },
                handler=self._tool_fill,
            ),
            ToolDefinition(
                name="monster_set_selection",
                description="Set an explicit rectangular selection.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["x", "y", "width", "height"],
                    "properties": {
                        "x": {"type": "integer", "minimum": 0},
                        "y": {"type": "integer", "minimum": 0},
                        "width": {"type": "integer", "minimum": 1},
                        "height": {"type": "integer", "minimum": 1},
                    },
                },
                handler=self._tool_set_selection,
            ),
            ToolDefinition(
                name="monster_clear_selection",
                description="Clear active selection.",
                input_schema={"type": "object", "additionalProperties": False, "properties": {}},
                handler=self._tool_clear_selection,
            ),
            ToolDefinition(
                name="monster_copy_selection",
                description="Copy the active selection into clipboard history.",
                input_schema={"type": "object", "additionalProperties": False, "properties": {}},
                handler=self._tool_copy_selection,
            ),
            ToolDefinition(
                name="monster_paste",
                description="Paste clipboard pixels at top-left coordinate.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["x", "y"],
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                    },
                },
                handler=self._tool_paste,
            ),
            ToolDefinition(
                name="monster_transform_selection",
                description="Mirror or rotate current selection.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["operation"],
                    "properties": {
                        "operation": {"type": "string", "enum": ["mirror", "rotate"]},
                    },
                },
                handler=self._tool_transform_selection,
            ),
            ToolDefinition(
                name="monster_undo",
                description="Undo one canvas operation.",
                input_schema={"type": "object", "additionalProperties": False, "properties": {}},
                handler=self._tool_undo,
            ),
            ToolDefinition(
                name="monster_redo",
                description="Redo one canvas operation.",
                input_schema={"type": "object", "additionalProperties": False, "properties": {}},
                handler=self._tool_redo,
            ),
            ToolDefinition(
                name="monster_save_sprites",
                description="Save front/back sprites for the current monster.",
                input_schema={"type": "object", "additionalProperties": False, "properties": {}},
                handler=self._tool_save_sprites,
            ),
            ToolDefinition(
                name="monster_read_pixel",
                description="Read RGBA at a grid position.",
                input_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["x", "y"],
                    "properties": {
                        "x": {"type": "integer"},
                        "y": {"type": "integer"},
                        "sprite": {"type": "string", "enum": ["front", "back"]},
                    },
                },
                handler=self._tool_read_pixel,
            ),
        ]
        return {tool.name: tool for tool in tools}

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def handle_jsonrpc_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        request_id: Any = None
        is_notification = False
        try:
            if not isinstance(message, dict):
                raise McpError(JSONRPC_INVALID_REQUEST, "Request must be a JSON object.")

            request_id = message.get("id")
            is_notification = "id" not in message

            if message.get("jsonrpc") != JSONRPC_VERSION:
                raise McpError(JSONRPC_INVALID_REQUEST, "Only JSON-RPC 2.0 requests are supported.")

            method = message.get("method")
            if not isinstance(method, str) or not method.strip():
                raise McpError(JSONRPC_INVALID_REQUEST, "Field 'method' must be a non-empty string.")

            params = message.get("params", {})
            if params is None:
                params = {}
            if not isinstance(params, dict):
                raise McpError(JSONRPC_INVALID_PARAMS, "Field 'params' must be an object.")

            if method == "initialize":
                result = {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": {
                        "name": self.server_name,
                        "version": self.server_version,
                    },
                    "capabilities": {
                        "tools": {
                            "listChanged": False,
                        }
                    },
                }
                return self._success_response(request_id, result)

            if method == "notifications/initialized":
                return None

            if method == "tools/list":
                return self._success_response(request_id, {"tools": self.list_tools()})

            if method == "tools/call":
                tool_result = self._handle_tools_call(params)
                return self._success_response(request_id, tool_result)

            raise McpError(JSONRPC_METHOD_NOT_FOUND, f"Method '{method}' is not supported.")
        except McpError as exc:
            if is_notification:
                return None
            return self._error_response(request_id, exc.code, exc.message)
        except Exception as exc:
            if is_notification:
                return None
            return self._error_response(
                request_id,
                JSONRPC_INTERNAL_ERROR,
                f"Internal server error: {exc}",
            )

    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            params,
            allowed={"name", "arguments"},
            required={"name"},
            label="tools/call params",
        )
        tool_name = _expect_non_empty_string(params.get("name"), "name")

        raw_arguments = params.get("arguments", {})
        if raw_arguments is None:
            raw_arguments = {}
        arguments = _expect_object(raw_arguments, "arguments")

        tool = self._tools.get(tool_name)
        if tool is None:
            return self._tool_error(f"Unknown tool '{tool_name}'.")

        try:
            payload = tool.handler(arguments)
        except ToolValidationError as exc:
            return self._tool_error(f"Invalid arguments for '{tool_name}': {exc}")
        except EditorApiError as exc:
            return self._tool_error(
                f"Editor API error ({exc.status_code}) while running '{tool_name}': {exc.message}"
            )
        except Exception as exc:  # pragma: no cover - defensive wrapper
            return self._tool_error(f"Unhandled tool error in '{tool_name}': {exc}")

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(payload, sort_keys=True),
                }
            ],
            "structuredContent": payload,
            "isError": False,
        }

    def _tool_error(self, message: str) -> Dict[str, Any]:
        return {
            "content": [{"type": "text", "text": message}],
            "isError": True,
        }

    def _run_action(self, action_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.controller.execute_action(action_payload)

    def _tool_session_start(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"monsterName", "monsterIndex", "sprite"},
            required=set(),
            label="monster_session_start arguments",
        )
        payload: Dict[str, Any] = {}
        if "monsterName" in args:
            payload["monsterName"] = _expect_non_empty_string(args["monsterName"], "monsterName")
        if "monsterIndex" in args:
            payload["monsterIndex"] = _expect_int(args["monsterIndex"], "monsterIndex", minimum=0)
        if "sprite" in args:
            sprite = _expect_non_empty_string(args["sprite"], "sprite")
            if sprite not in {"front", "back"}:
                raise ToolValidationError("Field 'sprite' must be 'front' or 'back'.")
            payload["sprite"] = sprite
        return self.controller.start_session(payload)

    def _tool_get_state(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed=set(),
            required=set(),
            label="monster_get_state arguments",
        )
        return self.controller.get_state()

    def _tool_select_monster(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"monsterName", "monsterIndex"},
            required=set(),
            label="monster_select arguments",
        )
        if "monsterName" in args and "monsterIndex" in args:
            raise ToolValidationError("Provide only one of 'monsterName' or 'monsterIndex'.")

        payload: Dict[str, Any] = {"action": "select_monster"}
        if "monsterName" in args:
            payload["monsterName"] = _expect_non_empty_string(args["monsterName"], "monsterName")
        elif "monsterIndex" in args:
            payload["monsterIndex"] = _expect_int(args["monsterIndex"], "monsterIndex", minimum=0)
        else:
            raise ToolValidationError("Provide 'monsterName' or 'monsterIndex'.")
        return self._run_action(payload)

    def _tool_set_sprite(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"sprite"},
            required={"sprite"},
            label="monster_set_sprite arguments",
        )
        sprite = _expect_non_empty_string(args["sprite"], "sprite")
        if sprite not in {"front", "back"}:
            raise ToolValidationError("Field 'sprite' must be 'front' or 'back'.")
        return self._run_action({"action": "set_sprite", "sprite": sprite})

    def _tool_set_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"tool"},
            required={"tool"},
            label="monster_set_tool arguments",
        )
        tool = _expect_non_empty_string(args["tool"], "tool").lower()
        allowed_tools = {"draw", "eraser", "fill", "select", "paste", "eyedropper"}
        if tool not in allowed_tools:
            raise ToolValidationError(
                "Field 'tool' must be one of: draw, eraser, fill, select, paste, eyedropper."
            )
        return self._run_action({"action": "set_tool", "tool": tool})

    def _tool_set_color(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"color"},
            required={"color"},
            label="monster_set_color arguments",
        )
        color = _expect_rgba(args["color"], "color")
        return self._run_action({"action": "set_color", "color": color})

    def _tool_draw_pixels(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"points", "color", "brushSize", "eraser"},
            required={"points"},
            label="monster_draw_pixels arguments",
        )
        raw_points = args["points"]
        if not isinstance(raw_points, list) or not raw_points:
            raise ToolValidationError("Field 'points' must be a non-empty array.")

        points: List[Dict[str, int]] = []
        for index, item in enumerate(raw_points):
            points.append(_expect_point(item, f"points[{index}]"))

        payload: Dict[str, Any] = {"action": "draw_pixels", "points": points}
        if "color" in args:
            payload["color"] = _expect_rgba(args["color"], "color")
        if "brushSize" in args:
            payload["brushSize"] = _expect_int(args["brushSize"], "brushSize", minimum=1)
        if "eraser" in args:
            payload["eraser"] = _expect_bool(args["eraser"], "eraser")
        return self._run_action(payload)

    def _tool_stamp_pattern(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"topLeft", "pattern", "palette", "transparentToken"},
            required={"topLeft", "pattern", "palette"},
            label="monster_stamp_pattern arguments",
        )
        top_left = _expect_point(args["topLeft"], "topLeft")

        pattern = args["pattern"]
        if not isinstance(pattern, list) or not pattern:
            raise ToolValidationError("Field 'pattern' must be a non-empty array of strings.")
        if any(not isinstance(row, str) for row in pattern):
            raise ToolValidationError("Each row in 'pattern' must be a string.")

        palette = _expect_object(args["palette"], "palette")
        if not palette:
            raise ToolValidationError("Field 'palette' must include at least one token/color mapping.")

        parsed_palette: Dict[str, List[int]] = {}
        for token, color in palette.items():
            token_str = _expect_non_empty_string(token, "palette token")
            parsed_palette[token_str] = _expect_rgba(color, f"palette['{token_str}']")

        transparent_token = args.get("transparentToken", ".")
        transparent_token = _expect_non_empty_string(transparent_token, "transparentToken")

        grouped_points: Dict[Tuple[int, int, int, int], List[Dict[str, int]]] = {}
        drawn_pixels = 0
        for row_index, row in enumerate(pattern):
            for col_index, token in enumerate(row):
                if token == transparent_token:
                    continue
                if token not in parsed_palette:
                    raise ToolValidationError(
                        f"Token '{token}' in pattern row {row_index} is missing from 'palette'."
                    )
                color = parsed_palette[token]
                color_key = (color[0], color[1], color[2], color[3])
                grouped_points.setdefault(color_key, []).append(
                    {
                        "x": top_left["x"] + col_index,
                        "y": top_left["y"] + row_index,
                    }
                )
                drawn_pixels += 1

        results: List[Dict[str, Any]] = []
        for color_key, points in grouped_points.items():
            action_result = self._run_action(
                {
                    "action": "draw_pixels",
                    "points": points,
                    "color": [color_key[0], color_key[1], color_key[2], color_key[3]],
                }
            )
            results.append(
                {
                    "color": [color_key[0], color_key[1], color_key[2], color_key[3]],
                    "pointCount": len(points),
                    "result": action_result["result"],
                }
            )

        return {
            "status": "ok",
            "drawnPixels": drawn_pixels,
            "colorPasses": len(results),
            "passes": results,
            "finalState": self.controller.get_state(),
        }

    def _tool_fill(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"x", "y", "color"},
            required={"x", "y"},
            label="monster_fill arguments",
        )
        payload: Dict[str, Any] = {
            "action": "fill_at",
            "x": _expect_int(args["x"], "x"),
            "y": _expect_int(args["y"], "y"),
        }
        if "color" in args:
            payload["color"] = _expect_rgba(args["color"], "color")
        return self._run_action(payload)

    def _tool_set_selection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"x", "y", "width", "height"},
            required={"x", "y", "width", "height"},
            label="monster_set_selection arguments",
        )
        return self._run_action(
            {
                "action": "set_selection",
                "x": _expect_int(args["x"], "x", minimum=0),
                "y": _expect_int(args["y"], "y", minimum=0),
                "width": _expect_int(args["width"], "width", minimum=1),
                "height": _expect_int(args["height"], "height", minimum=1),
            }
        )

    def _tool_clear_selection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed=set(),
            required=set(),
            label="monster_clear_selection arguments",
        )
        return self._run_action({"action": "clear_selection"})

    def _tool_copy_selection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed=set(),
            required=set(),
            label="monster_copy_selection arguments",
        )
        return self._run_action({"action": "copy_selection"})

    def _tool_paste(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"x", "y"},
            required={"x", "y"},
            label="monster_paste arguments",
        )
        return self._run_action(
            {
                "action": "paste_at",
                "x": _expect_int(args["x"], "x"),
                "y": _expect_int(args["y"], "y"),
            }
        )

    def _tool_transform_selection(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"operation"},
            required={"operation"},
            label="monster_transform_selection arguments",
        )
        operation = _expect_non_empty_string(args["operation"], "operation").lower()
        if operation == "mirror":
            return self._run_action({"action": "mirror_selection"})
        if operation == "rotate":
            return self._run_action({"action": "rotate_selection"})
        raise ToolValidationError("Field 'operation' must be 'mirror' or 'rotate'.")

    def _tool_undo(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(args, allowed=set(), required=set(), label="monster_undo arguments")
        return self._run_action({"action": "undo"})

    def _tool_redo(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(args, allowed=set(), required=set(), label="monster_redo arguments")
        return self._run_action({"action": "redo"})

    def _tool_save_sprites(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed=set(),
            required=set(),
            label="monster_save_sprites arguments",
        )
        return self._run_action({"action": "save_monster_sprites"})

    def _tool_read_pixel(self, args: Dict[str, Any]) -> Dict[str, Any]:
        _validate_allowed_keys(
            args,
            allowed={"x", "y", "sprite"},
            required={"x", "y"},
            label="monster_read_pixel arguments",
        )
        payload: Dict[str, Any] = {
            "action": "read_pixel",
            "x": _expect_int(args["x"], "x"),
            "y": _expect_int(args["y"], "y"),
        }
        if "sprite" in args:
            sprite = _expect_non_empty_string(args["sprite"], "sprite")
            if sprite not in {"front", "back"}:
                raise ToolValidationError("Field 'sprite' must be 'front' or 'back'.")
            payload["sprite"] = sprite
        return self._run_action(payload)

    def _success_response(self, request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "result": result,
        }

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": {"code": code, "message": message},
        }


def _read_framed_message(stdin_buffer) -> Optional[Dict[str, Any]]:
    headers: Dict[str, str] = {}
    while True:
        line = stdin_buffer.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("utf-8", errors="replace").strip()
        if ":" not in decoded:
            raise McpError(JSONRPC_PARSE_ERROR, f"Malformed header line: {decoded}")
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()

    if "content-length" not in headers:
        raise McpError(JSONRPC_PARSE_ERROR, "Missing Content-Length header.")
    try:
        content_length = int(headers["content-length"])
    except ValueError as exc:
        raise McpError(JSONRPC_PARSE_ERROR, "Invalid Content-Length value.") from exc

    payload_bytes = stdin_buffer.read(content_length)
    if len(payload_bytes) != content_length:
        raise McpError(JSONRPC_PARSE_ERROR, "Unexpected EOF while reading request payload.")

    try:
        return json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise McpError(JSONRPC_PARSE_ERROR, f"Malformed JSON payload: {exc}") from exc


def _write_framed_message(stdout_buffer, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    stdout_buffer.write(header)
    stdout_buffer.write(body)
    stdout_buffer.flush()


def run_stdio_mcp_server(server: Optional[MonsterDrawingMcpServer] = None) -> int:
    active_server = server or MonsterDrawingMcpServer()

    while True:
        try:
            request = _read_framed_message(sys.stdin.buffer)
        except McpError as exc:
            error_payload = {
                "jsonrpc": JSONRPC_VERSION,
                "id": None,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                },
            }
            _write_framed_message(sys.stdout.buffer, error_payload)
            continue
        except Exception as exc:  # pragma: no cover - defensive wrapper
            error_payload = {
                "jsonrpc": JSONRPC_VERSION,
                "id": None,
                "error": {
                    "code": JSONRPC_INTERNAL_ERROR,
                    "message": f"Unexpected framing error: {exc}",
                },
            }
            _write_framed_message(sys.stdout.buffer, error_payload)
            continue

        if request is None:
            return 0

        response = active_server.handle_jsonrpc_message(request)
        if response is not None:
            _write_framed_message(sys.stdout.buffer, response)


def main() -> int:
    return run_stdio_mcp_server()


if __name__ == "__main__":
    raise SystemExit(main())
