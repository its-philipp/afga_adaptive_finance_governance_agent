# Databricks Pipeline Testing Guide

## 🎯 Overview

This guide walks you through testing your Databricks pipeline end-to-end with **cost awareness** and **14-day trial optimization**.

**Estimated Time:** 1-2 hours  
**Estimated Cost:** ~$0.36 (with trial) vs ~$1.16 (without trial)  
**What You'll Verify:** Bronze → Silver → Gold data flow works

---

## 💰 Cost Breakdown

### With 14-Day Premium Trial (Your Current Setup):
```
Standard_DS3_v2 Single Node cluster:
- VM cost: $0.18/hour ✅ (you pay)
- DBU cost: $0/hour ✅ (FREE during trial!)
Total: $0.18/hour

Testing time: 1-2 hours
Total cost: ~$0.36
```

### After Trial Expires:
```
Same cluster:
- VM cost: $0.18/hour
- DBU cost: $0.40/hour (0.75 DBU × $0.55)
Total: $0.58/hour

Testing time: 1-2 hours  
Total cost: ~$1.16
```

**Savings with trial: 69%!** 🎉

---

## 📋 Step-by-Step Testing

### Step 1: Create Test Cluster (5 minutes, $0)

**In Databricks UI:**

1. Click **"Compute"** in left sidebar
2. Click **"+ Create Compute"** button
3. Fill in the form:

```
┌────────────────────────────────────────────────┐
│ Cluster name: test-rag-cluster                 │
│                                                 │
│ Policy: None (Unrestricted)                    │
│                                                 │
│ Cluster mode: Single Node ⭐                   │
│   (Cheapest option!)                           │
│                                                 │
│ Access mode: Single User                       │
│                                                 │
│ Databricks runtime version:                    │
│   14.3 LTS (or latest LTS)                     │
│                                                 │
│ Use Photon acceleration: OFF                   │
│   (Not needed for this workload)               │
│                                                 │
│ Node type: Standard_DS3_v2                     │
│   (4 cores, 14 GB RAM)                         │
│                                                 │
│ ⭐ Auto terminate: 15 minutes ⭐               │
│   (CRITICAL! Stops costs when idle)            │
│                                                 │
│ Advanced options (leave defaults)              │
│                                                 │
│ [Create Compute]                               │
└────────────────────────────────────────────────┘
```

4. Click **"Create Compute"**
5. Wait ~5 minutes for cluster to start
6. Status changes: Pending → Starting → Running ✅

