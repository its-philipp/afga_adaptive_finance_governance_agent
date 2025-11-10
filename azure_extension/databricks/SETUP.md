# Databricks Setup Guide

## Overview

This guide covers setting up Azure Databricks for the Adaptive Finance Governance AFGA. Databricks provides the governed data platform with Unity Catalog for enterprise-grade data management.

## Prerequisites

- Azure subscription with permissions to create Databricks workspace
- Databricks CLI installed: `pip install databricks-cli`
- Azure CLI logged in: `az login`

## Option 1: Manual Setup via Azure Portal (Recommended for First Time)

### Step 1: Create Databricks Workspace

1. Go to Azure Portal: https://portal.azure.com
2. Search for "Azure Databricks"
3. Click "+ Create"
4. Configure:
   - **Resource Group**: `afga-dev-rg` (or your chosen RG)
   - **Workspace Name**: `databricks-afga-dev`
   - **Region**: Same as storage + AKS (e.g., West Europe)
   - **Pricing Tier**: Premium (Unity Catalog required)
5. Click "Review + Create" → "Create"
6. Wait for deployment (~3-5 minutes)

### Step 2: Get Workspace URL

After creation:
1. Go to the Databricks workspace resource
2. Click "Launch Workspace"
3. Copy the URL (e.g., `https://adb-123456789.azuredatabricks.net`)
4. Save this URL - you'll need it for configuration

### Step 3: Create Access Token

1. In Databricks workspace, click your user profile (top right)
2. Go to "Settings" → "Developer" → "Access tokens"
3. Click "Generate new token"
4. Give it a name: "terraform-automation"
5. Set lifetime: 90 days (or as needed)
6. Click "Generate"
7. **Copy the token immediately** - you can't retrieve it later!

### Step 4: Configure Databricks CLI

```bash
databricks configure --token

# Enter when prompted:
# - Databricks Host: https://adb-123456789.azuredatabricks.net
# - Token: <your-token-from-step-3>
```

### Step 5: Upload Notebooks

```bash
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent/azure_extension

# Create a repo-friendly path in Databricks workspace
databricks workspace mkdirs /Repos/${USER}/afga/azure_extension/databricks/notebooks

# Upload notebooks (preserve repo structure for Jobs references)
databricks workspace import databricks/notebooks/01_ingest_raw.py \
  /Repos/${USER}/afga/azure_extension/databricks/notebooks/01_ingest_raw \
  --language PYTHON \
  --format SOURCE

databricks workspace import databricks/notebooks/02_validate_transform.py \
  /Repos/${USER}/afga/azure_extension/databricks/notebooks/02_validate_transform \
  --language PYTHON \
  --format SOURCE

databricks workspace import databricks/notebooks/03_chunk_embed_register.py \
  /Repos/${USER}/afga/azure_extension/databricks/notebooks/03_chunk_embed_register \
  --language PYTHON \
  --format SOURCE

echo "✅ Notebooks uploaded successfully!"
```

### Step 6: Create Unity Catalog

Unity Catalog requires metastore setup (one-time per region):

1. In Databricks workspace, go to "Data" → "Unity Catalog"
2. If no metastore exists, click "Create Metastore"
3. Follow the wizard to create metastore
4. Once metastore is linked, run the Unity Catalog SQL scripts

**Execute SQL scripts:**

1. Go to "SQL Editor" in Databricks
2. Copy contents from `databricks/unity_catalog/catalogs.sql`
3. Execute
4. Repeat for `schemas.sql` and `grants.sql`

### Step 7: Create Databricks Job

1. Go to "Workflows" → "Jobs" in Databricks
2. Click "Create Job"
3. Configure:
   - **Name**: `adaptive-finance-governance-rag-pipeline`
   - **Tasks**:
     - Task 1: `ingest_raw` → Notebook: `/Repos/<repo_path>/azure_extension/databricks/notebooks/01_ingest_raw`
     - Task 2: `validate_transform` → Notebook: `/Repos/<repo_path>/azure_extension/databricks/notebooks/02_validate_transform` (depends on Task 1)
     - Task 3: `chunk_embed_register` → Notebook: `/Repos/<repo_path>/azure_extension/databricks/notebooks/03_chunk_embed_register` (depends on Task 2)
     - (Set `<repo_path>` to match your Databricks Repo, e.g. `user@example.com/afga`)
   - **Parameters** (job-level or task-level):
     - `storage_account_name` = `<your-storage-account>`
     - `raw_container_name` = `raw-transactions`
     - `uc_catalog` = `afga_dev`
     - `bronze_schema` = `bronze`
     - `silver_schema` = `silver`
     - `gold_schema` = `gold`
     - `openai_api_key` = `<Databricks secret reference>`
     - `vector_index_name` = `finance_transactions_index`
4. Set schedule: Every 6 hours (or as needed)
5. Click "Create"
6. Note the Job ID (e.g., `12345`)

### Step 8: Store Databricks Secrets in Key Vault

