#!/bin/bash
# Run linting checks

echo "Running Flake8..."
uv run flake8 backend/ main.py

echo "Running MyPy..."
uv run mypy backend/ main.py

echo "Linting complete!"
