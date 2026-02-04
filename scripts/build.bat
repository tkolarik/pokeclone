@echo off
setlocal

set ROOT_DIR=%~dp0\..
for %%I in ("%ROOT_DIR%") do set "ROOT_DIR=%%~fI"
cd /d "%ROOT_DIR%"

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo PyInstaller not installed. Install with: pip install -r requirements-dev.txt
  exit /b 1
)

set NAME=PokeClone
set ENTRY=main_menu.py

python -m PyInstaller --noconfirm --clean --name "%NAME%" --distpath dist --workpath build --specpath build ^
  --collect-all pygame ^
  --hidden-import src.overworld.overworld ^
  --hidden-import src.battle.battle_simulator ^
  --hidden-import src.editor.pixle_art_editor ^
  --hidden-import src.editor.monster_editor ^
  --hidden-import src.overworld.map_editor ^
  --hidden-import src.overworld.world_view ^
  --add-data "%ROOT_DIR%\data;data" ^
  --add-data "%ROOT_DIR%\backgrounds;backgrounds" ^
  --add-data "%ROOT_DIR%\songs;songs" ^
  --add-data "%ROOT_DIR%\sounds;sounds" ^
  --add-data "%ROOT_DIR%\sprites;sprites" ^
  --add-data "%ROOT_DIR%\tiles;tiles" ^
  --add-data "%ROOT_DIR%\references;references" ^
  "%ENTRY%"

echo Build complete. Run dist\%NAME%\%NAME%.exe
