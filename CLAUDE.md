# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Python 3.13, dependencies managed with `uv`. There is no test suite, linter, or build step.

```bash
uv sync                      # install dependencies into .venv
./run.sh                     # start the app (cd backend && uv run uvicorn app:app --reload --port 8000)
```

- App: http://localhost:8000 — interactive API docs: http://localhost:8000/docs
- Requires `ANTHROPIC_API_KEY` in a root `.env` (template: `.env.example`, which is tracked by git — keep real keys out of it).
- The server **must be started from `backend/`**: modules use flat imports (`from config import config`) and paths are relative to that directory (`../docs`, `../frontend`, `./chroma_db`).
- Quick API check: `curl -X POST localhost:8000/api/query -H 'Content-Type: application/json' -d '{"query":"..."}'`

## Git workflow

Changes reach `main` only through a pull request. Never merge locally into `main` or push `main` directly.

1. Create a branch from an up-to-date `main` and commit there.
2. Push the branch to `origin`.
3. Open a PR (`gh pr create`).
4. Merge the PR on GitHub only after the user approves.

## Architecture

A course-materials RAG chatbot. One FastAPI process (`backend/app.py`) serves both the JSON API (`POST /api/query`, `GET /api/courses`) and the static frontend (`frontend/` mounted at `/`). The frontend is plain HTML/CSS/JS with no build step and calls the API via the relative base `/api`.

### Query flow (tool-based RAG, not retrieve-then-generate)

`RAGSystem` (`backend/rag_system.py`) wires everything together. Retrieval is **driven by Claude through tool use**, not done up front:

1. `RAGSystem.query()` pulls session history from `SessionManager` and calls `AIGenerator.generate_response()` with the tool definitions from `ToolManager`.
2. Claude decides whether to call `search_course_content` (`CourseSearchTool` in `search_tools.py`). The system prompt limits it to one search per query and tells it to answer general-knowledge questions without searching.
3. If Claude requests a tool, `AIGenerator._handle_tool_execution()` runs it and makes a **second** API call **without tools** to produce the final answer. Only one round of tool use is supported.
4. Sources shown in the UI travel out-of-band: `CourseSearchTool` stores them in `last_sources`, `RAGSystem` reads them via `ToolManager.get_last_sources()` and then resets them. One source string is emitted per retrieved chunk, so duplicates are possible.

Conversation history is in-memory only (lost on restart), capped by `MAX_HISTORY`, and injected into the **system prompt** as text rather than as prior messages.

### Vector store (`backend/vector_store.py`)

ChromaDB persisted at `backend/chroma_db/`, embeddings from sentence-transformers `all-MiniLM-L6-v2`. Two collections:

- `course_catalog` — one entry per course (title, instructor, links); the **course title is the document ID**. Used to fuzzy-resolve a partial `course_name` from Claude to an exact title via semantic search.
- `course_content` — text chunks with `course_title` / `lesson_number` metadata, filtered with Chroma `where` clauses.

### Ingestion (`backend/document_processor.py`)

On startup, `app.py` loads every `.txt/.pdf/.docx` in `docs/` (only plain-text reading is actually implemented). Courses whose title already exists in the store are **skipped**, so editing an existing course file has no effect until `backend/chroma_db/` is deleted (or `add_course_folder(..., clear_existing=True)` is used).

Expected document format:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <lesson title>
Lesson Link: <url>
<lesson content...>
```

Content is split into sentence-based chunks (`CHUNK_SIZE`/`CHUNK_OVERLAP` characters, set in `backend/config.py`) and tagged with course and lesson metadata.

### Configuration

All tunables (Claude model, embedding model, chunk sizes, `MAX_RESULTS`, `MAX_HISTORY`, Chroma path) live in the `Config` dataclass in `backend/config.py`. `AIGenerator` sends `max_tokens=800`; the current model rejects `temperature`, so don't add it back.

`main.py` at the repo root is an unused placeholder.
