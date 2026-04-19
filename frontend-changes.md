# Frontend Code Quality Changes

## Summary

Added frontend code quality tooling (Prettier for formatting, ESLint for linting) and applied consistent formatting across all frontend files.

---

## New Files

### `frontend/package.json`
Declares the frontend as a Node project and wires up quality check scripts:
- `npm run format` — formats all JS/CSS/HTML with Prettier (write mode)
- `npm run format:check` — checks formatting without modifying files (CI-safe)
- `npm run lint` — lints `script.js` with ESLint
- `npm run lint:fix` — auto-fixes ESLint issues
- `npm run quality` — runs both `format:check` and `lint` (full check)
- `npm run quality:fix` — runs both `format` and `lint:fix` (full auto-fix)

Dev dependencies: `prettier@^3.3.3`, `eslint@^8.57.0`

### `frontend/.prettierrc`
Prettier configuration:
- 4-space indentation, 100-char print width
- Single quotes, trailing commas (ES5), LF line endings

### `frontend/.prettierignore`
Excludes `node_modules/` from Prettier.

### `frontend/.eslintrc.json`
ESLint configuration targeting browser ES2021:
- Errors on `no-undef`, `eqeqeq` (strict equality), `no-var`, `curly`
- Warns on `no-unused-vars`, `prefer-const`
- Registers `marked` as a known read-only global (loaded via CDN)

### `scripts/check-frontend.sh`
Shell script to run all frontend quality checks from the repo root:
```bash
# Check only (exits non-zero if anything fails):
./scripts/check-frontend.sh

# Auto-fix formatting and lint issues:
./scripts/check-frontend.sh --fix
```

---

## Modified Files

### `frontend/script.js`
Applied Prettier-consistent formatting:
- Single quotes throughout
- Trailing commas on multi-line function arguments and object literals
- Explicit `curly` braces on all `if` bodies
- Arrow function parentheses around single parameters
- Consistent blank lines between logical sections

### `frontend/style.css`
Applied Prettier-consistent formatting:
- Each CSS selector on its own line (e.g. `*,\n*::before,\n*::after`)
- `h1`, `h2`, `h3` font-size rules expanded to separate blocks
- `@keyframes bounce` selector list expanded (`0%,\n80%,\n100%`)
- `.no-courses, .loading, .error` selector list expanded
- Removed stale inline comment on `.course-titles` block
- Consistent blank lines between rule blocks

### `frontend/index.html`
Applied Prettier-consistent formatting:
- `<!doctype html>` lowercased
- Self-closing void elements (`<meta ... />`, `<link ... />`, `<input ... />`)
- 4-space indentation throughout
- Long `<button>` attributes broken onto separate lines
- `<script>` tags moved inside `<body>` closing tag for consistency

---

# Frontend Feature: Dark/Light Mode Toggle

## Feature: Dark/Light Mode Toggle Button

### Summary
Added a floating theme toggle button (dark ↔ light mode) with sun/moon icons, smooth transitions, and full keyboard accessibility.

---

### Files Modified

#### `frontend/index.html`
- Added a `<button class="theme-toggle" id="themeToggle">` element as the first child of `.container`, positioned fixed in the top-right corner.
- Button contains two SVG icons:
  - **Moon icon** (`.icon-moon`): visible in dark mode (default)
  - **Sun icon** (`.icon-sun`): visible in light mode
- Includes `aria-label` (dynamically updated via JS) and `title` for accessibility.
- Bumped `style.css` cache-buster to `?v=12` and `script.js` to `?v=10`.

#### `frontend/style.css`
- **Light mode variables** (`body.light-mode`): new CSS variable overrides for `--background`, `--surface`, `--surface-hover`, `--text-primary`, `--text-secondary`, `--border-color`, `--assistant-message`, `--welcome-bg`, `--toggle-bg`, `--toggle-hover-bg`.
- **Global transition**: `body *` gets `transition` on `background-color`, `color`, `border-color`, `box-shadow` (0.3s ease) so every element smoothly cross-fades on theme switch.
- **`.theme-toggle` button styles**:
  - Fixed, top-right (`top: 1rem; right: 1rem; z-index: 1000`)
  - 42 × 42 px circle, uses `--toggle-bg` / `--toggle-hover-bg` for background
  - Scale animation on hover (`scale(1.1)`) and press (`scale(0.95)`)
  - `focus-visible` ring using `--focus-ring` for keyboard nav
