from __future__ import annotations

from typing import Callable

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from starlette.applications import Starlette

from ..agents.ema.agent_executor import EMAExecutor
from ..agents.paa.agent_executor import PAAExecutor
from ..core.config import Settings


def _build_agent_card(
    *,
    name: str,
    description: str,
    url: str,
    skill_id: str,
    skill_name: str,
    skill_description: str,
) -> AgentCard:
    capabilities = AgentCapabilities(streaming=True)
    skill = AgentSkill(
        id=skill_id,
        name=skill_name,
        description=skill_description,
        tags=["compliance", "governance"],
        examples=["Process a finance transaction request."],
    )

    normalized_url = url if url.endswith("/") else f"{url}/"

    return AgentCard(
        name=name,
        description=description,
        url=normalized_url,
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=capabilities,
        skills=[skill],
    )


def _build_server(
    *,
    executor_factory: Callable[[], object],
    agent_card: AgentCard,
) -> Starlette:
    request_handler = DefaultRequestHandler(
        agent_executor=executor_factory(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    return server.build()


def create_paa_a2a_app(settings: Settings) -> Starlette:
    base_url = settings.a2a_base_url.rstrip("/") + settings.a2a_paa_path
    agent_card = _build_agent_card(
        name="Policy Adherence Agent (PAA)",
        description="Performs policy compliance checks with adaptive memory.",
        url=base_url,
        skill_id="policy_checking",
        skill_name="Policy Checking",
        skill_description=(
            "Evaluate a finance transaction against company policies using RAG and adaptive memory."
        ),
    )
    return _build_server(executor_factory=PAAExecutor, agent_card=agent_card)


def create_ema_a2a_app(settings: Settings) -> Starlette:
    base_url = settings.a2a_base_url.rstrip("/") + settings.a2a_ema_path
    agent_card = _build_agent_card(
        name="Exception Manager Agent (EMA)",
        description="Processes human-in-the-loop feedback and updates adaptive memory.",
        url=base_url,
        skill_id="hitl_feedback",
        skill_name="HITL Feedback Processing",
        skill_description=(
            "Ingest human overrides, classify exceptions, and update adaptive memory with learned rules."
        ),
    )
    return _build_server(executor_factory=EMAExecutor, agent_card=agent_card)

