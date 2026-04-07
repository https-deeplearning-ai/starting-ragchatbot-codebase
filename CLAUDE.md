# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Start the development server (from repo root)
cd backend && uv run uvicorn app:app --reload --port 8000
# or use the helper script:
bash run.sh

# App available at http://localhost:8000
# OpenAPI docs at http://localhost:8000/docs
```

There are no test or lint commands configured in this project.

## Architecture

This is a **RAG (Retrieval-Augmented Generation) chatbot** that answers questions about course content using Claude's tool-calling API + ChromaDB semantic search.

### Stack

- **Backend**: FastAPI (Python 3.13), managed with `uv`
- **AI**: Anthropic Claude API (`claude-sonnet-4-20250514`) with tool calling
- **Vector DB**: ChromaDB (persistent, stored at `backend/chroma_db/`)
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`)
- **Frontend**: Vanilla HTML/CSS/JS served statically by FastAPI

### Key Data Flows

**Document ingestion** (runs automatically on startup via `app.py`):
```
docs/*.txt → DocumentProcessor → CourseChunk objects → VectorStore (ChromaDB)
```
Course docs follow a specific format: `Course Title:`, `Course Link:`, `Course Instructor:`, then `Lesson N:` sections.

**Query flow**:
```
POST /api/query → RAGSystem.query() → AIGenerator.generate_response()
  → Claude calls `search_course_content` tool (in search_tools.py)
  → VectorStore.search() (semantic search, optional course/lesson filters)
  → Claude synthesizes answer → response + sources back to frontend
```

Claude decides autonomously when to invoke the search tool vs. answer from general knowledge — this is not prompt-injected RAG, it uses Claude's native tool-calling agentic loop.

### Module Responsibilities

| File | Responsibility |
|------|---------------|
| `backend/app.py` | FastAPI routes, startup document loading |
| `backend/rag_system.py` | Orchestrates query pipeline; coordinates all other modules |
| `backend/ai_generator.py` | All Anthropic API calls; handles tool execution loop |
| `backend/vector_store.py` | ChromaDB management; two collections: `course_catalog` and `course_content` |
| `backend/document_processor.py` | Parses `.txt` course files into `Course` + `CourseChunk` objects |
| `backend/search_tools.py` | Tool schema for Claude + search execution; tracks sources for UI |
| `backend/session_manager.py` | In-memory conversation history per session |
| `backend/models.py` | Pydantic models: `Lesson`, `Course`, `CourseChunk` |
| `backend/config.py` | Central config loaded from `.env` (chunk size, model, max results, etc.) |

### Configuration

All tunable parameters live in `backend/config.py` and are sourced from `.env`:

- `ANTHROPIC_MODEL` — Claude model ID
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — text chunking (default 800 / 100 chars)
- `MAX_RESULTS` — semantic search results returned per tool call (default 5)
- `MAX_HISTORY` — conversation turns kept in session (default 2)
- `CHROMA_PATH` — path to ChromaDB persistence directory

Copy `.env.example` to `.env` and add your `ANTHROPIC_API_KEY` to run the app.
