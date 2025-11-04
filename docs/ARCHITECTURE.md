# AFGA Architecture

## System Overview

The Adaptive Finance Governance Agent (AFGA) is a multi-agent AI system for automated compliance checking of financial transactions. The system learns from human corrections through adaptive memory, reducing the Human Correction Rate (H-CR) over time.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                      Streamlit UI (Frontend)                  │
│  ┌──────────┬─────────────┬───────────┬──────────────────┐   │
│  │Transaction│  Agent      │    KPI    │    Memory        │   │
│  │  Review   │  Workflow   │ Dashboard │    Browser       │   │
│  └──────────┴─────────────┴───────────┴──────────────────┘   │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP REST API
┌────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Gateway                            │
│  POST /transactions/submit                                    │
│  GET  /transactions/{id}                                      │
│  POST /transactions/{id}/hitl                                 │
│  GET  /kpis/current                                           │
└────────────────────────┬─────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐  ┌────▼─────┐  ┌─────▼──────┐
│  TAA (Client)  │  │   PAA    │  │    EMA     │
│  Transaction   │  │  Policy  │  │  Exception │
│  Auditor Agent │  │ Adherence│  │  Manager   │
└───────┬────────┘  └────┬─────┘  └─────┬──────┘
        │ A2A            │ A2A           │ A2A
        │ Protocol       │ Protocol      │ Protocol
        ▼                ▼               ▼
┌──────────────────────────────────────────────┐
│           LangGraph Workflows                │
│  (State Machines with Audit Trails)          │
└──────────────────────────────────────────────┘
        │                │               │
        │                ▼               ▼
        │         ┌─────────────┐ ┌──────────┐
        │         │Policy       │ │ Adaptive │
        │         │Retriever    │ │ Memory   │
        │         │(RAG)        │ │ Manager  │
        │         └─────────────┘ └──────────┘
        │                │               │
        ▼                ▼               ▼
┌──────────────────────────────────────────────┐
│          SQLite Database (Local MVP)          │
│  ┌───────────────┬───────────┬──────────┐   │
│  │adaptive_memory│transactions│   kpis   │   │
│  └───────────────┴───────────┴──────────┘   │
└──────────────────────────────────────────────┘
        │                │               │
        ▼                ▼               ▼
┌──────────────────────────────────────────────┐
│          Observability (Langfuse)             │
│  - Traces    - Spans    - Generations        │
└──────────────────────────────────────────────┘
```

## Agent Responsibilities

### TAA (Transaction Auditor Agent) - Orchestrator

**Role:** Client agent that orchestrates the transaction processing workflow

**Workflow:**
1. Receive transaction (invoice)
2. Assess risk based on amount, vendor, category, PO status
3. Delegate to PAA for policy checking (via A2A)
4. Evaluate PAA response
5. Make final decision: Approve / Reject / HITL
6. Log complete audit trail

**Key Features:**
- Risk scoring with configurable thresholds
- A2A client for delegating to PAA and EMA
- Decision logic combining risk and policy compliance
- Complete audit trail for every transaction

### PAA (Policy Adherence Agent) - Compliance Checker

**Role:** Server agent that checks transactions against policies and memory

**Workflow:**
1. Receive compliance check request from TAA
2. Retrieve relevant policies (RAG with keyword matching)
3. Check adaptive memory for learned exceptions
4. Evaluate compliance using LLM
5. Return compliance result with confidence score

**Key Features:**
- RAG-based policy retrieval
- Adaptive memory integration
- LLM-based compliance evaluation
- Confidence scoring for uncertainty detection

### EMA (Exception Manager Agent) - Learning System

**Role:** Server agent that processes human feedback and updates memory

**Workflow:**
1. Receive HITL feedback (human override)
2. Analyze correction type with LLM
3. Update adaptive memory if applicable
4. Calculate H-CR KPI
5. Return memory update confirmation

**Key Features:**
- HITL feedback processing
- LLM-based correction analysis
- Adaptive memory updates
- KPI calculation for learning metrics

## Communication: A2A Protocol

The agents communicate using the **A2A (Agent-to-Agent) protocol**, an industry standard for multi-agent systems:

- **Agent Cards:** Each agent publishes its capabilities
- **Agent Executors:** Server agents (PAA, EMA) implement executors
- **Task Client:** TAA uses TaskClient to invoke server agents
- **Streaming:** Agents can stream progress updates
- **Structured Messages:** JSON-based message passing

## Data Flow

### Transaction Processing Flow

```
1. User submits invoice via Streamlit
   ↓
2. FastAPI creates transaction, calls TAA
   ↓
3. TAA assesses risk
   ↓
4. TAA → PAA (A2A): Check compliance
   ↓
5. PAA retrieves policies (RAG)
   ↓
6. PAA checks memory for exceptions
   ↓
