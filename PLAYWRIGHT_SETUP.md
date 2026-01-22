# Playwright Frontend Testing Setup

This document describes how to set up and run Playwright tests to verify frontend changes, specifically for the theme toggle button positioning fix.

## What Was Fixed

The PR adds `position: relative` to the `.theme-toggle` button in `frontend/style.css` (line 856). This ensures that the absolutely positioned SVG icons (sun and moon) are correctly positioned within the button container.

## Installation

1. Install Playwright and pytest-playwright:
   ```bash
   uv pip install playwright pytest-playwright
   ```

2. Install Playwright browsers (Chromium is sufficient):
   ```bash
   python -m playwright install chromium
   ```

## Running the Tests

1. Start the application:
   ```bash
   ./run.sh
   ```

2. In a separate terminal, run the Playwright tests:
   ```bash
   pytest backend/tests/test_frontend_theme_toggle.py -v
   ```

## Test Coverage

The test file `backend/tests/test_frontend_theme_toggle.py` includes:

1. **test_theme_toggle_button_exists**: Verifies the theme toggle button is visible
2. **test_theme_toggle_button_positioning**: Checks that the button has `position: relative` and correct dimensions (40x40px)
3. **test_theme_toggle_svg_icons_positioning**: Verifies SVG icons have `position: absolute` and correct opacity in dark theme
4. **test_theme_toggle_functionality**: Tests clicking the button switches themes correctly
5. **test_theme_toggle_visual_regression**: Takes screenshots for visual verification

## What the Tests Verify

### CSS Positioning
- Button has `position: relative` (the fix)
- SVG icons have `position: absolute`
- Button dimensions are 40x40px

### Visual Behavior
- Moon icon is visible (opacity: 1) in dark theme (default)
- Sun icon is hidden (opacity: 0) in dark theme
- Clicking the button switches to light theme
- Icons switch visibility when theme changes

### Visual Regression
- Screenshots are saved to `backend/tests/screenshots/`
- `theme-toggle-dark.png`: Dark theme appearance
- `theme-toggle-light.png`: Light theme appearance

## Expected Results

All tests should pass, confirming that:
1. The CSS fix correctly positions the button as relative
2. The SVG icons are properly positioned within the button
3. The theme toggle functionality works correctly
4. The visual appearance matches expectations

## Quick Test Script

For convenience, you can run:
```bash
bash test_theme_toggle.sh
```

This script will:
1. Install dependencies
2. Start the application
3. Run all tests
4. Save screenshots
5. Stop the application
6. Report results
