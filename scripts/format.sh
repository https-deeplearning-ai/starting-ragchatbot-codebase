#!/bin/bash
# Apply all formatters in place: isort + black for the backend, Prettier for the frontend.
# Usage: ./scripts/format.sh
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> isort (backend)"
uv run isort backend main.py

echo "==> black (backend)"
uv run black backend main.py

if [ ! -d node_modules ]; then
    echo "==> installing frontend dev dependencies"
    npm install --silent
fi

echo "==> prettier (frontend)"
npm run --silent format

echo
echo "All formatters applied."
