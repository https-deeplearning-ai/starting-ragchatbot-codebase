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

## Code Quality

This project includes comprehensive code quality tools to maintain clean, consistent code:

### Available Scripts

```bash
# Format all Python code (black + isort)
./scripts/format.sh

# Run all quality checks (black, isort, flake8, mypy, tests)
./scripts/check-quality.sh

# Set up git pre-commit hooks (one-time setup)
./scripts/setup-hooks.sh
```

### Tools Included

- **Black**: Python code formatter (88-character line length)
- **isort**: Import statement organizer
- **flake8**: Linter for code style and error checking
- **mypy**: Optional static type checking

### Development Workflow

1. Make code changes
2. Run `./scripts/format.sh` to fix formatting
3. Run `./scripts/check-quality.sh` to verify quality
4. Commit changes (pre-commit hooks will run automatically)

### Pre-commit Hooks

Set up automatic quality checks before each commit:
```bash
./scripts/setup-hooks.sh
```

After setup, git will automatically run quality checks before allowing commits. To bypass temporarily:
```bash
git commit --no-verify -m "Your commit message"
```

