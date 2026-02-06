# Getting Started

This project ships multiple entrypoints (menu + standalone tools). Use a virtual environment if you want isolation.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Launch options

- Main menu:
  ```bash
  python main_menu.py
  ```
- Battle simulator (standalone):
  ```bash
  python battle_simulator.py
  ```
- Pixel art editor (standalone):
  ```bash
  python pixle_art_editor.py
  ```
- Overworld (standalone):
  ```bash
  python -m src.overworld.overworld
  ```
- Map editor (standalone):
  ```bash
  python -m src.overworld.map_editor
  ```
- World view (standalone):
  ```bash
  python -m src.overworld.world_view
  ```

## Files you may edit

- `data/` for game data (monsters, moves, type chart)
- `data/maps/` for map JSON files
- `data/tilesets/` for tileset JSON files
- `sprites/`, `tiles/`, `backgrounds/`, `sounds/`, `songs/` for assets

If an action opens the pixel art editor, it launches `pixle_art_editor.py` in a separate process.

## Running tests (non-Conda)

Use the repository-local test workflow:

```bash
./scripts/bootstrap_test_env.sh
./scripts/run_tests.sh
```

`./scripts/run_tests.sh` is the canonical test command.
To use an existing interpreter (for example, a Conda env), set:

```bash
POKECLONE_TEST_PYTHON=/path/to/python ./scripts/run_tests.sh
```

If `.venv` was created with a Python that cannot load `pygame.mixer`, rebuild with Python 3.12:

```bash
POKECLONE_BOOTSTRAP_PYTHON=$(command -v python3.12) ./scripts/bootstrap_test_env.sh --recreate
./scripts/run_tests.sh
```
