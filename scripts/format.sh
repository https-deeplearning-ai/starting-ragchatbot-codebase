#!/bin/bash
# Auto-format the codebase: fix lint issues (incl. import order), then apply black.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> ruff (autofix lint + import sorting)"
uv run ruff check --fix .

echo "==> black (format)"
uv run black .
