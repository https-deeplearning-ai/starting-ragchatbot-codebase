# Frontend Changes — Dark / Light Theme Toggle

## Summary

Added a theme toggle so users can switch between dark and light themes. Themes are driven by CSS custom properties and a `data-theme` attribute on the `<html>` element.

## Files Changed

### `frontend/index.html`
- Added a fixed, top-right theme toggle button with sun/moon SVG icons
- Inline script applies the saved theme before paint to avoid a flash of the wrong theme
- Bumped stylesheet/script cache-bust query versions

### `frontend/style.css`
- Split CSS variables into dark (`:root` / `[data-theme="dark"]`) and light (`[data-theme="light"]`) sets
- Light theme uses light backgrounds, dark text, and adjusted borders/surfaces for contrast
- Added `.theme-toggle` styles: circular button, focus-visible ring, hover/active scale, icon cross-fade/rotate animation
- Wired more UI colors (code blocks, errors, success, shadows) through theme variables
- Added smooth `transition` on background/color/border for body and key surfaces

### `frontend/script.js`
- Theme helpers: `getPreferredTheme`, `applyTheme`, `initTheme`, `toggleTheme`
- Click handler on `#themeToggle` flips `data-theme` between `dark` and `light`
- Persists preference in `localStorage` under key `theme`
- Updates `aria-label` / `title` so the control stays accessible and keyboard-friendly

## Behavior
- Default theme: dark (matches the original UI)
- Toggle shows sun in dark mode (switch to light) and moon in light mode (switch to dark)
- Preference survives page reloads