**Cost so far:** $0 (startup doesn't cost, only running time)

---

### Step 2: Upload Sample Data to ADLS Gen2 (5 minutes, $0)

**You need data in ADLS for the pipeline to process!**

**Option A: Use existing data (if you have some in ADLS)**
```bash
# Check if you have data
az storage blob list \
  --account-name trustedaidevsa251031 \
  --container-name raw \
  --output table
```

**Option B: Upload a test document**
```bash
cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent

# Upload a sample document
az storage blob upload \
  --account-name trustedaidevsa251031 \
  --container-name raw \
  --name test-doc.txt \
  --file data/raw/eu_ai_act_article5.txt \
  --auth-mode login

# Create metadata JSON
cat > /tmp/test-doc.txt.metadata.json << 'EOF'
{
  "doc_id": "test-doc-001",
  "document_type": "regulation",
  "confidentiality_level": "public",
  "uploaded_at": "2025-11-01T12:00:00Z",
  "source": "EU AI Act"
}
EOF

az storage blob upload \
  --account-name trustedaidevsa251031 \
  --container-name raw \
  --name test-doc.txt.metadata.json \
  --file /tmp/test-doc.txt.metadata.json \
  --auth-mode login

rm /tmp/test-doc.txt.metadata.json

echo "✅ Test document uploaded to ADLS Gen2"
```

---

### Step 3: Test Notebook 1 - Ingest Raw (10 minutes, ~$0.03)

**In Databricks UI:**

1. Go to **"Workspace"** in left sidebar
2. Navigate to **"/Shared/afga-agent-notebooks"**
3. Click **"01_ingest_raw"**
4. Click **"Attach"** → Select **"test-rag-cluster"**
5. Set parameters (top of notebook):
   ```
   storage_account: trustedaidevsa251031
   container: raw
   doc_id: (leave empty to process all)
   ```
6. Click **"Run all"** 
7. Watch cells execute (~2-3 minutes)

**Expected Output:**
```
✅ Read X files from ADLS Gen2
✅ Loaded into afga_dev.bronze.finance_transactions_raw
✅ Ingested X invoices to bronze layer
```

**Verify in Catalog:**
1. Click **"Catalog"** in left sidebar
2. Navigate: `afga_dev` → `bronze` → `finance_transactions_raw`
3. Click **"Sample data"** to preview rows
4. You should see invoice fields (`invoice_id`, `vendor`, `amount`, `currency`, `ingested_at`)

**Cost so far:** ~$0.03 (10 min × $0.18/hr)

---

### Step 4: Test Notebook 2 - Validate Transform (15 minutes, ~$0.05)

**In Databricks UI:**

1. Navigate to **"/Repos/<repo_path>/azure_extension/databricks/notebooks/02_validate_transform"**
2. Click **"Attach"** → **"test-rag-cluster"** (should already be running)
3. No parameters needed (reads from bronze automatically)
4. Click **"Run all"**
5. Watch validation and chunking (~3-5 minutes)

**Expected Output:**
```
📄 Read X invoices from bronze layer
✅ Validation complete: X valid, Y invalid
📊 Risk scores calculated (high/medium/low)
🏷️ Policy flags generated
✅ Processed X invoices to silver layer
```

**Verify in Catalog:**
1. Navigate: `afga_dev` → `silver` → `finance_transactions_enriched`
2. Click **"Sample data"**
3. You should see:
- Normalized currency values
- Risk scores & risk_level column
- Policy flags array
- Structured summary text

**Cost so far:** ~$0.08 (25 min × $0.18/hr)

---

### Step 5: Test Notebook 3 - Embeddings (20 minutes, ~$0.12)

**⚠️ Important:** This notebook needs your OpenAI API key!

**In Databricks UI:**

1. Navigate to **"/Repos/<repo_path>/azure_extension/databricks/notebooks/03_chunk_embed_register"**
2. Click **"Attach"** → **"test-rag-cluster"**
3. **Set parameters:**
   ```
   openai_api_key: sk-your-key-here
   openai_model: text-embedding-3-small
   vector_index_name: finance_transactions_index
   ```
   
   **Get your key from:**
   - `.env` file in project root
   - OR Azure Key Vault: `az keyvault secret show --vault-name kv-dev-afga --name openai-api-key`

4. Click **"Run all"**
5. Watch embedding generation (~5-10 minutes depending on chunk count)

**Expected Output:**
```
📄 Read X summaries from silver layer
🔄 Generating embeddings for X summaries...
✅ Generated embeddings for X invoices
✅ Wrote to afga_dev.gold.finance_transaction_embeddings
```

**Verify in Catalog:**
1. Navigate: `afga_dev` → `gold` → `finance_transaction_embeddings`
2. Click **"Sample data"**
3. You should see:
- Structured summary text
   - Embedding vectors (arrays of floats)
   - Metadata

**Cost so far:** ~$0.15 (45 min × $0.18/hr)

---

### Step 6: Verify Complete Data Flow (5 minutes, $0)

**Run this SQL in SQL Editor:**

```sql
-- Check Bronze layer
SELECT COUNT(*) as document_count 
FROM afga_dev.bronze.finance_transactions_raw;

-- Check Silver layer
SELECT COUNT(*) as chunk_count 
FROM afga_dev.silver.finance_transactions_enriched;

-- Check Gold layer (embeddings)
SELECT COUNT(*) as embedding_count 
FROM afga_dev.gold.finance_transaction_embeddings;

-- View a sample with all metadata
SELECT 
  chunk_text,
  pii_detected,
  confidentiality_level,
  source_document
FROM afga_dev.silver.finance_transactions_enriched
LIMIT 5;
```

**Expected:**
- Bronze count > 0 ✅
- Silver count > Bronze count (chunks > documents) ✅
- Gold count = Silver count ✅

**This proves:** Bronze → Silver → Gold pipeline works! 🎉

---

### Step 7: CLEANUP - Stop Costs! (2 minutes, saves $0.18/hour)

**IMPORTANT: Do this immediately after testing!**

**In Databricks UI:**

1. Go to **"Compute"**
2. Find **"test-rag-cluster"**
3. Click **"..." menu** → **"Terminate"**
4. Wait ~30 seconds
5. Click **"..." menu** → **"Delete"** (optional but recommended)

**Why Delete?**
- Terminated clusters can be restarted (accidentally costs money)
- Deleted clusters are gone (no risk of accidental restart)
- You can recreate in 5 minutes when needed!

**OR run cleanup script:**
```bash
./scripts/databricks-cleanup.sh
```

**Costs stop immediately!** ✅

---

## 💰 Total Testing Cost

| Activity | Time | Cost (with trial) |
|----------|------|-------------------|
| Cluster startup | 5 min | $0 |
| Notebook 1 (Ingest) | 10 min | $0.03 |
| Notebook 2 (Validate) | 15 min | $0.05 |
| Notebook 3 (Embed) | 20 min | $0.06 |
| Verification SQL | 5 min | $0.01 |
| **TOTAL** | **55 min** | **~$0.15-0.18** |

Plus OpenAI API costs for embeddings: ~$0.01-0.05

**Grand Total: ~$0.20-0.25** ✅

(vs ~$0.60 without trial!)

---

## 🎯 Quick Start Checklist

Before we begin, make sure you have:

- [ ] Unity Catalog schemas created (bronze, silver, gold) ✅ You did this!
- [ ] Notebooks uploaded to Databricks ✅ Already done!
- [ ] Sample document in ADLS Gen2 (or ready to upload)
- [ ] OpenAI API key handy (for notebook 3)
- [ ] 1-2 hours available
- [ ] Ready to delete cluster after testing!

---

## 🚀 Ready to Start?

I'll help you:
1. Upload sample data to ADLS Gen2
2. Guide through each notebook execution
3. Verify data in each layer
4. Make sure you cleanup properly

**Let's begin! First, let's upload a test document to ADLS:**

<function_calls>
<invoke name="run_terminal_cmd">
<parameter name="command">cd /Users/philipptrinh/workspace/playground/adaptive_finance_governance_agent

echo "📤 Uploading test document to ADLS Gen2..."
echo ""

# Upload a sample document
az storage blob upload \
  --account-name trustedaidevsa251031 \
  --container-name raw \
  --name test-eu-ai-act.txt \
  --file data/raw/eu_ai_act_article5.txt \
  --auth-mode login \
  --overwrite

# Create metadata JSON
cat > /tmp/test-metadata.json << 'EOF'
{
  "doc_id": "test-eu-ai-act-001",
  "document_type": "regulation",
  "confidentiality_level": "public",
  "uploaded_at": "2025-11-01T12:00:00Z",
  "source": "EU AI Act Article 5",
  "title": "EU AI Act - Prohibited AI Practices"
}
EOF

az storage blob upload \
  --account-name trustedaidevsa251031 \
  --container-name raw \
  --name test-eu-ai-act.txt.metadata.json \
  --file /tmp/test-metadata.json \
  --auth-mode login \
  --overwrite

rm /tmp/test-metadata.json

echo ""
echo "✅ Test document uploaded!"
echo ""
echo "Next: Create cluster in Databricks UI and run notebooks"
