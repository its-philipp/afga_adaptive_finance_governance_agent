"""Memory Browser Page - Inspect and manage adaptive memory."""

import os

import httpx
import streamlit as st

from components.chat_assistant import render_chat_sidebar

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="Memory Browser", page_icon="🧠", layout="wide")

# Hide default Streamlit navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Adaptive Memory Browser")
st.markdown("Explore learned exceptions, view memory statistics, and understand how the system improves over time.")

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

    render_chat_sidebar("Memory Browser")

# Refresh button - force memory stats recalculation
if st.button("🔄 Refresh"):
    try:
        # Force memory stats refresh
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/memory/stats")
            if response.status_code == 200:
                st.success("✅ Memory stats refreshed!")
    except:
        pass
    st.rerun()

# Memory Statistics
st.markdown("## 📊 Memory Statistics")

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{API_BASE_URL}/memory/stats")
        
        if response.status_code == 200:
            stats = response.json()
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Exceptions",
                    stats.get("total_exceptions", 0),
                    help="Total number of learned exceptions in memory"
                )
            
            with col2:
                st.metric(
                    "Active Exceptions",
                    stats.get("active_exceptions", 0),
                    help="Exceptions that have been applied at least once"
                )
            
            with col3:
                st.metric(
                    "Total Applications",
                    stats.get("total_applications", 0),
                    help="Total times memory rules have been applied"
                )
            
            with col4:
                avg_success = stats.get("avg_success_rate", 0)
                st.metric(
                    "Avg Success Rate",
                    f"{avg_success:.1%}",
                    help="Average success rate of applied memory rules"
                )
            
            # Most Applied Rules
            st.markdown("### 🏆 Most Applied Rules")
            
            most_applied = stats.get("most_applied_rules", [])
            
            if most_applied:
                for idx, rule in enumerate(most_applied, 1):
                    with st.expander(f"#{idx} - {rule.get('description', 'N/A')} (Applied {rule.get('applied_count', 0)} times)"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown(f"**Exception ID:** {rule.get('exception_id')}")
                            st.markdown(f"**Applied Count:** {rule.get('applied_count', 0)}")
                        
                        with col2:
                            st.markdown(f"**Success Rate:** {rule.get('success_rate', 0):.1%}")
                            
                            # Progress bar for success rate
                            success_rate = rule.get('success_rate', 0)
                            if success_rate >= 0.8:
                                st.success(f"High confidence: {success_rate:.1%}")
                            elif success_rate >= 0.6:
                                st.warning(f"Medium confidence: {success_rate:.1%}")
                            else:
                                st.error(f"Low confidence: {success_rate:.1%}")
            else:
                st.info("No rules have been applied yet. Process transactions with HITL feedback to create learned rules!")
            
            # Recent Additions
            st.markdown("### 🆕 Recently Added Rules")
            
            recent = stats.get("recent_additions", [])
            
            if recent:
                for rule in recent:
                    st.write(f"- **{rule.get('description', 'N/A')}** (ID: {rule.get('exception_id')}, Added: {rule.get('created_at', 'N/A')})")
            else:
                st.info("No recent additions")

except Exception as e:
    st.error(f"Error loading memory stats: {str(e)}")

# Browse Exceptions
st.markdown("## 🔍 Browse Exceptions")

# Filters
col1, col2, col3 = st.columns(3)

with col1:
    filter_vendor = st.text_input("Filter by Vendor:", placeholder="e.g., Acme Corporation")

with col2:
    filter_category = st.text_input("Filter by Category:", placeholder="e.g., Software")

with col3:
    filter_rule_type = st.selectbox(
        "Filter by Rule Type:",
        ["All", "exception", "learned_threshold", "custom_rule", "recurring", "temporary", "policy_gap"]
    )
    if filter_rule_type == "All":
        filter_rule_type = None

# Query exceptions
if st.button("🔎 Search Exceptions", type="primary"):
    try:
        with httpx.Client(timeout=10.0) as client:
            params = {}
            if filter_vendor:
                params["vendor"] = filter_vendor
            if filter_category:
                params["category"] = filter_category
            if filter_rule_type:
                params["rule_type"] = filter_rule_type
            
            response = client.get(f"{API_BASE_URL}/memory/exceptions", params=params)
            
            if response.status_code == 200:
                data = response.json()
                exceptions = data.get("exceptions", [])
                
                st.markdown(f"### Found {len(exceptions)} Exception(s)")
                
                if exceptions:
                    for exc in exceptions:
                        # Determine icon based on success rate
                        success_rate = exc.get("success_rate", 0)
                        if success_rate >= 0.8:
                            icon = "🟢"
                        elif success_rate >= 0.6:
                            icon = "🟡"
                        else:
                            icon = "🔴"
                        
                        with st.expander(f"{icon} {exc.get('description', 'N/A')}"):
                            col1, col2, col3 = st.columns([2, 2, 1])
                            
                            with col1:
                                st.markdown(f"**Exception ID:** `{exc.get('exception_id')}`")
                                st.markdown(f"**Vendor:** {exc.get('vendor') or 'Any'}")
                                st.markdown(f"**Category:** {exc.get('category') or 'Any'}")
                                st.markdown(f"**Rule Type:** {exc.get('rule_type')}")
                            
                            with col2:
                                st.markdown(f"**Applied Count:** {exc.get('applied_count', 0)}")
                                st.markdown(f"**Success Rate:** {exc.get('success_rate', 0):.1%}")
                                st.markdown(f"**Created:** {exc.get('created_at', 'N/A')}")
                                if exc.get('last_applied_at'):
                                    st.markdown(f"**Last Applied:** {exc['last_applied_at']}")
                            
                            with col3:
                                # Delete button
                                if st.button("🗑️ Delete", key=f"delete_{exc.get('exception_id')}", use_container_width=True):
                                    try:
                                        with httpx.Client(timeout=10.0) as client:
                                            delete_response = client.delete(
                                                f"{API_BASE_URL}/memory/exceptions/{exc.get('exception_id')}"
                                            )
                                            
                                            if delete_response.status_code == 200:
                                                st.success(f"✅ Exception {exc.get('exception_id')} deleted!")
                                                st.rerun()
                                            else:
                                                st.error(f"Error deleting: {delete_response.status_code}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")
                            
                            # Condition
                            st.markdown("**Condition:**")
                            condition = exc.get("condition", {})
                            if condition:
                                st.json(condition)
                            else:
                                st.write("No specific conditions")
                else:
                    st.info("No exceptions found matching your criteria.")
            
            else:
                st.error(f"Error: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error querying exceptions: {str(e)}")

# All Exceptions (without filter)
st.markdown("---")
st.markdown("## 📋 All Exceptions")

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{API_BASE_URL}/memory/exceptions")
        
        if response.status_code == 200:
            data = response.json()
            exceptions = data.get("exceptions", [])
            
            if exceptions:
                st.markdown(f"**Total: {len(exceptions)} exception(s)**")
                
                # Summary table with delete buttons
                for exc in exceptions:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"**{exc.get('description', 'N/A')}** | ID: `{exc.get('exception_id')}` | Applied: {exc.get('applied_count', 0)}x | Success: {exc.get('success_rate', 0):.1%}")
                    with col2:
                        if st.button("🗑️ Delete", key=f"delete_all_{exc.get('exception_id')}", use_container_width=True):
                            try:
                                with httpx.Client(timeout=10.0) as client:
                                    delete_response = client.delete(
                                        f"{API_BASE_URL}/memory/exceptions/{exc.get('exception_id')}"
                                    )
                                    
                                    if delete_response.status_code == 200:
                                        st.success(f"✅ Deleted!")
                                        st.rerun()
                                    else:
                                        st.error(f"Error: {delete_response.status_code}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    
                    st.markdown("---")
                
                # Export option
                import json
                
                if st.button("💾 Export All Exceptions (JSON)"):
                    json_str = json.dumps(exceptions, indent=2, default=str)
                    st.download_button(
                        label="Download JSON",
                        data=json_str,
                        file_name="adaptive_memory_exceptions.json",
                        mime="application/json"
                    )
            
            else:
                st.info("No exceptions in memory yet. Process transactions with HITL feedback to create learned rules!")

except Exception as e:
    st.error(f"Error loading all exceptions: {str(e)}")

# Understanding Adaptive Memory
with st.expander("📖 How Adaptive Memory Works"):
    st.markdown("""
    ### Adaptive Learning Process
    
    1. **Transaction Processing:**
       - TAA → PAA checks compliance
       - System makes initial decision
    
    2. **Human Override (HITL):**
       - Human reviewer disagrees with system
       - Provides reasoning and feedback
    
    3. **EMA Analysis:**
       - Analyzes correction type with LLM
       - Determines if system should learn
       - Classification:
         - **New Exception:** Vendor/category specific rule
         - **Policy Gap:** Missing policy coverage
         - **One-Time Override:** Special circumstances
    
    4. **Memory Update:**
       - IF should_learn == True:
         - Create exception rule
         - Store in adaptive_memory table
         - Include vendor, category, conditions
    
    5. **Future Application:**
       - PAA queries memory during compliance check
       - Applies learned exceptions automatically
       - Updates success_rate and applied_count
    
    6. **Continuous Improvement:**
       - Low success rate exceptions can be deprecated
       - High success rate exceptions become trusted
       - H-CR decreases over time
       - CRS increases (better memory utilization)
    
    ### Exception Types
    
    - **Recurring:** Applied to all similar transactions (e.g., same vendor/category)
    - **Temporary:** One-time exception for special case
    - **Policy Gap:** Identifies missing policies that should be added
    
    ### Success Rate Calculation
    
    `success_rate = (successful_applications / total_applications)`
    
    - Starts at 1.0 (100%)
    - Updated each time the rule is applied
    - Moving average over all applications
    
    ### Memory Query Logic
    
    When PAA checks compliance:
    1. Query by vendor (if specific vendor rule exists)
    2. Query by category (if category rule exists)
    3. Check condition matching (amount thresholds, international, etc.)
    4. Apply all matching exceptions
    5. Report applied exceptions in result
    """)

# Deleted Exceptions
st.markdown("---")
st.markdown("## 🗑️ Deleted Exceptions")

try:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{API_BASE_URL}/memory/exceptions/deleted")
        
        if response.status_code == 200:
            data = response.json()
            deleted_exceptions = data.get("exceptions", [])
            
            if deleted_exceptions:
                st.warning(f"**{len(deleted_exceptions)} deleted exception(s)**")
                
                for exc in deleted_exceptions:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"~~{exc.get('description', 'N/A')}~~ | ID: `{exc.get('exception_id')}` | Was applied: {exc.get('applied_count', 0)}x")
                    with col2:
                        if st.button("♻️ Restore", key=f"restore_{exc.get('exception_id')}", use_container_width=True):
                            try:
                                restore_response = client.post(
                                    f"{API_BASE_URL}/memory/exceptions/{exc.get('exception_id')}/restore"
                                )
                                
                                if restore_response.status_code == 200:
                                    st.success(f"✅ Restored!")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {restore_response.status_code}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    st.markdown("---")
            else:
                st.info("No deleted exceptions. Deleted exceptions can be restored here.")
        else:
            st.error(f"Error loading deleted exceptions: {response.status_code}")
except Exception as e:
    st.error(f"Error: {str(e)}")

# Memory Management (Admin)
st.markdown("---")
st.markdown("## ⚙️ Memory Management")

with st.expander("🔧 Admin Tools"):
    st.warning("⚠️ **Admin Only:** These operations affect the adaptive memory system.")
    
    st.markdown("### Clear Low-Performance Rules")
    
    threshold = st.slider(
        "Success Rate Threshold:",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Remove rules with success rate below this threshold"
    )
    
    if st.button("🗑️ Clear Low-Performance Rules", type="secondary"):
        st.warning(f"This would remove all rules with success rate < {threshold:.1%}")
        st.info("Not implemented in MVP - manual database operation required")
    
    st.markdown("### Export Memory Database")
    
    if st.button("💾 Export Memory DB"):
        st.info("Download the entire adaptive_memory table as SQL dump")
        st.info("Not implemented in MVP - use SQLite tools directly")

st.markdown("---")
st.caption("AFGA Adaptive Memory | Continuous Learning System")

