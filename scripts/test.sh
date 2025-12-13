#!/bin/bash
set -e

echo "Running pytest..."
uv run pytest backend/tests/ -v

echo "✓ All tests passed!"
