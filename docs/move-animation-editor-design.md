# Move Animation Pixel Art Editor Design

## Purpose
- Provide a dedicated editor workflow for authoring **battle move animations** (effects like projectiles, flashes, screen shakes) that can be played by the existing battle simulator.
- Keep the workflow consistent with the existing `pixle_art_editor` patterns (frames tray, reference images, save/load JSON + PNG assets), while adding animation-specific QoL features.

## Goals (Scope)
- Create/edit a **Move Animation** asset with:
  - A timeline of frames (variable duration per frame).
  - One or more **objects/layers** (each can be drawn and repositioned).
  - Playback preview (looping, stepping, frame scrubbing).
- QoL requirements (explicit for POKE-27):
  - Onion-skin / afterimage preview (previous/next frame).
  - Reference image support (same model as monster/tile modes).
  - Draggable object/layer positioning (per-frame transforms).
- Export formats suitable for runtime usage (battle sim) and for asset review (sprite sheet / GIF).

## Non-goals (for now)
- Full Aseprite-grade animation features (tags, easing curves, per-layer blend modes).
- Hardware-accurate indexed palettes / tile constraints (can be added later; see “Future Enhancements”).
- Complex VFX primitives (particles, shaders); this editor focuses on pixel-authored sprites + simple transforms.

## Key Concepts

### 1) Stage vs. Object Canvas
- **Stage Preview:** A composited view that shows attacker + defender sprites (reference only) and the move animation objects on top.
- **Object Canvas:** The pixel grid where the user edits the active object’s pixels for the current frame (similar to the existing sprite/tile editor).

This split allows “draggable object positioning” without forcing artists to draw directly inside a full battle-sized canvas.

### 2) Anchors
Each object is placed relative to an anchor:
- `attacker` (relative to the attacker sprite)
- `defender` (relative to the defender sprite)
- `screen` (absolute screen coordinates)

Anchoring allows the same move animation to work across different sprite sizes/positions while still giving precise placement controls.

### 3) Integer Pixel Transforms
To preserve the pixel-art feel, per-frame transforms are integer-only:
- `x`, `y` translation: integers (no sub-pixel)
- Optional: `flipX`, `flipY`
- Optional: `visible` toggle

## UX / Workflow

### Startup / Asset Management
- Add a new edit mode: **Move Animations** alongside Monster / Tiles / Background.
- On entry:
  - **New Animation** → prompt for `animationId`, default object count = 1, default canvas size = 32×32.
  - **Edit Existing** → file list dialog of available move animation JSON files.

### Main Layout (proposed)
- **Left:** Stage preview (shows attacker/defender references + composited objects).
- **Center:** Object canvas (pixel grid for the active object, current frame).
- **Right panels:**
  - **Objects/Layers panel** (list; select active; add/remove; reorder).
  - **Properties panel** for selected object (anchor, default visibility, size).
- **Bottom:** Timeline (frame thumbnails) + playback controls.

### Timeline Interaction Details
- Frame thumbnails show the composited stage result (preferred) or the active object (fallback).
- Actions:
  - Click frame → select frame.
  - Drag frame thumbnails → reorder frames.
  - `+ Frame` → append blank frame (copies transforms; pixels optional).
  - `Duplicate Frame` → clones the current frame (pixels + transforms).
  - `Delete Frame` → removes frame (with guard: must keep ≥ 1).
  - Duration editor per frame: dropdown (50/100/150/200/300ms) + custom input.

### Playback Interaction Details
- Controls: Play/Pause, Loop toggle, FPS indicator (derived from per-frame durations).
- Keyboard:
  - Space: Play/Pause
  - , / . : Prev/Next frame
  - Shift + , / . : Jump -5/+5 frames
- During playback, the stage preview updates at the frame schedule; editing is locked or allowed with “live edit” mode (configurable).

### Onion Skin / Afterimage
- Toggles:
  - Onion-skin **Previous** on/off + alpha slider
  - Onion-skin **Next** on/off + alpha slider
- Behavior:
  - Previous frame is tinted (e.g., blue) and rendered behind current.
  - Next frame is tinted (e.g., red) and rendered behind current.
  - Onion skin applies to the **composited** stage by default (so you can judge motion across all objects).
  - Option: “Active object only” onion skin for cleaner pixel editing.

### Reference Images
- Reuse existing reference image pipeline:
  - Load/Clear reference image
  - Ref alpha slider
  - Alt+wheel scale, Alt+drag pan
- In Move Animation mode, references can include:
  - Imported concept art / mockups
  - Screenshots of classic move animations
  - Optional: “Use attacker sprite as reference” and “Use defender sprite as reference” (auto-loaded from selected monsters)

### Draggable Object/Layer Positioning (core requirement)
- In the stage preview:
  - Click object bounds → selects the object.
  - Drag → updates the object transform for the current frame (`x`, `y`).
- Fine controls:
  - Arrow keys move selected object by 1 px (Shift = 5 px).
  - “Snap to sprite grid” option when anchored to attacker/defender.
