"""Transaction Review Page - Submit and review invoice transactions."""

import json
import os
from pathlib import Path

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="Transaction Review", page_icon="📋", layout="wide")

st.title("📋 Transaction Review")
st.markdown("Submit invoices for automated compliance checking and provide human feedback when needed.")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["📤 Submit Transaction", "📜 Transaction History", "👤 Human Review (HITL)"])

# ==================== TAB 1: SUBMIT TRANSACTION ====================
with tab1:
    st.markdown("### Submit Invoice for Processing")
    
    # Option to use mock data, upload file, or custom JSON
    data_source = st.radio(
        "Data Source:",
        ["Mock Invoices (Test Data)", "Upload Receipt/Invoice (PDF/Image)", "Custom Invoice (JSON)"],
        horizontal=True
    )
    
    invoice_data = None
    
    if data_source == "Upload Receipt/Invoice (PDF/Image)":
        st.markdown("### 📄 Upload Receipt or Invoice Document")
        st.info("Upload a PDF or image of an expense report. The system will extract invoice data using AI.")
        
        uploaded_file = st.file_uploader(
            "Choose a file:",
            type=['pdf', 'png', 'jpg', 'jpeg', 'webp'],
            help="Supported formats: PDF, PNG, JPG, JPEG, WEBP"
        )
        
        if uploaded_file:
            st.success(f"✅ File uploaded: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
            
            # Show file preview (if image)
            if uploaded_file.type.startswith('image/'):
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
            else:
                st.info(f"📄 PDF document: {uploaded_file.name}")
            
            # Process button
            if st.button("🔍 Extract & Process Invoice", type="primary"):
                with st.spinner("Extracting invoice data with Vision LLM..."):
                    try:
                        # Upload to API for extraction
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        
                        with httpx.Client(timeout=120.0) as client:
                            response = client.post(
                                f"{API_BASE_URL}/transactions/upload-receipt",
                                files=files
                            )
                            
                            if response.status_code == 201:
                                result = response.json()
                                
                                st.success("✅ Invoice extracted and processed!")
                                
                                # Show extracted invoice data
                                st.markdown("#### 📋 Extracted Invoice Data")
                                extracted_invoice = result.get("invoice", {})
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Invoice ID", extracted_invoice.get("invoice_id"))
                                    st.metric("Vendor", extracted_invoice.get("vendor"))
                                
                                with col2:
                                    st.metric("Amount", f"${extracted_invoice.get('amount', 0):,.2f}")
                                    st.metric("Category", extracted_invoice.get("category"))
                                
                                with col3:
                                    st.metric("PO Number", extracted_invoice.get("po_number") or "N/A")
                                    st.metric("Date", extracted_invoice.get("date"))
                                
                                with st.expander("📋 Full Extracted Data"):
                                    st.json(extracted_invoice)
                                
                                # Show processing result (same as structured submission)
                                st.markdown("---")
                                st.markdown("#### 🎯 Processing Result")
                                
                                # Store in session for HITL
                                st.session_state.last_transaction = result
                                
                                # Decision badge
                                decision = result.get("final_decision")
                                if decision == "approved":
                                    st.success(f"✅ **APPROVED**")
                                elif decision == "rejected":
                                    st.error(f"❌ **REJECTED**")
                                else:
                                    st.warning(f"⚠️ **HITL REQUIRED**")
                                
                                # Risk and policy check (same as before)
                                risk = result.get("risk_assessment", {})
                                if risk:
                                    st.metric("Risk Level", risk.get("risk_level", "N/A").upper())
                                    st.metric("Risk Score", f"{risk.get('risk_score', 0):.1f}/100")
                                
                                # Audit trail
                                with st.expander("📜 Complete Audit Trail"):
                                    audit_trail = result.get("audit_trail", [])
                                    for idx, step in enumerate(audit_trail, 1):
                                        st.write(f"{idx}. {step}")
                            
                            elif response.status_code == 422:
                                st.error(f"❌ Could not extract valid invoice data from document")
                                st.error(f"Details: {response.json().get('detail', 'Unknown error')}")
                            else:
                                st.error(f"❌ Error: {response.status_code} - {response.text}")
                    
                    except Exception as e:
                        st.error(f"❌ Error processing document: {str(e)}")
                        st.info("Make sure the backend is running and has Vision LLM access")
    
    elif data_source == "Mock Invoices (Test Data)":
        st.markdown("### 🧪 Mock Invoice Testing")
        # List mock invoices
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{API_BASE_URL}/demo/list-mock-invoices")
                if response.status_code == 200:
                    data = response.json()
                    invoices = data.get("invoices", [])
                    
                    if invoices:
                        selected_invoice = st.selectbox(
                            "Select Mock Invoice:",
                            invoices,
                            help="Choose from pre-generated test invoices"
                        )
                        
                        # Load and display invoice
                        invoice_path = Path("data/mock_invoices") / selected_invoice
                        if invoice_path.exists():
                            with open(invoice_path, 'r') as f:
                                invoice_data = json.load(f)
                            
                            # Display invoice preview
                            st.markdown("#### Invoice Preview")
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Invoice ID", invoice_data.get("invoice_id"))
                                st.metric("Vendor", invoice_data.get("vendor"))
                            
                            with col2:
                                st.metric("Amount", f"${invoice_data.get('amount', 0):,.2f}")
                                st.metric("Category", invoice_data.get("category"))
                            
                            with col3:
                                st.metric("PO Number", invoice_data.get("po_number") or "N/A")
                                st.metric("Status", invoice_data.get("compliance_status", "Unknown"))
                            
                            with st.expander("📋 Full Invoice Details"):
                                st.json(invoice_data)
                    else:
                        st.warning("No mock invoices found. Run generate_mock_data.py first.")
        
        except Exception as e:
            st.error(f"Error loading mock invoices: {str(e)}")
    
    else:
        # Custom JSON input
        st.markdown("Enter invoice data in JSON format:")
        custom_json = st.text_area(
            "Invoice JSON:",
            height=300,
            placeholder='{"invoice_id": "INV-001", "vendor": "Acme Corp", "amount": 5000, ...}'
        )
        
        if custom_json:
            try:
                invoice_data = json.loads(custom_json)
                st.success("✅ Valid JSON")
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON: {str(e)}")
    
    # Submit button
    if st.button("🚀 Process Transaction", type="primary", disabled=not invoice_data):
        if invoice_data:
            with st.spinner("Processing transaction through TAA → PAA workflow..."):
                try:
                    with httpx.Client(timeout=60.0) as client:
                        response = client.post(
                            f"{API_BASE_URL}/transactions/submit",
                            json={"invoice": invoice_data}
                        )
                        
                        if response.status_code == 201:
                            result = response.json()
                            
                            # Store in session state for HITL tab
                            st.session_state.last_transaction = result
                            
                            # Display result
                            st.markdown("---")
                            st.markdown("### 🎯 Processing Result")
                            
                            # Decision badge
                            decision = result.get("final_decision")
                            if decision == "approved":
                                st.success(f"✅ **APPROVED**")
                            elif decision == "rejected":
                                st.error(f"❌ **REJECTED**")
                            else:
                                st.warning(f"⚠️ **HITL REQUIRED** - Human Review Needed")
                            
                            # Key metrics
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Transaction ID", result.get("transaction_id"))
                            
                            with col2:
                                risk = result.get("risk_assessment", {})
                                st.metric("Risk Level", risk.get("risk_level", "N/A").upper())
                            
                            with col3:
                                st.metric("Risk Score", f"{risk.get('risk_score', 0):.1f}/100")
                            
                            with col4:
                                st.metric("Processing Time", f"{result.get('processing_time_ms', 0)}ms")
                            
                            # Risk Assessment
                            if risk:
                                with st.expander("🎯 Risk Assessment Details"):
                                    st.markdown(f"**Risk Level:** {risk.get('risk_level', 'N/A').upper()}")
                                    st.markdown(f"**Risk Score:** {risk.get('risk_score', 0):.1f}/100")
                                    st.markdown("**Risk Factors:**")
                                    for factor in risk.get("risk_factors", []):
                                        st.write(f"- {factor}")
                            
                            # Policy Check
                            policy_check = result.get("policy_check")
                            if policy_check:
                                with st.expander("📋 Policy Compliance Check"):
                                    st.markdown(f"**Is Compliant:** {'✅ Yes' if policy_check.get('is_compliant') else '❌ No'}")
                                    st.markdown(f"**Confidence:** {policy_check.get('confidence', 0):.2%}")
                                    st.markdown(f"**Reasoning:** {policy_check.get('reasoning', 'N/A')}")
                                    
                                    if policy_check.get("violated_policies"):
                                        st.markdown("**Violated Policies:**")
                                        for policy in policy_check["violated_policies"]:
                                            st.write(f"- {policy}")
                                    
                                    if policy_check.get("applied_exceptions"):
                                        st.markdown("**Applied Exceptions:**")
                                        for exc in policy_check["applied_exceptions"]:
                                            st.write(f"- {exc}")
                            
                            # Decision Reasoning
                            st.markdown("### 💭 Decision Reasoning")
                            st.info(result.get("decision_reasoning", "No reasoning provided"))
                            
                            # Audit Trail
                            with st.expander("📜 Complete Audit Trail"):
                                audit_trail = result.get("audit_trail", [])
                                for idx, step in enumerate(audit_trail, 1):
                                    st.write(f"{idx}. {step}")
                            
                            # HITL prompt
                            if decision == "hitl":
                                st.markdown("---")
                                st.info("👤 This transaction requires human review. Go to the **Human Review (HITL)** tab to provide feedback.")
                        
                        else:
                            st.error(f"Error: {response.status_code} - {response.text}")
                
                except Exception as e:
                    st.error(f"Error processing transaction: {str(e)}")

# ==================== TAB 2: TRANSACTION HISTORY ====================
with tab2:
    st.markdown("### Recent Transactions")
    
    col_refresh, col_clear = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    with col_clear:
        if "selected_transaction" in st.session_state and st.button("✖️ Clear Selection", use_container_width=True):
            del st.session_state.selected_transaction
            st.rerun()
    
    # Show selected transaction details if any
    if "selected_transaction" in st.session_state:
        st.markdown("---")
        st.markdown("### 📋 Transaction Details")
        
        trans = st.session_state.selected_transaction
        
        # Header info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Transaction ID", trans.get("transaction_id", "N/A"))
        with col2:
            st.metric("Invoice ID", trans.get("invoice", {}).get("invoice_id", "N/A"))
        with col3:
            decision = trans.get("final_decision", "N/A").upper()
            if decision == "APPROVED":
                st.success(f"✅ {decision}")
            elif decision == "REJECTED":
                st.error(f"❌ {decision}")
            else:
                st.warning(f"⚠️ {decision}")
        
        # Full details in tabs
        detail_tab1, detail_tab2, detail_tab3 = st.tabs(["📊 Overview", "📜 Audit Trail", "📋 Raw Data"])
        
        with detail_tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Risk Assessment:**")
                st.write(f"- Level: {trans.get('risk_level', 'N/A').upper()}")
                st.write(f"- Score: {trans.get('risk_score', 0):.1f}/100")
                st.write(f"- Human Override: {'Yes' if trans.get('human_override') else 'No'}")
                st.write(f"- Processing Time: {trans.get('processing_time_ms', 0)}ms")
                
                st.markdown("**Decision:**")
                st.info(trans.get("decision_reasoning", "No reasoning available"))
            
            with col2:
                if trans.get("invoice"):
                    st.markdown("**Invoice Details:**")
                    invoice = trans["invoice"]
                    st.write(f"- Vendor: {invoice.get('vendor')}")
                    st.write(f"- Amount: ${invoice.get('amount', 0):,.2f}")
                    st.write(f"- Category: {invoice.get('category')}")
                    st.write(f"- PO Number: {invoice.get('po_number', 'N/A')}")
                    st.write(f"- International: {'Yes' if invoice.get('international') else 'No'}")
                    
                st.markdown(f"**Created:** {trans.get('created_at', 'N/A')}")
        
        with detail_tab2:
            st.markdown("**Complete Audit Trail:**")
            audit_trail = trans.get("audit_trail", [])
            if audit_trail:
                for idx, step in enumerate(audit_trail, 1):
                    st.write(f"{idx}. {step}")
            else:
                st.info("No audit trail available")
        
        with detail_tab3:
            st.json(trans)
        
        st.markdown("---")
    
    # Transaction list
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/transactions?limit=20")
            
            if response.status_code == 200:
                transactions = response.json()
                
                if transactions:
                    st.markdown(f"**Showing {len(transactions)} most recent transactions**")
                    
                    for trans in transactions:
                        # Highlight selected transaction
                        is_selected = ("selected_transaction" in st.session_state and 
                                     st.session_state.selected_transaction.get("transaction_id") == trans.get("transaction_id"))
                        
                        expander_label = f"{'🔍 ' if is_selected else ''}🧾 {trans.get('invoice_id', 'N/A')} - {trans.get('final_decision', 'N/A').upper()}"
                        
                        with st.expander(expander_label, expanded=is_selected):
                            col1, col2, col3 = st.columns([3, 3, 2])
                            
                            with col1:
                                st.markdown(f"**Invoice:** {trans.get('invoice_id', 'N/A')}")
                                st.markdown(f"**Vendor:** {trans.get('invoice', {}).get('vendor', 'N/A')}")
                                st.markdown(f"**Amount:** ${trans.get('invoice', {}).get('amount', 0):,.2f}")
                            
                            with col2:
                                st.markdown(f"**Decision:** {trans.get('final_decision', 'N/A').upper()}")
                                st.markdown(f"**Risk:** {trans.get('risk_level', 'N/A').upper()} ({trans.get('risk_score', 0):.1f})")
                                st.markdown(f"**Override:** {'Yes' if trans.get('human_override') else 'No'}")
                            
                            with col3:
                                if st.button("View Details", key=f"view_{trans.get('transaction_id')}", use_container_width=True):
                                    st.session_state.selected_transaction = trans
                                    st.rerun()
                else:
                    st.info("No transactions found. Submit your first transaction above!")
            
            else:
                st.error(f"Error loading transactions: {response.status_code}")
    
    except Exception as e:
        st.error(f"Error: {str(e)}")

# ==================== TAB 3: HUMAN REVIEW (HITL) ====================
with tab3:
    st.markdown("### 👤 Human-in-the-Loop (HITL) Feedback")
    st.markdown("Provide feedback on transactions. Your feedback helps the system learn!")
    
    # Fetch all transactions for selection
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/transactions?limit=50")
            
            if response.status_code == 200:
                all_transactions = response.json()
                
                if all_transactions:
                    # Transaction selector
                    st.markdown("#### Select Transaction for Feedback")
                    
                    # Create selection options
                    transaction_options = {}
                    for t in all_transactions:
                        label = f"{t.get('invoice_id', 'N/A')} - {t.get('final_decision', 'N/A').upper()} - ${t.get('invoice', {}).get('amount', 0):,.2f}"
                        transaction_options[label] = t
                    
                    # Use last_transaction if available, otherwise first transaction
                    default_trans = None
                    if "last_transaction" in st.session_state:
                        default_trans = st.session_state.last_transaction
                    elif all_transactions:
                        default_trans = all_transactions[0]
                    
                    # Find default index
                    default_index = 0
                    if default_trans:
                        for idx, (label, t) in enumerate(transaction_options.items()):
                            if t.get("transaction_id") == default_trans.get("transaction_id"):
                                default_index = idx
                                break
                    
                    selected_label = st.selectbox(
                        "Choose a transaction:",
                        options=list(transaction_options.keys()),
                        index=default_index
                    )
                    
                    trans = transaction_options[selected_label]
                else:
                    trans = None
                    st.info("No transactions available. Submit a transaction first!")
            else:
                trans = None
                st.error("Failed to load transactions")
    except Exception as e:
        trans = None
        st.error(f"Error loading transactions: {e}")
    
    if trans:
        
        st.markdown("#### Selected Transaction for Review")
        
        # Display transaction summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Transaction ID", trans.get("transaction_id"))
            st.metric("Invoice ID", trans.get("invoice", {}).get("invoice_id"))
        
        with col2:
            st.metric("System Decision", trans.get("final_decision", "N/A").upper())
            st.metric("Risk Level", trans.get("risk_assessment", {}).get("risk_level", "N/A").upper())
        
        with col3:
            invoice = trans.get("invoice", {})
            st.metric("Amount", f"${invoice.get('amount', 0):,.2f}")
            st.metric("Vendor", invoice.get("vendor", "N/A"))
        
        st.markdown("---")
        st.markdown("#### Provide Your Decision")
        
        # HITL form
        with st.form("hitl_form"):
            human_decision = st.radio(
                "Your Decision:",
                ["approved", "rejected"],
                format_func=lambda x: "✅ Approve" if x == "approved" else "❌ Reject",
                horizontal=True
            )
            
            reasoning = st.text_area(
                "Reasoning (required):",
                placeholder="Explain why you're overriding the system decision or confirming it...",
                help="This reasoning helps the system learn from your decision"
            )
            
            should_create_exception = st.checkbox(
                "Create Exception Rule",
                value=False,
                help="Check this if the system should learn this rule for similar future transactions"
            )
            
            exception_type = None
            if should_create_exception:
                exception_type = st.selectbox(
                    "Exception Type:",
                    ["recurring", "temporary", "policy_gap"],
                    format_func=lambda x: {
                        "recurring": "Recurring (applies to similar transactions)",
                        "temporary": "Temporary (one-time exception)",
                        "policy_gap": "Policy Gap (missing policy coverage)"
                    }[x]
                )
            
            submit_hitl = st.form_submit_button("💾 Submit Feedback", type="primary")
            
            if submit_hitl:
                if not reasoning:
                    st.error("Please provide reasoning for your decision")
                else:
                    with st.spinner("Processing feedback through EMA..."):
                        try:
                            feedback_data = {
                                "transaction_id": trans.get("transaction_id"),
                                "invoice_id": invoice.get("invoice_id"),
                                "original_decision": trans.get("final_decision"),
                                "human_decision": human_decision,
                                "reasoning": reasoning,
                                "should_create_exception": should_create_exception,
                                "exception_type": exception_type
                            }
                            
                            with httpx.Client(timeout=60.0) as client:
                                response = client.post(
                                    f"{API_BASE_URL}/transactions/{trans.get('transaction_id')}/hitl",
                                    json=feedback_data
                                )
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    
                                    st.success("✅ Feedback processed successfully!")
                                    
                                    # Show EMA result
                                    ema_result = result.get("ema_result", {})
                                    
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.metric("Memory Updated", "✅ Yes" if result.get("memory_updated") else "No")
                                    
                                    with col2:
                                        st.metric("H-CR Updated", "✅ Yes" if result.get("hcr_updated") else "No")
                                    
                                    if ema_result.get("correction_type"):
                                        st.info(f"**Correction Type:** {ema_result.get('correction_type')}")
                                    
                                    if ema_result.get("exception_description"):
                                        st.success(f"**Learned Rule:** {ema_result.get('exception_description')}")
                                    
                                    st.info("💡 KPIs and Memory have been updated. Check the KPI Dashboard and Memory Browser!")
                                    
                                    # Clear last transaction (but keep in history)
                                    if "last_transaction" in st.session_state:
                                        del st.session_state.last_transaction
                                
                                else:
                                    st.error(f"Error: {response.status_code} - {response.text}")
                        
                        except Exception as e:
                            st.error(f"Error submitting feedback: {str(e)}")
    

