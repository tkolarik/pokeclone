#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_PYTHON="${ROOT_DIR}/.venv/bin/python"
TEST_PYTHON="${POKECLONE_TEST_PYTHON:-${DEFAULT_PYTHON}}"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: ./scripts/run_tests.sh [pytest-args...]

Runs the project's automated test suite.

By default it uses:
  ./.venv/bin/python

You can override interpreter path:
  POKECLONE_TEST_PYTHON=/path/to/python ./scripts/run_tests.sh

If .venv is missing and you are not overriding interpreter, run:
  ./scripts/bootstrap_test_env.sh
EOF
  exit 0
fi

if [[ ! -x "${TEST_PYTHON}" ]]; then
  echo "Error: python interpreter not found at ${TEST_PYTHON}"
  if [[ "${TEST_PYTHON}" == "${DEFAULT_PYTHON}" ]]; then
    echo "Run: ./scripts/bootstrap_test_env.sh"
  fi
  exit 1
fi

if ! "${TEST_PYTHON}" -m pytest --version >/dev/null 2>&1; then
  echo "Error: pytest is not installed for interpreter ${TEST_PYTHON}."
  if [[ "${TEST_PYTHON}" == "${DEFAULT_PYTHON}" ]]; then
    echo "Run: ./scripts/bootstrap_test_env.sh"
  else
    echo "Install pytest in that environment or use ./scripts/bootstrap_test_env.sh"
  fi
  exit 1
fi

# Preflight for environments where pygame is installed without mixer support.
if ! "${TEST_PYTHON}" -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('pygame.mixer') else 1)" >/dev/null 2>&1; then
  echo "Error: pygame.mixer is unavailable for interpreter ${TEST_PYTHON}."
  echo "Battle tests require mixer support."
  if [[ "${TEST_PYTHON}" == "${DEFAULT_PYTHON}" ]]; then
    echo "Try rebuilding .venv with Python 3.12:"
    echo "  POKECLONE_BOOTSTRAP_PYTHON=$(command -v python3.12 || echo /path/to/python3.12) ./scripts/bootstrap_test_env.sh --recreate"
  fi
  exit 1
fi

if ! "${TEST_PYTHON}" -c "import os, tempfile; os.chdir(tempfile.mkdtemp()); import src.core.config" >/dev/null 2>&1; then
  echo "Installing project in editable mode for import resolution checks..."
  if ! "${TEST_PYTHON}" -m pip install --no-build-isolation --no-deps -e "${ROOT_DIR}"; then
    echo "Error: editable install failed for ${TEST_PYTHON}."
    echo "Run manually: ${TEST_PYTHON} -m pip install --no-build-isolation --no-deps -e ${ROOT_DIR}"
    exit 1
  fi
fi

export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}"
export POKECLONE_DISABLE_TK="${POKECLONE_DISABLE_TK:-1}"

cd "${ROOT_DIR}"
"${TEST_PYTHON}" -m pytest tests "$@"
