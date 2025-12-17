# 🗂️ Project Structure

Clean, organized structure with all active files. Archive folder contains historical documentation.

## Root Level

```
adaptive_finance_governance_agent/
├── README.md                   # Main project overview and quick start
├── QUICKSTART.md              # Detailed getting started guide
├── .env                       # Environment configuration (git-ignored)
├── .env.example               # Example environment template
├── pyproject.toml             # Python dependencies (uv)
├── start.sh                   # Start backend + frontend
└── stop.sh                    # Stop all services
```

## Core Application

```
src/                           # Backend (FastAPI)
├── agents/                    # Multi-agent system
│   ├── taa.py                # Transaction Assessment Agent
│   ├── paa.py                # Policy Alignment Agent
│   └── ema.py                # Exception Memory Agent
├── api/                      # REST API routes
├── db/                       # Database layer (SQLite)
├── services/                 # Business logic
└── main.py                   # FastAPI application

streamlit_app/                # Frontend (Streamlit)
├── app.py                    # Main entry point
└── pages/                    # Multi-page app
    ├── 01_Transaction_Assessment.py
    ├── 02_Policy_Compliance.py
    ├── 03_Exception_Memory.py
    ├── 04_Manual_HITL_Entry.py
    ├── 05_Automated_Processing.py
    ├── 06_Historical_Transactions.py
    ├── 07_Classifications_Dashboard.py
    └── 08_Settings.py
```

## Deployment

```
deployment/
├── README.md                 # Deployment options overview
├── docker/
│   ├── Dockerfile.backend    # Backend container
│   ├── Dockerfile.frontend   # Frontend container
│   └── docker-compose.yml    # Local multi-container setup
├── kubernetes/
│   ├── KUBERNETES_GUIDE.md   # K8s deployment details
│   ├── namespace.yaml
│   ├── backend-deployment.yaml
│   ├── frontend-deployment.yaml
│   ├── persistent-volume.yaml
│   └── ingress.yaml
└── helm/
    ├── README.md             # Helm + AKS guide
    ├── afga-agent/           # Production Helm chart
    │   ├── Chart.yaml
    │   ├── values.yaml
    │   └── templates/
    └── overlays/             # Environment-specific values
        ├── dev/
        └── prod/
```

## Data & Scripts

```
data/
├── memory.db                 # SQLite database (git-ignored)
├── mock_invoices/           # Test data
└── policies/                # Compliance policies

scripts/
├── generate_mock_invoices.py      # Create test data
├── batch_process_invoices.py     # Automated processing
├── export_to_csv.py              # Data export
└── test_api.py                   # API testing
```

## Documentation

```
docs/
├── README.md                      # Documentation index
├── ARCHITECTURE.md                # System design
├── CLASSIFICATIONS_GUIDE.md       # How to use classifications
├── GOVERNANCE.md                  # Governance patterns
├── A2A_VS_MCP.md                 # Agent protocols comparison
├── HYBRID_A2A_MCP.md             # Hybrid architecture
├── DOCUMENT_EXTRACTION.md         # OCR/extraction
└── SETUP_VISION.md               # Vision model setup
```

## Testing

```
tests/
├── test_agents.py           # Agent unit tests
├── test_api.py             # API endpoint tests
├── test_database.py        # Database tests
└── conftest.py             # Pytest configuration
```

## Archive

```
archive/                     # Historical files (not in git)
├── old_docs/               # Previous documentation
└── old_configs/            # Legacy configurations
```

## Key Files Explained

### Configuration
- `.env` - All secrets and API keys (NEVER commit)
- `.env.example` - Template showing required variables
- `pyproject.toml` - Python dependencies managed by `uv`
- `.gitignore` - Excludes logs, databases, archives, screenshots

### Scripts
- `start.sh` - Launches backend (port 8000) + frontend (port 8501)
- `stop.sh` - Gracefully stops both services using PID files

### Deployment
- **Docker** - For local development with containers
- **Kubernetes** - For self-managed K8s clusters (~$60/mo)
- **Helm** - For production AKS with autoscaling (~$200-400/mo)

## What's NOT Here (Intentionally)

- ❌ Databricks integration (disabled to save $100-135/month)
- ❌ Terraform configs (infrastructure-as-code removed)
- ❌ Azure DevOps pipelines (CI/CD not needed yet)
- ❌ Grafana dashboards (monitoring simplified)
- ❌ Old session/progress documentation (in archive/)

## Quick Navigation

| I want to... | Go to... |
|--------------|----------|
| Get started | [README.md](./README.md) → [QUICKSTART.md](./QUICKSTART.md) |
| Deploy locally | [deployment/docker/](./deployment/docker/) |
| Deploy to cloud | [deployment/README.md](./deployment/README.md) |
| Understand architecture | [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) |
| Use classifications | [docs/CLASSIFICATIONS_GUIDE.md](./docs/CLASSIFICATIONS_GUIDE.md) |
| Run tests | [tests/](./tests/) |
| Generate test data | [scripts/generate_mock_invoices.py](./scripts/generate_mock_invoices.py) |

## Cost Tracking

Current monthly costs (approximate):
- **OpenRouter API**: $10-50 (usage-based)
- **OpenAI API**: $5-20 (usage-based)
- **Langfuse**: $0 (hobby tier)
- **Azure Storage**: $0 (not using)
- **Databricks**: $0 (disabled)
- **Infrastructure**: $0 (running locally)

**Total**: ~$15-70/month for LLM APIs only

## File Count Summary

- Python source files: ~50
- Streamlit pages: 8
- Test files: 10+
- Deployment configs: 15+
- Documentation files: 10
- Scripts: 8

**Total active files**: ~100 (down from 150+ after cleanup)

---

Last updated: December 1, 2024
