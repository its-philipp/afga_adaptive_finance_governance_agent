from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

import httpx

from ..core.config import get_settings
from ..governance.audit_logger import GovernanceAuditLogger


class LangfuseInsights:
    """Aggregate Langfuse connectivity status and local audit analytics."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.host = (self.settings.langfuse_host or "").rstrip("/") if self.settings.langfuse_host else None
        self.public_key = self.settings.langfuse_public_key
        self.secret_key = self.settings.langfuse_secret_key
        self.enabled = bool(self.host and self.public_key and self.secret_key)
        self.audit_log_path = Path("governance_audit.jsonl")
        self.audit_logger = GovernanceAuditLogger(log_file=str(self.audit_log_path))
        self.violations_path = self.audit_log_path.parent / "governance_violations.jsonl"

    def get_summary(self, limit: int = 200) -> Dict[str, Any]:
        local_metrics = self._compute_local_metrics(limit=limit)
        langfuse_status = self._ping_langfuse()
        remote_metrics = self._fetch_remote_metrics() if langfuse_status.get("status") == "ok" else {"available": False}

        return {
            "enabled": self.enabled,
            "host": self.host,
            "langfuse_status": langfuse_status,
            "remote_metrics": remote_metrics,
            "local_metrics": local_metrics,
        }

    def _compute_local_metrics(self, limit: int = 200) -> Dict[str, Any]:
        stats = self.audit_logger.get_statistics()
        events = self._load_recent_audit_events(limit=limit)

        calls_by_agent = Counter(event.get("agent_name", "unknown") for event in events)
        calls_by_model = Counter(event.get("model", "unknown") for event in events)
        latency_samples = [
            {
                "timestamp": event.get("timestamp"),
                "processing_time_ms": event.get("processing_time_ms", 0),
                "agent": event.get("agent_name", "unknown"),
                "model": event.get("model", "unknown"),
            }
            for event in events
            if event.get("processing_time_ms") is not None
        ]

        cost_by_agent = Counter()
        for event in events:
            agent = event.get("agent_name", "unknown")
            cost_by_agent[agent] += float(event.get("cost_estimate_usd", 0.0))

        def _parse_timestamp(raw: Any) -> datetime | None:
            if not raw or not isinstance(raw, str):
                return None
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:
                return None

        # Guardrail analytics
        input_checks = 0
        output_checks = 0
        input_failures_audit = 0
        output_failures_audit = 0
        last_input_violation_ts: datetime | None = None
        last_output_violation_ts: datetime | None = None

        for event in events:
            event_ts = _parse_timestamp(event.get("timestamp"))

            if "input_valid" in event:
                input_checks += 1
                if event.get("input_valid") is False:
                    input_failures_audit += 1
                    if event_ts:
                        last_input_violation_ts = (
                            max(last_input_violation_ts, event_ts) if last_input_violation_ts else event_ts
                        )

            if "output_valid" in event:
                output_checks += 1
                if event.get("output_valid") is False:
                    output_failures_audit += 1
                    if event_ts:
                        last_output_violation_ts = (
                            max(last_output_violation_ts, event_ts) if last_output_violation_ts else event_ts
                        )

        violation_events = self._load_violation_events(limit=limit)
        input_violation_events = [evt for evt in violation_events if evt.get("event_type") == "input_validation_failed"]
        output_violation_events = [
            evt for evt in violation_events if evt.get("event_type") == "output_validation_failed"
        ]
        policy_violation_events = [evt for evt in violation_events if evt.get("event_type") == "policy_violation"]

        for evt in input_violation_events:
            evt_ts = _parse_timestamp(evt.get("timestamp"))
            if evt_ts:
                last_input_violation_ts = max(last_input_violation_ts, evt_ts) if last_input_violation_ts else evt_ts

        for evt in output_violation_events:
            evt_ts = _parse_timestamp(evt.get("timestamp"))
            if evt_ts:
                last_output_violation_ts = max(last_output_violation_ts, evt_ts) if last_output_violation_ts else evt_ts

        def _status(violations: int, checks: int) -> str:
            if checks == 0:
                return "idle"
            return "healthy" if violations == 0 else "attention"

        guardrail_summary = {
            "input": {
                "label": "Input Governance",
                "description": "PII redaction, forbidden words, prompt validation",
                "checks": input_checks + len(input_violation_events),
                "violations": input_failures_audit + len(input_violation_events),
                "last_violation": (last_input_violation_ts.isoformat() if last_input_violation_ts else None),
                "status": _status(
                    input_failures_audit + len(input_violation_events), input_checks + len(input_violation_events)
                ),
            },
            "output": {
                "label": "Output Governance",
                "description": "Content safety, PII redaction in responses",
                "checks": output_checks + len(output_violation_events),
                "violations": output_failures_audit + len(output_violation_events),
                "last_violation": (last_output_violation_ts.isoformat() if last_output_violation_ts else None),
                "status": _status(
                    output_failures_audit + len(output_violation_events), output_checks + len(output_violation_events)
                ),
            },
            "policy": {
                "label": "Policy Enforcement",
                "description": "Access controls, rate limits, compliance policies",
                "checks": max(stats.get("total_calls", len(events)), len(policy_violation_events)),
                "violations": len(policy_violation_events),
                "last_violation": None,
                "status": _status(
                    len(policy_violation_events),
                    max(stats.get("total_calls", len(events)), len(policy_violation_events)),
                ),
            },
            "audit": {
                "label": "Audit Logging",
                "description": "Tamper-evident trail for every LLM call",
                "checks": len(events),
                "violations": stats.get("violations", 0),
                "last_violation": None,
                "status": "healthy" if len(events) > 0 else "idle",
            },
        }

        # Track last policy violation timestamp if available
        if policy_violation_events:
            last_policy_ts = max(
                filter(None, (_parse_timestamp(evt.get("timestamp")) for evt in policy_violation_events)), default=None
            )
            if last_policy_ts:
                guardrail_summary["policy"]["last_violation"] = last_policy_ts.isoformat()

        return {
            "total_calls": stats.get("total_calls", len(events)),
            "violations": stats.get("violations", 0),
            "violation_rate": stats.get("violation_rate", 0.0),
            "total_cost_usd": stats.get("total_cost_usd", 0.0),
            "calls_by_agent": calls_by_agent.most_common(),
            "calls_by_model": calls_by_model.most_common(),
            "cost_by_agent": cost_by_agent.most_common(),
            "latency_samples": latency_samples[-50:],  # limit to recent 50 points for charts
            "guardrail_summary": guardrail_summary,
        }

    def _load_recent_audit_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self.audit_log_path.exists():
            return []

        try:
            with open(self.audit_log_path, "r", encoding="utf-8") as file:
                lines = file.readlines()[-limit:]
            events: List[Dict[str, Any]] = []
            for line in lines:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return events
        except Exception:
            return []

    def _load_violation_events(self, limit: int = 200) -> List[Dict[str, Any]]:
        if not self.violations_path.exists():
            return []

        try:
            with open(self.violations_path, "r", encoding="utf-8") as file:
                lines = file.readlines()[-limit:]
            events: List[Dict[str, Any]] = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return events
        except Exception:
            return []

    def _ping_langfuse(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled", "message": "Langfuse keys or host not configured"}

        try:
            url = f"{self.host}/api/public/health"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url, auth=(self.public_key, self.secret_key))
                if response.status_code == 200:
                    payload = response.json() if response.content else {}
                    return {"status": "ok", "payload": payload}
                return {"status": "error", "code": response.status_code, "message": response.text}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    def _fetch_remote_metrics(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"available": False}

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(
                    f"{self.host}/api/public/traces",
                    params={"limit": 25},
                    auth=(self.public_key, self.secret_key),
                )
                if response.status_code != 200:
                    return {"available": False, "code": response.status_code, "message": response.text}

                data = response.json()
                traces = data.get("data", data)
                if not isinstance(traces, list):
                    return {"available": False, "message": "Unexpected response format"}

                agent_counts = Counter()
                model_counts = Counter()
                recent_traces: List[Dict[str, Any]] = []

                for trace in traces[:25]:
                    metadata = trace.get("metadata", {}) if isinstance(trace, dict) else {}
                    agent = metadata.get("agent") or metadata.get("agent_name") or metadata.get("name", "unknown")
                    model = metadata.get("model") or trace.get("model")
                    agent_counts[agent or "unknown"] += 1
                    model_counts[model or "unknown"] += 1
                    recent_traces.append(
                        {
                            "id": trace.get("id"),
                            "name": trace.get("name"),
                            "agent": agent,
                            "model": model,
                            "timestamp": trace.get("timestamp") or trace.get("createdAt"),
                        }
                    )

                return {
                    "available": True,
                    "trace_count": len(traces),
                    "agents": agent_counts.most_common(),
                    "models": model_counts.most_common(),
                    "recent_traces": recent_traces[:10],
                }
        except Exception as exc:
            return {"available": False, "message": str(exc)}


_LANGFUSE_INSIGHTS = LangfuseInsights()


def get_langfuse_insights() -> LangfuseInsights:
    return _LANGFUSE_INSIGHTS
