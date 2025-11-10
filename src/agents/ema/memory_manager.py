"""Memory manager for EMA - handles adaptive memory operations."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Any

from ...core.config import get_settings
from ...db.memory_db import MemoryDatabase
from ...models.memory_schemas import MemoryQuery
from ...models.schemas import MemoryException, Invoice


logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages adaptive memory operations for the EMA."""

    def __init__(self):
        settings = get_settings()
        self.db = MemoryDatabase(db_path=settings.memory_db_path)
        logger.info("Memory manager initialized")

    def add_learned_exception(
        self,
        invoice: Invoice,
        exception_type: str,
        description: str,
        reason: str,
    ) -> str:
        """Add a new learned exception to adaptive memory."""
        vendor_value = invoice.vendor or None
        category_value = invoice.category or None

        condition = {
            "vendor": vendor_value,
            "category": category_value,
            "amount_threshold": invoice.amount if "threshold" in (description or "").lower() else None,
            "international": invoice.international if invoice.international else None,
            "reason": reason,
        }

        condition = {k: v for k, v in condition.items() if v is not None}

        normalized_description = self.db._normalize_description(description, vendor_value, condition, exception_type)

        exception_id = self.db.add_exception(
            vendor=vendor_value,
            category=category_value,
            rule_type=exception_type,
            description=normalized_description,
            condition=condition,
        )

        logger.info(f"Added learned exception {exception_id}: {normalized_description}")
        return exception_id

    def query_applicable_exceptions(self, invoice: Invoice) -> list[MemoryException]:
        """Query exceptions that might apply to this invoice.
        
        Args:
            invoice: Invoice to check against memory
            
        Returns:
            List of applicable exceptions
        """
        # Query by vendor
        vendor_exceptions = self.db.query_exceptions(
            MemoryQuery(vendor=invoice.vendor, min_success_rate=0.5)
        )

        # Query by category
        category_exceptions = self.db.query_exceptions(
            MemoryQuery(category=invoice.category, min_success_rate=0.5)
        )

        # Combine and deduplicate
        all_exceptions = {exc.exception_id: exc for exc in vendor_exceptions + category_exceptions}

        # Filter by additional conditions
        applicable = []
        for exc in all_exceptions.values():
            if self._matches_condition(invoice, exc.condition):
                applicable.append(exc)

        logger.info(f"Found {len(applicable)} applicable exceptions for invoice {invoice.invoice_id}")
        return applicable

    def _matches_condition(self, invoice: Invoice, condition: Dict[str, Any]) -> bool:
        """Check if an invoice matches the exception condition."""
        # Check amount threshold if present
        if "amount_threshold" in condition:
            threshold = condition["amount_threshold"]
            # Allow some tolerance (10%)
            if invoice.amount < threshold * 0.9 or invoice.amount > threshold * 1.1:
                return False

        # Check international flag
        if "international" in condition:
            if invoice.international != condition["international"]:
                return False

        # If we get here, it matches
        return True

    def update_exception_usage(self, exception_id: str, success: bool = True) -> None:
        """Update exception usage statistics."""
        self.db.update_exception_usage(exception_id, success)

    def get_context_retention_score(self) -> float:
        """Calculate the current Context Retention Score (CRS).
        
        Returns:
            CRS as a percentage (0-100)
        """
        crs_calc = self.db.calculate_crs()
        return crs_calc.crs_score

    def get_memory_stats(self):
        """Get statistics about the adaptive memory."""
        return self.db.get_memory_stats()

