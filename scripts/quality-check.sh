#!/bin/bash
# Run all code quality checks

set -e  # Exit on any error

echo "========================================"
echo "Running Code Quality Checks"
echo "========================================"

echo ""
echo "1. Checking code formatting with Black..."
uv run black --check backend/ main.py

echo ""
echo "2. Checking import sorting with isort..."
uv run isort --check-only backend/ main.py

echo ""
echo "3. Running Flake8 linting..."
uv run flake8 backend/ main.py

echo ""
echo "4. Running MyPy type checking..."
uv run mypy backend/ main.py

echo ""
echo "========================================"
echo "All quality checks passed!"
echo "========================================"
