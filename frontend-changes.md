# Frontend Code Quality Changes

## Summary

Added code quality tooling for the frontend (vanilla JS/CSS/HTML) and applied formatting consistency fixes to the existing source files.

---

## New Files

### `package.json`
Defines the project's frontend dev dependencies and npm scripts:
- `npm run format` — formats all frontend files with Prettier (modifies in place)
- `npm run format:check` — checks formatting without modifying files
- `npm run lint` — lints `frontend/script.js` with ESLint
- `npm run lint:fix` — auto-fixes ESLint issues in `frontend/script.js`

**Dev dependencies added:** `prettier@^3.3.0`, `eslint@^8.57.0`

---

### `.prettierrc`
Prettier configuration matching the existing code style:
- `tabWidth: 4` — 4-space indentation (consistent with current files)
- `singleQuote: true` — single quotes for JS strings
- `trailingComma: "es5"` — trailing commas in arrays/objects
- `printWidth: 88` — max line length
- `endOfLine: "lf"` — Unix line endings

---

### `.eslintrc.js`
ESLint configuration for browser-side JavaScript:
- Extends `eslint:recommended` ruleset
- Declares `marked` as a known global (loaded via CDN)
- `no-unused-vars`: warn
- `no-console`: warn (flags debug `console.log` calls left in production code)

---

### `scripts/frontend-format.sh`
Shell script to format all frontend files in one command:
```bash
./scripts/frontend-format.sh
```
Runs `prettier --write` over `frontend/**/*.{js,css,html}`.

---

### `scripts/frontend-lint.sh`
Shell script to check frontend quality without modifying files (suitable for CI):
```bash
./scripts/frontend-lint.sh
```
Runs `prettier --check` then `eslint` and exits non-zero if any check fails.

---

## Modified Files

### `frontend/script.js`
- Removed two double blank lines (between event listeners and between top-level functions) to match Prettier's single-blank-line-between-blocks style.

### `frontend/index.html`
- Removed an extra blank line between the closing `</div>` and the `<script>` tags at the bottom of `<body>`.

---

## Usage

Install dependencies once:
```bash
npm install
```

Then use the scripts directly:
```bash
# Format (modifies files)
./scripts/frontend-format.sh

# Lint only (no modifications — good for CI)
./scripts/frontend-lint.sh
```

Or use npm scripts:
```bash
npm run format        # format and save
npm run format:check  # check formatting only
npm run lint          # ESLint check
npm run lint:fix      # ESLint auto-fix
```

---

# Frontend Changes: Dark/Light Theme Toggle

## Feature
Added a toggle button that switches between dark (default) and light themes.

## Files Modified

### `frontend/index.html`
- Added a `<button id="themeToggle">` element with fixed positioning, placed directly inside `<body>` before `.container`
- Button contains two SVG icons: a **sun** (shown in dark mode) and a **moon** (shown in light mode)
- Includes `aria-label` and `title` attributes for accessibility

### `frontend/style.css`
- Added `[data-theme="light"]` CSS variable overrides:
  - `--background: #f8fafc`
  - `--surface: #ffffff`
  - `--surface-hover: #f1f5f9`
  - `--text-primary: #0f172a`
  - `--text-secondary: #64748b`
  - `--border-color: #e2e8f0`
  - `--assistant-message: #f1f5f9`
  - `--shadow` reduced opacity for light context
  - `--welcome-bg: #dbeafe`
- Added `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease` to all major UI elements for smooth switching
- Added `.theme-toggle` button styles:
  - `position: fixed; top: 1rem; right: 1rem; z-index: 1000`
  - 40×40px circular button matching the design aesthetic
  - Hover: scales up, highlights in primary blue, shows focus ring
  - Focus outline replaced with `box-shadow` focus ring for consistency
- Icon visibility rules: sun visible in dark mode, moon visible in light mode (via `[data-theme="light"]` selector)

### `frontend/script.js`
- Added an IIFE at the top of the file that reads `localStorage` and applies the saved theme to `<html>` immediately, preventing a flash of wrong theme on page load
- Added `initTheme()` function (sets `data-theme` from `localStorage` on DOMContentLoaded)
- Added `toggleTheme()` function:
  - Reads current `data-theme` attribute on `<html>`
  - Toggles the attribute between `"light"` and absent (dark)
  - Persists choice to `localStorage` under key `"theme"`
- Registered click listener for `#themeToggle` in `setupEventListeners()`

## Design Decisions
- Theme attribute is set on `document.documentElement` (`<html>`) so CSS selectors like `[data-theme="light"] .theme-toggle` work globally
- Dark mode is the default (no attribute needed); light mode uses `data-theme="light"`
- Theme preference persists across page reloads via `localStorage`
- All color changes rely on the existing CSS variable system — no element-level style overrides needed
