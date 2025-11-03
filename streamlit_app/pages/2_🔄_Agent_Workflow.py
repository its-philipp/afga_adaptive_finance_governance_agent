"""Agent Workflow Visualization Page - View multi-agent system architecture and flow."""

import os

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="Agent Workflow", page_icon="🔄", layout="wide")

st.title("🔄 Agent Workflow Visualization")
st.markdown("Understand how the three agents (TAA, PAA, EMA) work together using A2A/MCP protocol.")

# Architecture Overview
st.markdown("## 🏗️ System Architecture")

st.markdown("""
```
┌──────────────────────────────────────────────────────────────┐
│                    Streamlit UI (Frontend)                    │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP REST API
┌────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Gateway                            │
│  /transactions/submit   /transactions/{id}/hitl   /kpis/*    │
└────────────────────────┬─────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐  ┌────▼─────┐  ┌─────▼──────┐
│  TAA (Client)  │  │   PAA    │  │    EMA     │
│  Transaction   │  │  Policy  │  │  Exception │
│  Auditor Agent │  │ Adherence│  │  Manager   │
│                │  │  Agent   │  │   Agent    │
└───────┬────────┘  └────┬─────┘  └─────┬──────┘
        │ A2A            │ A2A           │ A2A
        │ Protocol       │ Protocol      │ Protocol
        ▼                ▼               ▼
┌──────────────────────────────────────────────┐
│           LangGraph State Machines           │
│  (6 nodes)        (5 nodes)      (4 nodes)  │
└──────────────────────────────────────────────┘
        │                │               │
        │                ▼               ▼
        │         ┌─────────────┐ ┌──────────┐
        │         │  Policy     │ │ Adaptive │
        │         │  Retriever  │ │  Memory  │
        │         │  (RAG)      │ │  Manager │
        │         └─────────────┘ └──────────┘
        │                │               │
        ▼                ▼               ▼
┌──────────────────────────────────────────────┐
│          SQLite Database (Local MVP)          │
│  ┌───────────────┬───────────┬──────────┐   │
│  │adaptive_memory│transactions│   kpis   │   │
│  └───────────────┴───────────┴──────────┘   │
└──────────────────────────────────────────────┘
```
""")

# Agent Details
st.markdown("## 🤖 Agent Responsibilities")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### TAA")
    st.markdown("**Transaction Auditor Agent**")
    st.markdown("📌 **Role:** Orchestrator (Client)")
    st.markdown("""
    **Workflow:**
    1. Receive transaction
    2. Assess risk
    3. Delegate to PAA (A2A)
    4. Evaluate PAA response
    5. Make final decision
    6. Log audit trail
    
    **LangGraph Nodes:** 6
    - receive_transaction
    - assess_risk
    - delegate_to_paa
    - evaluate_paa_response
    - make_final_decision
    - log_audit_trail
    """)

with col2:
    st.markdown("### PAA")
    st.markdown("**Policy Adherence Agent**")
    st.markdown("📌 **Role:** Compliance Checker (Server)")
    st.markdown("""
    **Workflow:**
    1. Receive request from TAA
    2. Retrieve policies (RAG)
    3. Check adaptive memory
    4. Evaluate compliance (LLM)
    5. Return result to TAA
    
    **LangGraph Nodes:** 5
    - receive_request
    - retrieve_policies
    - check_memory
    - evaluate_compliance
    - return_response
    """)

with col3:
    st.markdown("### EMA")
    st.markdown("**Exception Manager Agent**")
    st.markdown("📌 **Role:** Learning System (Server)")
    st.markdown("""
    **Workflow:**
    1. Receive HITL feedback
    2. Analyze correction type
    3. Update adaptive memory
    4. Calculate H-CR KPI
    
    **LangGraph Nodes:** 4
    - receive_hitl_request
    - analyze_correction
    - update_memory
    - calculate_hcr
    """)

# Transaction Flow
st.markdown("## 📊 Transaction Processing Flow")

st.markdown("""
### Normal Transaction Flow

```
1. User submits invoice via Streamlit
   ↓
2. FastAPI creates transaction, calls TAA
   ↓
3. TAA receives transaction (Node 1)
   ↓
4. TAA assesses risk (Node 2)
   Risk Score: 0-100
   Risk Level: LOW / MEDIUM / HIGH / CRITICAL
   ↓
5. TAA → PAA (A2A) (Node 3)
   Message: {"invoice": {...}, "trace_id": "..."}
   ↓
6. PAA receives request (Node 1)
   ↓
7. PAA retrieves relevant policies (Node 2)
   Uses: Keyword-based RAG
   Returns: Top 5 policy chunks
   ↓
8. PAA checks adaptive memory (Node 3)
   Queries: Exceptions by vendor/category
   Applies: Learned rules
   ↓
9. PAA evaluates compliance with LLM (Node 4)
   Model: OpenRouter (GPT-4o/Claude/Llama)
   Output: is_compliant, violated_policies, confidence
   ↓
10. PAA → TAA: Compliance result (Node 5)
    ↓
11. TAA evaluates PAA response (Node 4)
    ↓
12. TAA makes final decision (Node 5)
    Decision: APPROVED / REJECTED / HITL
    ↓
13. TAA logs audit trail (Node 6)
    ↓
14. Save to database
    ↓
15. Return result to user
```

### HITL Feedback Flow (When Human Overrides)

```
1. Human provides feedback via Streamlit
   Decision: Approve or Reject
   Reasoning: Why override?
   Exception: Should learn?
   ↓
2. FastAPI calls EMA (A2A)
   ↓
3. EMA receives HITL request (Node 1)
   ↓
4. EMA analyzes correction type with LLM (Node 2)
   Classification: new_exception / policy_gap / one_time_override
   Should Learn: Yes/No
   ↓
5. EMA updates adaptive memory (Node 3)
   IF should_learn:
       - Create exception rule
       - Store in adaptive_memory table
       - Update applied_count, success_rate
   ↓
6. EMA calculates H-CR KPI (Node 4)
   Updates: kpis table
   ↓
7. Memory available for next PAA call
   PAA will query and apply this learned rule
   ↓
8. System improves over time!
```
""")