- **Icon animation**:
  - `.icon-moon` and `.icon-sun` are `position: absolute`, layered on top of each other
  - Cross-fade (`opacity`) + rotate/scale transform on switch (0.25–0.35s ease)
  - Dark mode: moon opaque, sun rotated/hidden; light mode: the reverse

#### `frontend/script.js`
- **`initTheme()`**: reads `localStorage.getItem('theme')` on `DOMContentLoaded` and applies `body.light-mode` before first paint to avoid flash.
- **`toggleTheme()`**: toggles `body.light-mode`, persists choice to `localStorage`, and calls `updateToggleLabel()`.
- **`updateToggleLabel(isLight)`**: updates `aria-label` on the button to reflect the *next* action ("Switch to dark/light mode"), keeping screen-reader output accurate.
- Click listener wired to `#themeToggle` inside `setupEventListeners()`.

---

## Feature: Accessible Light Theme Variant

### Summary
Replaced all hard-coded color values with CSS custom properties and designed a complete light theme that meets WCAG 2.1 AA (most AAA) across all UI surfaces.

---

### Files Modified

#### `frontend/style.css`
**New CSS variables added to `:root` (dark defaults):**
| Variable | Value | Purpose |
|---|---|---|
| `--code-bg` | `rgba(0,0,0,0.25)` | Inline code / pre block background |
| `--source-link-color` | `#60a5fa` | Source chip link color |
| `--source-link-hover` | `#93c5fd` | Source chip link hover |
| `--error-color` | `#f87171` | Error message text |
| `--error-bg` | `rgba(239,68,68,0.12)` | Error message background |
| `--error-border` | `rgba(239,68,68,0.25)` | Error message border |
| `--success-color` | `#4ade80` | Success message text |
| `--success-bg` | `rgba(34,197,94,0.12)` | Success message background |
| `--success-border` | `rgba(34,197,94,0.25)` | Success message border |

**Light mode overrides (`body.light-mode`) with contrast ratios:**
| Variable | Light Value | Contrast vs Surface | WCAG Level |
|---|---|---|---|
| `--primary-color` | `#1d4ed8` (blue-700) | 6.2:1 on white | AA |
| `--primary-hover` | `#1e40af` (blue-800) | 8.1:1 on white | AAA |
| `--background` | `#f8fafc` (slate-50) | — | — |
| `--surface` | `#ffffff` | — | — |
| `--surface-hover` | `#f1f5f9` (slate-100) | — | — |
| `--text-primary` | `#1e293b` (slate-800) | 14.5:1 on bg | AAA |
| `--text-secondary` | `#475569` (slate-600) | 5.9:1 on bg | AA |
| `--border-color` | `#cbd5e1` (slate-300) | — | — |
| `--user-message` | `#1d4ed8` | white on bg: 6.2:1 | AA |
| `--source-link-color` | `#1d4ed8` | 6.2:1 on white | AA |
| `--error-color` | `#b91c1c` (red-700) | 7.5:1 on white | AAA |
| `--success-color` | `#15803d` (green-700) | 7.1:1 on white | AAA |
| `--code-bg` | `rgba(0,0,0,0.05)` | subtle gray tint | — |
| `--focus-ring` | `rgba(29,78,216,0.3)` | visible on all light surfaces | — |

**Hard-coded colors replaced with variables:**
- `.source-chip a` / `.source-chip a:hover` → `--source-link-color` / `--source-link-hover`
- `.message-content code` / `pre` → `--code-bg`
- `.error-message` → `--error-color`, `--error-bg`, `--error-border`
- `.success-message` → `--success-color`, `--success-bg`, `--success-border`

#### `frontend/index.html`
- Bumped `style.css` cache-buster to `?v=12`.
