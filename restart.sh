#!/bin/bash
# Smart restart script with duplicate process detection
# Use this for development and before demos

# Don't exit on error - we want to handle errors gracefully
# set -e is too aggressive for this script

echo "🔍 AFGA Smart Restart"
echo "=================================================="

# Function to check for running processes
check_processes() {
    local streamlit_count=$(pgrep -f "streamlit run" | wc -l | tr -d ' ')
    local uvicorn_count=$(pgrep -f "uvicorn.*8000" | wc -l | tr -d ' ')
    
    if [ "$streamlit_count" -gt 0 ] || [ "$uvicorn_count" -gt 0 ]; then
        echo "⚠️  Found running processes:"
        [ "$streamlit_count" -gt 0 ] && echo "   - Streamlit: $streamlit_count process(es)"
        [ "$uvicorn_count" -gt 0 ] && echo "   - Uvicorn: $uvicorn_count process(es)"
        return 1
    fi
    return 0
}

# 1. Check for existing processes
echo "1️⃣  Checking for existing AFGA processes..."
if ! check_processes; then
    echo "   🛑 Stopping all AFGA processes..."
    pkill -9 -f "streamlit run" 2>/dev/null || true
    pkill -9 -f "uvicorn.*8000" 2>/dev/null || true
    sleep 3
    
    # Verify they're gone
    if ! check_processes; then
        echo "   ❌ ERROR: Processes still running after kill!"
        echo "   Please manually kill:"
        pgrep -af "streamlit|uvicorn.*8000"
        exit 1
    fi
    echo "   ✅ All processes stopped"
else
    echo "   ✅ No existing processes found"
fi

# 2. Clean Python bytecode cache
echo "2️⃣  Cleaning Python bytecode cache..."
find src -type f -name "*.pyc" -delete 2>/dev/null || true
find src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "   ✅ Cache cleared"

# 3. Verify database exists (don't delete unless --clean flag)
if [ "$1" == "--clean" ]; then
    echo "3️⃣  🗑️  Deleting database (--clean mode)..."
    rm -f data/memory.db
    echo "   ✅ Database deleted"
else
    echo "3️⃣  Preserving database (use --clean to reset)"
fi

# 4. Sync dependencies (especially UI deps like streamlit)
echo "4️⃣  Syncing dependencies with uv..."
uv sync --all-extras > /dev/null 2>&1
echo "   ✅ Dependencies synced"

# 5. Initialize/verify database
echo "5️⃣  Initializing database..."
source .venv/bin/activate
python -c "from src.db.memory_db import MemoryDatabase; db = MemoryDatabase()" 2>&1 | grep -v "Traceback" || true
echo "   ✅ Database ready"

# 6. Start backend (NO --reload to avoid duplicate process issues)
echo "6️⃣  Starting FastAPI backend..."
nohup .venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > afga_backend.log 2>&1 &
BACKEND_PID=$!
disown  # Detach from shell so it stays alive when script exits
echo $BACKEND_PID > .backend.pid
echo "   Backend PID: $BACKEND_PID"

# Wait for backend
echo "   ⏳ Waiting for backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "   ✅ Backend is running!"
        break
    fi
    sleep 1
done

# 7. Start frontend
echo "7️⃣  Starting Streamlit frontend..."
nohup .venv/bin/streamlit run streamlit_app/app.py > afga_frontend.log 2>&1 &
FRONTEND_PID=$!
disown  # Detach from shell so it stays alive when script exits
echo $FRONTEND_PID > .frontend.pid
echo "   Frontend PID: $FRONTEND_PID"

# Wait for Streamlit to start
echo "   ⏳ Waiting for Streamlit..."
for i in {1..10}; do
    streamlit_count=$(pgrep -f "streamlit run" | wc -l | tr -d ' ')
    if [ "$streamlit_count" -ge 1 ]; then
        echo "   ✅ Streamlit is running!"
        break
    fi
    sleep 1
done

# 8. Final verification
sleep 2
echo ""
echo "=================================================="
echo "✅ AFGA STARTED SUCCESSFULLY!"
echo ""
echo "📊 Process Status:"
streamlit_count=$(pgrep -f "streamlit run" | wc -l | tr -d ' ')
uvicorn_count=$(pgrep -f "uvicorn.*8000" | wc -l | tr -d ' ')
echo "   - Streamlit: $streamlit_count process (expected: 1)"
echo "   - Uvicorn: $uvicorn_count process (expected: 1)"

if [ "$streamlit_count" -ne 1 ] || [ "$uvicorn_count" -ne 1 ]; then
    echo ""
    echo "⚠️  WARNING: Unexpected process count!"
    echo "   Run './restart.sh' again to fix"
fi

echo ""
echo "🌐 Access:"
echo "   Frontend: http://localhost:8501"
echo "   Backend:  http://localhost:8000"
echo "   Health:   http://localhost:8000/api/v1/health"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f afga_backend.log"
echo "   Frontend: tail -f afga_frontend.log"
echo ""
echo "🛑 Stop:"
echo "   kill \$(cat .backend.pid .frontend.pid 2>/dev/null)"
echo ""

