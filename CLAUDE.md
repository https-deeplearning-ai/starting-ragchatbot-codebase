# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Always use `uv` for Python/dependency commands in this repo — never call `pip` directly.**

**Install dependencies**:
```bash
uv sync
```

**Run the app** (serves both the API and the static frontend on port 8000):
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```
- Web UI: http://localhost:8000
- Swagger/OpenAPI docs: http://localhost:8000/docs

**Environment**: requires a `.env` file in the repo root with `ANTHROPIC_API_KEY=...` (see `.env.example`). Loaded via `python-dotenv` in `backend/config.py`.

There is currently no test suite, linter, or type-checker configured in this repo.

## Architecture

This is a RAG chatbot over course transcripts, but retrieval is **not a fixed pipeline** — it's Claude tool-use. The LLM decides per-query whether to search at all.

### Request flow

`frontend/script.js` → `POST /api/query` (`backend/app.py`) → `RAGSystem.query()` (`backend/rag_system.py`) → `AIGenerator.generate_response()` (`backend/ai_generator.py`), which calls Claude with the `search_course_content` tool attached (`tool_choice: auto`).

- If Claude answers without using the tool, that's returned directly.
- If Claude emits a `tool_use` block, `ToolManager.execute_tool()` (`backend/search_tools.py`) runs `CourseSearchTool.execute()`, results are appended as a `tool_result` message, and a **second** `messages.create()` call (without tools) produces the final synthesized answer. This two-call pattern only happens on the search path.
- The system prompt (in `ai_generator.py`) caps Claude to **one search per query** — it cannot chain searches to refine results.

Sources surfaced in the UI come from `CourseSearchTool.last_sources`, tracked as a side effect of formatting search results, fetched via `ToolManager.get_last_sources()`, and reset after each query — this is stateful and not thread-safe across concurrent requests.

### Storage: two ChromaDB collections

`backend/vector_store.py` maintains:
- `course_catalog` — one entry per course (title, instructor, serialized lesson JSON). Used only to **resolve a fuzzy course name** the user/LLM provides (e.g. "MCP") to an exact title via a semantic query, before filtering `course_content`.
- `course_content` — the actual chunks, with `course_title`/`lesson_number`/`chunk_index` metadata. This is what gets searched for real.

Course title is the unique ID/primary key throughout (catalog doc ID, dedup key on reload). Renaming a course's title line in its source file causes it to be re-ingested as a new course rather than updated.

### Document ingestion

On FastAPI startup, `app.py` loads every file in `../docs` via `RAGSystem.add_course_folder()`, skipping any course whose title already exists in `course_catalog` (no content-hash check — only title match).

`backend/document_processor.py` expects a specific transcript format:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <lesson title>
Lesson Link: <url>
<lesson body text...>

Lesson 1: <next lesson title>
...
```
Lesson bodies are sentence-chunked (`chunk_text`) with overlap, governed by `Config.CHUNK_SIZE`/`CHUNK_OVERLAP` (`backend/config.py`). The first chunk of each lesson is prefixed with lesson context (e.g. `"Lesson N content: ..."`) so the embedding still carries that context even without metadata filtering. If no `Lesson N:` markers are found, the whole file is chunked as one lesson-less block.

### Session / conversation history

`backend/session_manager.py` is a **plain in-process dict** (`session_id -> List[Message]`) — no persistence, no database. History is capped at `Config.MAX_HISTORY` exchanges (currently 2) and formatted as a flat `"User: ...\nAssistant: ..."` string injected into the system prompt, not passed as structured Anthropic message turns. `session_id` is created by `app.py` on first query if the client doesn't send one (sequential counter: `session_1`, `session_2`, ...) and must be echoed back by the client on subsequent requests to maintain context.

### Config

All tunables live in one dataclass, `backend/config.py`: chunk size/overlap, max search results, max history, embedding model (`all-MiniLM-L6-v2`), Claude model (`claude-sonnet-5-5`), and the Chroma persistence path (`./chroma_db`, relative to `backend/`).
