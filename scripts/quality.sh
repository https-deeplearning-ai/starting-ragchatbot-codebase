#!/bin/bash
# Run the full development quality suite.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Code quality checks ==="
echo

echo "1/2 Formatting (Black)..."
uv run black --check --diff backend/ main.py
echo

echo "2/2 Tests (pytest)..."
uv run pytest backend/tests/ -v
echo

echo "=== All quality checks passed ==="
