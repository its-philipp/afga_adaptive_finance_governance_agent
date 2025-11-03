"""Unit tests for Risk Scorer."""

import pytest

from src.models.schemas import Invoice, RiskLevel, LineItem
from src.services.risk_scorer import RiskScorer


def test_risk_scorer_high_amount():
    """Test risk scoring for high amount invoices."""
    scorer = RiskScorer()
    
    invoice = Invoice(
        invoice_id="TEST-001",
        vendor="Test Vendor",
        vendor_reputation=80,
        amount=15000.0,  # High amount
        currency="USD",
        category="Software",
        date="2025-11-03",
        po_number="PO-1234",
        line_items=[LineItem(description="Test item", quantity=1, unit_price=15000.0)],
        tax=1200.0,
        total=16200.0,
    )
    
    assessment = scorer.assess_risk(invoice)
    
    assert assessment.risk_level == RiskLevel.CRITICAL or assessment.risk_level == RiskLevel.HIGH
    assert assessment.risk_score > 40.0
    assert len(assessment.risk_factors) > 0


def test_risk_scorer_low_amount():
    """Test risk scoring for low amount invoices."""
    scorer = RiskScorer()
    
    invoice = Invoice(
        invoice_id="TEST-002",
        vendor="Test Vendor",
        vendor_reputation=90,
        amount=500.0,  # Low amount
        currency="USD",
        category="Office Supplies",
        date="2025-11-03",
        po_number="PO-1234",
        line_items=[LineItem(description="Test item", quantity=1, unit_price=500.0)],
        tax=40.0,
        total=540.0,
    )
    
    assessment = scorer.assess_risk(invoice)
    
    assert assessment.risk_level == RiskLevel.LOW
    assert assessment.risk_score < 30.0


def test_risk_scorer_missing_po():
    """Test risk scoring for missing PO."""
    scorer = RiskScorer()
    
    invoice = Invoice(
        invoice_id="TEST-003",
        vendor="Test Vendor",
        vendor_reputation=75,
        amount=2000.0,
        currency="USD",
        category="Services",
        date="2025-11-03",
        po_number=None,  # Missing PO
        line_items=[LineItem(description="Test item", quantity=1, unit_price=2000.0)],
        tax=160.0,
        total=2160.0,
    )
    
    assessment = scorer.assess_risk(invoice)
    
    # Should have additional risk due to missing PO
    assert any("purchase order" in factor.lower() for factor in assessment.risk_factors)
    assert assessment.risk_score > 20.0


def test_risk_scorer_low_vendor_reputation():
    """Test risk scoring for low vendor reputation."""
    scorer = RiskScorer()
    
    invoice = Invoice(
        invoice_id="TEST-004",
        vendor="Risky Vendor",
        vendor_reputation=40,  # Low reputation
        amount=1000.0,
        currency="USD",
        category="Services",
        date="2025-11-03",
        po_number="PO-1234",
        line_items=[LineItem(description="Test item", quantity=1, unit_price=1000.0)],
        tax=80.0,
        total=1080.0,
    )
    
    assessment = scorer.assess_risk(invoice)
    
    # Should have additional risk due to low reputation
    assert any("reputation" in factor.lower() for factor in assessment.risk_factors)
    assert assessment.risk_score > 30.0


def test_risk_scorer_international():
    """Test risk scoring for international transactions."""
    scorer = RiskScorer()
    
    invoice = Invoice(
        invoice_id="TEST-005",
        vendor="International Vendor",
        vendor_reputation=80,
        amount=3000.0,
        currency="EUR",  # Non-USD
        category="Services",
        date="2025-11-03",
        po_number="PO-1234",
        line_items=[LineItem(description="Test item", quantity=1, unit_price=3000.0)],
        tax=240.0,
        total=3240.0,
        international=True,
    )
    
    assessment = scorer.assess_risk(invoice)
    
    # Should have additional risk due to international
    assert any("international" in factor.lower() or "EUR" in factor for factor in assessment.risk_factors)
    assert assessment.risk_score > 10.0

