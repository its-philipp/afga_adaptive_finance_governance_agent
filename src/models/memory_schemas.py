"""Memory-specific schemas for adaptive learning."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MemoryQuery(BaseModel):
    """Query for searching adaptive memory."""
    vendor: Optional[str] = None
    category: Optional[str] = None
    amount_range: Optional[tuple[float, float]] = None
    rule_type: Optional[str] = None
    min_success_rate: float = 0.5


class MemoryStats(BaseModel):
    """Statistics about the adaptive memory."""
    total_exceptions: int
    active_exceptions: int
    total_applications: int
    avg_success_rate: float
    most_applied_rules: list[Dict[str, Any]]
    recent_additions: list[Dict[str, Any]]


class MemoryUpdateRequest(BaseModel):
    """Request to update adaptive memory."""
    exception_id: Optional[str] = None  # None for new exception
    vendor: Optional[str] = None
    category: Optional[str] = None
    rule_type: str
    description: str
    condition: Dict[str, Any]


class CRSCalculation(BaseModel):
    """Context Retention Score calculation details."""
    applicable_scenarios: int  # Number of times memory could have been applied
    successful_applications: int  # Number of times memory was correctly applied
    crs_score: float = Field(ge=0, le=100)  # CRS percentage
    details: str

