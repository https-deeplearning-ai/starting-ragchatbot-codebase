#!/bin/bash

# Format code with isort and black
echo "Sorting imports with isort..."
uv run isort backend/ main.py

echo ""
echo "Formatting code with black..."
uv run black backend/ main.py

echo ""
echo "Code formatting complete!"
