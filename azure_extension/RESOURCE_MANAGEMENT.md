# Resource Management Guide

## Stopping Services to Save Costs

### Local Services (Free - but saves CPU/memory)

#### Stop All Local Services
```bash
# Kill FastAPI
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Kill Streamlit  
lsof -ti:8501 | xargs kill -9 2>/dev/null

# Stop Docker containers
cd docker
docker-compose down

# Optional: Stop Docker Desktop to save memory
```

#### Start Services Again
```bash
# Start Weaviate only
cd docker
docker-compose up -d weaviate

# Start FastAPI in cloud mode
source .venv/bin/activate
source azure_extension/azure-terraform-env.sh
export CLOUD_MODE=databricks AZURE_STORAGE_ACCOUNT=trustedaidevsa251031
uvicorn src.api.main:app --reload

# Start Streamlit (in another terminal)
source .venv/bin/activate
streamlit run streamlit_app/app.py
```

---

## Azure Resources - Cost Management

### Current Monthly Costs (~$5-10)

| Resource | Monthly Cost | How to Reduce |
|----------|-------------|---------------|
| ADLS Gen2 | ~$0.02/GB | Delete test files if not needed |
| Key Vault | ~$0.03/10k ops | Minimal cost, keep running |
| ACR (Basic) | ~$5/month | Keep - needed for images |

**Recommendation**: Keep everything running. The cost is minimal (~$5-10/month) and services are needed for development.

### Optional: Pause Databricks (When Created)

**If you've created a Databricks workspace**:

```bash
# Stop all clusters
databricks clusters list | grep RUNNING | awk '{print $1}' | xargs -I {} databricks clusters delete --cluster-id {}

# Clusters cost money when running, workspace itself is cheap
```

**Cost impact**: Saves compute costs (~$0.55/hour per cluster)

### Optional: Delete AKS (If Deployed)

**If you've deployed AKS and want to stop it**:

```bash
cd azure_extension/infra/terraform/envs/dev

# Remove just the AKS module from main.tf (comment it out)
# Then run:
terraform apply

# Or delete the entire cluster via Azure CLI
az aks delete \
  --resource-group adaptive-finance-governance-rag-dev-rg \
  --name adaptive-finance-governance-rag-dev-aks \
  --yes --no-wait
```

**Cost impact**: Saves ~$70-100/month

**Rebuild when needed**: Just run `terraform apply` again (10-15 minutes)

---

## Recommended Resource Strategy

### Keep Running (Minimal Cost)
✅ **ADLS Gen2**: ~$0.02/GB/month  
✅ **Key Vault**: ~$0.03/10k operations  
✅ **ACR**: ~$5/month

**Total**: ~$5-10/month

**Why keep**: Development-ready, instant access, minimal cost

### Start Only When Needed
⏰ **Databricks clusters**: Start for testing, auto-terminate after 10 min  
⏰ **AKS cluster**: Only create when doing full demo

### Never Delete (Unless Cleaning Up Entirely)
🔒 **Terraform state storage**: `philippsstorageaccount/tfstate`  
🔒 **Resource groups**: Keep for easy management  
🔒 **Docker images in ACR**: Already built, no ongoing cost

---

## Complete Cleanup (If Starting Over)

**⚠️ WARNING: This deletes everything! Only if you're done with the project.**

```bash
# Delete everything via Terraform
cd azure_extension/infra/terraform/envs/dev
terraform destroy

# This will remove:
# - ADLS Gen2 (and all uploaded files)
# - Key Vault (and all secrets)
# - ACR (and all images)
# - AKS (if deployed)
# - Log Analytics (if created)

# Confirm with 'yes' when prompted
```

Or via Azure CLI:
```bash
# Delete entire resource group
az group delete \
  --name adaptive-finance-governance-rag-dev-rg \
  --yes --no-wait
```

---

## Cost Monitoring

### Check current costs

```bash
# Via Azure CLI
az consumption usage list \
  --start-date 2025-10-01 \
  --end-date 2025-10-31 \
  --query "[?contains(instanceName, 'trusted-ai')]" \
  --output table
```

### View in Azure Portal

1. Go to https://portal.azure.com
2. Search for "Cost Management + Billing"
3. Click "Cost analysis"
4. Filter by resource group: `adaptive-finance-governance-rag-dev-rg`
5. View daily/monthly costs

### Set up cost alerts

```bash
# Create budget alert (via Azure Portal or CLI)
az consumption budget create \
  --budget-name "trusted-ai-dev-budget" \
  --amount 20 \
  --time-grain Monthly \
  --resource-group adaptive-finance-governance-rag-dev-rg
```

---

## Current Status Summary

### Running in Azure (Always On)
- ✅ ADLS Gen2 storage account
- ✅ Key Vault with secrets
- ✅ ACR with Docker images
- **Cost**: ~$5-10/month

### Not Deployed (Saves Money)
- ❌ AKS cluster (saves ~$70-100/month)
- ❌ Databricks workspace (saves ~$10-50/month)
- ❌ Log Analytics (will be created with AKS)

### Local Services (Stopped)
- ❌ Weaviate container
- ❌ FastAPI backend
- ❌ Streamlit UI

**All services can be restarted in minutes when you continue development!**

---

## Quick Reference

```bash
# Start local dev environment
cd docker && docker-compose up -d weaviate
source .venv/bin/activate
uvicorn src.api.main:app --reload    # Terminal 1
streamlit run streamlit_app/app.py   # Terminal 2

# Stop local dev environment
docker-compose down
# Kill FastAPI/Streamlit with Ctrl+C

# Deploy AKS when ready
cd azure_extension/infra/terraform/envs/dev
terraform apply

# Destroy AKS to save costs
terraform destroy -target=module.aks -target=module.monitoring
```

**You're in full control of costs!** 💰

