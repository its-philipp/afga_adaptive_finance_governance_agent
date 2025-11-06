"""AI Governance & Safety Page - Monitor governance controls for all agent calls."""

import json
import os
from pathlib import Path

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="AI Governance & Safety", page_icon="🛡️", layout="wide")

# Hide default Streamlit navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ AI Governance & Safety")
st.markdown("Monitor governance controls, audit logs, and safety features for all agent LLM calls.")

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

# Agent Selector
st.markdown("## 🔍 Select Agent to View Governance Data")

agent_options = {
    "All Agents": "all",
    "TAA (Transaction Auditor Agent)": "taa",
    "PAA (Policy Adherence Agent)": "paa",
    "EMA (Exception Manager Agent)": "ema",
}

selected_agent_label = st.selectbox(
    "Choose Agent:",
    options=list(agent_options.keys()),
    help="Select an agent to view its governance metrics and audit logs"
)

selected_agent = agent_options[selected_agent_label]

# Governance Overview
st.markdown("## 📊 Governance Controls Overview")

st.markdown("""
AFGA implements comprehensive **AI Governance controls** for all LLM interactions:

- **Input Governance:** PII detection, forbidden words, prompt validation
- **Output Governance:** Content filtering, response validation
- **Audit Logging:** Every LLM call logged (JSONL format with PII redaction)
- **Cost Tracking:** Per-agent LLM cost monitoring
""")

# Governance Metrics
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

# Agent-Specific Governance Details
st.markdown("---")
st.markdown(f"## 🤖 {selected_agent_label} Governance Details")

if selected_agent == "all":
    st.info("📊 Showing governance data for all agents. Select a specific agent to see detailed metrics.")
    
    # Show summary for all agents
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### TAA Governance")
        st.write("✅ Risk assessment LLM calls")
        st.write("✅ Decision reasoning validation")
        st.write("✅ Audit trail logging")
    
    with col2:
        st.markdown("### PAA Governance")
        st.write("✅ Policy compliance LLM calls")
        st.write("✅ Memory query validation")
        st.write("✅ Exception application tracking")
    
    with col3:
        st.markdown("### EMA Governance")
        st.write("✅ Correction analysis LLM calls")
        st.write("✅ Memory update validation")
        st.write("✅ Learning pattern tracking")
else:
    # Agent-specific details
    agent_details = {
        "taa": {
            "name": "Transaction Auditor Agent",
            "role": "Orchestrator (Client)",
            "llm_calls": [
                "Risk assessment",
                "Decision reasoning",
                "Audit trail generation"
            ],
            "governance_checks": [
                "Input: Invoice data validation",
                "Input: PII detection in transaction data",
                "Output: Risk score validation (0-100)",
                "Output: Decision type validation (approved/rejected/hitl)",
                "Audit: Complete trail logging"
            ]
        },
        "paa": {
            "name": "Policy Adherence Agent",
            "role": "Compliance Checker (Server)",
            "llm_calls": [
                "Policy retrieval (RAG)",
                "Compliance evaluation",
                "Exception application"
            ],
            "governance_checks": [
                "Input: Policy query validation",
                "Input: Memory exception query validation",
                "Output: Compliance result validation",
                "Output: Confidence score validation (0-1)",
                "Audit: Policy application logging"
            ]
        },
        "ema": {
            "name": "Exception Manager Agent",
            "role": "Learning System (Server)",
            "llm_calls": [
                "Correction type analysis",
                "Learning decision",
                "Memory update reasoning"
            ],
            "governance_checks": [
                "Input: HITL feedback validation",
                "Input: PII detection in feedback",
                "Output: Correction classification validation",
                "Output: Should-learn decision validation",
                "Audit: Memory update logging"
            ]
        }
    }
    
    details = agent_details[selected_agent]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Agent:** {details['name']}")
        st.markdown(f"**Role:** {details['role']}")
        st.markdown("**LLM Calls:**")
        for call in details['llm_calls']:
            st.write(f"  - {call}")
    
    with col2:
        st.markdown("**Governance Checks:**")
        for check in details['governance_checks']:
            st.write(f"  ✅ {check}")

# Governance Features
st.markdown("---")
st.markdown("## 🔒 Governance Features")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Input Governance")
    st.write("✅ PII Detection (email, SSN, credit card, phone, IBAN)")
    st.write("✅ Forbidden word filtering")
    st.write("✅ Prompt length validation (5-50K chars)")
    st.write("✅ Sensitive data protection")
    st.write("✅ Automatic redaction for audit logs")

