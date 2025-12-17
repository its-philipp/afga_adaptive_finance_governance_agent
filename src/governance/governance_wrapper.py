"""Main governance wrapper for LLM calls.

Wraps OpenRouterClient with comprehensive governance controls:
- Input validation (PII, forbidden words)
- Output validation (content filtering)
- Policy enforcement (time controls)
- Enhanced audit logging
- Cost tracking
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from ..core.config import get_settings
from ..core.openrouter_client import OpenRouterClient
from .audit_logger import GovernanceAuditLogger
from .input_validator import InputValidator
from .output_validator import OutputValidator


logger = logging.getLogger(__name__)


class GovernanceWrapper:
    """Governance wrapper for LLM API calls.

    Intercepts all LLM calls to enforce:
    - Input governance (PII detection, forbidden words)
    - Output governance (content validation)
    - Policy enforcement (access controls)
    - Enhanced auditing (JSONL logs)
    - Cost tracking
    """

    def __init__(
        self,
        llm_client: Optional[OpenRouterClient] = None,
        audit_logger: Optional[GovernanceAuditLogger] = None,
        input_validator: Optional[InputValidator] = None,
        output_validator: Optional[OutputValidator] = None,
    ):
        self.settings = get_settings()
        self.llm_client = llm_client or OpenRouterClient()
        self.audit_logger = audit_logger or GovernanceAuditLogger()
        self.input_validator = input_validator or InputValidator()
        self.output_validator = output_validator or OutputValidator()

        # Governance statistics (in-memory for quick access)
        self.stats = {
            "total_calls": 0,
            "blocked_calls": 0,
            "input_violations": 0,
            "output_violations": 0,
            "total_cost_usd": 0.0,
        }

        logger.info("GovernanceWrapper initialized with full governance controls")

    def governed_completion(
        self,
        prompt: str,
        agent_name: str = "unknown",
        model: str | None = None,
        context: List[Dict[str, str]] | None = None,
        temperature: float = 0.3,
        user_id: str = "",
        trace_id: str = "",
        bypass_governance: bool = False,
    ) -> str:
        """Make a governed LLM completion call.

        Args:
            prompt: Input prompt
            agent_name: Name of the agent making the call
            model: Model to use (optional)
            context: Conversation context
            temperature: Sampling temperature
            user_id: User identifier
            trace_id: Trace ID for correlation
            bypass_governance: Emergency bypass (logged!)

        Returns:
            LLM response (validated)

        Raises:
            ValueError: If governance checks fail
            PermissionError: If policy enforcement blocks the call
        """
        start_time = time.time()

        # Update stats
        self.stats["total_calls"] += 1

        # 1. INPUT GOVERNANCE
        if not bypass_governance:
            input_valid, input_violations = self.input_validator.validate(prompt, agent_name)

            if not input_valid:
                self.stats["blocked_calls"] += 1
                self.stats["input_violations"] += 1

                # Log violation
                self.audit_logger.log_governance_event(
                    event_type="input_validation_failed",
                    agent_name=agent_name,
                    details={
                        "violations": input_violations,
                        "prompt_preview": prompt[:200],
                        "trace_id": trace_id,
                    },
                    severity="error",
                )

                raise ValueError(f"Input governance failed for {agent_name}: {', '.join(input_violations)}")
        else:
            input_valid = True
            input_violations = []
            logger.warning(f"Governance bypassed for {agent_name} (emergency mode)")

        # 2. POLICY ENFORCEMENT
        if not bypass_governance:
            try:
                self._enforce_policies(agent_name, user_id)
            except PermissionError as e:
                self.stats["blocked_calls"] += 1

                # Log policy violation
                self.audit_logger.log_governance_event(
                    event_type="policy_violation",
                    agent_name=agent_name,
                    details={
                        "error": str(e),
                        "trace_id": trace_id,
                    },
                    severity="error",
                )

                raise

        # 3. LLM API CALL
        try:
            response = self.llm_client.completion(
                prompt=prompt,
                model=model,
                context=context,
                temperature=temperature,
            )
        except Exception as e:
            logger.error(f"LLM call failed for {agent_name}: {e}")

            # Log API failure
            self.audit_logger.log_governance_event(
                event_type="llm_api_failure",
                agent_name=agent_name,
                details={
                    "error": str(e),
                    "model": model or self.settings.primary_model,
                    "trace_id": trace_id,
                },
                severity="error",
            )

            raise

        # 4. OUTPUT GOVERNANCE
        if not bypass_governance:
            output_valid, output_violations = self.output_validator.validate(response, agent_name)

            if not output_valid:
                self.stats["output_violations"] += 1

                # Log output violation
                self.audit_logger.log_governance_event(
                    event_type="output_validation_failed",
                    agent_name=agent_name,
                    details={
                        "violations": output_violations,
                        "response_preview": response[:200],
                        "trace_id": trace_id,
                    },
                    severity="warning",  # Warning, not error - we still return the response
                )

                logger.warning(f"Output validation failed for {agent_name}: {output_violations}")
        else:
            output_valid = True
            output_violations = []

        # 5. COST ESTIMATION
        processing_time_ms = int((time.time() - start_time) * 1000)
        cost_estimate = self._estimate_cost(prompt, response, model or self.settings.primary_model)
        self.stats["total_cost_usd"] += cost_estimate

        # 6. AUDIT LOGGING (with PII redaction)
        redacted_prompt = self.input_validator.redact_pii(prompt)
        redacted_response = self.output_validator.redact_pii(response)

        self.audit_logger.log_llm_call(
            agent_name=agent_name,
            prompt=redacted_prompt,
            response=redacted_response,
            model=model or self.settings.primary_model,
            input_valid=input_valid,
            input_violations=input_violations,
            output_valid=output_valid,
            output_violations=output_violations,
            processing_time_ms=processing_time_ms,
            trace_id=trace_id,
            user_id=user_id,
            cost_estimate=cost_estimate,
        )

        return response

    def _enforce_policies(self, agent_name: str, user_id: str) -> None:
        """Enforce access policies.

        Raises:
            PermissionError: If policy is violated
        """
        # Check working hours (optional, can be disabled)
        hour = datetime.now().hour

        # For demo, we allow all hours, but log if outside business hours
        if hour < 6 or hour > 22:
            logger.info(f"LLM call outside business hours by {agent_name} (allowed but logged)")
            # Could raise PermissionError("LLM access outside authorized hours") in production

        # Additional policies can be added here:
        # - User authorization
        # - Agent permissions
        # - Rate limiting
        # - Budget constraints

    def _estimate_cost(self, prompt: str, response: str, model: str) -> float:
        """Estimate cost of LLM call.

        Returns:
            Estimated cost in USD
        """
        # Rough token estimation (1 token ≈ 4 chars)
        prompt_tokens = len(prompt) / 4
        response_tokens = len(response) / 4

        # Cost per 1K tokens (approximate)
        cost_per_1k = {
            "openai/gpt-4o": 0.005,  # $5/1M tokens input
            "openai/gpt-4-vision-preview": 0.01,
            "anthropic/claude-3.5-sonnet": 0.003,
            "meta-llama/llama-3.1-70b-instruct": 0.0005,
        }

        rate = cost_per_1k.get(model, 0.005)  # Default to GPT-4o rate

        total_cost = ((prompt_tokens + response_tokens) / 1000) * rate

        return round(total_cost, 6)

    def get_statistics(self) -> Dict[str, Any]:
        """Get governance statistics.

        Returns:
            Dictionary with current governance metrics
        """
        # Combine in-memory stats with audit log stats
        audit_stats = self.audit_logger.get_statistics()

        return {
            **self.stats,
            **audit_stats,
            "compliance_rate": (
                (self.stats["total_calls"] - self.stats["blocked_calls"]) / self.stats["total_calls"] * 100
            )
            if self.stats["total_calls"] > 0
            else 100.0,
        }

    def get_recent_violations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent governance violations."""
        return self.audit_logger.get_recent_violations(limit)


class GovernedLLMClient:
    """Drop-in replacement for OpenRouterClient with governance.

    This provides the same interface as OpenRouterClient but with
    comprehensive governance controls.
    """

    def __init__(self, agent_name: str = "unknown"):
        self.agent_name = agent_name
        self.governance = GovernanceWrapper()
        logger.info(f"Governed LLM Client initialized for {agent_name}")

    def completion(
        self,
        prompt: str,
        model: str | None = None,
        context: List[Dict[str, str]] | None = None,
        temperature: float = 0.3,
        trace_id: str = "",
        user_id: str = "",
    ) -> str:
        """Make a governed completion call.

        Same interface as OpenRouterClient.completion() but with governance.
        """
        return self.governance.governed_completion(
            prompt=prompt,
            agent_name=self.agent_name,
            model=model,
            context=context,
            temperature=temperature,
            trace_id=trace_id,
            user_id=user_id,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get governance statistics for this client."""
        return self.governance.get_statistics()

    def close(self) -> None:
        """Close underlying LLM client."""
        self.governance.llm_client.close()
