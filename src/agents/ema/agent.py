"""EMA (Exception Manager Agent) - LangGraph implementation."""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END

from ...core.config import get_settings
from ...core.observability import Observability
from ...governance import GovernedLLMClient
from ...mcp_servers.memory_server import MemoryMCPServer
from ...models.schemas import HITLFeedback, Invoice
from .state import ExceptionManagerState


logger = logging.getLogger(__name__)


class ExceptionManagerAgent:
    """Exception Manager Agent - Handles HITL feedback and updates adaptive memory.
    
    Uses MCP (Model Context Protocol) to access memory tools,
    providing a clean interface for LLM-driven memory management operations.
    """

    def __init__(
        self,
        memory_mcp_server: MemoryMCPServer | None = None,
        observability: Observability | None = None,
    ):
        self.settings = get_settings()
        self.memory_mcp = memory_mcp_server or MemoryMCPServer()
        self.memory_manager = self.memory_mcp.memory_manager  # Access underlying manager
        self.observability = observability or Observability()
        self.llm_client = GovernedLLMClient(agent_name="EMA")  # Governed LLM with AI governance
        
        # Build LangGraph workflow
        self.graph = self._build_graph()
        logger.info("EMA initialized with MCP memory server and AI governance")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for EMA."""
        workflow = StateGraph(ExceptionManagerState)

        # Define nodes
        workflow.add_node("receive_hitl_request", self.receive_hitl_request)
        workflow.add_node("analyze_correction", self.analyze_correction)
        workflow.add_node("update_memory", self.update_memory)
        workflow.add_node("calculate_hcr", self.calculate_hcr)

        # Define edges
        workflow.set_entry_point("receive_hitl_request")
        workflow.add_edge("receive_hitl_request", "analyze_correction")
        
        # Conditional edge: only update memory if should_learn is True
        workflow.add_conditional_edges(
            "analyze_correction",
            lambda state: "update_memory" if state.get("should_learn", False) else "calculate_hcr",
            {
                "update_memory": "update_memory",
                "calculate_hcr": "calculate_hcr",
            }
        )
        
        workflow.add_edge("update_memory", "calculate_hcr")
        workflow.add_edge("calculate_hcr", END)

        return workflow.compile()

    def receive_hitl_request(self, state: ExceptionManagerState) -> ExceptionManagerState:
        """Node 1: Receive HITL feedback."""
        feedback = state["feedback"]
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append(f"EMA received HITL feedback for transaction {feedback.transaction_id}")
        audit_trail.append(f"Original decision: {feedback.original_decision}, Human decision: {feedback.human_decision}")
        
        logger.info(f"EMA processing HITL feedback for {feedback.transaction_id}")
        
        state["audit_trail"] = audit_trail
        return state

    def analyze_correction(self, state: ExceptionManagerState) -> ExceptionManagerState:
        """Node 2: Analyze the type of correction and determine if we should learn from it."""
        feedback = state["feedback"]
        invoice = state.get("invoice")
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("Analyzing correction type with LLM")

        llm_should_learn: bool | None = None

        # Use LLM to classify the correction
        prompt = f"""You are an AI compliance analyst. A human has overridden an automated decision.

Transaction Details:
- Invoice ID: {feedback.invoice_id}
- Original Decision: {feedback.original_decision}
- Human Decision: {feedback.human_decision}
- Human Reasoning: {feedback.reasoning}

Invoice Context:
- Vendor: {invoice.vendor if invoice else 'N/A'}
- Amount: ${invoice.amount if invoice else 'N/A'}
- Category: {invoice.category if invoice else 'N/A'}

Analyze this correction and determine:
1. Correction Type: Is this a "new_exception" (vendor/category specific rule), "policy_gap" (missing policy coverage), or "one_time_override" (special circumstances)?
2. Should Learn: Should the system learn from this correction to handle similar cases automatically in the future?
3. Exception Description: If we should learn, provide a concise description of the rule (1-2 sentences).

