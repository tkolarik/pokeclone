import os
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_declares_editable_package_and_scripts():
    pyproject_path = REPO_ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

    assert data["project"]["name"] == "pokeclone"
    assert "pygame>=2.0.0" in data["project"]["dependencies"]
    scripts = data["project"]["scripts"]
    assert scripts["pokeclone-main-menu"] == "src.ui.main_menu:main"
    assert scripts["pokeclone-battle"] == "src.battle.battle_simulator:main"
    assert scripts["pokeclone-pixel-editor"] == "src.editor.pixle_art_editor:main"


def test_src_imports_resolve_outside_repo_via_editable_install():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [sys.executable, "-c", "import src.core.config"],
            cwd=tmpdir,
            env=env,
            capture_output=True,
            text=True,
        )

    assert result.returncode == 0, (
        "Importing 'src' from outside the repository failed. "
        "Ensure editable install is active (`pip install -e .`).\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
