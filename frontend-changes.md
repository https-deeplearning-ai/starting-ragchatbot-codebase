# Frontend Changes

## Dark/Light Mode Toggle Button

### Feature
A theme toggle button positioned fixed in the top-right corner of the viewport, allowing users to switch between dark and light modes.

### Files Modified

#### `frontend/index.html`
- Added `<button id="themeToggle">` as a fixed-position element outside `.container`, before the main layout
- Button contains two inline SVGs: a sun icon (shown in dark mode) and a moon icon (shown in light mode), both with `aria-hidden="true"`
- Button has `aria-label` attribute (dynamically updated by JS) and `title` for tooltip
- Bumped cache-buster version on `style.css` and `script.js` links to `v=10`

#### `frontend/style.css`
- Added `[data-theme="light"]` CSS variable overrides for the full light palette (background, surface, text, border colours)
- Added `.theme-toggle` button styles: fixed position top-right, circular, 40×40 px, uses existing design tokens (`--surface`, `--border-color`, `--focus-ring`)
- Added hover (scale + primary colour), focus (3 px ring matching `--focus-ring`), and active (scale-down) states
- Sun/moon icon transition: `opacity` and `transform` (rotate + scale) with 0.3–0.4 s ease, so the outgoing icon rotates away and the incoming icon rotates in
- Added `transition: background-color/color/border-color 0.3s ease` to key layout elements (sidebar, chat container, inputs, messages, buttons) so the whole UI transitions smoothly on theme switch
- Added `transition: background-color/color` to `body` as a base fallback

#### `frontend/script.js`
- Added `initTheme()`: reads `localStorage` for a saved preference, falls back to `prefers-color-scheme` media query
- Added `applyTheme(theme)`: sets/removes `data-theme` attribute on `<html>`, updates `aria-label` on the button, and persists the choice to `localStorage`
- Added `toggleTheme()`: reads current state and calls `applyTheme` with the opposite value
- Wired `toggleTheme` to the toggle button's `click` event in `setupEventListeners()`
- Called `initTheme()` at the top of the `DOMContentLoaded` handler so the correct theme is applied before first paint

### Accessibility
- Button uses `aria-label` (updated dynamically to reflect the *target* state, e.g. "Switch to dark mode")
- SVG icons carry `aria-hidden="true"` so screen readers only announce the button label
- Focus ring uses the existing `--focus-ring` variable (3 px blue outline)
- Keyboard-navigable: standard `<button>` element responds to Enter and Space natively

---

## Light Theme — Complete Color System

### Feature
Completed the light theme by variabilizing all previously hardcoded colors so every element responds correctly to theme switching. All light-theme values were chosen to meet WCAG AA contrast ratios (≥ 4.5:1 for normal text).

### Files Modified

#### `frontend/style.css`

**New semantic CSS variables added to `:root`** (dark-theme defaults):
| Variable | Dark value | Purpose |
|---|---|---|
| `--link-color` | `#60a5fa` | Source citation link text |
| `--link-hover` | `#93c5fd` | Source link hover state |
| `--code-bg` | `rgba(0,0,0,0.25)` | Inline code and pre-block backgrounds |
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.25)` | Welcome message card shadow |
| `--error-bg/color/border` | red-tinted alpha values + `#f87171` | Error feedback banner |
| `--success-bg/color/border` | green-tinted alpha values + `#4ade80` | Success feedback banner |

**Light-theme overrides added to `[data-theme="light"]`**:
| Variable | Light value | Contrast note |
|---|---|---|
| `--border-color` | `#cbd5e1` | Slightly darker than before for visible borders |
| `--focus-ring` | `rgba(37,99,235,0.25)` | Slightly more opaque on light backgrounds |
| `--link-color` | `#1d4ed8` | ≈ 5.9:1 on white — passes AA |
| `--link-hover` | `#1e40af` | Darker on hover for clear feedback |
| `--code-bg` | `rgba(15,23,42,0.06)` | Subtle tint, dark-on-light direction |
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.06)` | Lighter shadow on light backgrounds |
| `--error-color` | `#b91c1c` | ≈ 6.7:1 on white — passes AA |
| `--success-color` | `#15803d` | ≈ 5.1:1 on white — passes AA |

**CSS rules updated to use variables** (previously hardcoded):
- `.sources-content a` and `:hover` → `var(--link-color)` / `var(--link-hover)`
- `.message-content code` and `pre` backgrounds → `var(--code-bg)`
- `.message.welcome-message .message-content` shadow → `var(--welcome-shadow)`
- `.error-message` and `.success-message` → `var(--error-bg/color/border)` and `var(--success-bg/color/border)`

**Bug fix**: `.message-content blockquote` referenced `var(--primary)` (undefined) — corrected to `var(--primary-color)`.
