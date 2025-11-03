"""Unit tests for Memory Database."""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from src.db.memory_db import MemoryDatabase
from src.models.memory_schemas import MemoryQuery


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_memory.db"
        db = MemoryDatabase(db_path=str(db_path))
        yield db


def test_add_exception(temp_db):
    """Test adding an exception to memory."""
    exception_id = temp_db.add_exception(
        vendor="Test Vendor",
        category="Software",
        rule_type="recurring",
        description="Test exception for Test Vendor software purchases",
        condition={"min_amount": 1000.0}
    )
    
    assert exception_id is not None
    assert len(exception_id) > 0


def test_query_exceptions_by_vendor(temp_db):
    """Test querying exceptions by vendor."""
    # Add test exception
    temp_db.add_exception(
        vendor="Acme Corp",
        category="Software",
        rule_type="recurring",
        description="Acme Corp software exception",
        condition={"reason": "preferred vendor"}
    )
    
    # Query by vendor
    query = MemoryQuery(vendor="Acme Corp")
    exceptions = temp_db.query_exceptions(query)
    
    assert len(exceptions) == 1
    assert exceptions[0].vendor == "Acme Corp"
    assert exceptions[0].description == "Acme Corp software exception"


def test_query_exceptions_by_category(temp_db):
    """Test querying exceptions by category."""
    # Add test exceptions
    temp_db.add_exception(
        vendor="Vendor A",
        category="Hardware",
        rule_type="recurring",
        description="Hardware exception",
        condition={}
    )
    
    temp_db.add_exception(
        vendor="Vendor B",
        category="Software",
        rule_type="recurring",
        description="Software exception",
        condition={}
    )
    
    # Query by category
    query = MemoryQuery(category="Hardware")
    exceptions = temp_db.query_exceptions(query)
    
    assert len(exceptions) == 1
    assert exceptions[0].category == "Hardware"


def test_update_exception_usage(temp_db):
    """Test updating exception usage statistics."""
    # Add exception
    exception_id = temp_db.add_exception(
        vendor="Test Vendor",
        category="Test",
        rule_type="recurring",
        description="Test exception",
        condition={}
    )
    
    # Update usage (success)
    temp_db.update_exception_usage(exception_id, success=True)
    
    # Query and verify
    query = MemoryQuery(vendor="Test Vendor")
    exceptions = temp_db.query_exceptions(query)
    
    assert len(exceptions) == 1
    assert exceptions[0].applied_count == 1
    assert exceptions[0].success_rate == 1.0
    
    # Update usage (failure)
    temp_db.update_exception_usage(exception_id, success=False)
    
    # Query and verify
    exceptions = temp_db.query_exceptions(query)
    
    assert exceptions[0].applied_count == 2
    assert exceptions[0].success_rate == 0.5  # 1 success out of 2 attempts


def test_get_memory_stats(temp_db):
    """Test getting memory statistics."""
    # Add some exceptions
    temp_db.add_exception(
        vendor="Vendor 1",
        category="Cat 1",
        rule_type="recurring",
        description="Exception 1",
        condition={}
    )
    
    exception_id2 = temp_db.add_exception(
        vendor="Vendor 2",
        category="Cat 2",
        rule_type="recurring",
        description="Exception 2",
        condition={}
    )
    
    # Apply one of them
    temp_db.update_exception_usage(exception_id2, success=True)
    
    # Get stats
    stats = temp_db.get_memory_stats()
    
    assert stats.total_exceptions == 2
    assert stats.active_exceptions == 1  # Only one has been applied
    assert stats.total_applications == 1


def test_calculate_kpis(temp_db):
    """Test KPI calculation."""
    from src.models.schemas import (
        Invoice, RiskAssessment, RiskLevel, PolicyCheckResult,
        TransactionResult, DecisionType, LineItem
    )
    
    # Create a test transaction
    invoice = Invoice(
        invoice_id="TEST-001",
        vendor="Test Vendor",
        vendor_reputation=80,
        amount=1000.0,
        currency="USD",
        category="Test",
        date="2025-11-03",
        po_number="PO-001",
        line_items=[LineItem(description="Test", quantity=1, unit_price=1000.0)],
        tax=80.0,
        total=1080.0
    )
    
    risk = RiskAssessment(
        risk_score=30.0,
        risk_level=RiskLevel.MEDIUM,
        risk_factors=["Test factor"],
        assessment_details={}
    )
    
    policy = PolicyCheckResult(
        is_compliant=True,
        violated_policies=[],
        applied_exceptions=[],
        reasoning="Test",
        confidence=0.9
    )
    
    result = TransactionResult(
        transaction_id="T-001",
        invoice=invoice,
        risk_assessment=risk,
        policy_check=policy,
        final_decision=DecisionType.APPROVED,
        decision_reasoning="Test",
        human_override=False,
        processing_time_ms=100,
        audit_trail=["Test trail"],
        trace_id="trace-001",
        created_at=datetime.now()
    )
    
    # Save transaction
    temp_db.save_transaction(result)
    
    # Calculate KPIs
    kpis = temp_db.calculate_and_save_kpis()
    
    assert kpis.total_transactions == 1
    assert kpis.human_corrections == 0
    assert kpis.hcr == 0.0  # No human corrections
    assert kpis.atar == 100.0  # 100% auto-approved
    assert kpis.audit_traceability_score == 100.0

