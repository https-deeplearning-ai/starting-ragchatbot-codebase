#!/bin/bash
# Comprehensive code quality checks (format, lint, type-check, and test)
set -e

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "       🚀 Running Code Quality Checks          "
echo "================================================"
echo ""

echo "Step 1/4: Code Formatting"
echo "------------------------"
bash "$SCRIPTS_DIR/format.sh"
echo ""

echo "Step 2/4: Code Linting"
echo "---------------------"
bash "$SCRIPTS_DIR/lint.sh"
echo ""

echo "Step 3/4: Type Checking"
echo "----------------------"
bash "$SCRIPTS_DIR/type-check.sh"
echo ""

echo "Step 4/4: Running Tests"
echo "----------------------"
uv run pytest backend/tests/ -v
echo ""

echo "================================================"
echo "✨ All quality checks passed!                 "
echo "================================================"
