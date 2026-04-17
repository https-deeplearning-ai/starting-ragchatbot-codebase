#!/usr/bin/env bash
# Frontend quality checks: Prettier formatting + ESLint linting
# Run from the repo root: ./scripts/check-frontend.sh
# Pass --fix to auto-fix formatting and lint issues: ./scripts/check-frontend.sh --fix

set -euo pipefail

FRONTEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../frontend" && pwd)"
FIX_MODE=false

for arg in "$@"; do
  if [[ "$arg" == "--fix" ]]; then
    FIX_MODE=true
  fi
done

echo "==> Frontend quality checks"
echo "    Directory: $FRONTEND_DIR"

# Ensure node_modules are installed
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo ""
  echo "==> Installing dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

echo ""
if $FIX_MODE; then
  echo "==> [1/2] Prettier (format)"
  (cd "$FRONTEND_DIR" && npx prettier --write .)
  echo ""
  echo "==> [2/2] ESLint (lint + fix)"
  (cd "$FRONTEND_DIR" && npx eslint --fix script.js)
  echo ""
  echo "All issues fixed."
else
  echo "==> [1/2] Prettier (check formatting)"
  (cd "$FRONTEND_DIR" && npx prettier --check .)
  echo ""
  echo "==> [2/2] ESLint (lint)"
  (cd "$FRONTEND_DIR" && npx eslint script.js)
  echo ""
  echo "All checks passed."
  echo ""
  echo "Tip: run with --fix to auto-correct formatting and lint issues."
fi
