"""Input governance for LLM prompts.

Validates prompts before they are sent to LLMs:
- PII detection (emails, credit cards, SSNs, etc.)
- Forbidden word filtering
- Prompt length validation
- Sensitive data protection
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Tuple


logger = logging.getLogger(__name__)


class InputValidator:
    """Validates LLM inputs for governance compliance."""

    def __init__(self):
        # PII patterns
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "phone": r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            "iban": r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b',
        }
        
        # Forbidden words (sensitive data markers)
        self.forbidden_words = [
            "password",
            "secret_key",
            "api_key",
            "private_key",
            "access_token",
        ]
        
        # Prompt constraints
        self.min_prompt_length = 5
        self.max_prompt_length = 50000  # Very large, but prevents abuse
        
        logger.info("Input Validator initialized")

    def validate(self, prompt: str, agent_name: str = "unknown") -> Tuple[bool, List[str]]:
        """Validate a prompt for governance compliance.
        
        Args:
            prompt: The prompt to validate
            agent_name: Name of the agent making the request
            
        Returns:
            (is_valid, violations) - True if valid, list of violation messages
        """
        violations = []
        
        # Check prompt length
        if len(prompt) < self.min_prompt_length:
            violations.append(f"Prompt too short ({len(prompt)} chars, min {self.min_prompt_length})")
        
        if len(prompt) > self.max_prompt_length:
            violations.append(f"Prompt too long ({len(prompt)} chars, max {self.max_prompt_length})")
        
        # Check for PII
        pii_found = self._detect_pii(prompt)
        if pii_found:
            for pii_type, matches in pii_found.items():
                violations.append(f"PII detected ({pii_type}): {len(matches)} instance(s)")
                logger.warning(f"PII detected in {agent_name} prompt: {pii_type}")
        
        # Check for forbidden words
        forbidden_found = self._detect_forbidden_words(prompt)
        if forbidden_found:
            violations.append(f"Forbidden words detected: {', '.join(forbidden_found)}")
            logger.warning(f"Forbidden words in {agent_name} prompt: {forbidden_found}")
        
        is_valid = len(violations) == 0
        
        if not is_valid:
            logger.warning(f"Input validation failed for {agent_name}: {violations}")
        
        return is_valid, violations

    def _detect_pii(self, text: str) -> Dict[str, List[str]]:
        """Detect PII in text using regex patterns.
        
        Returns:
            Dictionary of PII type -> list of matches
        """
        detected = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                detected[pii_type] = matches
        
        return detected

    def _detect_forbidden_words(self, text: str) -> List[str]:
        """Detect forbidden words in text.
        
        Returns:
            List of forbidden words found
        """
        text_lower = text.lower()
        found = []
        
        for word in self.forbidden_words:
            if word.lower() in text_lower:
                found.append(word)
        
        return found

    def redact_pii(self, text: str) -> str:
        """Redact PII from text for safe logging.
        
        Args:
            text: Text potentially containing PII
            
        Returns:
            Text with PII redacted
        """
        redacted = text
        
        # Redact emails
        redacted = re.sub(self.pii_patterns["email"], "[EMAIL_REDACTED]", redacted)
        
        # Redact SSNs
        redacted = re.sub(self.pii_patterns["ssn"], "[SSN_REDACTED]", redacted)
        
        # Redact credit cards
        redacted = re.sub(self.pii_patterns["credit_card"], "[CREDIT_CARD_REDACTED]", redacted)
        
        # Redact phones
        redacted = re.sub(self.pii_patterns["phone"], "[PHONE_REDACTED]", redacted)
        
        # Redact IBANs
        redacted = re.sub(self.pii_patterns["iban"], "[IBAN_REDACTED]", redacted)
        
        return redacted

