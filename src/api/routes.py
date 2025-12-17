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
    BatchTransactionRequest,
    BatchTransactionResponse,
    ProcessPendingRequest,
    ProcessPendingResponse,
    ProcessPendingItem,
)
from ..models.memory_schemas import MemoryQuery, MemoryStats
from ..services import KPITracker
from ..services.invoice_extractor import InvoiceExtractor
from ..services.langfuse_insights import get_langfuse_insights
from ..services.databricks_embeddings import (
    get_embeddings_stats,
    DatabricksUnavailable,
    search_embeddings,
)
from ..services.databricks_sink import get_databricks_sink
from ..services.similarity_advisor import get_similarity_advisor
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
        },
    }


# ==================== DATABRICKS EMBEDDINGS ====================


@router.get("/databricks/embeddings/stats", status_code=status.HTTP_200_OK)
def databricks_embeddings_stats(limit: int = 25):
    """Return sample embedding rows and table statistics."""
    try:
        stats = get_embeddings_stats(limit=limit)
        return stats
    except DatabricksUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.error("Embedding stats failed", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed querying gold table: {exc}") from exc


@router.post("/databricks/embeddings/search", status_code=status.HTTP_200_OK)
def databricks_embeddings_search(payload: dict):
    """Return top-k similar embeddings for a provided query string.

    Payload example:
    {
      "query": "Consulting invoice for Q4 advisory",
      "k": 5,
      "sample_limit": 300,
      "openai_api_key": "sk-..."  # optional override
    }
    """
    query = payload.get("query", "")
    k = int(payload.get("k", 5))
    sample_limit = int(payload.get("sample_limit", 500))
    override_key = payload.get("openai_api_key")
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=400, detail="'query' must be a non-empty string")
    if k <= 0:
        raise HTTPException(status_code=400, detail="'k' must be > 0")
    try:
        results = search_embeddings(
            query=query,
            k=k,
            sample_limit=sample_limit,
            openai_api_key_override=override_key,
        )
        return results
    except DatabricksUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.error("Similarity search failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ==================== DATABRICKS BACKFILL ====================


@router.post("/databricks/backfill", status_code=status.HTTP_200_OK)
def databricks_backfill(limit: int = 500, force: bool = False, dry_run: bool = False, skip_duplicates: bool = True):
    """Backfill previously processed transactions to Azure Blob for Databricks ingestion.

    Args:
        limit: Maximum number of transactions to consider (ordered by created_at ASC)
        force: Upload even if duplicate hash detected
        dry_run: Only report what would be uploaded
        skip_duplicates: If True, do not re-upload invoices whose content hash already exists
    """
    import sqlite3
    sink = get_databricks_sink()
    if not sink.enabled:
        raise HTTPException(status_code=503, detail="Databricks sink disabled (missing AZURE_STORAGE_CONNECTION_STRING)")

    memory_db = get_orch_cached().memory_db
    conn = sqlite3.connect(memory_db.db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT transaction_id, invoice_data, audit_trail, created_at
        FROM transactions
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    uploaded = 0
    skipped = 0
    duplicate_skipped = 0
    trail_uploaded = 0

    # Local duplicate registry to avoid recomputing sink logic for dry run
    seen_hashes: set[str] = set(sink._uploaded_hashes)  # type: ignore[attr-defined]

    for transaction_id, invoice_json, audit_trail_json, created_at in rows:
        # Parse invoice JSON
        try:
            invoice_dict = json.loads(invoice_json) if isinstance(invoice_json, str) else invoice_json
            if isinstance(invoice_dict, dict) and "invoice" in invoice_dict and isinstance(invoice_dict["invoice"], dict):
                # Some rows may already be wrapped with 'invoice'
                invoice_payload = invoice_dict["invoice"]
            else:
                invoice_payload = invoice_dict
        except Exception:
            skipped += 1
            continue

        # Compute hash for duplicate detection
        canonical = json.dumps(invoice_payload, sort_keys=True, separators=(",", ":"))
        import hashlib
        inv_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        if dry_run:
            if inv_hash in seen_hashes and skip_duplicates and not force:
                duplicate_skipped += 1
            else:
                uploaded += 1  # would upload
            continue

        if inv_hash in seen_hashes and skip_duplicates and not force:
            duplicate_skipped += 1
            continue

        blob_url = sink.upload_invoice(invoice=invoice_payload, transaction_id=transaction_id, created_at=created_at, force=force)
        if blob_url:
            uploaded += 1
            seen_hashes.add(inv_hash)
        else:
            skipped += 1

        # Upload agent trail if present
        try:
            audit_trail = json.loads(audit_trail_json) if isinstance(audit_trail_json, str) else audit_trail_json
        except Exception:
            audit_trail = []
        if isinstance(audit_trail, list) and audit_trail:
            trail_url = sink.upload_agent_trail(transaction_id=transaction_id, audit_trail=audit_trail)
            if trail_url:
                trail_uploaded += 1

    return {
        "limit": limit,
        "dry_run": dry_run,
        "force": force,
        "skip_duplicates": skip_duplicates,
        "uploaded_invoices": uploaded,
        "skipped_invoices": skipped,
        "duplicate_skipped": duplicate_skipped,
        "agent_trails_uploaded": trail_uploaded,
        "total_rows_considered": len(rows),
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

        # Upload invoice and audit trail to Databricks for historical analysis
        databricks_sink = get_databricks_sink()
        if databricks_sink.enabled:
            # Upload invoice JSON
            databricks_sink.upload_invoice(
                invoice=request.invoice.model_dump(mode="json"),
                transaction_id=result.transaction_id,
            )
            # Upload agent execution trail
            if result.audit_trail:
                databricks_sink.upload_agent_trail(
                    transaction_id=result.transaction_id,
                    audit_trail=result.audit_trail,
                )

        logger.info(f"Transaction {request.invoice.invoice_id} processed: {result.final_decision.value}")
        return result

    except Exception as e:
        logger.error(f"Error processing transaction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing transaction: {str(e)}"
        )


@router.post("/transactions/batch", response_model=BatchTransactionResponse, status_code=status.HTTP_202_ACCEPTED)
def enqueue_transactions(request: BatchTransactionRequest):
    """Queue multiple transactions for asynchronous processing."""
    if not request.transactions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one transaction is required.",
        )

    memory_db = get_orch_cached().memory_db
    payload = [
        {
            "invoice": item.invoice.model_dump(mode="json"),
            "trace_id": item.trace_id,
        }
        for item in request.transactions
    ]
    pending_ids = memory_db.enqueue_pending_transactions(payload)

    if not pending_ids:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to enqueue transactions.",
        )

    return BatchTransactionResponse(accepted=len(pending_ids), pending_ids=pending_ids)


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
        allowed_extensions = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
        file_ext = Path(file.filename).suffix.lower() if file.filename else ""

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}",
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

        # Upload to Databricks for historical analysis
        databricks_sink = get_databricks_sink()
        if databricks_sink.enabled:
            databricks_sink.upload_invoice(
                invoice=invoice.model_dump(mode="json"),
                transaction_id=result.transaction_id,
            )
            if result.audit_trail:
                databricks_sink.upload_agent_trail(
                    transaction_id=result.transaction_id,
                    audit_trail=result.audit_trail,
                )

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
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Could not extract valid invoice data: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing document: {str(e)}"
        )

