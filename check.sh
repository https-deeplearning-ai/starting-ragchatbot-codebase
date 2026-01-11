#!/bin/bash

# Run code quality checks
# Using Python 3.11 for torch compatibility
echo "Running code quality checks..."
echo ""

# Check formatting with black
echo "Checking formatting with black..."
uv run --python 3.11 --extra dev black --check backend/ main.py

if [ $? -eq 0 ]; then
    echo "All checks passed!"
else
    echo ""
    echo "Formatting issues found. Run ./format.sh to fix them."
    exit 1
fi
