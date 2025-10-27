#!/bin/bash

# Pre-commit Hook Script
# This script runs code quality checks before allowing commits

set -e

echo "🚦 Running pre-commit checks..."

# Run the main quality check script
if ./scripts/check-quality.sh; then
    echo "✅ Pre-commit checks passed!"
    echo "🎉 Ready to commit!"
    exit 0
else
    echo "❌ Pre-commit checks failed!"
    echo ""
    echo "Please fix the issues before committing:"
    echo "  1. Run: ./scripts/format.sh (to fix formatting)"
    echo "  2. Run: ./scripts/check-quality.sh (to see remaining issues)"
    echo ""
    echo "If you want to skip these checks, use:"
    echo "  git commit --no-verify"
    exit 1
fi