# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Install dependencies
uv sync

# Start the server (from project root)
cd backend && uv run uvicorn app:app --reload --port 8000

# Or use the shell script
./run.sh
```

Requires Ollama running locally with a model installed (configured in `.env`).
The app is served at http://localhost:8000 with API docs at http://localhost:8000/docs.

## Environment

- Python 3.13+ with `uv` package manager
- **Always use `uv` to run commands and manage dependencies. Never use `pip` directly.**
- `.env` file in project root with `OLLAMA_BASE_URL` and `OLLAMA_MODEL`
- No test suite exists currently

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for course materials. FastAPI backend serves both the API and the frontend static files.

**Query flow:** Frontend → `app.py` (FastAPI) → `rag_system.py` (orchestrator) → searches `vector_store.py` (ChromaDB) → sends query + retrieved chunks to `ai_generator.py` (Ollama LLM) → response back to frontend.

**Key design decisions:**
- Search-first approach: every query searches ChromaDB before calling the LLM (no tool calling — small local models can't handle it reliably)
- Two ChromaDB collections: `course_catalog` (metadata for fuzzy course name matching) and `course_content` (chunked text for semantic search)
- Embeddings via `all-MiniLM-L6-v2` sentence-transformer
- Session history is in-memory only (lost on restart), capped at 2 exchanges per session
- Documents are chunked at 800 chars with 100 char overlap
- Course documents in `docs/` are auto-loaded on server startup

**Backend modules:**
- `app.py` — API endpoints and static file serving
- `rag_system.py` — orchestrates search → LLM → session flow
- `vector_store.py` — ChromaDB wrapper with semantic search and course/lesson filtering
- `ai_generator.py` — Ollama API client
- `document_processor.py` — parses course .txt/.pdf/.docx files into structured chunks
- `search_tools.py` — search tool abstraction with source tracking
- `session_manager.py` — per-session conversation memory
- `models.py` — `Course`, `Lesson`, `CourseChunk` dataclasses
- `config.py` — loads settings from `.env`

**Frontend:** plain HTML/JS/CSS in `frontend/`, uses `marked.js` for markdown rendering. No build step.
