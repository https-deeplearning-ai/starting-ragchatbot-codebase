# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL: Package Management

**ALWAYS use `uv` for ALL dependency management operations. NEVER use `pip` directly.**

This project uses `uv` as its package manager. All Python commands must be run through `uv run`:

```bash
# ✅ CORRECT - Use uv
uv sync                           # Install/sync dependencies
uv run python script.py           # Run Python scripts
uv run uvicorn app:app --reload   # Run servers
uv add package-name               # Add new dependency
uv remove package-name            # Remove dependency

# ❌ WRONG - Do NOT use
pip install package-name          # Don't use pip
python script.py                  # Don't run Python directly
```

## Project Overview

This is a **RAG (Retrieval-Augmented Generation) system** for course materials. It allows users to query educational content and receive AI-powered responses backed by semantic search across course documents.

**Tech Stack:**
- Backend: FastAPI + Python 3.13
- Vector Database: ChromaDB with sentence-transformers embeddings
- AI: Anthropic Claude API (claude-sonnet-4-20250514)
- Frontend: Vanilla HTML/CSS/JavaScript
- **Package Manager: uv** (not pip)

## Development Commands

### Running the Application

```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

Application URLs:
- Frontend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### Package Management

See **"⚠️ CRITICAL: Package Management"** section at the top of this file.

All dependency operations use `uv` exclusively:
- Install dependencies: `uv sync`
- Add packages: `uv add <package>`
- Remove packages: `uv remove <package>`
- Run commands: `uv run <command>`

**Adding New Dependencies:**
When adding new packages to this project, always use `uv add`:
```bash
uv add anthropic          # Add to project dependencies
uv add --dev pytest       # Add development dependency
```

This updates both `pyproject.toml` and `uv.lock` automatically.

### Environment Setup

Create `.env` in project root:
```
ANTHROPIC_API_KEY=your_key_here
```

### Code Quality Tools

This project uses several code quality tools to maintain consistent, high-quality code:

**Tools:**
- **black**: Code formatter (line length: 100)
- **isort**: Import sorter (compatible with black)
- **flake8**: Linting and style checking
- **mypy**: Static type checking

**Quality Check Scripts:**

```bash
# Format code (auto-fix)
./scripts/format.sh

# Run linting and type checking
./scripts/lint.sh

# Run all checks (format check, lint, type check, tests)
./scripts/check.sh
```

**Manual Commands:**

```bash
# Format code
uv run black backend/ *.py
uv run isort backend/ *.py

# Check formatting without modifying
uv run black --check backend/ *.py
uv run isort --check-only backend/ *.py

# Run linting
uv run flake8 backend/ *.py

# Run type checking
uv run mypy backend/ *.py
```

**Configuration:**
- Tool settings are in `pyproject.toml` ([tool.black], [tool.isort], [tool.mypy])
- Flake8 settings are in `.flake8` (doesn't support pyproject.toml)
- All tools configured to use 100-character line length
- Excludes: `.venv`, `venv`, `chroma_db`

**Pre-commit Checklist:**
Before committing code, run `./scripts/check.sh` to ensure all quality checks pass.

## Architecture

### Core Components (backend/)

The system follows a modular architecture with clear separation of concerns:

1. **app.py** - FastAPI application entry point
   - Serves static frontend files
   - Exposes `/api/query` and `/api/courses` endpoints
   - Initializes RAGSystem and loads documents from `../docs` on startup

2. **rag_system.py** - Main orchestrator
   - Coordinates all components (document processor, vector store, AI generator, session manager)
   - `add_course_document()`: Process and add single course
   - `add_course_folder()`: Batch process all documents in a folder
   - `query()`: Execute RAG query using tool-based search

3. **vector_store.py** - ChromaDB interface
   - Two collections: `course_catalog` (course metadata) and `course_content` (chunked text)
   - `search()`: Unified search interface with course name resolution and content filtering
   - Uses semantic matching for course names (partial matches work)

4. **ai_generator.py** - Claude API integration
   - Uses Anthropic's tool calling for structured search
   - `generate_response()`: Handles tool execution flow
   - Temperature: 0, Max tokens: 800

5. **document_processor.py** - Course document parsing
   - Expects specific format: Course metadata (title/link/instructor) followed by lessons
   - `chunk_text()`: Sentence-based chunking with configurable overlap
   - Adds contextual prefixes to chunks (e.g., "Course X Lesson Y content:")

6. **search_tools.py** - Tool-based architecture
   - `CourseSearchTool`: Implements semantic search as an Anthropic tool
   - `ToolManager`: Registers and executes tools, tracks sources
   - Follows abstract Tool interface pattern for extensibility

7. **session_manager.py** - Conversation history
   - Tracks user sessions for multi-turn conversations
   - Configurable history length (MAX_HISTORY=2)

### Data Models (models.py)

- **Course**: Container for course metadata and lessons
- **Lesson**: Individual lesson with number, title, optional link
- **CourseChunk**: Text chunk with course/lesson metadata for vector storage

### Configuration (config.py)

Key settings in `Config` dataclass:
- `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`: Text chunking parameters
- `MAX_RESULTS=5`: Number of search results returned
- `MAX_HISTORY=2`: Conversation history length
- `EMBEDDING_MODEL="all-MiniLM-L6-v2"`: Sentence transformer model
- `CHROMA_PATH="./chroma_db"`: Vector database location

### Document Format

Course documents in `docs/` folder should follow this structure:

```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [lesson title]
Lesson Link: [optional url]
[lesson content...]

Lesson 1: [lesson title]
...
```

Supported formats: `.pdf`, `.docx`, `.txt`

### RAG Query Flow

1. User submits query → FastAPI endpoint
2. RAGSystem creates session if needed
3. AI Generator (Claude) receives query + tool definitions
4. Claude decides whether to use CourseSearchTool
5. If tool used: VectorStore performs semantic search (course name resolution → content search)
6. Tool returns formatted results with sources
7. Claude synthesizes final answer
8. Response + sources returned to user

### Vector Store Architecture

**Two-collection design:**
- **course_catalog**: Course-level metadata for course name resolution via semantic search
  - ID: course title
  - Stores: instructor, course_link, lessons (as JSON)

- **course_content**: Chunked course content
  - ID: `{course_title}_{chunk_index}`
  - Metadata: course_title, lesson_number, chunk_index
  - Used for actual content retrieval

This separation enables fuzzy course name matching while maintaining efficient content filtering.
