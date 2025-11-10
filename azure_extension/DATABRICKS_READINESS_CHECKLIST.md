# Databricks Readiness Checklist

## Overview

This checklist helps you decide **when** and **how** to integrate Azure Databricks with your Adaptive Finance Governance AFGA. It includes cost estimates, timelines, and decision criteria.

## Should You Add Databricks Now?

### ✅ Add Databricks If:

- [ ] You need **data governance at scale** (Unity Catalog)
- [ ] You want **PII detection and classification** automated
- [ ] You need **data lineage** for compliance audits
- [ ] You're processing **1000+ documents** regularly
- [ ] You want **Bronze/Silver/Gold** medallion architecture
- [ ] You have **data quality requirements** (validation, transformation)
- [ ] You're preparing for **enterprise demos** to CTOs
- [ ] Budget allows **$10-50/month** for development/testing

### ⏸️ Wait on Databricks If:

- [ ] You're still in **early development** (local mode works fine)
- [ ] You're processing **< 100 documents**
- [ ] Budget is **very tight** (< $10/month available)
- [ ] You don't need **Unity Catalog governance** yet
- [ ] You're focused on **RAG quality**, not data governance
- [ ] You want to perfect the **Helm charts and K8s** first

**Recommendation:** Most teams should start with **local mode**, validate the RAG quality, then add Databricks when preparing for production or enterprise demos.

---

## Cost Analysis

### Databricks Pricing Breakdown

**Base Costs:**
- **Workspace:** Free (just a management interface)
- **DBU (Databricks Unit):** ~$0.40-0.55/DBU (varies by region and tier)
- **Compute:** Azure VM costs + DBU costs

**Compute Options:**

| Cluster Type | VM Size | DBU/hour | VM Cost/hour | Total/hour | Use Case |
|--------------|---------|----------|--------------|------------|----------|
| **All-Purpose (Dev)** | Standard_DS3_v2 | 0.75 | $0.18 | ~$0.60 | Interactive development |
| **Jobs (Automated)** | Standard_DS3_v2 | 0.15 | $0.18 | ~$0.30 | Scheduled pipelines |
| **Single Node** | Standard_DS3_v2 | 0.75 | $0.18 | ~$0.60 | Testing/learning |

**Premium Tier:** Required for Unity Catalog (~20% higher DBU costs)

### Monthly Cost Scenarios

#### Scenario 1: Learning/Testing (Minimal Usage)
```
Assumptions:
- 10 hours/month interactive development
- Auto-terminate after 15 minutes
- Single-node cluster
- No scheduled jobs

Costs:
- Compute: 10 hours × $0.60 = $6.00
- Storage (Delta Lake): 5 GB × $0.02 = $0.10
- Network: Minimal = $0.50

Total: ~$7-10/month
```

#### Scenario 2: Active Development (Moderate Usage)
```
Assumptions:
- 40 hours/month interactive development
- Daily job runs (1 hour/day)
- Single-node cluster for dev
- Jobs cluster for automation

Costs:
- Interactive: 40 hours × $0.60 = $24.00
- Jobs: 30 hours × $0.30 = $9.00
- Storage: 50 GB × $0.02 = $1.00
- Network: $2.00

Total: ~$35-40/month
```

#### Scenario 3: Production-Ready (High Usage)
```
Assumptions:
- 80 hours/month development
- Hourly job runs (720 hours/month, but auto-scales)
- Multi-node cluster for production
- Unity Catalog governance

Costs:
- Interactive: 80 hours × $0.60 = $48.00
- Jobs: 100 hours × $0.40 = $40.00
- Storage: 500 GB × $0.02 = $10.00
- Unity Catalog: Included
- Network: $5.00

Total: ~$100-120/month
```

### Cost Optimization Tips

**1. Use Job Clusters (Not All-Purpose)**
```
Savings: ~50% on DBU costs
How: Schedule pipelines to run on job clusters instead of keeping all-purpose cluster running
```

**2. Auto-Termination**
```
Savings: ~70% on wasted compute
How: Set auto-terminate to 10-15 minutes of inactivity
```

**3. Right-Size Clusters**
```
Savings: ~30% on compute
How: Start with smallest size (Standard_DS3_v2), scale up only if needed
```

**4. Spot VMs for Jobs**
```
Savings: ~60-80% on VM costs
How: Enable spot instances for non-critical jobs
Risk: Jobs may be interrupted (usually fine for batch processing)
```

