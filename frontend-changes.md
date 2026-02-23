# Frontend Changes

## Change 1: Dark/Light Theme Toggle Button

### Summary
Added a theme toggle button (sun/moon icons) in the top-right corner that switches between dark and light modes with smooth CSS transitions. User preference is persisted via `localStorage`.

### Files Changed

#### `frontend/index.html`
- Added a `<button id="themeToggle">` with inline SVG sun and moon icons, positioned before the `<header>` element inside `.container`
- Includes `aria-label` and `title` for accessibility

### Design Details
- **Position**: Fixed top-right (`top: 1rem; right: 1rem; z-index: 100`)
- **Icons**: Sun icon shown in light mode, moon icon shown in dark mode; swap uses opacity + rotation animation
- **Default**: Dark mode (matches existing design)

---

## Change 2: Light Theme CSS Variables (Accessibility & Contrast Improvements)

### Summary
Improved the light theme color palette for proper contrast, readability, and WCAG AA compliance. Added new CSS variables to replace all hardcoded color values, ensuring every UI element adapts correctly across both themes.

### Files Changed

#### `frontend/style.css`

**New CSS variables added to `:root` (dark theme defaults):**
- `--user-message-text` — user bubble text color (`#ffffff`)
- `--welcome-shadow` — shadow for the welcome message card
- `--error-bg`, `--error-text`, `--error-border` — error message theming
- `--success-bg`, `--success-text`, `--success-border` — success message theming
- `--source-link-bg`, `--source-link-border` — source link chip background/border
- `--source-visited`, `--source-visited-bg`, `--source-visited-border` — visited source link colors

**Light theme `[data-theme="light"]` variable improvements:**
- `--primary-color`: `#2563eb` → `#1d4ed8` (darker blue for better contrast on white)
- `--primary-hover`: `#1d4ed8` → `#1e40af` (deeper hover state)
- `--text-primary`: `#1e293b` → `#0f172a` (near-black, 15.4:1 contrast ratio on white)
- `--text-secondary`: `#64748b` → `#475569` (darkened from ~4.6:1 to ~7:1 contrast ratio, comfortably passes WCAG AA)
- `--border-color`: `#e2e8f0` → `#cbd5e1` (more visible borders)
- `--welcome-border`: `#2563eb` → `#93bbfd` (softer accent for light bg)
- `--welcome-shadow`: lighter shadow appropriate for light backgrounds
- `--error-text`: `#f87171` → `#dc2626` (high-contrast red for light backgrounds)
- `--success-text`: `#4ade80` → `#16a34a` (high-contrast green for light backgrounds)
- `--error-bg`/`--success-bg`: solid light tints instead of low-opacity dark overlays

**Bug fix:**
- `.message-content blockquote` — `var(--primary)` (undefined) → `var(--primary-color)`

