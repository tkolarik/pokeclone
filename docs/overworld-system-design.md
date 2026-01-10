# Overworld System Design

## Purpose
- Define how the overworld runtime loads, renders, and executes maps authored by the map editor (`docs/map-editor-design.md`) without hand-editing data.
- Provide stable behaviors for movement, collision, interactions, triggers, map transitions, and audio so tooling can target a consistent contract.

## Scope
- Runtime systems: map loading, rendering, player control/movement, collision, interactions, triggers/actions, connections/portals, per-map audio, and save/load of map state (not player progress).
- Data contract: consumes the map JSON schema defined in `docs/map-editor-design.md`; extends it only with runtime-only state (e.g., transient flags, active music handle).
- Integration: battle simulator for NPC/team encounters, dialog/text box UI, and tile manager outputs for rendering.

## Non-goals (for now)
- Long-running scripting engine; keep to a limited action set (show text, start battle, set flags, play sound/music).
- World persistence (player save files, quest state); only ephemeral session flags are covered here.
- Networking or multiplayer.

## Architecture Overview
- **Map Loader:** Reads `maps/{mapId}.json` (see map editor doc for schema), validates required fields, and normalizes defaults (missing overlay layer → empty; missing overrides → empty map).
- **Renderer:** Draws ordered tile layers (`ground`, `overlay`, optional future layers) and entities/NPCs. Supports camera follow for the player with configurable margins.
- **Player Controller:** Handles input (WASD/arrow), movement, facing, and interaction button. Supports grid-stepped or smooth movement; collisions gate movement decisions.
- **Collision & Navigation:** Combines base tile walkability with per-cell overrides and entity collisions. Encounter flags are exposed to the trigger/action system.
- **Interaction System:** On interaction input, checks the facing cell for entities/triggers and dispatches actions (dialog, battle, etc.).
- **Trigger/Action Pipeline:** Evaluates `onEnter` and `onInteract` triggers, conditionally executes an ordered list of actions. Actions include `showText`, `startBattle`, `playSound`, `setFlag`, `clearFlag`, `warp`, and `runConnection` (reuse connection logic). Extensible with a registry.
- **Connections Manager:** Executes edge and portal transitions with spawn placement and facing rules; handles fade/transition effects.
- **Audio Manager:** Plays per-map music (`musicId`) and stops/fades when changing maps; exposes `playSound` for trigger actions.
- **State & Flags:** Maintains transient session flags (bool key/value) to gate dialogs, events, and visibility (e.g., environmental puzzles). Flags are in-memory; persistence is out-of-scope.

## Data Contract (summary)
- Full schema lives in `docs/map-editor-design.md`. The runtime consumes the same fields: metadata, dimensions, `tileSize`, `tilesetId`, ordered `layers`, `connections`, `entities`, `triggers`, `overrides`, optional `musicId`.
- Tilesets: referenced by stable IDs provided by the tile manager (OVERWORLD-4).
- Unknown fields: loader preserves unknown fields when saving back (round-trip friendly).

## Runtime Behavior
- **Movement Model:** Grid-stepped (one tile per move) with optional tweened animation; movement blocked by collisions before committing step. Facing updates even when blocked.
- **Camera:** Center on player with clamp to map bounds; optional dead-zone/margin to reduce jitter.
- **Collision Rules:**
  - Base walkability from tile data (default walkable unless tile property says otherwise per tileset definition).
  - Overrides (`overrides["x,y"].walkable`) take precedence.
  - Entities with `collision: true` block movement.
  - Edge cells remain walkable; transitions are handled by connections manager.
- **Interactions:**
  - Interaction key targets the cell in front of the player; if an entity with dialog/actions exists, dispatches its actions (from `dialog`/`dialogId` or `actions`).
  - If multiple triggers overlap, deterministic priority: entity-specific actions first, then cell triggers (`onInteract`), then default tile action (none).
- **Triggers:**
  - `onEnter` fires after a successful move into the cell.
  - `onInteract` fires when the interaction key is pressed toward the cell.
  - Trigger conditions can read flags; repeatability per trigger (`repeatable`).
- **Actions (minimal set):**
  - `showText` (blocking text box UI; supports sequences)
  - `startBattle` (launch battle simulator with referenced team/NPC)
  - `setFlag` / `clearFlag` (affects future dialogs/visibility)
  - `playSound`
  - `playMusic` / `stopMusic` (usually managed by map transitions)
  - `warp` / `runConnection` (teleport or invoke connection definition)
  - `toggleEntity` / `toggleTileOverride` (optional for environmental puzzles)
- **Connections:**
  - **Edge:** When stepping off-map on an edge with a connection, load target map and place player at target spawn; set facing to target’s `facing` (if provided) or opposite the entry edge.
  - **Portal:** When entering a portal cell, load target map and spawn at provided coords; facing uses specified `facing` or preserves player facing.
  - Validations align with the map editor doc (spawn within bounds, known map IDs).
- **Audio:**
  - On map load, resolve `musicId` to an audio asset; fade out current track and fade in new track.
  - Fallback to default overworld track if `musicId` missing.

## Rendering Details
- Tile drawing order: ground → entities (with simple depth-sort by `y`) → overlay → UI (text box, prompts).
- Support basic animations via tileset frame definitions if provided by tile manager (future-friendly).
- Optional debug overlays: collision mask, trigger markers, connection markers (toggled via debug key).

## File/Directory Conventions
- Maps: `maps/{mapId}.json` (as authored by the map editor).
- Tilesets: resolved via tile manager output directory/config (OVERWORLD-4).
- Music: resolved via audio asset path/id (OVERWORLD-5).

## Testing Strategy
- Unit: collision checks, trigger evaluation ordering, connection resolution (edge/portal), flag mutations, audio switching logic.
- Integration: load map → move → trigger dialog → change map → verify music swap; load/save round-trip preserves unknown fields.
- Manual: match the acceptance flow from OVERWORLD-3 (create map in editor → play in overworld and verify connections/dialog/collision).

## Open Questions
- Should triggers support parameterized conditions beyond flags (e.g., inventory checks) - lets backlog it for now
- Do we need persistence for flags across map loads, and if so, where to store it - broader question about save and load system. For now lets keep an eye towards allowing it in the future but not implement it yet.
