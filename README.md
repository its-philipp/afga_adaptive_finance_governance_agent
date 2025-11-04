# Adaptive Finance Governance Agent (AFGA)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Overview

The Adaptive Finance Governance Agent (AFGA) is a multi-agent agentic AI system for automated compliance and release checking of finance documents (invoices, expense reports). The system learns from human corrections and reduces the Human Correction Rate (H-CR) over time through adaptive memory.

## Architecture

**3 Specialized LangGraph Agents (A2A Protocol):**

- **TAA (Transaction Auditor Agent)**: Client/orchestrator - receives transactions, performs risk scoring, delegates to PAA and EMA
- **PAA (Policy Adherence Agent)**: Server - RAG-based compliance checking against policy documents and adaptive memory
- **EMA (Exception Manager Agent)**: Server - manages HITL feedback loop and updates adaptive memory

**Key Technologies:**
- LangGraph for agent state management
- A2A Protocol for inter-agent communication
- SQLite for local memory persistence (upgradeable to Databricks)
- FastAPI as API Gateway
- Streamlit for UI with agent workflow visualization
- Langfuse for observability
- OpenRouter for LLM calls

## Quick Start

### Prerequisites

- Python 3.11+
- uv package manager

### Setup

```bash
# Install dependencies
uv sync

# Install with all features (UI, dev tools)
uv sync --extra all

# Create environment configuration
cp .env.example .env
# Edit .env and add your OpenRouter API key

# Activate virtual environment
source .venv/bin/activate
```

### Run Services Locally

1. Start FastAPI backend:
   ```bash
   uvicorn src.api.main:app --reload
   ```

2. Start Streamlit UI:
   ```bash
   streamlit run streamlit_app/app.py
   ```

3. Navigate to http://localhost:8501

## Key Features

### 🤖 Multi-Agent System
- **TAA**: Orchestrates transaction flow and risk assessment
- **PAA**: Performs compliance checking with RAG and memory
- **EMA**: Manages human feedback and adaptive learning

### 🧠 Adaptive Memory
- Learns from human corrections
- Stores institutional knowledge in SQLite (local) or Databricks (production)
- Context Retention Score (CRS) tracks memory effectiveness

### 📄 Document Intelligence
- Upload receipts/invoices in PDF or image format
- AI extraction using Vision LLM (GPT-4 Vision)
- Supports German invoices ("Rechnung", "Spesenabrechnung")
- Handles handwriting, photos, scans, and multi-page PDFs

### 📊 KPI Dashboard
- **H-CR (Human Correction Rate)**: Measures learning progress
- **CRS (Context Retention Score)**: Memory effectiveness
- **ATAR (Automated Transaction Approval Rate)**: Operational efficiency
- **Audit Traceability**: Complete decision transparency

### 🔍 Agent Workflow Visualization
- Real-time LangGraph state visualization
- A2A message flow tracking
- Complete audit trail for all decisions

## API Endpoints

### Transaction Processing
- `POST /api/v1/transactions/submit` - Submit structured invoice (JSON)
- `POST /api/v1/transactions/upload-receipt` - Upload receipt/invoice (PDF/Image) with AI extraction
- `GET /api/v1/transactions/{transaction_id}` - Get transaction status
- `POST /api/v1/transactions/{transaction_id}/hitl` - Submit human feedback

### KPIs and Analytics
- `GET /api/v1/kpis/current` - Current KPI values
- `GET /api/v1/kpis/trend` - KPI trends over time

### Memory Management
- `GET /api/v1/memory/exceptions` - List learned exceptions
- `POST /api/v1/memory/exceptions` - Add exception (admin)

### Health Check
- `GET /api/v1/health` - Service health status

## Project Structure

```
adaptive_finance_governance_agent/
├── src/
│   ├── agents/          # TAA, PAA, EMA agents with A2A integration
│   ├── api/             # FastAPI gateway
│   ├── core/            # Config, observability, LLM clients
│   ├── models/          # Pydantic schemas
│   ├── services/        # Risk scoring, policy retrieval, KPI tracking
│   └── db/              # SQLite memory operations
├── data/
│   ├── mock_invoices/   # Synthetic test data
│   ├── policies/        # Policy documents
│   └── memory.db        # Adaptive memory (SQLite)
├── streamlit_app/       # Streamlit UI
├── tests/               # Unit and integration tests
└── docs/                # Documentation
```

## Development Roadmap

### Phase 1: Local MVP ✅ **COMPLETE**
- [x] Multi-agent architecture with LangGraph
- [x] A2A protocol implementation
- [x] SQLite adaptive memory
- [x] KPI tracking
- [x] Streamlit UI with workflow visualization
- [x] FastAPI gateway (15+ endpoints)
- [x] 50 mock invoices + 5 policy documents
- [x] Unit and integration tests
- [x] Complete documentation

### Phase 2: Databricks Integration (Future)
- [ ] Memory migration to Delta Lake
- [ ] Unity Catalog setup
- [ ] PII detection and governance

### Phase 3: AKS Deployment (Future)
- [ ] Terraform IaC
- [ ] Helm charts
- [ ] Istio service mesh
- [ ] ArgoCD GitOps

## Success Criteria

- ✅ 3 LangGraph agents communicate via A2A protocol
- ✅ Transaction processing with approve/reject/HITL decisions
- ✅ Adaptive memory stores and retrieves learned exceptions
- ✅ KPIs calculated and displayed in Streamlit
- ✅ Streamlit UI with 4 complete pages
- ✅ FastAPI gateway with 15+ endpoints
- ✅ Unit and integration tests passing
- ✅ 100% audit trail traceability
- ⏳ H-CR decreases over time (ready to validate with demo)

## Cost Estimate

- **Local Development**: $0 (Mac M2)
- **With Databricks**: ~$50/month
- **Full Production (AKS)**: ~$200-250/month

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture and design
- [A2A_PROTOCOL.md](docs/A2A_PROTOCOL.md) - Agent communication specifications
- [KPI_DEFINITIONS.md](docs/KPI_DEFINITIONS.md) - KPI formulas and interpretation

## License

MIT License

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

