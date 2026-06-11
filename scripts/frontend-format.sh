#!/usr/bin/env bash
# Auto-format all frontend files with Prettier.
set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/../frontend" && pwd)"

echo "==> Formatting frontend files with Prettier"
cd "$FRONTEND_DIR"
npx prettier --write .

echo "Done."
