# Pixel Art Editor

Entry point: `python pixle_art_editor.py`

This tool is a single app with three edit modes: **Monster**, **Background**, and **Tiles**. The UI is primarily button-driven with a small set of keyboard shortcuts.

## Startup dialogs

### Choose Edit Mode

Buttons:
- Monster
- Tiles
- Background

### Background action (only when Background is selected)

Buttons:
- New
- Edit Existing

### Text input dialogs

Used for naming tiles, tilesets, NPCs, and backgrounds.

Keyboard:
- Enter: confirm
- Esc: cancel
- Backspace: delete character

Buttons vary by dialog:
- Create / Cancel
- Save / Cancel

### File list dialogs

Used for loading backgrounds, tilesets, and reference images.

Keyboard:
- Up / Down: move selection
- Enter: load selected
- Esc: cancel

Mouse:
- Left click a file row: select
- Left click Load/Cancel: confirm or cancel
- Scroll wheel: scroll file list
- Drag scrollbar thumb when present
- Click quick directory buttons (when provided)

## Global buttons (all modes)

These buttons appear in a vertical stack on the right.

- Clear: clears the active canvas
- Color Picker: open the OS color picker (Tk)
- Eraser: toggle erase mode for draw tool
- Fill: switch to fill tool
- Select: toggle selection mode
- Copy: copy selection (only works when a selection is active)
- Paste: switch to paste tool (only when a copy buffer exists)
- Hist Prev / Hist Next: cycle clipboard history
- Fav Clip: toggle favorite on current clipboard item (persisted on disk)
- Mirror: mirror the active selection horizontally
- Rotate: rotate the active selection 90 degrees clockwise
- Cancel Paste: exit paste mode without placing
- Undo
- Redo

## Keyboard shortcuts (global)

- Ctrl/Cmd+Z: Undo
- Ctrl/Cmd+Y: Redo
- Ctrl/Cmd+C: Copy selection (only in Select mode)
- Ctrl/Cmd+V: Paste (uses the current copy buffer)
- Ctrl/Cmd+Shift+V: advance clipboard history and paste
- Ctrl/Cmd+[ / Ctrl/Cmd+]: previous/next clipboard history item
- Ctrl/Cmd+F: toggle favorite for active clipboard entry
- Ctrl/Cmd+M: Mirror selection
- Ctrl/Cmd+R: Rotate selection
- Esc: cancel paste mode or exit selection mode

## Mouse input (global)

- Left click: interact with buttons, palette, and canvas
- Left drag: draw with the active tool
- Mouse wheel over palette: scroll palette pages
- Click palette up/down arrows: scroll palette pages

## Monster mode

### Mode-specific buttons

- Save Sprites
- Prev Monster
- Next Monster
- Switch Sprite (front/back)
- Load Ref Img
- Clear Ref Img
- Import Ref

### Canvas behavior

- Two sprite canvases are shown (front and back). The active one is highlighted.
- Select mode works on the active sprite canvas.

### Reference image controls

- Alt + mouse wheel over the active sprite canvas: scale reference image
- Alt + left drag over the active sprite canvas: pan reference image
- Ref Alpha slider: adjust reference image opacity
- Subj Alpha slider: adjust the edited sprite opacity (monster mode only)

## Background mode

### Mode-specific buttons

- Save BG
- Load BG
- Zoom In
- Zoom Out
- Brush +
- Brush -
- Prev BG
- Next BG
- Pan Up
- Pan Down
- Pan Left
- Pan Right

### Canvas behavior

- The background canvas supports panning and zooming.

### Keyboard controls

- Arrow keys: pan the background

### Mouse controls

- Middle mouse drag: pan the background

## Tiles mode

Tiles mode has two sub-modes: **Edit Tiles** and **Edit NPCs**.

### Switch buttons (always visible in Tiles mode)

- Edit Tiles
- Edit NPCs

### Edit Tiles buttons

- Save Tile
- Save Tileset
- Load Tileset
- Load Ref Img
- Clear Ref Img
- Import Ref
- New Tile
- New Tileset
- Toggle Walk (walkable/blocked)
- Brush +
- Brush -
- Prev Tile
- Next Tile
- Prev Frame
- Next Frame
- Add Frame

### Edit NPCs buttons

- Save Tileset
- Save NPC
- Load Tileset
- Load Ref Img
- Clear Ref Img
- Import Ref
- Edit Player
- New NPC
- Prev NPC
- Next NPC
- Prev Frame
- Next Frame
- Add Frame

### Tile panel (right side)

- Tile list: click a tile row to select it
- Frame tray: click a frame preview to edit that frame
- Scroll tiles: click near top or bottom margins of the list
- Scroll frames: click near top or bottom of the frame tray

### NPC panel (right side)

- NPC list: click a row to select an NPC
- State tray: click a state name to select it
- Angle tray: click a facing angle to select it
- Scroll NPC list: click near top or bottom margins
- Scroll states/angles: click near top or bottom of each tray

## Selection workflow

1. Click Select to enter selection mode.
2. Click-drag on a canvas to define a rectangular selection.
3. Use Copy, Paste, Mirror, or Rotate.
4. Click Select again to exit selection mode.

Notes:
- Clicking outside the canvas cancels selection in progress.
- Copy/Paste/Mirror/Rotate only operate on the active canvas.
- Paste mode supports repeated placement until cancelled (Esc or Cancel Paste).
- A live paste preview is shown under the cursor while paste mode is active.

## Brush size display

The Brush slider is currently **display-only**. Use Brush + / Brush - buttons to change size.
