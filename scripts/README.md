# Development Scripts

Convenience scripts for code quality checks and development tasks.

## Available Scripts

- **format.sh** - Format code with Black
- **lint.sh** - Lint code with Ruff
- **type-check.sh** - Type check with MyPy
- **fix.sh** - Auto-fix formatting and linting issues
- **quality.sh** - Run all quality checks (format, lint, type-check, test)

## Usage

```bash
# Format code
./scripts/format.sh

# Check for issues
./scripts/lint.sh

# Type checking
./scripts/type-check.sh

# Auto-fix issues
./scripts/fix.sh

# Run everything
./scripts/quality.sh
```

## Quick Start

1. Make changes to code
2. Run `./scripts/fix.sh` to auto-fix issues
3. Run `./scripts/quality.sh` to verify everything passes
4. Commit your changes

For more details, see [DEVELOPMENT.md](../DEVELOPMENT.md)