# A2A/MCP Protocol
st.markdown("## 🔗 A2A/MCP Protocol")

st.markdown("""
The agents communicate using the **Agent-to-Agent (A2A) Protocol** with **Model Context Protocol (MCP)** standards.

### Key Concepts

**Agent Cards:** Each agent publishes its capabilities
- TAA Card: Defines orchestration capabilities
- PAA Card: Defines policy checking capabilities
- EMA Card: Defines learning capabilities

**Agent Executors:** Server agents (PAA, EMA) implement executors
- Receive tasks from clients
- Execute LangGraph workflows
- Stream progress updates
- Return structured artifacts

**Task-Based Communication:**
- Each request is a "task" with a lifecycle
- States: submitted → working → completed
- Supports cancellation and error handling
""")

# Get Agent Cards
st.markdown("### 📋 Agent Cards (A2A Discovery)")

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{API_BASE_URL}/agents/cards")
        
        if response.status_code == 200:
            cards = response.json()
            
            tab1, tab2, tab3 = st.tabs(["TAA Card", "PAA Card", "EMA Card"])
            
            with tab1:
                if "taa" in cards:
                    taa_card = cards["taa"]
                    st.markdown(f"**Name:** {taa_card.get('name')}")
                    st.markdown(f"**Description:** {taa_card.get('description')}")
                    st.markdown(f"**Version:** {taa_card.get('version')}")
                    
                    capabilities = taa_card.get("capabilities", [])
                    st.markdown(f"**Capabilities:** {len(capabilities)}")
                    for cap in capabilities:
                        with st.expander(f"🔧 {cap.get('name')}"):
                            st.write(cap.get("description"))
            
            with tab2:
                if "paa" in cards:
                    paa_card = cards["paa"]
                    st.markdown(f"**Name:** {paa_card.get('name')}")
                    st.markdown(f"**Description:** {paa_card.get('description')}")
                    st.markdown(f"**Version:** {paa_card.get('version')}")
                    
                    capabilities = paa_card.get("capabilities", [])
                    st.markdown(f"**Capabilities:** {len(capabilities)}")
                    for cap in capabilities:
                        with st.expander(f"🔧 {cap.get('name')}"):
                            st.write(cap.get("description"))
            
            with tab3:
                if "ema" in cards:
                    ema_card = cards["ema"]
                    st.markdown(f"**Name:** {ema_card.get('name')}")
                    st.markdown(f"**Description:** {ema_card.get('description')}")
                    st.markdown(f"**Version:** {ema_card.get('version')}")
                    
                    capabilities = ema_card.get("capabilities", [])
                    st.markdown(f"**Capabilities:** {len(capabilities)}")
                    for cap in capabilities:
                        with st.expander(f"🔧 {cap.get('name')}"):
                            st.write(cap.get("description"))

except Exception as e:
    st.error(f"Error loading agent cards: {str(e)}")

# Observability
st.markdown("## 📊 Observability & Audit Trail")

st.markdown("""
Every transaction is fully traceable through **Langfuse** integration:

- **Traces:** Top-level workflow (one per transaction)
- **Spans:** Individual agent steps with timing
- **Generations:** LLM calls with token usage
- **A2A Messages:** Inter-agent communication logged

**Audit Trail Components:**
1. TAA steps (risk assessment, delegation, decision)
2. PAA steps (policy retrieval, memory check, evaluation)
3. A2A communication messages
4. LLM prompts and responses
5. Memory updates (if HITL feedback provided)
6. KPI recalculations

**Target:** 100% audit traceability for compliance
""")

# System Status
st.markdown("## 🔍 System Status")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Agent Status")
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                health = response.json()
                agents = health.get("agents", {})
                
                for agent, status in agents.items():
                    if status == "running":
                        st.success(f"✅ {agent.upper()}: Running")
                    else:
                        st.error(f"❌ {agent.upper()}: {status}")
    except:
        st.error("❌ Cannot connect to API")

with col2:
    st.markdown("### Services Status")
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                health = response.json()
                services = health.get("services", {})
                
                for service, status in services.items():
                    if status in ["running", "connected"]:
                        st.success(f"✅ {service.replace('_', ' ').title()}: {status.title()}")
                    else:
                        st.error(f"❌ {service.replace('_', ' ').title()}: {status}")
    except:
        st.error("❌ Cannot check services")

st.markdown("---")
st.caption("AFGA Agent Workflow | LangGraph + A2A/MCP Architecture")

