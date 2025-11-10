"""Orchestrator bridging TAA, PAA, and EMA via hybrid A2A + MCP architecture."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import httpx
from a2a.client import A2AClient
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
)

from ..core.config import get_settings
from ..core.observability import Observability
from ..db.memory_db import MemoryDatabase
from ..mcp_servers import MemoryMCPServer, PolicyMCPServer
from ..models.schemas import (
    DecisionType,
    HITLFeedback,
    Invoice,
    PolicyCheckResult,
    TransactionResult,
)
from .ema import ExceptionManagerAgent
from .paa import PolicyAdherenceAgent
from .taa import TransactionAuditorAgent


logger = logging.getLogger(__name__)


class AFGAOrchestrator:
    """Coordinate AFGA agents using HTTP-based A2A with MCP-backed resources."""

    def __init__(
        self,
        observability: Optional[Observability] = None,
        memory_db: Optional[MemoryDatabase] = None,
    ):
        self.settings = get_settings()
        self.observability = observability or Observability()
        self.memory_db = memory_db or MemoryDatabase()
        
        self.a2a_enabled = self.settings.a2a_enabled
        self._paa_endpoint = self._compose_endpoint(self.settings.a2a_paa_path)
        self._ema_endpoint = self._compose_endpoint(self.settings.a2a_ema_path)
        self._paa_card: AgentCard | None = None
        self._ema_card: AgentCard | None = None

        # MCP servers remain available for direct policy browsing and memory stats.
        self.policy_mcp = PolicyMCPServer()
        self.memory_mcp = MemoryMCPServer()
        
        self.taa = TransactionAuditorAgent(observability=self.observability)
        self.paa: PolicyAdherenceAgent | None = None
        self.ema: ExceptionManagerAgent | None = None

        if self.a2a_enabled:
            try:
                self._paa_card = self._resolve_agent_card(self._paa_endpoint)
                self._ema_card = self._resolve_agent_card(self._ema_endpoint)
                logger.info("Initialized HTTP A2A clients for PAA and EMA.")
            except Exception:
                logger.exception(
                    "Failed to initialize HTTP-based A2A clients; falling back to in-process execution."
                )
                self.a2a_enabled = False

        if not self.a2a_enabled:
            self.paa = PolicyAdherenceAgent(
                policy_mcp_server=self.policy_mcp,
                observability=self.observability,
            )
            self.ema = ExceptionManagerAgent(
                memory_mcp_server=self.memory_mcp,
                observability=self.observability,
            )
            logger.info("Initialized in-process PAA and EMA agents.")

    def process_transaction(
        self,
        invoice: Invoice,
        trace_id: Optional[str] = None,
        source_document_path: Optional[str] = None,
    ) -> TransactionResult:
        if not trace_id:
            trace_id = str(uuid.uuid4())

        start_time = time.time()
        logger.info("Processing transaction %s [trace: %s]", invoice.invoice_id, trace_id)
        
        with self.observability.trace(
            name="transaction_processing",
            metadata={
                "invoice_id": invoice.invoice_id,
                "vendor": invoice.vendor,
                "amount": invoice.amount,
            },
        ):
            taa_state = self.taa.process_transaction_sync(invoice, trace_id=trace_id)
            
            if self.observability:
                self.observability.log_a2a_communication(
                    trace_id=trace_id,
                    from_agent="TAA",
                    to_agent="PAA",
                    message={
                        "invoice_id": invoice.invoice_id,
                        "action": "check_compliance",
                    },
                )
            
            if self.a2a_enabled and self._paa_card:
                paa_state = self._invoke_paa_via_a2a(invoice, trace_id)
            elif self.paa:
                paa_state = self.paa.check_compliance_sync(invoice, trace_id=trace_id)
            else:
                raise RuntimeError("No Policy Adherence Agent available.")

            paa_result = paa_state.get("compliance_result")
            taa_state["paa_response"] = paa_result
            taa_state["paa_request_sent"] = True
            taa_state = self._update_taa_decision(taa_state)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            transaction_id = str(uuid.uuid4())[:8]
            
            result = TransactionResult(
                transaction_id=transaction_id,
                invoice=invoice,
                risk_assessment=taa_state.get("risk_assessment"),
                policy_check=paa_result,
                final_decision=taa_state.get("final_decision", DecisionType.HITL),
                decision_reasoning=taa_state.get("decision_reasoning", "Unknown"),
                human_override=False,
                processing_time_ms=processing_time_ms,
                audit_trail=self._merge_audit_trails(taa_state, paa_state),
                trace_id=trace_id,
                created_at=datetime.now(),
                source_document_path=source_document_path,
            )
            
            self.memory_db.save_transaction(result)
            logger.info(
                "Transaction %s processed: %s in %sms",
                invoice.invoice_id,
                result.final_decision.value,
                processing_time_ms,
            )
            return result

    def process_hitl_feedback(
        self,
        feedback: HITLFeedback,
        invoice: Invoice,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not trace_id:
            trace_id = str(uuid.uuid4())

        logger.info("Processing HITL feedback for %s [trace: %s]", feedback.transaction_id, trace_id)
        
        with self.observability.trace(
            name="hitl_feedback_processing",
            metadata={
                "transaction_id": feedback.transaction_id,
                "human_decision": feedback.human_decision.value,
            },
        ):
            if self.observability:
                self.observability.log_a2a_communication(
                    trace_id=trace_id,
                    from_agent="TAA",
                    to_agent="EMA",
                    message={
                        "transaction_id": feedback.transaction_id,
                        "action": "process_hitl",
                    },
                )
            
            if self.a2a_enabled and self._ema_card:
                ema_state = self._invoke_ema_via_a2a(feedback, invoice, trace_id)
            elif self.ema:
                ema_state = self.ema.process_hitl_feedback_sync(
                    feedback, invoice, trace_id=trace_id
                )
            else:
                raise RuntimeError("No Exception Manager Agent available.")

            reasoning = f"Human override: {feedback.reasoning}"
            self.memory_db.update_transaction_after_hitl(
                transaction_id=feedback.transaction_id,
                human_decision=feedback.human_decision.value,
                final_reasoning=reasoning,
            )
            self.memory_db.calculate_and_save_kpis()
            logger.info("HITL feedback processed for %s", feedback.transaction_id)
            
            return {
                "transaction_id": feedback.transaction_id,
                "ema_result": ema_state,
                "memory_updated": bool(ema_state.get("memory_update_id")),
                "hcr_updated": ema_state.get("hcr_updated", False),
            }

    def _update_taa_decision(self, taa_state: Dict[str, Any]) -> Dict[str, Any]:
        """Update TAA decision based on PAA response."""
        paa_response = taa_state.get("paa_response")
        risk_assessment = taa_state.get("risk_assessment")
        audit_trail = taa_state.get("audit_trail", [])

        if paa_response:
            manual_exception_labels = getattr(paa_response, "manual_exception_labels", [])
            manual_exception_ids = getattr(paa_response, "manual_exception_ids", [])
            if manual_exception_ids:
                label_text = ", ".join(manual_exception_labels or manual_exception_ids)
                taa_state["final_decision"] = DecisionType.HITL
                taa_state["decision_reasoning"] = (
                    "Manual review required due to learned exception(s): " + label_text
                )
                taa_state["requires_hitl"] = True
                audit_trail.append(
                    "TAA: Manual review required based on learned exception(s)"
                )
                taa_state["audit_trail"] = audit_trail
                return taa_state

            # If PAA says non-compliant, reject
            if not paa_response.is_compliant:
                taa_state["final_decision"] = DecisionType.REJECTED
                taa_state["decision_reasoning"] = f"Policy violation: {', '.join(paa_response.violated_policies)}"
                taa_state["requires_hitl"] = False
                audit_trail.append("TAA: Decision updated based on PAA - REJECTED")
            # If PAA says compliant with high confidence, approve
            elif paa_response.confidence > 0.8:
                taa_state["final_decision"] = DecisionType.APPROVED
                taa_state["decision_reasoning"] = f"Compliant with policies (confidence: {paa_response.confidence:.2f})"
                taa_state["requires_hitl"] = False
                audit_trail.append("TAA: Decision updated based on PAA - APPROVED")
            # If PAA uncertain, escalate to HITL
            else:
                taa_state["final_decision"] = DecisionType.HITL
                taa_state["decision_reasoning"] = f"Low confidence ({paa_response.confidence:.2f}), requires human review"
                taa_state["requires_hitl"] = True
                audit_trail.append("TAA: Decision updated based on PAA - HITL required")

        taa_state["audit_trail"] = audit_trail
        return taa_state

    def _merge_audit_trails(
        self,
        taa_state: Dict[str, Any],
        paa_state: Dict[str, Any],
    ) -> list[str]:
        taa_trail = taa_state.get("audit_trail", [])
        paa_trail = paa_state.get("audit_trail", [])
        
        warnings_to_remove = {
            "⚠️ PAA A2A integration pending - using mock response",
            "⚠️ No PAA response available (using risk-based decision)",
            "Delegating to PAA for policy check (A2A)",
            "Preparing for PAA policy check (A2A)",
        }
        
        merged: list[str] = []
        for step in taa_trail:
            if paa_trail and any(marker in step for marker in warnings_to_remove):
                continue
            merged.append(f"[TAA] {step}")
        
        for step in paa_trail:
            merged.append(f"[PAA] {step}")
        
        return merged

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        return self.memory_db.get_transaction(transaction_id)

    def get_recent_transactions(self, limit: int = 10) -> list[Dict[str, Any]]:
        return self.memory_db.get_recent_transactions(limit)

    def get_kpis(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        return self.memory_db.get_kpis(start_date, end_date)

    def calculate_current_kpis(self):
        return self.memory_db.calculate_and_save_kpis()

    def get_memory_stats(self):
        if self.ema:
            return self.ema.memory_manager.get_memory_stats()

        # When running via A2A, memory updates still flow through the shared SQLite database
        # so we can safely read stats directly from the memory DB.
        return self.memory_db.get_memory_stats()

    def get_agent_cards(self) -> Dict[str, Any]:
        from .taa import get_taa_agent_card
        from .paa import get_paa_agent_card
        from .ema import get_ema_agent_card

        cards: Dict[str, Any] = {"taa": get_taa_agent_card().model_dump(mode="json")}
        if self.a2a_enabled:
            cards["paa"] = (
                self._paa_card.model_dump(mode="json") if self._paa_card else {}
            )
            cards["paa"]["endpoint"] = self._paa_endpoint
            cards["paa"]["agentCardUrl"] = urljoin(self._paa_endpoint, ".well-known/agent-card.json")
            cards["ema"] = (
                self._ema_card.model_dump(mode="json") if self._ema_card else {}
            )
            cards["ema"]["endpoint"] = self._ema_endpoint
            cards["ema"]["agentCardUrl"] = urljoin(self._ema_endpoint, ".well-known/agent-card.json")
        else:
            fallback_paa_endpoint = self._compose_endpoint(self.settings.a2a_paa_path)
            fallback_ema_endpoint = self._compose_endpoint(self.settings.a2a_ema_path)
            cards["paa"] = get_paa_agent_card().model_dump(mode="json")
            cards["paa"]["endpoint"] = fallback_paa_endpoint
            cards["paa"]["agentCardUrl"] = urljoin(fallback_paa_endpoint, ".well-known/agent-card.json")
            cards["ema"] = get_ema_agent_card().model_dump(mode="json")
            cards["ema"]["endpoint"] = fallback_ema_endpoint
            cards["ema"]["agentCardUrl"] = urljoin(fallback_ema_endpoint, ".well-known/agent-card.json")
        return cards

    # --- A2A helpers ---

    def _resolve_agent_card(self, endpoint: str) -> AgentCard:
        headers = self._build_http_kwargs().get("headers")
        card_url = urljoin(endpoint, ".well-known/agent-card.json")
        with httpx.Client(timeout=self.settings.a2a_request_timeout, headers=headers) as client:
            response = client.get(card_url)
            response.raise_for_status()
            card_data = response.json()
        return AgentCard.model_validate(card_data)

    def _build_http_kwargs(self) -> Dict[str, Any]:
        headers = {}
        if self.settings.a2a_api_key:
            headers["Authorization"] = f"Bearer {self.settings.a2a_api_key}"
        return {"headers": headers} if headers else {}

    def _build_send_message_request(self, payload: Dict[str, Any]) -> SendMessageRequest:
        message_id = str(uuid.uuid4())
        params = MessageSendParams.model_validate(
            {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": json.dumps(payload)}],
                    "messageId": message_id,
                }
            }
        )
        return SendMessageRequest(id=message_id, params=params)

    def _send_a2a_request(
        self,
        card: AgentCard,
        url: str,
        payload: Dict[str, Any],
    ) -> Task:
        if card is None:
            raise RuntimeError("Agent card not initialized for A2A request.")

        async def _send() -> Task:
            async with httpx.AsyncClient(
                timeout=self.settings.a2a_request_timeout
            ) as client:
                client_instance = A2AClient(client, card, url=url)
                request = self._build_send_message_request(payload)
                response: SendMessageResponse = await client_instance.send_message(
                    request, http_kwargs=self._build_http_kwargs()
                )
            logger.info(
                "A2A response for %s: %s",
                url,
                response.model_dump(mode="json"),
            )
            return self._ensure_task_response(response)

        return asyncio.run(_send())

    @staticmethod
    def _ensure_task_response(response: SendMessageResponse) -> Task:
        root = response.root
        if not isinstance(root, SendMessageSuccessResponse):
            raise RuntimeError("A2A call returned an error response.")

        result = root.result
        if isinstance(result, Task):
            return result
        if isinstance(result, Message):
            payload = result.model_dump(mode="json")
            text_parts = [
                part.get("text", "")
                for part in payload.get("parts", [])
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            message_text = " | ".join(filter(None, text_parts)) or json.dumps(payload)
            logger.error("A2A call returned message instead of task: %s", message_text)
            raise RuntimeError(f"A2A call returned message result: {message_text}")
        logger.error(
            "A2A call returned unexpected type %s with payload %s",
            type(result),
            getattr(result, "model_dump", lambda **_: str(result))(mode="json"),
        )
        raise RuntimeError("A2A call did not return a Task result.")

    @staticmethod
    def _extract_artifact(task: Task, artifact_name: str) -> Dict[str, Any]:
        if not task.artifacts:
            raise RuntimeError(f"No artifacts returned (expected {artifact_name}).")

        for artifact in task.artifacts:
            if artifact.name and artifact.name != artifact_name:
                continue
            for part in artifact.parts:
                text = getattr(part.root, "text", None)
                if text:
                    return json.loads(text)

        raise RuntimeError(f"Artifact {artifact_name} not found in A2A task result.")

    def _invoke_paa_via_a2a(self, invoice: Invoice, trace_id: str) -> Dict[str, Any]:
        if self._paa_card is None:
            raise RuntimeError("PAA agent card not initialized.")

        task = self._send_a2a_request(
            self._paa_card,
            self._paa_endpoint,
            {"invoice": invoice.model_dump(), "trace_id": trace_id},
        )
        payload = self._extract_artifact(task, "paa_compliance_result")

        compliance_payload = payload.get("compliance_result")
        if not compliance_payload:
            raise RuntimeError("PAA artifact missing compliance_result payload.")

        compliance_result = PolicyCheckResult.model_validate(compliance_payload)
        audit_trail = payload.get("audit_trail", [])
        
        return {
            "compliance_result": compliance_result,
            "audit_trail": audit_trail,
            "hallucination_warnings": payload.get("hallucination_warnings", []),
        }

    def _invoke_ema_via_a2a(
        self,
        feedback: HITLFeedback,
        invoice: Invoice,
        trace_id: str,
    ) -> Dict[str, Any]:
        if self._ema_card is None:
            raise RuntimeError("EMA agent card not initialized.")

        task = self._send_a2a_request(
            self._ema_card,
            self._ema_endpoint,
            {
                "feedback": feedback.model_dump(),
                "invoice": invoice.model_dump(),
                "trace_id": trace_id,
            },
        )
        return self._extract_artifact(task, "ema_result")

    def _compose_endpoint(self, agent_path: str) -> str:
        base = self.settings.a2a_base_url.rstrip("/")
        path = agent_path.lstrip("/")
        endpoint = f"{base}/{path}"
        return endpoint if endpoint.endswith("/") else f"{endpoint}/"

