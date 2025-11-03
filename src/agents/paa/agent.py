"""PAA (Policy Adherence Agent) - LangGraph implementation."""

from __future__ import annotations

import logging

from langgraph.graph import StateGraph, END

from ...agents.ema.memory_manager import MemoryManager
from ...core.config import get_settings
from ...core.observability import Observability
from ...core.openrouter_client import OpenRouterClient
from ...models.memory_schemas import MemoryQuery
from ...models.schemas import Invoice, PolicyCheckResult
from ...services.policy_retriever import PolicyRetriever
from .state import PolicyAdherenceState


logger = logging.getLogger(__name__)


class PolicyAdherenceAgent:
    """Policy Adherence Agent - Checks transactions against policies and memory."""

    def __init__(
        self,
        policy_retriever: PolicyRetriever | None = None,
        memory_manager: MemoryManager | None = None,
        observability: Observability | None = None,
    ):
        self.settings = get_settings()
        self.policy_retriever = policy_retriever or PolicyRetriever()
        self.memory_manager = memory_manager or MemoryManager()
        self.observability = observability or Observability()
        self.llm_client = OpenRouterClient()
        
        # Build LangGraph workflow
        self.graph = self._build_graph()
        logger.info("PAA initialized")

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for PAA."""
        workflow = StateGraph(PolicyAdherenceState)

        # Define nodes
        workflow.add_node("receive_request", self.receive_request)
        workflow.add_node("retrieve_policies", self.retrieve_policies)
        workflow.add_node("check_memory", self.check_memory)
        workflow.add_node("evaluate_compliance", self.evaluate_compliance)
        workflow.add_node("return_response", self.return_response)

        # Define edges
        workflow.set_entry_point("receive_request")
        workflow.add_edge("receive_request", "retrieve_policies")
        workflow.add_edge("retrieve_policies", "check_memory")
        workflow.add_edge("check_memory", "evaluate_compliance")
        workflow.add_edge("evaluate_compliance", "return_response")
        workflow.add_edge("return_response", END)

        return workflow.compile()

    def receive_request(self, state: PolicyAdherenceState) -> PolicyAdherenceState:
        """Node 1: Receive compliance check request from TAA."""
        invoice = state["invoice"]
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append(f"PAA received request for invoice {invoice.invoice_id}")
        audit_trail.append(f"Checking: {invoice.vendor}, ${invoice.amount}, {invoice.category}")
        
        logger.info(f"PAA checking compliance for {invoice.invoice_id}")
        
        state["audit_trail"] = audit_trail
        return state

    def retrieve_policies(self, state: PolicyAdherenceState) -> PolicyAdherenceState:
        """Node 2: Retrieve relevant policy documents."""
        invoice = state["invoice"]
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("Retrieving relevant policies (RAG)")

        try:
            relevant_policies = self.policy_retriever.retrieve_relevant_policies(invoice, top_k=5)
            state["retrieved_policies"] = relevant_policies
            
            policy_names = list(set(p["policy_name"] for p in relevant_policies))
            audit_trail.append(f"Retrieved {len(relevant_policies)} policy chunks from: {', '.join(policy_names)}")
            
            if self.observability:
                self.observability.log_agent_step(
                    trace_id=state.get("trace_id", ""),
                    agent_name="PAA",
                    step_name="retrieve_policies",
                    input_data={"invoice_id": invoice.invoice_id},
                    output_data={"retrieved_count": len(relevant_policies), "policies": policy_names},
                )

        except Exception as e:
            logger.error(f"Error retrieving policies: {e}")
            state["retrieved_policies"] = []
            audit_trail.append(f"Error retrieving policies: {str(e)}")

        state["audit_trail"] = audit_trail
        return state

    def check_memory(self, state: PolicyAdherenceState) -> PolicyAdherenceState:
        """Node 3: Query adaptive memory for learned exceptions."""
        invoice = state["invoice"]
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("Checking adaptive memory for exceptions")

        try:
            # Query memory for applicable exceptions
            exceptions = self.memory_manager.query_applicable_exceptions(invoice)
            state["memory_exceptions"] = exceptions
            
            if exceptions:
                audit_trail.append(f"Found {len(exceptions)} applicable memory exceptions")
                for exc in exceptions[:3]:  # Show first 3
                    audit_trail.append(f"  - {exc.description} (applied {exc.applied_count} times)")
            else:
                audit_trail.append("No applicable memory exceptions found")
            
            if self.observability:
                self.observability.log_agent_step(
                    trace_id=state.get("trace_id", ""),
                    agent_name="PAA",
                    step_name="check_memory",
                    input_data={"invoice_id": invoice.invoice_id},
                    output_data={"exception_count": len(exceptions)},
                )

        except Exception as e:
            logger.error(f"Error checking memory: {e}")
            state["memory_exceptions"] = []
            audit_trail.append(f"Error checking memory: {str(e)}")

        state["audit_trail"] = audit_trail
        return state

    def evaluate_compliance(self, state: PolicyAdherenceState) -> PolicyAdherenceState:
        """Node 4: Evaluate compliance using LLM with policies and memory."""
        invoice = state["invoice"]
        policies = state.get("retrieved_policies", [])
        exceptions = state.get("memory_exceptions", [])
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("Evaluating compliance with LLM")

        # Build context for LLM
        policy_context = "\n\n".join([
            f"Policy: {p['policy_name']}\n{p['content']}"
            for p in policies[:3]  # Top 3 most relevant
        ])
        
        exception_context = ""
        if exceptions:
            exception_context = "\n\nLearned Exceptions (from previous human decisions):\n" + "\n".join([
                f"- {exc.description} (Success rate: {exc.success_rate:.1%})"
                for exc in exceptions[:3]
            ])

        prompt = f"""You are a compliance auditor. Check if this invoice complies with company policies.

