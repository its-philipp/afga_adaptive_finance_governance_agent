"""Agent Workflow Visualization Page - View multi-agent system architecture and flow."""

import os

import httpx
import streamlit as st

from components.chat_assistant import render_chat_sidebar

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="Agent Workflow", page_icon="🔄", layout="wide")

# Hide default Streamlit navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔄 Agent Workflow Visualization")
st.markdown("Understand how the three agents (TAA, PAA, EMA) work together using hybrid A2A + MCP protocols.")

# Sidebar
with st.sidebar:
    st.title("🤖 AFGA")
    st.caption("Adaptive Finance Governance Agent")
    st.markdown("---")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_📋_Transaction_Review.py", label="Transaction Review", icon="📋")
    st.page_link("pages/2_🔄_Agent_Workflow.py", label="Agent Workflow", icon="🔄")
    st.page_link("pages/3_📊_KPI_Dashboard.py", label="KPI Dashboard", icon="📊")
    st.page_link("pages/4_🧠_Memory_Browser.py", label="Memory Browser", icon="🧠")
    st.page_link("pages/5_📖_Policy_Viewer.py", label="Policy Viewer", icon="📖")
    st.page_link("pages/6_🛡️_AI_Governance.py", label="AI Governance", icon="🛡️")

    render_chat_sidebar("Agent Workflow")

# Architecture Overview
st.markdown("## 🏗️ System Architecture")

