"""PAA (Policy Adherence Agent) state definition."""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from ...models.schemas import Invoice, PolicyCheckResult, MemoryException, RetrievedSource, RAGTriadMetrics


class PolicyAdherenceState(TypedDict, total=False):
    """State for Policy Adherence Agent workflow."""

    # Input
    invoice: Invoice
    trace_id: str

    # Policy Retrieval
    retrieved_policies: List[Dict[str, Any]]
    retrieved_sources: List[RetrievedSource]
    rag_metrics: RAGTriadMetrics
    hallucination_warnings: List[str]

    # Memory Check
    memory_exceptions: List[MemoryException]

    # Compliance Evaluation
    compliance_result: PolicyCheckResult
    reasoning: str

    # Audit
    audit_trail: List[str]
