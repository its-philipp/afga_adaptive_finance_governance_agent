#!/usr/bin/env python3
"""Insert a synthetic pending HITL transaction into the local memory DB.

Use this to demo the HITL flow in the UI without auto-submitting feedback.
"""
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/memory.db")
INVOICE_PATH = Path("data/mock_invoices/INV-HITL-001.json")

now = datetime.now()

if not DB_PATH.exists():
    raise SystemExit(f"Memory DB not found at {DB_PATH}. Start the app once to initialize it.")

if not INVOICE_PATH.exists():
    raise SystemExit(f"Invoice file not found at {INVOICE_PATH}. Create it first.")

with open(INVOICE_PATH, "r") as f:
    invoice = json.load(f)

transaction_id = uuid.uuid4().hex[:8]

policy_check = {
    "is_compliant": True,
    "violated_policies": [],
    "applied_exceptions": [],
    "reasoning": "Borderline case: compliant but ambiguous context; deferring to human.",
    "confidence": 0.60,
    "retrieved_sources": [],
}

audit_trail = [
    f"Synthetic insertion for demo at {now.isoformat(timespec='seconds')}",
    "Final decision set to HITL to allow human review demo.",
]

row = (
    transaction_id,                          # transaction_id
    invoice.get("invoice_id", "INV-HITL-001"),  # invoice_id
    json.dumps(invoice),                      # invoice_data
    60.0,                                     # risk_score
    "medium",                                # risk_level
    "compliant",                             # paa_decision
    json.dumps(policy_check),                 # policy_check_json
    "hitl",                                  # final_decision (lowercase in DB)
    "Low confidence; requires human review", # decision_reasoning
    0,                                        # human_override (pending)
    2500,                                     # processing_time_ms
    json.dumps(audit_trail),                  # audit_trail
    "demo-hitl",                             # trace_id
    now,                                      # created_at
    now,                                      # updated_at
    None,                                     # source_document_path
)

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

cursor.execute(
    """
    INSERT INTO transactions
    (transaction_id, invoice_id, invoice_data, risk_score, risk_level,
     paa_decision, policy_check_json, final_decision, decision_reasoning, human_override,
     processing_time_ms, audit_trail, trace_id, created_at, updated_at, source_document_path)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    row,
)

conn.commit()
conn.close()

print(f"Inserted pending HITL transaction: {transaction_id}")
