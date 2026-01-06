#!/bin/bash
# Format Python code using isort and black

set -e

echo "🔧 Formatting Python code..."

echo "📦 Running isort..."
uv run isort backend/ *.py

echo "🎨 Running black..."
uv run black backend/ *.py

echo "✅ Code formatting complete!"
