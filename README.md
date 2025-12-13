# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Development

### Code Quality Tools

This project uses modern Python code quality tools to maintain consistent, high-quality code:

- **Black** - Automatic code formatting (100 char line length)
- **Ruff** - Fast linting and import sorting (10-100x faster than flake8/isort)
- **mypy** - Static type checking for type safety
- **pytest** - Testing framework with 49 tests

### Running Quality Checks

```bash
# Auto-fix formatting and linting issues
./scripts/fix.sh

# Format code only
./scripts/format.sh

# Run linters (Ruff + mypy)
./scripts/lint.sh

# Run tests
./scripts/test.sh

# Run all checks (formatting + linting + tests)
./scripts/quality.sh
```

### Before Committing

Always run quality checks before committing code:

```bash
./scripts/quality.sh
```

This ensures:
- Code is consistently formatted
- No linting errors
- Type hints are valid
- Tests pass

### Code Quality Configuration

All tools are configured in `pyproject.toml`:
- Black uses 100-character line length for better readability
- Ruff performs fast linting with modern Python best practices
- mypy is configured leniently to allow gradual type adoption
- Configuration can be adjusted as the project matures

