"""Pydantic schemas for AFGA data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ComplianceStatus(str, Enum):
    """Transaction compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    EDGE_CASE = "edge_case"
    PENDING = "pending"


class DecisionType(str, Enum):
    """Final decision types."""
    APPROVED = "approved"
    REJECTED = "rejected"
    HITL = "hitl"  # Human-in-the-loop required
    PENDING = "pending"


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LineItem(BaseModel):
    """Invoice line item."""
    description: str
    quantity: int
    unit_price: float


class Invoice(BaseModel):
    """Invoice data model."""
    invoice_id: str
    vendor: str
    vendor_reputation: int = Field(ge=0, le=100)
    amount: float
    currency: str = "USD"
    category: str
    date: str
    po_number: Optional[str] = None
    line_items: List[LineItem]
    tax: float
    total: float
    payment_terms: str = "Net 30"
    notes: Optional[str] = None
    international: bool = False


class TransactionRequest(BaseModel):
    """Request to process a transaction."""
    invoice: Invoice
    trace_id: Optional[str] = None


class RiskAssessment(BaseModel):
    """Risk assessment result from TAA."""
    risk_score: float = Field(ge=0, le=100)
    risk_level: RiskLevel
    risk_factors: List[str]
    assessment_details: Dict[str, Any]


class RetrievedSource(BaseModel):
    """Metadata about a retrieved policy chunk used as evidence."""
    policy_name: str
    policy_filename: Optional[str] = None
    chunk_index: int
    score: float
    snippet: str
    matched_terms: List[str] = Field(default_factory=list)


class RAGTriadMetrics(BaseModel):
    """RAG transparency metrics for policy evidence."""
    supporting_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    hallucinated_references: List[str] = Field(default_factory=list)
    coverage_ratio: float = 0.0
    average_relevance: float = 0.0


class PolicyCheckResult(BaseModel):
    """Policy adherence check result from PAA."""
    is_compliant: bool
    violated_policies: List[str] = Field(default_factory=list)
    applied_exceptions: List[str] = Field(default_factory=list)
    reasoning: str
    confidence: float = Field(ge=0, le=1)
    retrieved_sources: List[RetrievedSource] = Field(default_factory=list)
    rag_metrics: Optional[RAGTriadMetrics] = None
    hallucination_warnings: List[str] = Field(default_factory=list)
    applied_exception_ids: List[str] = Field(default_factory=list)


class AssistantChatHistoryEntry(BaseModel):
    role: str
    content: str


class AssistantChatRequest(BaseModel):
    message: str
    page: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    history: List[AssistantChatHistoryEntry] = Field(default_factory=list)


class AssistantChatSource(BaseModel):
    type: str
    id: str
    title: str
    snippet: Optional[str] = None
    url: Optional[str] = None


class AssistantChatResponse(BaseModel):
    reply: str
    sources: List[AssistantChatSource] = Field(default_factory=list)


class HITLFeedback(BaseModel):
    """Human-in-the-loop feedback for EMA."""
    transaction_id: str
    invoice_id: str
    original_decision: DecisionType
    human_decision: DecisionType  # approve or reject
    reasoning: str
    should_create_exception: bool = False
    exception_type: Optional[str] = None  # "temporary", "recurring", "policy_gap"


class MemoryException(BaseModel):
    """Learned exception stored in adaptive memory."""
    exception_id: str
    vendor: Optional[str] = None
    category: Optional[str] = None
    rule_type: str  # "exception", "learned_threshold", "custom_rule"
    description: str
    condition: Dict[str, Any]  # Structured rule conditions
    applied_count: int = 0
    success_rate: float = 1.0
    created_at: datetime
    last_applied_at: Optional[datetime] = None


class TransactionResult(BaseModel):
    """Complete transaction processing result."""
    transaction_id: str
    invoice: Invoice
    risk_assessment: RiskAssessment
    policy_check: PolicyCheckResult
    final_decision: DecisionType
    decision_reasoning: str
    human_override: bool = False
    processing_time_ms: int
    audit_trail: List[str]
    trace_id: str
    created_at: datetime


class KPIMetrics(BaseModel):
    """Key Performance Indicators."""
    date: str
    total_transactions: int
    human_corrections: int
    hcr: float  # Human Correction Rate (%)
    crs: float  # Context Retention Score (%)
    atar: float  # Automated Transaction Approval Rate (%)
    avg_processing_time_ms: int
    audit_traceability_score: float


class TransactionSummary(BaseModel):
    """Summary of a transaction for display."""
    transaction_id: str
    invoice_id: str
    vendor: str
    amount: float
    category: str
    risk_level: RiskLevel
    final_decision: DecisionType
    human_override: bool
    created_at: datetime

