#!/bin/bash

# RAG Chatbot Startup Script with Performance Options
# Usage: ./run.sh [mode]
# Modes: fast (default), quick, full, preload

set -e

# Get mode from argument or use default
MODE=${1:-fast}

echo "🚀 Starting RAG Chatbot in '$MODE' mode..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Set environment variables based on mode
case $MODE in
    "fast")
        export LAZY_LOADING=true
        export BACKGROUND_DOCUMENT_PROCESSING=true
        export QUICK_START=false
        export PRELOAD_COMPONENTS=false
        echo "⚡ Fast Mode - Lazy loading + background processing"
        ;;
    "quick")
        export LAZY_LOADING=true
        export BACKGROUND_DOCUMENT_PROCESSING=false
        export QUICK_START=true
        export PRELOAD_COMPONENTS=false
        echo "🚀 Quick Start Mode - Lazy loading only, no document processing"
        ;;
    "preload")
        export LAZY_LOADING=false
        export BACKGROUND_DOCUMENT_PROCESSING=false
        export QUICK_START=false
        export PRELOAD_COMPONENTS=true
        echo "⏳ Preload Mode - All components loaded upfront"
        ;;
    "full")
        export LAZY_LOADING=false
        export BACKGROUND_DOCUMENT_PROCESSING=false
        export QUICK_START=false
        export PRELOAD_COMPONENTS=false
        echo "🔧 Full Mode - Traditional startup (for comparison)"
        ;;
    *)
        echo "❌ Unknown mode: $MODE"
        echo "Available modes: fast, quick, preload, full"
        exit 1
        ;;
esac

echo ""
echo "🔧 Configuration:"
echo "   - LAZY_LOADING: ${LAZY_LOADING:-false}"
echo "   - BACKGROUND_DOCUMENT_PROCESSING: ${BACKGROUND_DOCUMENT_PROCESSING:-false}"
echo "   - QUICK_START: ${QUICK_START:-false}"
echo "   - PRELOAD_COMPONENTS: ${PRELOAD_COMPONENTS:-false}"
echo "   - EMBEDDING_MODEL: ${EMBEDDING_MODEL:-all-MiniLM-L6-v2}"
echo ""

# Navigate to backend directory
cd backend

# Record start time
START_TIME=$(date +%s)

# Start the application
echo "🌟 Starting FastAPI server..."
echo "📍 Server will be available at: http://localhost:8000"
echo "📊 API docs at: http://localhost:8000/docs"
echo "🔄 Processing status at: http://localhost:8000/api/processing-status"
echo ""

# Run uvicorn with optimized settings
uv run uvicorn app:app --reload --port 8000 --log-level info

# Note: The script doesn't reach here since uvicorn runs indefinitely
# The timing information would be shown in the startup logs
