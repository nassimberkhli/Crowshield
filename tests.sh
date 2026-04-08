#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
DOCKER_IMAGE="python:3.13-slim"

echo "[INFO] Starting test workflow..."
echo "[INFO] Preparing execution environment..."
"$PROJECT_DIR/create_venv.sh"
echo "[INFO] Environment is ready."

run_local_tests() {
  echo "[INFO] Running tests in the local virtual environment..."
  . "$PROJECT_DIR/.venv/bin/activate"
  export PYTHONPATH="$PROJECT_DIR"

  python tests/test_simulation.py
  python tests/test_contract.py
  python tests/test_security.py
}

run_docker_tests() {
  echo "[INFO] Running tests in Docker fallback mode..."
  docker run --rm \
    -v "$PROJECT_DIR:/app" \
    -w /app \
    "$DOCKER_IMAGE" \
    bash -lc '
      set -euo pipefail
      python -m pip install --no-cache-dir --upgrade pip >/dev/null
      python -m pip install --no-cache-dir smartpy-tezos >/dev/null
      export PYTHONPATH=/app
      python tests/test_simulation.py
      python tests/test_contract.py
      python tests/test_security.py
    '
}

if [ -f "$PROJECT_DIR/.venv/.mode" ] && grep -qx "docker-fallback" "$PROJECT_DIR/.venv/.mode"; then
  run_docker_tests
  echo "[INFO] All tests finished successfully."
  exit 0
fi

if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
  run_local_tests
  echo "[INFO] All tests finished successfully."
  exit 0
fi

echo "[ERROR] No usable Python virtual environment was found." >&2
exit 1