@router.get("/databricks/embeddings/stats", status_code=status.HTTP_200_OK)
def databricks_embeddings_stats(limit: int = 5):
    """Return Databricks gold embeddings table stats and sample rows.

    Query parameters
    ----------------
    limit : int
        Number of sample rows to return (default 5).
    """
    try:
        stats = get_embeddings_stats(limit=limit)
        return stats
    except DatabricksUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected error fetching embeddings stats", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/databricks/embeddings/search", status_code=status.HTTP_200_OK)
def databricks_embeddings_search(payload: dict):
    """Return top-k similar embeddings for a provided query string.

    Payload example:
    {
      "query": "Consulting invoice for Q4 advisory",
      "k": 5,
      "sample_limit": 300
    }
    """
    query = payload.get("query", "")
    k = int(payload.get("k", 5))
    sample_limit = int(payload.get("sample_limit", 500))
    override_key = payload.get("openai_api_key")
    if not query or not isinstance(query, str):
        raise HTTPException(status_code=400, detail="'query' must be a non-empty string")
    if k <= 0:
        raise HTTPException(status_code=400, detail="'k' must be > 0")
    try:
        results = search_embeddings(
            query=query,
            k=k,
            sample_limit=sample_limit,
            openai_api_key_override=override_key,
        )
        return results
    except DatabricksUnavailable as exc:
        raise HTTPException(status_code=424, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.error("Similarity search failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.post("/transactions/pending/process", response_model=ProcessPendingResponse)
def process_pending_transactions(request: ProcessPendingRequest):
    """Process queued transactions (intended for scheduled jobs)."""
    memory_db = get_orch_cached().memory_db
    total_pending_before = memory_db.count_pending_transactions()

    entries = memory_db.fetch_pending_transactions(
        limit=request.limit,
        mark_processing=not request.dry_run,
    )
    attempted = len(entries)

    if request.dry_run or not entries:
        items = [
            ProcessPendingItem(
                pending_id=entry["pending_id"],
                status="dry_run" if request.dry_run else "skipped",
                invoice_id=_coerce_json(entry.get("invoice_data") or {}).get("invoice_id")
                if isinstance(_coerce_json(entry.get("invoice_data")), dict)
                else None,
            )
            for entry in entries
        ]
        remaining = total_pending_before if request.dry_run else total_pending_before
        return ProcessPendingResponse(
            total_pending_before=total_pending_before,
            remaining_pending=remaining,
            attempted=attempted,
            successes=0,
            failures=0,
            items=items,
        )

    orch = get_orchestrator()
    successes = 0
    failures = 0
    items: list[ProcessPendingItem] = []

    for entry in entries:
        pending_id = entry["pending_id"]
        invoice_payload = entry.get("invoice_data") or "{}"
        trace_id = entry.get("trace_id")

        try:
            invoice_data = json.loads(invoice_payload)
        except json.JSONDecodeError:
            invoice_data = {}

        invoice_id = invoice_data.get("invoice_id") if isinstance(invoice_data, dict) else None

        try:
            invoice = Invoice(**invoice_data)
        except Exception as exc:
            failures += 1
            error_message = f"Invalid invoice payload: {exc}"
            memory_db.update_pending_transaction(
                pending_id,
                status="failed",
                error_message=error_message,
            )
            items.append(
                ProcessPendingItem(
                    pending_id=pending_id,
                    status="failed",
                    error_message=error_message,
                    invoice_id=invoice_id,
                )
            )
            continue

        try:
            result = orch.process_transaction(invoice=invoice, trace_id=trace_id)
            memory_db.update_pending_transaction(
                pending_id,
                status="completed",
                transaction_id=result.transaction_id,
            )
            successes += 1
            items.append(
                ProcessPendingItem(
                    pending_id=pending_id,
                    status="completed",
                    transaction_id=result.transaction_id,
                    decision=result.final_decision,
                    invoice_id=invoice.invoice_id,
                )
            )
        except Exception as exc:
            failures += 1
            error_message = str(exc)
            memory_db.update_pending_transaction(
                pending_id,
                status="failed",
                error_message=error_message,
            )
            items.append(
                ProcessPendingItem(
                    pending_id=pending_id,
                    status="failed",
                    error_message=error_message,
                    invoice_id=invoice.invoice_id,
                )
            )

    remaining = memory_db.count_pending_transactions()

    return ProcessPendingResponse(
        total_pending_before=total_pending_before,
        remaining_pending=remaining,
        attempted=attempted,
        successes=successes,
        failures=failures,
        items=items,
        )


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    """Get transaction details by ID."""
    transaction = get_orch_cached().get_transaction(transaction_id)

    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction {transaction_id} not found")

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
def list_transactions(limit: int = 10, decision_filter: Optional[str] = None):
    """List recent transactions with optional filtering.
    
    Args:
        limit: Maximum number of transactions to return
        decision_filter: Filter by decision type (APPROVED, REJECTED, HITL)
    """
    transactions = get_orch_cached().get_recent_transactions(limit=limit)

    # Apply decision filter if specified
    if decision_filter:
        transactions = [
            t for t in transactions
            if t.get("final_decision") == decision_filter.upper()
        ]

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction {transaction_id} not found")

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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing HITL feedback: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error calculating KPIs: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting KPI trend: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting KPI summary: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting transaction stats: {str(e)}"
        )


@router.get("/transactions/classifications/summary")
def get_classifications_summary():
    """Get summary of all transaction classifications.
    
    Returns counts and percentages for each decision type (APPROVED, REJECTED, HITL).
    """
    import sqlite3
    try:
        memory_db = get_orch_cached().memory_db
        conn = sqlite3.connect(memory_db.db_path)
        cursor = conn.cursor()
        
        # Get decision counts
        cursor.execute("""
            SELECT 
                final_decision,
                COUNT(*) as count,
                AVG(risk_score) as avg_risk_score,
                AVG(processing_time_ms) as avg_processing_time
            FROM transactions
            GROUP BY final_decision
        """)
        
        decision_stats = {}
        total_count = 0
        
        for row in cursor.fetchall():
            decision = row[0]
            count = row[1]
            decision_stats[decision] = {
                "count": count,
                "avg_risk_score": round(row[2], 2) if row[2] else 0,
                "avg_processing_time_ms": round(row[3], 2) if row[3] else 0,
            }
            total_count += count
        
        # Add percentages
        for decision in decision_stats:
            decision_stats[decision]["percentage"] = round(
                (decision_stats[decision]["count"] / total_count * 100), 2
            ) if total_count > 0 else 0
        
        # Get HITL specific stats
        cursor.execute("""
            SELECT COUNT(*) 
            FROM transactions 
            WHERE LOWER(final_decision) = 'hitl' AND human_override = 0
        """)
        pending_hitl = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_transactions": total_count,
            "decision_stats": decision_stats,
            "pending_hitl_count": pending_hitl,
        }
        
    except Exception as e:
        logger.error(f"Error getting classifications summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting classifications summary: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error querying memory: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting memory stats: {str(e)}"
        )


