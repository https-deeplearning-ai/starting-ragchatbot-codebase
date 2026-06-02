# Development Guide

This guide covers code quality tools and development workflows for this project.

## Code Quality Tools

This project uses industry-standard Python code quality tools to maintain consistency and correctness:

- **Black** - Code formatter (enforces consistent style)
- **Ruff** - Fast Python linter (style, imports, and best practices)
- **MyPy** - Static type checker (catches type-related bugs)
- **Pytest** - Testing framework (validates functionality)

## Quick Commands

All quality commands can be run via `uv run`:

### Format Code

```bash
# Format code automatically
uv run black backend/ main.py

# Or use the convenience script
./scripts/format.sh
```

### Lint Code

```bash
# Check for style and import issues
uv run ruff check backend/ main.py

# Or use the convenience script
./scripts/lint.sh
```

### Fix Linting Issues

```bash
# Auto-fix imports and common issues
uv run ruff check --fix backend/ main.py
```

### Type Checking

```bash
# Check type annotations
uv run mypy backend/ main.py --ignore-missing-imports

# Or use the convenience script
./scripts/type-check.sh
```

### Run Tests

```bash
# Run all tests
uv run pytest backend/tests/

# Run with verbose output
uv run pytest backend/tests/ -v

# Run specific test file
uv run pytest backend/tests/test_ai_generator.py -v
```

### Run All Quality Checks

```bash
# Run format, lint, type-check, and tests in sequence
./scripts/quality.sh

# Or using taskipy
uv run task quality
```

### Auto-Fix Issues

```bash
# Automatically fix formatting and import issues
./scripts/fix.sh

# Or using taskipy
uv run task quality-fix
```

## Taskipy Tasks

The following tasks are configured in `pyproject.toml`:

| Task | Command | Purpose |
|------|---------|---------|
| `test` | `uv run task test` | Run pytest on backend tests |
| `fmt` | `uv run task fmt` | Format code with black |
| `lint` | `uv run task lint` | Check code style with ruff |
| `type-check` | `uv run task type-check` | Type check with mypy |
| `quality` | `uv run task quality` | Run lint, type-check, and test |
| `quality-fix` | `uv run task quality-fix` | Auto-fix ruff and format with black |

## Tool Configuration

### Black (Code Formatter)

Configuration in `pyproject.toml`:
- **Line length**: 100 characters
- **Target**: Python 3.13
- **Excludes**: venv, .venv, chroma_db, __pycache__

Black is opinionated and non-configurable by design. It ensures consistent formatting across the codebase.

### Ruff (Linter)

Configuration in `pyproject.toml`:
- **Line length**: 100 characters
- **Selected rules**: E, W, F, I (imports), C4, UP, RUF
- **Ignored**: E501 (line too long - handled by black), W503 (line break before binary operator)

Ruff checks for:
- PEP 8 style violations
- Import ordering (via isort integration)
- Code complexity improvements
- Unnecessary comprehensions
- Code upgrades (pyupgrade)

### MyPy (Type Checker)

Configuration in `pyproject.toml`:
- **Python version**: 3.13
- **Strict-ish mode**: warns on untyped definitions and unused config
- **Ignores missing imports**: Enabled (many packages lack type stubs)

Type checking helps catch bugs early and improves code documentation.

## Pre-Commit Workflow

Recommended workflow before committing:

```bash
# 1. Auto-fix issues
./scripts/fix.sh

# 2. Review changes
git diff

# 3. Run all quality checks
./scripts/quality.sh

# 4. If tests pass, commit
git add .
git commit -m "your message"
```

## Continuous Improvement

### Adding Type Annotations

Gradually add type annotations to your code. Start with function signatures:

```python
# Before
def search_courses(query):
    results = []
    # ...
    return results

# After
def search_courses(query: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    # ...
    return results
```

### Fixing Linting Issues

Review ruff output and fix issues. Common issues:

- **E501**: Line too long → Black will handle on format
- **F841**: Unused variable → Remove or prefix with `_`
- **E302**: Too few blank lines → Add blank lines between functions
- **I001**: Unsorted imports → Run `ruff check --fix` or `fmt`

### Writing Tests

As the project grows, add tests:

```bash
# Run existing tests
uv run pytest backend/tests/ -v

# Add new test file
# backend/tests/test_new_feature.py

# Run new tests
uv run pytest backend/tests/test_new_feature.py -v
```

## Troubleshooting

### Black conflicts with other tools?

Black takes precedence. Other tools (ruff) are configured to not conflict:
- E501 (line too long) is disabled in ruff
- Import ordering is handled by ruff's isort integration

### MyPy says "error: Cannot find implementation or library stub"?

This is expected for packages without type information. Configuration:
- `ignore_missing_imports = true` ignores these errors
- Gradually add types as projects improve their stubs

### How to skip type checking for a line?

Use `# type: ignore` comment:

```python
result = some_untyped_function()  # type: ignore
```

### Need to disable a lint rule?

Use `# noqa` comments (ruff will skip the line):

```python
x = 1  # noqa: E501
```

Or disable for entire file (at top):

```python
# ruff: noqa: E501
```

## IDE Integration

### VS Code

Install extensions:
- Python (Microsoft)
- Black Formatter
- Pylance

Configure `.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit"
    }
  },
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true
}
```

### PyCharm

- **Settings > Tools > Python Integrated Tools > Default Test Runner**: pytest
- **Settings > Editor > Code Style > Python**: Use Black formatter
- Run → Edit Configurations to set up run scripts

## References

- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
