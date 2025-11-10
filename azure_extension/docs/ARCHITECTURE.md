# Architecture Documentation: Azure-Native Extension

## Overview

This document describes the technical architecture of the Azure-native extension for the Adaptive Finance Governance AFGA.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Ingestion Layer                             │
├─────────────────────────────────────────────────────────────────────┤
│  Streamlit UI / SharePoint Sync                                     │
│      │                                                              │
│      ▼                                                              │
│  FastAPI Endpoints                                                  │
│      │                                                              │
│      ├── CLOUD_MODE=local ──► WeaviateSink ──► Weaviate DB          │
│      │                                                              │
│      └── CLOUD_MODE=databricks ──► DatabricksSink ──► ADLS Gen2     │
│                                         │                           │
│                                         ▼                           │
│                                   Databricks Job Trigger            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      Databricks ELT Pipeline                        │
├─────────────────────────────────────────────────────────────────────┤
│  01_ingest_raw.py: ADLS Gen2 → Bronze (Delta)                       │
│      │                                                              │
│      ▼                                                              │
│  02_validate_transform.py: Validation, Chunking, Governance Tags    │
│      │                                                              │
│      ▼                                                              │
│  03_chunk_embed_register.py: Embeddings → Gold (Vector Search)      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      Query & Retrieval Layer                        │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI Query Endpoint                                             │
│      │                                                              │
│      ▼                                                              │
│  LangGraph Agent Workflow                                           │
│      │                                                              │
│      ├── Phase 1: WeaviateRetrievalAdapter ──► Weaviate             │
│      │                                                              │
│      └── Phase 2: DatabricksRetrievalAdapter ──► Vector Search      │
│      │                                                              │
│      ▼                                                              │
│  OpenAI API (gpt-4o-mini) ──► Answer Synthesis                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Ingestion Sinks

#### WeaviateSink (Local Mode)
- **Purpose**: Direct ingestion to Weaviate for local demos
- **Implementation**: Wraps existing `DocumentProcessor`
- **When Used**: `CLOUD_MODE=local` (default)

#### DatabricksSink (Cloud Mode)
- **Purpose**: Upload to ADLS Gen2 and trigger Databricks job
- **Implementation**: Uses Azure Storage SDK + Databricks SDK
- **When Used**: `CLOUD_MODE=databricks`
- **Auth**: Managed Identity (preferred) or Service Principal

### 2. Databricks ELT Pipeline

#### Notebook 01: Ingest Raw
- Reads from ADLS Gen2 `raw` container
- Writes to Bronze Delta table
- Stores raw files and metadata

#### Notebook 02: Validate Transform
- Validates document quality (Great Expectations)
- Chunks documents (LangChain RecursiveCharacterTextSplitter)
- Applies governance tags (PII detection, classification)
- Writes to Silver Delta table

#### Notebook 03: Chunk Embed Register
- Generates embeddings (OpenAI `text-embedding-3-small`)
- Writes to Gold Delta table
- Registers Vector Search index

### 3. Retrieval Adapters

#### WeaviateRetrievalAdapter (Phase 1)
- Uses existing `HybridRetriever`
- Queries Weaviate for document chunks

#### DatabricksRetrievalAdapter (Phase 2)
- Queries Databricks Vector Search index
- Filters by Unity Catalog metadata
- Returns `RetrievedChunk` objects

### 4. Infrastructure

#### Terraform Modules
- `storage_adls`: ADLS Gen2 storage account and containers
- `key_vault`: Azure Key Vault for secrets
- `acr`: Azure Container Registry
- `aks`: Azure Kubernetes Service with Workload Identity
- `databricks`: Databricks workspace and Unity Catalog
- `monitoring`: Log Analytics and diagnostics

#### Helm Chart
- Deployment, Service, HPA
- ServiceAccount with Workload Identity
- SecretProviderClass for Key Vault CSI
- Istio Gateway, VirtualService, DestinationRule

#### ArgoCD
- App-of-Apps pattern
- Environment-specific overlays (dev/staging/prod)
- Automated sync with self-healing

## Data Flow

### Ingestion Flow (Cloud Mode)

1. User uploads document via Streamlit or SharePoint sync
2. FastAPI receives upload at `/api/v1/ingest`
3. `DatabricksSink.ingest_bytes()`:
   - Uploads file to ADLS Gen2: `raw/{source}/{year}/{month}/{day}/{doc_id}/{filename}`
   - Creates metadata JSON: `raw/{source}/{year}/{month}/{day}/{doc_id}/{filename}.metadata.json`
   - Triggers Databricks job (if configured)
4. Databricks job executes:
   - Notebook 01: Ingest to Bronze
   - Notebook 02: Validate & Transform to Silver
   - Notebook 03: Embed & Register to Gold

### Query Flow

1. User submits query via Streamlit or API
2. FastAPI receives at `/api/v1/query`
3. LangGraph agent workflow:
   - Analyze query
   - Retrieve documents (via `WeaviateRetrievalAdapter` or `DatabricksRetrievalAdapter`)
   - Validate documents
   - Synthesize answer via OpenAI
4. Return response with citations and audit trail

## Security

### Authentication & Authorization

- **AKS → Key Vault**: Workload Identity (managed identity)
- **AKS → ADLS**: Workload Identity with RBAC
- **Databricks → ADLS**: Service Principal with RBAC
- **AKS → Databricks**: Managed Identity (Phase 2)

### Network Security

- **Phase 1**: Public ingress with Istio hardening
- **Phase 2**: Private endpoints, VNet integration

### Secrets Management

- All secrets stored in Azure Key Vault
- Mounted via CSI driver to pods
- Never committed to code

## Observability

### LLMOps
- Langfuse: Traces all LangGraph steps
- Query/response logging
- Performance metrics

### Infrastructure
- Azure Monitor: AKS metrics and logs
- Log Analytics: Centralized logging
- Databricks: Audit logs and job history

## Scaling Considerations

### Horizontal Pod Autoscaling (HPA)
- CPU: 70% threshold
- Memory: 80% threshold
- Min replicas: 2 (configurable per env)
- Max replicas: 10-20 (configurable per env)

### Databricks Clusters
- Auto-scaling enabled
- Job clusters for ELT pipeline
- All-purpose clusters for ad-hoc queries

## Environment Configuration

### Development
- `CLOUD_MODE=local`
- Single replica
- Weaviate for retrieval
- Simplified networking

### Staging
- `CLOUD_MODE=databricks`
- 2 replicas
- Databricks Vector Search (Phase 2)
- Full Istio configuration

### Production
- `CLOUD_MODE=databricks`
- 3+ replicas with HPA
- Private endpoints (Phase 2)
- Strict mTLS
- Enhanced monitoring

