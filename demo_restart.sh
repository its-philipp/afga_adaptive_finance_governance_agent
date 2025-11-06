#!/bin/bash
# DEMO RESTART - Nuclear option for clean slate
# Use this before presenting to ensure audit trails are clean

echo "🧹 DEMO RESTART - Ensuring clean slate..."

# 1. Kill EVERYTHING Python-related (nuclear option)
echo "☠️  Killing all Python processes..."
pkill -9 python3 2>/dev/null
pkill -9 streamlit 2>/dev/null
pkill -9 uvicorn 2>/dev/null
sleep 3

# Verify nothing is left
if pgrep -x streamlit > /dev/null || pgrep -x uvicorn > /dev/null; then
    echo "❌ Processes still running! Manually check:"
    ps aux | grep -E "streamlit|uvicorn" | grep -v grep
    exit 1
fi

# 2. Delete ALL Python bytecode (everywhere)
echo "🗑️  Removing ALL Python bytecode..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# 3. Clear virtual environment cache
echo "🗑️  Clearing venv cache..."
rm -rf .venv/lib/python*/site-packages/__pycache__ 2>/dev/null

# 4. Delete database for fresh start
echo "🗑️  Deleting database..."
rm -f data/memory.db
rm -f data/*.db-journal

# 5. Initialize database schema
echo "🔧 Initializing database schema..."
source .venv/bin/activate
python -c "from src.db.memory_db import MemoryDB; db = MemoryDB(); print('✅ Database initialized')"

# 6. Regenerate mock data (will use current clean code)
echo "📝 Regenerating mock invoices with clean audit trail code..."
python scripts/generate_mock_data.py --invoices 5

# 7. Wait to ensure everything is dead
echo "⏳ Waiting for system to settle..."
sleep 2

# 8. Start fresh
echo "🚀 Starting fresh servers..."
./start.sh &

echo ""
echo "✅ DEMO RESTART COMPLETE!"
echo ""
echo "Next steps for demo:"
echo "  1. Wait 10 seconds for servers to start"
echo "  2. Open http://localhost:8501 in a FRESH browser window (or incognito)"
echo "  3. Process a NEW transaction (e.g., INV-0002)"
echo "  4. Audit trail will be CLEAN with no warnings!"
echo ""