7. PAA evaluates with LLM
   ↓
8. PAA → TAA: Compliance result
   ↓
9. TAA makes final decision
   ↓
10. Save to database
    ↓
11. Return result to user
```

### HITL Feedback Flow

```
1. Human overrides decision via Streamlit
   ↓
2. FastAPI calls EMA (A2A)
   ↓
3. EMA analyzes correction with LLM
   ↓
4. EMA updates adaptive memory
   ↓
5. EMA calculates H-CR KPI
   ↓
6. Memory available for next PAA call
```

## Storage Schema

### adaptive_memory Table

```sql
CREATE TABLE adaptive_memory (
    exception_id TEXT PRIMARY KEY,
    vendor TEXT,
    category TEXT,
    rule_type TEXT,  -- 'exception', 'learned_threshold', 'custom_rule'
    description TEXT,
    condition TEXT,  -- JSON
    applied_count INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 1.0,
    created_at TIMESTAMP,
    last_applied_at TIMESTAMP
);
```

### transactions Table

```sql
CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,
    invoice_id TEXT,
    invoice_data TEXT,  -- JSON
    risk_score REAL,
    risk_level TEXT,
    paa_decision TEXT,
    final_decision TEXT,
    human_override INTEGER,
    processing_time_ms INTEGER,
    audit_trail TEXT,  -- JSON
    trace_id TEXT,
    created_at TIMESTAMP
);
```

### kpis Table

```sql
CREATE TABLE kpis (
    date TEXT PRIMARY KEY,
    total_transactions INTEGER,
    human_corrections INTEGER,
    hcr REAL,  -- Human Correction Rate (%)
    crs REAL,  -- Context Retention Score (%)
    atar REAL, -- Automated Transaction Approval Rate (%)
    avg_processing_time_ms INTEGER,
    audit_traceability_score REAL
);
```

## Technology Stack

- **Language:** Python 3.11+
- **Agent Framework:** LangGraph (state machines)
- **A2A Protocol:** a2a-sdk
- **LLM Router:** OpenRouter (GPT-4o, Claude, Llama)
- **Observability:** Langfuse
- **API Gateway:** FastAPI
- **Frontend:** Streamlit
- **Database:** SQLite (local), Delta Lake (production)
- **Embedding:** sentence-transformers (for future RAG upgrade)

## Key Design Patterns

### 1. State Machine Pattern (LangGraph)

Each agent is a deterministic state machine with:
- Typed state (TypedDict)
- Nodes (functions that transform state)
- Edges (transitions between nodes)
- Audit trail accumulation

### 2. A2A Protocol Pattern

- **Client-Server:** TAA is client, PAA and EMA are servers
- **Task-based:** Each request is a task with lifecycle
- **Streaming:** Agents can stream progress updates
- **Artifacts:** Results returned as structured artifacts

### 3. Adaptive Memory Pattern

- **Write:** EMA adds exceptions based on human feedback
- **Read:** PAA queries memory during compliance checks
- **Update:** Usage statistics (applied_count, success_rate) tracked
- **Prune:** Low success rate exceptions can be deprecated

### 4. Observability Pattern

- **Traces:** One per transaction (end-to-end)
- **Spans:** One per agent step (risk, policy check, memory update)
- **Generations:** LLM calls with token usage
- **A2A Messages:** Inter-agent communication logged

## Deployment Modes

### Phase 1: Local MVP (Current)

- SQLite database
- In-process A2A (no network calls)
- Local Streamlit + FastAPI
- Mock invoice data

### Phase 2: Databricks Integration

- Delta Lake for adaptive memory
- Unity Catalog for governance
- ADLS Gen2 for document storage
- PII detection and redaction

### Phase 3: AKS Production

- Kubernetes deployment
- Istio service mesh for A2A security
- Azure Monitor for observability
- GitOps with ArgoCD

## Security Considerations

- **API Authentication:** JWT tokens (production)
- **A2A Encryption:** TLS + Istio mTLS (production)
- **PII Protection:** Redaction in logs and memory
- **Access Control:** Unity Catalog policies (Databricks)
- **Audit Trail:** Complete traceability for compliance

## Performance Targets

- **Transaction Processing:** < 3 seconds (p95)
- **HITL Feedback:** < 2 seconds (p95)
- **KPI Calculation:** < 1 second (daily batch)
- **Memory Query:** < 100ms (p95)
- **Throughput:** 100 transactions/minute (production)

## Future Enhancements

1. **Embeddings-based RAG:** Upgrade from keyword to semantic search
2. **Multi-tenancy:** Support multiple organizations
3. **Real-time KPIs:** Stream processing for live dashboards
4. **ML-based Risk Scoring:** Train risk model on historical data
5. **Graph RAG:** Policy relationships and dependencies
6. **Voice Interface:** Streamlit voice input for HITL feedback