**5. Schedule Jobs During Off-Peak**
```
Savings: ~10-20% (if using spot instances)
How: Run intensive jobs during night/weekend when spot prices are lower
```

**6. Delta Lake Optimization**
```
Savings: ~50% on storage costs over time
How: Enable auto-optimize, vacuum old versions regularly
```

### Total Cost Comparison

| Deployment Level | Monthly Cost | What's Included |
|------------------|--------------|-----------------|
| **Local Only** | $0 | Docker Compose, Weaviate, no cloud |
| **Cloud Storage** | $5-10 | ADLS Gen2, Key Vault, ACR |
| **+ Databricks (Light)** | $15-20 | Storage + minimal Databricks usage |
| **+ Databricks (Active)** | $40-60 | Storage + active development |
| **+ AKS (Dev)** | $110-180 | Everything above + Kubernetes cluster |
| **Production (Full)** | $300-500 | Everything + HA, scaling, monitoring |

---

## Implementation Timeline

### Phase 1: Preparation (1-2 hours)

**Before spending any money:**

- [ ] Review Databricks fundamentals
  - Unity Catalog concepts
  - Bronze/Silver/Gold architecture
  - PySpark basics
- [ ] Review existing notebooks in `databricks/notebooks/`
- [ ] Understand the medallion architecture
- [ ] Plan your catalog/schema structure
- [ ] Estimate document volume and frequency

**Resources:**
- Databricks Documentation: https://docs.databricks.com
- Unity Catalog Guide: https://docs.databricks.com/data-governance/unity-catalog/
- Your existing docs: `azure_extension/databricks/SETUP.md`

---

### Phase 2: Create Workspace (5-10 minutes, ~$0)

**Action:** Create Databricks workspace in Azure

```bash
# Using Azure Portal (recommended for first time)
1. Go to portal.azure.com
2. Search "Azure Databricks"
3. Click "+ Create"
4. Configure:
   - Resource Group: adaptive-finance-governance-rag-dev-rg
   - Workspace Name: databricks-adaptive-finance-governance-dev
   - Region: West Europe
   - Pricing Tier: Premium (required for Unity Catalog)
5. Review + Create (~3-5 minutes)
```

**Cost:** Workspace itself is **free**, you only pay for compute when you use it.

