# Monster Drawing MCP

The monster drawing MCP server provides **tool-based, agent-oriented control** over the pixel editor's monster workflow.

It wraps the editor control API and exposes MCP `tools/list` + `tools/call` methods over stdio (JSON-RPC 2.0 with `Content-Length` framing).

## Start the MCP server

Using project script:

```bash
pokeclone-monster-mcp
```

Or module entrypoint:

```bash
python -m src.mcp.monster_drawing_mcp
```

## Protocol support

- `initialize`
- `notifications/initialized`
- `tools/list`
- `tools/call`

## Tool catalog (monster-first)

- `monster_session_start`
- `monster_get_state`
- `monster_select`
- `monster_set_sprite`
- `monster_set_tool`
- `monster_set_color`
- `monster_draw_pixels`
- `monster_stamp_pattern`
- `monster_fill`
- `monster_set_selection`
- `monster_clear_selection`
- `monster_copy_selection`
- `monster_paste`
- `monster_transform_selection`
- `monster_undo`
- `monster_redo`
- `monster_save_sprites`
- `monster_read_pixel`

## Example MCP-only workflow

1. Call `monster_session_start`.
2. Call `monster_set_color` with RGBA.
3. Call `monster_draw_pixels` or `monster_stamp_pattern`.
4. Optionally call `monster_set_selection` + `monster_copy_selection` + `monster_paste`.
5. Optionally call `monster_undo` / `monster_redo`.
6. Call `monster_save_sprites`.

## Error behavior

- Tool argument validation failures are returned as `tools/call` results with `isError: true`.
- Underlying editor/API failures are propagated as structured MCP tool errors with status context.
- Protocol-level JSON-RPC problems return JSON-RPC error responses.

## Current scope

- Exposed workflows are intentionally scoped to **monster sprite authoring**.
- Background and tile/NPC editor workflows are not yet exported by this MCP server.
