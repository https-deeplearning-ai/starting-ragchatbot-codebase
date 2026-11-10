#!/bin/bash
# Run every quality gate: formatting, linting, and tests. Use before committing.
set -euo pipefail
cd "$(dirname "$0")/.."

./scripts/lint.sh

echo "==> pytest"
uv run pytest
