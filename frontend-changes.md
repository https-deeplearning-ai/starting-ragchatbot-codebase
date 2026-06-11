# Frontend Quality Tooling Changes

## Summary

Added Prettier for automatic code formatting and ESLint for static analysis, along with development scripts to run quality checks from the project root.

## New Files

### `frontend/package.json`
Node package manifest defining the project as an ES module and declaring dev dependencies:
- `prettier@^3.3.0` — code formatter
- `eslint@^9.0.0` — static analysis

npm scripts:
- `npm run format` — format all frontend files in-place
- `npm run format:check` — check formatting without writing (CI-safe)
- `npm run lint` — lint `script.js` with ESLint
- `npm run quality` — run both `format:check` and `lint` together

### `frontend/.prettierrc`
Prettier configuration:
- 100-character print width
- 2-space indentation
- Single quotes for JS strings
- Trailing commas where valid in ES5
- LF line endings

### `frontend/.prettierignore`
Excludes `node_modules/` from formatting.

### `frontend/eslint.config.js`
Flat ESLint config (ESLint 9 format) targeting `script.js` with browser globals (`document`, `window`, `fetch`, `marked`). Rules enforced:
- `no-var` error — require `let`/`const`
- `eqeqeq` error — require `===`
- `no-undef` error — catch typos
- `prefer-const` / `no-unused-vars` warnings

### `scripts/frontend-quality.sh`
Root-level script to run all quality checks in one step:
```bash
bash scripts/frontend-quality.sh
```

### `scripts/frontend-format.sh`
Root-level script to auto-format all frontend files:
```bash
bash scripts/frontend-format.sh
```

## Modified Files

### `frontend/script.js`, `frontend/style.css`, `frontend/index.html`
Reformatted by Prettier on initial setup. Changes were whitespace/indentation only — no logic or structure was altered.
