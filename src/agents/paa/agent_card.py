"""PAA A2A Agent Card - defines PAA's capabilities for A2A discovery."""

from __future__ import annotations

from a2a.types import AgentCard, AgentSkill, AgentCapabilities


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
        url="http://localhost:8000/api/v1/agents/paa",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True),
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
        skills=[
            AgentSkill(
                id="policy_checking",
                name="Policy Checking",
                description=(
                    "Check if a transaction complies with company policies. Uses RAG to retrieve "
                    "relevant policy documents and queries adaptive memory for exceptions."
                ),
                tags=["compliance", "policy", "rag"],
                inputModes=["application/json"],
                outputModes=["application/json"],
                examples=[
                    "Check if invoice complies with expense policy",
                    "Validate international transaction against policy",
                ],
            ),
            AgentSkill(
                id="compliance_evaluation",
                name="Compliance Evaluation",
                description=(
                    "Evaluate compliance using LLM with retrieved policies and learned exceptions. "
                    "Provides detailed reasoning and confidence assessment."
                ),
                tags=["compliance", "llm", "evaluation"],
                inputModes=["application/json"],
                outputModes=["application/json"],
                examples=[
                    "Evaluate invoice against retrieved policies",
                    "Assess compliance with confidence score",
                ],
            ),
        ],
    )

