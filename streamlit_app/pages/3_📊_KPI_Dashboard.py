"""KPI Dashboard Page - Monitor system performance and learning metrics."""

import os

import httpx
import plotly.graph_objects as go
import streamlit as st

from components.chat_assistant import render_chat_sidebar

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

kpi_summary = None
kpi_summary_error = None
kpi_trend = None
kpi_trend_error = None

try:
    with httpx.Client(timeout=15.0) as client:
        try:
            summary_resp = client.get(f"{API_BASE_URL}/kpis/summary")
            if summary_resp.status_code == 200:
                kpi_summary = summary_resp.json()
            else:
                kpi_summary_error = f"HTTP {summary_resp.status_code}" \
                    + (f" - {summary_resp.text}" if summary_resp.text else "")
        except Exception as exc:
            kpi_summary_error = str(exc)

        try:
            trend_resp = client.get(f"{API_BASE_URL}/kpis/trend?days=30")
            if trend_resp.status_code == 200:
                kpi_trend = trend_resp.json()
            else:
                kpi_trend_error = f"HTTP {trend_resp.status_code}" \
                    + (f" - {trend_resp.text}" if trend_resp.text else "")
        except Exception as exc:
            kpi_trend_error = str(exc)
except Exception as exc:
    if not kpi_summary_error:
        kpi_summary_error = str(exc)
    if not kpi_trend_error:
        kpi_trend_error = str(exc)

assistant_context = {"page_summary": "KPI dashboard with H-CR, CRS, ATAR, and audit traceability metrics."}

if kpi_summary and kpi_summary.get("current"):
    assistant_context["current_metrics"] = kpi_summary["current"]
    assistant_context["learning_metrics"] = kpi_summary.get("learning_metrics", {})
    assistant_context["trend_flags"] = {
        key: value.get("improving")
        for key, value in (kpi_summary.get("trends") or {}).items()
    }

if kpi_trend and kpi_trend.get("kpis"):
    assistant_context["trend_sample"] = {
        "days": kpi_trend.get("days"),
        "point_count": len(kpi_trend.get("kpis", [])),
    }

st.set_page_config(page_title="KPI Dashboard", page_icon="📊", layout="wide")

# Hide default Streamlit navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 KPI Dashboard")
st.markdown("Monitor system performance, learning metrics, and operational efficiency.")

# Sidebar
sidebar_nav = st.sidebar.container()
sidebar_assistant = st.sidebar.container()

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

with sidebar_assistant:
    st.markdown("---")
    render_chat_sidebar("KPI Dashboard", context=assistant_context)

# Refresh button - force KPI recalculation
if st.button("🔄 Refresh Data"):
    try:
        # Force KPI recalculation
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/kpis/current")
            if response.status_code == 200:
                st.success("✅ KPIs recalculated!")
    except:
        pass
    st.rerun()

