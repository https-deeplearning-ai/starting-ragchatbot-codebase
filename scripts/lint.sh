#!/bin/bash
# Run linting checks on the codebase

echo "Running flake8 linter..."
uv run flake8 backend/ main.py --max-line-length=88 --extend-ignore=E203,W503

echo ""
echo "Running mypy type checker..."
uv run mypy backend/ main.py

echo ""
echo "✅ Linting complete!"
