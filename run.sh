#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

echo "[INFO] Preparing execution environment..."
"$PROJECT_DIR/create_venv.sh"
echo "[INFO] Environment is ready."

if [ -f "$PROJECT_DIR/.venv/.mode" ] && grep -qx "docker-fallback" "$PROJECT_DIR/.venv/.mode"; then
  echo "[INFO] Docker fallback mode detected."
  echo "[INFO] Interactive manual simulation is not started automatically in Docker fallback mode."
  echo "[INFO] Install a compatible local Python version to use the interactive simulator."
  exit 0
fi

if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
  . "$PROJECT_DIR/.venv/bin/activate"
  export PYTHONPATH="$PROJECT_DIR"
  echo "[INFO] Starting interactive manual simulation..."
  python contracts/main.py
  exit 0
fi

echo "[ERROR] No usable Python virtual environment was found." >&2
exit 1