@router.delete("/memory/exceptions/{exception_id}")
def delete_exception(exception_id: str):
    """Soft-delete an exception from adaptive memory."""
    try:
        deleted = get_orch_cached().memory_db.delete_exception(exception_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Exception {exception_id} not found or already deleted"
            )

        logger.info(f"Soft-deleted exception {exception_id}")
        return {"message": f"Exception {exception_id} deleted successfully", "exception_id": exception_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting exception: {str(e)}"
        )


@router.post("/memory/exceptions/{exception_id}/restore")
def restore_exception(exception_id: str):
    """Restore a soft-deleted exception."""
    try:
        restored = get_orch_cached().memory_db.restore_exception(exception_id)

        if not restored:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Exception {exception_id} not found or already active"
            )

        logger.info(f"Restored exception {exception_id}")
        return {"message": f"Exception {exception_id} restored successfully", "exception_id": exception_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error restoring exception: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error querying deleted exceptions: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error getting agent cards: {str(e)}"
        )


# ==================== AUDIT TRAIL ENDPOINTS ====================


@router.post("/audit/upload-memory-snapshot")
def upload_memory_snapshot():
    """Upload current adaptive memory snapshot to Databricks for audit."""
    try:
        databricks_sink = get_databricks_sink()
        if not databricks_sink.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Databricks sink not configured. Set AZURE_STORAGE_CONNECTION_STRING.",
            )

        memory_db = get_orch_cached().memory_db
        query = MemoryQuery()
        exceptions = memory_db.query_exceptions(query)
        
        exceptions_data = [
            {
                "exception_id": exc.exception_id,
                "description": exc.description,
                "vendor": exc.vendor,
                "category": exc.category,
                "condition": exc.condition,
                "rule_type": exc.rule_type,
                "applied_count": exc.applied_count,
                "success_count": exc.success_count,
                "success_rate": exc.success_rate,
                "created_at": exc.created_at.isoformat() if exc.created_at else None,
                "last_applied": exc.last_applied.isoformat() if exc.last_applied else None,
            }
            for exc in exceptions
        ]

        blob_url = databricks_sink.upload_memory_snapshot(exceptions_data)
        
        if not blob_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload memory snapshot",
            )

        return {
            "success": True,
            "blob_url": blob_url,
            "total_exceptions": len(exceptions_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading memory snapshot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading memory snapshot: {str(e)}",
        )


@router.post("/audit/upload-policies")
def upload_policies():
    """Upload all policy documents to Databricks for centralized governance."""
    try:
        databricks_sink = get_databricks_sink()
        if not databricks_sink.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Databricks sink not configured. Set AZURE_STORAGE_CONNECTION_STRING.",
            )

        policies_dir = Path("data/policies")
        if not policies_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policies directory not found",
            )

        uploaded = []
        failed = []

        for policy_file in policies_dir.glob("*.pdf"):
            blob_url = databricks_sink.upload_policy_document(
                policy_path=policy_file,
                metadata={"uploaded_via": "api"},
            )
            if blob_url:
                uploaded.append(policy_file.name)
            else:
                failed.append(policy_file.name)

        return {
            "success": True,
            "uploaded": uploaded,
            "failed": failed,
            "total": len(uploaded) + len(failed),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading policies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading policies: {str(e)}",
        )


