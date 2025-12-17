"""Classifications Dashboard - View all invoice classifications and HITL cases."""

import streamlit as st
import httpx
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

# API Configuration
API_BASE = "http://localhost:8000/api/v1"


def get_classifications_summary() -> Optional[Dict]:
    """Fetch classifications summary from API."""
    try:
        response = httpx.get(f"{API_BASE}/transactions/classifications/summary", timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch classifications summary: {e}")
        return None


def get_all_transactions(limit: int = 100, decision_filter: Optional[str] = None) -> Optional[List[Dict]]:
    """Fetch all transactions from API."""
    try:
        params = {"limit": limit}
        if decision_filter:
            params["decision_filter"] = decision_filter
        
        response = httpx.get(f"{API_BASE}/transactions", params=params, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch transactions: {e}")
        return None


def render_decision_badge(decision: str) -> str:
    """Render colored badge for decision type."""
    decision = (decision or "").upper()
    colors = {
        "APPROVED": "🟢",
        "REJECTED": "🔴",
        "HITL": "🟡",
    }
    return f"{colors.get(decision, '⚪')} {decision}"


def render_risk_level_badge(risk_score: float) -> str:
    """Render colored badge for risk level."""
    if risk_score >= 70:
        return f"🔴 HIGH ({risk_score:.1f})"
    elif risk_score >= 40:
        return f"🟡 MEDIUM ({risk_score:.1f})"
    else:
        return f"🟢 LOW ({risk_score:.1f})"


def render_summary_cards(summary: Dict):
    """Render summary statistics cards."""
    st.markdown("### 📊 Classification Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Transactions",
            summary["total_transactions"],
        )
    
    with col2:
        # Handle lowercase keys from API
        ds = summary.get("decision_stats", {})
        approved_stats = ds.get("APPROVED") or ds.get("approved", {})
        approved_count = approved_stats.get("count", 0)
        approved_pct = approved_stats.get("percentage", 0)
        st.metric(
            "✅ Approved",
            approved_count,
            delta=f"{approved_pct:.1f}%",
            delta_color="normal",
        )
    
    with col3:
        rejected_stats = ds.get("REJECTED") or ds.get("rejected", {})
        rejected_count = rejected_stats.get("count", 0)
        rejected_pct = rejected_stats.get("percentage", 0)
        st.metric(
            "❌ Rejected",
            rejected_count,
            delta=f"{rejected_pct:.1f}%",
            delta_color="inverse",
        )
    
    with col4:
        hitl_stats = ds.get("HITL") or ds.get("hitl", {})
        hitl_count = hitl_stats.get("count", 0)
        hitl_pct = hitl_stats.get("percentage", 0)
        st.metric(
            "⚠️ Requires Review",
            hitl_count,
            delta=f"{hitl_pct:.1f}%",
            delta_color="off",
        )


def render_decision_chart(summary: Dict):
    """Render decision distribution chart."""
    decision_stats = summary.get("decision_stats", {})
    
    if not decision_stats:
        st.info("No transaction data available")
        return
    
    # Prepare data for chart
    chart_data = pd.DataFrame([
        {"Decision": str(decision).upper(), "Count": stats.get("count", 0)}
        for decision, stats in decision_stats.items()
    ])
    
    st.markdown("### 📈 Decision Distribution")
    st.bar_chart(chart_data.set_index("Decision"))


def render_performance_metrics(summary: Dict):
    """Render average performance metrics."""
    st.markdown("### ⚡ Performance Metrics")
    
    decision_stats = summary.get("decision_stats", {})
    
    cols = st.columns(len(decision_stats))
    
    for idx, (decision, stats) in enumerate(decision_stats.items()):
        with cols[idx]:
            st.markdown(f"**{render_decision_badge(str(decision))}**")
            st.metric(
                "Avg Risk Score",
                f"{stats.get('avg_risk_score', 0):.1f}",
            )
            st.metric(
                "Avg Processing Time",
                f"{stats.get('avg_processing_time_ms', 0):.0f}ms",
            )


def render_transactions_table(transactions: List[Dict], decision_filter: Optional[str] = None):
    """Render table of transactions."""
    if not transactions:
        st.info("No transactions found")
        return
    
    st.markdown(f"### 📋 Transactions ({len(transactions)})")
    
    # Prepare table data
    table_data = []
    for trans in transactions:
        invoice = trans.get("invoice", {})
        
        table_data.append({
            "Transaction ID": trans.get("transaction_id", "N/A")[:12] + "...",
            "Invoice ID": invoice.get("invoice_id", "N/A"),
            "Vendor": invoice.get("vendor", "N/A"),
            "Amount": f"${invoice.get('amount', 0):,.2f}",
            "Category": invoice.get("category", "N/A"),
            "Risk Score": trans.get("risk_score", 0),
            "Decision": str(trans.get("final_decision", "N/A")).upper(),
            "Human Override": "Yes" if trans.get("human_override") else "No",
            "Created": trans.get("created_at", "N/A")[:19] if trans.get("created_at") else "N/A",
        })
    
    df = pd.DataFrame(table_data)
    
    # Color code by decision
    def highlight_decision(row):
        decision = row["Decision"]
        style = ''
        if decision == "APPROVED":
            style = 'color: #1a7f37; font-weight: 600;'
        elif decision == "REJECTED":
            style = 'color: #d1242f; font-weight: 600;'
        elif decision == "HITL":
            style = 'color: #9a6700; font-weight: 600;'
        return [style] * len(row)
    
    styled_df = df.style.apply(highlight_decision, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=400)


def render_hitl_cases(transactions: List[Dict]):
    """Render detailed view of HITL cases requiring review."""
    hitl_cases = [
        t for t in transactions
        if str(t.get("final_decision", "")).lower() == "hitl" and not t.get("human_override")
    ]
    
    if not hitl_cases:
        st.success("✅ No pending HITL cases - all transactions reviewed!")
        return
    
    st.markdown(f"### 🚨 Cases Requiring Human Review ({len(hitl_cases)})")
    st.warning(f"**{len(hitl_cases)} transactions require human evaluation**")
    
    for idx, trans in enumerate(hitl_cases, 1):
        with st.expander(f"Case {idx}: {trans.get('invoice', {}).get('invoice_id', 'Unknown')}"):
            invoice = trans.get("invoice", {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Invoice Details:**")
                st.write(f"- **Vendor:** {invoice.get('vendor', 'N/A')}")
                st.write(f"- **Amount:** ${invoice.get('amount', 0):,.2f} {invoice.get('currency', 'USD')}")
                st.write(f"- **Category:** {invoice.get('category', 'N/A')}")
                st.write(f"- **Date:** {invoice.get('date', 'N/A')}")
                st.write(f"- **PO Number:** {invoice.get('po_number', 'N/A')}")
            
            with col2:
                st.markdown("**Classification Details:**")
                st.write(f"- **Risk Score:** {render_risk_level_badge(trans.get('risk_score', 0))}")
                st.write(f"- **Decision:** {render_decision_badge(trans.get('final_decision', 'N/A'))}")
                st.write(f"- **Transaction ID:** `{trans.get('transaction_id', 'N/A')[:20]}...`")
                st.write(f"- **Created:** {trans.get('created_at', 'N/A')[:19]}")
            
            # Show decision reasoning
            reasoning = trans.get("decision_reasoning", "No reasoning available")
            st.markdown("**Decision Reasoning:**")
            st.info(reasoning)
            
            # Show policy check if available
            policy_check = trans.get("policy_check", {})
            if policy_check and isinstance(policy_check, dict):
                compliant = policy_check.get("is_compliant") if "is_compliant" in policy_check else policy_check.get("compliant", False)
                violations = policy_check.get("violated_policies") if "violated_policies" in policy_check else policy_check.get("violations", [])
                
                if not compliant and violations:
                    st.markdown("**Policy Violations:**")
                    for violation in violations:
                        st.warning(f"⚠️ {violation}")
            
            # HITL feedback form (inline)
            st.markdown("**Provide HITL Feedback:**")
            with st.form(f"hitl_form_{trans.get('transaction_id')}"):
                human_decision = st.radio(
                    "Your Decision:",
                    ["approved", "rejected"],
                    format_func=lambda x: "✅ Approve" if x == "approved" else "❌ Reject",
                    horizontal=True,
                )
                reasoning = st.text_area(
                    "Reasoning (required):",
                    placeholder="Explain your decision and context...",
                    help="This reasoning helps the system learn from your decision",
                )
                should_create_exception = st.checkbox(
                    "Create Exception Rule",
                    value=False,
                    help="Check this if the system should learn this rule for similar future transactions",
                )
                exception_type = st.selectbox(
                    "Exception Type:",
                    ["recurring", "temporary", "policy_gap"],
                    format_func=lambda x: {
                        "recurring": "Recurring (applies to similar transactions)",
                        "temporary": "Temporary (one-time exception)",
                        "policy_gap": "Policy Gap (missing policy coverage)",
                    }[x],
                    disabled=not should_create_exception,
                )
                submit_hitl = st.form_submit_button("💾 Submit Feedback", type="primary")

                if submit_hitl:
                    if not reasoning:
                        st.error("Please provide reasoning for your decision")
                    else:
                        try:
                            payload = {
                                "transaction_id": trans.get("transaction_id"),
                                "invoice_id": invoice.get("invoice_id"),
                                "original_decision": trans.get("final_decision"),
                                "human_decision": human_decision,
                                "reasoning": reasoning,
                                "should_create_exception": should_create_exception,
                                "exception_type": exception_type,
                            }
                            resp = httpx.post(
                                f"{API_BASE}/transactions/{trans.get('transaction_id')}/hitl",
                                json=payload,
                                timeout=60.0,
                            )
                            if resp.status_code == 200:
                                st.success("✅ Feedback processed successfully!")
                                st.info("This case will disappear from pending after refresh.")
                                st.rerun()
                            else:
                                st.error(f"Error: {resp.status_code} - {resp.text}")
                        except Exception as e:
                            st.error(f"Error submitting feedback: {e}")


# ==================== PAGE CONTENT ====================

st.set_page_config(
    page_title="Classifications Dashboard",
    page_icon="📊",
    layout="wide",
)

# Hide default Streamlit navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
sidebar_nav = st.sidebar.container()

with sidebar_nav:
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
    st.page_link("pages/7_🔍_Embeddings_Browser.py", label="Embeddings Browser", icon="🔍")
    st.page_link("pages/8_📊_Classifications_Dashboard.py", label="Classifications", icon="📊")

st.title("📊 Invoice Classifications Dashboard")
st.markdown("View all classified invoices and identify cases requiring human review")

# Fetch data
with st.spinner("Loading classification data..."):
    summary = get_classifications_summary()
    transactions = get_all_transactions(limit=200)

if not summary or not transactions:
    st.error("Failed to load data. Make sure the API is running.")
    st.stop()

# Render summary cards
render_summary_cards(summary)

st.divider()

# Render charts and metrics
col1, col2 = st.columns(2)

with col1:
    render_decision_chart(summary)

with col2:
    render_performance_metrics(summary)

st.divider()

# HITL cases section
render_hitl_cases(transactions)

st.divider()

# Filter and view all transactions
st.markdown("### 🔍 All Transactions")

filter_col1, filter_col2 = st.columns([1, 3])

with filter_col1:
    decision_filter = st.selectbox(
        "Filter by Decision",
        ["All", "APPROVED", "REJECTED", "HITL"],
    )

with filter_col2:
    limit = st.slider("Number of transactions", 10, 500, 100, 10)

# Fetch filtered transactions
filtered_filter = None if decision_filter == "All" else decision_filter
filtered_transactions = get_all_transactions(limit=limit, decision_filter=filtered_filter)

if filtered_transactions:
    render_transactions_table(filtered_transactions, filtered_filter)

# Refresh button
st.divider()
if st.button("🔄 Refresh Data", use_container_width=True):
    st.rerun()
