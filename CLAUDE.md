# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Use `uv` to manage all dependencies and run all Python. Never call `pip` or bare `python` directly. Dependencies live in `pyproject.toml` + `uv.lock`; change them only through uv so the lockfile stays in sync.

```bash
uv sync                      # install dependencies (Python >=3.13, see .python-version)
./run.sh                     # start the server: cd backend && uv run uvicorn app:app --reload --port 8000
uv add <package>             # add a dependency (updates pyproject.toml + uv.lock)
uv remove <package>          # remove a dependency
uv add <package>==<version>  # upgrade/pin a version; or `uv lock --upgrade-package <package>` then `uv sync`
uv run <command>             # run any Python tool/script inside the project environment
```

- App: http://localhost:8000 · API docs: http://localhost:8000/docs
- Requires `ANTHROPIC_API_KEY` in `.env` at the repo root (copy `.env.example`). `.env` is read only at startup, so restart the server after changing it; `--reload` only watches `backend/`.
- Tests: `uv run pytest` (config in `pyproject.toml`, tests in `backend/tests/`, Claude and ChromaDB mocked). API tests use `create_test_app()` in `backend/tests/conftest.py`, a copy of `app.py`'s endpoints (app.py builds a real RAGSystem on import); keep it in sync when routes change. No linter or formatter.
- Quick API check without the UI:
  `curl -s -X POST localhost:8000/api/query -H 'Content-Type: application/json' -d '{"query":"What is the MCP course about?"}'`

## Architecture

A RAG chatbot over course transcripts. FastAPI (`backend/app.py`) serves both the API (`/api/query`, `/api/courses`) and the static frontend (`frontend/`, plain HTML/JS, mounted at `/`).

**Query path:** `app.py` → `RAGSystem.query()` (`rag_system.py`) → `AIGenerator.generate_response()` (`ai_generator.py`). Retrieval is **tool-based**, not pre-fetched: Claude is offered one tool, `search_course_content` (`search_tools.py`), and decides whether to call it. If it does, `_handle_tool_execution` runs the tool and makes a **second Claude call with no tools**, so at most one search per query. General questions get one call and no search.

**Search (`vector_store.py`):** ChromaDB with two collections:
- `course_catalog`: one doc per course (title is the ID). Used to resolve a fuzzy `course_name` ("MCP") to an exact title by semantic search.
- `course_content`: text chunks with `course_title` / `lesson_number` metadata, filtered by the resolved title and lesson.
Embeddings are `all-MiniLM-L6-v2` via sentence-transformers.

**Sources side channel:** search sources are not returned through the Claude response. `CourseSearchTool` stores them in `last_sources`; `RAGSystem.query()` reads them via `ToolManager.get_last_sources()` and then resets them. That state lives on a single shared tool instance, so concurrent requests can mix sources. Keep the read-then-reset order if you touch this.

**Ingestion:** on startup, `app.py` loads `../docs` via `RAGSystem.add_course_folder()`. Courses already in `backend/chroma_db/` (matched by title) are skipped, so **edited docs are not re-indexed** unless you delete `backend/chroma_db/` or pass `clear_existing=True`. `document_processor.py` expects this file format:
```
Course Title: …
Course Link: …
Course Instructor: …
Lesson N: <title>
Lesson Link: …            (optional)
<lesson text>
```
Chunks are sentence-based (`CHUNK_SIZE` 800 chars, `CHUNK_OVERLAP` 100), set in `config.py`.

**Sessions:** `session_manager.py` keeps history in memory only (lost on restart), capped at `MAX_HISTORY` exchanges, and injects it as plain text into the system prompt rather than as API messages.

## Gotchas

- **Working directory matters:** `CHROMA_PATH="./chroma_db"`, `../docs`, and `../frontend` are relative, so the server must run from `backend/` (as `run.sh` does).
- **Claude API constraints:** the pinned SDK is `anthropic==0.58.2`, which predates params like `output_config`. Current models reject `temperature`, and responses can begin with a thinking block, so read text via `AIGenerator._text_of()` rather than `content[0].text`. Thinking counts toward `max_tokens`.
- `app.py` defines `DevStaticFiles` (no-cache headers) but mounts the plain `StaticFiles`; `main.py` is an unused placeholder.
- API errors surface as HTTP 500 with the exception text in `detail`; the frontend shows only "Query failed".
