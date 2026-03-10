# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack RAG (Retrieval-Augmented Generation) chatbot that enables semantic search and AI-powered Q&A over course documents. Uses ChromaDB for vector storage, sentence-transformers for embeddings, and Anthropic Claude for response generation.

## Setup

Requires Python 3.13+, `uv` package manager, and an Anthropic API key.

```bash
uv sync
cp .env.example .env   # then add your ANTHROPIC_API_KEY
```

## Running

```bash
# Quick start
./run.sh

# Manual (from repo root)
cd backend && uv run uvicorn app:app --reload --port 8000
```

Access the app at `http://localhost:8000`, API docs at `http://localhost:8000/docs`.

On startup, `app.py` auto-loads all `.txt` files from `../docs/` into ChromaDB.

## Architecture

**Request flow:**

```
Frontend (frontend/) → POST /api/query → RAGSystem.query()
  → ai_generator (Claude with tools) → search_tools (if needed)
  → vector_store (ChromaDB semantic search) → response to frontend
```

**Backend modules** (`backend/`):

| File | Role |
|------|------|
| `app.py` | FastAPI entry point; mounts frontend as static files; startup doc loading |
| `rag_system.py` | Orchestrator — wires all components together for a query |
| `document_processor.py` | Parses structured `.txt` course files into chunks |
| `vector_store.py` | ChromaDB wrapper; two collections: `course_catalog` and `course_content` |
| `ai_generator.py` | Anthropic Claude wrapper with tool-calling support |
| `search_tools.py` | Tool definitions and execution (`search_course_content`) |
| `session_manager.py` | In-memory conversation history (max 2 exchanges) |
| `models.py` | Pydantic models: `Course`, `Lesson`, `CourseChunk` |
| `config.py` | All configuration via `Config` dataclass (model, chunk size, paths, etc.) |

**Frontend** (`frontend/`): Vanilla HTML/CSS/JS SPA; uses `marked.js` from CDN for markdown rendering; chat UI with collapsible course stats sidebar.

**Course document format** (files in `docs/`):
```
Course Title: [name]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[content...]
```

## Key Configuration (`backend/config.py`)

- `ANTHROPIC_MODEL`: `claude-sonnet-4-20250514`
- `EMBEDDING_MODEL`: `all-MiniLM-L6-v2` (384-dim, via sentence-transformers)
- `CHUNK_SIZE` / `CHUNK_OVERLAP`: 800 / 100 characters
- `MAX_RESULTS`: 5 search results returned
- `MAX_HISTORY`: 2 conversation exchanges retained
- `CHROMA_PATH`: `./chroma_db` (persistent, relative to `backend/`)

## Dependencies

Managed via `uv`. Key packages: `fastapi`, `uvicorn`, `chromadb`, `anthropic`, `sentence-transformers`, `python-dotenv`. Lock file is `uv.lock`.

## Notes

- No test framework or linting tools are configured.
- ChromaDB persists to `backend/chroma_db/` — delete this directory to reset the vector store.
- The backend serves the frontend as static files; no separate frontend build step.
- Windows users must use Git Bash (not PowerShell/CMD) to run `run.sh`.
