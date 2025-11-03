"""EMA (Exception Manager Agent) state definition."""

from __future__ import annotations

from typing import Dict, List, TypedDict

from ...models.schemas import HITLFeedback, Invoice, DecisionType


class ExceptionManagerState(TypedDict, total=False):
    """State for Exception Manager Agent workflow."""
    
    # Input
    feedback: HITLFeedback
    invoice: Invoice
    
    # Processing
    correction_type: str  # "new_exception", "policy_gap", "one_time_override"
    should_learn: bool
    exception_description: str
    exception_condition: Dict[str, any]
    
    # Output
    memory_update_id: str
    hcr_updated: bool
    notification_sent: bool
    
    # Audit
    audit_trail: List[str]
    trace_id: str

