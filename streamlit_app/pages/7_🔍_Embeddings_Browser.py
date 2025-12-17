"""Databricks Embeddings Browser - View and search historical invoice embeddings."""

import os
import streamlit as st
import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="Databricks Embeddings", page_icon="🔍", layout="wide")

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

st.title("🔍 Databricks Embeddings Browser")
st.markdown("""
This page provides visibility into the invoice embeddings stored in Databricks for historical pattern analysis and audit purposes.

**Features:**
- View embeddings statistics from the gold table
- Semantic similarity search across historical invoices
- Audit trail for centralized governance data
""")

# ==================== EMBEDDINGS STATS ====================

st.header("📊 Embeddings Statistics")

try:
    with st.spinner("Fetching embeddings stats..."):
        response = httpx.get(
            f"{API_BASE_URL}/databricks/embeddings/stats",
            params={"limit": 10},
            timeout=30.0,
        )
        
    if response.status_code == 200:
        stats = response.json()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Embeddings", stats.get("total_count", 0))
        with col2:
            st.metric("Gold Table", stats.get("gold_table", "N/A"))
        with col3:
            st.metric("Embedding Model", stats.get("model", "N/A"))
        
        # Sample data
        if stats.get("sample_data"):
            st.subheader("Sample Invoices")
            for idx, sample in enumerate(stats["sample_data"][:5], 1):
                with st.expander(f"📄 {sample.get('invoice_id', f'Sample {idx}')}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"**Invoice ID:** {sample.get('invoice_id', 'N/A')}")
                        st.write(f"**Created:** {sample.get('created_at', 'N/A')}")
                    with col_b:
                        embedding = sample.get("embedding")
                        if embedding:
                            st.write(f"**Embedding Dimension:** {len(embedding)}")
                            st.write(f"**Sample Vector:** `[{embedding[0]:.4f}, {embedding[1]:.4f}, ...]`")
                        else:
                            st.write("**Embedding:** N/A")
    elif response.status_code == 424:
        st.warning("⚠️ Databricks unavailable. Check your connection and credentials.")
        st.info("Make sure `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, and `DATABRICKS_TOKEN` are set in your `.env` file.")
    else:
        st.error(f"Failed to fetch stats: HTTP {response.status_code}")
        st.code(response.text)

except httpx.TimeoutException:
    st.error("Request timed out. Databricks may be slow or unavailable.")
except Exception as e:
    st.error(f"Error fetching embeddings stats: {e}")

st.divider()

# ==================== BACKFILL CONTROL ====================

st.header("🧩 Databricks Backfill")
st.markdown("""
Trigger a server-side backfill of previously processed transactions to ensure all historical invoices and agent trails are present in Azure Blob for Databricks ingestion.

Use **Dry Run** first to see how many would be uploaded. Duplicate detection uses invoice content hashing; you can override with **Force Upload**.
""")

col_bf1, col_bf2, col_bf3, col_bf4, col_bf5 = st.columns([1,1,1,1,2])
with col_bf1:
    bf_limit = st.number_input("Limit", min_value=10, max_value=5000, value=500, step=50,
                               help="Maximum number of transactions to consider (ordered by creation time)")
with col_bf2:
    bf_skip_dup = st.checkbox("Skip Duplicates", value=True, help="Skip invoices whose hash already exists")
with col_bf3:
    bf_force = st.checkbox("Force Upload", value=False, help="Upload even if duplicate detected")
with col_bf4:
    bf_dry_run = st.checkbox("Dry Run", value=True, help="Do not upload; only show what would happen")
with col_bf5:
    if st.button("🚀 Run Backfill", use_container_width=True):
        params = {
            "limit": bf_limit,
            "force": str(bf_force).lower(),
            "dry_run": str(bf_dry_run).lower(),
            "skip_duplicates": str(bf_skip_dup).lower(),
        }
        try:
            with st.spinner("Executing backfill operation..."):
                resp = httpx.post(f"{API_BASE_URL}/databricks/backfill", params=params, timeout=120.0)
            if resp.status_code == 200:
                data = resp.json()
                if bf_dry_run:
                    st.info("Dry run complete – no data uploaded.")
                st.success("Backfill operation finished")
                metrics_cols = st.columns(4)
                with metrics_cols[0]:
                    st.metric("Invoices Uploaded", data.get("uploaded_invoices", 0))
                with metrics_cols[1]:
                    st.metric("Duplicates Skipped", data.get("duplicate_skipped", 0))
                with metrics_cols[2]:
                    st.metric("Agent Trails Uploaded", data.get("agent_trails_uploaded", 0))
                with metrics_cols[3]:
                    st.metric("Total Considered", data.get("total_rows_considered", 0))
                with st.expander("Raw Backfill Response"):
                    st.json(data)
            elif resp.status_code == 503:
                st.warning("Databricks sink disabled. Set AZURE_STORAGE_CONNECTION_STRING.")
            else:
                st.error(f"Backfill failed: HTTP {resp.status_code}")
                st.code(resp.text)
        except httpx.TimeoutException:
            st.error("Backfill request timed out. Try reducing the limit.")
        except Exception as e:
            st.error(f"Backfill error: {e}")

st.divider()

# ==================== SIMILARITY SEARCH ====================

st.header("🔎 Semantic Similarity Search")

st.markdown("""
Search for invoices similar to your query using semantic embeddings. This helps identify historical patterns and precedents.
""")

col_search, col_params = st.columns([3, 1])

with col_search:
    query = st.text_input(
        "Search Query",
        placeholder="e.g., consulting services for Q4 advisory",
        help="Natural language description of the invoice you're looking for",
    )

with col_params:
    k = st.number_input("Top K Results", min_value=1, max_value=20, value=5, help="Number of similar invoices to return")
    sample_limit = st.number_input(
        "Sample Limit",
        min_value=10,
        max_value=1000,
        value=500,
        step=50,
        help="Max embeddings to search (higher = slower but more comprehensive)",
    )

if st.button("🔍 Search", type="primary", use_container_width=True):
    if not query:
        st.warning("Please enter a search query.")
    else:
        try:
            with st.spinner("Searching similar invoices..."):
                search_response = httpx.post(
                    f"{API_BASE_URL}/databricks/embeddings/search",
                    json={"query": query, "k": k, "sample_limit": sample_limit},
                    timeout=60.0,
                )
            
            if search_response.status_code == 200:
                results = search_response.json()
                
                st.success(f"✅ Found {len(results.get('results', []))} similar invoices (searched {results.get('total_searched', 0)} embeddings)")
                
                if results.get("results"):
                    st.subheader("Similar Invoices")
                    
                    for idx, result in enumerate(results["results"], 1):
                        invoice_id = result.get("invoice_id", "Unknown")
                        similarity = result.get("similarity", 0)
                        
                        # Color code by similarity
                        if similarity >= 0.8:
                            color = "🟢"
                            badge = "Very Similar"
                        elif similarity >= 0.6:
                            color = "🟡"
                            badge = "Similar"
                        else:
                            color = "🔵"
                            badge = "Somewhat Similar"
                        
                        with st.expander(f"{color} #{idx} - {invoice_id} ({similarity:.1%} match) - {badge}"):
                            st.write(f"**Invoice ID:** {invoice_id}")
                            st.write(f"**Cosine Similarity:** {similarity:.4f}")
                            st.progress(similarity)
                            
                            # Note: Additional invoice details would require joining with silver/bronze tables
                            st.caption("💡 Tip: This invoice has similar semantic characteristics to your query.")
                else:
                    st.info("No similar invoices found. Try a different query or increase the sample limit.")
                    
            elif search_response.status_code == 424:
                st.warning("⚠️ Databricks unavailable. Check your connection and credentials.")
            elif search_response.status_code == 400:
                st.error(f"Invalid request: {search_response.json().get('detail', 'Unknown error')}")
            else:
                st.error(f"Search failed: HTTP {search_response.status_code}")
                st.code(search_response.text)

        except httpx.TimeoutException:
            st.error("⏱️ Search timed out. Try reducing the sample limit or check Databricks performance.")
        except Exception as e:
            st.error(f"Search error: {e}")

st.divider()

# ==================== AUDIT DATA UPLOADS ====================

st.header("📤 Audit Data Management")

st.markdown("""
Upload compliance data to Databricks for centralized governance and historical tracking.
""")

col_up1, col_up2, col_up3 = st.columns(3)

with col_up1:
    if st.button("📝 Upload Memory Snapshot", use_container_width=True):
        with st.spinner("Uploading adaptive memory..."):
            try:
                upload_response = httpx.post(
                    f"{API_BASE_URL}/audit/upload-memory-snapshot",
                    timeout=30.0,
                )
                if upload_response.status_code == 200:
                    data = upload_response.json()
                    st.success(f"✅ Uploaded {data.get('total_exceptions', 0)} memory exceptions")
                    st.caption(f"Blob URL: `{data.get('blob_url', 'N/A')}`")
                elif upload_response.status_code == 503:
                    st.warning("⚠️ Databricks sink not configured. Set `AZURE_STORAGE_CONNECTION_STRING` in your environment.")
                else:
                    st.error(f"Upload failed: {upload_response.status_code}")
            except Exception as e:
                st.error(f"Upload error: {e}")

with col_up2:
    if st.button("📋 Upload Policy Documents", use_container_width=True):
        with st.spinner("Uploading policy documents..."):
            try:
                upload_response = httpx.post(
                    f"{API_BASE_URL}/audit/upload-policies",
                    timeout=60.0,
                )
                if upload_response.status_code == 200:
                    data = upload_response.json()
                    st.success(f"✅ Uploaded {len(data.get('uploaded', []))} policies")
                    if data.get("failed"):
                        st.warning(f"Failed: {', '.join(data['failed'])}")
                elif upload_response.status_code == 503:
                    st.warning("⚠️ Databricks sink not configured.")
                else:
                    st.error(f"Upload failed: {upload_response.status_code}")
            except Exception as e:
                st.error(f"Upload error: {e}")

with col_up3:
    if st.button("📊 Upload KPI Snapshot", use_container_width=True):
        with st.spinner("Uploading KPIs..."):
            try:
                upload_response = httpx.post(
                    f"{API_BASE_URL}/audit/upload-kpis",
                    timeout=30.0,
                )
                if upload_response.status_code == 200:
                    data = upload_response.json()
                    st.success("✅ KPI snapshot uploaded successfully")
                    st.caption(f"Blob URL: `{data.get('blob_url', 'N/A')}`")
                elif upload_response.status_code == 503:
                    st.warning("⚠️ Databricks sink not configured.")
                else:
                    st.error(f"Upload failed: {upload_response.status_code}")
            except Exception as e:
                st.error(f"Upload error: {e}")

st.divider()

# ==================== CONFIGURATION HELP ====================

with st.expander("⚙️ Configuration & Setup"):
    st.markdown("""
    ### Required Environment Variables
    
    **For reading embeddings:**
    - `DATABRICKS_SERVER_HOSTNAME` - Your Databricks workspace URL
    - `DATABRICKS_HTTP_PATH` - SQL warehouse HTTP path
    - `DATABRICKS_TOKEN` - Personal access token
    - `DATABRICKS_GOLD_TABLE` - Gold table name (default: `afga_dev.gold.finance_transaction_embeddings`)
    - `OPENAI_API_KEY` - For embedding query text during similarity search
    
    **For uploading audit data:**
    - `AZURE_STORAGE_CONNECTION_STRING` - Azure Blob Storage connection string
    - `AZURE_CONTAINER_INVOICES` - Container for invoices (default: `raw-transactions`)
    - `AZURE_CONTAINER_AUDIT` - Container for audit trails (default: `audit-trails`)
    
    ### Databricks Pipeline
    
    The scheduled Databricks job (every 6 hours) processes:
    1. **Bronze Layer:** Ingest raw invoices from ADLS Gen2
    2. **Silver Layer:** Validate and enrich with risk scores
    3. **Gold Layer:** Generate embeddings using OpenAI
    
    ### Usage Tips
    
    - **Similarity Search:** Use natural language queries that describe the invoice characteristics
    - **Sample Limit:** Higher values are more comprehensive but slower (500 is a good balance)
    - **Audit Uploads:** Run periodically to maintain centralized compliance records
    - **Historical Analysis:** Use similarity search to find precedents for edge-case decisions
    """)
