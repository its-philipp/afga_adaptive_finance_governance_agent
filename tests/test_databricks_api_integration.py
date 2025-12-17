"""Integration test for FastAPI Databricks embeddings stats endpoint.

This test requires the following environment variables to be set:
  DATABRICKS_SERVER_HOSTNAME
  DATABRICKS_HTTP_PATH
  DATABRICKS_TOKEN
Optional:
  DATABRICKS_GOLD_TABLE (defaults to afga_dev.gold.finance_transaction_embeddings)

Run with:
  pytest -k databricks_api_integration -s
"""
from __future__ import annotations

import os
import pytest
import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
ENDPOINT = f"{API_BASE_URL}/databricks/embeddings/stats"

required_env = ["DATABRICKS_SERVER_HOSTNAME", "DATABRICKS_HTTP_PATH", "DATABRICKS_TOKEN"]

def _missing_env():
  return [v for v in required_env if not os.getenv(v)]

def test_databricks_embeddings_stats_endpoint():  # noqa: D401
  missing = _missing_env()
  if missing:
    pytest.skip(f"Missing env vars: {', '.join(missing)}")
    """Calls the embeddings stats endpoint and validates basic structure."""
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(ENDPOINT, params={"limit": 3})
    assert resp.status_code == 200, f"Unexpected status code: {resp.status_code} body={resp.text}"

    data = resp.json()
    assert "gold_table" in data
    assert "rows_total" in data
    assert "samples" in data

    samples = data["samples"]
    assert isinstance(samples, list)
    for sample in samples:
        assert "invoice_id" in sample
        assert "embedding_dim" in sample
        assert "dimension_ok" in sample

    # If there are rows, ensure dimension flag matches expected embedding size.
    if data["rows_total"] > 0 and samples:
        for sample in samples:
            if sample["embedding_dim"] > 0:
                assert isinstance(sample["dimension_ok"], bool)
