"""API routes for AFGA."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from urllib.parse import quote

from ..agents import AFGAOrchestrator
from ..models.schemas import (
    Invoice,
    HITLFeedback,
    TransactionRequest,
    TransactionResult,
    TransactionSummary,
    KPIMetrics,
    DecisionType,
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantChatSource,
)
from ..models.memory_schemas import MemoryQuery, MemoryStats
from ..services import KPITracker
from ..services.invoice_extractor import InvoiceExtractor
from ..services.langfuse_insights import get_langfuse_insights
from ..governance import GovernedLLMClient


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
langfuse_insights = get_langfuse_insights()

# Helper to get orchestrator instance (use cached for read operations)
def get_orch_cached():
    """Get cached orchestrator for read operations."""
    return _startup_orch


def _coerce_json(value):
    """Ensure database JSON fields are returned as native Python objects."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning("Failed to json.loads value; returning raw string", exc_info=True)
            return value
    return value


def _search_memory_rules(query: str, limit: int = 3) -> list[dict]:
    """Return matching adaptive memory rules for assistant context."""
    memory_db = get_orch_cached().memory_db
    try:
        exceptions = memory_db.query_exceptions(MemoryQuery())
    except Exception as exc:
        logger.warning(f"Memory query failed: {exc}")
        return []

    if not exceptions:
        return []

    query_terms = {term for term in (query or "").lower().split() if term}
    scored: list[tuple[float, MemoryStats]] = []  # type: ignore[assignment]

    matches = []
    for exc in exceptions:
        searchable = " ".join(
            filter(
                None,
                [
                    exc.vendor or "",
                    exc.category or "",
                    exc.description,
                    json.dumps(exc.condition),
                ],
            )
        ).lower()
        score = 0.0
        for term in query_terms:
            if term in searchable:
                score += 1.0
        score += exc.applied_count * 0.1
        matches.append(
            {
                "exception_id": exc.exception_id,
                "vendor": exc.vendor,
                "category": exc.category,
                "description": exc.description,
                "condition": exc.condition,
                "applied_count": exc.applied_count,
                "score": score,
            }
        )

    matches.sort(key=lambda item: item["score"], reverse=True)

    if all(match["score"] == 0 for match in matches):
        matches.sort(key=lambda item: item["applied_count"], reverse=True)

    return matches[:limit]


