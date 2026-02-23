#!/bin/bash
# Run code quality checks for the project

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  format    Run black to format all Python files"
    echo "  check     Run black in check mode (no changes, exit 1 if unformatted)"
    echo "  test      Run pytest"
    echo "  all       Run all checks (check + test)"
    echo ""
    echo "If no command is given, 'all' is used."
}

run_format() {
    echo -e "${YELLOW}Formatting code with black...${NC}"
    uv run --group dev black backend/ main.py
    echo -e "${GREEN}Formatting complete.${NC}"
}

run_check() {
    echo -e "${YELLOW}Checking formatting with black...${NC}"
    if uv run --group dev black --check backend/ main.py; then
        echo -e "${GREEN}All files are properly formatted.${NC}"
    else
        echo -e "${RED}Some files need formatting. Run '$0 format' to fix.${NC}"
        return 1
    fi
}

run_test() {
    echo -e "${YELLOW}Running tests...${NC}"
    uv run pytest backend/tests/ -v
    echo -e "${GREEN}Tests passed.${NC}"
}

run_all() {
    run_check
    run_test
    echo -e "${GREEN}All quality checks passed.${NC}"
}

COMMAND="${1:-all}"

case "$COMMAND" in
    format) run_format ;;
    check)  run_check ;;
    test)   run_test ;;
    all)    run_all ;;
    -h|--help) usage ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        usage
        exit 1
        ;;
esac
