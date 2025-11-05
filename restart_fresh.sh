#!/bin/bash

# AFGA Fresh Restart Script
# Clears Python cache and restarts with clean state

echo "🛑 Stopping AFGA..."
pkill -f "streamlit run" 2>/dev/null
pkill -f "uvicorn src.api.main" 2>/dev/null
sleep 2

echo "🧹 Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "✅ Cache cleared"

echo ""
echo "🚀 Starting AFGA with fresh code..."
./start.sh

