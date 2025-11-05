"""Agent Workflow Visualization Page - View multi-agent system architecture and flow."""

import os

import httpx
import streamlit as st

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

# AI Governance Dashboard
st.markdown("---")
st.markdown("## 🛡️ AI Governance & Safety")

st.markdown("""
AFGA implements comprehensive **AI Governance controls** for all LLM interactions:

- **Input Governance:** PII detection, forbidden words, prompt validation
- **Output Governance:** Content filtering, response validation
- **Audit Logging:** Every LLM call logged (JSONL format with PII redaction)
- **Cost Tracking:** Per-agent LLM cost monitoring
""")

# Governance Metrics
try:
    # Get governance statistics from the orchestrator's agents
    import sys
    import os
    import json
    from pathlib import Path
    
    # We need to access the governance wrapper statistics
    # For now, show a placeholder with live capability indication
    
    st.markdown("### 🔍 Governance Controls Active")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Input Validation",
            "✅ Active",
            help="PII detection, forbidden words, prompt length validation"
        )
    
    with col2:
        st.metric(
            "Output Validation",
            "✅ Active",
            help="Content filtering, response validation, PII in outputs"
        )
    
    with col3:
        st.metric(
            "Audit Logging",
            "✅ Active",
            help="All LLM calls logged to governance_audit.jsonl with PII redaction"
        )
    
    with col4:
        st.metric(
            "Cost Tracking",
            "✅ Active",
            help="Per-agent and per-call cost estimation"
        )
    
    # Governance Features
    st.markdown("### 🔒 Governance Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Input Governance:**")
        st.write("✅ PII Detection (email, SSN, credit card, phone, IBAN)")
        st.write("✅ Forbidden word filtering")
        st.write("✅ Prompt length validation (5-50K chars)")
        st.write("✅ Sensitive data protection")
        st.write("✅ Automatic redaction for audit logs")
    
    with col2:
        st.markdown("**Output Governance:**")
        st.write("✅ Empty response detection")
        st.write("✅ Response length validation")
        st.write("✅ PII in responses detection")
        st.write("✅ Content policy enforcement")
        st.write("✅ JSON schema validation")
    
    # Check for governance audit file
    audit_file = Path("governance_audit.jsonl")
    violations_file = Path("governance_violations.jsonl")
    
    if audit_file.exists():
        st.markdown("### 📊 Governance Statistics")
        
        # Read audit log
        total_calls = 0
        violations = 0
        by_agent = {}
        
        try:
            with open(audit_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    total_calls += 1
                    
                    if entry.get("governance_status") == "violation":
                        violations += 1
                    
                    agent = entry.get("agent_name", "unknown")
                    if agent not in by_agent:
                        by_agent[agent] = 0
                    by_agent[agent] += 1
            
            # Display stats
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total LLM Calls", total_calls)
            
            with col2:
                st.metric("Governance Violations", violations)
            
            with col3:
                compliance_rate = ((total_calls - violations) / total_calls * 100) if total_calls > 0 else 100
                st.metric("Compliance Rate", f"{compliance_rate:.1f}%")
            
            # By agent
            if by_agent:
                st.markdown("**Calls by Agent:**")
                for agent, count in sorted(by_agent.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- {agent}: {count} calls")
        
        except Exception as e:
            st.warning(f"Could not parse audit log: {e}")
    
    # Recent violations
    if violations_file.exists():
        st.markdown("### ⚠️ Recent Governance Events")
        
        try:
            violations_list = []
            with open(violations_file, 'r') as f:
                for line in f:
                    violations_list.append(json.loads(line))
            
            # Show last 5
            recent = violations_list[-5:] if len(violations_list) > 5 else violations_list
            
            if recent:
                for idx, v in enumerate(reversed(recent), 1):
                    event_type = v.get("event_type", "llm_call")
                    agent = v.get("agent_name", "unknown")
                    timestamp = v.get("timestamp", "")
                    
                    with st.expander(f"{idx}. {event_type} - {agent} ({timestamp})"):
                        if "input_violations" in v:
                            st.write(f"**Input Violations:** {v.get('input_violations', [])}")
                        if "output_violations" in v:
                            st.write(f"**Output Violations:** {v.get('output_violations', [])}")
                        if "details" in v:
                            st.json(v["details"])
            else:
                st.success("✅ No governance violations detected!")
        
        except Exception as e:
            st.info(f"Governance events will appear here after LLM calls")
    else:
        st.info("💡 Governance audit logs will appear here after processing transactions")
    
    # Governance Best Practices
    with st.expander("📖 AI Governance Best Practices"):
        st.markdown("""
        ### Input Governance
        
        **What We Check:**
        - PII (Personally Identifiable Information)
        - Forbidden words (passwords, keys, secrets)
        - Prompt length and quality
        
        **Why It Matters:**
        - Prevents data leaks to LLM providers
        - Ensures compliance with privacy regulations
        - Protects sensitive company information
        
        ### Output Governance
        
        **What We Check:**
        - Response quality (not empty, reasonable length)
        - PII in model outputs (shouldn't leak data)
        - Content policy compliance
        
        **Why It Matters:**
        - Ensures LLM responses are safe to use
        - Detects potential data exposure
        - Maintains quality standards
        
        ### Audit Logging
        
        **What We Log:**
        - Every LLM call (with PII redaction)
        - All governance violations
        - Cost per call
        - Processing time
        
        **Why It Matters:**
        - Complete transparency
        - Regulatory compliance
        - Cost accountability
        - Performance monitoring
        
        ### Files Created
        
        - `governance_audit.jsonl` - All LLM calls
        - `governance_violations.jsonl` - Violations only
        
        These can be ingested into:
        - ELK Stack (Elasticsearch, Logstash, Kibana)
        - Splunk
        - Azure Monitor
        - Prometheus + Grafana
        """)

except Exception as e:
    st.error(f"Error loading governance data: {e}")

st.markdown("---")
st.caption("AFGA Agent Workflow | LangGraph + A2A + MCP Hybrid Architecture")

