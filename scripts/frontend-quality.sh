#!/usr/bin/env bash
# Run all frontend quality checks from the project root.
set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

echo "==> Frontend quality checks"

echo ""
echo "--- Prettier (format check) ---"
cd "$FRONTEND_DIR"
npx prettier --check .

echo ""
echo "--- ESLint ---"
npx eslint script.js

echo ""
echo "All frontend quality checks passed."
