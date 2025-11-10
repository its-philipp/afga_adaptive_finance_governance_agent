#!/bin/bash
# Bootstrap Databricks workspace with notebooks and Unity Catalog

set -e

DATABRICKS_WORKSPACE_URL="${DATABRICKS_WORKSPACE_URL:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
DATABRICKS_DIR="${PROJECT_ROOT}/azure_extension/databricks"

if [ -z "$DATABRICKS_WORKSPACE_URL" ]; then
    echo "Error: DATABRICKS_WORKSPACE_URL not set"
    exit 1
fi

echo "Bootstraping Databricks workspace: ${DATABRICKS_WORKSPACE_URL}"

# Import notebooks
echo "Importing notebooks..."
databricks workspace import "${DATABRICKS_DIR}/notebooks/01_ingest_raw.py" /notebooks/01_ingest_raw --language PYTHON
databricks workspace import "${DATABRICKS_DIR}/notebooks/02_validate_transform.py" /notebooks/02_validate_transform --language PYTHON
databricks workspace import "${DATABRICKS_DIR}/notebooks/03_chunk_embed_register.py" /notebooks/03_chunk_embed_register --language PYTHON

# Setup Unity Catalog (run SQL commands)
echo "Setting up Unity Catalog..."
# Note: These require manual execution or databricks CLI SQL command (if available)
echo "Please run Unity Catalog SQL scripts manually:"
echo "  - ${DATABRICKS_DIR}/unity_catalog/catalogs.sql"
echo "  - ${DATABRICKS_DIR}/unity_catalog/schemas.sql"
echo "  - ${DATABRICKS_DIR}/unity_catalog/grants.sql"

# Create job (requires manual JSON update with actual values)
echo "Creating Databricks job..."
echo "Please update ${DATABRICKS_DIR}/jobs/pipeline_job.json with actual values, then run:"
echo "  databricks jobs create --json-file ${DATABRICKS_DIR}/jobs/pipeline_job.json"

echo "✅ Databricks bootstrap completed (partial - manual steps required)"