**Deliverables:**
- [ ] Workspace created
- [ ] Workspace URL saved (e.g., https://adb-123456789.azuredatabricks.net)
- [ ] Can access workspace UI

---

### Phase 3: Initial Setup (30-45 minutes, ~$0.50)

**Action:** Configure workspace and upload notebooks

**Step 1: Create Access Token**
```
1. In Databricks workspace → User Settings
2. Developer → Access Tokens
3. Generate new token (90 days)
4. Save token securely
```

**Step 2: Configure Databricks CLI**
```bash
databricks configure --token

# Enter:
# - Host: https://adb-your-workspace.azuredatabricks.net
# - Token: <your-token>
```

**Step 3: Upload Notebooks**
```bash
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent/azure_extension

databricks workspace mkdirs /notebooks

databricks workspace import databricks/notebooks/01_ingest_raw.py \
  /notebooks/01_ingest_raw --language PYTHON --format SOURCE

databricks workspace import databricks/notebooks/02_validate_transform.py \
  /notebooks/02_validate_transform --language PYTHON --format SOURCE

databricks workspace import databricks/notebooks/03_chunk_embed_register.py \
  /notebooks/03_chunk_embed_register --language PYTHON --format SOURCE
```

**Step 4: Grant Storage Access**
```bash
# Get Databricks workspace's managed identity principal ID
DATABRICKS_PRINCIPAL_ID=$(az databricks workspace show \
  --name databricks-adaptive-finance-governance-dev \
  --resource-group adaptive-finance-governance-rag-dev-rg \
  --query managedResourceGroupId -o tsv)

# Grant Storage Blob Data Contributor
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee $DATABRICKS_PRINCIPAL_ID \
  --scope /subscriptions/fd6c7319-01d0-4610-9681-b82980e227fb/resourceGroups/adaptive-finance-governance-rag-dev-rg/providers/Microsoft.Storage/storageAccounts/trustedaidevsa251031
```

**Cost for this phase:** ~$0.50 (a few minutes of cluster time)

**Deliverables:**
- [ ] Databricks CLI configured
- [ ] Notebooks uploaded to workspace
- [ ] Storage access granted
- [ ] Can view notebooks in Databricks UI

---

### Phase 4: Unity Catalog Setup (1-2 hours, ~$2)

**Action:** Create Unity Catalog structure

**Step 1: Create/Link Metastore**

If no metastore exists in your region:
```
1. In Databricks → Data → Unity Catalog
2. Click "Create Metastore"
3. Follow wizard
4. Link to workspace
```

If metastore exists:
```
1. Admin Console → Workspaces
2. Link existing metastore to your workspace
```

**Step 2: Execute Unity Catalog SQL**

```bash
# Copy SQL scripts content
cat databricks/unity_catalog/catalogs.sql
cat databricks/unity_catalog/schemas.sql
cat databricks/unity_catalog/grants.sql
```

In Databricks SQL Editor:
1. Create new query
2. Paste and execute `catalogs.sql`
3. Paste and execute `schemas.sql`
4. Paste and execute `grants.sql`

**Step 3: Verify Structure**

```sql
-- In Databricks SQL Editor
SHOW CATALOGS;
SHOW SCHEMAS IN afga_dev;
SHOW TABLES IN afga_dev.bronze;
```

**Cost for this phase:** ~$2 (1-2 hours of your time, ~30 min cluster time)

**Deliverables:**
- [ ] Unity Catalog metastore linked
- [ ] Catalog `afga_dev` created
- [ ] Schemas `bronze`, `silver`, `gold` created
- [ ] Access grants configured

---

### Phase 5: Test Pipeline (2-3 hours, ~$3-5)

**Action:** Run notebooks manually to test

**Step 1: Create Test Cluster**

```
1. Compute → Create Compute
2. Configure:
   - Name: "test-cluster"
   - Policy: None (Unrestricted)
   - Mode: Single Node
   - Access Mode: Single User
   - Runtime: 14.3 LTS (includes Apache Spark 3.5)
   - Node: Standard_DS3_v2 (4 cores, 14GB)
   - Auto-terminate: 15 minutes
3. Create (~5 minutes)
```

**Step 2: Run Notebook 1 (Ingest Raw)**

```
1. Open /notebooks/01_ingest_raw
2. Attach to test-cluster
3. Set parameters (widget values):
   - storage_account: trustedaidevsa251031
   - container: raw
4. Run All
5. Review output
6. Verify data in bronze layer:
   SELECT * FROM afga_dev.bronze.documents LIMIT 10;
```

**Step 3: Run Notebook 2 (Validate Transform)**

```
1. Open /notebooks/02_validate_transform
2. Attach to test-cluster
3. Run All
4. Review validation results
5. Verify data in silver layer:
   SELECT * FROM afga_dev.silver.validated_documents LIMIT 10;
```

**Step 4: Run Notebook 3 (Chunk Embed)**

```
1. Open /notebooks/03_chunk_embed_register
2. Attach to test-cluster
3. Set parameters:
   - openai_api_key: (from Key Vault or enter directly for testing)
4. Run All
5. Verify embeddings in gold layer:
   SELECT * FROM afga_dev.gold.document_embeddings LIMIT 5;
```

**Cost for this phase:** ~$3-5 (2-3 hours compute × ~$0.60/hour, with auto-terminate)

**Deliverables:**
- [ ] All three notebooks run successfully
- [ ] Data flows Bronze → Silver → Gold
- [ ] Embeddings generated
- [ ] PII tags visible in metadata
- [ ] Cluster auto-terminates after 15 minutes

---

### Phase 6: Create Automated Job (30 minutes, ~$1)

**Action:** Schedule pipeline as a job

**Using Databricks UI:**

```
1. Workflows → Jobs → Create Job
2. Configure:
   - Name: "adaptive-finance-governance-rag-pipeline"
   
3. Add Task 1:
   - Task name: "ingest_raw"
   - Type: Notebook
   - Notebook path: /notebooks/01_ingest_raw
   - Cluster: New job cluster (smallest size)
   - Parameters: {"storage_account": "trustedaidevsa251031", "container": "raw"}

4. Add Task 2:
   - Task name: "validate_transform"
   - Type: Notebook
   - Notebook path: /notebooks/02_validate_transform
   - Depends on: ingest_raw
   
5. Add Task 3:
   - Task name: "chunk_embed"
   - Type: Notebook
   - Notebook path: /notebooks/03_chunk_embed_register
   - Depends on: validate_transform

6. Schedule: Daily at 2 AM (or as needed)

7. Notifications: Add your email for failures

8. Save
```

**Test the Job:**
```
1. Click "Run Now"
2. Monitor execution
3. Review logs for each task
4. Verify completion
```

**Cost for this phase:** ~$1 (testing job runs)

**Deliverables:**
- [ ] Job created with 3 tasks
- [ ] Job runs successfully end-to-end
- [ ] Schedule configured
- [ ] Notifications set up

---

### Phase 7: Integration with Application (1 hour, ~$0)

**Action:** Update application to use Databricks mode

**Step 1: Store Databricks Secrets in Key Vault**

```bash
# Store workspace URL
az keyvault secret set \
  --vault-name kv-dev-afga \
  --name databricks-workspace-url \
  --value "https://adb-your-workspace.azuredatabricks.net"

# Store job ID
JOB_ID="12345"  # Get from job URL
az keyvault secret set \
  --vault-name kv-dev-afga \
  --name databricks-job-id \
  --value "$JOB_ID"

# Store token (or use managed identity in production)
az keyvault secret set \
  --vault-name kv-dev-afga \
  --name databricks-token \
  --value "your-token-here"
```

**Step 2: Update Application Configuration**

```bash
# In your .env file (for local testing)
echo "CLOUD_MODE=databricks" >> .env
echo "DATABRICKS_WORKSPACE_URL=https://adb-your-workspace.azuredatabricks.net" >> .env
echo "DATABRICKS_JOB_ID=12345" >> .env
echo "DATABRICKS_TOKEN=your-token" >> .env
```

**Step 3: Test Integration**

```bash
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent

# Activate virtual environment
source .venv/bin/activate

# Start application
uvicorn src.api.main:app --reload

# In another terminal, test document upload
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@data/raw/eu_ai_act_article5.txt" \
  -F "document_type=regulation" \
  -F "confidentiality_level=public"

# Should trigger Databricks job
```

**Cost for this phase:** ~$0 (no additional Databricks compute)

**Deliverables:**
- [ ] Application configured for Databricks mode
- [ ] Secrets stored in Key Vault
- [ ] Document upload triggers Databricks job
- [ ] Can query processed documents

---

### Phase 8: Monitoring & Optimization (Ongoing)

**Action:** Set up cost monitoring and optimization

**Cost Monitoring:**

```bash
# Set up Azure Cost Management alert
az consumption budget create \
  --resource-group adaptive-finance-governance-rag-dev-rg \
  --budget-name databricks-monthly-budget \
  --amount 50 \
  --time-grain Monthly \
  --start-date $(date +%Y-%m-01) \
  --end-date 2025-12-31 \
  --notifications amount=40 recipients=your-email@example.com
```

**In Databricks:**
1. Admin Console → Billing Usage
2. Review DBU consumption daily
3. Identify expensive jobs/clusters
4. Optimize as needed

**Optimization Checklist:**
- [ ] Auto-terminate enabled on all clusters (10-15 minutes)
- [ ] Job clusters used instead of all-purpose
- [ ] Smallest cluster size that meets performance needs
- [ ] Delta Lake auto-optimize enabled
- [ ] Regular vacuum of old versions (every 7 days)
- [ ] Spot instances enabled for non-critical jobs

**Cost:** Ongoing monitoring is free, optimization actions save money

---

## Complete Cost Timeline

| Phase | Time | Compute Cost | Your Time |
|-------|------|--------------|-----------|
| 1. Preparation | N/A | $0 | 1-2 hours |
| 2. Create Workspace | 5 min | $0 | 5 minutes |
| 3. Initial Setup | 30 min | ~$0.50 | 30-45 minutes |
| 4. Unity Catalog | 1 hour | ~$2 | 1-2 hours |
| 5. Test Pipeline | 2 hours | ~$3-5 | 2-3 hours |
| 6. Create Job | 30 min | ~$1 | 30 minutes |
| 7. Integration | 1 hour | ~$0 | 1 hour |
| **TOTAL** | **~5 hours** | **~$7-10** | **5-8 hours** |

**Ongoing:** $10-50/month depending on usage

---

## Decision Matrix

### When to Add Databricks

| Factor | Score (1-5) | Weight | Weighted |
|--------|-------------|--------|----------|
| **Need Unity Catalog governance** | ___ | 0.25 | ___ |
| **Processing > 1000 docs** | ___ | 0.20 | ___ |
| **Budget available ($50/mo)** | ___ | 0.15 | ___ |
| **Enterprise demo needed** | ___ | 0.15 | ___ |
| **Data quality automation needed** | ___ | 0.15 | ___ |
| **PII detection required** | ___ | 0.10 | ___ |
| **Total** | | **1.00** | ___ |

**Scoring Guide:**
- 1 = Not at all
- 3 = Somewhat
- 5 = Critical need

**Decision:**
- < 2.5 = Wait, focus on local development
- 2.5-3.5 = Consider adding soon (1-2 weeks)
- > 3.5 = Add now (within this week)

---

## Alternatives to Consider

### Alternative 1: Continue with Local Mode

**Pros:**
- ✅ Zero cost
- ✅ Fast iteration
- ✅ Good for RAG quality development

**Cons:**
- ❌ No Unity Catalog governance
- ❌ Manual data quality checks
- ❌ Less impressive for enterprise demos

**Best for:** Early development, RAG experimentation

---

### Alternative 2: Simple Azure Function Processing

**Pros:**
- ✅ Lower cost (~$2-5/month)
- ✅ Simpler architecture
- ✅ Serverless auto-scaling

**Cons:**
- ❌ No Unity Catalog
- ❌ Limited PySpark capabilities
- ❌ Less enterprise-ready

**Best for:** Simple pipelines, budget-constrained projects

---

### Alternative 3: Databricks Community Edition

**Pros:**
- ✅ Free forever
- ✅ Learn Databricks/PySpark
- ✅ Test notebooks

**Cons:**
- ❌ No Unity Catalog
- ❌ No Azure integration
- ❌ Can't connect to your ADLS
- ❌ Not for production

**Best for:** Learning, training, experimentation

**Sign up:** https://community.cloud.databricks.com

---

## Recommended Path

### For Most Teams:

**Week 1-2: Local Development**
- ✅ Perfect RAG quality
- ✅ Test Helm charts with minikube
- ✅ Set up GitHub Actions
- Cost: $0

**Week 3-4: Add Cloud Storage**
- ✅ Deploy ADLS Gen2
- ✅ Test cloud mode
- ✅ Validate storage integration
- Cost: ~$5-10/month

**Week 5-6: Add Databricks (if needed)**
- ✅ Create workspace
- ✅ Set up Unity Catalog
- ✅ Test pipelines
- ✅ Prepare for demos
- Cost: ~$15-50/month

**Week 7+: Production Kubernetes (if needed)**
- ✅ Deploy AKS
- ✅ Install Istio
- ✅ Configure ArgoCD
- ✅ Full production demo
- Cost: ~$150-500/month

---

## Quick Start Command

When you're ready to begin:

```bash
# Save this as start-databricks.sh
#!/bin/bash
set -e

echo "🚀 Starting Databricks Setup..."
echo ""

echo "📋 Prerequisites Check:"
echo "  [ ] Azure subscription active"
echo "  [ ] Budget approved (~\$50/month)"
echo "  [ ] Time available (5-8 hours total)"
echo "  [ ] ADLS Gen2 deployed and working"
echo ""

read -p "All prerequisites met? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Complete prerequisites first"
    exit 1
fi

echo "✅ Prerequisites confirmed"
echo ""

echo "📚 Next steps:"
echo "  1. Review: azure_extension/databricks/SETUP.md"
echo "  2. Create workspace in Azure Portal"
echo "  3. Follow Phase 3-7 in DATABRICKS_READINESS_CHECKLIST.md"
echo ""

echo "💡 Tip: Use smallest cluster size and enable auto-terminate to minimize costs"
echo ""

echo "🎯 Ready to proceed!"
```

---

## Summary

**Databricks adds significant value for:**
- Enterprise demos requiring governance
- Production deployments at scale
- Compliance/audit requirements
- Automated data quality pipelines

**Start without Databricks if:**
- Early development phase
- Budget is very tight
- Focused on RAG quality first

**When ready:**
- Budget: ~$10-50/month for development
- Time: 5-8 hours initial setup
- Complexity: Medium (well-documented)

**Follow:** `azure_extension/databricks/SETUP.md` for step-by-step instructions.

Good luck! 🚀

