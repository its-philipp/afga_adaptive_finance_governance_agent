"""Migrate database to latest schema."""

import sqlite3
from pathlib import Path

def migrate_database():
    """Add missing columns and tables to existing database."""
    db_path = Path("data/memory.db")
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("   Run the app first to create it, or delete and recreate.")
        return
    
    print(f"✅ Database found at {db_path}")
    print("🔧 Running migrations...")
    print("=" * 80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Migration 1: Add updated_at to transactions
    print("\n1️⃣ Adding 'updated_at' column to transactions table...")
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN updated_at TIMESTAMP")
        conn.commit()
        print("   ✅ Added 'updated_at' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("   ℹ️  Column already exists, skipping")
        else:
            print(f"   ❌ Error: {e}")
    
    # Migration 2: Add decision_reasoning to transactions
    print("\n2️⃣ Adding 'decision_reasoning' column to transactions table...")
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN decision_reasoning TEXT")
        conn.commit()
        print("   ✅ Added 'decision_reasoning' column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("   ℹ️  Column already exists, skipping")
        else:
            print(f"   ❌ Error: {e}")
    
    # Migration 3: Create exceptions table
    print("\n3️⃣ Creating 'exceptions' table...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exception_type TEXT NOT NULL,
                condition TEXT NOT NULL,
                action TEXT NOT NULL,
                reasoning TEXT,
                confidence_score REAL DEFAULT 1.0,
                applied_count INTEGER DEFAULT 0,
                source_transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_applied_at TIMESTAMP,
                metadata TEXT
            )
        """)
        conn.commit()
        print("   ✅ Created 'exceptions' table")
    except sqlite3.Error as e:
        print(f"   ❌ Error: {e}")
    
    # Migration 4: Create exception_applications table
    print("\n4️⃣ Creating 'exception_applications' table...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exception_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exception_id INTEGER NOT NULL,
                transaction_id TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result TEXT,
                FOREIGN KEY (exception_id) REFERENCES exceptions (id)
            )
        """)
        conn.commit()
        print("   ✅ Created 'exception_applications' table")
    except sqlite3.Error as e:
        print(f"   ❌ Error: {e}")
    
    # Verify migrations
    print("\n" + "=" * 80)
    print("🔍 Verifying schema...")
    
    cursor.execute("PRAGMA table_info(transactions)")
    trans_cols = [col[1] for col in cursor.fetchall()]
    print(f"\nTransactions columns: {', '.join(trans_cols)}")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"\nAll tables: {', '.join(tables)}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ Migration complete!")
    print("\n🚀 Next steps:")
    print("   1. Restart the app: ./restart_fresh.sh")
    print("   2. Process a new transaction")
    print("   3. Provide HITL feedback with 'Create Exception Rule'")
    print("   4. Check KPI Dashboard and Memory Browser")

if __name__ == "__main__":
    migrate_database()

