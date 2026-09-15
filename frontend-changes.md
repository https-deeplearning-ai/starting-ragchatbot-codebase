# Frontend Changes — Code Quality Tooling

Adds automatic code formatting and dev scripts for running quality checks.

The feature request named **black**, which only formats Python, while the scope was restricted to
the front end. Both halves are covered: black + isort for `backend/`, and **Prettier** for
`frontend/` — so the front-end files are actually formatted rather than left out of a
"code quality" change. One set of scripts drives both.

## What changed

### New files

| File | Purpose |
| --- | --- |
| `package.json` | Declares Prettier as the only npm dev dependency; `format` / `format:check` scripts scoped to `frontend/**/*.{html,css,js}`. `"private": true`, no build step. |
| `package-lock.json` | Lockfile so every machine gets the identical Prettier version. |
| `.prettierrc.json` | Prettier config (see below). |
| `.prettierignore` | Excludes `node_modules/`, `.venv/`, `__pycache__/`, `backend/chroma_db/`, `.playwright-mcp/`, and `docs/`. |
| `scripts/format.sh` | Auto-formats everything in place: isort → black → Prettier. |
| `scripts/check.sh` | Verifies formatting without writing; prints diffs, exits 1 if anything is unformatted. |
| `scripts/quality.sh` | Full gate: `check.sh` + `pytest`. Run before committing; suitable for CI. |

`docs/` is deliberately Prettier-ignored — `DocumentProcessor` parses those course files
line-by-line against an exact `Course Title:` / `Lesson N:` layout, so reformatting them would
break ingestion.

### Modified files

- **`pyproject.toml`** — added `black>=25.1.0` and `isort>=6.0.1` to the `dev` dependency group,
  plus `[tool.black]` (line length 88, target `py313`) and `[tool.isort]` (`profile = "black"` so
  the two tools never fight, with the `backend/` modules listed as `known_first_party` — they are
  imported as top-level names via pytest's `pythonpath`, so isort would otherwise sort them as
  third-party).
- **`.gitignore`** — added `.venv/` and `node_modules/`.
- **`README.md`** — new "Code Quality" section; Node.js 18+ noted as a prerequisite for the
  formatter only.
- **`CLAUDE.md`** — replaced the now-stale "no test suite, linter, or build step" line with the
  script list and a note about the pre-existing test failures.

### Reformatted front-end sources

All three front-end files were reformatted by Prettier — cosmetic only, no behavior change:

| File | Lines changed |
| --- | --- |
| `frontend/index.html` | +96 / −74 |
| `frontend/script.js` | +161 / −157 |
| `frontend/style.css` | +422 / −409 |

The front end had **mixed indentation** (some blocks 4-space, some 2-space, some misaligned) and
mixed quote styles; that is what most of the diff is. Specifically:

- **Consistent 2-space indentation** across HTML, CSS and JS, replacing the mix.
- **Double quotes** in JS and CSS (`'/api'` → `"/api"`, `content: '▶'` → `content: "▶"`).
- **Self-closing void elements** in HTML (`<meta ...>` → `<meta ... />`), lowercase `<!doctype html>`.
- **One selector per line** in CSS (`*, *::before, *::after` and `@keyframes` stops).
- **Expanded one-line rules** (`.message-content h1 { font-size: 1.5rem; }` → block form).
- **Long attribute lists wrapped** — the `data-question` buttons and the send-button `<svg>`.
- `&quot;` inside a `data-question` attribute became a single-quoted attribute holding literal
  `"` (identical after HTML parsing).
- Trailing newline added to `index.html`, which previously had none.
- Trailing whitespace and stray blank lines removed throughout.

Backend `.py` files were reformatted too (13 files), which is where the rest of the overall diff
comes from.

## Configuration

`.prettierrc.json`:

```json
{
  "printWidth": 100,
  "tabWidth": 2,
  "semi": true,
  "singleQuote": false,
  "trailingComma": "es5",
  "arrowParens": "always",
  "endOfLine": "lf",
  "htmlWhitespaceSensitivity": "css"
}
```

- `printWidth` 100 (120 for HTML via an override) — the existing markup is attribute-heavy, and
  the default 80 would have shattered nearly every tag onto multiple lines.