```bash
# Store Databricks workspace URL
az keyvault secret set \
  --vault-name kv-dev-adaptive-finance-governance \
  --name databricks-workspace-url \
  --value "https://adb-your-workspace.azuredatabricks.net"

# Store Databricks job ID
az keyvault secret set \
  --vault-name kv-dev-adaptive-finance-governance \
  --name databricks-job-id \
  --value "12345"

# Store Databricks token (for API access)
az keyvault secret set \
  --vault-name kv-dev-adaptive-finance-governance \
  --name databricks-token \
  --value "your-databricks-token"
```

### Step 9: Configure Storage Access

Grant Databricks access to ADLS Gen2:

```bash
# Get Databricks workspace's managed identity
DATABRICKS_PRINCIPAL_ID=$(az databricks workspace show \
  --name databricks-afga-dev \
  --resource-group afga-dev-rg \
  --query managedResourceGroupId -o tsv)

# Grant Storage Blob Data Contributor
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee $DATABRICKS_PRINCIPAL_ID \
  --scope /subscriptions/<subscription-id>/resourceGroups/afga-dev-rg/providers/Microsoft.Storage/storageAccounts/<your-storage-account>
```

### Step 10: Install Backend Dependencies for Databricks Mode

The AFGA backend stays untouched for local demos. To enable Databricks replication, install the optional dependencies **inside your virtual environment**:

```bash
uv add azure-identity azure-storage-file-datalake databricks-sdk
```

This installs the Azure Data Lake SDK and the Databricks client used by the override modules under `azure_extension/src_overrides`.

### Step 11: Run AFGA Backend with Databricks Overrides

```bash
# From repository root
./azure_extension/scripts/run_backend_databricks.sh
```

This helper:

- Activates the virtual environment  
- Prepends `azure_extension/src_overrides/src` to `PYTHONPATH` so the Databricks-aware modules shadow the defaults  
- Sets `MEMORY_BACKEND=databricks` to activate lakehouse replication  
- Starts the FastAPI backend on port `8000`

**Environment variables required:**

```bash
export MEMORY_BACKEND=databricks
export AZURE_STORAGE_ACCOUNT=<your-storage-account>
export AZURE_STORAGE_KEY=<optional-if-no-managed-identity>
export DATABRICKS_WORKSPACE_URL=https://adb-xxxx.azuredatabricks.net
export DATABRICKS_JOB_ID=<job-id>               # integer
export DATABRICKS_TOKEN=<pat-token>             # or configure managed identity later
```

These can be supplied via `.env` or your deployment pipeline.

## Option 2: Terraform-Based Setup (Future)

We can add a Databricks Terraform module later for full automation. For now, manual setup is faster for learning and testing.

## Testing the Pipeline

### Test Individual Notebooks

1. Go to "Workspace" in Databricks
2. Navigate to `/notebooks/01_ingest_raw`
3. Attach to a cluster (create one if needed - smallest size for dev)
4. Set parameters:
   ```
   storage_account = <your-storage-account>
   raw_container = raw-transactions
   catalog_name = afga_dev
   bronze_schema = bronze
   ```
5. Click "Run All"
6. Verify output
7. Repeat for notebooks 02 and 03

### Test the Full Job

1. Go to "Workflows" → your job
2. Click "Run Now"
3. Monitor execution
4. Check outputs and Delta tables

## Integration with Cloud Mode

Once Databricks is configured, update your application config:

```bash
# .env or environment variables
CLOUD_MODE=databricks
DATABRICKS_WORKSPACE_URL=https://adb-your-workspace.azuredatabricks.net
DATABRICKS_JOB_ID=12345
DATABRICKS_TOKEN=your-token  # Or use managed identity in production
```

When a transaction document is uploaded via the API:
1. File → ADLS Gen2 (`raw-transactions` container)
2. Metadata JSON created (invoice metadata, exception flags)
3. **Databricks job triggered automatically** (if configured)
4. Job runs the 3-notebook pipeline
5. Data flows: Bronze → Silver → Gold
6. Embeddings stored in Unity Catalog

## Costs Estimate

### Databricks Workspace
- **Premium tier**: ~$0.55/DBU + compute costs
- **DBU (Databricks Unit)**: ~$0.55/hour for all-purpose compute
- **Optimization**:
  - Use job clusters (auto-terminate)
  - Don't keep all-purpose clusters running
  - Set auto-termination to 10-15 minutes
  - **Estimated cost**: ~$10-50/month for light dev usage

### How to Minimize Costs

1. **Only run when testing**: Start clusters when needed, terminate after
2. **Use smallest cluster size**: Single node for development
3. **Job clusters**: Use for scheduled pipelines (cheaper)
4. **Auto-termination**: Always enable with short timeout
5. **Monitor**: Check Azure Cost Management regularly

## No-Cost Alternative: Local Databricks Community Edition

For learning without costs:
1. Sign up at https://community.cloud.databricks.com (free)
2. Upload notebooks
3. Test SQL and PySpark logic
4. **Limitation**: No Unity Catalog, no Azure integration

Then move to Azure Databricks when ready for production testing.

## Next Steps

- [ ] Create Databricks workspace (when budget allows)
- [ ] Upload notebooks
- [ ] Create Unity Catalog structure
- [ ] Test pipeline manually
- [ ] Configure job with schedule
- [ ] Integrate with application API
- [ ] Monitor costs in Azure Portal

For now, you can keep using local mode (`CLOUD_MODE=local`) and switch to full cloud mode when Databricks is ready!

