"""TAA A2A Agent Card - defines TAA's capabilities for A2A discovery."""

from __future__ import annotations

from a2a.types import AgentCard, Capability, CapabilityType


def get_taa_agent_card() -> AgentCard:
    """Get the A2A Agent Card for TAA (Transaction Auditor Agent).
    
    Note: TAA is primarily a client agent, but we define its card for documentation.
    """
    return AgentCard(
        name="Transaction Auditor Agent (TAA)",
        description=(
            "Orchestrates transaction processing by assessing risk and delegating "
            "to specialized agents (PAA for policy checking, EMA for learning). "
            "Makes final approve/reject/HITL decisions."
        ),
        capabilities=[
            Capability(
                type=CapabilityType.ACTION,
                name="transaction_audit",
                description=(
                    "Process a financial transaction through risk assessment and policy checking. "
                    "Delegates to PAA and EMA as needed, returns final decision."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "invoice": {
                            "type": "object",
                            "description": "Invoice data to process",
                            "properties": {
                                "invoice_id": {"type": "string"},
                                "vendor": {"type": "string"},
                                "amount": {"type": "number"},
                                "category": {"type": "string"},
                                "po_number": {"type": "string", "nullable": True},
                            },
                            "required": ["invoice_id", "vendor", "amount", "category"],
                        },
                        "trace_id": {"type": "string", "description": "Trace ID for observability"},
                    },
                    "required": ["invoice"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "final_decision": {
                            "type": "string",
                            "enum": ["approved", "rejected", "hitl"],
                        },
                        "decision_reasoning": {"type": "string"},
                        "risk_assessment": {"type": "object"},
                        "requires_hitl": {"type": "boolean"},
                        "audit_trail": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ),
            Capability(
                type=CapabilityType.ACTION,
                name="risk_scoring",
                description=(
                    "Assess the risk level of a transaction based on amount, vendor reputation, "
                    "missing documentation, and other factors."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "invoice": {"type": "object"},
                    },
                    "required": ["invoice"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "risk_score": {"type": "number", "minimum": 0, "maximum": 100},
                        "risk_level": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                        },
                        "risk_factors": {"type": "array", "items": {"type": "string"}},
                    },
                },
            ),
        ],
        version="1.0.0",
        url="http://localhost:8000/api/v1/agents/taa",
    )

