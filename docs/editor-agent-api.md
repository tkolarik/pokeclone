# Editor Agent API

Run the API server:

```bash
python server.py
```

This API exposes deterministic, command-driven control over the **pixel art editor** for agent workflows without UI event simulation.

## Endpoints

- `POST /api/editor/session`
  - Starts or resets an editor control session.
  - Request body: JSON object (use `{}` for defaults).
- `GET /api/editor/state`
  - Returns current editor state needed for autonomous control loops.
- `GET /api/editor/features`
  - Returns the feature-to-action coverage matrix.
- `POST /api/editor/action`
  - Executes one validated editor command.

## Session start example

```bash
curl -sS -X POST http://localhost:8001/api/editor/session \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Action example (monster sprite draw)

```bash
curl -sS -X POST http://localhost:8001/api/editor/action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "draw_pixels",
    "points": [{"x": 5, "y": 8}],
    "color": [255, 0, 0, 255]
  }'
```

## Read state example

```bash
curl -sS http://localhost:8001/api/editor/state
```

## Feature Coverage Matrix

| Editor feature | API action / endpoint | Status |
| --- | --- | --- |
| Session bootstrap | `POST /api/editor/session` | Supported |
| State inspection | `GET /api/editor/state` | Supported |
| Tool selection (draw/eraser/fill/select/paste/eyedropper) | `set_tool` | Supported |
| Monster navigation | `select_monster`, `next_monster`, `previous_monster` | Supported |
| Sprite side control (front/back) | `set_sprite`, `switch_sprite` | Supported |
| Draw strokes | `draw_pixels` | Supported |
| Flood fill | `fill_at` | Supported |
| Selection set/clear | `set_selection`, `clear_selection` | Supported |
| Copy/paste selection | `copy_selection`, `paste_at` | Supported |
| Selection transforms | `mirror_selection`, `rotate_selection` | Supported |
| Color + brush controls | `set_color`, `set_brush_size` | Supported |
| Pixel readback | `read_pixel` | Supported |
| Undo/redo | `undo`, `redo` | Supported |
| Clipboard history/favorites | `clipboard_prev`, `clipboard_next`, `clipboard_toggle_favorite` | Supported |
| Save monster sprites | `save_monster_sprites` | Supported |
| Reference image controls | `load_reference_image`, `clear_reference_image`, `set_reference_alpha`, `set_subject_alpha`, `set_reference_scale`, `import_reference_image` | Supported |
| Background-mode editing actions | N/A | Not yet exposed |
| Tile/NPC mode editing actions | N/A | Not yet exposed |

## Validation and error behavior

- Invalid payloads return 4xx JSON errors with actionable messages.
- Actions requiring an initialized editor session return `409` until `POST /api/editor/session` is called.
- Invalid coordinates and schema violations are rejected without mutating editor state.
