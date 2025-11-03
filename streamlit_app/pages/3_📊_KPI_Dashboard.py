"""KPI Dashboard Page - Monitor system performance and learning metrics."""

import os

import httpx
import plotly.graph_objects as go
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="KPI Dashboard", page_icon="📊", layout="wide")

st.title("📊 KPI Dashboard")
st.markdown("Monitor system performance, learning metrics, and operational efficiency.")

# Refresh button
if st.button("🔄 Refresh Data"):
    st.rerun()

# Load KPI summary
try:
    with httpx.Client(timeout=15.0) as client:
        response = client.get(f"{API_BASE_URL}/kpis/summary")
        
        if response.status_code == 200:
            summary = response.json()
            
            if summary.get("current"):
                current = summary["current"]
                trends = summary.get("trends", {})
                learning = summary.get("learning_metrics", {})
                
                # Current KPIs
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
                
                # Additional metrics
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
                
                # Learning Status
                st.markdown("## 🧠 Learning Status")
                
                if learning.get("system_learning"):
                    st.success("✅ **System is Learning!** H-CR is decreasing and CRS is increasing.")
                elif learning.get("hcr_reducing"):
                    st.info("📊 **Partial Learning:** H-CR is improving but CRS needs work.")
                elif learning.get("crs_increasing"):
                    st.info("📊 **Memory Improving:** CRS is increasing but H-CR hasn't decreased yet.")
                else:
                    st.warning("⚠️ **More Data Needed:** Process more transactions to see learning trends.")
                
                # Trend Charts
                st.markdown("## 📉 Trend Analysis")
                
                # Get 30-day trend
                response_trend = client.get(f"{API_BASE_URL}/kpis/trend?days=30")
                
                if response_trend.status_code == 200:
                    trend_data = response_trend.json()
                    kpis = trend_data.get("kpis", [])
                    
                    if kpis:
                        # Prepare data
                        dates = [kpi.get("date") for kpi in kpis]
                        hcr_values = [kpi.get("hcr", 0) for kpi in kpis]
                        crs_values = [kpi.get("crs", 0) for kpi in kpis]
                        atar_values = [kpi.get("atar", 0) for kpi in kpis]
                        
                        # H-CR Trend
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
                        
                        # CRS Trend
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
                        st.caption("📈 Higher is better - Shows memory effectiveness in applying learned rules")
                        
                        # ATAR Trend
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
                        st.caption("📈 Higher is better - Shows percentage of transactions handled automatically")
                        
                        # Combined View
                        st.markdown("### Combined KPI View")
                        fig_combined = go.Figure()
                        fig_combined.add_trace(go.Scatter(
                            x=dates, y=hcr_values,
                            mode='lines', name='H-CR',
                            line=dict(color='#ff7f0e', width=2)
                        ))
                        fig_combined.add_trace(go.Scatter(
                            x=dates, y=crs_values,
                            mode='lines', name='CRS',
                            line=dict(color='#2ca02c', width=2)
                        ))
                        fig_combined.add_trace(go.Scatter(
                            x=dates, y=atar_values,
                            mode='lines', name='ATAR',
                            line=dict(color='#1f77b4', width=2)
                        ))
                        fig_combined.update_layout(
                            xaxis_title="Date",
                            yaxis_title="Percentage (%)",
                            hovermode='x unified',
                            height=400
                        )
                        st.plotly_chart(fig_combined, use_container_width=True)
                        
                        # 30-Day Averages
                        st.markdown("### 30-Day Averages")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            hcr_avg = trends.get("hcr", {}).get("30_day_avg", 0)
                            st.metric("Avg H-CR", f"{hcr_avg:.1f}%")
                        
                        with col2:
                            crs_avg = trends.get("crs", {}).get("30_day_avg", 0)
                            st.metric("Avg CRS", f"{crs_avg:.1f}%")
                        
                        with col3:
                            atar_avg = trends.get("atar", {}).get("30_day_avg", 0)
                            st.metric("Avg ATAR", f"{atar_avg:.1f}%")
                    
                    else:
                        st.info("Not enough data for trend analysis. Process more transactions!")
                
                # Transaction Statistics
                st.markdown("## 📊 Transaction Statistics")
                
                response_stats = client.get(f"{API_BASE_URL}/kpis/stats")
                
                if response_stats.status_code == 200:
                    stats = response_stats.json()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("### By Decision Type")
                        by_decision = stats.get("by_decision", {})
                        
                        if by_decision:
                            fig_decision = go.Figure(data=[
                                go.Pie(
                                    labels=list(by_decision.keys()),
                                    values=list(by_decision.values()),
                                    hole=0.3
                                )
                            ])
                            fig_decision.update_layout(height=300)
                            st.plotly_chart(fig_decision, use_container_width=True)
                        else:
                            st.info("No data yet")
                    
                    with col2:
                        st.markdown("### By Risk Level")
                        by_risk = stats.get("by_risk_level", {})
                        
                        if by_risk:
                            fig_risk = go.Figure(data=[
                                go.Pie(
                                    labels=list(by_risk.keys()),
                                    values=list(by_risk.values()),
                                    hole=0.3
                                )
                            ])
                            fig_risk.update_layout(height=300)
                            st.plotly_chart(fig_risk, use_container_width=True)
                        else:
                            st.info("No data yet")
                
                # KPI Definitions
                with st.expander("📖 KPI Definitions"):
                    st.markdown("""
                    ### H-CR (Human Correction Rate)
                    **Formula:** `(# of human corrections / # of total transactions) × 100`
                    
                    **Interpretation:**
                    - Lower is better
                    - Decreasing trend indicates system is learning
                    - Target: < 10% (90%+ automation)
                    
                    ### CRS (Context Retention Score)
                    **Formula:** `(# of successful memory applications / # of applicable scenarios) × 100`
                    
                    **Interpretation:**
                    - Higher is better
                    - Measures effectiveness of adaptive memory
                    - Target: > 80% (strong memory utilization)
                    
                    ### ATAR (Automated Transaction Approval Rate)
                    **Formula:** `(# of auto-approved transactions / # of total transactions) × 100`
                    
                    **Interpretation:**
                    - Higher is better
                    - Measures operational efficiency
                    - Target: > 70% (high automation)
                    
                    ### Audit Traceability Score
                    **Formula:** `(# of transactions with complete audit trail / # of total) × 100`
                    
                    **Interpretation:**
                    - Must be 100%
                    - Critical for compliance
                    - Every decision must be traceable
                    """)
            
            else:
                st.info("No KPI data available yet. Process some transactions to see metrics!")
        
        else:
            st.error(f"Error loading KPIs: {response.status_code}")

except Exception as e:
    st.error(f"Error: {str(e)}")
    st.info("Make sure the FastAPI backend is running at " + API_BASE_URL)

st.markdown("---")
st.caption("AFGA KPI Dashboard | Real-time Learning Metrics")

