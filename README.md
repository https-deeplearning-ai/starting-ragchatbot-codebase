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

This project uses several code quality tools to maintain consistent, clean code:

- **Black**: Automatic code formatting
- **isort**: Import statement sorting
- **Flake8**: Linting for code quality issues
- **Mypy**: Static type checking

#### Running Quality Checks

To run all quality checks at once:

```bash
# On Linux/macOS or Git Bash (Windows)
./quality.sh

# On Windows Command Prompt
quality.bat
```

This will check:
- Code formatting (Black)
- Import organization (isort)
- Code linting (Flake8)
- Type checking (Mypy)

#### Auto-formatting Code

To automatically format all Python code:

```bash
# On Linux/macOS or Git Bash (Windows)
./format.sh

# On Windows Command Prompt
format.bat
```

This will:
- Sort imports with isort
- Format code with Black

#### Configuration

All tools are configured in `pyproject.toml` (Black, isort, Mypy) and `.flake8` (Flake8).

Key settings:
- Line length: 88 characters (Black default)
- Python version: 3.13
- Excludes: `.venv`, `chroma_db`, build directories

## Testing

The project includes automated testing infrastructure for API endpoints and functionality.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=backend
```

