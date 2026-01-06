#!/bin/bash
# Run linting and type checking

set -e

echo "🔍 Running code quality checks..."

echo "📋 Running flake8..."
uv run flake8 backend/ *.py

echo "🔬 Running mypy..."
uv run mypy backend/ *.py

echo "✅ All linting checks passed!"