# Load KPI summary
if kpi_summary and kpi_summary.get("current"):
    summary = kpi_summary
    current = summary["current"]
    trends = summary.get("trends", {})
    learning = summary.get("learning_metrics", {})
    
    st.markdown("## 📈 Current Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        hcr = current.get("hcr", 0)
        hcr_improving = trends.get("hcr", {}).get("improving", False)
        st.metric(
            "H-CR",
            f"{hcr:.1f}%",
            delta=f"{'↓ Improving' if hcr_improving else '↑ Needs Work'}",
            delta_color="inverse",
            help="Human Correction Rate - Lower is better (indicates learning)"
        )
    
    with col2:
        crs = current.get("crs", 0)
        crs_improving = trends.get("crs", {}).get("improving", False)
        st.metric(
            "CRS",
            f"{crs:.1f}%",
            delta=f"{'↑ Improving' if crs_improving else '↓ Needs Work'}",
            delta_color="normal",
            help="Context Retention Score - Higher is better (memory effectiveness)"
        )
    
    with col3:
        atar = current.get("atar", 0)
        atar_improving = trends.get("atar", {}).get("improving", False)
        st.metric(
            "ATAR",
            f"{atar:.1f}%",
            delta=f"{'↑ Improving' if atar_improving else '↓ Needs Work'}",
            delta_color="normal",
            help="Automated Transaction Approval Rate - Higher is better (automation)"
        )
    
    with col4:
        traceability = current.get("audit_traceability_score", 0)
        st.metric(
            "Audit Trail",
            f"{traceability:.0f}%",
            delta="Target: 100%",
            help="Audit Traceability Score - Should be 100%"
        )
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Transactions",
            current.get("total_transactions", 0),
            help="Total number of transactions processed"
        )
    
    with col2:
        st.metric(
            "Human Corrections",
            current.get("human_corrections", 0),
            help="Number of times human overrode system decision"
        )
    
    with col3:
        st.metric(
            "Avg Processing Time",
            f"{current.get('avg_processing_time_ms', 0)}ms",
            help="Average time to process a transaction"
        )
    
    st.markdown("## 🧠 Learning Status")
    
    if learning.get("system_learning"):
        st.success("✅ **System is Learning!** H-CR is decreasing and CRS is increasing.")
    elif learning.get("hcr_reducing"):
        st.info("📊 **Partial Learning:** H-CR is improving but CRS needs work.")
    elif learning.get("crs_increasing"):
        st.info("📊 **Memory Improving:** CRS is increasing but H-CR hasn't decreased yet.")
    else:
        st.warning("⚠️ **More Data Needed:** Process more transactions to see learning trends.")
else:
    if kpi_summary_error:
        st.error(f"Error loading KPI summary: {kpi_summary_error}")
    else:
        st.info("No KPI data available yet. Process transactions to populate metrics.")

# Trend Charts
if kpi_trend and kpi_trend.get("kpis"):
    st.markdown("## 📉 Trend Analysis")
    kpis = kpi_trend.get("kpis", [])
    
    dates = [kpi.get("date") for kpi in kpis]
    hcr_values = [kpi.get("hcr", 0) for kpi in kpis]
    crs_values = [kpi.get("crs", 0) for kpi in kpis]
    atar_values = [kpi.get("atar", 0) for kpi in kpis]
    
    st.markdown("### H-CR Trend (Human Correction Rate)")
    fig_hcr = go.Figure()
    fig_hcr.add_trace(go.Scatter(
        x=dates,
        y=hcr_values,
        mode='lines+markers',
        name='H-CR',
        line=dict(color='#ff7f0e', width=2),
        marker=dict(size=6)
    ))
    fig_hcr.update_layout(
        xaxis_title="Date",
        yaxis_title="H-CR (%)",
        hovermode='x unified',
        height=300
    )
    st.plotly_chart(fig_hcr, use_container_width=True)
    st.caption("📉 Lower is better - Shows system learning from human corrections")
    
    st.markdown("### CRS Trend (Context Retention Score)")
    fig_crs = go.Figure()
    fig_crs.add_trace(go.Scatter(
        x=dates,
        y=crs_values,
        mode='lines+markers',
        name='CRS',
        line=dict(color='#2ca02c', width=2),
        marker=dict(size=6)
    ))
    fig_crs.update_layout(
        xaxis_title="Date",
        yaxis_title="CRS (%)",
        hovermode='x unified',
        height=300
    )
    st.plotly_chart(fig_crs, use_container_width=True)
    st.caption("📈 Higher is better - Indicates memory effectiveness")
    
    st.markdown("### ATAR Trend (Automated Transaction Approval Rate)")
    fig_atar = go.Figure()
    fig_atar.add_trace(go.Scatter(
        x=dates,
        y=atar_values,
        mode='lines+markers',
        name='ATAR',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6)
    ))
    fig_atar.update_layout(
        xaxis_title="Date",
        yaxis_title="ATAR (%)",
        hovermode='x unified',
        height=300
    )
    st.plotly_chart(fig_atar, use_container_width=True)
    st.caption("📈 Higher is better - Indicates automation coverage")
else:
    if kpi_trend_error:
        st.warning(f"Trend data unavailable: {kpi_trend_error}")
    else:
        st.info("Trend data will appear after enough historical transactions are processed.")

