#!/bin/bash

# AFGA Quick Start Script
# Starts both FastAPI backend and Streamlit frontend

echo "🚀 Starting Adaptive Finance Governance Agent (AFGA)"
echo "=================================================="

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Run 'uv sync' first."
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Check if data directory exists
if [ ! -d "data/mock_invoices" ]; then
    echo "📊 Generating mock data..."
    python scripts/generate_mock_data.py
fi

# Start FastAPI backend in background
echo "🔧 Starting FastAPI backend..."
uvicorn src.api.main:app --reload --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ Backend is running!"
else
    echo "❌ Backend failed to start. Check backend.log"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start Streamlit frontend
echo "🎨 Starting Streamlit frontend..."
# Skip email prompt and disable usage stats collection
STREAMLIT_SERVER_HEADLESS=true streamlit run streamlit_app/app.py --server.headless=true

# Cleanup on exit
echo ""
echo "🛑 Shutting down..."
kill $BACKEND_PID 2>/dev/null
echo "✅ AFGA stopped"

