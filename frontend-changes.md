# Frontend Changes

## Code Quality Tooling

### What was added

| File | Purpose |
|---|---|
| `frontend/package.json` | npm project manifest with Prettier and ESLint as dev dependencies |
| `frontend/.prettierrc` | Prettier configuration |
| `frontend/.eslintrc.json` | ESLint configuration |
| `frontend/.prettierignore` | Excludes `node_modules/` from formatting |
| `scripts/check-frontend.sh` | Shell script that runs both Prettier and ESLint |

### Prettier (`frontend/.prettierrc`)

Prettier is the JavaScript/CSS/HTML equivalent of Black — it enforces a single, consistent code style with no configuration debates.

Settings chosen to match the existing code style:
- `singleQuote: true` — use single quotes (already used throughout)
- `semi: true` — require semicolons
- `tabWidth: 2` — 2-space indentation
- `trailingComma: "es5"` — trailing commas in objects/arrays (ES5-safe)
- `printWidth: 100` — line length limit
- `arrowParens: "always"` — always parenthesise arrow function params: `(x) => x`

### ESLint (`frontend/.eslintrc.json`)

Catches real bugs and enforces best practices in `script.js`:
- `eqeqeq` — require `===` instead of `==`
- `no-var` — disallow `var`, enforcing `const`/`let`
- `prefer-const` — warn when `let` could be `const`
- `no-unused-vars` — warn on unused variables
- `no-implicit-globals` — prevent accidental globals

`marked` (loaded from CDN) is declared as a global so ESLint does not flag it as undefined.

### `script.js` formatting changes applied

Prettier was applied to `script.js`. Key diffs from the original:

1. **Indentation normalised to 2 spaces** throughout (was 4 spaces).
2. **Trailing commas** added in multi-line objects:
   - `{ 'Content-Type': 'application/json' }` fetch header object
   - `{ query, session_id }` request body object
3. **Arrow function parentheses** made consistent: `s =>` → `(s) =>`, `.forEach(button =>` → `.forEach((button) =>`
4. **Double blank lines** collapsed to single blank lines (e.g. in `setupEventListeners`).
5. **Method chains** reformatted: `sources.map(...).join('')` broken across lines for readability.
6. **`addMessage` long string call** broken into multi-line form with trailing argument style.

### Running quality checks

**Install dependencies (once):**
```bash
cd frontend && npm install
```

**Check formatting and linting:**
```bash
# From repo root:
./scripts/check-frontend.sh

# Or from frontend/:
npm run quality
```

**Auto-fix all issues:**
```bash
# From repo root:
./scripts/check-frontend.sh --fix

# Or from frontend/ (format then lint-fix):
npm run format
npm run lint:fix
```

**Individual commands:**
```bash
cd frontend

npm run format        # apply Prettier formatting
npm run format:check  # check formatting without writing
npm run lint          # run ESLint
npm run lint:fix      # run ESLint with auto-fix
npm run quality       # format:check + lint (CI-safe, no writes)
```

---

## Dark/Light Theme Toggle

### Summary

Added a dark/light theme toggle button to the frontend. Users can switch between the existing dark theme and a new light theme. The preference is persisted in `localStorage` and applied immediately on page load (no flash of wrong theme).

---

### Files Modified

#### `frontend/index.html`

- Added a `<button class="theme-toggle" id="themeToggle">` element directly after `<body>`, positioned fixed in the top-right corner.
- The button contains two SVG icons: a **moon** (visible in dark mode) and a **sun** (visible in light mode). Icon visibility is controlled purely via CSS.
- Includes `aria-label` and `title` attributes for accessibility.
- Bumped stylesheet cache-buster version from `v=11` to `v=12`.

#### `frontend/style.css`

- **Light theme variables** — Added a `[data-theme="light"]` block defining a full set of CSS custom properties:
  - `--background`: `#f8fafc` (near-white page background)
  - `--surface`: `#ffffff` (white cards/sidebar)
  - `--surface-hover`: `#e2e8f0`
  - `--text-primary`: `#0f172a` (near-black for high contrast)
  - `--text-secondary`: `#64748b`
  - `--border-color`: `#cbd5e1`
  - `--welcome-bg` / `--welcome-border`: light blue tints
  - Theme toggle button variables (`--theme-toggle-bg`, `--theme-toggle-border`, `--theme-toggle-color`, `--theme-toggle-hover-bg`)

- **Smooth transitions** — Added a universal `transition` rule (`background-color`, `border-color`, `color`, `box-shadow` — 0.25 s ease) on `*, *::before, *::after` so every themed element animates smoothly when toggling.

- **Theme toggle button styles** — Added `.theme-toggle` styles:
  - Fixed position, top-right (`top: 1rem; right: 1rem; z-index: 1000`)
  - 40×40 px circle with border and shadow matching the current theme
  - Hover: scales up slightly, highlights with `--primary-color`
  - Focus: visible focus ring using `--focus-ring` for keyboard navigation
  - Icon switching: `.icon-moon` shown by default; `.icon-sun` shown when `[data-theme="light"]` is set

- **Code block contrast fix** — Reduced hard-coded `rgba(0,0,0,0.2)` backgrounds for `code` and `pre` to `rgba(0,0,0,0.12)`, with a further light-mode override at `rgba(0,0,0,0.07)` / `rgba(0,0,0,0.05)` to keep inline code readable on white backgrounds.

- **Source pill colors for light mode** — Added `[data-theme="light"] .source-pill` overrides to replace the dark-optimised `#90cdf4` color with `#1d4ed8` (dark blue) on a light blue tint background, maintaining sufficient contrast.

#### `frontend/script.js`

- **`initTheme()`** — Reads `localStorage.getItem('theme')` and sets `data-theme="light"` on `<html>` if needed. Called immediately at module evaluation (before `DOMContentLoaded`) to prevent a flash of the wrong theme on reload.

- **`toggleTheme()`** — Reads the current `data-theme` attribute on `document.documentElement` and toggles between dark (no attribute) and light (`data-theme="light"`). Saves the result to `localStorage`.

- **Event listener** — Wired `themeToggle` button to `toggleTheme()` inside `setupEventListeners()`.

---

### Design Decisions

- `data-theme` is set on `<html>` (i.e. `document.documentElement`) so the attribute is available from the very first paint, minimising any flash.
- Dark mode remains the default (no `data-theme` attribute = dark). Only `data-theme="light"` needs to be explicitly set.
- No extra libraries or build steps — pure CSS variables + vanilla JS.
- The toggle button is `position: fixed` (not inside a hidden `<header>`) so it is always accessible regardless of layout or scroll state.
