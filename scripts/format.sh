#!/bin/bash
# Format Python source with Black.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "Formatting Python code with Black..."
uv run black backend/ main.py
echo "Formatting complete."
