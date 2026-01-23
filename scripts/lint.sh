#!/bin/bash
# Run linting checks with ruff

set -e

cd "$(dirname "$0")/.."

echo "Running ruff linter..."
uv run ruff check backend/ main.py

echo "Linting complete!"
