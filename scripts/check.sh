#!/bin/bash
# Verify formatting without writing any files. Exits non-zero if anything is unformatted.
# Usage: ./scripts/check.sh
set -uo pipefail

cd "$(dirname "$0")/.."

failed=0

echo "==> isort --check-only (backend)"
uv run isort --check-only --diff backend main.py || failed=1

echo "==> black --check (backend)"
uv run black --check --diff backend main.py || failed=1

if [ ! -d node_modules ]; then
    echo "==> installing frontend dev dependencies"
    npm install --silent
fi

echo "==> prettier --check (frontend)"
npm run --silent format:check || failed=1

echo
if [ "$failed" -ne 0 ]; then
    echo "Formatting check FAILED. Run ./scripts/format.sh to fix."
    exit 1
fi

echo "Formatting check passed."
