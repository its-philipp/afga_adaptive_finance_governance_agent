"""EMA A2A Agent Card - defines EMA's capabilities for A2A discovery."""

from __future__ import annotations

from a2a.types import AgentCard, Capability, CapabilityType


def get_ema_agent_card() -> AgentCard:
    """Get the A2A Agent Card for EMA (Exception Manager Agent).
    
    The agent card defines EMA's capabilities for A2A service discovery.
    """
    return AgentCard(
        name="Exception Manager Agent (EMA)",
        description=(
            "Processes human-in-the-loop (HITL) feedback to learn from human corrections "
            "and update the adaptive memory. Manages exception rules and calculates the "
            "Human Correction Rate (H-CR) KPI."
        ),
        capabilities=[
            Capability(
                type=CapabilityType.ACTION,
                name="hitl_processing",
                description=(
                    "Process HITL feedback when a human overrides an automated decision. "
                    "Analyzes the correction type and determines if the system should learn from it."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "feedback": {
                            "type": "object",
                            "properties": {
                                "transaction_id": {"type": "string"},
                                "invoice_id": {"type": "string"},
                                "original_decision": {"type": "string", "enum": ["approved", "rejected", "hitl"]},
                                "human_decision": {"type": "string", "enum": ["approved", "rejected"]},
                                "reasoning": {"type": "string"},
                                "should_create_exception": {"type": "boolean"},
                                "exception_type": {
                                    "type": "string",
                                    "enum": ["temporary", "recurring", "policy_gap"],
                                    "nullable": True,
                                },
                            },
                            "required": [
                                "transaction_id",
                                "invoice_id",
                                "original_decision",
                                "human_decision",
                                "reasoning",
                            ],
                        },
                        "invoice": {
                            "type": "object",
                            "description": "Original invoice data for context",
                        },
                        "trace_id": {"type": "string", "description": "Trace ID for observability"},
                    },
                    "required": ["feedback", "invoice"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "correction_type": {
                            "type": "string",
                            "enum": ["new_exception", "policy_gap", "one_time_override"],
                        },
                        "should_learn": {"type": "boolean"},
                        "exception_description": {"type": "string"},
                        "memory_update_id": {"type": "string", "nullable": True},
                        "hcr_updated": {"type": "boolean"},
                        "audit_trail": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ),
            Capability(
                type=CapabilityType.ACTION,
                name="memory_management",
                description=(
                    "Manage the adaptive memory: add, query, and update learned exceptions. "
                    "Provides Context Retention Score (CRS) and memory statistics."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["query", "stats"]},
                        "vendor": {"type": "string", "nullable": True},
                        "category": {"type": "string", "nullable": True},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "exceptions": {"type": "array"},
                        "stats": {"type": "object"},
                        "crs_score": {"type": "number"},
                    },
                },
            ),
        ],
        version="1.0.0",
        url="http://localhost:8000/api/v1/agents/ema",  # Will be updated based on deployment
    )

