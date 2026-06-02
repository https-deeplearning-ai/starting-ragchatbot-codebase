#!/bin/bash
# Lint Python code with ruff
set -e

echo "🔍 Linting code with ruff..."
uv run ruff check backend/ main.py

echo "✅ Linting complete!"
