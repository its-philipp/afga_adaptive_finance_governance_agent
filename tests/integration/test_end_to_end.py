"""End-to-end integration tests for AFGA."""

import json
import tempfile
from pathlib import Path

import pytest

from src.agents import AFGAOrchestrator
from src.models.schemas import Invoice, HITLFeedback, DecisionType, LineItem


@pytest.fixture
def temp_orchestrator():
    """Create an orchestrator with temporary database."""
    from src.db.memory_db import MemoryDatabase
    from src.core.observability import Observability
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = MemoryDatabase(db_path=str(db_path))
        obs = Observability()
        orchestrator = AFGAOrchestrator(observability=obs, memory_db=db)
        yield orchestrator


def test_process_compliant_transaction(temp_orchestrator):
    """Test processing a compliant transaction end-to-end."""
    invoice = Invoice(
        invoice_id="TEST-001",
        vendor="Acme Corporation",
        vendor_reputation=90,
        amount=2000.0,
        currency="USD",
        category="Software",
        date="2025-11-03",
        po_number="PO-1234",
        line_items=[LineItem(description="Software license", quantity=1, unit_price=2000.0)],
        tax=160.0,
        total=2160.0,
    )
    
    result = temp_orchestrator.process_transaction(invoice)
    
    # Verify result
    assert result is not None
    assert result.transaction_id is not None
    assert result.invoice.invoice_id == "TEST-001"
    assert result.risk_assessment is not None
    assert result.policy_check is not None
    assert result.final_decision in [DecisionType.APPROVED, DecisionType.REJECTED, DecisionType.HITL]
    assert len(result.audit_trail) > 0
    assert result.processing_time_ms > 0


def test_process_high_risk_transaction(temp_orchestrator):
    """Test processing a high-risk transaction."""
    invoice = Invoice(
        invoice_id="TEST-002",
        vendor="Unknown Vendor",
        vendor_reputation=45,  # Low reputation
        amount=25000.0,  # High amount
        currency="USD",
        category="Services",
        date="2025-11-03",
        po_number=None,  # Missing PO
        line_items=[LineItem(description="Consulting services", quantity=1, unit_price=25000.0)],
        tax=2000.0,
        total=27000.0,
    )
    
    result = temp_orchestrator.process_transaction(invoice)
    
    # High risk transaction should require HITL or be rejected
    assert result.risk_assessment.risk_level.value in ["high", "critical"]
    assert result.final_decision in [DecisionType.HITL, DecisionType.REJECTED]


def test_hitl_feedback_and_memory_learning(temp_orchestrator):
    """Test HITL feedback processing and memory learning."""
    # Step 1: Process a transaction
    invoice = Invoice(
        invoice_id="TEST-003",
        vendor="Special Vendor",
        vendor_reputation=75,
        amount=5500.0,
        currency="USD",
        category="Marketing",
        date="2025-11-03",
        po_number="PO-5678",
        line_items=[LineItem(description="Marketing campaign", quantity=1, unit_price=5500.0)],
        tax=440.0,
        total=5940.0,
    )
    
    result = temp_orchestrator.process_transaction(invoice)
    
    # Step 2: Provide HITL feedback
    feedback = HITLFeedback(
        transaction_id=result.transaction_id,
        invoice_id=invoice.invoice_id,
        original_decision=result.final_decision,
        human_decision=DecisionType.APPROVED,
        reasoning="Special Vendor is a trusted partner, approved despite medium risk",
        should_create_exception=True,
        exception_type="recurring"
    )
    
    hitl_result = temp_orchestrator.process_hitl_feedback(feedback, invoice)
    
    # Verify HITL processing
    assert hitl_result is not None
    assert hitl_result.get("transaction_id") == result.transaction_id
    assert hitl_result.get("memory_updated") is not None
    
    # Step 3: Verify memory was updated
    memory_stats = temp_orchestrator.get_memory_stats()
    assert memory_stats.total_exceptions >= 1


def test_kpi_calculation(temp_orchestrator):
    """Test KPI calculation after processing transactions."""
    # Process multiple transactions
    for i in range(5):
        invoice = Invoice(
            invoice_id=f"TEST-{i:03d}",
            vendor=f"Vendor {i}",
            vendor_reputation=70 + i * 5,
            amount=1000.0 + i * 500,
            currency="USD",
            category="Services",
            date="2025-11-03",
            po_number=f"PO-{i:04d}",
            line_items=[LineItem(description=f"Service {i}", quantity=1, unit_price=1000.0 + i * 500)],
            tax=80.0 + i * 40,
            total=1080.0 + i * 540,
        )
        
        temp_orchestrator.process_transaction(invoice)
    
    # Calculate KPIs
    kpis = temp_orchestrator.calculate_current_kpis()
    
    # Verify KPIs
    assert kpis is not None
    assert kpis.total_transactions == 5
    assert kpis.hcr >= 0.0  # H-CR should be >= 0
    assert kpis.atar >= 0.0  # ATAR should be >= 0
    assert kpis.audit_traceability_score >= 0.0


def test_transaction_retrieval(temp_orchestrator):
    """Test retrieving processed transactions."""
    # Process a transaction
    invoice = Invoice(
        invoice_id="TEST-RETRIEVE",
        vendor="Test Vendor",
        vendor_reputation=80,
        amount=1500.0,
        currency="USD",
        category="Software",
        date="2025-11-03",
        po_number="PO-9999",
        line_items=[LineItem(description="Software", quantity=1, unit_price=1500.0)],
        tax=120.0,
        total=1620.0,
    )
    
    result = temp_orchestrator.process_transaction(invoice)
    
    # Retrieve the transaction
    retrieved = temp_orchestrator.get_transaction(result.transaction_id)
    
    # Verify retrieval
    assert retrieved is not None
    assert retrieved.get("transaction_id") == result.transaction_id
    assert retrieved.get("invoice_id") == "TEST-RETRIEVE"


def test_agent_cards(temp_orchestrator):
    """Test that agent cards are properly defined."""
    cards = temp_orchestrator.get_agent_cards()
    
    # Verify all three agents have cards
    assert "taa" in cards
    assert "paa" in cards
    assert "ema" in cards
    
    # Verify card structure
    for agent_name, card in cards.items():
        assert card.get("name") is not None
        assert card.get("description") is not None
        assert card.get("capabilities") is not None
        assert len(card.get("capabilities", [])) > 0

