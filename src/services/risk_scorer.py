"""Risk scoring service for TAA."""

from __future__ import annotations

import logging
from typing import List

from ..core.config import get_settings
from ..models.schemas import Invoice, RiskAssessment, RiskLevel


logger = logging.getLogger(__name__)


class RiskScorer:
    """Calculates risk scores for transactions."""

    def __init__(self):
        self.settings = get_settings()

    def assess_risk(self, invoice: Invoice) -> RiskAssessment:
        """Assess the risk level of a transaction.
        
        Args:
            invoice: Invoice to assess
            
        Returns:
            RiskAssessment with score, level, and factors
        """
        risk_factors = []
        risk_score = 0.0

        # Factor 1: Amount-based risk (40% weight)
        if invoice.amount > self.settings.high_risk_amount:
            risk_score += 40.0
            risk_factors.append(f"High amount: ${invoice.amount:.2f} exceeds threshold")
        elif invoice.amount > self.settings.medium_risk_amount:
            risk_score += 25.0
            risk_factors.append(f"Medium amount: ${invoice.amount:.2f}")
        elif invoice.amount > self.settings.low_risk_amount:
            risk_score += 10.0
            risk_factors.append(f"Low-medium amount: ${invoice.amount:.2f}")

        # Factor 2: Vendor reputation (30% weight)
        if invoice.vendor_reputation < 60:
            risk_score += 30.0
            risk_factors.append(f"Low vendor reputation: {invoice.vendor_reputation}/100")
        elif invoice.vendor_reputation < 75:
            risk_score += 15.0
            risk_factors.append(f"Medium vendor reputation: {invoice.vendor_reputation}/100")

        # Factor 3: Missing PO (20% weight)
        if not invoice.po_number and invoice.amount > 500:
            risk_score += 20.0
            risk_factors.append("Missing purchase order for amount over $500")

        # Factor 4: International transaction (10% weight)
        if invoice.international or invoice.currency != "USD":
            risk_score += 10.0
            risk_factors.append(f"International transaction ({invoice.currency})")

        # Factor 5: Category-specific risk adjustments
        high_risk_categories = ["Software", "Professional Services", "Consulting"]
        if invoice.category in high_risk_categories:
            risk_score += 5.0
            risk_factors.append(f"High-risk category: {invoice.category}")

        # Determine risk level based on score
        if risk_score >= 70:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 50:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 25:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        assessment = RiskAssessment(
            risk_score=min(risk_score, 100.0),  # Cap at 100
            risk_level=risk_level,
            risk_factors=risk_factors if risk_factors else ["No significant risk factors identified"],
            assessment_details={
                "amount": invoice.amount,
                "vendor_reputation": invoice.vendor_reputation,
                "has_po": bool(invoice.po_number),
                "international": invoice.international,
                "category": invoice.category,
            }
        )

        logger.info(f"Risk assessment for {invoice.invoice_id}: {risk_level.value} ({risk_score:.1f})")
        return assessment

