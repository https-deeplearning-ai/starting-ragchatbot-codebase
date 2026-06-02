#!/bin/bash
# Auto-fix code issues (formatting and import ordering)
set -e

echo "🔧 Auto-fixing code issues..."
echo ""

echo "1. Running ruff with --fix..."
uv run ruff check --fix backend/ main.py
echo ""

echo "2. Running black formatter..."
uv run black backend/ main.py
echo ""

echo "✅ Auto-fixes complete!"
