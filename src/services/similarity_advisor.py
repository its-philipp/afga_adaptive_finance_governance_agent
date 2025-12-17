"""Similarity advisor for PAA to query historical invoice patterns."""

from __future__ import annotations

import logging
from typing import Any

from .databricks_embeddings import search_embeddings, DatabricksUnavailable

logger = logging.getLogger(__name__)


class SimilarityAdvisor:
    """Provides historical invoice similarity context to PAA decisions."""

    def __init__(self, enabled: bool = True):
        """Initialize similarity advisor.
        
        Args:
            enabled: Whether to query Databricks (disable for local-only mode)
        """
        self.enabled = enabled

    def get_similar_invoices(
        self, 
        invoice_summary: str, 
        k: int = 3,
        sample_limit: int = 500,
    ) -> dict[str, Any]:
        """Query Databricks for similar historical invoices.
        
        Args:
            invoice_summary: Natural language invoice description
            k: Number of similar invoices to return
            sample_limit: Max embeddings to search
            
        Returns:
            Dict with similar invoices and metadata, or empty result if disabled/error
        """
        if not self.enabled:
            return {"enabled": False, "results": [], "note": "Similarity advisor disabled"}

        try:
            results = search_embeddings(
                query=invoice_summary,
                k=k,
                sample_limit=sample_limit,
            )
            return {
                "enabled": True,
                "results": results.get("results", []),
                "total_searched": results.get("total_searched", 0),
                "model": results.get("model"),
                "note": "Historical patterns retrieved successfully",
            }
        except DatabricksUnavailable as exc:
            logger.warning(f"Databricks unavailable for similarity search: {exc}")
            return {
                "enabled": True,
                "results": [],
                "note": f"Databricks unavailable: {exc}",
                "error": "unavailable",
            }
        except Exception as exc:
            logger.error(f"Similarity search failed: {exc}", exc_info=True)
            return {
                "enabled": True,
                "results": [],
                "note": f"Similarity search error: {exc}",
                "error": "failed",
            }

    def format_for_llm_context(self, similar_invoices: list[dict]) -> str:
        """Format similar invoices for LLM context.
        
        Args:
            similar_invoices: List of similar invoice results
            
        Returns:
            Formatted string for LLM prompt
        """
        if not similar_invoices:
            return "No similar historical invoices found."

        lines = ["### Similar Historical Invoices"]
        for idx, invoice in enumerate(similar_invoices, 1):
            invoice_id = invoice.get("invoice_id", "Unknown")
            similarity = invoice.get("similarity", 0) * 100
            lines.append(f"{idx}. **{invoice_id}** (Similarity: {similarity:.1f}%)")
        
        return "\n".join(lines)


# Global singleton
_similarity_advisor: SimilarityAdvisor | None = None


def get_similarity_advisor() -> SimilarityAdvisor:
    """Get or create the global SimilarityAdvisor instance."""
    global _similarity_advisor
    if _similarity_advisor is None:
        import os
        enabled = os.getenv("ENABLE_SIMILARITY_ADVISOR", "true").lower() == "true"
        _similarity_advisor = SimilarityAdvisor(enabled=enabled)
    return _similarity_advisor