@router.post("/audit/upload-kpis")
def upload_kpis():
    """Upload current KPI snapshot to Databricks for historical tracking."""
    try:
        databricks_sink = get_databricks_sink()
        if not databricks_sink.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Databricks sink not configured. Set AZURE_STORAGE_CONNECTION_STRING.",
            )

        kpis = kpi_tracker.get_all_kpis()
        blob_url = databricks_sink.upload_kpi_snapshot(kpis)
        
        if not blob_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload KPI snapshot",
            )

        return {
            "success": True,
            "blob_url": blob_url,
            "kpis": kpis,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading KPI snapshot: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading KPI snapshot: {str(e)}",
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Invoice file {invoice_file} not found")

        with open(invoice_path, "r") as f:
            invoice_data = json.load(f)

        invoice = Invoice(**invoice_data)

        orch = get_orchestrator()
        result = orch.process_transaction(invoice=invoice)

        return result.model_dump()

    except Exception as e:
        logger.error(f"Error processing mock invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing mock invoice: {str(e)}"
        )


@router.get("/demo/list-mock-invoices")
def list_mock_invoices():
    """List available mock invoices."""
    try:
        from pathlib import Path

        invoices_dir = Path("data/mock_invoices")

        if not invoices_dir.exists():
            return {"invoices": []}

        invoice_files = [f.name for f in invoices_dir.glob("INV-*.json")]

        return {"invoices": sorted(invoice_files)}
    except Exception as e:
        logger.error(f"Error listing mock invoices: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error listing mock invoices: {str(e)}"
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching Langfuse insights: {str(e)}"
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
        category = (
            selected_txn.get("invoice", {}).get("category") if isinstance(selected_txn.get("invoice"), dict) else None
        )
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
    memory_section = (
        "\n".join(memory_section_lines) if memory_section_lines else "No learned exceptions matched the query."
    )

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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Assistant chat failed: {exc}")
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
                " | ".join(
                    filter(
                        None, [f"Vendor: {vendor}" if vendor else None, f"Category: {category}" if category else None]
                    )
                )
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