Respond in this format:
CORRECTION_TYPE: [new_exception|policy_gap|one_time_override]
SHOULD_LEARN: [yes|no]
DESCRIPTION: [your description]
REASONING: [brief explanation]
"""

        try:
            response = self.llm_client.completion(
                prompt=prompt,
                temperature=self.settings.ema_temperature,
                trace_id=state.get("trace_id", ""),
            )

            # Parse LLM response
            correction_type = "one_time_override"
            description = ""

            for line in response.split("\n"):
                if line.startswith("CORRECTION_TYPE:"):
                    correction_type = line.split(":", 1)[1].strip()
                elif line.startswith("SHOULD_LEARN:"):
                    llm_should_learn = "yes" in line.lower()
                elif line.startswith("DESCRIPTION:"):
                    description = line.split(":", 1)[1].strip()

            state["correction_type"] = correction_type
            state["exception_description"] = description or feedback.reasoning or "Learned exception"

            if self.observability:
                self.observability.log_llm_call(
                    trace_id=state.get("trace_id", ""),
                    prompt=prompt,
                    response=response,
                    model=self.settings.primary_model,
                )

        except Exception as e:
            logger.error(f"Error analyzing correction: {e}")
            state["correction_type"] = feedback.exception_type or "one_time_override"
            state["exception_description"] = feedback.reasoning or ""
            audit_trail.append(f"Error analyzing correction: {str(e)}")

        should_learn_final = feedback.should_create_exception or (llm_should_learn if llm_should_learn is not None else False)
        state["should_learn"] = should_learn_final
        audit_trail.append(
            f"Correction classified as: {state.get('correction_type', 'one_time_override')}, should_learn={should_learn_final}"
        )

        state["audit_trail"] = audit_trail
        return state

    def update_memory(self, state: ExceptionManagerState) -> ExceptionManagerState:
        """Node 3: Update adaptive memory via MCP tools.
        
        Uses MCP (Model Context Protocol) to call memory management tools,
        demonstrating how LLM agents can perform operations through standardized protocols.
        """
        feedback = state["feedback"]
        invoice = state.get("invoice")
        correction_type = state.get("correction_type", "one_time_override")
        description = state.get("exception_description", "") or feedback.reasoning or "Learned exception"
        audit_trail = state.get("audit_trail", [])

        audit_trail.append("Updating adaptive memory via MCP tools")

        try:
            # Use MCP tool to add exception
            # This provides a clean abstraction - EMA uses MCP interface
            exception_id = self.memory_mcp.add_exception_sync(
                vendor=invoice.vendor,
                category=invoice.category,
                rule_type=feedback.exception_type or correction_type,
                description=description,
                reason=feedback.reasoning
            )

            state["memory_update_id"] = exception_id
            audit_trail.append(f"Created memory exception via MCP: {exception_id}")
            audit_trail.append(f"Exception description: {description}")
            
            logger.info(f"Memory updated via MCP with exception {exception_id}")

        except Exception as e:
            logger.error(f"Error updating memory via MCP: {e}")
            state["memory_update_id"] = ""
            audit_trail.append(f"Error updating memory via MCP: {str(e)}")

        state["audit_trail"] = audit_trail
        return state

    def calculate_hcr(self, state: ExceptionManagerState) -> ExceptionManagerState:
        """Node 4: Update Human Correction Rate KPI."""
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("Updating H-CR KPI")

        try:
            # Trigger KPI recalculation (will be done by the KPI tracker service)
            state["hcr_updated"] = True
            audit_trail.append("H-CR KPI marked for update")
            
        except Exception as e:
            logger.error(f"Error updating H-CR: {e}")
            state["hcr_updated"] = False
            audit_trail.append(f"Error updating H-CR: {str(e)}")

        state["audit_trail"] = audit_trail
        return state

    async def process_hitl_feedback(
        self,
        feedback: HITLFeedback,
        invoice: Invoice,
        trace_id: str = "",
    ) -> ExceptionManagerState:
        """Process HITL feedback through the EMA workflow.
        
        Args:
            feedback: HITL feedback from human reviewer
            invoice: Original invoice data
            trace_id: Trace ID for observability
            
        Returns:
            Final state after processing
        """
        initial_state = ExceptionManagerState(
            feedback=feedback,
            invoice=invoice,
            audit_trail=[],
            trace_id=trace_id,
        )

        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        logger.info(f"EMA completed processing for {feedback.transaction_id}")
        return final_state

    def process_hitl_feedback_sync(
        self,
        feedback: HITLFeedback,
        invoice: Invoice,
        trace_id: str = "",
    ) -> ExceptionManagerState:
        """Synchronous version of process_hitl_feedback."""
        initial_state = ExceptionManagerState(
            feedback=feedback,
            invoice=invoice,
            audit_trail=[],
            trace_id=trace_id,
        )

        # Run the graph synchronously
        final_state = self.graph.invoke(initial_state)
        
        logger.info(f"EMA completed processing for {feedback.transaction_id}")
        return final_state

