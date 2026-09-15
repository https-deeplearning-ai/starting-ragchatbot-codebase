#!/bin/bash
# Full quality gate: formatting checks followed by the test suite.
# This is the one to run before committing (and the one CI should call).
# Usage: ./scripts/quality.sh
set -uo pipefail

cd "$(dirname "$0")/.."

failed=0

./scripts/check.sh || failed=1

echo
echo "==> pytest"
uv run pytest || failed=1

echo
if [ "$failed" -ne 0 ]; then
    echo "Quality gate FAILED."
    exit 1
fi

echo "Quality gate passed."
