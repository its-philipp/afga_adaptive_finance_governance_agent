"""EMA A2A Agent Executor - enables EMA to act as an A2A server agent."""

from __future__ import annotations

import json
import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState, TextPart

from ...models.schemas import HITLFeedback, Invoice
from .agent import ExceptionManagerAgent


logger = logging.getLogger(__name__)


class EMAExecutor(AgentExecutor):
    """A2A Executor for Exception Manager Agent.
    
    Enables EMA to receive HITL feedback via A2A protocol and process it.
    """

    def __init__(self):
        self.agent = ExceptionManagerAgent()
        logger.info("EMA Executor initialized")

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute EMA workflow in response to A2A task."""
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
            
            # Expected format: JSON with feedback and invoice data
            input_data = json.loads(user_input)
            feedback = HITLFeedback(**input_data["feedback"])
            invoice = Invoice(**input_data["invoice"])
            trace_id = input_data.get("trace_id", "")

            # Send status update
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message([
                    Part(root=TextPart(text=f"Processing HITL feedback for transaction {feedback.transaction_id}"))
                ]),
            )

            # Process feedback through EMA
            result = await self.agent.process_hitl_feedback(feedback, invoice, trace_id)

            # Prepare response
            response_text = f"✅ HITL feedback processed\n"
            response_text += f"Correction type: {result.get('correction_type', 'N/A')}\n"
            response_text += f"Should learn: {result.get('should_learn', False)}\n"
            
            if result.get("memory_update_id"):
                response_text += f"Memory updated: {result['memory_update_id']}\n"
            
            response_text += f"H-CR KPI updated: {result.get('hcr_updated', False)}\n"

            # Send audit trail
            audit_trail = result.get("audit_trail", [])
            response_text += f"\nAudit Trail:\n" + "\n".join(f"- {step}" for step in audit_trail)

            # Add artifact with structured result
            await updater.add_artifact(
                [Part(root=TextPart(text=json.dumps(result, default=str)))],
                name="ema_result",
            )

            # Complete task
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message([Part(root=TextPart(text=response_text))]),
            )
            await updater.complete()

        except Exception as e:
            logger.error(f"Error in EMA execution: {e}", exc_info=True)
            await updater.update_status(
                TaskState.working,
                message=updater.new_agent_message([
                    Part(root=TextPart(text=f"❌ Error processing HITL feedback: {str(e)}"))
                ]),
            )
            raise

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handle task cancellation."""
        logger.info(f"EMA task {context.task_id} cancelled")
        # EMA doesn't support cancellation - just log it
        raise NotImplementedError("EMA does not support task cancellation")

