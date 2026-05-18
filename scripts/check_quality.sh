#!/usr/bin/env bash
# Run all quality checks (non-destructive — exits non-zero if anything fails)
set -e
cd "$(dirname "$0")/.."

echo "==> black (format check)"
uv run black --check backend/

echo ""
echo "All quality checks passed."
