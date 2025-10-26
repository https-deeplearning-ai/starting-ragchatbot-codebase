#!/bin/bash

# Code Formatting Script
# This script formats all Python code in the project using black and isort

set -e

echo "🎨 Formatting Python code..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Activated virtual environment"
fi

# Check if required tools are installed
echo "🔧 Checking for code formatting tools..."
if ! command -v black &> /dev/null; then
    echo "❌ Black is not installed. Run: uv add black"
    exit 1
fi

if ! command -v isort &> /dev/null; then
    echo "❌ isort is not installed. Run: uv add isort"
    exit 1
fi

# Format code with black
echo "⚫ Running black formatter..."
black backend/

# Sort imports with isort
echo "📚 Sorting imports with isort..."
isort backend/

echo "✅ Code formatting complete!"
echo "🎉 All Python files have been formatted and imports sorted."