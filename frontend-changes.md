# Frontend and Development Changes

## Code Quality Tools

### Overview
Added comprehensive code quality tools to the development workflow to ensure consistent code formatting and catch potential issues early.

### Changes Made

#### 1. Dependencies Added
Added the following development dependencies to `pyproject.toml`:
- **black** (v25.9.0+): Automatic Python code formatter
- **flake8** (v7.3.0+): Linting tool for style guide enforcement
- **isort** (v6.1.0+): Import statement organizer
- **mypy** (v1.18.2+): Static type checker

#### 2. Configuration Files

##### pyproject.toml
Added configuration sections for all tools:
- **[tool.black]**: Line length 88, Python 3.13 target, excludes build directories
- **[tool.isort]**: Black-compatible profile, integrates with black formatting
- **[tool.mypy]**: Python 3.13, relaxed settings for gradual adoption

##### .flake8
Created dedicated flake8 configuration file with:
- Max line length: 88 (matches black)
- Ignored rules: E203, W503 (black compatibility)
- Excluded directories: .venv, build, dist, chroma_db, etc.

#### 3. Development Scripts
Created three shell scripts in `scripts/` directory:

##### scripts/format.sh
- Runs black formatter on backend/ and main.py
- Runs isort for import organization
- Automatically fixes formatting issues

##### scripts/lint.sh
- Runs flake8 linter with configured rules
- Runs mypy type checker
- Reports issues without fixing them

##### scripts/quality.sh
- Comprehensive quality check script
- Runs format checks (without modifying files)
- Runs import sorting checks
- Runs flake8 linting
- Runs mypy type checking
- Exits with error code if any check fails
- Suitable for CI/CD integration

#### 4. Code Formatting Applied
- Formatted all Python files in backend/ and main.py with black
- Organized all imports with isort
- 15 files reformatted, maintaining functionality

### Usage

#### Format code automatically:
```bash
./scripts/format.sh
```

#### Run linting checks:
```bash
./scripts/lint.sh
```

#### Run all quality checks (CI-friendly):
```bash
./scripts/quality.sh
```

#### Individual tool usage:
```bash
# Format with black
uv run black backend/ main.py

# Check formatting without changes
uv run black --check backend/ main.py

# Sort imports
uv run isort backend/ main.py

# Lint code
uv run flake8 backend/ main.py

# Type check
uv run mypy backend/ main.py
```

### Benefits
- **Consistent code style**: All code formatted to same standards
- **Early bug detection**: Linting and type checking catch issues before runtime
- **Better collaboration**: Reduced style-related code review comments
- **Automated workflow**: Simple scripts for quality enforcement
- **CI/CD ready**: Quality script returns proper exit codes for automation

### Integration Recommendations
- Run `./scripts/format.sh` before committing code
- Add `./scripts/quality.sh` to pre-commit hooks
- Include quality checks in CI/CD pipeline
- Team members should run `uv sync` to install dev dependencies

---

## Theme Toggle Feature

### Overview
Implemented a complete dark/light theme toggle system for the Course Materials Assistant application.

### Changes Made

#### 1. HTML Structure (`frontend/index.html`)
- **Added theme toggle button** positioned at the top-right of the page
- Button includes both sun and moon SVG icons for visual feedback
- Placed outside the main container for fixed positioning
- Added `aria-label="Toggle theme"` for accessibility

**Location**: Lines 13-28

#### 2. CSS Styling (`frontend/style.css`)

##### Light Theme Variables
- **Added light theme color palette** using `[data-theme="light"]` selector
- Light theme colors include:
  - Background: `#f8fafc` (light gray-blue)
  - Surface: `#ffffff` (white)
  - Text Primary: `#0f172a` (dark slate)
  - Text Secondary: `#475569` (medium gray)
  - Border: `#e2e8f0` (light gray)
  - Proper contrast ratios for accessibility

**Location**: Lines 27-44

##### Theme Toggle Button Styles
- **Circular button** (48px diameter) with fixed positioning
- Positioned at `top: 1.5rem; right: 1.5rem`
- Smooth hover effects with scale transform
- Focus state with visible focus ring for keyboard navigation
- Active state with scale-down animation
- Shadow effects using CSS variables

**Location**: Lines 795-828

##### Icon Animations
- **Smooth icon transitions** between sun and moon icons
- Icons rotate and scale during theme switch
- Moon icon visible in dark mode, sun icon visible in light mode
- Opacity and transform transitions for smooth visual feedback

**Location**: Lines 830-855

##### Global Smooth Transitions
- **Added smooth transitions** for background colors, borders, and text colors
- Transition duration: 0.3s with ease timing function
- Selective transitions to prevent unwanted animations on specific elements
- Body element transitions for smooth theme changes

**Location**: Lines 56, 857-885

##### Responsive Design
- **Mobile optimization** for screens under 768px
- Toggle button resized to 44px on mobile devices
- Adjusted positioning for mobile layouts

**Location**: Lines 887-894

#### 3. JavaScript Functionality (`frontend/script.js`)

##### Theme Management Functions
- **`loadTheme()`**: Loads saved theme preference from localStorage on page load
  - Defaults to 'dark' theme if no preference saved
  - Sets `data-theme` attribute on document root

**Location**: Lines 226-229

- **`toggleTheme()`**: Switches between light and dark themes
  - Toggles `data-theme` attribute between 'dark' and 'light'
  - Saves preference to localStorage for persistence
  - Updates DOM immediately for instant visual feedback

**Location**: Lines 231-237

##### Event Listeners
- **Click event** on theme toggle button
- **Keyboard support** for Enter and Space keys
  - Prevents default behavior to avoid page scrolling
  - Makes button fully keyboard-accessible

**Location**: Lines 34-43

##### Initialization
- **Added theme toggle element** to DOM element references
- **Call `loadTheme()`** on page initialization
- Ensures theme is applied before content renders

**Location**: Lines 8, 18, 21

### Features Implemented

#### ✅ Toggle Button Design
- Icon-based design with sun/moon SVG icons
- Positioned in top-right corner
- Fits existing design aesthetic with rounded button and consistent styling
- Smooth hover, focus, and active states

#### ✅ Light Theme
- Complete light theme color palette
- High contrast ratios for accessibility (WCAG AA compliant)
- Maintains visual hierarchy from dark theme
- Proper colors for all UI elements (surfaces, borders, text, messages)

#### ✅ Smooth Animations
- 0.3s transition duration for theme changes
- Icon rotation and scale animations
- Background, border, and text color transitions
- Hover and click feedback animations

#### ✅ Accessibility
- ARIA label for screen readers
- Full keyboard navigation support (Enter/Space keys)
- Visible focus ring for keyboard users
- High contrast ratios in both themes
- Semantic HTML button element

#### ✅ Persistence
- Theme preference saved to localStorage
- Theme restored on page reload
- Defaults to dark theme for new users

### User Experience
- **Instant feedback**: Theme changes apply immediately without page reload
- **Smooth transitions**: All color changes animate smoothly
- **Visual clarity**: Icon clearly indicates current theme state
- **Accessibility**: Works with keyboard, screen readers, and mouse
- **Persistence**: User preference remembered across sessions
