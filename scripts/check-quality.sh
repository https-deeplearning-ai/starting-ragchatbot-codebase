#!/bin/bash

# Code Quality Check Script
# This script runs all code quality checks (black, isort, flake8, mypy)

set -e

EXIT_CODE=0

echo "🔍 Running code quality checks..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Activated virtual environment"
fi

# Function to run a check and handle failures
run_check() {
    local tool_name="$1"
    local tool_command="$2"

    echo "🔧 Running $tool_name..."
    if eval "$tool_command"; then
        echo "✅ $tool_name passed"
        return 0
    else
        echo "❌ $tool_name failed"
        EXIT_CODE=1
        return 1
    fi
}

# Check code formatting with black
run_check "Black formatting check" "black --check backend/"

# Check import sorting with isort
run_check "Import sorting check" "isort --check-only backend/"

# Check code style with flake8
run_check "Flake8 linting" "flake8 backend/"

# Type checking with mypy (optional - may fail on untyped code)
echo "🔧 Running MyPy type checking..."
if mypy backend/ --ignore-missing-imports --no-strict-optional; then
    echo "✅ MyPy type checking passed"
else
    echo "⚠️  MyPy type checking found issues (optional check)"
fi

# Run tests if they exist
if [ -d "backend/tests" ]; then
    run_check "Tests" "cd backend && python -m pytest tests/ -v"
fi

if [ $EXIT_CODE -eq 0 ]; then
    echo "🎉 All required code quality checks passed!"
else
    echo "💥 Some code quality checks failed!"
    echo ""
    echo "To fix formatting issues, run:"
    echo "  ./scripts/format.sh"
    echo ""
    echo "To see flake8 issues in detail, run:"
    echo "  flake8 backend/"
fi

exit $EXIT_CODE