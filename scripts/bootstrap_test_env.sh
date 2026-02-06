#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
BOOTSTRAP_PYTHON="${POKECLONE_BOOTSTRAP_PYTHON:-}"
RECREATE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --recreate)
      RECREATE=1
      shift
      ;;
    --help|-h)
      cat <<'EOF'
Usage: ./scripts/bootstrap_test_env.sh [--recreate]

Creates/updates a local .venv and installs dependencies required to run tests.

Environment override:
  POKECLONE_BOOTSTRAP_PYTHON=/path/to/python ./scripts/bootstrap_test_env.sh
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Run --help for usage."
      exit 1
      ;;
  esac
done

if [[ -z "${BOOTSTRAP_PYTHON}" ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    BOOTSTRAP_PYTHON="$(command -v python3.12)"
  else
    BOOTSTRAP_PYTHON="$(command -v python3)"
  fi
fi

if [[ ! -x "${BOOTSTRAP_PYTHON}" ]]; then
  echo "Error: bootstrap python not found at ${BOOTSTRAP_PYTHON}"
  exit 1
fi

if [[ "${RECREATE}" -eq 1 && -d "${VENV_DIR}" ]]; then
  echo "Recreating virtual environment at ${VENV_DIR}"
  rm -rf "${VENV_DIR}"
fi

if [[ -d "${VENV_DIR}" && -x "${VENV_DIR}/bin/python" ]]; then
  VENV_MM="$("${VENV_DIR}/bin/python" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  BOOTSTRAP_MM="$("${BOOTSTRAP_PYTHON}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "${VENV_MM}" != "${BOOTSTRAP_MM}" ]]; then
    echo "Existing .venv is Python ${VENV_MM}, requested bootstrap interpreter is Python ${BOOTSTRAP_MM}."
    echo "Run with --recreate to rebuild .venv with ${BOOTSTRAP_PYTHON}."
    exit 1
  fi
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  echo "Creating virtual environment at ${VENV_DIR}"
  "${BOOTSTRAP_PYTHON}" -m venv "${VENV_DIR}"
fi

echo "Installing dependencies from requirements-dev.txt"
if ! "${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/requirements-dev.txt"; then
  echo "Dependency installation failed."
  echo "If you are offline, connect to the internet or use a pre-populated package cache/index."
  exit 1
fi

echo "Installing project package in editable mode"
if ! "${VENV_DIR}/bin/python" -m pip install --no-build-isolation --no-deps -e "${ROOT_DIR}"; then
  echo "Editable install failed."
  exit 1
fi

echo "Bootstrap complete."
echo "Run tests with: ./scripts/run_tests.sh"
