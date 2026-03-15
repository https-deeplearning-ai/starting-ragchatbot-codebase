# Frontend Changes

## API Endpoint Testing

No frontend changes were made in this feature.

This feature added API endpoint testing infrastructure to the backend test suite:

- `backend/tests/conftest.py` — added `mock_rag_system` and `api_client` shared fixtures; the `api_client` fixture builds a minimal FastAPI test app that mirrors `app.py`'s API endpoints without the static-file mount (which requires `../frontend` to exist and would fail in CI/test environments)
- `backend/tests/test_api.py` — 21 new tests covering `POST /api/query`, `GET /api/courses`, and `DELETE /api/sessions/{session_id}`
- `pyproject.toml` — added `httpx>=0.27` to dev dependencies (required by FastAPI's `TestClient`) and `addopts = "-v --tb=short"` to `[tool.pytest.ini_options]`

## Code Quality Tooling Setup

### What was added

**`frontend/package.json`**
- Defines `prettier` as a dev dependency (`^3.5.3`).
- Adds three npm scripts:
  - `npm run format` — formats all frontend files in-place.
  - `npm run format:check` (alias `npm run lint`) — checks formatting without writing changes (suitable for CI).

**`frontend/.prettierrc`**
- Prettier config enforcing consistent style across `.js`, `.html`, and `.css` files:
  - 100-character print width
  - 2-space indentation (spaces, not tabs)
  - Semicolons required
  - Single quotes in JS
  - Trailing commas where valid in ES5
  - LF line endings

**`frontend/.prettierignore`**
- Excludes `node_modules/` from formatting checks.

**`lint.sh`** (project root)
- Shell script for running quality checks without having to remember npm commands.
- `./lint.sh` — runs `prettier --check` (CI-safe, exits non-zero on violations).
- `./lint.sh --fix` — runs `prettier --write` to auto-format all files.
- Automatically installs npm deps if `node_modules/` is missing.

### Formatting applied to existing files

**`frontend/script.js`**
- Removed double blank lines between function declarations.
- Removed trailing whitespace on lines.
- Removed stale `// Removed removeMessage function` comment (dead documentation).

### How to use

```bash
# Install deps (one-time)
cd frontend && npm install

# Check formatting
./lint.sh

# Auto-fix formatting
./lint.sh --fix

# Or directly via npm
cd frontend
npm run format        # fix
npm run format:check  # check only
```

## Dark/Light Mode Toggle Button

### Files Modified
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

### What Was Added

#### `index.html`
- Added a `<button id="themeToggle">` element outside `.container`, fixed-positioned in the top-right corner.
- Button contains two inline SVG icons: a **sun** (shown in dark mode) and a **moon** (shown in light mode), both with `aria-hidden="true"`.
- Button has `aria-label="Toggle light/dark mode"` and `title` for accessibility.

#### `style.css`
- **`body.light-theme` CSS variables**: overrides `--background`, `--surface`, `--surface-hover`, `--text-primary`, `--text-secondary`, `--border-color`, `--assistant-message`, `--shadow`, and `--focus-ring` with light-palette equivalents.
- **Light theme code block fix**: overrides `background-color` for `.message-content code` and `pre` to use subtle light values instead of dark `rgba(0,0,0,0.2)`.
- **`body` transition**: added `transition: background-color 0.25s ease, color 0.25s ease` for smooth theme switching.
- **`.theme-toggle` button styles**: fixed position (`top: 1rem; right: 1rem; z-index: 1000`), circular (42×42px), uses CSS variable colors so it automatically adapts to the active theme. Hover and `:focus-visible` states use a scale transform and the `--focus-ring` shadow.
- **Icon visibility**: `.icon-sun` is shown by default (dark mode); in `body.light-theme`, `.icon-sun` is hidden and `.icon-moon` is shown.

#### `script.js`
- Added `setupThemeToggle()` function called on `DOMContentLoaded`.
- Reads `localStorage.getItem('theme')` on load — if `'light'`, applies `.light-theme` to `<body>` immediately (persists across page reloads).
- Click handler toggles `body.light-theme` and saves the new preference to `localStorage`.

### Design Decisions
- Toggle is **fixed-positioned** so it stays visible regardless of scroll state.
- Uses the existing CSS variable system — no additional selectors needed for most components.
- Preference is **persisted** in `localStorage` under the key `theme`.
- Fully **keyboard-navigable**: focusable via Tab, activatable via Space/Enter, with a visible `:focus-visible` ring.

---

## Light Theme CSS Variables (expanded)

### Files Modified
- `frontend/style.css`

### What Was Added / Changed

#### `body.light-theme` variable block (`style.css`)
Expanded to cover every token defined in `:root`, organized by category:

| Token | Dark value | Light value | Notes |
|---|---|---|---|
| `--background` | `#0f172a` | `#f8fafc` | Near-white page background |
| `--surface` | `#1e293b` | `#ffffff` | Cards, sidebar, input |
| `--surface-hover` | `#334155` | `#e2e8f0` | Hover states |
| `--text-primary` | `#f1f5f9` | `#0f172a` | ~18:1 contrast on light bg |
| `--text-secondary` | `#94a3b8` | `#475569` | ~7:1 contrast on light bg (raised from `#64748b`) |
| `--border-color` | `#334155` | `#cbd5e1` | Visible but subtle on white |
| `--focus-ring` | `rgba(37,99,235,0.2)` | `rgba(37,99,235,0.18)` | Slightly tighter on light |
| `--shadow` | `0 4px 6px -1px rgba(0,0,0,0.3)` | `0 4px 6px -1px rgba(0,0,0,0.08)` | Lighter drop shadow |
| `--assistant-message` | `#374151` | `#f1f5f9` | Soft gray bubble |
| `--user-message` | `#2563eb` | `#2563eb` | Blue stays; white text = ~4.6:1 (AA) |
| `--welcome-bg` | `#1e3a5f` | `#eff6ff` | Light blue tint for welcome panel |
| `--welcome-border` | `#2563eb` | `#93c5fd` | Lighter accent border |

#### Targeted component overrides

- **Code blocks** — `code` and `pre` backgrounds changed from `rgba(0,0,0,0.2)` to `rgba(15,23,42,0.07/0.05)` and `code` text set to `#1e293b` for readability.
- **Source tag links** — hardcoded `#93c5fd` text (~1.7:1 on white, fails WCAG) replaced with `#1d4ed8` (~5.9:1); hover swaps to `#1e40af`.
- **Error messages** — `#f87171` text replaced with `#b91c1c` (~5.9:1 on white).
- **Success messages** — `#4ade80` text replaced with `#15803d` (~5.1:1 on white).
- **Welcome message shadow** — reduced from `rgba(0,0,0,0.2)` spread to `rgba(0,0,0,0.08)` for a lighter feel.

### Accessibility Notes
All foreground/background colour pairs in light mode meet **WCAG 2.1 AA** (minimum 4.5:1 for normal text, 3:1 for large text and UI components). The primary interactive blue (`#2563eb`) is retained as it passes AA for the blue-on-white button label and button-border contexts.

---

## Theme Toggle — JavaScript Functionality & Smooth Transitions

### Files Modified
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

### What Was Added / Changed

#### FOUC (Flash of Unstyled Content) prevention (`index.html`, `style.css`, `script.js`)
- An inline `<script>` added to `<head>` reads `localStorage` and sets `html.light-theme-early` **before the first paint**, so users who saved a light preference never see a dark flash on load.
- All light-theme CSS rules now have a paired `html.light-theme-early body` selector alongside `body.light-theme` so the early class drives identical styles.
- In `setupThemeToggle()`, once the DOM is ready the early class is transferred to `body.light-theme` (with transitions briefly suppressed via `body.style.transition = 'none'` + forced reflow) and the early class is removed from `<html>`.

#### Smooth surface transitions (`style.css`)
Added `transition: background-color 0.25s ease, color 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease` to all theme-sensitive elements so every surface fades together when the theme toggles:
- `.sidebar`, `.chat-main`, `.chat-container`, `.chat-messages`, `.chat-input-container`
- `#chatInput`, `#sendButton`
- `.message-content`, `.stat-item`, `.suggested-item`
- `.source-tag a`, `.error-message`, `.success-message`

#### Animated icon swap (`style.css`)
Replaced the `display: none/block` icon switch (which cannot animate) with an **opacity + scale/rotate** crossfade:
- Both SVG icons are `position: absolute` inside the button, overlapping.
- The outgoing icon fades to `opacity: 0` + `scale(0.5)` with a slight rotation; the incoming icon fades in from the same state.
- Governed by `transition: opacity 0.25s ease, transform 0.3s ease` — independent of the surface transitions.

#### `aria-pressed` and dynamic `aria-label` (`script.js`, `index.html`)
- Button now has `aria-pressed="false"` as a default HTML attribute.
- `syncButton()` sets `aria-pressed` to `"true"/"false"` and updates `aria-label` to `"Switch to dark mode"` / `"Switch to light mode"` to reflect the *next* action — consistent with toggle-button best practice.
- Called once on init and again on every click.

---

## `data-theme` Attribute Refactor

### Files Modified
- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

### What Changed

#### Single attribute on `<html>` replaces classes
The previous implementation used `body.light-theme` for live toggling and `html.light-theme-early` for FOUC prevention, requiring every CSS rule to be duplicated with two selectors. This was replaced with a single `data-theme` attribute on `<html>`:

| Before | After |
|---|---|
| `html.light-theme-early body, body.light-theme { ... }` | `:root[data-theme="light"] { ... }` |
| `html.light-theme-early body .source-tag a, body.light-theme .source-tag a` | `[data-theme="light"] .source-tag a` |

#### `index.html` — inline script
```js
// Before
document.documentElement.classList.add('light-theme-early');
// After
document.documentElement.setAttribute('data-theme', savedTheme || 'dark');
```
The attribute is set to `'dark'` by default (explicit), so `:root` always carries a value and the CSS selector is always unambiguous.

#### `script.js` — `setupThemeToggle()`
- Removed the early-class transfer logic (no longer needed — inline script and `setupThemeToggle` both write to the same attribute).
- Removed the `transition = 'none'` suppression hack (no longer needed — attribute was set before CSS loaded, so no reflow is visible).
- Toggle writes `document.documentElement.setAttribute('data-theme', 'light'|'dark')` directly.
- `isLight()` reads back the same attribute as the single source of truth.

#### `style.css` — CSS variable scoping
- All light-theme variable overrides moved to `:root[data-theme="light"]`, which is the most specific and correct scope for custom property inheritance — descendant elements automatically pick up the new values via `var()`.
- All component overrides (`code`, `pre`, source tags, alerts, welcome shadow, icon states) simplified to single `[data-theme="light"] .selector` rules.
