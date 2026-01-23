#!/bin/bash
# Run all code quality checks (format check + lint)

set -e

cd "$(dirname "$0")/.."

echo "=== Code Quality Checks ==="
echo

echo "1. Checking formatting with black..."
uv run black --check backend/ main.py
echo "   Formatting OK!"
echo

echo "2. Running ruff linter..."
uv run ruff check backend/ main.py
echo "   Linting OK!"
echo

echo "=== All quality checks passed! ==="
