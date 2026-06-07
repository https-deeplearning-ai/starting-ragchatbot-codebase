#!/bin/bash
# Apply black formatting and ruff import-sort fixes in place.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== black (format) ==="
uv run black "$ROOT/backend" "$ROOT/main.py"

echo "=== ruff (fix imports) ==="
uv run ruff check --fix "$ROOT/backend" "$ROOT/main.py"

echo "Formatting complete."
