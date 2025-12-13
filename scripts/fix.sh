#!/bin/bash
set -e

echo "Auto-fixing code quality issues..."

echo "1. Formatting with Black..."
uv run black backend/

echo "2. Fixing auto-fixable linting issues..."
uv run ruff check --fix backend/

echo "✓ Auto-fixes applied! Run 'scripts/quality.sh' to verify."