with col2:
    st.markdown("### Output Governance")
    st.write("✅ Empty response detection")
    st.write("✅ Response length validation")
    st.write("✅ PII in responses detection")
    st.write("✅ Content policy enforcement")
    st.write("✅ JSON schema validation")

# Audit Logs
st.markdown("---")
st.markdown("## 📜 Audit Logs")

# Check for governance audit file
audit_file = Path("governance_audit.jsonl")
violations_file = Path("governance_violations.jsonl")

if audit_file.exists():
    # Read and filter by agent
    audit_entries = []
    with open(audit_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    # Filter by agent if not "all" - check both 'agent' and 'agent_name' fields
                    agent_name = (entry.get("agent") or entry.get("agent_name", "")).lower()
                    if selected_agent == "all" or agent_name == selected_agent:
                        audit_entries.append(entry)
                except json.JSONDecodeError:
                    continue
    
    if audit_entries:
        st.markdown(f"### 📋 Recent Audit Entries ({len(audit_entries)} total)")
        
        # Show last 20 entries in chronological order (most recent first)
        recent_entries = audit_entries[-20:] if len(audit_entries) > 20 else audit_entries
        
        for idx, entry in enumerate(reversed(recent_entries), 1):
            # Get agent name (try both fields)
            agent_display = entry.get("agent") or entry.get("agent_name", "Unknown")
            entry_number = len(audit_entries) - idx + 1  # Chronological numbering
            
            with st.expander(f"#{entry_number} - {agent_display.upper()} - {entry.get('timestamp', 'N/A')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Metadata:**")
                    st.write(f"- Agent: {agent_display}")
                    st.write(f"- Timestamp: {entry.get('timestamp', 'N/A')}")
                    # Clean up model name (remove openrouter/ prefix if present)
                    model_name = entry.get('model', 'N/A')
                    if model_name.startswith('openrouter/'):
                        model_name = model_name.replace('openrouter/', '')
                    st.write(f"- Model: {model_name}")
                    st.write(f"- Cost: ${entry.get('cost_estimate_usd', entry.get('estimated_cost', 0)):.6f}")
                    st.write(f"- Processing Time: {entry.get('processing_time_ms', 0)}ms")
                
                with col2:
                    st.markdown("**Governance:**")
                    st.write(f"- Input Valid: {'✅' if entry.get('input_valid', False) else '❌'}")
                    st.write(f"- Output Valid: {'✅' if entry.get('output_valid', False) else '❌'}")
                    if entry.get('violations'):
                        st.warning(f"⚠️ Violations: {len(entry.get('violations', []))}")
                    else:
                        st.success("✅ No violations")
                
                if entry.get('violations'):
                    st.markdown("**Violations:**")
                    for violation in entry.get('violations', []):
                        st.error(f"- {violation}")
                
                with st.expander("📄 Full Entry (JSON)"):
                    st.json(entry)
    else:
        st.info(f"💡 No audit entries found for {selected_agent_label}. Process transactions to generate audit logs.")
else:
    st.info("💡 Governance audit logs will appear here after processing transactions")

# Violations
if violations_file.exists():
    st.markdown("---")
    st.markdown("## ⚠️ Governance Violations")
    
    violations = []
    with open(violations_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    violation = json.loads(line)
                    # Filter by agent if not "all" - check both fields
                    agent_name = (violation.get("agent") or violation.get("agent_name", "")).lower()
                    if selected_agent == "all" or agent_name == selected_agent:
                        violations.append(violation)
                except json.JSONDecodeError:
                    continue
    
    if violations:
        st.warning(f"⚠️ **{len(violations)} violation(s) found**")
        
        for idx, violation in enumerate(reversed(violations[-10:]), 1):
            agent_display = violation.get("agent") or violation.get("agent_name", "Unknown")
            violation_number = len(violations) - idx + 1  # Chronological numbering
            
            with st.expander(f"#{violation_number} - {agent_display.upper()} - {violation.get('timestamp', 'N/A')}"):
                st.error(f"**Type:** {violation.get('violation_type', 'N/A')}")
                st.error(f"**Message:** {violation.get('message', 'N/A')}")
                st.json(violation)
    else:
        st.success("✅ No violations found!")

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

st.markdown("---")
st.caption("AFGA AI Governance & Safety | Comprehensive LLM Call Monitoring")

