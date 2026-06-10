# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run the server:**
```bash
./run.sh
# or directly:
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app serves at http://localhost:8000; API docs at http://localhost:8000/docs.

No tests or linting are currently configured.

## Environment Setup

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`. No other credentials are required — ChromaDB is file-based and persists to `./chroma_db/`.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for course materials. On startup, the backend loads `.txt` files from `../docs/`, chunks them, generates embeddings, and stores them in ChromaDB. User queries flow through Claude with tool use: Claude decides whether to call the `search_course_content` tool, which runs a semantic search, and then generates an answer grounded in the retrieved chunks.

**Request flow:**
```
frontend (HTML/JS) → POST /api/query → RAGSystem.query()
  → AIGenerator.generate_response()  [Claude API with tool definitions]
    → CourseSearchTool.execute()      [if Claude calls the tool]
      → VectorStore.search()          [ChromaDB semantic search]
    → Claude generates final answer
  → response + sources → frontend
```

**Key backend modules:**
- `backend/app.py` — FastAPI routes; mounts static frontend; triggers course loading on startup
- `backend/rag_system.py` — Orchestrator: initializes all components, drives the query pipeline
- `backend/ai_generator.py` — Calls Claude Sonnet with system prompt and tool definitions; handles the tool-use loop
- `backend/search_tools.py` — Defines the `search_course_content` tool schema for Claude and executes it; tracks `last_sources` for citation display
- `backend/vector_store.py` — ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (searchable chunks); includes fuzzy course-name resolution
- `backend/document_processor.py` — Parses course files using a structured header format, chunks text with sentence-aware overlap
- `backend/session_manager.py` — In-memory conversation history keyed by session ID (lost on server restart); default 2-turn window
- `backend/config.py` — Central config (model, chunk size, overlap, max results, ChromaDB path)
- `backend/models.py` — Pydantic models: `Course`, `Lesson`, `CourseChunk`

**Frontend** (`frontend/`) is static HTML/CSS/JS — no build step. It creates a session on load, POSTs queries to `/api/query`, and renders markdown responses via marked.js.

## Course Document Format

Files in `docs/` must follow this structure for `document_processor.py` to parse them:

```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[lesson content]

Lesson 1: [title]
...
```

## Key Configuration (backend/config.py)

| Setting | Default | Notes |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local sentence-transformer |
| `CHUNK_SIZE` | 800 chars | |
| `CHUNK_OVERLAP` | 100 chars | |
| `MAX_RESULTS` | 5 | Search results returned to Claude |
| `MAX_HISTORY` | 2 turns | Conversation window |
| `CHROMA_PATH` | `./chroma_db` | Relative to `backend/` |

All settings can be overridden via environment variables.
