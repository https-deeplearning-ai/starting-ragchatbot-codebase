# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- Node.js 18+ and npm (only for the front-end formatter; the app itself has no build step)
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

Formatting is enforced by [black](https://black.readthedocs.io/) + [isort](https://pycqa.github.io/isort/)
for Python and [Prettier](https://prettier.io/) for the front end (`frontend/*.html|css|js`).

```bash
./scripts/format.sh    # auto-format everything in place
./scripts/check.sh     # verify formatting only, writes nothing (exits 1 if unformatted)
./scripts/quality.sh   # full gate: check.sh + pytest — run this before committing
```

`format.sh` and `check.sh` install the front-end dev dependency (Prettier) on first run.
Config lives in `pyproject.toml` (`[tool.black]`, `[tool.isort]`) and `.prettierrc.json`.

