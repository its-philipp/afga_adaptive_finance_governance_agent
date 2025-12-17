"""Integration test for similarity search endpoint.

Requires running API locally and Databricks env vars.
Skips automatically if configuration is missing.
"""
from __future__ import annotations

import os
import pytest
import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
ENDPOINT = f"{API_BASE_URL}/databricks/embeddings/search"

required_env = ["DATABRICKS_SERVER_HOSTNAME", "DATABRICKS_HTTP_PATH", "DATABRICKS_TOKEN"]
openai_env_candidates = ["OPENAI_API_KEY", "OPENAI_KEY", "OPENAI_API_TOKEN"]

def _missing_env():
    missing = [v for v in required_env if not os.getenv(v)]
    # Require at least one OpenAI key variant; if absent, mark as missing synthetic name OPENAI_API_KEY
    if not any(os.getenv(name) for name in openai_env_candidates):
        missing.append("OPENAI_API_KEY")
    return missing

def test_similarity_search_basic():  # noqa: D401
    missing = _missing_env()
    if missing:
        pytest.skip(f"Missing env vars: {', '.join(missing)}")
    payload = {"query": "consulting services invoice", "k": 3, "sample_limit": 50}
    # Inject key override so endpoint can work even if backend didn't load .env early
    for name in openai_env_candidates:
        val = os.getenv(name)
        if val:
            # Skip if obviously a placeholder
            if val.startswith("sk-REDACTED") or "YOUR_OPENAI" in val.upper():
                pytest.skip("OpenAI key placeholder detected; skipping similarity search test.")
            payload["openai_api_key"] = val
            break
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(ENDPOINT, json=payload)
    assert resp.status_code == 200, f"Unexpected status {resp.status_code} body={resp.text}"
    data = resp.json()
    assert "results" in data
    assert "query" in data
    assert data["query"] == payload["query"]
    assert isinstance(data["results"], list)
    # If there are any embeddings searched we expect <= k results
    if data.get("total_searched", 0) > 0:
        assert len(data["results"]) <= payload["k"]
        for item in data["results"]:
            assert "invoice_id" in item
            assert "similarity" in item
            assert isinstance(item["similarity"], float)
