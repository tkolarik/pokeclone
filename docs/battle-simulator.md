# Battle Simulator

Entry point: `python battle_simulator.py`

## Creature select screen

### Buttons

Each monster is a button with its name. Clicking a monster selects it.

### Keyboard controls

- Arrow keys: move the selection highlight within the grid
- Enter or Space: pick the highlighted monster
- ] (right bracket): next page
- [ (left bracket): previous page

Notes:
- When you are at the edge of the grid, the UI shows a hint telling you to use [ or ] for paging.

### Mouse controls

- Left click a monster button to select it.

## Battle screen

### Buttons

- One button per move (the active creature's move list)

### Mouse controls

- Left click a move to execute it.

### Visual hints

- Type labels are shown under both HP bars.
- Move buttons get a green border for super-effective hits and red for not-very-effective hits.

### Audio

- Background music plays from `songs/` when audio is available.
- Battle events trigger SFX from `sounds/events/`.
- If a move-specific file exists under `sounds/moves/<Move Name>.mp3|.wav`, it is used first.

## End-of-battle screen

### Buttons

- New Battle
- Quit

### Mouse controls

- Left click one of the buttons to continue or exit.
