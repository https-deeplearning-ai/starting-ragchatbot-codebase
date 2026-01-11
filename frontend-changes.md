# Frontend Changes: Dark/Light Theme Toggle

## Overview
Added a theme toggle button that allows users to switch between dark and light themes with smooth transitions and persistent preferences.

## Files Modified

### 1. `frontend/index.html`
- Added a theme toggle button positioned at the top-right of the page
- Button includes sun and moon SVG icons for visual indication
- Includes accessibility attributes (`aria-label`, `title`) for screen readers

### 2. `frontend/style.css`
- Added light theme CSS variables under `[data-theme="light"]` selector
- Added `--code-bg` variable for code block backgrounds
- Added `.theme-toggle` button styles including:
  - Fixed positioning in top-right corner
  - Hover, focus, and active states
  - Icon toggle visibility based on current theme
- Added smooth transition animations for theme switching on key elements

### 3. `frontend/script.js`
- Added `themeToggle` DOM element reference
- Added `initTheme()` function to load saved theme preference from localStorage
- Added `toggleTheme()` function to switch between themes
- Added `setTheme(theme)` function to apply theme and persist to localStorage
- Theme toggle event listener added to `setupEventListeners()`

## Features

### Toggle Button
- Positioned in top-right corner (fixed position)
- Circular button with sun/moon icons
- Smooth scale animation on hover/click
- Keyboard accessible (focusable, works with Enter/Space)

### Light Theme Colors
| Variable | Dark Theme | Light Theme |
|----------|-----------|-------------|
| `--background` | `#0f172a` | `#f8fafc` |
| `--surface` | `#1e293b` | `#ffffff` |
| `--surface-hover` | `#334155` | `#f1f5f9` |
| `--text-primary` | `#f1f5f9` | `#1e293b` |
| `--text-secondary` | `#94a3b8` | `#64748b` |
| `--border-color` | `#334155` | `#e2e8f0` |
| `--assistant-message` | `#374151` | `#f1f5f9` |

### Theme Persistence
- Theme preference is saved to `localStorage`
- Preference persists across page reloads and browser sessions
- Defaults to dark theme if no preference is saved

### Smooth Transitions
- 0.3s ease transitions on background, border, color, and box-shadow
- Applied to all major UI elements for seamless theme switching

## Accessibility
- Button has `aria-label="Toggle theme"` for screen readers
- Button has `title` attribute for tooltip on hover
- Supports keyboard navigation (Tab to focus, Enter/Space to activate)
- Color contrast maintained in both themes for readability
