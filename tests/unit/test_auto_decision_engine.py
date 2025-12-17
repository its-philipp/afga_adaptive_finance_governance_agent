from __future__ import annotations

import tempfile
from datetime import datetime

from src.db.memory_db import MemoryDatabase
from src.models.schemas import (
    DecisionType,
    Invoice,
    LineItem,
    PolicyCheckResult,
    RiskAssessment,
    RiskLevel,
)
from src.services.auto_decision_engine import AutoDecisionEngine


def _build_invoice(vendor: str, amount: float = 1200.0) -> Invoice:
    return Invoice(
        invoice_id="INV-001",
        vendor=vendor,
        vendor_reputation=80,
        amount=amount,
        currency="USD",
        category="Software",
        date=datetime.now().strftime("%Y-%m-%d"),
        line_items=[LineItem(description="Subscription", quantity=1, unit_price=amount)],
        tax=0.0,
        total=amount,
        payment_terms="Net 30",
        international=False,
    )


def _build_risk(level: RiskLevel) -> RiskAssessment:
    return RiskAssessment(
        risk_score=20.0 if level == RiskLevel.LOW else 35.0,
        risk_level=level,
        risk_factors=["Test factor"],
        assessment_details={
            "amount": 1200.0,
            "vendor_reputation": 80,
            "has_po": True,
            "international": False,
            "category": "Software",
        },
    )


def _build_policy(confidence: float = 0.9) -> PolicyCheckResult:
    return PolicyCheckResult(
        is_compliant=True,
        violated_policies=[],
        applied_exceptions=[],
        reasoning="Compliant",
        confidence=confidence,
    )


def test_rule_based_auto_decision_overrides_hitl():
    with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
        db = MemoryDatabase(db_path=temp_db.name)
        db.add_exception(
            vendor="Acme Corp",
            category="Software",
            rule_type="recurring",
            description="Recurring subscription auto-approve",
            condition={
                "vendor": "Acme Corp",
                "auto_decision": "approved",
                "amount_threshold": 1200.0,
            },
        )

        engine = AutoDecisionEngine(memory_db=db)
        invoice = _build_invoice("Acme Corp")
        policy = _build_policy(confidence=0.6)  # below heuristic threshold to ensure rule path
        risk = _build_risk(RiskLevel.MEDIUM)

        outcome = engine.evaluate(
            invoice=invoice,
            current_decision=DecisionType.HITL,
            policy_check=policy,
            risk_assessment=risk,
        )

        assert outcome.should_override
        assert outcome.decision == DecisionType.APPROVED
        assert outcome.source == "rule"
        assert outcome.rule_id is not None


def test_low_risk_heuristic_auto_approval():
    with tempfile.NamedTemporaryFile(suffix=".db") as temp_db:
        db = MemoryDatabase(db_path=temp_db.name)

        engine = AutoDecisionEngine(memory_db=db)
        invoice = _build_invoice("Beta LLC", amount=1500.0)
        policy = _build_policy(confidence=0.9)
        risk = _build_risk(RiskLevel.LOW)

        outcome = engine.evaluate(
            invoice=invoice,
            current_decision=DecisionType.HITL,
            policy_check=policy,
            risk_assessment=risk,
        )

        assert outcome.should_override
        assert outcome.decision == DecisionType.APPROVED
        assert outcome.source == "heuristic"
