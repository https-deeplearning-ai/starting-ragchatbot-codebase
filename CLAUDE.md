# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) system for answering questions about course materials, using ChromaDB for vector storage, Anthropic's Claude for AI generation (via tool-calling), and a static HTML/JS frontend.

## Commands

Package management is via `uv` (not pip/poetry). Windows users run these from Git Bash.

Always use `uv run` to start the server or execute scripts — never invoke `python`/`python3` directly.

```bash
uv sync                                     # install dependencies
```

Set `ANTHROPIC_API_KEY` in a `.env` file at the repo root (see `.env.example`).

Run the app (starts the backend and serves the frontend from the same FastAPI process):

```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

- Web UI: http://localhost:8000
- API docs: http://localhost:8000/docs

There is no build step in this repo (the frontend is served as static files).

**Code quality / formatting** — black + isort for Python, Prettier for `frontend/*.{html,css,js}`:

```bash
./scripts/format.sh    # auto-format everything in place
./scripts/check.sh     # verify formatting only, writes nothing (exits 1 if unformatted)
./scripts/quality.sh   # full gate: check.sh + pytest
```

Run `./scripts/format.sh` after editing any file, and `./scripts/quality.sh` before committing.
Formatter config: `[tool.black]`/`[tool.isort]` in `pyproject.toml`, `.prettierrc.json` for the
frontend. Prettier is the only npm dependency and is installed automatically on first script run.

Tests live in `backend/tests/` and run via `uv run pytest`. Note that 3 tests in
`test_rag_system_content_queries.py` fail against the committed baseline — these are
pre-existing diagnostic failures, not regressions.

## Architecture

**Request flow:** frontend (`frontend/script.js`) POSTs to `/api/query` → `app.py` → `RAGSystem.query()` (`backend/rag_system.py`) → `AIGenerator.generate_response()` (`backend/ai_generator.py`) calls Claude with the `search_course_content` tool available → Claude decides whether to invoke the tool → if it does, `ToolManager` executes `CourseSearchTool.execute()` against `VectorStore` → tool results are fed back to Claude for a final synthesized answer → sources collected from `ToolManager.get_last_sources()` are returned alongside the answer.

The key design point: retrieval is **agentic, not a fixed pipeline step**. `RAGSystem` doesn't search before calling Claude; it exposes search as a tool (see `search_tools.py`) and Claude's system prompt (`AIGenerator.SYSTEM_PROMPT`) instructs it to search only for course-specific questions, general questions are answered from Claude's own knowledge, and at most one search per query.

**Core components (`backend/`):**
- `app.py` — FastAPI app. Two endpoints: `POST /api/query` (ask a question, returns answer + sources + session_id) and `GET /api/courses` (course analytics). On startup, loads all documents from `../docs` into the vector store (skips courses already present by title). Also mounts `../frontend` as static files at `/`.
- `rag_system.py` — orchestrator (`RAGSystem`) wiring together `DocumentProcessor`, `VectorStore`, `AIGenerator`, `SessionManager`, and `ToolManager`. Entry points: `add_course_document`/`add_course_folder` (ingestion) and `query` (answering).
- `document_processor.py` — parses course documents into a `Course` + `List[CourseChunk]`. Expects a specific text format (see below), splits lesson bodies into overlapping sentence-based chunks (`CHUNK_SIZE`/`CHUNK_OVERLAP` in `config.py`), and prefixes the first chunk of each lesson with course/lesson context so embeddings retain that context even out of order.
- `vector_store.py` — wraps ChromaDB with **two collections**: `course_catalog` (one doc per course, keyed by title, used only to resolve a fuzzy `course_name` filter to an exact title via semantic search) and `course_content` (the actual chunked material, filterable by `course_title`/`lesson_number`). `VectorStore.search()` is the unified entry point: resolves course name → builds a Chroma `where` filter → queries `course_content`.
- `search_tools.py` — `Tool`/`ToolManager` abstraction for exposing search to Claude as an Anthropic tool-use tool. `CourseSearchTool` formats results with `[Course - Lesson N]` headers and tracks `last_sources` for the UI; `ToolManager.reset_sources()` is called by `RAGSystem` after each query so sources don't leak across requests.
- `ai_generator.py` — thin wrapper around the Anthropic Messages API. Single-round tool-use loop: initial call with `tools` + `tool_choice: auto` → if `stop_reason == "tool_use"`, execute the tool call(s) via `tool_manager` and make one follow-up call *without* tools to get the final text.
- `session_manager.py` — in-memory (non-persistent) per-session conversation history, truncated to `MAX_HISTORY` exchanges.
- `models.py` — Pydantic models: `Course`, `Lesson`, `CourseChunk`. `Course.title` is used as the unique ID throughout (Chroma document ID in `course_catalog`, filter key in `course_content`).
- `config.py` — central `Config` dataclass (loaded from `.env` via `python-dotenv`): model name, embedding model, chunk size/overlap, max search results, max history, Chroma path.

**RAG pipeline in detail:**

*Ingestion (on startup, `app.py` → `RAGSystem.add_course_folder` → `add_course_document`):*
1. `DocumentProcessor.process_course_document` parses the file into a `Course` (title/link/instructor) and per-lesson text bodies (see format below).
2. Each lesson body is split into overlapping chunks by `chunk_text`: sentence-boundary splitting, packed up to `CHUNK_SIZE` (800 chars), with the tail `CHUNK_OVERLAP` (100 chars) of sentences repeated at the start of the next chunk so context isn't lost at chunk edges.
3. The first chunk of each lesson is prefixed with `"Course {title} Lesson {n} content: ..."` so that chunk retains course/lesson identity even when embedded and retrieved in isolation.
4. `VectorStore.add_course_metadata` embeds one document per course (title only) into the `course_catalog` collection, storing instructor/link/lesson list as metadata — this collection exists purely to resolve fuzzy course-name lookups later, not for content retrieval.
5. `VectorStore.add_course_content` embeds every chunk into the `course_content` collection, with `course_title`/`lesson_number`/`chunk_index` as metadata for filtering.
6. Both collections use the same embedding function: `sentence-transformers` model `all-MiniLM-L6-v2` (`EMBEDDING_MODEL` in `config.py`), run locally (no API calls for embeddings).
7. Ingestion is idempotent by course title: `app.py` skips any course whose title is already in `course_catalog`.

*Retrieval (per query, `RAGSystem.query` → `AIGenerator.generate_response`):*
1. Claude receives the user question plus recent session history and the `search_course_content` tool definition; it decides whether the question needs course-specific lookup at all (general knowledge questions get answered without searching).
2. If Claude calls the tool, `CourseSearchTool.execute` → `VectorStore.search`:
   - If a `course_name` was passed, it's first resolved via a semantic query against `course_catalog` (top-1 match) to get the exact stored title — so the tool tolerates fuzzy/partial course names.
   - A Chroma `where` filter is built from the resolved `course_title` and/or `lesson_number`.
   - `course_content` is queried with the filter, returning up to `MAX_RESULTS` (5) chunks by embedding similarity.
3. Results are formatted as `[Course Title - Lesson N]` headers followed by chunk text, and `CourseSearchTool` records them in `last_sources` (with lesson links resolved via `VectorStore.get_lesson_link`) for the frontend to display.
4. Formatted results are appended to the conversation and sent back to Claude in a second API call *without* tools, so Claude cannot loop/chain further searches — at most one search round-trip per query.
5. Claude synthesizes the final answer from the retrieved chunks; `RAGSystem` returns `(answer, sources)` and calls `ToolManager.reset_sources()` so sources don't leak into the next query.

**Expected course document format** (see `docs/*.txt`), parsed line-by-line by `DocumentProcessor.process_course_document`:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <lesson title>
Lesson Link: <url>
<lesson body text...>

Lesson 1: <lesson title>
...
```

**Frontend (`frontend/`):** plain HTML/CSS/vanilla JS, no build step or framework. `script.js` calls `/api/query` and `/api/courses` directly and renders responses/sources into the DOM.
