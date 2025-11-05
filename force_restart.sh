#!/bin/bash

# AGGRESSIVE RESTART - Kill everything and clear all caches

echo "🛑 FORCE STOPPING ALL SERVICES..."
pkill -9 -f "streamlit" 2>/dev/null
pkill -9 -f "uvicorn" 2>/dev/null
pkill -9 -f "python.*afga" 2>/dev/null
sleep 3

echo "🧹 AGGRESSIVE CACHE CLEARING..."
# Clear ALL Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "*.pyo" -delete 2>/dev/null

# Clear pip cache in virtual env
rm -rf .venv/lib/python*/site-packages/__pycache__/* 2>/dev/null

# Clear any lingering .pyc files in src
find src -name "*.pyc" -delete 2>/dev/null
find src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo "✅ Cache cleared"
echo ""
echo "🔄 REACTIVATING VIRTUAL ENV..."
source .venv/bin/activate

echo "🚀 STARTING FRESH..."
./start.sh

