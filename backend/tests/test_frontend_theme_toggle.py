"""
Playwright test to verify the theme toggle button positioning.

This test ensures that the CSS fix (position: relative on .theme-toggle)
correctly positions the SVG icons within the button.
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def base_url():
    """Base URL for the application."""
    return "http://localhost:8000"


def test_theme_toggle_button_exists(page: Page, base_url: str):
    """Test that the theme toggle button exists and is visible."""
    page.goto(base_url)
    theme_toggle = page.locator("#themeToggle")
    expect(theme_toggle).to_be_visible()


def test_theme_toggle_button_positioning(page: Page, base_url: str):
    """Test that the theme toggle button has correct CSS positioning."""
    page.goto(base_url)

    theme_toggle = page.locator("#themeToggle")

    # Verify the button has position: relative
    position = theme_toggle.evaluate("el => window.getComputedStyle(el).position")
    assert position == "relative", f"Expected position: relative, got {position}"

    # Verify button dimensions
    box = theme_toggle.bounding_box()
    assert box is not None, "Theme toggle button should have bounding box"
    assert box["width"] == 40, f"Expected width 40px, got {box['width']}px"
    assert box["height"] == 40, f"Expected height 40px, got {box['height']}px"


def test_theme_toggle_svg_icons_positioning(page: Page, base_url: str):
    """Test that the SVG icons are correctly positioned within the button."""
    page.goto(base_url)

    # Get the button and its icons
    theme_toggle = page.locator("#themeToggle")
    moon_icon = theme_toggle.locator(".moon-icon")
    sun_icon = theme_toggle.locator(".sun-icon")

    # Both icons should exist
    expect(moon_icon).to_be_attached()
    expect(sun_icon).to_be_attached()

    # Check that moon icon is visible in dark theme (default)
    moon_opacity = moon_icon.evaluate("el => window.getComputedStyle(el).opacity")
    assert float(moon_opacity) == 1.0, f"Moon icon should be visible in dark theme, opacity: {moon_opacity}"

    # Check that sun icon is hidden in dark theme
    sun_opacity = sun_icon.evaluate("el => window.getComputedStyle(el).opacity")
    assert float(sun_opacity) == 0.0, f"Sun icon should be hidden in dark theme, opacity: {sun_opacity}"

    # Verify the SVG icons have position: absolute
    moon_position = moon_icon.evaluate("el => window.getComputedStyle(el).position")
    sun_position = sun_icon.evaluate("el => window.getComputedStyle(el).position")
    assert moon_position == "absolute", f"Moon icon should have position: absolute, got {moon_position}"
    assert sun_position == "absolute", f"Sun icon should have position: absolute, got {sun_position}"


def test_theme_toggle_functionality(page: Page, base_url: str):
    """Test that clicking the theme toggle switches themes correctly."""
    page.goto(base_url)

    theme_toggle = page.locator("#themeToggle")
    body = page.locator("body")

    # Initially should be dark theme (no data-theme attribute or data-theme="dark")
    initial_theme = body.get_attribute("data-theme")
    assert initial_theme is None or initial_theme == "dark", f"Expected dark theme initially, got {initial_theme}"

    # Click to switch to light theme
    theme_toggle.click()
    page.wait_for_timeout(500)  # Wait for transition

    # Should now be light theme
    current_theme = body.get_attribute("data-theme")
    assert current_theme == "light", f"Expected light theme after click, got {current_theme}"

    # Verify sun icon is now visible
    sun_icon = theme_toggle.locator(".sun-icon")
    moon_icon = theme_toggle.locator(".moon-icon")

    sun_opacity = sun_icon.evaluate("el => window.getComputedStyle(el).opacity")
    moon_opacity = moon_icon.evaluate("el => window.getComputedStyle(el).opacity")

    assert float(sun_opacity) == 1.0, f"Sun icon should be visible in light theme, opacity: {sun_opacity}"
    assert float(moon_opacity) == 0.0, f"Moon icon should be hidden in light theme, opacity: {moon_opacity}"

    # Click again to switch back to dark theme
    theme_toggle.click()
    page.wait_for_timeout(500)  # Wait for transition

    # Should be back to dark theme
    final_theme = body.get_attribute("data-theme")
    assert final_theme is None or final_theme == "dark", f"Expected dark theme after second click, got {final_theme}"


def test_theme_toggle_visual_regression(page: Page, base_url: str):
    """Visual regression test for the theme toggle button."""
    page.goto(base_url)
    page.wait_for_load_state("networkidle")

    # Take screenshot of header area with theme toggle
    header = page.locator(".header-bar")
    header.screenshot(path="backend/tests/screenshots/theme-toggle-dark.png")

    # Switch to light theme
    theme_toggle = page.locator("#themeToggle")
    theme_toggle.click()
    page.wait_for_timeout(500)

    # Take screenshot of light theme
    header.screenshot(path="backend/tests/screenshots/theme-toggle-light.png")
