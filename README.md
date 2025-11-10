# Adaptive Finance Governance Agent (AFGA)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Overview

Adaptive Finance Governance Agent (AFGA) is a production-ready, multi-agent compliance assistant for finance operations. It automates invoice auditing, enforces policy adherence, and learns from human reviewers via adaptive memory so the Human Correction Rate (H-CR) drops over time.

The system now ships with **real HTTP-based A2A communication** between agents, **MCP resources/tools** for shared knowledge, end-to-end observability, and a Streamlit UI tailored for demos.

## Architecture

AFGA runs three specialized LangGraph agents connected through a hybrid protocol stack:

- **TAA – Transaction Auditor Agent** (client): orchestrates the workflow, scores risk, and calls downstream agents through the A2A protocol.
- **PAA – Policy Adherence Agent** (server): exposes an A2A executor that consults MCP policy resources + RAG to evaluate compliance.
- **EMA – Exception Manager Agent** (server): processes HITL feedback, updates adaptive memory through MCP tools, and feeds improvements back into PAA.

**Key technologies**
- LangGraph state machines for each agent
- A2A HTTP/JSON-RPC for cross-agent delegation
- MCP (Model Context Protocol) for policies, adaptive memory, and KPI tooling
- FastAPI gateway, Streamlit front-end, Langfuse observability
- SQLite (local) with upgrade path to Databricks Delta for persistence

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/HYBRID_A2A_MCP.md`](docs/HYBRID_A2A_MCP.md) for full diagrams.

## Quick Start

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- OpenRouter API key (or compatible LLM provider)

### Setup & Run
```bash
# Install dependencies
uv sync --extra all

# Copy environment template and add secrets (no keys are committed)
cp .env.example .env
$EDITOR .env

# Activate virtual environment
source .venv/bin/activate

# Start FastAPI backend
uvicorn src.api.main:app --reload

# In a second terminal start Streamlit UI
streamlit run streamlit_app/app.py
```
Navigate to http://localhost:8501 to explore the workflow dashboard.

## Flagship Capabilities

### 🤖 Multi-Agent Orchestration
- TAA delegates to PAA/EMA over authenticated A2A HTTP calls.
- Each agent exposes LangGraph nodes with typed state transitions.

### 🧠 Adaptive Memory
- HITL feedback creates learned exceptions persisted via MCP tools.
- Context Retention Score (CRS) and Human Correction Rate (H-CR) track learning effectiveness.

### 📄 Document Intelligence
- Upload PDF or image receipts for extraction and validation.
- Zero-width characters are normalized for clean UI rendering.

### 🛡️ AI Governance & Auditability
- Input/output governance, redaction, and KPI tracking.
- Langfuse captures traces, spans, and LLM generations.

### 📊 KPIs & Dashboarding
- Streamlit visualizes KPIs (H-CR, CRS, ATAR), learned exceptions, and RAG transparency.

## API Surface (selected endpoints)
- `POST /api/v1/transactions/submit`
- `POST /api/v1/transactions/upload-receipt`
- `POST /api/v1/transactions/{transaction_id}/hitl`
- `GET /api/v1/kpis/current`
- `GET /api/v1/memory/exceptions`

## Project Layout
```
adaptive_finance_governance_agent/
├── src/                  # Agents, FastAPI gateway, services, persistence
├── streamlit_app/        # Streamlit UI + workflow visualizations
├── tests/                # Unit & integration tests
├── data/
│   ├── mock_invoices/    # Synthetic samples (checked in)
│   ├── policies/         # Policy corpora (checked in)
│   └── uploads/          # Runtime uploads (.gitkeep only)
├── docs/                 # Living docs (A2A, MCP, governance, vision)
│   └── archive/          # Historical status reports and legacy notes
├── scripts/              # Developer utilities (DB migrate, mock data)
├── env.example           # Configuration template (no secrets)
└── azure_extension/      # Optional Azure/AKS deployment assets
```
Runtime databases (e.g., `data/memory.db`) and uploaded receipts are ignored by git so the repository stays clean.

## Development Status
- ✅ Local MVP with hybrid A2A + MCP agents
- ✅ Adaptive memory + KPI dashboard
- ✅ Streamlit + FastAPI demo experience
- ✅ Extensive documentation (see `/docs`)
- 🚧 Optional Azure/Databricks deployment scripts live under `azure_extension/`

## Documentation Index
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) – system design
- [`docs/HYBRID_A2A_MCP.md`](docs/HYBRID_A2A_MCP.md) – protocol deep dive
- [`docs/A2A_VS_MCP.md`](docs/A2A_VS_MCP.md) – comparison guide
- [`docs/DOCUMENT_EXTRACTION.md`](docs/DOCUMENT_EXTRACTION.md) – vision pipeline
- [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) – AI governance and audit trail
- [`docs/SETUP_VISION.md`](docs/SETUP_VISION.md) – enabling vision models
- [`docs/archive`](docs/archive) – historical deliverables and status logs
- [`azure_extension/README.md`](azure_extension/README.md) – cloud deployment playbooks

## Contributing
Pull requests are welcome! Please open an issue describing the change and ensure `uv run pytest` and `ruff` pass locally.

## License
MIT License

