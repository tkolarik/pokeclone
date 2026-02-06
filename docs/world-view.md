# World View

Entry point: `python -m src.overworld.world_view`

World View visualizes all maps and their connections. It supports arranging maps, zooming, and auto-connecting edges.

## Map discovery rules

- World View only discovers `.json` files that contain map-definition payloads.
- A discovered map file must include a non-empty `id` and a `layers` list with tile rows.
- Metadata files (for example `data/maps/world_layout.json`) are explicitly excluded.
- Invalid or non-map JSON files are skipped and are never loaded as playable maps.

## Keyboard shortcuts

- Q or Esc: quit
- R: reload maps from disk
- S: save layout to `data/maps/world_layout.json`
- C: auto-connect edges
- P: toggle manual portal mode
- Enter: create a manual portal (when manual mode has source and target)
- + or =: zoom in
- - or _: zoom out

## Mouse controls

- Left click and drag on a map: move that map
- Left click and drag on empty space: pan the view
- Mouse wheel: zoom in/out

## Manual portal mode

1. Press P to enter manual portal mode.
2. Click a source map.
3. Click a destination map.
4. Press Enter to create the portal connection.
