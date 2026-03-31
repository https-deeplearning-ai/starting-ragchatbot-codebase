#!/usr/bin/env bash
# Lint frontend files without modifying them.
# Exits with a non-zero code if any check fails.
set -e
cd "$(dirname "$0")/.."

echo "Checking formatting with Prettier..."
npx prettier --check "frontend/**/*.{js,css,html}"

echo "Linting JavaScript with ESLint..."
npx eslint frontend/script.js

echo "All frontend checks passed."
