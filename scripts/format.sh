#!/bin/bash
# Format Python code with black
set -e

echo "🎨 Formatting code with black..."
uv run black backend/ main.py

echo "✅ Code formatting complete!"
