"""Databricks embeddings stats service.

Provides lightweight read-only access to the gold embeddings table.
Designed to avoid hard dependencies if environment variables are missing.
"""
from __future__ import annotations

from typing import Any, Dict, List
import os
import logging

logger = logging.getLogger(__name__)

EXPECTED_EMBEDDING_DIM = 1536  # adjust if model changes
DEFAULT_GOLD_TABLE = "afga_dev.gold.finance_transaction_embeddings"
DEFAULT_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")

class DatabricksUnavailable(Exception):
    """Raised when Databricks configuration or library is unavailable."""


def _get_env(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value.strip()
    return None


_REQUIRED_VARS = ["DATABRICKS_SERVER_HOSTNAME", "DATABRICKS_HTTP_PATH", "DATABRICKS_TOKEN"]

def missing_config_vars() -> list[str]:
    """Return list of missing Databricks required environment variables."""
    return [v for v in _REQUIRED_VARS if not _get_env(v)]

def is_configured() -> bool:
    return len(missing_config_vars()) == 0


def get_embeddings_stats(limit: int = 5) -> Dict[str, Any]:
    """Return aggregate stats and sample embeddings metadata.

    Parameters
    ----------
    limit : int
        Number of sample rows to return.
    """
    if not is_configured():
        raise DatabricksUnavailable(
            "Databricks environment variables missing: " + ", ".join(missing_config_vars())
        )

    try:
        from databricks import sql  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise DatabricksUnavailable(f"databricks-sql-connector not installed: {exc}") from exc

    gold_table = _get_env("DATABRICKS_GOLD_TABLE") or DEFAULT_GOLD_TABLE

    result: Dict[str, Any] = {
        "gold_table": gold_table,
        "expected_dim": EXPECTED_EMBEDDING_DIM,
        "rows_total": 0,
        "samples": [],  # type: List[Dict[str, Any]]
    }

    try:
        with sql.connect(
            server_hostname=_get_env("DATABRICKS_SERVER_HOSTNAME"),
            http_path=_get_env("DATABRICKS_HTTP_PATH"),
            access_token=_get_env("DATABRICKS_TOKEN"),
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) FROM {gold_table}")
                result["rows_total"] = cursor.fetchone()[0]

                cursor.execute(
                    f"SELECT invoice_id, size(embedding) AS emb_dim FROM {gold_table} LIMIT {int(limit)}"
                )
                samples = []
                for invoice_id, emb_dim in cursor.fetchall():
                    samples.append(
                        {
                            "invoice_id": invoice_id,
                            "embedding_dim": int(emb_dim),
                            "dimension_ok": int(emb_dim) == EXPECTED_EMBEDDING_DIM,
                        }
                    )
                result["samples"] = samples
    except DatabricksUnavailable:
        raise
    except Exception as exc:  # pragma: no cover - log and bubble
        logger.error("Databricks query failed", exc_info=True)
        result["error"] = str(exc)

    return result


def search_embeddings(
    query: str,
    k: int = 5,
    sample_limit: int = 500,
    openai_api_key_override: str | None = None,
) -> Dict[str, Any]:
    """Perform a naive similarity search over embeddings fetched from Databricks.

    This client-side implementation retrieves up to ``sample_limit`` rows from the gold table,
    embeds the query text using OpenAI, computes cosine similarity, and returns top-k matches.

    Parameters
    ----------
    query : str
        Natural language query or invoice-like description.
    k : int
        Number of most similar results to return.
    sample_limit : int
        Maximum number of rows to pull from Databricks for in-memory similarity.
    """
    if not query or not query.strip():
        raise ValueError("Query text must be non-empty.")
    if not is_configured():
        raise DatabricksUnavailable(
            "Databricks environment variables missing for similarity search: "
            + ", ".join(missing_config_vars())
        )

    try:
        from databricks import sql  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise DatabricksUnavailable(f"databricks-sql-connector not installed: {exc}") from exc

    # Embed query using OpenAI (accept multiple possible env var names)
    try:
        from openai import OpenAI  # type: ignore
        key_candidates = [
            openai_api_key_override,
            _get_env("OPENAI_API_KEY"),
            _get_env("OPENAI_KEY"),
            _get_env("OPENAI_API_TOKEN"),
            os.getenv("OPENAI_API_KEY"),
            os.getenv("OPENAI_KEY"),
            os.getenv("OPENAI_API_TOKEN"),
        ]
        openai_key = next((k for k in key_candidates if k), None)
        if not openai_key:
            raise RuntimeError(
                "No OpenAI API key found. Provide one via env (OPENAI_API_KEY) or payload openai_api_key."
            )
        client = OpenAI(api_key=openai_key)
        embed_resp = client.embeddings.create(model=DEFAULT_EMBED_MODEL, input=query[:8000])
        query_vec = embed_resp.data[0].embedding
    except Exception as exc:  # pragma: no cover
        msg = str(exc)
        if any(term in msg.lower() for term in ["api key", "unauthorized", "invalid", "401"]):
            raise ValueError(f"OpenAI key invalid or unauthorized: {msg}") from exc
        raise RuntimeError(f"Failed to generate query embedding: {msg}") from exc

    import math
    import numpy as np

    gold_table = _get_env("DATABRICKS_GOLD_TABLE") or DEFAULT_GOLD_TABLE
    rows: list[tuple[str, list[float]]] = []
    try:
        with sql.connect(
            server_hostname=_get_env("DATABRICKS_SERVER_HOSTNAME"),
            http_path=_get_env("DATABRICKS_HTTP_PATH"),
            access_token=_get_env("DATABRICKS_TOKEN"),
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT invoice_id, embedding FROM {gold_table} LIMIT {int(sample_limit)}"
                )
                for invoice_id, embedding in cursor.fetchall():
                    if embedding is not None:  # skip null/empty
                        rows.append((invoice_id, embedding))
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Failed querying gold table: {exc}") from exc

    if not rows:
        return {
            "query": query,
            "results": [],
            "total_searched": 0,
            "gold_table": gold_table,
            "model": DEFAULT_EMBED_MODEL,
            "note": "No embeddings available to search.",
        }

    q = np.array(query_vec, dtype=float)
    q_norm = np.linalg.norm(q) or 1.0
    scored: list[tuple[str, float]] = []
    for invoice_id, emb in rows:
        # Some drivers may return list, tuple, numpy array, or None.
        if emb is None:
            continue
        try:
            v = np.array(emb, dtype=float)
        except Exception:
            # If conversion fails, skip this embedding row.
            continue
        if v.size == 0:
            continue
        denom = (np.linalg.norm(v) or 1.0) * q_norm
        if denom == 0.0:
            continue
        sim = float(np.dot(q, v) / denom)
        if not math.isnan(sim):
            scored.append((invoice_id, sim))

    scored.sort(key=lambda t: t[1], reverse=True)
    top = scored[:k]

    return {
        "query": query,
        "results": [
            {"invoice_id": invoice_id, "similarity": round(score, 6)} for invoice_id, score in top
        ],
        "total_searched": len(scored),
        "gold_table": gold_table,
        "model": DEFAULT_EMBED_MODEL,
    }
