#!/bin/bash
# Launch AFGA backend using Databricks overrides.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT/.."

if [ ! -d ".venv" ]; then
  echo "[run_backend_databricks] Python venv not found. Run 'uv sync' first." >&2
  exit 1
fi

source .venv/bin/activate

export PYTHONPATH="$PROJECT_ROOT/src_overrides/src:$PYTHONPATH"
export MEMORY_BACKEND="databricks"

uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
