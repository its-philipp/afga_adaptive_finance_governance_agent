"""API routes for AFGA."""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status

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


logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize orchestrator and services
orchestrator = AFGAOrchestrator()
kpi_tracker = KPITracker(memory_db=orchestrator.memory_db)


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
    """Submit a new transaction for processing.
    
    The transaction will be processed through the TAA → PAA workflow
    and a final decision (approve/reject/HITL) will be returned.
    """
    try:
        logger.info(f"Submitting transaction: {request.invoice.invoice_id}")
        
        result = orchestrator.process_transaction(
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


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    """Get transaction details by ID."""
    transaction = orchestrator.get_transaction(transaction_id)
    
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
    transactions = orchestrator.get_recent_transactions(limit=limit)
    
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
        transaction = orchestrator.get_transaction(transaction_id)
        
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
        
        result = orchestrator.process_hitl_feedback(
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
        
        exceptions = orchestrator.ema.memory_manager.db.query_exceptions(query)
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
        stats = orchestrator.get_memory_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting memory stats: {str(e)}"
        )


# ==================== AGENT ENDPOINTS ====================

@router.get("/agents/cards")
def get_agent_cards():
    """Get A2A agent cards for all agents."""
    try:
        cards = orchestrator.get_agent_cards()
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

