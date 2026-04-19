#!/usr/bin/env bash
# Frontend quality checks: formatting (Prettier) and linting (ESLint)
# Usage: ./scripts/check-frontend.sh [--fix]

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"
FIX=false

for arg in "$@"; do
    case $arg in
        --fix) FIX=true ;;
        *) echo "Unknown argument: $arg" && exit 1 ;;
    esac
done

echo "==> Installing frontend dependencies..."
cd "$FRONTEND_DIR"
npm install --silent

if [ "$FIX" = true ]; then
    echo "==> Auto-fixing: formatting with Prettier..."
    npm run format

    echo "==> Auto-fixing: linting with ESLint..."
    npm run lint:fix

    echo "==> All fixes applied."
else
    echo "==> Checking formatting with Prettier..."
    npm run format:check

    echo "==> Linting with ESLint..."
    npm run lint

    echo "==> All checks passed."
fi
