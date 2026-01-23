#!/bin/bash
# Format code with black and fix imports with ruff

set -e

cd "$(dirname "$0")/.."

echo "Running black formatter..."
uv run black backend/ main.py

echo "Running ruff import sorting..."
uv run ruff check --fix --select I backend/ main.py

echo "Formatting complete!"
