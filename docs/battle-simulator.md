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

There are no battle-specific keyboard shortcuts in the current implementation.

## End-of-battle screen

### Buttons

- New Battle
- Quit

### Mouse controls

- Left click one of the buttons to continue or exit.
