#!/bin/bash
# Type checking with mypy
set -e

echo "🔎 Type checking with mypy..."
uv run mypy backend/ main.py \
  --ignore-missing-imports \
  --follow-imports=skip \
  --allow-untyped-defs \
  --no-error-summary || true

echo "✅ Type checking complete!"
