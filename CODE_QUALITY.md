# Code Quality Setup

This document describes the code quality tools and practices set up for this project.

## Tools Installed

### 1. Black (Code Formatter)
- **Purpose**: Automatic code formatting for consistent style
- **Line length**: 88 characters
- **Target**: Python 3.13

### 2. isort (Import Sorter)
- **Purpose**: Organizes and sorts imports
- **Profile**: Black-compatible
- **Sections**: FUTURE, STDLIB, THIRDPARTY, FIRSTPARTY, LOCALFOLDER

### 3. Flake8 (Linter)
- **Purpose**: Style guide enforcement (PEP 8)
- **Max line length**: 88 characters
- **Max complexity**: 10
- **Ignored errors**: E203, E266, E501, W503 (Black compatibility)

### 4. MyPy (Type Checker)
- **Purpose**: Static type checking
- **Mode**: Gradual typing (not strict mode)
- **Python version**: 3.13

### 5. Pre-commit (Git Hooks)
- **Purpose**: Automatic quality checks before commits
- **Hooks**: Black, isort, Flake8, MyPy, trailing whitespace, end-of-file fixer, YAML/JSON/TOML checks

## Usage

### Quick Commands

```bash
# Format code
./scripts/format.sh

# Run linting
./scripts/lint.sh

# Run all quality checks
./scripts/quality-check.sh

# Install pre-commit hooks
uv run pre-commit install
```

### Individual Tools

```bash
# Black
uv run black backend/ main.py              # Format
uv run black --check backend/ main.py      # Check only

# isort
uv run isort backend/ main.py              # Sort imports
uv run isort --check-only backend/ main.py # Check only

# Flake8
uv run flake8 backend/ main.py             # Lint

# MyPy
uv run mypy backend/ main.py               # Type check

# Pre-commit
uv run pre-commit run --all-files          # Run all hooks
```

## Configuration Files

### `pyproject.toml`
Contains configuration for:
- Black: Formatting rules and exclusions
- isort: Import sorting rules
- MyPy: Type checking settings

### `.flake8`
Contains Flake8 linting rules:
- Max line length
- Ignored error codes
- Excluded directories
- Per-file ignore rules

### `.pre-commit-config.yaml`
Defines pre-commit hooks:
- Black (v25.9.0)
- isort (v6.1.0)
- Flake8 (v7.3.0)
- MyPy (v1.18.2)
- Various file checks

## Current Status

- All 17 Python files have been formatted with Black
- All imports have been sorted with isort
- Pre-commit hooks installed and ready to use

## Known Issues

Some Flake8 warnings exist in the current codebase:
- E402: Module level imports not at top of file (mainly in app.py and test files)
- F401: Unused imports (in tests and some modules)
- F841: Unused variables (in some test files)
- C901: High complexity in DocumentProcessor.process_course_document

These can be addressed incrementally without blocking development.

## Best Practices

1. **Before committing**: Run `./scripts/quality-check.sh` to ensure code passes all checks
2. **Use pre-commit hooks**: They will automatically format and check your code
3. **Format frequently**: Run `./scripts/format.sh` while developing
4. **Address linting issues**: Fix Flake8 warnings before committing when possible
5. **Add type hints**: MyPy is configured for gradual typing; add hints incrementally

## IDE Integration

### VS Code
Install these extensions:
- Python (ms-python.python)
- Black Formatter (ms-python.black-formatter)
- isort (ms-python.isort)
- Flake8 (ms-python.flake8)
- Mypy Type Checker (ms-python.mypy-type-checker)

Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.linting.flake8Enabled": true,
  "python.linting.enabled": true,
  "isort.check": true
}
```

### PyCharm
1. Go to Settings → Tools → Black
2. Enable "On save" formatting
3. Configure File Watcher for isort
4. Enable Flake8 inspection

## CI/CD Integration

To integrate these checks into CI/CD pipelines, add this to your workflow:

```yaml
- name: Run code quality checks
  run: |
    uv run black --check backend/ main.py
    uv run isort --check-only backend/ main.py
    uv run flake8 backend/ main.py
    uv run mypy backend/ main.py
```

## Maintenance

### Updating Tools

```bash
# Update all dev dependencies
uv sync --upgrade

# Update specific tool
uv add --dev black@latest

# Update pre-commit hooks
uv run pre-commit autoupdate
```

### Temporarily Bypassing Hooks

```bash
# Skip pre-commit hooks (not recommended)
git commit --no-verify
```

## Resources

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