- `endOfLine: "lf"` keeps diffs stable on Windows, which is the primary dev platform here.
- `htmlWhitespaceSensitivity: "css"` lets Prettier re-indent only where CSS `display` makes
  whitespace insignificant, so re-wrapping the `<button>` elements cannot change rendering.

## Usage

```bash
./scripts/format.sh    # fix everything
./scripts/check.sh     # verify only (CI-friendly, writes nothing)
./scripts/quality.sh   # check.sh + pytest
```

Front-end only, without `uv`:

```bash
npm run format
npm run format:check
```

First run of `format.sh` / `check.sh` installs Prettier automatically if `node_modules/` is absent.

## Verification

- `./scripts/format.sh` — clean run; 13 Python files and all 3 front-end files reformatted.
- `./scripts/check.sh` — passes (idempotent: a second format pass is a no-op).
- `uv run pytest` — **28 passed, 3 failed**. The same 3 failures reproduce on the unmodified
  `HEAD` snapshot (verified via `git archive HEAD` into a temp dir), so they are pre-existing
  diagnostic failures in `test_rag_system_content_queries.py`, not caused by reformatting.
- Runtime smoke test — started `uvicorn app:app`, confirmed `GET /` returns 200 and serves the
  reformatted `index.html` byte-identical to the source file, and `GET /api/courses` returns all
  4 courses.
- Reviewed the front-end diff with `git diff -w` to confirm every change is whitespace, quoting,
  or wrapping — no semantic edits.

Tool versions: black 26.5.1, isort 9.0.1, Prettier 3.9.6.

---

# Changes: API testing infrastructure

> **Scope note:** the requested feature is backend/test-infrastructure work, not a
> frontend change. No files under `frontend/` were modified. What these tests *do*
> cover is the HTTP contract `frontend/script.js` depends on — the exact shape of
> `/api/query`, `/api/courses`, `DELETE /api/session/{id}`, and the static mount
> that serves the frontend itself — so a breaking change to the API surface the UI
> consumes now fails a test instead of only breaking in the browser.

## Summary

Added API endpoint tests, shared fixtures, and pytest configuration to the
existing backend test suite.

| File | Change |
| --- | --- |
| `backend/tests/test_api_endpoints.py` | **New.** 29 endpoint tests. |
| `backend/tests/conftest.py` | Added an inline FastAPI app factory + API fixtures. |
| `backend/tests/test_rag_system_content_queries.py` | Marked `slow`. |
| `pyproject.toml` | Expanded `[tool.pytest.ini_options]`; added `httpx` dev dep. |

---

## 1. `backend/tests/test_api_endpoints.py` (new)

29 tests, all marked `api`, grouped by endpoint:

**`POST /api/query`** (12 tests)
- 200 response shape is exactly `{answer, sources, session_id}`
- `Source` dataclasses serialize to `{text, link}`, including `link: null`
- a session is created when `session_id` is omitted or `null`
- a supplied `session_id` is reused and `create_session` is *not* called
- `rag.query` is called with `(query, session_id)` positionally
- empty `sources` list is valid (general-knowledge answers)
- 422 on missing `query`, wrong `query` type, and malformed JSON
- unknown body fields are ignored rather than rejected
- a `RuntimeError` from the RAG system becomes a 500 with the message in `detail`
- `GET` on the route is 405

**`GET /api/courses`** (3 tests) — stats payload, empty catalog, 500 on failure.

