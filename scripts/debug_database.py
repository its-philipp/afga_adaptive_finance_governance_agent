"""Debug script to check database contents."""

import sys
from pathlib import Path
import sqlite3
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def check_database():
    """Check what's actually in the database."""
    db_path = Path("data/memory.db")
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    print(f"✅ Database found at {db_path}")
    print("=" * 80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check table schema first
    print("\n📊 DATABASE SCHEMA:")
    print("-" * 80)
    cursor.execute("PRAGMA table_info(transactions)")
    columns = cursor.fetchall()
    print("Transactions table columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]}) {'[PRIMARY KEY]' if col[5] else ''}")
    
    # Check transactions
    print("\n📋 TRANSACTIONS:")
    print("-" * 80)
    
    # Get column names dynamically
    cursor.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 5")
    col_names = [description[0] for description in cursor.description]
    
    transactions = cursor.fetchall()
    if transactions:
        for txn in transactions:
            txn_dict = dict(zip(col_names, txn))
            print(f"\nTransaction: {txn_dict.get('transaction_id', 'N/A')[:8]}")
            print(f"  Invoice: {txn_dict.get('invoice_id', 'N/A')}")
            print(f"  Decision: {txn_dict.get('final_decision', 'N/A')}")
            print(f"  Human Override: {txn_dict.get('human_override', 0)} {'✅ YES' if txn_dict.get('human_override') == 1 else '❌ NO'}")
            print(f"  Created: {txn_dict.get('created_at', 'N/A')}")
            if 'updated_at' in txn_dict:
                print(f"  Updated: {txn_dict.get('updated_at', 'N/A')}")
            if 'decision_reasoning' in txn_dict:
                print(f"  Reasoning: {txn_dict.get('decision_reasoning', 'N/A')}")
    else:
        print("  No transactions found")
    
    # Check total human overrides
    print("\n" + "=" * 80)
    cursor.execute("SELECT COUNT(*) FROM transactions WHERE human_override = 1")
    override_count = cursor.fetchone()[0]
    print(f"📊 Total Human Overrides: {override_count}")
    
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_count = cursor.fetchone()[0]
    print(f"📊 Total Transactions: {total_count}")
    
    if total_count > 0:
        hcr = (override_count / total_count) * 100
        print(f"📈 Calculated H-CR: {hcr:.1f}%")
    
    # Check exceptions
    print("\n" + "=" * 80)
    print("\n🧠 EXCEPTIONS:")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            id,
            exception_type,
            condition,
            applied_count,
            confidence_score,
            created_at
        FROM exceptions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    exceptions = cursor.fetchall()
    if exceptions:
        for exc in exceptions:
            print(f"\nException #{exc[0]}:")
            print(f"  Type: {exc[1]}")
            print(f"  Condition: {exc[2]}")
            print(f"  Applied Count: {exc[3]} {'✅ USED' if exc[3] > 0 else '❌ NEVER USED'}")
            print(f"  Confidence: {exc[4]:.2f}")
            print(f"  Created: {exc[5]}")
    else:
        print("  No exceptions found")
    
    cursor.execute("SELECT COUNT(*) FROM exceptions WHERE applied_count > 0")
    applied_exceptions = cursor.fetchone()[0]
    print(f"\n📊 Exceptions Applied: {applied_exceptions}")
    
    cursor.execute("SELECT COUNT(*) FROM exceptions")
    total_exceptions = cursor.fetchone()[0]
    print(f"📊 Total Exceptions: {total_exceptions}")
    
    # Check KPIs
    print("\n" + "=" * 80)
    print("\n📈 KPIs (latest):")
    print("-" * 80)
    cursor.execute("""
        SELECT 
            date,
            hcr,
            crs,
            atar,
            audit_score,
            human_corrections,
            total_transactions
        FROM kpis
        ORDER BY date DESC
        LIMIT 3
    """)
    
    kpis = cursor.fetchall()
    if kpis:
        for kpi in kpis:
            print(f"\n{kpi[0]}:")
            print(f"  H-CR: {kpi[1]:.1f}%")
            print(f"  CRS: {kpi[2]:.1f}%")
            print(f"  ATAR: {kpi[3]:.1f}%")
            print(f"  Human Corrections: {kpi[5]}")
            print(f"  Total Transactions: {kpi[6]}")
    else:
        print("  No KPIs found")
    
    conn.close()
    print("\n" + "=" * 80)
    print("\n✅ Database check complete!")

if __name__ == "__main__":
    check_database()

