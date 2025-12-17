"""Output governance for LLM responses.

Validates LLM outputs before returning to agents:
- Empty response detection
- Content length validation
- PII in responses
- Basic toxicity keywords
- Schema compliance
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Tuple


logger = logging.getLogger(__name__)


class OutputValidator:
    """Validates LLM outputs for governance compliance."""

    def __init__(self):
        # Response constraints
        self.min_response_length = 1
        self.max_response_length = 100000

        # Basic toxicity keywords (can be extended with API)
        self.toxic_keywords = [
            "offensive_term_1",  # Placeholder - add real toxic terms carefully
            "offensive_term_2",
        ]

        # PII patterns (same as input)
        self.pii_patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        }

        logger.info("Output Validator initialized")

    def validate(self, response: str, agent_name: str = "unknown") -> Tuple[bool, List[str]]:
        """Validate an LLM response for governance compliance.

        Args:
            response: The LLM response to validate
            agent_name: Name of the agent that made the request

        Returns:
            (is_valid, violations) - True if valid, list of violation messages
        """
        violations = []

        # Check response length
        if len(response) < self.min_response_length:
            violations.append(f"Empty or too short response ({len(response)} chars)")

        if len(response) > self.max_response_length:
            violations.append(f"Response too long ({len(response)} chars, max {self.max_response_length})")

        # Check for PII in response
        pii_found = self._detect_pii(response)
        if pii_found:
            for pii_type, matches in pii_found.items():
                violations.append(f"PII in response ({pii_type}): {len(matches)} instance(s)")
                logger.warning(f"PII in {agent_name} response: {pii_type}")

        # Check for toxic content (basic)
        toxic_found = self._detect_toxic_keywords(response)
        if toxic_found:
            violations.append(f"Toxic keywords detected: {len(toxic_found)} instance(s)")
            logger.warning(f"Toxic content in {agent_name} response")

        is_valid = len(violations) == 0

        if not is_valid:
            logger.warning(f"Output validation failed for {agent_name}: {violations}")

        return is_valid, violations

    def _detect_pii(self, text: str) -> Dict[str, List[str]]:
        """Detect PII in text."""
        detected = {}

        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[pii_type] = matches

        return detected

    def _detect_toxic_keywords(self, text: str) -> List[str]:
        """Detect toxic keywords (basic implementation).

        For production, integrate with Perspective API or similar.
        """
        text_lower = text.lower()
        found = []

        for keyword in self.toxic_keywords:
            if keyword.lower() in text_lower:
                found.append(keyword)

        return found

    def validate_json_response(self, response: str) -> Tuple[bool, str]:
        """Validate that response is valid JSON.

        Args:
            response: Expected JSON string

        Returns:
            (is_valid, error_message)
        """
        import json

        try:
            # Try to parse
            json.loads(response)
            return True, ""
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"

    def redact_pii(self, text: str) -> str:
        """Redact PII from text for safe logging."""
        redacted = text

        for pii_type, pattern in self.pii_patterns.items():
            redacted = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", redacted)

        return redacted
