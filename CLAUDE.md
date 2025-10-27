# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) system for answering questions about course materials using semantic search and AI-powered responses. The system uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.

## Development Commands

### Running the Application
```bash
# Quick start (recommended)
chmod +x run.sh
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependencies
uv add package_name

# Run Python scripts with uv
uv run script.py
```

### Code Quality Tools
```bash
# Format all code (black + isort)
./scripts/format.sh

# Run all quality checks
./scripts/check-quality.sh

# Set up git pre-commit hooks
./scripts/setup-hooks.sh
```

### Environment Setup
```bash
# Create .env file with:
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Architecture Overview

The system follows a modular RAG architecture:

```
Frontend (static files) → FastAPI Backend → RAG System → Components
                                      ↓
                              ChromaDB Vector Store
                                      ↓
                              Anthropic Claude API
```

### Key Components

**RAG System (`backend/rag_system.py`)**
- Main orchestrator that coordinates all components
- Handles document ingestion and query processing
- Manages tool-based search with conversation context

**Vector Store (`backend/vector_store.py`)**
- ChromaDB-based vector storage for semantic search
- Stores course metadata and content chunks
- Handles similarity search operations

**Document Processor (`backend/document_processor.py`)**
- Extracts structured course information from documents
- Creates text chunks with overlap for vector storage
- Supports PDF, DOCX, and TXT formats

**AI Generator (`backend/ai_generator.py`)**
- Interfaces with Anthropic's Claude API
- Tool-based search integration for accurate responses
- Conversation context management

**Search Tools (`backend/search_tools.py`)**
- Tool manager for course content search
- Integrates with vector store for semantic search
- Provides structured search capabilities

**Session Manager (`backend/session_manager.py`)**
- Maintains conversation history and context
- Session-based query enhancement

## Configuration

Configuration is managed through `backend/config.py`:
- **Chunk Settings**: `CHUNK_SIZE` (800), `CHUNK_OVERLAP` (100)
- **Search Settings**: `MAX_RESULTS` (5), `MAX_HISTORY` (2)
- **Models**: `EMBEDDING_MODEL` (all-MiniLM-L6-v2), `ANTHROPIC_MODEL` (claude-sonnet-4-20250514)
- **Storage**: ChromaDB data stored in `./chroma_db`

## Document Storage

- Course documents are stored in the `docs/` directory
- Supported formats: PDF, DOCX, TXT
- Documents are automatically processed and added to vector store on startup
- The system prevents duplicate course processing

## API Endpoints

- `POST /api/query` - Main query endpoint with session support
- `GET /api/courses` - Course statistics and analytics
- `GET /docs` - FastAPI auto-generated documentation
- `GET /` - Frontend web interface

## Code Quality Workflow

This project includes comprehensive code quality tools to maintain consistent, clean code:

### Tools Included
- **Black**: Python code formatter (88-character line length)
- **isort**: Import statement organizer
- **flake8**: Linter for code style and error checking
- **mypy**: Optional static type checking

### Configuration
- `pyproject.toml`: Black, isort, and MyPy settings
- `.flake8`: Linting rules and exclusions

### Daily Development Workflow
1. **Before committing**: Run `./scripts/check-quality.sh` to ensure code passes all checks
2. **Fix formatting**: Run `./scripts/format.sh` to automatically fix formatting issues
3. **Pre-commit hooks**: Run `./scripts/setup-hooks.sh` to set up automatic quality checks

### Git Integration
The project supports automatic pre-commit hooks that run quality checks before allowing commits:
```bash
# Set up hooks (one-time setup)
./scripts/setup-hooks.sh

# Commit normally (hooks run automatically)
git commit -m "Your changes"

# Skip hooks if needed (not recommended)
git commit --no-verify -m "Your changes"
```

## Development Notes

- The application automatically loads documents from `../docs` on startup
- Frontend files are served as static files from `../frontend`
- The system uses sentence-based chunking with overlap for better context
- Tool-based search ensures accurate, course-specific responses
- Session management maintains conversation context for follow-up questions
- All code is automatically formatted with Black and imports sorted with isort
- Pre-commit hooks ensure code quality before changes are committed