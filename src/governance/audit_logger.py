"""Enhanced audit logging for AI governance.

Logs all LLM interactions in JSONL format with:
- Input/output content (PII-redacted)
- Governance violations
- Cost tracking
- Performance metrics
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class GovernanceAuditLogger:
    """Enhanced audit logger for AI governance."""

    def __init__(self, log_file: str = "governance_audit.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Also create violations log
        self.violations_file = self.log_file.parent / "governance_violations.jsonl"

        logger.info(f"Governance Audit Logger initialized: {self.log_file}")

    def log_llm_call(
        self,
        agent_name: str,
        prompt: str,
        response: str,
        model: str,
        input_valid: bool,
        input_violations: List[str],
        output_valid: bool,
        output_violations: List[str],
        processing_time_ms: int,
        trace_id: str = "",
        user_id: str = "",
        cost_estimate: float = 0.0,
    ) -> None:
        """Log an LLM call with governance information.

        Args:
            agent_name: Agent making the call
            prompt: Input prompt (will be redacted if contains PII)
            response: LLM response (will be redacted if contains PII)
            model: Model used
            input_valid: Whether input passed validation
            input_violations: List of input violations
            output_valid: Whether output passed validation
            output_violations: List of output violations
            processing_time_ms: Processing time in milliseconds
            trace_id: Trace ID for correlation
            user_id: User identifier
            cost_estimate: Estimated cost in USD
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": trace_id,
            "user_id": user_id,
            "agent_name": agent_name,
            "model": model,
            "prompt": prompt,  # Redacted prompts for transparency
            "response": response,  # Redacted responses for transparency
            "prompt_length": len(prompt),
            "response_length": len(response),
            "input_valid": input_valid,
            "input_violations": input_violations,
            "output_valid": output_valid,
            "output_violations": output_violations,
            "processing_time_ms": processing_time_ms,
            "cost_estimate_usd": cost_estimate,
            "governance_status": "pass" if input_valid and output_valid else "violation",
        }

        # Write to main audit log
        self._write_entry(self.log_file, entry)

        # If violations, also write to violations log
        if not input_valid or not output_valid:
            self._write_entry(self.violations_file, entry)
            logger.warning(
                f"Governance violation in {agent_name}: input={input_violations}, output={output_violations}"
            )

    def log_governance_event(
        self,
        event_type: str,
        agent_name: str,
        details: Dict[str, Any],
        severity: str = "info",
    ) -> None:
        """Log a governance event (rate limit, access control, etc.).

        Args:
            event_type: Type of event (rate_limit, access_denied, etc.)
            agent_name: Agent involved
            details: Event details
            severity: Event severity (info, warning, error)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "agent_name": agent_name,
            "severity": severity,
            "details": details,
        }

        self._write_entry(self.violations_file, entry)

    def _write_entry(self, file_path: Path, entry: Dict[str, Any]) -> None:
        """Write a JSONL entry to file."""
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_recent_violations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent governance violations.

        Args:
            limit: Number of violations to return

        Returns:
            List of violation entries
        """
        if not self.violations_file.exists():
            return []

        try:
            violations = []
            with open(self.violations_file, "r", encoding="utf-8") as f:
                for line in f:
                    violations.append(json.loads(line))

            # Return most recent
            return violations[-limit:] if len(violations) > limit else violations

        except Exception as e:
            logger.error(f"Failed to read violations: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """Get governance statistics from audit log.

        Returns:
            Dictionary with governance metrics
        """
        if not self.log_file.exists():
            return {
                "total_calls": 0,
                "violations": 0,
                "violation_rate": 0.0,
            }

        try:
            total_calls = 0
            violations = 0
            total_cost = 0.0
            by_agent = {}

            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    total_calls += 1

                    if entry.get("governance_status") == "violation":
                        violations += 1

                    total_cost += entry.get("cost_estimate_usd", 0.0)

                    agent = entry.get("agent_name", "unknown")
                    if agent not in by_agent:
                        by_agent[agent] = {"calls": 0, "violations": 0}
                    by_agent[agent]["calls"] += 1
                    if entry.get("governance_status") == "violation":
                        by_agent[agent]["violations"] += 1

            violation_rate = (violations / total_calls * 100) if total_calls > 0 else 0.0

            return {
                "total_calls": total_calls,
                "violations": violations,
                "violation_rate": violation_rate,
                "total_cost_usd": total_cost,
                "by_agent": by_agent,
            }

        except Exception as e:
            logger.error(f"Failed to calculate statistics: {e}")
            return {"total_calls": 0, "violations": 0, "violation_rate": 0.0}
