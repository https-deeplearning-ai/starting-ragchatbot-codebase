#!/bin/bash

# Run all code quality checks
echo "==================================="
echo "Running Code Quality Checks"
echo "==================================="

# Track if any check fails
FAILED=0

# Check Black formatting
echo ""
echo "Checking code formatting with Black..."
if ! uv run black --check backend/ main.py; then
    echo "Black check failed! Run './format.sh' to fix formatting."
    FAILED=1
else
    echo "Black check passed!"
fi

# Check isort
echo ""
echo "Checking import sorting with isort..."
if ! uv run isort --check-only backend/ main.py; then
    echo "Isort check failed! Run './format.sh' to fix imports."
    FAILED=1
else
    echo "Isort check passed!"
fi

# Run flake8
echo ""
echo "Running flake8 linter..."
if ! uv run flake8 backend/ main.py; then
    echo "Flake8 check failed!"
    FAILED=1
else
    echo "Flake8 check passed!"
fi

# Run mypy type checking
echo ""
echo "Running mypy type checker..."
if ! uv run mypy backend/ main.py; then
    echo "Mypy check failed!"
    FAILED=1
else
    echo "Mypy check passed!"
fi

# Summary
echo ""
echo "==================================="
if [ $FAILED -eq 0 ]; then
    echo "All quality checks passed!"
    exit 0
else
    echo "Some quality checks failed!"
    exit 1
fi
