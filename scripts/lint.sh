#!/bin/bash
set -e

echo "Running Ruff linter..."
uv run ruff check backend/

echo "Running mypy type checker..."
uv run mypy backend/

echo "✓ All linting checks passed!"
