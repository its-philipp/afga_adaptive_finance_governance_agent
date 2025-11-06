"""Main Streamlit application for AFGA."""

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="AFGA - Home",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Adaptive Finance Governance Agent - Multi-Agent AI System for Automated Finance Compliance"
    }
)

# Custom CSS
st.markdown("""
<style>
    /* Hide the default app name in sidebar */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        padding-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown('<div class="main-header">🤖 Adaptive Finance Governance Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Multi-Agent AI System for Automated Finance Compliance with Adaptive Learning</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🤖 AFGA")
    st.caption("Adaptive Finance Governance Agent")
    st.markdown("---")
    
    # Navigation
    st.markdown("### 📑 Navigation")
    st.page_link("app.py", label="Home", icon="🏠")
    st.page_link("pages/1_📋_Transaction_Review.py", label="Transaction Review", icon="📋")
    st.page_link("pages/2_🔄_Agent_Workflow.py", label="Agent Workflow", icon="🔄")
    st.page_link("pages/3_📊_KPI_Dashboard.py", label="KPI Dashboard", icon="📊")
    st.page_link("pages/4_🧠_Memory_Browser.py", label="Memory Browser", icon="🧠")
    st.page_link("pages/5_📖_Policy_Viewer.py", label="Policy Viewer", icon="📖")
    st.page_link("pages/6_🛡️_AI_Governance.py", label="AI Governance", icon="🛡️")
    
    st.markdown("---")
    st.info("""
    **AFGA Features:**
    - 🔍 Transaction Processing
    - 📊 Real-time KPI Dashboard
    - 🧠 Adaptive Memory Learning
    - 🔄 Agent Workflow Visualization
    - 📝 Complete Audit Trails
    """)
    
    st.markdown("---")
    st.markdown("**System Status**")
    
    # Check API health
    import httpx
    import os
    
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                st.success("✅ API Connected")
            else:
                st.error("❌ API Error")
    except:
        st.error("❌ API Offline")
        st.caption(f"URL: {API_BASE_URL}")

# Main content
st.markdown("## Welcome to AFGA")

st.markdown("""
The **Adaptive Finance Governance Agent (AFGA)** is a sophisticated multi-agent AI system designed to automate 
financial transaction compliance checking with continuous learning capabilities.

### 🎯 System Overview

AFGA consists of three specialized AI agents that work together:

1. **TAA (Transaction Auditor Agent)** - Orchestrator
   - Receives and assesses transactions
   - Performs risk scoring
   - Coordinates with other agents
   - Makes final approve/reject/HITL decisions

2. **PAA (Policy Adherence Agent)** - Compliance Checker
   - Retrieves relevant policies (RAG)
   - Checks adaptive memory for exceptions
   - Evaluates compliance using LLM
   - Returns confidence-scored results

3. **EMA (Exception Manager Agent)** - Learning System
   - Processes human feedback (HITL)
   - Analyzes correction patterns
   - Updates adaptive memory
   - Tracks learning metrics (H-CR)

### 📊 Key Performance Indicators

The system tracks four critical KPIs:

- **H-CR (Human Correction Rate):** Percentage of decisions requiring human override (should decrease over time)
- **CRS (Context Retention Score):** Effectiveness of adaptive memory in applying learned rules
- **ATAR (Automated Transaction Approval Rate):** Percentage of transactions approved automatically
- **Audit Traceability Score:** Completeness of audit trails (target: 100%)

### 🚀 Getting Started

Use the sidebar to navigate to different sections:

- **📋 Transaction Review:** Submit invoices and review decisions
- **🔄 Agent Workflow:** Visualize the agent processing pipeline  
- **📊 KPI Dashboard:** Monitor system performance and learning
- **🧠 Memory Browser:** Inspect learned exceptions and rules

### 🎓 How It Works

1. **Submit Transaction:** Upload or select a mock invoice
2. **Automated Processing:** TAA → PAA workflow checks compliance
3. **Decision:** System approves, rejects, or escalates to human review (HITL)
4. **Human Feedback:** If needed, human reviewer provides input
5. **Learning:** EMA processes feedback and updates memory
6. **Improvement:** System learns and reduces future H-CR

### 📈 Learning Demonstration

AFGA is designed to demonstrate **adaptive learning**. As you process transactions and provide feedback:

- The system learns from your decisions
- Similar situations are handled automatically
- H-CR decreases over time
- CRS increases (better memory utilization)
- ATAR improves (more automation)

---

**Start by navigating to 📋 Transaction Review in the sidebar to process your first transaction!**
""")

# Quick stats
st.markdown("### 📊 Quick Stats")

try:
    with httpx.Client(timeout=10.0) as client:
        # Get KPI summary
        response = client.get(f"{API_BASE_URL}/kpis/summary")
        if response.status_code == 200:
            summary = response.json()
            
            if summary.get("current"):
                col1, col2, col3, col4 = st.columns(4)
                
                current = summary["current"]
                
                with col1:
                    st.metric(
                        "Total Transactions",
                        current.get("total_transactions", 0)
                    )
                
                with col2:
                    hcr = current.get("hcr", 0)
                    st.metric(
                        "H-CR",
                        f"{hcr:.1f}%",
                        delta=f"{'↓' if summary.get('trends', {}).get('hcr', {}).get('improving') else '↑'} Learning"
                    )
                
                with col3:
                    crs = current.get("crs", 0)
                    st.metric(
                        "CRS",
                        f"{crs:.1f}%",
                        delta=f"{'↑' if summary.get('trends', {}).get('crs', {}).get('improving') else '↓'} Memory"
                    )
                
                with col4:
                    atar = current.get("atar", 0)
                    st.metric(
                        "ATAR",
                        f"{atar:.1f}%",
                        delta=f"{'↑' if summary.get('trends', {}).get('atar', {}).get('improving') else '↓'} Automation"
                    )
            else:
                st.info("No transactions processed yet. Start by reviewing a transaction!")
        
        # Get transaction stats
        response = client.get(f"{API_BASE_URL}/kpis/stats")
        if response.status_code == 200:
            stats = response.json()
            
            if stats.get("total_transactions", 0) > 0:
                st.markdown("### 📈 Transaction Distribution")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**By Decision:**")
                    by_decision = stats.get("by_decision", {})
                    for decision, count in by_decision.items():
                        st.write(f"- {decision.title()}: {count}")
                
                with col2:
                    st.markdown("**By Risk Level:**")
                    by_risk = stats.get("by_risk_level", {})
                    for risk, count in by_risk.items():
                        st.write(f"- {risk.title()}: {count}")

except Exception as e:
    st.warning(f"Could not load quick stats: {str(e)}")

st.markdown("---")
st.caption("AFGA v0.1.0 | Multi-Agent AI for Finance Compliance | Built with LangGraph + A2A + MCP")

