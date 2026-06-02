# Toggle Button Design - Frontend Changes

## Overview
Implemented icon-based toggle buttons positioned in the top right of the header:
1. **Theme Toggle** - Switch between dark and light modes with sun/moon icon
2. **Sidebar Toggle** - Show/hide sidebar with menu icon

Both toggles fit seamlessly with the existing design aesthetic and include persistent state via localStorage.

## Changes Made

### 1. HTML (`frontend/index.html`)

**Added:**
- Wrapped header title in a `header-top` container to create flex layout
- Added `header-controls` container to hold both toggle buttons
- Added theme toggle button with sun icon SVG
  ```html
  <button id="themeToggle" class="theme-toggle" title="Toggle dark/light theme">
    <svg><!-- Sun icon --></svg>
  </button>
  ```
- Added sidebar toggle button with menu icon SVG
  ```html
  <button id="sidebarToggle" class="sidebar-toggle" title="Toggle sidebar">
    <svg><!-- Menu icon --></svg>
  </button>
  ```
- Updated cache-busting version numbers (v9 → v11) for CSS and JS files

### 2. CSS (`frontend/style.css`)

**CSS Variables - Dark Mode (Default):**
- Original dark theme variables (--primary-color, --background, --surface, etc.)

**CSS Variables - Light Mode:**
```css
:root.light-mode {
    --primary-color: #1d4ed8;
    --background: #f8fafc;      /* Light gray background */
    --surface: #e2e8f0;         /* Light gray surface */
    --surface-hover: #cbd5e1;   /* Slightly darker gray */
    --text-primary: #0f172a;    /* Dark text */
    --text-secondary: #475569;  /* Muted text */
    --border-color: #cbd5e1;    /* Light border */
    /* ... other variables */
}
```

**Header Layout:**
- `.header-top` - Flex container for title and toggle button alignment
  - `display: flex`
  - `align-items: center`
  - `justify-content: space-between`

- `.header-controls` - Container for toggle buttons
  - `display: flex`
  - `align-items: center`
  - `gap: 0.75rem`

**Theme Toggle Button:**
- `.theme-toggle` - Button styling
  - Base: 40x40px, surface color background, border-radius: 8px
  - `display: none` by default (shown on smaller screens)
  - Smooth transitions on all state changes (0.2s ease)
  - SVG sun icon: 20x20px with currentColor stroke

- `.theme-toggle:hover` - Hover state
  - Background: surface-hover color
  - Border color: primary-color (blue)
  - Color text: primary-color
  - Transform: translateY(-1px)

- `.theme-toggle:focus` - Accessibility
  - Focus ring: 3px var(--focus-ring) with proper outline

**Sidebar Toggle Button:**
- `.sidebar-toggle` - Button styling
  - Same styling as theme toggle for consistency

**Responsive Visibility:**
- `@media (max-width: 1024px)` - Both toggles display
  - `.theme-toggle, .sidebar-toggle { display: flex; }`

**Light Mode Specific Styles:**
- `.message.assistant .message-content` - Added border for contrast
- `.sources-content` - Light blue tint background
- `.source-item` - Subtle gradient background
- `.stat-item` - Light gray background
- `.new-chat-btn`, `.suggested-item` - Light gray backgrounds
- `#chatInput` - Light gray input field with proper focus ring

**Sidebar States:**
- `.sidebar.hidden` - Sidebar hidden state (`display: none`)
- `.main-content.sidebar-hidden .chat-main` - Full-width chat when sidebar hidden

### 3. JavaScript (`frontend/script.js`)

**DOM Elements Added:**
- `themeToggle` - Reference to theme toggle button
- `sidebarToggle` - Reference to sidebar toggle button
- `sidebar` - Reference to sidebar element
- `mainContent` - Reference to main content container

**Initialization:**
- Added `restoreThemeState()` call in DOMContentLoaded to restore previous theme
- Added `restoreSidebarState()` call in DOMContentLoaded to restore previous sidebar state

**Event Listeners:**
- Added click handler for `themeToggle` → `toggleTheme()` function
- Added click handler for `sidebarToggle` → `toggleSidebar()` function

**Theme Toggle Functions:**

1. `toggleTheme()` - Handles theme toggle click
   - Toggles 'light-mode' class on document root
   - Saves state to localStorage (`lightMode`)
   - Updates button appearance via `updateThemeToggleState()`

