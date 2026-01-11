#!/bin/bash

# Create necessary directories
mkdir -p docs 

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "Error: backend directory not found"
    exit 1
fi

echo "Starting Course Materials RAG System..."
echo "Make sure you have set your ANTHROPIC_API_KEY in .env"

# Change to backend directory and start the server
# Using Python 3.11 for torch compatibility with Intel Mac
cd backend && uv run --python 3.11 uvicorn app:app --reload --port 8000