# Frontend Changes: Theme Toggle Button

## Summary
Added a light/dark theme toggle button fixed in the top-right corner of the app. It uses sun/moon icons, animates between states, remembers the user's choice, and is fully keyboard accessible.

## Files changed

### `frontend/index.html`
- Added `<button id="themeToggle" class="theme-toggle">` at the top of `<body>` with two inline SVG icons (sun and moon, `aria-hidden="true"`).
- Added a small inline script in `<head>` that sets `data-theme` on `<html>` before first paint (saved choice in `localStorage`, otherwise the OS `prefers-color-scheme`, otherwise dark). This prevents a flash of the wrong theme.
- Bumped cache-busting query strings to `?v=13` for `style.css` and `script.js`.

### `frontend/style.css`
- **Light theme:** added a `:root[data-theme="light"]` block that redefines the existing CSS variables (background, surface, text, border, link colors, etc.). The default dark palette is unchanged.
- **New variables** so hard-coded colors follow the theme: `--code-bg`, `--welcome-shadow`, `--error-text`, `--success-text`. Code blocks, the welcome message shadow, and error/success messages now use them. Added `color-scheme` so native controls and scrollbars match too.
- **Toggle button styles** (`.theme-toggle`): a 44×44 round button using the existing surface, border, shadow, and primary-color hover styles, like the other controls.
- **Icon animation:** both icons sit on top of each other. The inactive one rotates out (±90°), shrinks to 50%, and fades out, while the active one rotates and scales in (0.4s ease). Dark mode shows the sun (switch to light). Light mode shows the moon (switch to dark).
- **Smooth theme change:** an `html.theme-transition` class, added briefly while switching, fades background, text, border, and shadow colors over 0.3s. It is only active during a toggle, so page load and other animations are not affected.
- **Accessibility:** visible `:focus-visible` ring using the existing `--focus-ring`. Under `prefers-reduced-motion: reduce`, the icon and button animations are turned off.

### `frontend/script.js`
- Added `getCurrentTheme()`, `updateThemeToggle()`, and `toggleTheme()`.
- `toggleTheme()` flips `data-theme` on `<html>`, saves the choice to `localStorage` (wrapped in try/catch in case storage is unavailable), updates the button's `aria-label`/`title` ("Switch to light theme" / "Switch to dark theme"), and adds the color-transition class unless the user prefers reduced motion.
- The button is a native `<button type="button">`, so Tab focuses it and Enter/Space activate it with no extra key handling.

## Verification
Checked in a browser with a static server: Tab moves focus to the toggle, Enter and Space switch themes, the aria-label updates, the choice is saved in `localStorage`, and both themes render correctly with the icon in the top right.
