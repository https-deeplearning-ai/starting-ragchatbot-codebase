#!/bin/bash
# Script to set up and run Playwright tests for theme toggle verification

set -e

echo "=== Theme Toggle Playwright Test Setup ==="
echo ""

# Install Playwright and pytest-playwright
echo "Installing Playwright dependencies..."
uv pip install playwright pytest-playwright

# Install Playwright browsers
echo "Installing Playwright browsers..."
python -m playwright install chromium

# Create screenshots directory
mkdir -p backend/tests/screenshots

echo ""
echo "=== Starting Application ==="
# Start the application in the background
./run.sh &
APP_PID=$!

# Wait for the application to start
echo "Waiting for application to start on port 8000..."
sleep 5

# Check if the application is running
if ! curl -s http://localhost:8000 > /dev/null; then
    echo "Error: Application failed to start on port 8000"
    kill $APP_PID 2>/dev/null || true
    exit 1
fi

echo "Application is running!"
echo ""

# Run the Playwright tests
echo "=== Running Playwright Tests ==="
pytest backend/tests/test_frontend_theme_toggle.py -v

# Capture the test result
TEST_RESULT=$?

# Stop the application
echo ""
echo "=== Stopping Application ==="
kill $APP_PID 2>/dev/null || true
wait $APP_PID 2>/dev/null || true

# Display results
echo ""
echo "=== Test Results ==="
if [ $TEST_RESULT -eq 0 ]; then
    echo "✓ All tests passed!"
    echo ""
    echo "Screenshots saved to: backend/tests/screenshots/"
    ls -lh backend/tests/screenshots/ 2>/dev/null || true
else
    echo "✗ Some tests failed. Please review the output above."
fi

exit $TEST_RESULT
