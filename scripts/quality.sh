#!/bin/bash
set -e

echo "========================================="
echo "Running Code Quality Checks"
echo "========================================="
echo ""

echo "Step 1/3: Formatting check..."
uv run black --check backend/
echo "✓ Formatting OK"
echo ""

echo "Step 2/3: Linting..."
uv run ruff check backend/
uv run mypy backend/
echo "✓ Linting OK"
echo ""

echo "Step 3/3: Tests..."
uv run pytest backend/tests/ -v
echo "✓ Tests OK"
echo ""

echo "========================================="
echo "All quality checks passed! 🎉"
echo "========================================="
