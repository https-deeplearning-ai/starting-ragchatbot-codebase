# Frontend Code Quality Tools - Changes Made

## Overview

Added essential code quality tools to the frontend development workflow, implementing automatic code formatting with Prettier and JavaScript linting with ESLint.

## Files Added

### Package Configuration

- **`frontend/package.json`** - New npm package configuration with:
  - Prettier (^3.2.0) for code formatting
  - ESLint (^8.56.0) for JavaScript linting
  - npm scripts for running quality checks

### Prettier Configuration

- **`frontend/.prettierrc`** - Prettier configuration:
  - 4-space indentation
  - Single quotes
  - Semicolons required
  - Trailing commas in ES5 contexts
  - 100 character line width

- **`frontend/.prettierignore`** - Files excluded from formatting:
  - node_modules/
  - dist/, build/
  - Minified files (*.min.js, *.min.css)

### ESLint Configuration

- **`frontend/.eslintrc.json`** - ESLint configuration:
  - Browser environment enabled
  - ES2021 syntax support
  - Recommended rules extended
  - Custom rules: prefer-const, no-var, eqeqeq, curly
  - Global `marked` library declared

- **`frontend/.eslintignore`** - Files excluded from linting:
  - node_modules/
  - dist/, build/
  - Minified files

### Development Scripts

- **`frontend/scripts/quality-check.sh`** - Runs both format check and linting
- **`frontend/scripts/format.sh`** - Auto-formats all frontend code

### Git Configuration

- **`frontend/.gitignore`** - Excludes node_modules from version control

## Available npm Scripts

Run these from the `frontend/` directory:

| Command | Description |
|---------|-------------|
| `npm run format` | Auto-format all files with Prettier |
| `npm run format:check` | Check if files are properly formatted |
| `npm run lint` | Run ESLint on JavaScript files |
| `npm run lint:fix` | Run ESLint and auto-fix issues |
| `npm run quality` | Run both format check and lint |
| `npm run quality:fix` | Auto-fix both formatting and linting issues |

## Shell Scripts

| Script | Description |
|--------|-------------|
| `./scripts/quality-check.sh` | Full quality check (installs deps if needed) |
| `./scripts/format.sh` | Format code (installs deps if needed) |

## Usage

### Initial Setup

```bash
cd frontend
npm install
```

### Running Quality Checks

```bash
# Check formatting and linting
npm run quality

# Or use the shell script
./scripts/quality-check.sh
```

### Auto-fixing Issues

```bash
# Fix all formatting and linting issues
npm run quality:fix
```

## Code Formatting Applied

The existing frontend files have been formatted with Prettier:
- `index.html`
- `script.js`
- `style.css`

All files now follow consistent formatting standards.