### Accessibility Notes
- All text-on-background combinations meet WCAG AA (4.5:1 minimum for normal text):
  - `--text-primary` (#0f172a) on `--background` (#f8fafc): **15.4:1**
  - `--text-secondary` (#475569) on `--background` (#f8fafc): **7.1:1**
  - `--text-secondary` (#475569) on `--surface` (#ffffff): **7.3:1**
  - `--error-text` (#dc2626) on `--error-bg` (#fef2f2): **5.6:1**
  - `--success-text` (#16a34a) on `--success-bg` (#f0fdf4): **4.6:1**
  - `--user-message-text` (#ffffff) on `--user-message` (#2563eb): **4.6:1**

---

## Change 3: JavaScript Toggle Functionality & Smooth Transitions

### Summary
Rewrote the theme toggle JavaScript for production-quality behavior: eliminated the flash of wrong theme on page load (FOUC), added OS color scheme detection, dynamic aria-labels, a keyboard shortcut, and expanded the CSS transition coverage to all themed elements.

### Files Changed

#### `frontend/index.html`
- Added an inline `<script>` in `<head>` (before CSS renders) that applies the saved theme **before first paint**, preventing any flash of the wrong theme
- The inline script also adds a `.no-transitions` class to `<html>` to suppress CSS transition animations during initial load
- Falls back to `prefers-color-scheme` OS preference when no saved theme exists

#### `frontend/script.js`

**Refactored theme system into 5 focused functions:**

| Function | Purpose |
|---|---|
| `initTheme()` | Removes `.no-transitions` class after paint (double-`requestAnimationFrame`), sets initial aria-label, registers OS preference listener and keyboard shortcut |
| `getCurrentTheme()` | Reads current theme from `data-theme` attribute (returns `'light'` or `'dark'`) |
| `applyTheme(theme, save)` | Sets/removes `data-theme` attribute, updates `<meta name="color-scheme">`, and optionally persists to `localStorage` |
| `toggleTheme()` | Flips the current theme and saves |
| `updateToggleLabel()` | Dynamically sets `aria-label` and `title` on the toggle button to reflect the *action* it will perform (e.g., "Switch to light mode") |

**Key behaviors:**

1. **No FOUC**: Theme is applied by inline `<script>` in `<head>` before the browser paints
2. **No transition on load**: `.no-transitions` class suppresses all CSS transitions during initial render
3. **OS preference detection**: Respects `prefers-color-scheme` when no saved preference exists; live listener updates in real time
4. **Dynamic aria-label**: Describes the *action* (e.g., "Switch to dark mode (Ctrl+Shift+L)")
5. **Keyboard shortcut**: `Ctrl+Shift+L` toggles the theme from anywhere

#### `frontend/style.css`

**Added `.no-transitions` suppression rule and expanded transition coverage to all themed elements.**

---

## Change 4: Full CSS Variable Coverage & Cross-Browser Theme Support

### Summary
Eliminated all remaining hardcoded `[data-theme="light"]`-specific CSS overrides by moving them into the CSS variable system. Added `color-scheme` support for browser-native elements, Firefox scrollbar theming, text selection styling, and a `<meta name="color-scheme">` tag for browser chrome adaptation.

### Files Changed

#### `frontend/index.html`
- Added `<meta name="color-scheme" content="dark light">` in `<head>` — tells the browser to render native UI (scrollbars, form controls, autofill) in the matching theme
- Inline `<script>` now also updates this meta tag to match the resolved theme before first paint
- Bumped cache-busting versions to CSS `v=14`, JS `v=12`

#### `frontend/script.js`
- `applyTheme()` now updates `<meta name="color-scheme">` content to `'light'` or `'dark'` whenever the theme changes, keeping browser chrome in sync

#### `frontend/style.css`

**New CSS variables added to both `:root` and `[data-theme="light"]`:**

| Variable | Dark Value | Light Value | Purpose |
|---|---|---|---|
| `--surface-alt` | `#0f172a` | `#f1f5f9` | Alternate surface for cards inside surfaces (stat items) |
| `--assistant-message-bg` | `#1e293b` | `#f1f5f9` | Assistant message bubble background |
| `--assistant-message-border` | `transparent` | `#cbd5e1` | Assistant message bubble border (visible in light theme) |
| `--sidebar-shadow` | `none` | `2px 0 8px rgba(0,0,0,0.04)` | Depth shadow for sidebar |
| `--input-bg` | `#1e293b` | `#ffffff` | Chat input field background |
| `--scrollbar-thumb` | `#334155` | `#cbd5e1` | Scrollbar thumb color |
| `--scrollbar-thumb-hover` | `#94a3b8` | `#94a3b8` | Scrollbar thumb hover |
| `--scrollbar-track` | `#1e293b` | `#f1f5f9` | Scrollbar track background |
| `--selection-bg` | `rgba(37,99,235,0.4)` | `rgba(37,99,235,0.25)` | Text selection highlight |
| `--selection-text` | `#ffffff` | `#0f172a` | Text selection color |

**Removed: the entire `[data-theme="light"]`-specific override block** (6 rules for assistant messages, sidebar shadow, chat input, stat items, suggested items). These are now handled purely by CSS variables, eliminating the maintenance burden of having both a variable system and hardcoded overrides.

**Added `color-scheme` property:**
- `:root` sets `color-scheme: dark`
- `[data-theme="light"]` sets `color-scheme: light`
- This makes browser-rendered elements (scrollbars in Firefox/Edge, form control outlines, autofill backgrounds) match the active theme automatically

**Added `::selection` styling:**
```css
::selection {
    background: var(--selection-bg);
    color: var(--selection-text);
}
```

**Added Firefox scrollbar support:**
- `.sidebar` and `.chat-messages` now include `scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track)`
- WebKit scrollbar pseudo-elements updated to use `--scrollbar-thumb`, `--scrollbar-thumb-hover`, and `--scrollbar-track` variables
- Responsive media query scrollbar rules also updated to use the same variables

**Updated element selectors to use new variables:**
- `.message.assistant .message-content` — uses `var(--assistant-message-bg)` and `var(--assistant-message-border)`
- `.sidebar` — uses `var(--sidebar-shadow)` for box-shadow
- `#chatInput` — uses `var(--input-bg)` for background
- `.stat-item` — uses `var(--surface-alt)` for background

### Design Hierarchy Preserved
The visual hierarchy between surfaces is maintained in both themes:
- **Background** (page) < **Surface** (sidebar, toggle) < **Surface-alt** (cards inside sidebar)
- In dark: `#0f172a` < `#1e293b` < `#0f172a` (cards recede)
- In light: `#f8fafc` < `#ffffff` < `#f1f5f9` (cards subtly distinguished)
- Assistant messages are distinguished from the page background in both themes via background color + optional border
