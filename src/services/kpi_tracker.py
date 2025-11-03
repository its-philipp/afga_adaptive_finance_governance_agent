"""KPI tracking service for AFGA.

Calculates and tracks key performance indicators:
- H-CR (Human Correction Rate)
- CRS (Context Retention Score)
- ATAR (Automated Transaction Approval Rate)
- Audit Traceability Score
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ..db.memory_db import MemoryDatabase
from ..models.schemas import KPIMetrics


logger = logging.getLogger(__name__)


class KPITracker:
    """Tracks and calculates KPIs for AFGA system."""

    def __init__(self, memory_db: Optional[MemoryDatabase] = None):
        self.db = memory_db or MemoryDatabase()
        logger.info("KPI Tracker initialized")

    def calculate_current_kpis(self, date: Optional[str] = None) -> KPIMetrics:
        """Calculate KPIs for a specific date (defaults to today).
        
        Args:
            date: Date string in YYYY-MM-DD format
            
        Returns:
            KPIMetrics with all calculated values
        """
        return self.db.calculate_and_save_kpis(date)

    def get_kpi_trend(self, days: int = 30) -> List[KPIMetrics]:
        """Get KPI trend over the last N days.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of KPIMetrics, most recent first
        """
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        return self.db.get_kpis(start_date, end_date)

    def get_latest_kpis(self) -> Optional[KPIMetrics]:
        """Get the most recent KPI metrics."""
        return self.db.get_latest_kpis()

    def get_hcr_trend(self, days: int = 30) -> List[Dict[str, any]]:
        """Get H-CR (Human Correction Rate) trend.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of date/H-CR pairs
        """
        kpis = self.get_kpi_trend(days)
        return [{"date": kpi.date, "hcr": kpi.hcr} for kpi in kpis]

    def get_crs_trend(self, days: int = 30) -> List[Dict[str, any]]:
        """Get CRS (Context Retention Score) trend.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of date/CRS pairs
        """
        kpis = self.get_kpi_trend(days)
        return [{"date": kpi.date, "crs": kpi.crs} for kpi in kpis]

    def get_atar_trend(self, days: int = 30) -> List[Dict[str, any]]:
        """Get ATAR (Automated Transaction Approval Rate) trend.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of date/ATAR pairs
        """
        kpis = self.get_kpi_trend(days)
        return [{"date": kpi.date, "atar": kpi.atar} for kpi in kpis]

    def get_kpi_summary(self) -> Dict[str, any]:
        """Get a comprehensive KPI summary.
        
        Returns:
            Dictionary with current KPIs and trends
        """
        latest = self.get_latest_kpis()
        trend_7d = self.get_kpi_trend(7)
        trend_30d = self.get_kpi_trend(30)
        
        if not latest:
            return {
                "current": None,
                "message": "No KPI data available yet"
            }
        
        # Calculate trend direction (improving or declining)
        hcr_improving = self._is_improving_trend([kpi.hcr for kpi in trend_7d], lower_is_better=True)
        crs_improving = self._is_improving_trend([kpi.crs for kpi in trend_7d], lower_is_better=False)
        atar_improving = self._is_improving_trend([kpi.atar for kpi in trend_7d], lower_is_better=False)
        
        return {
            "current": {
                "date": latest.date,
                "hcr": latest.hcr,
                "crs": latest.crs,
                "atar": latest.atar,
                "total_transactions": latest.total_transactions,
                "human_corrections": latest.human_corrections,
                "avg_processing_time_ms": latest.avg_processing_time_ms,
                "audit_traceability_score": latest.audit_traceability_score,
            },
            "trends": {
                "hcr": {
                    "7_day": [{"date": kpi.date, "value": kpi.hcr} for kpi in trend_7d],
                    "30_day_avg": sum(kpi.hcr for kpi in trend_30d) / len(trend_30d) if trend_30d else 0,
                    "improving": hcr_improving,
                },
                "crs": {
                    "7_day": [{"date": kpi.date, "value": kpi.crs} for kpi in trend_7d],
                    "30_day_avg": sum(kpi.crs for kpi in trend_30d) / len(trend_30d) if trend_30d else 0,
                    "improving": crs_improving,
                },
                "atar": {
                    "7_day": [{"date": kpi.date, "value": kpi.atar} for kpi in trend_7d],
                    "30_day_avg": sum(kpi.atar for kpi in trend_30d) / len(trend_30d) if trend_30d else 0,
                    "improving": atar_improving,
                },
            },
            "learning_metrics": {
                "hcr_reducing": hcr_improving,
                "crs_increasing": crs_improving,
                "system_learning": hcr_improving and crs_improving,
            }
        }

    def _is_improving_trend(self, values: List[float], lower_is_better: bool = True) -> bool:
        """Determine if a trend is improving.
        
        Args:
            values: List of KPI values (chronological order)
            lower_is_better: True if lower values indicate improvement
            
        Returns:
            True if trend is improving
        """
        if len(values) < 2:
            return False
        
        # Simple trend: compare first half to second half
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(values[mid:]) / (len(values) - mid) if len(values) > mid else 0
        
        if lower_is_better:
            return second_half_avg < first_half_avg
        else:
            return second_half_avg > first_half_avg

    def get_transaction_stats(self) -> Dict[str, any]:
        """Get transaction statistics."""
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Total transactions
        cursor.execute("SELECT COUNT(*) FROM transactions")
        total = cursor.fetchone()[0]
        
        # By decision type
        cursor.execute("""
            SELECT final_decision, COUNT(*) 
            FROM transactions 
            GROUP BY final_decision
        """)
        by_decision = dict(cursor.fetchall())
        
        # By risk level
        cursor.execute("""
            SELECT risk_level, COUNT(*) 
            FROM transactions 
            GROUP BY risk_level
        """)
        by_risk = dict(cursor.fetchall())
        
        # Average processing time
        cursor.execute("SELECT AVG(processing_time_ms) FROM transactions")
        avg_time = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_transactions": total,
            "by_decision": by_decision,
            "by_risk_level": by_risk,
            "avg_processing_time_ms": int(avg_time),
        }

    def force_recalculate_all_kpis(self) -> Dict[str, any]:
        """Recalculate KPIs for all dates with transactions.
        
        Useful for backfilling after system changes.
        
        Returns:
            Summary of recalculation
        """
        import sqlite3
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Get all unique dates
        cursor.execute("""
            SELECT DISTINCT DATE(created_at) as date 
            FROM transactions 
            ORDER BY date
        """)
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        recalculated = []
        for date in dates:
            kpi = self.db.calculate_and_save_kpis(date)
            recalculated.append({
                "date": date,
                "hcr": kpi.hcr,
                "crs": kpi.crs,
                "atar": kpi.atar,
            })
        
        logger.info(f"Recalculated KPIs for {len(dates)} dates")
        
        return {
            "recalculated_dates": len(dates),
            "kpis": recalculated,
        }

