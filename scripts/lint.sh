#!/bin/bash
# Check-only: fail if code is not black-formatted or has lint errors. Changes nothing.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> black (check)"
uv run black --check --diff .

echo "==> ruff (lint)"
uv run ruff check .
