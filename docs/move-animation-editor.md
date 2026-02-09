# Move Animation Editor

Entry points:
- `python move_animation_editor.py`
- `python -m src.editor.move_animation_editor`

The Move Animation Editor is for authoring battle move animation assets in:
- `data/move_animations/<animation_id>.json`
- `sprites/move_animations/<animation_id>/<object_id>/frame_NNN.png`

## Startup workflow

On launch, the editor opens the first available move animation file. If none exist, it creates `new_animation`.

## Layout

- `Stage Preview` (left): composited preview with attacker/defender anchors.
- `Object Canvas` (center): pixel editing for the selected object and frame.
- `Objects` panel (right): select object/layer and inspect frame transform.
- `Timeline` (bottom): frame strip with click-to-select and drag-to-reorder.
- `Top controls`: save/load, frame/object actions, playback, onion-skin toggles, anchor/visibility, duration, color/reference controls.

## Core controls

### Timeline and playback

- `Space`: Play/Pause.
- `,` and `.`: previous/next frame.
- `Shift + ,` and `Shift + .`: jump -5/+5 frames.
- `N`: add frame.
- `D`: duplicate frame.
- `Delete`/`Backspace`: delete frame (keeps at least one frame).
- Drag timeline thumbnails to reorder frames.

### Object/layer editing

- Click object rows in the right panel to select active object.
- Drag object bounds in stage preview to update per-frame `x/y` transforms.
- Arrow keys: nudge selected object by `1px` (`Shift` = `5px`).
- `Apply All` toggle applies drag/nudge transforms to every frame of the selected object.
- `Anchor` button cycles `attacker -> defender -> screen`.
- `Visible` toggles current-frame visibility for the selected object.

### Onion skin

- `Onion Prev` and `Onion Next` buttons toggle previous/next ghost frames.
- `Active Only` restricts onion-skin rendering to the selected object.

### Drawing and reference image

- Left mouse in object canvas: paint with current color.
- Right mouse in object canvas: erase to transparent.
- `Color` button or `C` key: choose paint color.
- `Load Ref` / `Clear Ref` or `R` key: manage reference image.
- `Alt + Mouse Wheel` on object canvas: scale reference image.
- `Alt + Drag` on object canvas: pan reference image.

### Save/load

- `Ctrl/Cmd + S`: save JSON and all object frame PNGs.
- `Ctrl/Cmd + O`: open existing animation (in-app file dialog).
- `Ctrl/Cmd + N`: create new animation (`new_animation`, `new_animation_2`, ...).

## In-app dialogs (Tk-free, macOS-safe)

The Move Animation Editor avoids Tk dialogs to prevent SDL/Tk crashes on macOS, and uses in-app Pygame dialogs instead.

- `Open`: shows a selectable file list from `data/move_animations/*.json`.
- `Load Ref`: shows a selectable file list discovered from:
  - `references/`
  - `sprites/`
  - `backgrounds/`
  - `~/Desktop`
  - `~/Downloads`
- Dialog controls:
  - `Up/Down`: move selection
  - `Enter`: load selected file
  - `Esc`: cancel
  - Mouse wheel / scrollbar drag: scroll

## Data format notes

- Global timeline is defined by `frames[]` with `durationMs`.
- Each object has `frames[]` aligned to timeline indices.
- Object frame transforms are integer pixel values (`x`, `y`) with `visible`, `flipX`, `flipY`.
- The loader/saver preserves unknown JSON fields so future schema extensions survive round-trips.
