# Map Editor

Entry point: `python -m src.overworld.map_editor`

The map editor is a grid-based tool with a top toolbar, a left palette, a right inspector, and a central canvas.

## Toolbar buttons

### Tools

- Brush
- Fill
- Rect
- Line
- Erase
- Eye (eyedropper)

### Modes

- Tiles
- Entities
- Triggers
- Connect
- Overrides

### Layers

- Ground
- Overlay

### Right-side buttons

- World (open World View)
- New Map
- Help? / Help On

## Palette panel (left)

### Tabs

- Tiles
- NPCs

### Actions

- Add Tile
- Add NPC

## Inspector panel (right)

Shows:
- Current mode, tool, layer
- Selected tile
- Map id and dimensions
- Tileset id
- Zoom
- Hover cell details (tile ids, overrides, entities, triggers, portals)
- Shortcuts list

## Keyboard shortcuts

- Ctrl+S: save map
- Ctrl+O: load map
- Ctrl+Z: undo
- Ctrl+Y: redo
- 1: set layer to Ground
- 2: set layer to Overlay
- B: Brush tool
- F: Fill tool
- R: Rect tool
- L: Line tool
- E: Erase tool
- I: Eyedropper tool
- T: Tiles mode
- N: Entities mode
- G: Triggers mode
- C: Connections mode
- O: Overrides mode
- + / = / keypad + / ]: zoom in
- - / _ / keypad - / [: zoom out
- A: add entity/trigger/connection (depends on mode)
- M: edit map metadata (id, name, tileset, size, music)
- Esc: quit

## Mouse controls

- Left click: primary action (varies by mode/tool)
- Right click: secondary action (varies by mode)
- Middle mouse drag: pan camera
- Space + left drag: pan camera

## Help mode

- Click Help? to toggle help mode.
- While help mode is on, clicking a control shows its tooltip in the status bar instead of performing the action.

## Mode behaviors

### Tiles mode

Primary (left click):
- Brush/Erase: set or clear the tile on the active layer
- Fill: flood-fill the active layer
- Rect: click start cell, release to fill rectangle
- Line: click start cell, release to draw a line
- Eyedropper: pick the tile under the cursor

Secondary (right click):
- If a tile exists and Shift is not held: open Pixel Art Editor for that tile
- Otherwise: erase tile (set to empty) on the active layer

### Entities mode

Primary (left click):
- If an entity exists on the cell: select it
- Otherwise: place an entity using the selected NPC from the palette

Secondary (right click):
- If an entity exists and Shift is not held: open Pixel Art Editor for its sprite
- If an entity exists and Shift is held: delete the entity

Add (A key with a hover cell):
- Prompts for entity id, name, sprite id, dialog text

### Triggers mode

Primary (left click):
- Select a trigger on the cell (if any)

Add (A key with a hover cell):
- Prompts for trigger id, type, and JSON actions

### Connections mode

Primary (left click):
- If a connection exists at the cell or map edge: select it
- Otherwise: add a connection (prompts for target map, spawn, and facing)

Add (A key with a hover cell):
- Prompts for connection info (same as above)

### Overrides mode

Primary (left click):
- Cycle walkable state: None -> blocked -> walkable -> None
- If Shift is held: toggle the "spawn" flag

Secondary (right click):
- Remove override at the cell

## Dialog prompts

The editor uses blocking text prompts for most creation and metadata edits. Common patterns:

- Enter to confirm
- Esc to cancel
- Backspace to delete characters

Specific prompts include:

- New map id, width/height, and optional connection type
- Entity id/name/sprite id/dialog text
- Trigger id/type/actions JSON
- Connection id/target map/spawn/facing
- Map metadata (id, name, tileset id, dimensions, tile size, music id)
