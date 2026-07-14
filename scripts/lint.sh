#!/bin/bash
# Check Python formatting with Black (no writes).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Checking Python formatting with Black..."
uv run black --check --diff backend/ main.py
echo "Formatting check passed."
