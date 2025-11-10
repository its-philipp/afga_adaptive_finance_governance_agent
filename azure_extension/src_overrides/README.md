# AFGA Databricks Overrides

These modules shadow the default `src/` implementations when the backend is launched with
`PYTHONPATH=azure_extension/src_overrides/src`. They add Phase 2 integrations without touching the
local demo codebase.

## Modules

- `core/config.py` – extends settings with Databricks/ADLS fields (`MEMORY_BACKEND`, job ID, etc.).
- `agents/orchestrator.py` – sends processed transactions and HITL feedback to the lakehouse.
- `services/databricks_lakehouse.py` – uploads JSON artifacts to ADLS Gen2 and triggers Databricks jobs.

To activate them, run `./azure_extension/scripts/run_backend_databricks.sh` (or export the
`PYTHONPATH` manually). When `MEMORY_BACKEND=databricks`, the orchestrator replicates data to Azure
while retaining SQLite for the interactive UI.
