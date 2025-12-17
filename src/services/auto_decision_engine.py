from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from ..core.config import Settings, get_settings
from ..db.memory_db import MemoryDatabase
from ..models.memory_schemas import MemoryQuery
from ..models.schemas import (
    DecisionType,
    Invoice,
    PolicyCheckResult,
    RiskAssessment,
    RiskLevel,
    MemoryException,
)


logger = logging.getLogger(__name__)


@dataclass
class AutoDecisionOutcome:
    """Result emitted by the autonomous decision engine."""

    should_override: bool
    decision: DecisionType
    reason: str
    confidence: float
    source: str
    rule_id: Optional[str] = None
    rule_label: Optional[str] = None

    def audit_message(self) -> str:
        prefix = "🤖 Auto decision"
        if self.source == "rule" and self.rule_id:
            return f"{prefix} (rule {self.rule_id}): {self.reason}"
        if self.source == "heuristic":
            return f"{prefix} (low-risk heuristic): {self.reason}"
        return f"{prefix}: {self.reason}"


class AutoDecisionEngine:
    """Applies learned rules and heuristics to minimize HITL escalations."""

    _AMOUNT_TOLERANCE = 0.1  # ±10% wiggle room for learned thresholds

    def __init__(
        self,
        memory_db: Optional[MemoryDatabase] = None,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.memory_db = memory_db or MemoryDatabase(self.settings.memory_db_path)

    def evaluate(
        self,
        *,
        invoice: Invoice,
        current_decision: DecisionType,
        policy_check: Optional[PolicyCheckResult],
        risk_assessment: Optional[RiskAssessment],
    ) -> AutoDecisionOutcome:
        """Return an override decision when automation can safely act."""
        if not self.settings.auto_decision_enabled:
            return AutoDecisionOutcome(False, current_decision, "", 0.0, source="disabled")

        if not policy_check:
            return AutoDecisionOutcome(False, current_decision, "Missing policy result", 0.0, source="missing_policy")

        # We only intervene when the pipeline would otherwise escalate to HITL
        if current_decision != DecisionType.HITL:
            return AutoDecisionOutcome(False, current_decision, "", policy_check.confidence, source="finalized")

        if policy_check.manual_review_required or policy_check.manual_exception_ids:
            return AutoDecisionOutcome(
                False, DecisionType.HITL, "Manual exception present", policy_check.confidence, source="manual_exception"
            )

        rule_match = self._match_rule(invoice)
        if rule_match:
            exception, action = rule_match
            let_reason = exception.description or "Learned exception"
            confidence = max(policy_check.confidence, exception.success_rate)
            reason = f"{let_reason} (success rate {exception.success_rate:.0%})"
            try:
                self.memory_db.update_exception_usage(exception.exception_id, success=True)
            except Exception as err:  # pragma: no cover - defensive logging
                logger.warning("Failed to update usage for exception %s: %s", exception.exception_id, err)
            logger.info("Auto decision via learned rule %s -> %s", exception.exception_id, action.value)
            return AutoDecisionOutcome(
                True,
                action,
                reason,
                confidence=confidence,
                source="rule",
                rule_id=exception.exception_id,
                rule_label=let_reason,
            )

        heuristic_override = self._heuristic_auto_approval(invoice, risk_assessment, policy_check)
        if heuristic_override:
            return heuristic_override

        return AutoDecisionOutcome(
            False, DecisionType.HITL, "No safe automation rule", policy_check.confidence, source="no_match"
        )

    def _match_rule(self, invoice: Invoice) -> Optional[Tuple[MemoryException, DecisionType]]:
        """Return the first learned rule that matches this invoice."""
        candidates: Dict[str, MemoryException] = {}
        queries = [
            MemoryQuery(vendor=invoice.vendor, min_success_rate=self.settings.auto_rule_min_success_rate),
            MemoryQuery(category=invoice.category, min_success_rate=self.settings.auto_rule_min_success_rate),
        ]
        for query in queries:
            try:
                for exc in self.memory_db.query_exceptions(query):
                    candidates.setdefault(exc.exception_id, exc)
            except Exception as err:  # pragma: no cover - defensive logging
                logger.warning("Failed to query adaptive memory for automation: %s", err)

        for exception in candidates.values():
            action = self._normalize_action(exception.condition)
            if not action:
                continue
            if self._condition_matches(invoice, exception.condition):
                return exception, action
        return None

    def _normalize_action(self, condition: Optional[Dict[str, Any]]) -> Optional[DecisionType]:
        """Extract the desired decision stored with the rule."""
        if not isinstance(condition, dict):
            return None
        raw_value = condition.get("auto_decision") or condition.get("auto_action")
        if not raw_value:
            return None
        normalized = str(raw_value).strip().lower()
        if normalized in {"approve", "approved", "auto_approve"}:
            return DecisionType.APPROVED
        if normalized in {"reject", "rejected", "auto_reject"}:
            return DecisionType.REJECTED
        return None

    def _condition_matches(self, invoice: Invoice, condition: Optional[Dict[str, Any]]) -> bool:
        """Check whether invoice attributes satisfy the rule condition."""
        if not isinstance(condition, dict):
            return True

        vendor = condition.get("vendor")
        if vendor and vendor.lower() != (invoice.vendor or "").lower():
            return False

        category = condition.get("category")
        if category and category.lower() != (invoice.category or "").lower():
            return False

        currency = condition.get("currency")
        if currency and currency.upper() != invoice.currency.upper():
            return False

        if "international" in condition:
            desired = bool(condition["international"])
            if bool(invoice.international) != desired:
                return False

        if not self._amount_in_range(invoice.amount, condition):
            return False

        return True

    def _amount_in_range(self, amount: float, condition: Dict[str, Any]) -> bool:
        """Check amount-related constraints."""
        threshold = condition.get("amount_threshold")
        if threshold is not None:
            tolerance = condition.get("amount_tolerance", self._AMOUNT_TOLERANCE)
            lower = threshold * (1 - tolerance)
            upper = threshold * (1 + tolerance)
            if not (lower <= amount <= upper):
                return False

        max_amount = condition.get("max_amount")
        if max_amount is not None and amount > max_amount:
            return False

        min_amount = condition.get("min_amount")
        if min_amount is not None and amount < min_amount:
            return False

        return True

    def _heuristic_auto_approval(
        self,
        invoice: Invoice,
        risk_assessment: Optional[RiskAssessment],
        policy_check: PolicyCheckResult,
    ) -> Optional[AutoDecisionOutcome]:
        """Apply lightweight heuristics for low-risk invoices."""
        if not risk_assessment:
            return None
        if not policy_check.is_compliant:
            return None

        risk_level = risk_assessment.risk_level
        thresholds = {
            RiskLevel.LOW: (
                self.settings.auto_low_risk_confidence_threshold,
                self.settings.auto_low_risk_max_amount,
            ),
            RiskLevel.MEDIUM: (
                self.settings.auto_medium_risk_confidence_threshold,
                self.settings.auto_medium_risk_max_amount,
            ),
        }

        if risk_level not in thresholds:
            return None

        min_confidence, max_amount = thresholds[risk_level]
        if policy_check.confidence < min_confidence:
            return None
        if invoice.amount > max_amount:
            return None

        reason = (
            f"{risk_level.value.title()} risk invoice auto-approved "
            f"(confidence {policy_check.confidence:.2f}, amount ${invoice.amount:,.2f})"
        )
        logger.info(
            "Auto decision via heuristic for invoice %s -> approved (risk=%s, confidence=%.2f)",
            invoice.invoice_id,
            risk_level.value,
            policy_check.confidence,
        )
        return AutoDecisionOutcome(
            True,
            DecisionType.APPROVED,
            reason,
            confidence=policy_check.confidence,
            source="heuristic",
        )
