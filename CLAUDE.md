# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Always use `uv` to run Python commands and manage dependencies. Never use `pip` directly.**

```bash
# Install dependencies
uv sync

# Install dev dependencies (includes black)
uv sync --extra dev

# Run the application (starts on http://localhost:8000)
./run.sh
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Run a single Python file
uv run python backend/<file>.py

# Code quality commands
./format.sh   # Format all Python files with black
./check.sh    # Check formatting (exits with error if issues found)
```

**Environment Setup**: Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for querying course materials. The system uses an agentic pattern where Claude decides when to search.

### Query Flow

```
Frontend (script.js)
    → POST /api/query
    → RAGSystem.query()
    → AIGenerator calls Claude with tools
    → Claude invokes search_course_content tool
    → CourseSearchTool.execute()
    → VectorStore.search() (ChromaDB)
    → Results returned to Claude
    → Final response sent to frontend
```

### Backend Components (`backend/`)

| File | Purpose |
|------|---------|
| `app.py` | FastAPI endpoints, serves frontend, loads docs on startup |
| `rag_system.py` | Main orchestrator - coordinates all components |
| `ai_generator.py` | Claude API integration with tool execution loop |
| `search_tools.py` | Tool definitions for Claude (CourseSearchTool) |
| `vector_store.py` | ChromaDB wrapper with two collections |
| `document_processor.py` | Parses course files, chunks text with overlap |
| `session_manager.py` | Conversation history per session |
| `config.py` | Settings dataclass (chunk size, model, etc.) |
| `models.py` | Pydantic models: Course, Lesson, CourseChunk |

### ChromaDB Collections

- **`course_catalog`**: Course metadata for fuzzy name resolution (title → exact match)
- **`course_content`**: Text chunks with embeddings for semantic search

### Document Format

Course files in `/docs` follow this structure:
```
Course Title: [Name]
Course Link: [URL]
Course Instructor: [Name]

Lesson 0: [Title]
Lesson Link: [URL]
[Content...]

Lesson 1: [Title]
[Content...]
```

### Key Configuration (`config.py`)

- `CHUNK_SIZE`: 800 chars, `CHUNK_OVERLAP`: 100 chars
- `MAX_RESULTS`: 5 search results returned
- `MAX_HISTORY`: 2 conversation exchanges kept
- Embedding model: `all-MiniLM-L6-v2`
- LLM: `claude-sonnet-4-20250514`

### Frontend (`frontend/`)

Vanilla HTML/CSS/JS with Marked.js for markdown rendering. Communicates via `/api/query` and `/api/courses` endpoints.