st.markdown("""
```
┌──────────────────────────────────────────────────────────────┐
│                    Streamlit UI (Frontend)                   │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP REST API
┌────────────────────────▼─────────────────────────────────────┐
│                    FastAPI Gateway                           │
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
│  (6 nodes)        (5 nodes)      (4 nodes)   │
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
│          SQLite Database (Local MVP)         │
│  ┌───────────────┬────────────┬──────────┐   │
│  │adaptive_memory│transactions│   kpis   │   │
│  └───────────────┴────────────┴──────────┘   │
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

# Hybrid A2A + MCP Architecture
st.markdown("## 🔗 Hybrid A2A + MCP Architecture")

st.markdown("""
AFGA uses **two industry-standard protocols** working together, as recommended by MIT GenAI research:

### 1. A2A Protocol (Agent-to-Agent Communication)

**Used for:** Inter-agent communication

- **TAA → PAA:** A2A task delegation for compliance checking
- **TAA → EMA:** A2A task delegation for HITL feedback

**Key Concepts:**
- **Agent Cards:** Each agent publishes its capabilities
  - TAA Card: Orchestration capabilities
  - PAA Card: Policy checking capabilities  
  - EMA Card: Learning capabilities

- **Agent Executors:** Server agents (PAA, EMA) implement executors
  - Receive tasks from TAA
  - Execute LangGraph workflows
  - Stream progress updates
  - Return structured artifacts

- **Task Lifecycle:** submitted → working → completed

### 2. MCP Protocol (Model Context Protocol)

**Used for:** Agent access to resources and tools

- **PAA → Policy Resources:** Accesses company policies via MCP resources
  - `policy://vendor_approval_policy`
  - `policy://expense_limits_policy`
  - `policy://po_matching_requirements`
  - etc.

- **EMA → Memory Tools:** Calls memory operations via MCP tools
  - `add_exception()` - Create learned rules
  - `query_exceptions()` - Search memory
  - `update_exception_usage()` - Track usage
  - `get_memory_stats()` - Memory statistics

**Benefits:**
- ✅ Clean abstraction (agents don't touch databases directly)
- ✅ Standardized interfaces (MCP resources/tools)
- ✅ Observable (MCP calls are logged)
- ✅ Testable (can mock MCP servers)

### Why Both Protocols?

**A2A** = Agent orchestration (TAA delegates to PAA/EMA)  
**MCP** = Data access (PAA/EMA access policies/memory)

This hybrid approach follows MIT GenAI research recommendations for scalable, governable AI systems.
""")

# Get Agent Cards
st.markdown("### 📋 Agent Cards (A2A Discovery)")

def render_agent_card(card: dict | None) -> None:
    if not card:
        st.info("Agent card unavailable")
        return

    st.markdown(f"**Name:** {card.get('name', 'Unknown Agent')}")
    st.markdown(f"**Description:** {card.get('description', 'N/A')}")
    st.markdown(f"**Version:** {card.get('version', 'N/A')}")
    if card.get("url"):
        st.caption(f"Endpoint: {card['url']}")

    default_inputs = card.get("defaultInputModes") or card.get("default_input_modes") or []
    default_outputs = card.get("defaultOutputModes") or card.get("default_output_modes") or []
    if default_inputs or default_outputs:
        st.markdown("**Default Modes:**")
        if default_inputs:
            st.write("• Input: " + ", ".join(default_inputs))
        if default_outputs:
            st.write("• Output: " + ", ".join(default_outputs))

    capabilities = card.get("capabilities") or {}
    st.markdown("**Capabilities:**")
    if isinstance(capabilities, dict) and capabilities:
        for key, enabled in capabilities.items():
            if key is None:
                continue
            label = str(key).replace("_", " ").replace("-", " ").title()
            icon = "✅" if enabled else "⏸️"
            st.write(f"{icon} {label}")
    elif isinstance(capabilities, list) and capabilities:
        for cap in capabilities:
            if isinstance(cap, dict):
                name = cap.get("name") or cap.get("id") or "Capability"
                with st.expander(f"🔧 {name}"):
                    st.write(cap.get("description", "No description"))
    else:
        st.write("No explicit capabilities declared")

    skills = card.get("skills") or []
    if skills:
        st.markdown("**Skills:**")
        for skill in skills:
            if not isinstance(skill, dict):
                continue
            title = skill.get("name") or skill.get("id") or "Skill"
            with st.expander(f"🧠 {title}"):
                st.write(skill.get("description", "No description"))
                examples = skill.get("examples")
                if examples:
                    st.markdown("**Examples:**")
                    for example in examples:
                        st.write(f"- {example}")
    st.markdown("---")

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{API_BASE_URL}/agents/cards")

        if response.status_code == 200:
            cards = response.json()

            tab1, tab2, tab3 = st.tabs(["TAA Card", "PAA Card", "EMA Card"])

            with tab1:
                render_agent_card(cards.get("taa"))

            with tab2:
                render_agent_card(cards.get("paa"))

            with tab3:
                render_agent_card(cards.get("ema"))
        else:
            st.error(f"Failed to load agent cards: {response.status_code} {response.text}")
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

# Removed AI Governance section - now on separate page (6_🛡️_AI_Governance.py)
st.markdown("---")
st.markdown("## 🛡️ AI Governance & Safety")

st.info("""
🔒 **AI Governance controls are active for all LLM interactions!**

For detailed governance metrics, audit logs, and safety features, visit the **AI Governance** page.
""")

st.page_link("pages/6_🛡️_AI_Governance.py", label="Go to AI Governance Page →", icon="🛡️")

st.markdown("---")
st.markdown("## 💡 Next Steps")

st.markdown("""
**To explore AFGA:**

1. **📋 Transaction Review** - Submit invoices and see the TAA → PAA workflow in action
2. **📊 KPI Dashboard** - Monitor H-CR, CRS, ATAR metrics
3. **🧠 Memory Browser** - Inspect learned exceptions from HITL feedback
4. **🛡️ AI Governance** - Review audit logs and governance controls

**Key Features:**
- Real-time compliance checking
- Adaptive learning from human feedback
- Complete audit trails
- Multi-agent coordination (A2A protocol)
""")

st.markdown("---")
st.caption("AFGA Agent Workflow | LangGraph + A2A + MCP Hybrid Architecture")
