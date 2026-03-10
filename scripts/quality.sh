#!/usr/bin/env bash
# Development quality checks: formatting and tests
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

run_format() {
    echo "=== Formatting: black ==="
    uv run black backend/ main.py
    echo "Formatting complete."
}

run_check() {
    echo "=== Format check: black --check ==="
    uv run black --check backend/ main.py
    echo "Format check passed."
}

run_tests() {
    echo "=== Tests: pytest ==="
    uv run pytest
}

case "${1:-}" in
    format)
        run_format
        ;;
    check)
        run_check
        ;;
    test)
        run_tests
        ;;
    all)
        run_check
        run_tests
        ;;
    *)
        echo "Usage: $0 {format|check|test|all}"
        echo ""
        echo "  format  Apply black formatting to all Python files"
        echo "  check   Verify all Python files are black-formatted (CI-safe)"
        echo "  test    Run pytest test suite"
        echo "  all     Run format check + tests"
        exit 1
        ;;
esac
