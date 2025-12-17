"""EMA A2A Agent Card - defines EMA's capabilities for A2A discovery."""

from __future__ import annotations

from a2a.types import AgentCard, AgentSkill, AgentCapabilities


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
        url="http://localhost:8000/api/v1/agents/ema",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False, state_transition_history=True),
        defaultInputModes=["application/json"],
        defaultOutputModes=["application/json"],
        skills=[
            AgentSkill(
                id="hitl_processing",
                name="HITL Processing",
                description=(
                    "Process HITL feedback when a human overrides an automated decision. "
                    "Analyzes the correction type and determines if the system should learn from it."
                ),
                tags=["hitl", "learning", "feedback"],
                inputModes=["application/json"],
                outputModes=["application/json"],
                examples=[
                    "Process feedback when a human overrides an approval decision",
                    "Learn from policy gap corrections",
                ],
            ),
            AgentSkill(
                id="memory_management",
                name="Memory Management",
                description=(
                    "Manage the adaptive memory: add, query, and update learned exceptions. "
                    "Provides Context Retention Score (CRS) and memory statistics."
                ),
                tags=["memory", "learning", "exceptions"],
                inputModes=["application/json"],
                outputModes=["application/json"],
                examples=[
                    "Query exceptions for a specific vendor",
                    "Get memory statistics",
                ],
            ),
        ],
    )
