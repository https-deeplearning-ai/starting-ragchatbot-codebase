#!/bin/bash

# Format all Python files with black
# Using Python 3.11 for torch compatibility
echo "Formatting Python files with black..."
uv run --python 3.11 --extra dev black backend/ main.py

echo "Done! All files formatted."
