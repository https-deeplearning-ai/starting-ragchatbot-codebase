#!/bin/bash
set -e

echo "Running Black formatter..."
uv run black backend/

echo "Running Ruff import organizer..."
uv run ruff check --select I --fix backend/

echo "✓ Formatting complete!"
