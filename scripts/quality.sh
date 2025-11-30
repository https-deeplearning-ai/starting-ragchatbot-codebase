#!/bin/bash
# Run all code quality checks

echo "=== Running Code Quality Checks ==="
echo ""

# Format check
echo "1. Checking code formatting..."
uv run black --check backend/ main.py

if [ $? -ne 0 ]; then
    echo "❌ Code formatting issues found. Run ./scripts/format.sh to fix."
    exit 1
fi

echo "✅ Code formatting OK"
echo ""

# Import sorting check
echo "2. Checking import sorting..."
uv run isort --check-only backend/ main.py

if [ $? -ne 0 ]; then
    echo "❌ Import sorting issues found. Run ./scripts/format.sh to fix."
    exit 1
fi

echo "✅ Import sorting OK"
echo ""

# Linting
echo "3. Running flake8 linter..."
uv run flake8 backend/ main.py --max-line-length=88 --extend-ignore=E203,W503

if [ $? -ne 0 ]; then
    echo "❌ Linting issues found."
    exit 1
fi

echo "✅ Linting OK"
echo ""

# Type checking
echo "4. Running mypy type checker..."
uv run mypy backend/ main.py

if [ $? -ne 0 ]; then
    echo "❌ Type checking issues found."
    exit 1
fi

echo "✅ Type checking OK"
echo ""

echo "==================================="
echo "✨ All quality checks passed! ✨"
echo "==================================="
