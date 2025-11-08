"""Policy Viewer Page - Browse company policies used for compliance checking."""

import os
from pathlib import Path

import streamlit as st

from components.chat_assistant import render_chat_sidebar

st.set_page_config(page_title="Policy Viewer", page_icon="📖", layout="wide")

# Hide default Streamlit navigation
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.title("📖 Policy Viewer")
st.markdown("Browse the company policies used by PAA for compliance checking.")

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

    render_chat_sidebar("Policy Viewer")

# Find policies directory
policies_dir = Path("data/policies")

if not policies_dir.exists():
    st.error(f"Policies directory not found: {policies_dir}")
    st.info("Run `python scripts/generate_mock_data.py` to generate mock policies.")
else:
    # Get all policy files
    policy_files = sorted(policies_dir.glob("*.txt"))
    
    if not policy_files:
        st.warning("No policy files found in the policies directory.")
    else:
        st.markdown(f"**Found {len(policy_files)} policy documents**")
        st.markdown("---")
        
        # Display policies
        for policy_file in policy_files:
            # Extract policy name from filename
            policy_name = policy_file.stem.replace("_", " ").title()
            
            with st.expander(f"📋 {policy_name}", expanded=False):
                try:
                    with open(policy_file, 'r') as f:
                        policy_content = f.read()
                    
                    # Display metadata
                    col1, col2 = st.columns([1, 4])
                    
                    with col1:
                        st.metric("File", policy_file.name)
                        st.metric("Size", f"{len(policy_content)} chars")
                        st.metric("Lines", len(policy_content.split('\n')))
                    
                    with col2:
                        st.markdown("**Policy Content:**")
                        st.text_area(
                            label="Content",
                            value=policy_content,
                            height=300,
                            key=f"policy_{policy_file.name}",
                            label_visibility="collapsed"
                        )
                
                except Exception as e:
                    st.error(f"Error reading policy: {e}")

# Information about how policies are used
st.markdown("---")
st.markdown("## 📚 How Policies Are Used")

st.markdown("""
### Policy Adherence Agent (PAA)

The PAA uses these policy documents through the **Policy MCP Server**:

1. **Policy Retrieval (RAG):**
   - When a transaction is submitted, PAA queries relevant policies
   - Uses keyword-based retrieval to find the top 5 most relevant policies
   - Policies are matched based on vendor, category, amount, and other invoice attributes

2. **Compliance Evaluation:**
   - PAA sends retrieved policies to the LLM along with the invoice
   - LLM evaluates whether the transaction complies with each policy
   - Returns: is_compliant, violated_policies, confidence score

3. **MCP Integration:**
   - Policies are exposed as **MCP Resources**: `policy://policy_name`
   - PAA accesses policies via `PolicyMCPServer.search_relevant_policies()`
   - Clean abstraction: PAA doesn't read files directly

### Policy Types in AFGA MVP

The mock policies cover common financial compliance scenarios:

- **Expense Limits:** Maximum amounts for different categories
- **Vendor Approval:** Pre-approved vs. new vendors
- **PO Matching:** When purchase orders are required
- **International Transactions:** Additional requirements for foreign vendors
- **Reimbursement Guidelines:** Rules for employee expense reports

### Adding New Policies

To add a new policy:

1. Create a `.txt` file in `data/policies/`
2. Write clear, structured policy text
3. PAA will automatically include it in RAG retrieval
4. No code changes needed - policies are loaded dynamically

### Policy Format Best Practices

**Good Policy Format:**
```
Policy: Vendor Approval Requirements

All vendors must be pre-approved before processing payments.

Requirements:
- New vendors: Require manager approval + credit check
- Existing vendors: Automatic approval if in good standing
- International vendors: Additional compliance checks required
```

**What Makes a Good Policy:**
- Clear title and purpose
- Specific requirements or rules
- Conditions and exceptions
- Action items or procedures
""")

st.markdown("---")

# Search functionality
st.markdown("## 🔍 Search Policies")

search_term = st.text_input("Search across all policies:", placeholder="e.g., vendor approval, expense limit, PO number")

if search_term:
    st.markdown(f"**Searching for: '{search_term}'**")
    
    results = []
    for policy_file in policy_files:
        try:
            with open(policy_file, 'r') as f:
                content = f.read()
            
            # Simple case-insensitive search
            if search_term.lower() in content.lower():
                # Find context around the search term
                lines = content.split('\n')
                matching_lines = []
                for line_num, line in enumerate(lines, 1):
                    if search_term.lower() in line.lower():
                        matching_lines.append((line_num, line))
                
                if matching_lines:
                    results.append({
                        "policy": policy_file.stem.replace("_", " ").title(),
                        "file": policy_file.name,
                        "matches": matching_lines
                    })
        except Exception as e:
            st.error(f"Error searching {policy_file.name}: {e}")
    
    if results:
        st.success(f"Found {len(results)} policy document(s) with matches")
        
        for result in results:
            with st.expander(f"📄 {result['policy']} ({len(result['matches'])} matches)"):
                st.markdown(f"**File:** `{result['file']}`")
                st.markdown("**Matching lines:**")
                
                for line_num, line in result['matches'][:10]:  # Show first 10 matches
                    st.markdown(f"Line {line_num}: `{line.strip()}`")
                
                if len(result['matches']) > 10:
                    st.info(f"+ {len(result['matches']) - 10} more matches")
    else:
        st.info("No matches found. Try a different search term.")

st.markdown("---")
st.caption("AFGA Policy Viewer | Policies are accessed via MCP by PAA")

