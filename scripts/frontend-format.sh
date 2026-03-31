#!/usr/bin/env bash
# Format all frontend files using Prettier.
# Modifies files in place.
set -e
cd "$(dirname "$0")/.."

echo "Formatting frontend files with Prettier..."
npx prettier --write "frontend/**/*.{js,css,html}"
echo "Formatting complete."
