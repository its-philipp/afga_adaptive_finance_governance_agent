"""SQLite database operations for adaptive memory."""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..models.memory_schemas import MemoryQuery, MemoryStats, CRSCalculation
from ..models.schemas import MemoryException, KPIMetrics, TransactionResult


logger = logging.getLogger(__name__)


class MemoryDatabase:
    """SQLite database for adaptive memory and transaction storage."""

    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = db_path
        self._ensure_database()

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
                last_applied_at TIMESTAMP
            )
        """)

        # Create transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                invoice_id TEXT,
                invoice_data TEXT,
                risk_score REAL,
                risk_level TEXT,
                paa_decision TEXT,
                final_decision TEXT,
                human_override INTEGER,
                processing_time_ms INTEGER,
                audit_trail TEXT,
                trace_id TEXT,
                created_at TIMESTAMP
            )
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
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO adaptive_memory 
            (exception_id, vendor, category, rule_type, description, condition, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (exception_id, vendor, category, rule_type, description, json.dumps(condition), datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added exception {exception_id}: {description}")
        return exception_id

    def query_exceptions(self, query: MemoryQuery) -> List[MemoryException]:
        """Query exceptions from adaptive memory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build dynamic query
        where_clauses = []
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
        
        cursor.execute(f"""
            SELECT * FROM adaptive_memory
            WHERE {where_clause}
            ORDER BY applied_count DESC, created_at DESC
        """, params)

        rows = cursor.fetchall()
        conn.close()

        exceptions = []
        for row in rows:
            exceptions.append(MemoryException(
                exception_id=row["exception_id"],
                vendor=row["vendor"],
                category=row["category"],
                rule_type=row["rule_type"],
                description=row["description"],
                condition=json.loads(row["condition"]),
                applied_count=row["applied_count"],
                success_rate=row["success_rate"],
                created_at=datetime.fromisoformat(row["created_at"]),
                last_applied_at=datetime.fromisoformat(row["last_applied_at"]) if row["last_applied_at"] else None,
            ))

        return exceptions

    def update_exception_usage(self, exception_id: str, success: bool = True) -> None:
        """Update exception usage statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get current stats
        cursor.execute("""
            SELECT applied_count, success_rate FROM adaptive_memory
            WHERE exception_id = ?
        """, (exception_id,))
        
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Exception {exception_id} not found")
            conn.close()
            return

        applied_count, success_rate = row
        new_applied_count = applied_count + 1
        
        # Calculate new success rate using moving average
        new_success_rate = ((success_rate * applied_count) + (1.0 if success else 0.0)) / new_applied_count

        cursor.execute("""
            UPDATE adaptive_memory
            SET applied_count = ?,
                success_rate = ?,
                last_applied_at = ?
            WHERE exception_id = ?
        """, (new_applied_count, new_success_rate, datetime.now(), exception_id))

        conn.commit()
        conn.close()
        
        logger.info(f"Updated exception {exception_id}: applied={new_applied_count}, success_rate={new_success_rate:.2f}")

    def get_memory_stats(self) -> MemoryStats:
        """Get statistics about adaptive memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total and active exceptions
        cursor.execute("SELECT COUNT(*) FROM adaptive_memory")
        total_exceptions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM adaptive_memory WHERE applied_count > 0")
        active_exceptions = cursor.fetchone()[0]

        # Total applications
        cursor.execute("SELECT SUM(applied_count) FROM adaptive_memory")
        total_applications = cursor.fetchone()[0] or 0

        # Average success rate
        cursor.execute("SELECT AVG(success_rate) FROM adaptive_memory WHERE applied_count > 0")
        avg_success_rate = cursor.fetchone()[0] or 0.0

        # Most applied rules
        cursor.execute("""
            SELECT exception_id, description, applied_count, success_rate
            FROM adaptive_memory
            WHERE applied_count > 0
            ORDER BY applied_count DESC
            LIMIT 5
        """)
        most_applied = [
            {
                "exception_id": row[0],
                "description": row[1],
                "applied_count": row[2],
                "success_rate": row[3],
            }
            for row in cursor.fetchall()
        ]

        # Recent additions
        cursor.execute("""
            SELECT exception_id, description, created_at
            FROM adaptive_memory
            ORDER BY created_at DESC
            LIMIT 5
        """)
        recent_additions = [
            {"exception_id": row[0], "description": row[1], "created_at": row[2]}
            for row in cursor.fetchall()
        ]

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

    def save_transaction(self, result: TransactionResult) -> None:
        """Save transaction result to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transactions
            (transaction_id, invoice_id, invoice_data, risk_score, risk_level, 
             paa_decision, final_decision, human_override, processing_time_ms, 
             audit_trail, trace_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.transaction_id,
            result.invoice.invoice_id,
            result.invoice.model_dump_json(),
            result.risk_assessment.risk_score,
            result.risk_assessment.risk_level.value,
            "compliant" if result.policy_check.is_compliant else "non_compliant",
            result.final_decision.value,
            1 if result.human_override else 0,
            result.processing_time_ms,
            json.dumps(result.audit_trail),
            result.trace_id,
            result.created_at,
        ))

        conn.commit()
        conn.close()
        
        logger.info(f"Saved transaction {result.transaction_id}")

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

        return dict(row)

    def get_recent_transactions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent transactions."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM transactions
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========== KPI OPERATIONS ==========

    def calculate_and_save_kpis(self, date: Optional[str] = None) -> KPIMetrics:
        """Calculate KPIs for a specific date and save to database."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get transactions for the date
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN human_override = 1 THEN 1 ELSE 0 END) as human_corrections,
                   SUM(CASE WHEN final_decision = 'approved' AND human_override = 0 THEN 1 ELSE 0 END) as auto_approved,
                   AVG(processing_time_ms) as avg_time,
                   SUM(CASE WHEN audit_trail IS NOT NULL AND audit_trail != '[]' THEN 1 ELSE 0 END) as with_audit
            FROM transactions
            WHERE DATE(created_at) = ?
        """, (date,))

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

        # Calculate CRS (Context Retention Score)
        crs_calc = self.calculate_crs(date)
        crs = crs_calc.crs_score

        # Save KPIs
        cursor.execute("""
            INSERT OR REPLACE INTO kpis
            (date, total_transactions, human_corrections, hcr, crs, atar, 
             avg_processing_time_ms, audit_traceability_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date, total_transactions, human_corrections, hcr, crs, atar, avg_time, audit_traceability))

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
        """Calculate Context Retention Score."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get exceptions applied on this date
        cursor.execute("""
            SELECT COUNT(*) FROM adaptive_memory
            WHERE DATE(last_applied_at) = ?
        """, (date,))
        
        applications_today = cursor.fetchone()[0] or 0

        # Get successful applications (where success_rate > 0.5)
        cursor.execute("""
            SELECT SUM(applied_count * success_rate) / SUM(applied_count)
            FROM adaptive_memory
            WHERE DATE(last_applied_at) = ? AND applied_count > 0
        """, (date,))
        
        avg_success = cursor.fetchone()[0] or 0.0

        conn.close()

        # CRS is the percentage of successful memory applications
        crs_score = avg_success * 100 if applications_today > 0 else 0.0

        return CRSCalculation(
            applicable_scenarios=applications_today,
            successful_applications=int(applications_today * avg_success),
            crs_score=crs_score,
            details=f"Applied memory {applications_today} times with {crs_score:.1f}% success rate"
        )

    def get_kpis(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[KPIMetrics]:
        """Get KPI metrics for a date range."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM kpis
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (start_date, end_date))
        elif start_date:
            cursor.execute("""
                SELECT * FROM kpis
                WHERE date >= ?
                ORDER BY date DESC
            """, (start_date,))
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

