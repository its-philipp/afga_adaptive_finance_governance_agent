#!/bin/bash
# Stop AFGA application cleanly

echo "🛑 Stopping AFGA..."

# Check if PIDs exist
if [ -f .backend.pid ] || [ -f .frontend.pid ]; then
    # Kill processes using saved PIDs
    kill $(cat .backend.pid .frontend.pid 2>/dev/null) 2>/dev/null || true
    
    # Wait for graceful shutdown
    sleep 2
    
    # Verify they're stopped
    streamlit_count=$(pgrep -f "streamlit run" 2>/dev/null | wc -l | tr -d ' ')
    uvicorn_pattern="uvicorn.*(8000|src\\.api\\.main:app)"
    uvicorn_count=$(pgrep -f "$uvicorn_pattern" 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$streamlit_count" -eq 0 ] && [ "$uvicorn_count" -eq 0 ]; then
        echo "✅ All processes stopped cleanly"
    else
        echo "⚠️  Some processes still running, forcing shutdown..."
        pkill -9 -f "streamlit run" 2>/dev/null || true
        pkill -9 -f "$uvicorn_pattern" 2>/dev/null || true
        sleep 1
        echo "✅ Forced shutdown complete"
    fi
    
    # Clean up PID files
    rm -f .backend.pid .frontend.pid
    
else
    # No PID files, try to find and kill processes
    echo "⚠️  No PID files found, searching for running processes..."
    
    streamlit_count=$(pgrep -f "streamlit run" 2>/dev/null | wc -l | tr -d ' ')
    uvicorn_pattern="uvicorn.*(8000|src\\.api\\.main:app)"
    uvicorn_count=$(pgrep -f "$uvicorn_pattern" 2>/dev/null | wc -l | tr -d ' ')
    
    if [ "$streamlit_count" -eq 0 ] && [ "$uvicorn_count" -eq 0 ]; then
        echo "✅ No AFGA processes running"
    else
        echo "   Found: Streamlit=$streamlit_count, Uvicorn=$uvicorn_count"
        echo "   Killing..."
        pkill -9 -f "streamlit run" 2>/dev/null || true
        pkill -9 -f "$uvicorn_pattern" 2>/dev/null || true
        sleep 1
        echo "✅ Processes stopped"
    fi
fi

# Force free ports 8000 and 8501 if anything is still using them
echo "🔌 Ensuring ports 8000 and 8501 are free..."
for port in 8000 8501; do
    pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo "   ⚠️  Port $port still in use by PID $pid, killing..."
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
done
echo "   ✅ Ports are free"

# Clean Python bytecode cache to ensure fresh code on next start
echo "🧹 Cleaning Python bytecode cache..."
find . -path "./.venv" -prune -o -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -rf __pycache__ src/__pycache__ src/*/__pycache__ src/*/*/__pycache__ 2>/dev/null || true
rm -rf streamlit_app/__pycache__ streamlit_app/*/__pycache__ 2>/dev/null || true
echo "   ✅ Cache cleared"

echo ""
echo "🏁 AFGA is now stopped."
echo ""
echo "▶️  Start again with:"
echo "   ./start.sh"
echo ""

