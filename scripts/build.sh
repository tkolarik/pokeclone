#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! python3 -m PyInstaller --version >/dev/null 2>&1; then
  echo "PyInstaller not installed. Install with: python3 -m pip install -r requirements-dev.txt"
  exit 1
fi

NAME="PokeClone"
ENTRY="main_menu.py"

PYI_ARGS=(
  "--noconfirm"
  "--clean"
  "--name" "$NAME"
  "--distpath" "dist"
  "--workpath" "build"
  "--specpath" "build"
  "--collect-all" "pygame"
  "--hidden-import" "src.overworld.overworld"
  "--hidden-import" "src.battle.battle_simulator"
  "--hidden-import" "src.editor.pixle_art_editor"
  "--hidden-import" "src.editor.monster_editor"
  "--hidden-import" "src.overworld.map_editor"
  "--hidden-import" "src.overworld.world_view"
)

add_data() { PYI_ARGS+=("--add-data" "$1:$2"); }

add_data "${ROOT_DIR}/data" "data"
add_data "${ROOT_DIR}/backgrounds" "backgrounds"
add_data "${ROOT_DIR}/songs" "songs"
add_data "${ROOT_DIR}/sounds" "sounds"
add_data "${ROOT_DIR}/sprites" "sprites"
add_data "${ROOT_DIR}/tiles" "tiles"
add_data "${ROOT_DIR}/references" "references"

python3 -m PyInstaller "${PYI_ARGS[@]}" "$ENTRY"

echo "Build complete. Run ./dist/${NAME}/${NAME} (or the platform-specific binary)."