2. `updateThemeToggleState(isLightMode)` - Updates theme button accessibility/state
   - Sets `aria-pressed` attribute
   - Updates button title text
   - Provides visual feedback

3. `restoreThemeState()` - Restores previous theme on page load
   - Reads from localStorage
   - Applies 'light-mode' class if light mode was previously enabled
   - Updates button appearance to match state

**Sidebar Toggle Functions:**

1. `toggleSidebar()` - Handles sidebar toggle click
   - Toggles 'hidden' class on sidebar
   - Toggles 'sidebar-hidden' class on main content
   - Saves state to localStorage
   - Updates button appearance via `updateToggleButtonState()`

2. `updateToggleButtonState(isHidden)` - Updates sidebar button accessibility/state
   - Sets `aria-pressed` attribute
   - Updates button title text
   - Provides visual feedback

3. `restoreSidebarState()` - Restores previous sidebar state on page load
   - Reads from localStorage
   - Applies 'hidden' class if sidebar was previously hidden
   - Updates button appearance to match state

## Design Aesthetic

The toggle buttons maintain consistency with the existing design:
- **Color Scheme**: Uses CSS variables (--primary-color, --surface, --border-color)
  - Dark mode: Dark blue/slate colors (existing theme)
  - Light mode: Light blue/gray colors (new theme)
- **Typography**: System fonts, consistent sizing
- **Interactions**: Smooth transitions (0.2s ease), hover effects, focus rings
- **Icons**: 
  - Theme toggle: Clean SVG sun icon (shown in dark mode to suggest light mode switch)
  - Sidebar toggle: Clean SVG menu icon (three horizontal lines)
- **Spacing**: Fits naturally in header with proper padding
- **Theme Variables**: Both themes use the same CSS variable names for easy switching

## Light Mode Features

**Color Palette:**
- Background: Light gray (#f8fafc)
- Surface: Light slate (#e2e8f0)
- Text: Dark navy (#0f172a) for contrast
- Primary: Dark blue (#1d4ed8)
- Messages: Light gray backgrounds with dark text

**Contrast & Readability:**
- All text maintains WCAG AA contrast ratios
- Messages and UI elements clearly distinguished
- Proper border styling for light backgrounds
- Subtle gradients for source items and stats

**User Experience:**
- Smooth transition between themes with CSS variables
- All interactive elements remain visible and functional
- Consistent spacing and layout across both modes

## Responsive Behavior

- **Desktop (>1024px)**: Toggle buttons hidden, sidebar always visible
- **Tablet/Mobile (≤1024px)**: Toggle buttons visible, users can:
  - Switch between dark and light modes for comfort
  - Hide sidebar for more chat space
- **State Persistence**: Both theme and sidebar states saved to localStorage and restored on page reload

## Accessibility Features

- Proper ARIA attributes (`aria-pressed`)
- Focus ring styling for keyboard navigation
- Title attributes for hover tooltips
- Semantic HTML button elements
- Sufficient color contrast in both themes (WCAG AA)
- Dynamic title updates to reflect current state

## Browser Compatibility

- Modern browsers with CSS Flexbox and CSS custom properties support
- localStorage API support for state persistence
- SVG inline icon support
- ES6 JavaScript features
- CSS `:root.light-mode` selector support

## Testing Notes

**Theme Toggle:**
1. ✅ Sun icon visible and clickable on screens ≤1024px
2. ✅ Clicking toggles between dark and light modes
3. ✅ Light mode applies correct colors and contrast
4. ✅ All UI elements readable in both modes
5. ✅ Theme preference persists across page reloads
6. ✅ Smooth transition between themes
7. ✅ Title updates correctly ("Switch to dark/light theme")

**Sidebar Toggle:**
1. ✅ Menu icon visible and clickable on screens ≤1024px
2. ✅ Clicking hides sidebar
3. ✅ Chat area expands to full width
4. ✅ Shows sidebar when clicked again
5. ✅ Sidebar visibility persists across page reloads
6. ✅ Maintains proper styling and transitions
7. ✅ Works correctly in both dark and light modes

**Combined Features:**
1. ✅ Both toggles work independently
2. ✅ Both buttons have proper spacing and alignment
3. ✅ Keyboard navigation works for both buttons
4. ✅ Hover and active states provide visual feedback
5. ✅ Focus rings visible for accessibility
