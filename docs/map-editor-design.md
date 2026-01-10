# Map Editor Design

## Purpose
- Provide a dedicated tool to author overworld maps (tiles, entities, triggers, connections) that can be loaded by the existing overworld runtime without hand-editing files.
- Establish stable formats and IDs so future features (tile manager, per-map music) plug in without data migrations.

## Goals
- Fast tile painting with common tools and a preview of the selected tile.
- Visible and editable connections between maps (edges and explicit portals) with spawn position and facing.
- Entity and trigger authoring with dialog/text support that the overworld can render.
- Per-cell property overrides (walkable, encounter flags, water/slow/warp, etc.).
- Save/load maps in a versioned, schema-validated format.
- undo/redo
- state based triggers conditional logic simple actions should allow for features on a similar level as pokemon crystal. check for flags to determine entity dialog, environmental puzzles to make parts of environment appear/disappear or lock and unlock.
- colision UI with capbility to add override 
- preview adjcent maps (helps with aligning paths for example)
- connection with tile editor (planned feature) launch pixle art editor with selected already active, ability to write placeholder single color tiles directly to tile path for later editing.
- NPCs can be battleable or non, with predefined teams, editable a team editor pop up which can be opened from map editor.
- Tiles can be rotated natively without requiring multiple images saved
- Tiles and entities support animations.
- Maps include NPC entities as special "tile" types
- Global Player spawn on new game - special tile

## Non-goals (for now)
- Scripting beyond dialog/text triggers (note in data model for future expansion).
- Multi-user collaboration or remote storage.

## UX / Workflow
- **Map canvas:** Grid-aligned view with zoom and pan. Cursor shows tile under edit. Optional grid toggle.
- **Tile palette:** Lists tiles from a selected tile set (from tile manager); shows tile ID/name. Supports eyedropper from canvas.
- **Layers:** At minimum `ground` and `overlay`. Layer picker shows which layer edits apply to. Optional hidden/lock toggles.
- **Tools:** Brush, fill, rectangle, line, erase (tile to empty), eyedropper. Keyboard shortcuts encouraged.
- **Connections overlay:** Edge markers for N/E/S/W connections plus portal icons rendered at specific cells. Selecting a marker opens connection properties.
- **Entity/trigger mode:** Placement cursor snaps to cells; selection opens property inspector.
- **Inspector panel:** Contextual detail editor for tiles (overrides), entities/NPCs, triggers, connections.
- **Validation:** Save button runs validation and reports blocking errors (missing references, invalid coordinates) plus warnings.

## Data Model (per map)
- **Metadata:** `id` (string, stable), `name`, `version`, `tileSize` (pixels), `dimensions` (`width`, `height`).
- **Tileset reference:** `tilesetId` and optional version/hash. Tiles referenced by stable `tileId`s provided by the tile manager (see OVERWORLD-4).
- **Layers:** Ordered list; each layer is a 2D array of `tileId` or `null`. Required: `ground`, `overlay`. Future layers allowed.
- **Connections:** Entries for edges and portals with: `type` (`edge`/`portal`), `from` (edge side or cell coords), `to` (`mapId`, `spawn` coords, optional `facing`), and optional `condition` stub for future scripting.
- **Entities/NPCs:** Objects with `id`, `type` (`npc`/`object`), `name`, `spriteId`, `position` (cell), `facing`, `collision` (bool), optional `dialogId` or inline `dialog` text, and custom properties.
- **Triggers:** Objects with `id`, `type` (`onEnter`/`onInteract`), `position` (cell or area), `actions` (e.g., `showText`, `startBattle`, `playSound` placeholder), `repeatable` flag.
- **Cell overrides:** Sparse map keyed by cell coords (`"x,y"`): `{ walkable: bool, flags: [string] }` where flags cover encounter zones, water, slow, warp, etc.
- **Music (OVERWORLD-5):** Optional `musicId` per map.

### Example (trimmed JSON)
```json
{
  "id": "town_square",
  "name": "Town Square",
  "version": "1.0.0",
  "tileSize": 16,
  "dimensions": { "width": 64, "height": 64 },
  "tilesetId": "town_tiles_v1",
  "layers": [
    { "name": "ground", "tiles": [[ "grass", "path" ], [ "grass", "path" ]] },
    { "name": "overlay", "tiles": [[ null, "lamp_post" ], [ null, null ]] }
  ],
  "connections": [
    { "id": "north_exit", "type": "edge", "from": "north", "to": { "mapId": "route_1", "spawn": { "x": 10, "y": 63 }, "facing": "south" } },
    { "id": "house_portal", "type": "portal", "from": { "x": 20, "y": 30 }, "to": { "mapId": "house_interior", "spawn": { "x": 5, "y": 8 }, "facing": "north" } }
  ],
  "entities": [
    { "id": "npc_1", "type": "npc", "name": "Guide", "spriteId": "guide_npc", "position": { "x": 12, "y": 14 }, "facing": "south", "collision": true, "dialog": [ "Welcome!", "Stay on the path." ] }
  ],
  "triggers": [
    { "id": "enter_tutorial", "type": "onEnter", "position": { "x": 12, "y": 14 }, "actions": [ { "kind": "showText", "text": "You stepped on a tutorial tile." } ], "repeatable": false }
  ],
  "overrides": {
    "15,22": { "walkable": false, "flags": [ "water" ] },
    "10,63": { "walkable": true, "flags": [ "spawn" ] }
  },
  "musicId": "town_theme"
}
```

## Validation Rules
- Dimensions must match layer array sizes; tile IDs must exist in the referenced tileset.
- Connections: `to.mapId` must exist; spawn coords within target map bounds; facing in `north/east/south/west`.
- Entities/triggers positions within bounds; referenced sprites/dialog IDs must resolve.
- Overrides only on valid cells; flags must be from a known set.
- Version field required; editor should refuse to save with blocking errors.

## Integration Points
- **File format:** JSON saved to `maps/{mapId}.json` (or configurable directory). Include `version` for migrations.
- **Runtime load:** Overworld loader reads the same schema; missing layers default to empty overlay.
- **Tile manager dependency:** Palette populated from tile manager output; tiles referenced by stable IDs.
- **Music linkage:** `musicId` consumed by overworld audio system (OVERWORLD-5).
- **Export/import:** Editor can open existing map files, edit, and re-save without losing unknown fields (preserve extras).
