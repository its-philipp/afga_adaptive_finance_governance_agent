"""API routes for AFGA."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, UploadFile, File

from ..agents import AFGAOrchestrator
from ..models.schemas import (
    Invoice,
    HITLFeedback,
    TransactionRequest,
    TransactionResult,
    TransactionSummary,
    KPIMetrics,
    DecisionType,
)
from ..models.memory_schemas import MemoryQuery, MemoryStats
from ..services import KPITracker
from ..services.invoice_extractor import InvoiceExtractor


logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize orchestrator and services
# TEMPORARY DEV FIX: Force rebuild on EVERY request until LangGraph caching is resolved
def get_orchestrator():
    """Get fresh orchestrator instance on every request.
    
    TEMPORARY: LangGraph compiles workflows ONCE and keeps old method bindings.
    Even after restart, compiled graphs persist with old code.
    This forces rebuild on every request for clean audit trails during development.
    
    TODO: Remove this hack once in production (or find better LangGraph reload solution)
    """
    logger.debug("Creating fresh orchestrator with recompiled LangGraph workflows")
    return AFGAOrchestrator()


# Legacy global references - initialize once for startup
_startup_orch = get_orchestrator()
kpi_tracker = KPITracker(memory_db=_startup_orch.memory_db)
invoice_extractor = InvoiceExtractor()

# Helper to get orchestrator instance (use cached for read operations)
def get_orch_cached():
    """Get cached orchestrator for read operations."""
    return _startup_orch


@router.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agents": {
            "taa": "running",
            "paa": "running",
            "ema": "running",
        },
        "services": {
            "orchestrator": "running",
            "kpi_tracker": "running",
            "memory_db": "connected",
        }
    }


# ==================== TRANSACTION ENDPOINTS ====================

@router.post("/transactions/submit", response_model=TransactionResult, status_code=status.HTTP_201_CREATED)
def submit_transaction(request: TransactionRequest):
    """Submit a new transaction for processing (structured JSON).
    
    The transaction will be processed through the TAA → PAA workflow
    and a final decision (approve/reject/HITL) will be returned.
    """
    try:
        logger.info(f"Submitting transaction: {request.invoice.invoice_id}")
        
        # Get fresh orchestrator (will rebuild if TAA changed)
        orch = get_orchestrator()
        result = orch.process_transaction(
            invoice=request.invoice,
            trace_id=request.trace_id,
        )
        
        logger.info(f"Transaction {request.invoice.invoice_id} processed: {result.final_decision.value}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing transaction: {str(e)}"
        )


@router.post("/transactions/upload-receipt", response_model=TransactionResult, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: UploadFile = File(...),
    source: str = "expense_report",
):
    """Upload a receipt/invoice document (PDF or image) for automated extraction and processing.
    
    Supported formats: PDF, PNG, JPG, JPEG, WEBP
    
    The document will be:
    1. Extracted using Vision LLM (GPT-4 Vision)
    2. Structured into Invoice format
    3. Processed through TAA → PAA workflow
    4. Decision returned (approve/reject/HITL)
    """
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}
        file_ext = Path(file.filename).suffix.lower() if file.filename else ''
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
            )
        
        logger.info(f"Uploading document: {file.filename}")
        
        # Read file bytes
        file_bytes = await file.read()
        
        # Extract invoice data using Vision LLM
        logger.info(f"Extracting invoice data from {file.filename}")
        invoice = invoice_extractor.extract_from_document(
            file_bytes=file_bytes,
            filename=file.filename,
            source=source,
        )
        
        logger.info(f"Extracted invoice: {invoice.invoice_id} from {file.filename}")
        
        # Process through normal workflow
        result = orchestrator.process_transaction(invoice=invoice)
        
        logger.info(f"Document {file.filename} processed: {result.final_decision.value}")
        return result
        
    except ValueError as e:
        # Extraction or validation error
        logger.error(f"Error extracting invoice data: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not extract valid invoice data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    """Get transaction details by ID."""
    transaction = get_orch_cached().get_transaction(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found"
        )
    
    # Parse JSON fields
    if "invoice_data" in transaction:
        transaction["invoice"] = json.loads(transaction["invoice_data"])
    if "audit_trail" in transaction:
        transaction["audit_trail"] = json.loads(transaction["audit_trail"])
    
    return transaction


@router.get("/transactions", response_model=List[dict])
def list_transactions(limit: int = 10):
    """List recent transactions."""
    transactions = get_orch_cached().get_recent_transactions(limit=limit)
    
    # Parse JSON fields
    for trans in transactions:
        if "invoice_data" in trans:
            trans["invoice"] = json.loads(trans["invoice_data"])
        if "audit_trail" in trans:
            trans["audit_trail"] = json.loads(trans["audit_trail"])
    
    return transactions


@router.post("/transactions/{transaction_id}/hitl")
def submit_hitl_feedback(transaction_id: str, feedback: HITLFeedback):
    """Submit human-in-the-loop feedback for a transaction.
    
    This endpoint is called when a human reviewer overrides an automated decision.
    The feedback is processed by EMA to potentially update adaptive memory.
    """
    try:
        # Get original transaction
        transaction = get_orch_cached().get_transaction(transaction_id)
        
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction {transaction_id} not found"
            )
        
        # Parse invoice data
        invoice_data = json.loads(transaction["invoice_data"])
        invoice = Invoice(**invoice_data)
        
        # Update feedback with transaction ID
        feedback.transaction_id = transaction_id
        
        logger.info(f"Processing HITL feedback for transaction {transaction_id}")
        
        # Use fresh orchestrator for HITL processing
        orch = get_orchestrator()
        result = orch.process_hitl_feedback(
            feedback=feedback,
            invoice=invoice,
            trace_id=transaction.get("trace_id"),
        )
        
        logger.info(f"HITL feedback processed for {transaction_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing HITL feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing HITL feedback: {str(e)}"
        )


# ==================== KPI ENDPOINTS ====================

@router.get("/kpis/current", response_model=KPIMetrics)
def get_current_kpis():
    """Get current KPI values for today."""
    try:
        kpis = kpi_tracker.calculate_current_kpis()
        return kpis
    except Exception as e:
        logger.error(f"Error calculating KPIs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating KPIs: {str(e)}"
        )


@router.get("/kpis/trend")
def get_kpi_trend(days: int = 30):
    """Get KPI trend over time.
    
    Args:
        days: Number of days to retrieve (default 30)
    """
    try:
        kpis = kpi_tracker.get_kpi_trend(days=days)
        return {"days": days, "kpis": [kpi.model_dump() for kpi in kpis]}
    except Exception as e:
        logger.error(f"Error getting KPI trend: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting KPI trend: {str(e)}"
        )


@router.get("/kpis/summary")
def get_kpi_summary():
    """Get comprehensive KPI summary with trends and learning metrics."""
    try:
        summary = kpi_tracker.get_kpi_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting KPI summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting KPI summary: {str(e)}"
        )


@router.get("/kpis/stats")
def get_transaction_stats():
    """Get transaction statistics."""
    try:
        stats = kpi_tracker.get_transaction_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting transaction stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting transaction stats: {str(e)}"
        )


# ==================== MEMORY ENDPOINTS ====================

@router.get("/memory/exceptions")
def list_memory_exceptions(
    vendor: Optional[str] = None,
    category: Optional[str] = None,
    rule_type: Optional[str] = None,
):
    """List exceptions in adaptive memory.
    
    Args:
        vendor: Filter by vendor
        category: Filter by category
        rule_type: Filter by rule type
    """
    try:
        query = MemoryQuery(
            vendor=vendor,
            category=category,
            rule_type=rule_type,
        )
        
        exceptions = get_orch_cached().ema.memory_manager.db.query_exceptions(query)
        return {"exceptions": [exc.model_dump() for exc in exceptions]}
    except Exception as e:
        logger.error(f"Error querying memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying memory: {str(e)}"
        )


@router.get("/memory/stats", response_model=MemoryStats)
def get_memory_stats():
    """Get statistics about the adaptive memory."""
    try:
        stats = get_orch_cached().get_memory_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting memory stats: {str(e)}"
        )


@router.delete("/memory/exceptions/{exception_id}")
def delete_exception(exception_id: str):
    """Soft-delete an exception from adaptive memory."""
    try:
        deleted = get_orch_cached().ema.memory_manager.db.delete_exception(exception_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exception {exception_id} not found or already deleted"
            )
        
        logger.info(f"Soft-deleted exception {exception_id}")
        return {"message": f"Exception {exception_id} deleted successfully", "exception_id": exception_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting exception: {str(e)}"
        )


@router.post("/memory/exceptions/{exception_id}/restore")
def restore_exception(exception_id: str):
    """Restore a soft-deleted exception."""
    try:
        restored = get_orch_cached().ema.memory_manager.db.restore_exception(exception_id)
        
        if not restored:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exception {exception_id} not found or already active"
            )
        
        logger.info(f"Restored exception {exception_id}")
        return {"message": f"Exception {exception_id} restored successfully", "exception_id": exception_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restoring exception: {str(e)}"
        )


@router.get("/memory/exceptions/deleted")
def list_deleted_exceptions():
    """List soft-deleted exceptions."""
    try:
        conn = get_orch_cached().ema.memory_manager.db.db_path
        import sqlite3
        conn = sqlite3.connect(conn)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM adaptive_memory
            WHERE is_active = 0
            ORDER BY deleted_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        from ..models.memory_schemas import MemoryException
        exceptions = []
        for row in rows:
            row_dict = dict(row)
            row_dict["condition"] = json.loads(row_dict.get("condition", "{}"))
            exceptions.append(MemoryException(**row_dict))
        
        return {"exceptions": [exc.model_dump() for exc in exceptions]}
        
    except Exception as e:
        logger.error(f"Error querying deleted exceptions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error querying deleted exceptions: {str(e)}"
        )


# ==================== AGENT ENDPOINTS ====================

@router.get("/agents/cards")
def get_agent_cards():
    """Get A2A agent cards for all agents."""
    try:
        cards = get_orch_cached().get_agent_cards()
        return cards
    except Exception as e:
        logger.error(f"Error getting agent cards: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent cards: {str(e)}"
        )


# ==================== DEMO/TEST ENDPOINTS ====================

@router.post("/demo/process-mock-invoice")
def process_mock_invoice(invoice_file: str):
    """Process a mock invoice from the data/mock_invoices directory.
    
    Args:
        invoice_file: Filename of the invoice (e.g., "INV-0001.json")
    """
    try:
        import json
        from pathlib import Path
        
        invoice_path = Path("data/mock_invoices") / invoice_file
        
        if not invoice_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice file {invoice_file} not found"
            )
        
        with open(invoice_path, 'r') as f:
            invoice_data = json.load(f)
        
        invoice = Invoice(**invoice_data)
        
        result = orchestrator.process_transaction(invoice=invoice)
        
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"Error processing mock invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing mock invoice: {str(e)}"
        )


@router.get("/demo/list-mock-invoices")
def list_mock_invoices():
    """List available mock invoices."""
    try:
        from pathlib import Path
        
        invoices_dir = Path("data/mock_invoices")
        
        if not invoices_dir.exists():
            return {"invoices": []}
        
        invoice_files = [
            f.name for f in invoices_dir.glob("INV-*.json")
        ]
        
        return {"invoices": sorted(invoice_files)}
    except Exception as e:
        logger.error(f"Error listing mock invoices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing mock invoices: {str(e)}"
        )

