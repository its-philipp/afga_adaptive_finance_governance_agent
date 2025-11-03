"""PAA A2A Agent Card - defines PAA's capabilities for A2A discovery."""

from __future__ import annotations

from a2a.types import AgentCard, Capability, CapabilityType


def get_paa_agent_card() -> AgentCard:
    """Get the A2A Agent Card for PAA (Policy Adherence Agent).
    
    The agent card defines PAA's capabilities for A2A service discovery.
    """
    return AgentCard(
        name="Policy Adherence Agent (PAA)",
        description=(
            "Checks transactions against company policies using RAG (Retrieval-Augmented Generation). "
            "Retrieves relevant policy documents and consults adaptive memory for learned exceptions. "
            "Returns compliance result with confidence score."
        ),
        capabilities=[
            Capability(
                type=CapabilityType.ACTION,
                name="policy_checking",
                description=(
                    "Check if a transaction complies with company policies. Uses RAG to retrieve "
                    "relevant policy documents and queries adaptive memory for exceptions."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "invoice": {
                            "type": "object",
                            "description": "Invoice data to check",
                            "properties": {
                                "invoice_id": {"type": "string"},
                                "vendor": {"type": "string"},
                                "amount": {"type": "number"},
                                "category": {"type": "string"},
                                "po_number": {"type": "string", "nullable": True},
                                "international": {"type": "boolean"},
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
                        "is_compliant": {"type": "boolean"},
                        "violated_policies": {"type": "array", "items": {"type": "string"}},
                        "applied_exceptions": {"type": "array", "items": {"type": "string"}},
                        "reasoning": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                },
            ),
            Capability(
                type=CapabilityType.ACTION,
                name="compliance_evaluation",
                description=(
                    "Evaluate compliance using LLM with retrieved policies and learned exceptions. "
                    "Provides detailed reasoning and confidence assessment."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "invoice": {"type": "object"},
                        "policies": {"type": "array", "items": {"type": "string"}},
                        "exceptions": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["invoice"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "is_compliant": {"type": "boolean"},
                        "confidence": {"type": "number"},
                        "reasoning": {"type": "string"},
                    },
                },
            ),
        ],
        version="1.0.0",
        url="http://localhost:8000/api/v1/agents/paa",
    )

