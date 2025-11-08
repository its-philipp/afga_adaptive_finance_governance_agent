"""TAA A2A Agent Card - defines TAA's capabilities for A2A discovery."""

from __future__ import annotations

from a2a.types import AgentCard, AgentSkill, AgentCapabilities


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
        url="http://localhost:8000/api/v1/agents/taa",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=True, state_transition_history=True),
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
        skills=[
            AgentSkill(
                id="transaction_audit",
                name="Transaction Audit",
                description=(
                    "Process a financial transaction through risk assessment and policy checking. "
                    "Delegates to PAA and EMA as needed, returns final decision."
                ),
                tags=["audit", "orchestration", "risk"],
                inputModes=["application/json"],
                outputModes=["application/json"],
                examples=[
                    "Audit invoice for approval decision",
                    "Process transaction with risk assessment",
                ],
            ),
            AgentSkill(
                id="risk_scoring",
                name="Risk Scoring",
                description=(
                    "Assess the risk level of a transaction based on amount, vendor reputation, "
                    "missing documentation, and other factors."
                ),
                tags=["risk", "scoring", "assessment"],
                inputModes=["application/json"],
                outputModes=["application/json"],
                examples=[
                    "Score transaction risk level",
                    "Assess vendor reputation risk",
                ],
            ),
        ],
    )

