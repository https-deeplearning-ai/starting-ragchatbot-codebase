# Development Scripts

This directory contains helper scripts for maintaining code quality in the RAG chatbot project.

## Available Scripts

### `format.sh`
Automatically formats Python code using Black and isort.

```bash
./scripts/format.sh
```

**What it does:**
- Applies Black code formatting (line length: 88 characters)
- Organizes imports with isort (compatible with Black)

### `lint.sh`
Runs linting and type checking tools.

```bash
./scripts/lint.sh
```

**What it does:**
- Runs Flake8 for style guide enforcement
- Runs MyPy for static type checking

### `quality-check.sh`
Runs all code quality checks without modifying files.

```bash
./scripts/quality-check.sh
```

**What it does:**
- Checks code formatting (Black)
- Checks import sorting (isort)
- Runs linting (Flake8)
- Runs type checking (MyPy)

**Note:** This script exits on the first error to help identify issues quickly.

## Pre-commit Hooks

To automatically run quality checks before each commit:

```bash
# Install hooks
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files

# Run on specific files
uv run pre-commit run --files backend/app.py
```

## Configuration

All tools are configured through files in the project root:

- **pyproject.toml**: Black, isort, and MyPy settings
- **.flake8**: Flake8 configuration
- **.pre-commit-config.yaml**: Pre-commit hooks

## Windows Users

These scripts are compatible with Git Bash on Windows. Make sure you have Git Bash installed and run scripts through it.
