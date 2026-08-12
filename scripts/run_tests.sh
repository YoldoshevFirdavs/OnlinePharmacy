#!/usr/bin/env bash
set -euo pipefail

PY_VER="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$PY_VER" != "3.10" ]]; then
  echo "Error: tests must run with Python 3.10, current: $PY_VER"
  exit 1
fi

python --version
python -m pytest -q "$@"

