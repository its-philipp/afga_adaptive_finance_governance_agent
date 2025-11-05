"""Orchestrator for connecting TAA, PAA, and EMA via A2A + MCP protocols.

Hybrid Architecture:
- A2A (Agent-to-Agent): Inter-agent communication (TAA ↔ PAA, TAA ↔ EMA)
- MCP (Model Context Protocol): Agent ↔ Resources/Tools (PAA ↔ Policies, EMA ↔ Memory)

This demonstrates both industry-standard protocols working together.
In production, agents would be deployed as separate services with HTTP-based A2A.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Optional
import uuid
from datetime import datetime
import time

from ..core.observability import Observability
from ..db.memory_db import MemoryDatabase
from ..mcp_servers import PolicyMCPServer, MemoryMCPServer
from ..models.schemas import (
    Invoice,
    HITLFeedback,
    TransactionResult,
    DecisionType,
)
from .taa import TransactionAuditorAgent
from .paa import PolicyAdherenceAgent
from .ema import ExceptionManagerAgent


logger = logging.getLogger(__name__)


class AFGAOrchestrator:
    """Orchestrator for AFGA multi-agent system.
    
    Hybrid Architecture:
    - A2A Protocol: Coordinates TAA, PAA, and EMA (inter-agent communication)
    - MCP Protocol: PAA accesses policies, EMA manages memory (agent-to-resource/tools)
    
    This demonstrates both protocols working together as recommended by MIT GenAI research.
    """

    def __init__(
        self,
        observability: Optional[Observability] = None,
        memory_db: Optional[MemoryDatabase] = None,
    ):
        """Initialize orchestrator with all three agents and MCP servers."""
        self.observability = observability or Observability()
        self.memory_db = memory_db or MemoryDatabase()
        
        # Initialize MCP servers
        self.policy_mcp = PolicyMCPServer()
        self.memory_mcp = MemoryMCPServer()
        
        # Initialize agents with MCP servers
        self.taa = TransactionAuditorAgent(observability=self.observability)
        self.paa = PolicyAdherenceAgent(
            policy_mcp_server=self.policy_mcp,
            observability=self.observability
        )
        self.ema = ExceptionManagerAgent(
            memory_mcp_server=self.memory_mcp,
            observability=self.observability
        )
        
        logger.info("AFGA Orchestrator initialized with TAA, PAA, EMA + MCP servers (hybrid A2A+MCP architecture)")

    def process_transaction(
        self,
        invoice: Invoice,
        trace_id: Optional[str] = None,
    ) -> TransactionResult:
        """Process a transaction through the full AFGA workflow.
        
        Args:
            invoice: Invoice to process
            trace_id: Optional trace ID for observability
            
        Returns:
            TransactionResult with final decision and audit trail
        """
        if not trace_id:
            trace_id = str(uuid.uuid4())

        start_time = time.time()
        
        logger.info(f"Processing transaction {invoice.invoice_id} [trace: {trace_id}]")
        
        with self.observability.trace(
            name="transaction_processing",
            metadata={"invoice_id": invoice.invoice_id, "vendor": invoice.vendor, "amount": invoice.amount},
        ) as observed_trace_id:
            # Step 1: TAA processes transaction
            taa_state = self.taa.process_transaction_sync(invoice, trace_id=trace_id)
            
            # Step 2: Simulate A2A call to PAA (in-process for MVP)
            # In production, this would be an actual A2A HTTP call
            logger.info(f"Simulating A2A call: TAA → PAA for {invoice.invoice_id}")
            
            if self.observability:
                self.observability.log_a2a_communication(
                    trace_id=trace_id,
                    from_agent="TAA",
                    to_agent="PAA",
                    message={"invoice_id": invoice.invoice_id, "action": "check_compliance"}
                )
            
            paa_state = self.paa.check_compliance_sync(invoice, trace_id=trace_id)
            paa_result = paa_state.get("compliance_result")
            
            # Update TAA state with PAA response
            taa_state["paa_response"] = paa_result
            taa_state["paa_request_sent"] = True
            
            # Re-evaluate TAA decision with PAA response
            taa_state = self._update_taa_decision(taa_state)
            
            # Step 3: Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Step 4: Build TransactionResult
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
            )
            
            # Step 5: Save to database
            self.memory_db.save_transaction(result)
            
            logger.info(
                f"Transaction {invoice.invoice_id} processed: "
                f"{result.final_decision.value} in {processing_time_ms}ms"
            )
            
            return result

    def process_hitl_feedback(
        self,
        feedback: HITLFeedback,
        invoice: Invoice,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process human-in-the-loop feedback through EMA.
        
        Args:
            feedback: HITL feedback from human
            invoice: Original invoice
            trace_id: Optional trace ID
            
        Returns:
            EMA processing result
        """
        if not trace_id:
            trace_id = str(uuid.uuid4())

        logger.info(f"Processing HITL feedback for {feedback.transaction_id} [trace: {trace_id}]")
        
        with self.observability.trace(
            name="hitl_feedback_processing",
            metadata={"transaction_id": feedback.transaction_id, "human_decision": feedback.human_decision.value},
        ) as observed_trace_id:
            # Simulate A2A call to EMA
            logger.info(f"Simulating A2A call: TAA → EMA for {feedback.transaction_id}")
            
            if self.observability:
                self.observability.log_a2a_communication(
                    trace_id=trace_id,
                    from_agent="TAA",
                    to_agent="EMA",
                    message={"transaction_id": feedback.transaction_id, "action": "process_hitl"}
                )
            
            ema_state = self.ema.process_hitl_feedback_sync(feedback, invoice, trace_id=trace_id)
            
            # Update transaction in database with HITL feedback
            reasoning = f"Human override: {feedback.reasoning}"
            self.memory_db.update_transaction_after_hitl(
                transaction_id=feedback.transaction_id,
                human_decision=feedback.human_decision.value,
                final_reasoning=reasoning
            )
            
            # Recalculate KPIs
            self.memory_db.calculate_and_save_kpis()
            
            logger.info(f"HITL feedback processed for {feedback.transaction_id}")
            
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

    def _merge_audit_trails(self, taa_state: Dict[str, Any], paa_state: Dict[str, Any]) -> list[str]:
        """Merge audit trails from TAA and PAA."""
        taa_trail = taa_state.get("audit_trail", [])
        paa_trail = paa_state.get("audit_trail", [])
        
        # Filter out obsolete warnings from TAA if PAA actually ran
        warnings_to_remove = [
            "⚠️ PAA A2A integration pending - using mock response",
            "⚠️ No PAA response available (using risk-based decision)",
            "Delegating to PAA for policy check (A2A)",  # Replace with cleaner message
        ]
        
        # Interleave trails chronologically
        merged = []
        for step in taa_trail:
            # Skip warning messages if PAA actually executed
            if paa_trail and any(warning in step for warning in warnings_to_remove):
                continue
            merged.append(f"[TAA] {step}")
        
        for step in paa_trail:
            merged.append(f"[PAA] {step}")
        
        return merged

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID."""
        return self.memory_db.get_transaction(transaction_id)

    def get_recent_transactions(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Get recent transactions."""
        return self.memory_db.get_recent_transactions(limit)

    def get_kpis(self, start_date: Optional[str] = None, end_date: Optional[str] = None):
        """Get KPI metrics."""
        return self.memory_db.get_kpis(start_date, end_date)

    def calculate_current_kpis(self):
        """Calculate and return current KPIs."""
        return self.memory_db.calculate_and_save_kpis()

    def get_memory_stats(self):
        """Get adaptive memory statistics."""
        return self.ema.memory_manager.get_memory_stats()

    def get_agent_cards(self) -> Dict[str, Any]:
        """Get A2A agent cards for all agents."""
        from .taa import get_taa_agent_card
        from .paa import get_paa_agent_card
        from .ema import get_ema_agent_card
        
        return {
            "taa": get_taa_agent_card().dict(),
            "paa": get_paa_agent_card().dict(),
            "ema": get_ema_agent_card().dict(),
        }