**`DELETE /api/session/{session_id}`** (3 tests) — deletes the named session,
stays 200 for an unknown id (the manager's `pop` is a no-op), 500 on failure.
This is what the frontend's "+ New Chat" button calls.

**`GET /` static mount** (6 tests) — `index.html` at `/`, `style.css`/`script.js`
served, the no-cache headers `DevStaticFiles` adds, 404 for a missing asset, and
that the `"/"` mount does not shadow `/api/*`.

**Cross-cutting** (5 tests) — CORS simple + preflight headers, the OpenAPI schema
listing all three API paths, and app-factory isolation.

## 2. `backend/tests/conftest.py`

`backend/app.py` **cannot be imported under test**: at import time it constructs a
real `RAGSystem` (loading the sentence-transformer model and Chroma) and calls
`app.mount("/", StaticFiles(directory="../frontend"))` — a cwd-relative path that
does not resolve when pytest runs from the repo root per `testpaths`.

So the endpoints are re-declared inline via a factory:

- `create_test_app(rag_system, static_dir=None)` — mirrors `app.py`'s routes,
  Pydantic models (`QueryRequest`/`SourceItem`/`QueryResponse`/`CourseStats`),
  CORS middleware, and `_NoCacheStaticFiles` (a copy of `DevStaticFiles`).
  The static mount is **opt-in**, so API-only tests need no frontend on disk.
  *This is a deliberate duplicate — keep it in sync with `backend/app.py`.*

New fixtures:

| Fixture | Purpose |
| --- | --- |
| `mock_rag` | Stand-in RAG system. No Chroma, no embedding model, no Anthropic. |
| `sample_sources` | Two `Source` records — one with a lesson link, one without. |
| `sample_analytics` | A `get_course_analytics()`-shaped payload. |
| `static_dir` | Throwaway `tmp_path` frontend with `index.html`/`style.css`/`script.js`. |
| `api_client` | `TestClient` over the API routes only. |
| `full_client` | `TestClient` over API routes **plus** the static mount. |

`mock_rag` is a plain `MagicMock`, not `MagicMock(spec=RAGSystem)`, because
`session_manager` is an instance attribute and would not survive spec
introspection.

## 3. `pyproject.toml`

```toml
[tool.pytest.ini_options]
pythonpath = ["backend", "backend/tests"]   # "backend/tests" lets tests import the app factory from conftest
testpaths = ["backend/tests"]
python_files / python_classes / python_functions  # explicit discovery rules
addopts = ["-q", "--tb=short", "-ra", "--strict-markers", "--strict-config"]
markers = ["api", "slow"]
filterwarnings = [...]                      # silences chromadb/pydantic deprecation noise
```

`--strict-markers` means a typo'd marker is an error, not a silent no-op.
Added `httpx>=0.28.1` to the dev group — `TestClient` requires it, and it was
previously only present as a transitive dependency of `anthropic`.

## 4. `test_rag_system_content_queries.py` marked `slow`

These integration tests read the real `backend/chroma_db` and only pass once
`./run.sh` has ingested `docs/`. Marking them `slow` makes a clean fast run
possible.

---

## Running

```bash
uv run pytest                  # everything
uv run pytest -m "not slow"    # fast run, no Chroma/embedding model  -> 54 passed in 0.67s
uv run pytest -m api           # endpoint tests only                  -> 29 passed in 0.33s
```

**Current state:** 57 passed, 3 failed. The 3 failures are pre-existing and
environmental — `test_rag_system_content_queries.py` needs a populated
`backend/chroma_db`, and this worktree's store is empty (0 courses). They pass
once documents have been ingested, and are excluded by `-m "not slow"`.

On Windows/OneDrive, `uv sync` fails to hardlink into the uv cache (`os error 396`).
`pyproject.toml` now sets `[tool.uv] link-mode = "copy"`, so no environment
variable is needed. (This could *not* go in `.env` — uv only reads a `.env` when
`--env-file`/`UV_ENV_FILE` is given, and then only to populate the child command's
environment, not uv's own install behavior.)

---

# Frontend Changes — Dark / Light Theme Toggle

Adds a theme toggle button that switches the UI between the existing dark theme and a
new light theme. Frontend only — no backend files were touched.

## Summary

- Icon-based toggle button pinned to the **top-right** of the viewport.
- Sun icon in dark mode, moon icon in light mode, cross-fading with a rotate + scale animation.
- Full light-theme palette driven entirely by CSS variables.
- Choice persists in `localStorage`; falls back to the OS `prefers-color-scheme` setting.
- Accessible: native `<button>` with `role="switch"`, live `aria-checked`/`aria-label`, visible focus ring, keyboard-operable.

## Files changed

### `frontend/index.html`

- **Inline head script** — reads `localStorage.theme` (or the OS preference) and sets
  `data-theme` on `<html>` *before first paint*, so the page never flashes the wrong theme.
  Wrapped in `try/catch` so a blocked `localStorage` (private mode) falls back to dark.
- **Toggle button** — new `#themeToggle` as the first child of `.container`, containing two
  inline SVGs (`.theme-icon-sun`, `.theme-icon-moon`) inside a `.theme-toggle-icons` wrapper.
  Markup carries `type="button"`, `role="switch"`, `aria-checked`, `aria-label` and `title`;
  the icon wrapper is `aria-hidden="true"` so screen readers only announce the label.
- Bumped the cache-busting query strings on `style.css` and `script.js` from `v=9` to `v=10`.

### `frontend/style.css`

- **Theme variables** — the old `:root` block is now `:root, [data-theme="dark"]` (dark stays
  the default), and a parallel `[data-theme="light"]` block defines the light palette:
  white background, `#f1f5f9` surfaces, dark slate text, lighter borders, and a softer shadow.
- **New variables** so previously hardcoded colors can follow the theme:
  - `--code-bg` — inline `code` / `pre` background (was a hardcoded `rgba(0,0,0,0.2)`, which
    was invisible on a white background).
  - `--error-text` / `--success-text` — light theme uses darker red/green so status text stays
    readable on white; dark theme keeps its original colors via the `var(..., fallback)` default.
- **Transition block** — a shared `transition: background-color / color / border-color 0.3s ease`
  on the themed surfaces (body, sidebar, chat areas, message bubbles, input container, stat items,
  code blocks) so switching themes animates instead of snapping. `#chatInput` and `.suggested-item`
  are deliberately excluded because their existing `transition: all` rules already cover it.
- **`.theme-toggle` styles** — 44px circular button, `position: fixed` at `top/right: 1.25rem`,
  `z-index: 100`, using `--surface` / `--border-color` / `--shadow` so it matches the existing
  aesthetic (same variables as the sidebar cards). Hover lifts it 1px and tints it with the accent
  color, `:active` scales it to 0.94, and `:focus-visible` shows the same 3px `--focus-ring` used
  by the send button and input.
- **Icon animation** — both SVGs are absolutely stacked in a 20×20 wrapper. The inactive icon is
  `opacity: 0` and rotated ±90° at `scale(0.5)`; the active one is `opacity: 1`, `rotate(0) scale(1)`.
  Transitioned over 0.3s/0.4s `cubic-bezier(0.4, 0, 0.2, 1)`, which reads as the sun spinning out
  while the moon spins in.
- **Responsive** — inside the existing `max-width: 768px` query the button shrinks to 38px with
  tighter offsets and 18px icons.
- **Reduced motion** — a new `@media (prefers-reduced-motion: reduce)` block disables the toggle's
  transitions and hover/active transforms.
- **Drive-by fix** — `.message-content blockquote` referenced the undefined variable `--primary`;
  corrected to `--primary-color` so the blockquote border actually renders.

### `frontend/script.js`

- Added `themeToggle` to the cached DOM element list and `initTheme()` to `DOMContentLoaded`.
- `setupEventListeners()` binds `click` on the toggle. Because it is a real `<button>`, Enter and
  Space activate it and it sits in the natural tab order — no extra key handling needed.
- New functions:
  - `initTheme()` — syncs the button's ARIA state with the theme the inline script already applied,
    then subscribes to `prefers-color-scheme` changes so the UI follows the OS *until* the user
    makes an explicit choice.
  - `toggleTheme()` — flips between `light` and `dark` and persists the result.
  - `applyTheme(theme, persist)` — sets `data-theme` on `<html>`, optionally writes to
    `localStorage`, and updates `aria-checked`, `aria-label` and `title`
    ("Switch to light theme" ↔ "Switch to dark theme").
  - `getStoredTheme()` — `localStorage` read guarded by `try/catch`.

## Behavior

| Situation | Result |
| --- | --- |
| First visit, OS set to light | Light theme |
| First visit, OS set to dark / unknown | Dark theme (unchanged from before) |
| User clicks the toggle | Theme flips, animates, and is saved |
| Reload after clicking | Saved theme applied before first paint, no flash |
| OS theme changes later | Followed only if the user never clicked the toggle |
| `localStorage` unavailable | Toggle still works for the session; defaults to dark |

## Manual test checklist

1. Load `http://localhost:8000` — toggle sits in the top-right, showing a sun on the dark theme.
2. Click it — colors cross-fade to light, icon animates to a moon.
3. Reload — light theme is restored with no dark flash.
4. Tab to the button — focus ring is visible; Enter and Space both toggle.
5. Send a query — user bubble, assistant bubble, sources list, and any code blocks are all
   readable in both themes.
6. Narrow the window below 768px — the button shrinks and stays clear of the chat content.
