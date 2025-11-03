from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from .config import get_settings


logger = logging.getLogger(__name__)


class Observability:
    """Observability layer for tracing and logging with Langfuse.
    
    Provides comprehensive audit trail for AFGA workflows:
    - Traces: Top-level workflow tracking (transaction processing)
    - Spans: Individual step tracking (risk assessment, policy check, memory update)
    - Generations: LLM call tracking with token usage and cost
    
    Gracefully falls back to standard logging if Langfuse is not configured.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = False
        self.client = None
        self._current_trace = None  # Store current trace context
        
        # Try to initialize Langfuse if credentials are provided
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            try:
                from langfuse import Langfuse
                self.client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.langfuse_host,
                )
                self.enabled = True
                logger.info("Langfuse observability enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse, falling back to logging: {e}")
        else:
            logger.info("Langfuse credentials not configured, using standard logging")

    @contextmanager
    def trace(
        self, name: str, metadata: Dict[str, Any] | None = None, user_id: Optional[str] = None
    ) -> Generator[str, None, None]:
        """Create a trace for the entire transaction workflow.
        
        Args:
            name: Name of the trace (e.g., "transaction_processing")
            metadata: Additional metadata (e.g., transaction_id, invoice data)
            user_id: Optional user identifier for multi-tenant tracking
            
        Yields:
            trace_id: Unique identifier for this trace
        """
        metadata = metadata or {}
        trace_id = str(uuid.uuid4())
        
        if self.enabled and self.client:
            try:
                trace = self.client.trace(
                    name=name,
                    input=metadata,
                    metadata={"trace_id": trace_id, "user_id": user_id} if user_id else {"trace_id": trace_id},
                )
                self._current_trace = trace  # Store trace context
                logger.info(f"Langfuse trace started: {name} [{trace_id}]")
                try:
                    yield trace_id
                    trace.update(output={"status": "completed"})
                finally:
                    self._current_trace = None  # Clear trace context
            except Exception as e:
                logger.warning(f"Langfuse trace failed: {e}")
                yield trace_id
        else:
            logger.info(f"Trace {name} [{trace_id}]: {metadata}")
            yield trace_id

    def log_agent_step(
        self, trace_id: str, agent_name: str, step_name: str, input_data: Dict[str, Any], output_data: Dict[str, Any]
    ) -> None:
        """Log an agent step as a span.
        
        Args:
            trace_id: ID of the parent trace
            agent_name: Name of the agent (TAA, PAA, EMA)
            step_name: Name of the step (e.g., "assess_risk", "check_policy")
            input_data: Input to the step
            output_data: Output from the step
        """
        if self.enabled and self.client and self._current_trace:
            try:
                span = self._current_trace.span(
                    name=f"{agent_name}_{step_name}",
                    input=input_data,
                    output=output_data,
                    metadata={"trace_id": trace_id, "agent": agent_name, "step": step_name},
                )
                span.end()
                logger.info(f"Langfuse span logged [{trace_id}]: {agent_name}.{step_name}")
            except Exception as e:
                logger.warning(f"Langfuse log_agent_step failed: {e}")
                logger.info(f"Agent step [{trace_id}]: {agent_name}.{step_name}")
        else:
            logger.info(f"Agent step [{trace_id}]: {agent_name}.{step_name}")

    def log_llm_call(
        self,
        trace_id: str,
        prompt: str,
        response: str,
        model: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        model_parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log LLM generation as a specialized generation observation.
        
        Args:
            trace_id: ID of the parent trace
            prompt: Input prompt to the LLM
            response: Generated response
            model: Model identifier (e.g., "openai/gpt-4o")
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            model_parameters: Model configuration (temperature, max_tokens, etc.)
        """
        model_parameters = model_parameters or {}
        usage = None
        
        # Prepare usage details if available
        if prompt_tokens is not None and completion_tokens is not None:
            usage = {
                "input": prompt_tokens,
                "output": completion_tokens,
                "total": prompt_tokens + completion_tokens,
            }
        
        if self.enabled and self.client and self._current_trace:
            try:
                generation = self._current_trace.generation(
                    name="llm_generation",
                    model=model,
                    input=prompt[:1000],  # Truncate for readability
                    output=response,
                    metadata={
                        "trace_id": trace_id,
                        "prompt_length": len(prompt),
                        "response_length": len(response),
                    },
                    model_parameters=model_parameters,
                    usage=usage,
                )
                generation.end()
                logger.info(f"Langfuse generation logged [{trace_id}]: model={model}")
            except Exception as e:
                logger.warning(f"Langfuse log_llm_call failed: {e}")
                logger.info(
                    f"LLM call [{trace_id}]: model={model}, prompt_len={len(prompt)}, response_len={len(response)}"
                )
        else:
            logger.info(f"LLM call [{trace_id}]: model={model}")

    def log_a2a_communication(
        self, trace_id: str, from_agent: str, to_agent: str, message: Dict[str, Any]
    ) -> None:
        """Log A2A inter-agent communication.
        
        Args:
            trace_id: ID of the parent trace
            from_agent: Source agent name
            to_agent: Destination agent name
            message: Message content
        """
        if self.enabled and self.client and self._current_trace:
            try:
                span = self._current_trace.span(
                    name=f"a2a_{from_agent}_to_{to_agent}",
                    input={"from": from_agent, "to": to_agent},
                    output=message,
                    metadata={"trace_id": trace_id, "communication_type": "A2A"},
                )
                span.end()
                logger.info(f"Langfuse A2A logged [{trace_id}]: {from_agent} → {to_agent}")
            except Exception as e:
                logger.warning(f"Langfuse log_a2a_communication failed: {e}")
                logger.info(f"A2A [{trace_id}]: {from_agent} → {to_agent}")
        else:
            logger.info(f"A2A [{trace_id}]: {from_agent} → {to_agent}")

    def flush(self) -> None:
        """Flush all pending events to Langfuse.
        
        Call this before shutdown to ensure all events are sent.
        """
        if self.enabled and self.client:
            try:
                self.client.flush()
                logger.info("Langfuse events flushed")
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse events: {e}")

