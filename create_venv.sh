#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON_BIN=""

find_python() {
  for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      "$candidate" - <<'PY' >/dev/null 2>&1
import sys
ok = (3, 10) <= sys.version_info[:2] <= (3, 14)
raise SystemExit(0 if ok else 1)
PY
      if [ $? -eq 0 ]; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

if PYTHON_BIN="$(find_python)"; then
  echo "[INFO] Compatible Python detected: $PYTHON_BIN"

  if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "[INFO] Creating local virtual environment..."
    "$PYTHON_BIN" -m venv "$PROJECT_DIR/.venv"
  else
    echo "[INFO] Reusing existing local virtual environment."
  fi

  . "$PROJECT_DIR/.venv/bin/activate"

  echo "[INFO] Upgrading pip..."
  python -m pip install --upgrade pip

  echo "[INFO] Installing or upgrading project dependencies..."
  python -m pip install --upgrade smartpy-tezos

  rm -f "$PROJECT_DIR/.venv/.mode"
  echo "[INFO] Local virtual environment is ready."
  exit 0
fi

if command -v docker >/dev/null 2>&1; then
  mkdir -p "$PROJECT_DIR/.venv"
  printf '%s\n' "docker-fallback" > "$PROJECT_DIR/.venv/.mode"
  echo "[WARNING] No compatible local Python version found. Docker fallback mode enabled."
  exit 0
fi

echo "[ERROR] No compatible Python version was found and Docker is not installed." >&2
echo "[ERROR] Install Python 3.10 to 3.14, or install Docker, then run again." >&2
exit 1
