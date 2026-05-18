#!/usr/bin/env bash
# Auto-format all Python files with black
set -e
cd "$(dirname "$0")/.."
uv run black backend/