Invoice Details:
- ID: {invoice.invoice_id}
- Vendor: {invoice.vendor} (reputation: {invoice.vendor_reputation}/100)
- Amount: ${invoice.amount} {invoice.currency}
- Category: {invoice.category}
- PO Number: {invoice.po_number or 'MISSING'}
- International: {invoice.international}
- Line Items: {len(invoice.line_items)} items

Relevant Company Policies:
{policy_context}
{exception_context}

Analyze this invoice against the policies and learned exceptions. Determine:
1. Is this invoice COMPLIANT or NON-COMPLIANT?
2. What policies (if any) are violated?
3. Do any learned exceptions apply?
4. What is your confidence level (0.0 to 1.0)?

Respond in this format:
COMPLIANT: [yes|no]
VIOLATED_POLICIES: [comma-separated list or "none"]
APPLIED_EXCEPTIONS: [comma-separated list or "none"]
CONFIDENCE: [0.0-1.0]
REASONING: [detailed explanation]
"""

        try:
            response = self.llm_client.completion(
                prompt=prompt,
                temperature=self.settings.paa_temperature,
            )

            # Parse LLM response
            is_compliant = False
            violated_policies = []
            applied_exceptions = []
            confidence = 0.5
            reasoning = ""

            for line in response.split("\n"):
                if line.startswith("COMPLIANT:"):
                    is_compliant = "yes" in line.lower()
                elif line.startswith("VIOLATED_POLICIES:"):
                    policies_str = line.split(":", 1)[1].strip()
                    if policies_str.lower() not in ["none", ""]:
                        violated_policies = [p.strip() for p in policies_str.split(",")]
                elif line.startswith("APPLIED_EXCEPTIONS:"):
                    exceptions_str = line.split(":", 1)[1].strip()
                    if exceptions_str.lower() not in ["none", ""]:
                        applied_exceptions = [e.strip() for e in exceptions_str.split(",")]
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line.split(":", 1)[1].strip())
                    except:
                        confidence = 0.5
                elif line.startswith("REASONING:"):
                    reasoning = line.split(":", 1)[1].strip()

            compliance_result = PolicyCheckResult(
                is_compliant=is_compliant,
                violated_policies=violated_policies,
                applied_exceptions=applied_exceptions,
                reasoning=reasoning,
                confidence=confidence,
            )

            state["compliance_result"] = compliance_result
            state["reasoning"] = reasoning

            status = "✅ Compliant" if is_compliant else "❌ Non-compliant"
            audit_trail.append(f"Compliance check: {status} (confidence: {confidence:.2f})")
            
            if violated_policies:
                audit_trail.append(f"Violated policies: {', '.join(violated_policies)}")
            if applied_exceptions:
                audit_trail.append(f"Applied exceptions: {', '.join(applied_exceptions)}")
            
            if self.observability:
                self.observability.log_llm_call(
                    trace_id=state.get("trace_id", ""),
                    prompt=prompt,
                    response=response,
                    model=self.settings.primary_model,
                )

        except Exception as e:
            logger.error(f"Error evaluating compliance: {e}")
            # Default to non-compliant with low confidence if error
            compliance_result = PolicyCheckResult(
                is_compliant=False,
                violated_policies=["Error in compliance check"],
                applied_exceptions=[],
                reasoning=f"Error during evaluation: {str(e)}",
                confidence=0.0,
            )
            state["compliance_result"] = compliance_result
            state["reasoning"] = f"Error: {str(e)}"
            audit_trail.append(f"❌ Error evaluating compliance: {str(e)}")

        state["audit_trail"] = audit_trail
        return state

    def return_response(self, state: PolicyAdherenceState) -> PolicyAdherenceState:
        """Node 5: Return compliance result to TAA."""
        audit_trail = state.get("audit_trail", [])
        
        audit_trail.append("PAA compliance check completed")
        
        logger.info(f"PAA completed check for {state['invoice'].invoice_id}")
        
        state["audit_trail"] = audit_trail
        return state

    async def check_compliance(
        self,
        invoice: Invoice,
        trace_id: str = "",
    ) -> PolicyAdherenceState:
        """Check compliance for an invoice.
        
        Args:
            invoice: Invoice to check
            trace_id: Trace ID for observability
            
        Returns:
            Final state with compliance result
        """
        initial_state = PolicyAdherenceState(
            invoice=invoice,
            trace_id=trace_id,
            audit_trail=[],
        )

        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        logger.info(f"PAA completed compliance check for {invoice.invoice_id}")
        return final_state

    def check_compliance_sync(
        self,
        invoice: Invoice,
        trace_id: str = "",
    ) -> PolicyAdherenceState:
        """Synchronous version of check_compliance."""
        initial_state = PolicyAdherenceState(
            invoice=invoice,
            trace_id=trace_id,
            audit_trail=[],
        )

        # Run the graph synchronously
        final_state = self.graph.invoke(initial_state)
        
        logger.info(f"PAA completed compliance check for {invoice.invoice_id}")
        return final_state

