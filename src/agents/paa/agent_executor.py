"""PAA A2A Agent Executor - enables PAA to act as an A2A server agent."""

from __future__ import annotations

import json
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState, TextPart

from ...models.schemas import Invoice
from .agent import PolicyAdherenceAgent


logger = logging.getLogger(__name__)


class PAAExecutor(AgentExecutor):
    """A2A Executor for Policy Adherence Agent.
    
    Enables PAA to receive compliance check requests via A2A protocol.
    """

    def __init__(self):
        self.agent = PolicyAdherenceAgent()
        logger.info("PAA Executor initialized")

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute PAA workflow in response to A2A task."""
        if not context.task_id or not context.context_id:
            raise ValueError("RequestContext must have task_id and context_id")
        if not context.message:
            raise ValueError("RequestContext must have a message")

        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        
        # Submit task
        if not context.current_task:
            await updater.submit()
        
        # Start working
        await updater.start_work()

        try:
            # Parse input message
            user_input = context.get_user_input()
            
            # Expected format: JSON with invoice data
            input_data = json.loads(user_input)
            invoice = Invoice(**input_data["invoice"])
            trace_id = input_data.get("trace_id", "")

            # Send status update
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message([
                    Part(root=TextPart(text=f"Checking compliance for invoice {invoice.invoice_id}"))
                ]),
            )

            # Check compliance through PAA
            result = await self.agent.check_compliance(invoice, trace_id)

            # Get compliance result
            compliance_result = result.get("compliance_result")
            
            # Prepare response
            if compliance_result:
                status_icon = "✅" if compliance_result.is_compliant else "❌"
                response_text = f"{status_icon} Compliance Check Complete\n"
                response_text += f"Result: {'Compliant' if compliance_result.is_compliant else 'Non-compliant'}\n"
                response_text += f"Confidence: {compliance_result.confidence:.2f}\n"
                
                if compliance_result.violated_policies:
                    response_text += f"Violated Policies: {', '.join(compliance_result.violated_policies)}\n"
                
                if compliance_result.applied_exceptions:
                    response_text += f"Applied Exceptions: {', '.join(compliance_result.applied_exceptions)}\n"
                
                response_text += f"\nReasoning: {compliance_result.reasoning}\n"
            else:
                response_text = "❌ Error: No compliance result generated"

            # Send audit trail
            audit_trail = result.get("audit_trail", [])
            response_text += f"\nAudit Trail:\n" + "\n".join(f"- {step}" for step in audit_trail)

            # Add artifact with structured result
            if compliance_result:
                artifact_payload = {
                    "compliance_result": compliance_result.model_dump(mode="json"),
                    "audit_trail": result.get("audit_trail", []),
                    "hallucination_warnings": result.get("hallucination_warnings", []),
                    "rag_metrics": (
                        result.get("rag_metrics").model_dump(mode="json")
                        if result.get("rag_metrics")
                        else None
                    ),
                }
                await updater.add_artifact(
                    [Part(root=TextPart(text=json.dumps(artifact_payload)))],
                    name="paa_compliance_result",
                )

            # Complete task
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message([Part(root=TextPart(text=response_text))]),
            )
            await updater.complete()

        except Exception as e:
            logger.error(f"Error in PAA execution: {e}", exc_info=True)
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message([
                    Part(root=TextPart(text=f"❌ Error checking compliance: {str(e)}"))
                ]),
            )
            raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle task cancellation."""
        logger.info(f"PAA task {context.task_id} cancelled")
        # PAA doesn't support cancellation - just log it
        raise NotImplementedError("PAA does not support task cancellation")

