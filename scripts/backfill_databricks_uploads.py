#!/usr/bin/env python3
"""Backfill previously processed transactions to Databricks Azure Blob storage.

This script scans the SQLite `memory.db` for transactions and uploads any
that do not yet exist in the Azure Blob invoice container (or forcibly re-uploads
if `--force` is provided).

Usage:
    python scripts/backfill_databricks_uploads.py \
        --limit 100 \
        --force

Prerequisites:
    - AZURE_STORAGE_CONNECTION_STRING must be set in environment
    - azure-storage-blob package installed

Logic:
    1. Connect to SQLite and fetch up to N transactions.
    2. For each transaction, build expected blob path.
    3. If blob missing OR --force passed, upload invoice + agent trail.
    4. Report summary counts.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill")

DB_PATH = Path("data/memory.db")
INVOICE_SUBFOLDER = "invoices"


def connect_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise SystemExit(f"SQLite database not found: {path}")
    return sqlite3.connect(str(path))


def fetch_transactions(conn: sqlite3.Connection, limit: int) -> List[Tuple]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT transaction_id, invoice_data, audit_trail, created_at
        FROM transactions
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (limit,),
    )
    return cursor.fetchall()


def init_blob_clients():
    from azure.storage.blob import BlobServiceClient  # type: ignore

    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise SystemExit("AZURE_STORAGE_CONNECTION_STRING not set; cannot backfill.")

    container_invoices = os.getenv("AZURE_CONTAINER_INVOICES", "raw-transactions")
    container_audit = os.getenv("AZURE_CONTAINER_AUDIT", "audit-trails")

    service = BlobServiceClient.from_connection_string(connection_string)
    invoice_container = service.get_container_client(container_invoices)
    audit_container = service.get_container_client(container_audit)

    return invoice_container, audit_container


def blob_exists(container, blob_name: str) -> bool:
    try:
        container.get_blob_client(blob_name).get_blob_properties()
        return True
    except Exception:
        return False


def upload_invoice(container, invoice_payload: dict, transaction_id: str, created_at: str, force: bool) -> bool:
    # Derived date path from created_at (fallback to today)
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "")) if created_at else datetime.utcnow()
    except Exception:
        dt = datetime.utcnow()

    blob_name = f"invoices/{dt.strftime('%Y/%m/%d')}/{transaction_id}.json"

    if not force and blob_exists(container, blob_name):
        logger.debug(f"Skip existing invoice blob: {blob_name}")
        return False

    payload = {
        "invoice": invoice_payload.get("invoice", invoice_payload),  # may already be dict
        "transaction_id": transaction_id,
        "uploaded_at": datetime.utcnow().isoformat(),
        "source": "backfill",
    }

    container.get_blob_client(blob_name).upload_blob(
        data=json.dumps(payload, indent=2), overwrite=True, metadata={"transaction_id": transaction_id, "source": "backfill"}
    )
    logger.info(f"Uploaded invoice blob: {blob_name}")
    return True


def upload_agent_trail(container, audit_trail: list, transaction_id: str, created_at: str, force: bool) -> bool:
    if not audit_trail:
        return False

    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "")) if created_at else datetime.utcnow()
    except Exception:
        dt = datetime.utcnow()

    blob_name = f"agent-trails/{dt.strftime('%Y/%m/%d')}/{transaction_id}_trail.json"

    if not force and blob_exists(container, blob_name):
        logger.debug(f"Skip existing trail blob: {blob_name}")
        return False

    payload = {
        "transaction_id": transaction_id,
        "audit_trail": audit_trail,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "backfill",
    }

    container.get_blob_client(blob_name).upload_blob(
        data=json.dumps(payload, indent=2), overwrite=True, metadata={"transaction_id": transaction_id, "type": "agent_trail", "source": "backfill"}
    )
    logger.info(f"Uploaded agent trail blob: {blob_name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Backfill transactions to Databricks Azure Blob storage")
    parser.add_argument("--limit", type=int, default=500, help="Max transactions to consider")
    parser.add_argument("--force", action="store_true", help="Re-upload even if blob already exists")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be uploaded without writing blobs")
    args = parser.parse_args()

    # Initialize blobs
    try:
        invoice_container, audit_container = init_blob_clients()
    except Exception as e:
        logger.error(f"Blob init failed: {e}")
        raise SystemExit(1)

    conn = connect_db(DB_PATH)
    rows = fetch_transactions(conn, args.limit)

    logger.info(f"Fetched {len(rows)} transactions from database (limit={args.limit})")

    uploaded_invoices = 0
    uploaded_trails = 0
    skipped_invoices = 0
    skipped_trails = 0

    for transaction_id, invoice_json, audit_trail_json, created_at in rows:
        try:
            invoice_payload = json.loads(invoice_json) if isinstance(invoice_json, str) else invoice_json
        except Exception:
            logger.warning(f"Malformed invoice JSON for {transaction_id}; skipping")
            skipped_invoices += 1
            continue

        try:
            audit_trail = json.loads(audit_trail_json) if isinstance(audit_trail_json, str) else audit_trail_json
        except Exception:
            audit_trail = []

        if args.dry_run:
            logger.info(f"[DRY RUN] Would process {transaction_id}")
            continue

        # Upload invoice
        changed = upload_invoice(invoice_container, invoice_payload, transaction_id, created_at, force=args.force)
        if changed:
            uploaded_invoices += 1
        else:
            skipped_invoices += 1

        # Upload agent trail
        changed_trail = upload_agent_trail(audit_container, audit_trail or [], transaction_id, created_at, force=args.force)
        if changed_trail:
            uploaded_trails += 1
        else:
            skipped_trails += 1

    logger.info("Backfill summary:")
    logger.info(f"  Invoices uploaded: {uploaded_invoices}")
    logger.info(f"  Invoices skipped:  {skipped_invoices}")
    logger.info(f"  Trails uploaded:   {uploaded_trails}")
    logger.info(f"  Trails skipped:    {skipped_trails}")

    conn.close()


if __name__ == "__main__":
    main()
