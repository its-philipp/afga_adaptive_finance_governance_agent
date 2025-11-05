"""TAA (Transaction Auditor Agent) - LangGraph implementation."""

from __future__ import annotations

import logging
from typing import Optional

from langgraph.graph import StateGraph, END

from ...core.config import get_settings
from ...core.observability import Observability
from ...models.schemas import Invoice, PolicyCheckResult, DecisionType
from ...services.risk_scorer import RiskScorer
from .state import TransactionAuditorState


logger = logging.getLogger(__name__)


class TransactionAuditorAgent:
    """Transaction Auditor Agent - Orchestrates transaction processing."""

    def __init__(
        self,
        risk_scorer: RiskScorer | None = None,
        observability: Observability | None = None,
    ):
        self.settings = get_settings()
        self.risk_scorer = risk_scorer or RiskScorer()
        self.observability = observability or Observability()
        
        # PAA and EMA clients will be injected during A2A integration
        self.paa_client = None  # Will be set in orchestrator
        self.ema_client = None  # Will be set in orchestrator
        
        # Build LangGraph workflow
        self.graph = self._build_graph()
        logger.info("TAA initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for TAA."""
        workflow = StateGraph(TransactionAuditorState)

        # Define nodes
        workflow.add_node("receive_transaction", self.receive_transaction)
        workflow.add_node("assess_risk", self.assess_risk)
        workflow.add_node("delegate_to_paa", self.delegate_to_paa)
        workflow.add_node("evaluate_paa_response", self.evaluate_paa_response)
        workflow.add_node("make_final_decision", self.make_final_decision)
        workflow.add_node("log_audit_trail", self.log_audit_trail)

        # Define edges
        workflow.set_entry_point("receive_transaction")
        workflow.add_edge("receive_transaction", "assess_risk")
        workflow.add_edge("assess_risk", "delegate_to_paa")
        workflow.add_edge("delegate_to_paa", "evaluate_paa_response")
        workflow.add_edge("evaluate_paa_response", "make_final_decision")
        workflow.add_edge("make_final_decision", "log_audit_trail")
        workflow.add_edge("log_audit_trail", END)

        return workflow.compile()

    def receive_transaction(self, state: TransactionAuditorState) -> TransactionAuditorState:
        """Node 1: Receive and validate incoming transaction."""
        invoice = state["invoice"]
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append(f"TAA received transaction: {invoice.invoice_id}")
        audit_trail.append(f"Vendor: {invoice.vendor}, Amount: ${invoice.amount}, Category: {invoice.category}")
        
        logger.info(f"TAA processing transaction {invoice.invoice_id}")
        
        state["audit_trail"] = audit_trail
        return state

    def assess_risk(self, state: TransactionAuditorState) -> TransactionAuditorState:
        """Node 2: Perform risk assessment."""
        invoice = state["invoice"]
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("Performing risk assessment")

        try:
            risk_assessment = self.risk_scorer.assess_risk(invoice)
            state["risk_assessment"] = risk_assessment
            
            audit_trail.append(
                f"Risk assessed: {risk_assessment.risk_level.value} "
                f"(score: {risk_assessment.risk_score:.1f}/100)"
            )
            audit_trail.append(f"Risk factors: {', '.join(risk_assessment.risk_factors)}")
            
            if self.observability:
                self.observability.log_agent_step(
                    trace_id=state.get("trace_id", ""),
                    agent_name="TAA",
                    step_name="assess_risk",
                    input_data={"invoice_id": invoice.invoice_id},
                    output_data=risk_assessment.model_dump(),
                )

        except Exception as e:
            logger.error(f"Error assessing risk: {e}")
            audit_trail.append(f"Error assessing risk: {str(e)}")

        state["audit_trail"] = audit_trail
        return state

    def delegate_to_paa(self, state: TransactionAuditorState) -> TransactionAuditorState:
        """Node 3: Delegate to Policy Adherence Agent via A2A."""
        invoice = state["invoice"]
        risk_assessment = state.get("risk_assessment")
        audit_trail = state.get("audit_trail", [])
        
        # Note: A2A delegation is handled by the orchestrator
        # This node prepares the state for PAA delegation
        audit_trail.append("Preparing for PAA policy check (A2A)")
        state["paa_request_sent"] = True
        
        if self.observability:
            self.observability.log_a2a_communication(
                trace_id=state.get("trace_id", ""),
                from_agent="TAA",
                to_agent="PAA",
                message={"invoice_id": invoice.invoice_id, "risk_level": risk_assessment.risk_level.value if risk_assessment else "unknown"},
            )

        state["audit_trail"] = audit_trail
        return state

    def evaluate_paa_response(self, state: TransactionAuditorState) -> TransactionAuditorState:
        """Node 4: Evaluate PAA's policy check response."""
        audit_trail = state.get("audit_trail", [])
        paa_response = state.get("paa_response")
        
        audit_trail.append("Evaluating PAA response")

        if paa_response:
            if paa_response.is_compliant:
                audit_trail.append(f"✅ Compliant (PAA confidence: {paa_response.confidence:.2f})")
            else:
                audit_trail.append(f"❌ Non-compliant")
                if paa_response.violated_policies:
                    audit_trail.append(f"Violated policies: {', '.join(paa_response.violated_policies)}")
            
            if paa_response.applied_exceptions:
                audit_trail.append(f"✅ Applied {len(paa_response.applied_exceptions)} learned exception(s)")
        else:
            # Orchestrator will provide PAA response
            audit_trail.append("Awaiting PAA response from orchestrator")

        state["audit_trail"] = audit_trail
        return state

    def make_final_decision(self, state: TransactionAuditorState) -> TransactionAuditorState:
        """Node 5: Make final approve/reject/HITL decision."""
        risk_assessment = state.get("risk_assessment")
        paa_response = state.get("paa_response")
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("Making final decision")

        # Decision logic
        if paa_response:
            # If PAA says non-compliant, reject
            if not paa_response.is_compliant:
                decision = DecisionType.REJECTED
                reasoning = f"Policy violation: {', '.join(paa_response.violated_policies)}"
                requires_hitl = False
            # If PAA says compliant with high confidence, approve
            elif paa_response.confidence > 0.8:
                decision = DecisionType.APPROVED
                reasoning = f"Compliant with policies (confidence: {paa_response.confidence:.2f})"
                requires_hitl = False
            # If PAA uncertain, escalate to HITL
            else:
                decision = DecisionType.HITL
                reasoning = f"Low confidence ({paa_response.confidence:.2f}), requires human review"
                requires_hitl = True
        else:
            # No PAA response - decide based on risk level
            if risk_assessment:
                if risk_assessment.risk_level.value in ["critical", "high"]:
                    decision = DecisionType.HITL
                    reasoning = f"High risk ({risk_assessment.risk_level.value}), requires human review"
                    requires_hitl = True
                elif risk_assessment.risk_level.value == "medium":
                    decision = DecisionType.HITL
                    reasoning = f"Medium risk, requires review. Risk factors: {', '.join(risk_assessment.risk_factors)}"
                    requires_hitl = True
                else:
                    decision = DecisionType.APPROVED
                    reasoning = f"Low risk ({risk_assessment.risk_level.value}), auto-approved"
                    requires_hitl = False
            else:
                # No risk assessment either - default to HITL
                decision = DecisionType.HITL
                reasoning = "Unable to assess risk or policy compliance, requires human review"
                requires_hitl = True

        state["final_decision"] = decision
        state["decision_reasoning"] = reasoning
        state["requires_hitl"] = requires_hitl
        
        audit_trail.append(f"Final decision: {decision.value}")
        audit_trail.append(f"Reasoning: {reasoning}")
        
        state["audit_trail"] = audit_trail
        return state

    def log_audit_trail(self, state: TransactionAuditorState) -> TransactionAuditorState:
        """Node 6: Log complete audit trail."""
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("TAA workflow completed")
        
        logger.info(f"TAA completed processing for {state['invoice'].invoice_id}")
        logger.debug(f"Audit trail: {audit_trail}")
        
        state["audit_trail"] = audit_trail
        return state

    async def process_transaction(
        self,
        invoice: Invoice,
        trace_id: str = "",
    ) -> TransactionAuditorState:
        """Process a transaction through the TAA workflow.
        
        Args:
            invoice: Invoice to process
            trace_id: Trace ID for observability
            
        Returns:
            Final state after processing
        """
        initial_state = TransactionAuditorState(
            invoice=invoice,
            trace_id=trace_id,
            audit_trail=[],
        )

        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        logger.info(f"TAA completed processing for {invoice.invoice_id}")
        return final_state

    def process_transaction_sync(
        self,
        invoice: Invoice,
        trace_id: str = "",
    ) -> TransactionAuditorState:
        """Synchronous version of process_transaction."""
        initial_state = TransactionAuditorState(
            invoice=invoice,
            trace_id=trace_id,
            audit_trail=[],
        )

        # Run the graph synchronously
        final_state = self.graph.invoke(initial_state)
        
        logger.info(f"TAA completed processing for {invoice.invoice_id}")
        return final_state

