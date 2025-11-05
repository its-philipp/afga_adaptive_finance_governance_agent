"""Reset database to test new fixes with fresh data."""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from db.memory_db import MemoryDatabase

def reset_database():
    """Delete the database file to start fresh."""
    db_path = Path("data/memory.db")
    
    if db_path.exists():
        print(f"🗑️  Deleting existing database: {db_path}")
        db_path.unlink()
        print("✅ Database deleted")
    else:
        print(f"ℹ️  No database found at {db_path}")
    
    # Initialize fresh database
    print("📊 Creating fresh database...")
    db = MemoryDatabase()
    print("✅ Fresh database created with new schema!")
    print()
    print("🎯 Next steps:")
    print("1. Restart the app (./start.sh)")
    print("2. Process a NEW transaction")
    print("3. Provide HITL feedback")
    print("4. Check KPIs and Memory Browser")
    print()
    print("⚠️  All old transactions and exceptions are deleted.")
    print("    This is necessary to test the bug fixes!")

if __name__ == "__main__":
    reset_database()