def _flatten_context_text(context: dict | None) -> str:
    """Flatten nested context values into a single search string."""
    if not context:
        return ""

    parts: list[str] = []

    def _walk(value):
        if value is None:
            return
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (int, float, bool)):
            parts.append(str(value))
        elif isinstance(value, dict):
            for nested in value.values():
                _walk(nested)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                _walk(item)

    _walk(context)
    joined = " ".join(parts)
    return joined[:2000]  # prevent excessively long queries


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
        uploads_dir = Path("data/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)
        temp_name = f"{uuid4().hex}{file_ext}"
        temp_path = uploads_dir / temp_name

        # Read file bytes
        file_bytes = await file.read()
        with open(temp_path, "wb") as temp_file:
            temp_file.write(file_bytes)
        
        # Extract invoice data using Vision LLM
        logger.info(f"Extracting invoice data from {file.filename}")
        invoice = invoice_extractor.extract_from_document(
            file_bytes=file_bytes,
            filename=file.filename,
            source=source,
        )
        
        logger.info(f"Extracted invoice: {invoice.invoice_id} from {file.filename}")
        
        # Process through normal workflow
        orch = get_orchestrator()
        result = orch.process_transaction(invoice=invoice)

        final_path = temp_path
        try:
            final_filename = f"{result.transaction_id}{file_ext}"
            final_path = uploads_dir / final_filename
            shutil.move(str(temp_path), str(final_path))
        except Exception as move_err:
            logger.warning(f"Unable to rename uploaded file {temp_path} -> {final_path}: {move_err}")

        if final_path.exists():
            final_path_str = str(final_path)
        elif temp_path.exists():
            final_path = temp_path
            final_path_str = str(final_path)
        else:
            final_path_str = None

        if final_path_str:
            result.source_document_path = final_path_str
            try:
                orch.memory_db.update_transaction_source(result.transaction_id, final_path_str)
            except Exception as update_err:
                logger.warning(f"Failed to update transaction with source document path: {update_err}")
        
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
        transaction["invoice"] = _coerce_json(transaction["invoice_data"])
    if "audit_trail" in transaction:
        transaction["audit_trail"] = _coerce_json(transaction["audit_trail"])
    if "policy_check" in transaction:
        transaction["policy_check"] = _coerce_json(transaction["policy_check"])
    elif "policy_check_json" in transaction:
        transaction["policy_check"] = _coerce_json(transaction["policy_check_json"])
        del transaction["policy_check_json"]
    
    return transaction


@router.get("/transactions", response_model=List[dict])
def list_transactions(limit: int = 10):
    """List recent transactions."""
    transactions = get_orch_cached().get_recent_transactions(limit=limit)
    
    # Parse JSON fields
    for trans in transactions:
        if "invoice_data" in trans:
            trans["invoice"] = _coerce_json(trans["invoice_data"])
        if "audit_trail" in trans:
            trans["audit_trail"] = _coerce_json(trans["audit_trail"])
        if "policy_check" in trans:
            trans["policy_check"] = _coerce_json(trans["policy_check"])
        elif "policy_check_json" in trans:
            trans["policy_check"] = _coerce_json(trans["policy_check_json"])
            del trans["policy_check_json"]
    
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
        invoice_payload = _coerce_json(transaction.get("invoice_data"))
        if not isinstance(invoice_payload, dict):
            # Fallback to already parsed invoice payload if available
            invoice_payload = transaction.get("invoice", {})
        invoice = Invoice(**invoice_payload)
        
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
        
        exceptions = get_orch_cached().memory_db.query_exceptions(query)
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
        deleted = get_orch_cached().memory_db.delete_exception(exception_id)
        
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
        restored = get_orch_cached().memory_db.restore_exception(exception_id)
        
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
        db_path = get_orch_cached().memory_db.db_path
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM adaptive_memory
            WHERE is_active = 0
            ORDER BY deleted_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to dicts manually (avoid MemoryException import issues)
        exceptions = []
        for row in rows:
            row_dict = dict(row)
            # Parse condition JSON
            try:
                row_dict["condition"] = json.loads(row_dict.get("condition", "{}"))
            except:
                row_dict["condition"] = {}
            exceptions.append(row_dict)
        
        return {"exceptions": exceptions}
        
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
        
        orch = get_orchestrator()
        result = orch.process_transaction(invoice=invoice)
        
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


# ==================== OBSERVABILITY ====================

@router.get("/observability/langfuse")
def get_langfuse_overview():
    """Return Langfuse connectivity status and local audit analytics."""
    try:
        return langfuse_insights.get_summary()
    except Exception as e:
        logger.error(f"Error fetching Langfuse insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching Langfuse insights: {str(e)}"
        )


@router.post("/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    """Handle governance assistant chat requests."""
    logger.info("Assistant chat request received for page=%s", request.page)

    policy_retriever = getattr(_startup_orch.policy_mcp, "policy_retriever", None)
    context_dict = request.context or {}
    flattened_context = _flatten_context_text(context_dict)

    # Gather policy matches
    policy_matches: dict[tuple[str | None, int], dict] = {}
    if policy_retriever:
        queries = set(filter(None, [request.message.strip(), flattened_context.strip()]))
        # Include vendor/category hints from selected transaction if present
        selected_txn = context_dict.get("selected_transaction", {}) if isinstance(context_dict, dict) else {}
        vendor = selected_txn.get("vendor")
        category = selected_txn.get("invoice", {}).get("category") if isinstance(selected_txn.get("invoice"), dict) else None
        extra_terms = " ".join(filter(None, [vendor, category]))
        if extra_terms:
            queries.add(extra_terms)
        for query in queries:
            for match in policy_retriever.search_by_text(query, top_k=5):
                key = (match.get("policy_filename"), match.get("chunk_index", 0))
                if key not in policy_matches or match.get("score", 0) > policy_matches[key].get("score", 0):
                    policy_matches[key] = match
    else:
        logger.warning("Policy retriever unavailable for assistant chat")

    policy_list = list(policy_matches.values())[:5]

    # Gather memory matches
    memory_matches = _search_memory_rules(request.message)

    # Build prompt sections
    import json as _json

    context_section = _json.dumps(context_dict, indent=2, default=str) if context_dict else "{}"

    policy_section_lines = []
    for idx, match in enumerate(policy_list, start=1):
        snippet = match.get("snippet") or match.get("content", "")
        snippet = (snippet or "").strip()
        if len(snippet) > 600:
            snippet = f"{snippet[:600]}..."
        policy_section_lines.append(
            f"{idx}. {match.get('policy_name', 'Unknown Policy')} (score: {match.get('score', 0):.2f})\n"
            f"   Source: {match.get('policy_filename', 'N/A')} • Chunk #{match.get('chunk_index', 0)}\n"
            f"   Excerpt: {snippet}"
        )
    policy_section = "\n".join(policy_section_lines) if policy_section_lines else "No direct policy passages retrieved."

    memory_section_lines = []
    for match in memory_matches:
        condition_preview = match.get("condition")
        try:
            condition_str = _json.dumps(condition_preview, ensure_ascii=False) if condition_preview else "{}"
        except TypeError:
            condition_str = str(condition_preview)
        memory_section_lines.append(
            f"- {match.get('description', 'Learned rule')} (ID: {match.get('exception_id')})\n"
            f"  Vendor: {match.get('vendor') or 'Any'} • Category: {match.get('category') or 'Any'} • Applied: {match.get('applied_count', 0)} times\n"
            f"  Condition: {condition_str}"
        )
    memory_section = "\n".join(memory_section_lines) if memory_section_lines else "No learned exceptions matched the query."

    # Construct LLM prompt
    system_instructions = (
        "You are the AFGA Governance Assistant. Provide precise, compliant answers based on the provided context, "
        "policy evidence, and learned exception rules. Reference policy names or exception IDs when relevant. "
        "Keep the tone professional and focused on auditability. Include a short 'Suggested follow-ups' list with "
        "one or two bullet points when it helps the user continue the investigation."
    )

    prompt = (
        f"{system_instructions}\n\n"
        f"## Page Context\n{context_section}\n\n"
        f"## Relevant Policy Evidence\n{policy_section}\n\n"
        f"## Learned Exceptions\n{memory_section}\n\n"
        f"## User Question\n{request.message.strip()}"
    )

    history_messages = [
        {"role": entry.role, "content": entry.content}
        for entry in request.history
        if entry.role in {"user", "assistant"}
    ]

    client = GovernedLLMClient(agent_name="GovernanceAssistant")
    try:
        reply = client.completion(
            prompt=prompt,
            context=history_messages,
            model=None,
            temperature=0.2,
        )
    except ValueError as exc:
        logger.warning("Assistant chat blocked by governance: %s", exc)
        friendly_message = (
            "🚫 Request blocked by guardrails.\n"
            f"Details: {exc}.\n"
            "Please remove sensitive data or forbidden terms and try again."
        )
        violation_sources = [
            AssistantChatSource(
                type="governance_violation",
                id="input_validation",
                title="Input validation blocked the request",
                snippet=str(exc),
            )
        ]
        return AssistantChatResponse(reply=friendly_message, sources=violation_sources)
    except Exception as exc:
        logger.error("Assistant chat failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assistant chat failed: {exc}"
        )
    finally:
        try:
            client.close()
        except Exception:
            pass

    # Build sources for UI transparency
    sources: List[AssistantChatSource] = []
    for match in policy_list:
        filename = match.get("policy_filename")
        streamlit_path = f"Policy_Viewer?policy={quote(filename)}" if filename else None
        snippet = match.get("snippet") or match.get("content")
        if snippet and len(snippet) > 280:
            snippet = f"{snippet[:280]}..."
        sources.append(
            AssistantChatSource(
                type="policy",
                id=match.get("policy_name", filename or "policy"),
                title=filename or match.get("policy_name", "Policy excerpt"),
                snippet=snippet,
                url=f"streamlit://{streamlit_path}" if streamlit_path else None,
            )
        )

    for match in memory_matches:
        snippet_parts = [match.get("description") or "Learned rule"]
        vendor = match.get("vendor")
        category = match.get("category")
        if vendor or category:
            snippet_parts.append(
                " | ".join(filter(None, [f"Vendor: {vendor}" if vendor else None, f"Category: {category}" if category else None]))
            )
        snippet_parts.append(f"Applied {match.get('applied_count', 0)} time(s)")
        sources.append(
            AssistantChatSource(
                type="memory_rule",
                id=str(match.get("exception_id")),
                title=match.get("description", "Adaptive memory rule"),
                snippet="; ".join(snippet_parts),
            )
        )

    return AssistantChatResponse(reply=reply.strip(), sources=sources)


@router.get("/policies/{policy_filename}")
def download_policy(policy_filename: str):
    """Serve policy document content for transparency links."""
    policy_retriever = getattr(_startup_orch.policy_mcp, "policy_retriever", None)
    if not policy_retriever:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Policy retriever not available")

    safe_name = Path(policy_filename).name
    policy_path = policy_retriever.policies_dir / safe_name
    if not policy_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Policy file {safe_name} not found")

    return FileResponse(path=policy_path, media_type="text/plain", filename=safe_name)

