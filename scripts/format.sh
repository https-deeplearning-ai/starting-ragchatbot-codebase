#!/bin/bash
# Format code with Black and isort

echo "Running Black formatter..."
uv run black backend/ main.py

echo "Running isort..."
uv run isort backend/ main.py

echo "Code formatting complete!"
