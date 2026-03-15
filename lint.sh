#!/usr/bin/env bash
# Run all frontend code quality checks.
# Usage: ./lint.sh [--fix]

set -e

cd "$(dirname "$0")/frontend"

# Install deps if needed
if [ ! -d node_modules ]; then
  echo "Installing frontend dev dependencies..."
  npm install
fi

if [ "$1" = "--fix" ]; then
  echo "Formatting frontend files with Prettier..."
  npx prettier --write .
  echo "Done."
else
  echo "Checking frontend formatting with Prettier..."
  npx prettier --check .
  echo "All checks passed."
fi
