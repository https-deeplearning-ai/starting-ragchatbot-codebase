#!/bin/bash

# Frontend Quality Check Script
# Runs formatting and linting checks on the frontend code

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$FRONTEND_DIR"

echo "========================================"
echo "Frontend Code Quality Check"
echo "========================================"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    echo ""
fi

echo "1. Checking code formatting with Prettier..."
echo "----------------------------------------"
if npm run format:check; then
    echo "✓ All files are properly formatted"
else
    echo "✗ Some files need formatting. Run 'npm run format' to fix."
    exit 1
fi
echo ""

echo "2. Running ESLint..."
echo "----------------------------------------"
if npm run lint; then
    echo "✓ No linting errors found"
else
    echo "✗ Linting errors found. Run 'npm run lint:fix' to auto-fix where possible."
    exit 1
fi
echo ""

echo "========================================"
echo "✓ All quality checks passed!"
echo "========================================"
