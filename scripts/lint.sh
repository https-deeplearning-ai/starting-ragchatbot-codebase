#!/bin/bash
# Run all code quality checks. Exit non-zero if any check fails.
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== black (format check) ==="
uv run black --check "$ROOT/backend" "$ROOT/main.py"

echo "=== ruff (lint) ==="
uv run ruff check "$ROOT/backend" "$ROOT/main.py"

echo "All quality checks passed."
