#!/usr/bin/env bash
set -e

echo "=== Checking formatting (black) ==="
uv run black --check .

echo "=== Running tests (pytest) ==="
uv run pytest

echo "=== All checks passed ==="
