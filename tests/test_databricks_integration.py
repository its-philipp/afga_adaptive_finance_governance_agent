"""Databricks integration smoke test.

Run after setting:
  export DATABRICKS_SERVER_HOSTNAME=adb-XXXXXXXX.azuredatabricks.net
  export DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/XXXXXXXX
  export DATABRICKS_TOKEN=dapiXXXXXXXXXXXXXXXX

Purpose:
  1. Verifies the Python environment can import the connector.
  2. Confirms credentials work (simple metadata query).
  3. Checks gold table row & sample embedding shape.
"""

import os
import sys
import importlib.util
from typing import Sequence

# Attempt to load environment variables from a .env file if present.
# Uses APP_ENV_FILE override if set; falls back to project root .env.
def _load_dotenv():
    env_file = os.getenv("APP_ENV_FILE", ".env")
    if not os.path.isfile(env_file):
        print(f"ℹ️ No .env file found at '{env_file}' (skipping load)")
        return
    try:
        from dotenv import load_dotenv  # python-dotenv is already a project dependency
        load_dotenv(dotenv_path=env_file, override=False)
        print(f"📦 Loaded environment variables from {env_file}")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ Failed to load .env file '{env_file}': {e}")

_load_dotenv()

EXPECTED_EMBEDDING_DIM = 1536  # adjust if model changes
DEFAULT_GOLD_TABLE = "afga_dev.gold.finance_transaction_embeddings"

def fail(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)

def warn(msg: str) -> None:
    print(f"⚠️ {msg}")

def info(msg: str) -> None:
    print(f"🔍 {msg}")

def check_env(var_names: Sequence[str]) -> dict:
    missing = [v for v in var_names if not os.getenv(v)]
    if missing:
        # Hint about .env usage if variables absent
        example = "\nExample .env entries:\n" + "\n".join(
            f"{name}=<value>" for name in var_names
        )
        fail(
            "Missing env vars: "
            + ", ".join(missing)
            + "\nEnsure they are exported or present in .env (not committed)."
            + example
        )
    return {v: os.getenv(v) for v in var_names}

def ensure_connector_import():
    if importlib.util.find_spec("databricks") is None:
        fail(
            "Module 'databricks' not found. Install inside ACTIVE venv with:\n"
            "  python -m pip install databricks-sql-connector\n"
            "If using uv: uv add databricks-sql-connector"
        )
    from databricks import sql  # noqa: WPS433
    return sql

def main():
    info("Validating required environment variables")
    env = check_env([
        "DATABRICKS_SERVER_HOSTNAME",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_TOKEN",
    ])

    gold_table = os.getenv("DATABRICKS_GOLD_TABLE", DEFAULT_GOLD_TABLE)
    info(f"Using gold table: {gold_table}")

    sql = ensure_connector_import()

    info("Opening Databricks SQL connection")
    try:
        with sql.connect(
            server_hostname=env["DATABRICKS_SERVER_HOSTNAME"],
            http_path=env["DATABRICKS_HTTP_PATH"],
            access_token=env["DATABRICKS_TOKEN"],
        ) as connection:
            with connection.cursor() as cursor:
                info("Running metadata sanity query")
                cursor.execute("SELECT current_user(), current_catalog(), current_schema()")
                meta = cursor.fetchone()
                print(f"✅ Connected as user={meta[0]} catalog={meta[1]} schema={meta[2]}")

                info("Sampling embeddings")
                try:
                    # Fetch sample plus computed length to avoid materializing large arrays repeatedly.
                    cursor.execute(
                        f"SELECT invoice_id, embedding, size(embedding) AS emb_dim FROM {gold_table} LIMIT 5"
                    )
                    rows = cursor.fetchall()
                except Exception as e:  # table missing or permission
                    fail(f"Failed to query gold table '{gold_table}': {e}")

                if not rows:
                    warn("Gold table has 0 rows or query returned none")
                else:
                    for row in rows:
                        # Row structure can vary; support tuple unpacking defensively.
                        if len(row) == 3:
                            invoice_id, embedding, emb_dim = row
                        else:  # fallback if driver returns only selected columns
                            invoice_id, embedding = row[0], row[1]
                            emb_dim = len(embedding) if embedding is not None else 0

                        if embedding is None:
                            warn(f"{invoice_id}: embedding is NULL")
                            continue

                        # Some drivers return numpy arrays; treat uniformly.
                        try:
                            dim = int(emb_dim)
                        except Exception:
                            dim = len(embedding) if hasattr(embedding, "__len__") else -1

                        if dim == EXPECTED_EMBEDDING_DIM:
                            print(f"✅ {invoice_id}: embedding OK dim={dim}")
                        elif dim > 0:
                            warn(
                                f"{invoice_id}: embedding dim {dim} (expected {EXPECTED_EMBEDDING_DIM})"
                            )
                        else:
                            warn(f"{invoice_id}: empty embedding (dim={dim})")

                cursor.execute(f"SELECT COUNT(*) FROM {gold_table}")
                total = cursor.fetchone()[0]
                print(f"📊 Total rows in gold table: {total}")
                print("🎉 Databricks integration test complete")
    except Exception as e:
        fail(f"Connection or query failed: {e}")

if __name__ == "__main__":
    main()
