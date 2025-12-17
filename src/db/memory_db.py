"""SQLite database operations for adaptive memory."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..models.memory_schemas import MemoryQuery, MemoryStats, CRSCalculation
from ..models.schemas import MemoryException, KPIMetrics, TransactionResult


logger = logging.getLogger(__name__)


class MemoryDatabase:
    """SQLite database for adaptive memory and transaction storage."""

    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = db_path
        self._ensure_database()
        self._backfill_missing_descriptions()

    def _ensure_database(self) -> None:
        """Create database and tables if they don't exist."""
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create adaptive_memory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS adaptive_memory (
                exception_id TEXT PRIMARY KEY,
                vendor TEXT,
                category TEXT,
                rule_type TEXT,
                description TEXT,
                condition TEXT,
                applied_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                created_at TIMESTAMP,
                last_applied_at TIMESTAMP,
                deleted_at TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Add deleted_at and is_active columns if they don't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE adaptive_memory ADD COLUMN deleted_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE adaptive_memory ADD COLUMN is_active INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN source_document_path TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                invoice_id TEXT,
                invoice_data TEXT,
                risk_score REAL,
                risk_level TEXT,
                paa_decision TEXT,
                policy_check_json TEXT,
                final_decision TEXT,
                decision_reasoning TEXT,
                human_override INTEGER,
                processing_time_ms INTEGER,
                audit_trail TEXT,
                trace_id TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                source_document_path TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_transactions (
                pending_id TEXT PRIMARY KEY,
                invoice_data TEXT NOT NULL,
                trace_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                transaction_id TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        # Add columns if they don't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN decision_reasoning TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN updated_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # Column already exists

        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN policy_check_json TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pending_status
            ON pending_transactions(status)
        """)

        # Create kpis table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kpis (
                date TEXT PRIMARY KEY,
                total_transactions INTEGER,
                human_corrections INTEGER,
                hcr REAL,
                crs REAL,
                atar REAL,
                avg_processing_time_ms INTEGER,
                audit_traceability_score REAL
            )
        """)

        # Create indices for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_vendor 
            ON adaptive_memory(vendor)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_category 
            ON adaptive_memory(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_date 
            ON transactions(created_at)
        """)

        conn.commit()
        conn.close()
        logger.info(f"Memory database initialized at {self.db_path}")

    def _normalize_description(
        self,
        description: Optional[str],
        vendor: Optional[str],
        condition: Optional[Dict[str, Any]],
        rule_type: Optional[str],
    ) -> str:
        """Ensure descriptions are human-readable instead of placeholders like 'N/A'."""
        text = (description or "").strip()
        if text.lower() in {"", "n/a", "na", "none"}:
            reason = None
            if isinstance(condition, dict):
                reason = condition.get("reason")
            if isinstance(reason, str) and reason.strip():
                text = reason.strip()
            elif vendor:
                rule_label = (rule_type or "Learned exception").replace("_", " ").title()
                text = f"{rule_label} – Vendor {vendor}"
            elif rule_type:
                text = (rule_type or "Learned exception").replace("_", " ").title()
            else:
                text = "Learned exception"
        return text

    def _backfill_missing_descriptions(self) -> None:
        """Update existing rows that still have placeholder descriptions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT exception_id, vendor, rule_type, description, condition
            FROM adaptive_memory
            WHERE description IS NULL
               OR TRIM(description) = ''
               OR LOWER(description) IN ('n/a', 'na', 'none')
        """
        )
        rows = cursor.fetchall()
        updated = 0
        for exception_id, vendor, rule_type, description, condition_json in rows:
            try:
                condition = json.loads(condition_json or "{}")
            except json.JSONDecodeError:
                condition = {}
            normalized = self._normalize_description(description, vendor, condition, rule_type)
            cursor.execute(
                "UPDATE adaptive_memory SET description = ? WHERE exception_id = ?",
                (normalized, exception_id),
            )
            updated += 1
        if updated:
            conn.commit()
            logger.info(f"Backfilled descriptions for {updated} adaptive memory rule(s)")
        conn.close()

    # ========== ADAPTIVE MEMORY OPERATIONS ==========

    def add_exception(
        self,
        vendor: Optional[str],
        category: Optional[str],
        rule_type: str,
        description: str,
        condition: Dict[str, Any],
    ) -> str:
        """Add a new exception to adaptive memory."""
        exception_id = str(uuid.uuid4())[:8]
        normalized_description = self._normalize_description(description, vendor, condition, rule_type)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO adaptive_memory 
            (exception_id, vendor, category, rule_type, description, condition, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (exception_id, vendor, category, rule_type, normalized_description, json.dumps(condition), datetime.now()),
        )

        conn.commit()
        conn.close()

        logger.info(f"Added exception {exception_id}: {normalized_description}")
        return exception_id

    def delete_exception(self, exception_id: str) -> bool:
        """Soft-delete an exception from adaptive memory (mark as inactive).

        Returns:
            True if exception was deleted, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE adaptive_memory 
            SET is_active = 0, deleted_at = ?
            WHERE exception_id = ? AND is_active = 1
        """,
            (datetime.now(), exception_id),
        )
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        if deleted:
            logger.info(f"Soft-deleted exception {exception_id}")
        else:
            logger.warning(f"Exception {exception_id} not found or already deleted")

        return deleted

    def restore_exception(self, exception_id: str) -> bool:
        """Restore a soft-deleted exception.

        Returns:
            True if exception was restored, False if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE adaptive_memory 
            SET is_active = 1, deleted_at = NULL
            WHERE exception_id = ? AND is_active = 0
        """,
            (exception_id,),
        )
        restored = cursor.rowcount > 0

        conn.commit()
        conn.close()

        if restored:
            logger.info(f"Restored exception {exception_id}")
        else:
            logger.warning(f"Exception {exception_id} not found or already active")

        return restored

    def query_exceptions(self, query: MemoryQuery) -> List[MemoryException]:
        """Query exceptions from adaptive memory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build dynamic query - only show active exceptions by default
        where_clauses = ["is_active = 1"]
        params = []

        if query.vendor:
            where_clauses.append("vendor = ?")
            params.append(query.vendor)

        if query.category:
            where_clauses.append("category = ?")
            params.append(query.category)

        if query.rule_type:
            where_clauses.append("rule_type = ?")
            params.append(query.rule_type)

        if query.min_success_rate:
            where_clauses.append("success_rate >= ?")
            params.append(query.min_success_rate)

        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

        cursor.execute(
            f"""
            SELECT * FROM adaptive_memory
            WHERE {where_clause}
            ORDER BY applied_count DESC, created_at DESC
        """,
            params,
        )

        rows = cursor.fetchall()
        conn.close()

        exceptions = []
        for row in rows:
            condition = json.loads(row["condition"]) if row["condition"] else {}
            exceptions.append(
                MemoryException(
                    exception_id=row["exception_id"],
                    vendor=row["vendor"],
                    category=row["category"],
                    rule_type=row["rule_type"],
                    description=self._normalize_description(
                        row["description"], row["vendor"], condition, row["rule_type"]
                    ),
                    condition=condition,
                    applied_count=row["applied_count"],
                    success_rate=row["success_rate"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_applied_at=datetime.fromisoformat(row["last_applied_at"]) if row["last_applied_at"] else None,
                )
            )

        return exceptions

    def update_exception_usage(self, exception_id: str, success: bool = True) -> None:
        """Update exception usage statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current stats
        cursor.execute(
            """
            SELECT applied_count, success_rate FROM adaptive_memory
            WHERE exception_id = ?
        """,
            (exception_id,),
        )

        row = cursor.fetchone()
        if not row:
            logger.warning(f"Exception {exception_id} not found")
            conn.close()
            return

        applied_count, success_rate = row
        new_applied_count = applied_count + 1

        # Calculate new success rate using moving average
        new_success_rate = ((success_rate * applied_count) + (1.0 if success else 0.0)) / new_applied_count

        cursor.execute(
            """
            UPDATE adaptive_memory
            SET applied_count = ?,
                success_rate = ?,
                last_applied_at = ?
            WHERE exception_id = ?
        """,
            (new_applied_count, new_success_rate, datetime.now(), exception_id),
        )

        conn.commit()
        conn.close()

        logger.info(
            f"Updated exception {exception_id}: applied={new_applied_count}, success_rate={new_success_rate:.2f}"
        )

    def get_memory_stats(self) -> MemoryStats:
        """Get statistics about adaptive memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total and active exceptions (only count active ones)
        cursor.execute("SELECT COUNT(*) FROM adaptive_memory WHERE is_active = 1")
        total_exceptions = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM adaptive_memory WHERE applied_count > 0 AND is_active = 1")
        active_exceptions = cursor.fetchone()[0] or 0

        # Total applications - ensure we get a number, not None (only active)
        cursor.execute("SELECT COALESCE(SUM(applied_count), 0) FROM adaptive_memory WHERE is_active = 1")
        total_applications = cursor.fetchone()[0] or 0

        # Average success rate (only active)
        cursor.execute("SELECT AVG(success_rate) FROM adaptive_memory WHERE applied_count > 0 AND is_active = 1")
        avg_success_rate = cursor.fetchone()[0] or 0.0

        # Most applied rules (only active)
        cursor.execute(
            """
            SELECT exception_id, description, applied_count, success_rate
            FROM adaptive_memory
            WHERE applied_count > 0 AND is_active = 1
            ORDER BY applied_count DESC, created_at DESC
            LIMIT 5
        """
        )
        most_applied = []
        for row in cursor.fetchall():
            cursor.execute(
                "SELECT vendor, rule_type, condition FROM adaptive_memory WHERE exception_id = ?",
                (row[0],),
            )
            vendor_row = cursor.fetchone()
            if vendor_row:
                vendor, rule_type, condition_json = vendor_row
            else:
                vendor = rule_type = None
                condition_json = "{}"
            try:
                condition = json.loads(condition_json or "{}")
            except json.JSONDecodeError:
                condition = {}
            most_applied.append(
                {
                    "exception_id": row[0],
                    "description": self._normalize_description(row[1], vendor, condition, rule_type),
                    "applied_count": row[2],
                    "success_rate": row[3],
                }
            )

        # Recent additions (only active)
        cursor.execute(
            """
            SELECT exception_id, description, created_at, vendor, rule_type, condition
            FROM adaptive_memory
            WHERE is_active = 1
            ORDER BY created_at DESC
            LIMIT 5
        """
        )
        recent_additions = []
        for row in cursor.fetchall():
            try:
                condition = json.loads(row[5] or "{}")
            except json.JSONDecodeError:
                condition = {}
            recent_additions.append(
                {
                    "exception_id": row[0],
                    "description": self._normalize_description(row[1], row[3], condition, row[4]),
                    "created_at": row[2],
                }
            )

        conn.close()

        return MemoryStats(
            total_exceptions=total_exceptions,
            active_exceptions=active_exceptions,
            total_applications=total_applications,
            avg_success_rate=avg_success_rate,
            most_applied_rules=most_applied,
            recent_additions=recent_additions,
        )

    # ========== TRANSACTION OPERATIONS ==========

    def enqueue_pending_transactions(self, items: list[Dict[str, Any]]) -> list[str]:
        """Add invoices to the pending queue for later batch processing."""
        if not items:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now()
        pending_ids: list[str] = []

        for item in items:
            invoice_payload = item.get("invoice")
            trace_id = item.get("trace_id")
            if not invoice_payload:
                continue

            pending_id = str(uuid.uuid4())[:12]
            cursor.execute(
                """
                INSERT INTO pending_transactions (
                    pending_id,
                    invoice_data,
                    trace_id,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (pending_id, json.dumps(invoice_payload), trace_id, now, now),
            )
            pending_ids.append(pending_id)

        conn.commit()
        conn.close()

        if pending_ids:
            logger.info("Enqueued %s pending transaction(s)", len(pending_ids))
        return pending_ids

    def fetch_pending_transactions(self, limit: int = 25, mark_processing: bool = True) -> list[Dict[str, Any]]:
        """Fetch pending transactions and optionally mark them as processing."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pending_id, invoice_data, trace_id
            FROM pending_transactions
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        pending_ids = [row["pending_id"] for row in rows]

        if pending_ids and mark_processing:
            now = datetime.now()
            cursor.executemany(
                """
                UPDATE pending_transactions
                SET status = 'processing', updated_at = ?
                WHERE pending_id = ?
                """,
                [(now, pending_id) for pending_id in pending_ids],
            )
            conn.commit()

        conn.close()

        pending: list[Dict[str, Any]] = []
        for row in rows:
            pending.append(
                {
                    "pending_id": row["pending_id"],
                    "invoice_data": row["invoice_data"],
                    "trace_id": row["trace_id"],
                }
            )
        return pending

    def update_pending_transaction(
        self,
        pending_id: str,
        *,
        status: str,
        transaction_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the final status of a pending transaction."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE pending_transactions
            SET status = ?,
                transaction_id = ?,
                error_message = ?,
                updated_at = ?
            WHERE pending_id = ?
            """,
            (status, transaction_id, error_message, datetime.now(), pending_id),
        )
        conn.commit()
        conn.close()

    def count_pending_transactions(self) -> int:
        """Return the number of transactions still pending execution."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM pending_transactions WHERE status = 'pending'")
        result = cursor.fetchone()
        conn.close()
        return (result[0] or 0) if result else 0

    def save_transaction(self, result: TransactionResult) -> None:
        """Save transaction result to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO transactions
            (transaction_id, invoice_id, invoice_data, risk_score, risk_level, 
             paa_decision, policy_check_json, final_decision, decision_reasoning, human_override, processing_time_ms, 
             audit_trail, trace_id, created_at, updated_at, source_document_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                result.transaction_id,
                result.invoice.invoice_id,
                result.invoice.model_dump_json(),
                result.risk_assessment.risk_score,
                result.risk_assessment.risk_level.value,
                "compliant" if result.policy_check.is_compliant else "non_compliant",
                result.policy_check.model_dump_json(),
                result.final_decision.value,
                result.decision_reasoning,
                1 if result.human_override else 0,
                result.processing_time_ms,
                json.dumps(result.audit_trail),
                result.trace_id,
                result.created_at,
                result.created_at,  # updated_at initially same as created_at
                result.source_document_path,
            ),
        )

        conn.commit()
        conn.close()

        logger.info(f"Saved transaction {result.transaction_id}")

    def update_transaction_source(self, transaction_id: str, path: str) -> None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE transactions SET source_document_path = ?, updated_at = ? WHERE transaction_id = ?""",
            (path, datetime.now(), transaction_id),
        )
        conn.commit()
        conn.close()

        logger.info(f"Updated source document for transaction {transaction_id}")

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        transaction = dict(row)
        if "invoice_data" in transaction:
            transaction["invoice"] = json.loads(transaction["invoice_data"])
        if "audit_trail" in transaction:
            transaction["audit_trail"] = json.loads(transaction["audit_trail"])
        if transaction.get("policy_check_json"):
            transaction["policy_check"] = json.loads(transaction["policy_check_json"])
            del transaction["policy_check_json"]

        return transaction

    def get_recent_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM transactions
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        transactions = []
        for row in rows:
            trans = dict(row)
            if "invoice_data" in trans:
                trans["invoice"] = json.loads(trans["invoice_data"])
            if "audit_trail" in trans:
                trans["audit_trail"] = json.loads(trans["audit_trail"])
            if trans.get("policy_check_json"):
                trans["policy_check"] = json.loads(trans["policy_check_json"])
                del trans["policy_check_json"]

            transactions.append(trans)
        return transactions

    def update_transaction_after_hitl(self, transaction_id: str, human_decision: str, final_reasoning: str) -> None:
        """Update transaction record after HITL feedback."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Use datetime.now() to ensure same timezone as created_at
        cursor.execute(
            """
            UPDATE transactions
            SET human_override = 1,
                final_decision = ?,
                decision_reasoning = ?,
                updated_at = ?
            WHERE transaction_id = ?
        """,
            (human_decision, final_reasoning, datetime.now(), transaction_id),
        )

        conn.commit()
        conn.close()

        logger.info(f"Updated transaction {transaction_id} with HITL feedback")

    # ========== KPI OPERATIONS ==========

    def calculate_and_save_kpis(self, date: Optional[str] = None) -> KPIMetrics:
        """Calculate KPIs for a specific date and save to database.

        If no transactions exist for the date, calculates across ALL transactions
        to provide meaningful metrics.
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get transactions for the date
        cursor.execute(
            """
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN human_override = 1 THEN 1 ELSE 0 END) as human_corrections,
                   SUM(CASE WHEN final_decision = 'approved' AND human_override = 0 THEN 1 ELSE 0 END) as auto_approved,
                   AVG(processing_time_ms) as avg_time,
                   SUM(CASE WHEN audit_trail IS NOT NULL AND audit_trail != '[]' THEN 1 ELSE 0 END) as with_audit
            FROM transactions
            WHERE DATE(created_at) = ?
        """,
            (date,),
        )

        row = cursor.fetchone()
        total_transactions = row[0] or 0
        human_corrections = row[1] or 0
        auto_approved = row[2] or 0
        avg_time = int(row[3]) if row[3] else 0
        with_audit = row[4] or 0

        # If no transactions for this date, calculate across ALL transactions
        if total_transactions == 0:
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN human_override = 1 THEN 1 ELSE 0 END) as human_corrections,
                       SUM(CASE WHEN final_decision = 'approved' AND human_override = 0 THEN 1 ELSE 0 END) as auto_approved,
                       AVG(processing_time_ms) as avg_time,
                       SUM(CASE WHEN audit_trail IS NOT NULL AND audit_trail != '[]' THEN 1 ELSE 0 END) as with_audit
                FROM transactions
            """)
            row = cursor.fetchone()
            total_transactions = row[0] or 0
            human_corrections = row[1] or 0
            auto_approved = row[2] or 0
            avg_time = int(row[3]) if row[3] else 0
            with_audit = row[4] or 0

        # Calculate KPIs
        hcr = (human_corrections / total_transactions * 100) if total_transactions > 0 else 0
        atar = (auto_approved / total_transactions * 100) if total_transactions > 0 else 0
        audit_traceability = (with_audit / total_transactions * 100) if total_transactions > 0 else 0

        # Calculate CRS (Context Retention Score) - use all time if no date-specific data
        crs_calc = self.calculate_crs(date if total_transactions > 0 else None)
        crs = crs_calc.crs_score

        # Save KPIs
        cursor.execute(
            """
            INSERT OR REPLACE INTO kpis
            (date, total_transactions, human_corrections, hcr, crs, atar, 
             avg_processing_time_ms, audit_traceability_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (date, total_transactions, human_corrections, hcr, crs, atar, avg_time, audit_traceability),
        )

        conn.commit()
        conn.close()

        kpi_metrics = KPIMetrics(
            date=date,
            total_transactions=total_transactions,
            human_corrections=human_corrections,
            hcr=hcr,
            crs=crs,
            atar=atar,
            avg_processing_time_ms=avg_time,
            audit_traceability_score=audit_traceability,
        )

        logger.info(f"Calculated KPIs for {date}: H-CR={hcr:.1f}%, CRS={crs:.1f}%, ATAR={atar:.1f}%")
        return kpi_metrics

    def calculate_crs(self, date: Optional[str] = None) -> CRSCalculation:
        """Calculate Context Retention Score.

        If date is None, calculates across ALL exceptions (all-time).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if date:
            # Get exceptions applied on this date
            cursor.execute(
                """
                SELECT COUNT(*) FROM adaptive_memory
                WHERE DATE(last_applied_at) = ? AND applied_count > 0
            """,
                (date,),
            )

            applications_today = cursor.fetchone()[0] or 0

            # Get successful applications (where success_rate > 0.5)
            cursor.execute(
                """
                SELECT SUM(applied_count * success_rate) / SUM(applied_count)
                FROM adaptive_memory
                WHERE DATE(last_applied_at) = ? AND applied_count > 0
            """,
                (date,),
            )

            avg_success = cursor.fetchone()[0] or 0.0
        else:
            # Calculate across ALL exceptions (all-time)
            cursor.execute("""
                SELECT COUNT(*) FROM adaptive_memory
                WHERE applied_count > 0
            """)

            applications_today = cursor.fetchone()[0] or 0

            # Get successful applications (weighted by applied_count)
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN SUM(applied_count) > 0 
                        THEN SUM(applied_count * success_rate) / SUM(applied_count)
                        ELSE 0.0
                    END
                FROM adaptive_memory
                WHERE applied_count > 0
            """)

            avg_success = cursor.fetchone()[0] or 0.0

        conn.close()

        # CRS is the percentage of successful memory applications
        crs_score = avg_success * 100 if applications_today > 0 else 0.0

        return CRSCalculation(
            applicable_scenarios=applications_today,
            successful_applications=int(applications_today * avg_success) if applications_today > 0 else 0,
            crs_score=crs_score,
            details=f"Applied memory {applications_today} times with {crs_score:.1f}% success rate",
        )

    def get_kpis(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[KPIMetrics]:
        """Get KPI metrics for a date range."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if start_date and end_date:
            cursor.execute(
                """
                SELECT * FROM kpis
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            """,
                (start_date, end_date),
            )
        elif start_date:
            cursor.execute(
                """
                SELECT * FROM kpis
                WHERE date >= ?
                ORDER BY date DESC
            """,
                (start_date,),
            )
        else:
            cursor.execute("""
                SELECT * FROM kpis
                ORDER BY date DESC
                LIMIT 30
            """)

        rows = cursor.fetchall()
        conn.close()

        return [KPIMetrics(**dict(row)) for row in rows]

    def get_latest_kpis(self) -> Optional[KPIMetrics]:
        """Get the most recent KPI metrics."""
        kpis = self.get_kpis()
        return kpis[0] if kpis else None
