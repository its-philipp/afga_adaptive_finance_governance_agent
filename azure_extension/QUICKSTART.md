# Azure Extension Quick Start

## ✅ What We've Accomplished

1. **Terraform Backend Setup** ✓
   - Resource Group: `tfstate-rg`
   - Storage Account: `philippsstorageaccount`
   - Container: `tfstate`

2. **Dev Environment Infrastructure** ✓
   - Resource Group: `adaptive-finance-governance-rag-dev-rg`
   - Storage Account (ADLS Gen2): `trustedaidevsa251031`
   - Containers: `raw`, `bronze`, `silver`, `gold`

3. **RBAC Permissions** ✓
   - Service Principal: `Storage Blob Data Contributor` role assigned
   - Your User Account: `Storage Blob Data Contributor` role assigned
   - **Note**: RBAC propagation takes 5-10 minutes

4. **Azure SDK Dependencies** ✓
   - `azure-storage-file-datalake`
   - `azure-identity`
   - `databricks-sdk`

## 🧪 Testing Cloud Mode (After RBAC Propagation)

### Wait for RBAC Propagation
RBAC role assignments can take up to 10 minutes to propagate. Wait and then test:

```bash
# Test after 10-15 minutes
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent
source .venv/bin/activate
python test_cloud_mode_cli.py
```

### Manual Test via Azure Portal
While waiting, you can verify the storage account works:

1. Go to Azure Portal: https://portal.azure.com
2. Navigate to Storage Account: `trustedaidevsa251031`
3. Click "Containers" → "raw"
4. Try uploading a test file manually
5. If this works, the RBAC just needs time to propagate

## 📊 Environments

### Development (Created)
```
Resource Group: adaptive-finance-governance-rag-dev-rg
Storage: trustedaidevsa251031
  ├── raw (for uploads/SharePoint)
  ├── bronze (for raw ingestion)
  ├── silver (for validated data)
  └── gold (for embeddings)
```

### Staging/Production (To Create Later)
```bash
# For staging
cd azure_extension/infra/terraform/envs/staging
terraform init
terraform plan
terraform apply

# For production
cd azure_extension/infra/terraform/envs/prod
terraform init
terraform plan
terraform apply
```

## 🔧 Configuration

### Environment Variables for Cloud Mode

Create or update `.env`:

```bash
# Cloud Mode Configuration
CLOUD_MODE=databricks  # or "local" for Weaviate
LLM_PROVIDER=openai    # or "openrouter"

# OpenAI (when LLM_PROVIDER=openai)
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Azure Storage (when CLOUD_MODE=databricks)
AZURE_STORAGE_ACCOUNT=trustedaidevsa251031
AZURE_STORAGE_CONTAINER=raw
AZURE_USE_MANAGED_IDENTITY=true

# Databricks (optional, for job triggering)
DATABRICKS_WORKSPACE_URL=https://adb-xxxxx.azuredatabricks.net
DATABRICKS_JOB_ID=12345

# Weaviate (when CLOUD_MODE=local)
WEAVIATE_URL=http://localhost:8080
WEAVIATE_API_KEY=optional

# Langfuse (optional)
LANGFUSE_PUBLIC_KEY=your-key
LANGFUSE_SECRET_KEY=your-secret
LANGFUSE_HOST=https://cloud.langfuse.com
```

## 🚀 Next Steps

### 1. Test Cloud Mode Ingestion (After RBAC Propagation)
```bash
python test_cloud_mode_cli.py
```

### 2. Run the Application in Cloud Mode
```bash
# Set environment variables
export CLOUD_MODE=databricks
export AZURE_STORAGE_ACCOUNT=trustedaidevsa251031

# Start backend
uvicorn src.api.main:app --reload

# Start Streamlit (in another terminal)
source .venv/bin/activate
streamlit run streamlit_app/app.py
```

### 3. Upload a Document via API
```bash
curl -X POST "http://localhost:8000/api/v1/ingest" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@data/raw/eu_ai_act_article5.txt" \
  -F "source=test_upload" \
  -F "doc_type=regulation" \
  -F "confidentiality_level=public"
```

### 4. Verify Upload in Azure Portal
1. Go to Storage Account: `trustedaidevsa251031`
2. Navigate to Containers → `raw`
3. Look for: `<source>/<year>/<month>/<day>/<doc_id>/`

### 5. Add More Infrastructure

#### Key Vault (for secrets management)
```bash
cd azure_extension/infra/terraform/envs/dev
# Add Key Vault module to main.tf
terraform plan
terraform apply
```

#### Azure Container Registry (for Docker images)
```bash
# Add ACR module to main.tf
terraform plan
terraform apply
```

#### Azure Kubernetes Service (for deployment)
```bash
# Add AKS module to main.tf
terraform plan
terraform apply
```

## 📚 Documentation

- [CTO Overview](docs/CTO_OVERVIEW.md) - Executive summary
- [Architecture](docs/ARCHITECTURE.md) - Technical details
- [Runbook](docs/RUNBOOK.md) - Operations guide
- [README](README.md) - Extension overview

## ⚠️ Troubleshooting

### RBAC Permission Errors
**Symptom**: `AuthorizationPermissionMismatch` errors

**Solution**: Wait 10-15 minutes for RBAC propagation, then retry

### DefaultAzureCredential Not Working
**Symptom**: `DefaultAzureCredential()` fails to authenticate

**Solutions**:
1. Use `AzureCliCredential()` (requires `az login`)
2. Set Service Principal environment variables:
   ```bash
   export AZURE_CLIENT_ID=<service-principal-app-id>
   export AZURE_CLIENT_SECRET=<service-principal-password>
   export AZURE_TENANT_ID=<tenant-id>
   ```

### Storage Account Not Found
**Symptom**: Storage account doesn't exist

**Solution**: Run Terraform apply:
```bash
cd azure_extension/infra/terraform/envs/dev
terraform apply
```

## 💡 Tips

1. **Always wait 10-15 minutes after RBAC changes** before testing
2. **Use local mode initially** to test without cloud dependencies
3. **Check Azure Portal** to verify resources are created correctly
4. **Monitor costs** in Azure Cost Management
5. **Use dev environment** for testing before creating staging/prod

## 🎯 Success Criteria

- ✅ Infrastructure created via Terraform
- ✅ RBAC roles assigned
- ⏳ Waiting for RBAC propagation (10-15 minutes)
- ⏳ Cloud mode upload test passes
- ⏳ Document visible in Azure Portal

Current Status: **Waiting for RBAC Propagation** (check again in ~10 minutes)

