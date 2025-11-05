"""TAA (Transaction Auditor Agent) state definition."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from ...models.schemas import Invoice, RiskAssessment, PolicyCheckResult, DecisionType


class TransactionAuditorState(TypedDict, total=False):
    """State for Transaction Auditor Agent workflow."""
    
    # Input
    invoice: Invoice
    trace_id: str
    
    # Risk Assessment
    risk_assessment: RiskAssessment
    
    # PAA Communication
    paa_request_sent: bool
    paa_response: Optional[PolicyCheckResult]
    
    # EMA Communication (optional - only for human overrides later)
    ema_request_sent: bool
    ema_response: Optional[Dict[str, Any]]
    
    # Decision
    final_decision: DecisionType
    decision_reasoning: str
    requires_hitl: bool
    
    # Audit
    audit_trail: List[str]

