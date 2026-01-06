#!/bin/bash
# Run all quality checks: formatting, linting, and tests

set -e

echo "🚀 Running all quality checks..."
echo ""

# Check formatting (without modifying files)
echo "1️⃣  Checking code formatting..."
uv run black --check backend/ *.py
uv run isort --check-only backend/ *.py
echo "✅ Format check passed!"
echo ""

# Run linting
echo "2️⃣  Running linting..."
uv run flake8 backend/ *.py
echo "✅ Flake8 passed!"
echo ""

# Run type checking
echo "3️⃣  Running type checking..."
uv run mypy backend/ *.py
echo "✅ Type checking passed!"
echo ""

# Run tests
echo "4️⃣  Running tests..."
cd backend
uv run pytest
cd ..
echo "✅ Tests passed!"
echo ""

echo "🎉 All quality checks passed successfully!"
