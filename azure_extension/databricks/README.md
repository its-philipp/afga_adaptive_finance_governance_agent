# Databricks Components

This directory contains all Databricks assets that enable Phase 2 of the Adaptive Finance Governance Agent (AFGA): governed data pipelines, Unity Catalog configuration, and production-ready job definitions.

## Directory Structure

```
databricks/
├── notebooks/
│   ├── 01_ingest_raw.py             # Bronze: ingest invoices from ADLS
│   ├── 02_validate_transform.py     # Silver: validation + risk signals
│   └── 03_chunk_embed_register.py   # Gold: embeddings + vector prep
├── jobs/
│   └── pipeline_job.json            # Multi-task Databricks job definition
├── unity_catalog/
│   ├── catalogs.sql                 # Creates AFGA catalog and comment
│   ├── schemas.sql                  # bronze / silver / gold schemas
│   └── grants.sql                   # Role-based access control
├── README.md                        # You are here
└── SETUP.md                         # Hands-on setup guide
```

## Pipeline Overview

| Layer  | Notebook | Purpose | Tables |
|--------|----------|---------|--------|
| Bronze | `01_ingest_raw` | Pull JSON invoices from ADLS `raw-transactions` container and stamp ingestion metadata | `afga_dev.bronze.finance_transactions_raw` |
| Silver | `02_validate_transform` | Run finance validation rules, compute risk scores, normalize currency, build summaries | `afga_dev.silver.finance_transactions_enriched` |
| Gold   | `03_chunk_embed_register` | Turn structured summaries into OpenAI embeddings, persist for retrieval, prep vector search | `afga_dev.gold.finance_transaction_embeddings` |

### Bronze Highlights
- Recursive load of Phase 1 invoice JSON files.
- Adds metadata: ingestion timestamp + storage path.
- Ensures AFGA still runs locally while promoting raw data to Unity Catalog.

### Silver Highlights
- Validation rules (missing fields, non-positive totals, etc.).
- Currency normalization to USD with configurable exchange rates.
- Risk score heuristics + policy flags aligned with governance playbooks.
- Generates `structured_summary` text for downstream embeddings.

### Gold Highlights
- Embeds finance summaries with `text-embedding-3-small`.
- Stores embeddings + risk metadata in Unity Catalog.
- Provides checklist for Databricks Vector Search integration.

## Unity Catalog Layout

```
Catalog: afga_dev
├── Schema: bronze
│   └── Table: finance_transactions_raw
├── Schema: silver
│   └── Table: finance_transactions_enriched
└── Schema: gold
    └── Table: finance_transaction_embeddings
        └── (Optional) Vector Index: finance_transactions_index
```

## Access Control Model

- **Application / AKS (read-only)**  
  - `SELECT` on `silver.finance_transactions_enriched`  
  - `SELECT` on `gold.finance_transaction_embeddings`
- **Databricks jobs (read/write)**  
  - `ALL PRIVILEGES` on `bronze`, `silver`, `gold`
- **Data Engineering**  
  - `USAGE` on catalog, ability to rerun notebooks, manage jobs

Use `unity_catalog/grants.sql` as the baseline policy; adapt principal names to match your Azure AD groups or service principals.

## Config Files at a Glance

- `jobs/pipeline_job.json` – Multi-task job referencing the repo path under `/Repos/<repo_path>/azure_extension/...`. Populate `${var.*}` placeholders with Terraform or the Databricks UI.
- `unity_catalog/*.sql` – Run in order (`catalogs` → `schemas` → `grants`). Safe to rerun thanks to `IF NOT EXISTS`.
- `SETUP.md` – Full walkthrough (workspace, secrets, job creation, cost guidance).

## Getting Started

1. Follow [SETUP.md](SETUP.md) to provision Databricks, upload notebooks, and create Unity Catalog objects.
2. Run notebooks manually to validate each layer.
3. Create a Databricks job using `jobs/pipeline_job.json` via the UI or CLI.
4. Store workspace URL + job ID in Azure Key Vault so AKS/CI can trigger jobs.

## Monitoring & Operations

- **Jobs UI** – Track pipeline runs, retries, and cluster usage.
- **Delta Tables** – Query with Databricks SQL to validate bronze/silver/gold outputs.
- **Unity Catalog Lineage** – View end-to-end provenance for audits.
- **Logs** – Each notebook prints summary stats (counts, high-risk totals).

## Troubleshooting Cheatsheet

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| Notebook 01 cannot read ADLS | Managed identity lacks storage RBAC | Re-run Step 9 in `SETUP.md` |
| Validation shows zero invoices | Raw container empty or wrong path | Confirm upload path and `raw_container` parameter |
| Embedding failures | Missing OpenAI key or rate limiting | Populate secret scope `afga-secrets`, reduce batch size |
| Job cannot find notebook | Repo path mismatch | Update job JSON `repo_path` to match workspace |

## Cost Tips

1. Use job clusters with auto-termination (10–15 minutes).
2. Keep dev clusters single-node (e.g., `Standard_DS3_v2`).
3. Schedule jobs only when new invoices arrive.
4. Monitor spending via Azure Cost Management.

## Next Steps Toward Phase 2 Completion

1. Automate job triggers from the AFGA ingestion service.
2. Register `finance_transactions_index` in Databricks Vector Search.
3. Switch AFGA retrieval adapters to query Unity Catalog instead of the local store.
4. Enable Unity Catalog audit logging for compliance-grade traceability.

AFGA continues to run fully locally. This Databricks extension is additive—use it when you're ready to onboard enterprise data or demonstrate governed AI workflows in Azure.

