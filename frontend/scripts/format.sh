#!/bin/bash

# Frontend Format Script
# Automatically formats all frontend code using Prettier

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$FRONTEND_DIR"

echo "========================================"
echo "Frontend Code Formatting"
echo "========================================"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    echo ""
fi

echo "Formatting code with Prettier..."
npm run format

echo ""
echo "========================================"
echo "✓ Code formatting complete!"
echo "========================================"
