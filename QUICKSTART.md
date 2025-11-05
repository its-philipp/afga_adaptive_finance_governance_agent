# AFGA Quick Start Guide

Get the Adaptive Finance Governance Agent running in 5 minutes!

## Prerequisites

- Python 3.11+
- uv package manager
- Terminal/Command line

## Step 1: Install System Dependencies (for PDF support)

**Note:** For local Mac M2 development, install poppler. For Docker deployment, poppler is included in the image.

**macOS (Local Development - Recommended):**
```bash
brew install poppler
```

**Ubuntu/Linux:**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
- Download poppler: https://github.com/oschwartz10612/poppler-windows

**Docker:** Poppler is pre-installed in the Docker image (see Dockerfile)

## Step 2: Install Python Dependencies

```bash
cd adaptive_finance_governance_agent
uv sync --extra all
```

This installs:
- Core dependencies (LangGraph, FastAPI, etc.)
- Streamlit UI
- Document processing (pdf2image, pillow)
- Development tools

## Step 3: Configure Environment

```bash
cp env.example .env
```

Edit `.env` and add your OpenRouter API key:

```bash
OPENROUTER_API_KEY=your_key_here
```

**Get a free API key:** https://openrouter.ai/

**Note:** Vision LLM (for PDF/image uploads) requires GPT-4 Vision access via OpenRouter

## Step 4: Start the System

### Option A: Direct Start (Recommended for Mac M2)

**This is the simplest way - no Docker needed!**

```bash
./start.sh
```

This automatically:
- Activates virtual environment
- Generates mock data (if needed)
- Starts FastAPI backend
- Starts Streamlit frontend

### Option B: Manual Start (Two Terminals)

Terminal 1 - Backend:
```bash
source .venv/bin/activate
uvicorn src.api.main:app --reload
```

Terminal 2 - Frontend:
```bash
source .venv/bin/activate
streamlit run streamlit_app/app.py
```

### Option C: Docker Compose (Optional - For Deployment)

**Note:** Only use Docker if you want to test containerization. Not needed for local development.

```bash
# Build and start
docker-compose up --build

# Access same URLs
# Streamlit: http://localhost:8501
# API: http://localhost:8000
```

**When to use Docker:**
- Testing containerized deployment
- Deploying to cloud
- Multi-environment setups

**When NOT to use Docker:**
- Local Mac M2 development (use direct start instead)
- Quick testing and iteration
- Current MVP phase

## Step 5: Access the UI

Open your browser to:
- **Streamlit UI:** http://localhost:8501
- **API Docs:** http://localhost:8000/docs

## Step 6: Try It Out!

### Option A: Upload Real Receipt/Invoice (NEW!)

1. Go to **📋 Transaction Review** page
2. Select **"Upload Receipt/Invoice (PDF/Image)"**
3. Upload any PDF or image of an invoice/receipt
4. Click **"🔍 Extract & Process Invoice"**
5. Watch AI extract the data
6. View the decision and audit trail

### Option B: Use Mock Data

1. Go to **📋 Transaction Review** page
2. Select **"Mock Invoices (Test Data)"**
3. Choose an invoice from the dropdown
4. Click **"🚀 Process Transaction"**
5. View the decision and audit trail

### Provide HITL Feedback

1. If transaction requires human review
2. Go to **👤 Human Review (HITL)** tab
3. Make your decision (Approve/Reject)
4. Provide reasoning
5. Check "Create Exception Rule" to teach the system

### Monitor Learning

1. Go to **📊 KPI Dashboard**
2. Watch H-CR (Human Correction Rate) decrease
3. See CRS (Context Retention Score) increase
4. View ATAR (Automation Rate) improve

### Explore Memory

1. Go to **🧠 Memory Browser**
2. View learned exceptions
3. See memory statistics
4. Browse by vendor/category

## Common Tasks

### Test with Mock Invoices

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/demo/process-mock-invoice \
  -H "Content-Type: application/json" \
  -d '{"invoice_file": "INV-0001.json"}'

# Via UI
- Go to Transaction Review
- Select from dropdown
- Process
```

### View Current KPIs

```bash
curl http://localhost:8000/api/v1/kpis/current
```

### Check System Health

```bash
curl http://localhost:8000/api/v1/health
```

## Troubleshooting

### Backend won't start

```bash
# Check logs
tail -f backend.log

# Verify port is free
lsof -i :8000

# Restart
pkill -f uvicorn
uvicorn src.api.main:app --reload
```

### Frontend won't start

```bash
# Check port
lsof -i :8501

# Restart
pkill -f streamlit
streamlit run streamlit_app/app.py
```

### No mock data

```bash
# Generate manually
source .venv/bin/activate
python scripts/generate_mock_data.py
```

### Database issues

```bash
# Reset database
rm data/memory.db

# Database will be recreated on next transaction
```

## What's Next?

### Run the Full Demo

Process all 50 mock invoices to see the system learn:

1. Go through invoices one by one
2. Provide HITL feedback on edge cases
3. Watch KPIs improve
4. See memory grow

### Validate Learning

Expected results after 50 transactions:
- H-CR: Decreases from ~30% to < 15%
- CRS: Increases from 0% to > 50%
- ATAR: Increases from ~40% to > 60%

### Explore the Code

- `src/agents/` - TAA, PAA, EMA implementations
- `src/api/` - FastAPI endpoints
- `streamlit_app/` - UI pages
- `docs/ARCHITECTURE.md` - System design

## Key Endpoints

### Transactions
- `POST /api/v1/transactions/submit` - Submit invoice
- `GET /api/v1/transactions/{id}` - Get transaction
- `POST /api/v1/transactions/{id}/hitl` - HITL feedback

### KPIs
- `GET /api/v1/kpis/current` - Current metrics
- `GET /api/v1/kpis/trend` - Historical trends
- `GET /api/v1/kpis/summary` - Comprehensive summary

### Memory
- `GET /api/v1/memory/exceptions` - List exceptions
- `GET /api/v1/memory/stats` - Memory statistics

### Demo
- `GET /api/v1/demo/list-mock-invoices` - List test data
- `POST /api/v1/demo/process-mock-invoice` - Process test invoice

## Performance Notes

- Transaction processing: 2-5 seconds
- Memory queries: < 100ms
- KPI calculations: < 1 second
- Local SQLite: Suitable for 1000s of transactions

## Next Steps

After mastering the local MVP:

1. **Phase 2:** Migrate to Databricks
   - Delta Lake for memory
   - Unity Catalog for governance
   - PII detection

2. **Phase 3:** Deploy to AKS
   - Kubernetes orchestration
   - Istio service mesh
   - Real HTTP-based A2A

## Support

- Check `docs/` for detailed documentation
- Review `PROGRESS.md` for implementation details
- See `MVP_STATUS.md` for system overview

---

**Enjoy exploring AFGA!** 🤖

For questions or issues, review the architecture docs or check the logs.