- Per-frame vs. global:
  - Default: transform edits apply to the **current frame** only.
  - Option: “Apply to all frames” for quickly repositioning an object track.

## Data Model & File Format

### Storage Layout (proposed)
- Metadata: `data/move_animations/{animationId}.json`
- Images: `sprites/move_animations/{animationId}/{objectId}/frame_{NNN}.png`

This mirrors existing conventions: JSON in `data/`, pixels in an asset directory.

### JSON Schema (v1)
```json
{
  "version": "1.0.0",
  "id": "ember_strike",
  "name": "Ember Strike",
  "canvas": { "w": 32, "h": 32 },
  "frames": [
    { "durationMs": 100 },
    { "durationMs": 100 }
  ],
  "objects": [
    {
      "id": "proj",
      "name": "Projectile",
      "anchor": "attacker",
      "size": { "w": 32, "h": 32 },
      "frames": [
        { "image": "proj/frame_000.png", "x": 16, "y": 16, "visible": true },
        { "image": "proj/frame_001.png", "x": 20, "y": 14, "visible": true }
      ]
    }
  ],
  "preview": {
    "attackerSprite": "sprites/SomeMon_front.png",
    "defenderSprite": "sprites/SomeMon_back.png",
    "background": "backgrounds/arena.png"
  }
}
```

Notes:
- `frames[]` defines the global timeline length and default timing.
- Each object has its own `frames[]` aligned by index with the global `frames[]`.
- `image` paths are stored relative to `sprites/move_animations/{animationId}/`.
- `preview` is editor-only; runtime should ignore it.
- The editor/runtime should preserve unknown JSON fields to allow future extensions without migrations.

### Validation Rules
- `id` must be unique and file-safe (lowercase + underscores recommended).
- Must have ≥ 1 global frame; durations must be positive integers.
- For every object and every frame index, the referenced image must exist (or the editor generates a placeholder).
- Transform values must be integers; clamp or warn when values exceed reasonable bounds.

## Integration Points

### Pixel Art Editor
- Add `edit_mode == "move"` and a corresponding startup dialog option.
- New modules (proposed):
  - `src/editor/move_animation_state.py` (data structures)
  - `src/editor/move_animation_io.py` (load/save JSON + PNG)
  - `src/editor/move_animation_ui.py` (timeline + object panel rendering)
- Reuse existing systems:
  - `DialogManager` for file lists and text prompts
  - `UndoRedoManager` for frame/object edits
  - Reference image implementation already present in `src/editor/pixle_art_editor.py`

### Battle Simulator Runtime
- Add a `MoveAnimationPlayer` responsible for:
  - Loading `data/move_animations/{animationId}.json`
  - Loading required PNGs lazily or preloading per play
  - Advancing frames by `durationMs`
  - Rendering objects with their anchors + transforms on the battle screen
- Anchor interpretation (v1):
  - `attacker` / `defender`: base position is the top-left of the scaled sprite; `(x, y)` is an offset in **sprite-local pixels** multiplied by `BATTLE_SPRITE_SCALE_FACTOR`.
  - `screen`: `(x, y)` is in battle screen pixels.

### Move Definitions
- Extend `data/moves.json` entries with optional `animationId`.
- If missing/unknown, runtime skips animation (no crash; log a warning in debug).

## Export Formats
- **Runtime export (required):** JSON + per-frame PNGs (format above).
- **Review exports (optional but valuable):**
  - Flattened sprite sheet per object (`.png`) with row-major frame packing.
  - Flattened composite sprite sheet (stage only) for quick visual QA.
  - Animated GIF for quick sharing/review.

## Automated Unit Testing Expectations (for planned tooling logic)
The editor is UI-heavy, but the **state transitions and serialization** should be kept in pure/testable modules.

Minimum unit tests to add when implementing this design:
- **Frame list operations**
  - Insert/delete/duplicate/reorder frames maintains correct indices.
  - Duplicate clones pixel references + transform values correctly.
  - Duration edits clamp/validate correctly.
- **Onion-skin selection logic**
  - Given current frame index and toggles, the correct previous/next indices are chosen (with edge handling at 0 / last).
  - “Active object only” mode selects the correct surfaces.
- **Drag transform application**
  - Drag delta updates integer `x/y` correctly.
  - “Apply to all frames” updates all transforms for that object.
  - Anchor-specific coordinate conversion is correct (`attacker`/`defender` scaled vs `screen` absolute).
- **Serialization**
  - Load → save roundtrip preserves unknown fields and does not reorder frames/objects unexpectedly.
  - Missing image paths result in placeholders (or explicit validation errors) deterministically.

## Future Enhancements (informed by pixel-art tooling research)
- Indexed palette mode for move assets (16 colors + transparent) with “colors used” meter.
- Timeline tags (startup/loop/end) similar to Aseprite for reusable move segments.
- Palette cycling helper for classic fire/water shimmer effects.
- Simple procedural helpers: screen shake track, flash overlay track, and affine “squash/stretch” transforms for Gen-3-style motion.

