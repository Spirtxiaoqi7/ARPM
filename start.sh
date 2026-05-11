#!/usr/bin/env sh
set -eu

APP_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
export ARPM_RUNTIME_DIR="${ARPM_RUNTIME_DIR:-$APP_ROOT/runtime/arpm-app}"
export ARPM_MODEL_ROOT="${ARPM_MODEL_ROOT:-$APP_ROOT/assets/models}"
export PYTHONNOUSERSITE=1

if [ -x "$APP_ROOT/.venv/bin/python" ]; then
  PYTHON_EXE="$APP_ROOT/.venv/bin/python"
else
  PYTHON_EXE="${PYTHON_EXE:-python}"
fi

cd "$APP_ROOT/backend"
exec "$PYTHON_EXE" app.py
