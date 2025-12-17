from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import httpx

from .config import get_settings


logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Simple wrapper around the OpenRouter API supporting retries and fallbacks."""

    def __init__(self, timeout: float = 60.0) -> None:
        self.settings = get_settings()
        self.client = httpx.Client(timeout=timeout)

    def completion(
        self,
        prompt: str,
        model: str | None = None,
        context: List[Dict[str, str]] | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Generate completion with automatic fallback to backup models.

        Args:
            prompt: The prompt to send to the model
            model: Specific model to use (optional, uses primary_model if not specified)
            context: Conversation context (list of message dicts)
            temperature: Sampling temperature for the model

        Returns:
            Generated text response

        Raises:
            RuntimeError: If all models fail to generate a completion
        """
        models = [model or self.settings.primary_model, *self.settings.fallback_models]
        for model_id in models:
            try:
                result = self._call_openrouter(prompt, model_id, context=context, temperature=temperature)
                return result
            except Exception:
                logger.warning("OpenRouter model %s failed, trying next fallback", model_id, exc_info=True)
        raise RuntimeError("All OpenRouter models failed to generate a completion")

    def _call_openrouter(
        self,
        prompt: str,
        model: str,
        context: List[Dict[str, str]] | None = None,
        temperature: float = 0.3,
    ) -> str:
        """Call OpenRouter API with specified model."""
        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "HTTP-Referer": "https://afga-demo",
            "Content-Type": "application/json",
        }

        messages = context + [{"role": "user", "content": prompt}] if context else [{"role": "user", "content": prompt}]

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        response = self.client.post(
            f"{self.settings.openrouter_base_url}/chat/completions", headers=headers, content=json.dumps(payload)
        )

        # Log response for debugging
        if response.status_code != 200:
            logger.error(f"OpenRouter error {response.status_code}: {response.text}")

        response.raise_for_status()
        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices returned from OpenRouter API")
        message = choices[0]["message"]["content"]
        return message

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
