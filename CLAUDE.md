# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependencies are managed with `uv` (Python 3.13). Requires `ANTHROPIC_API_KEY` in a root `.env` (see `.env.example`).

```bash
uv sync                                               # install dependencies
./run.sh                                              # start the server on :8000
cd backend && uv run uvicorn app:app --reload --port 8000   # same, manually
```

- Web UI: http://localhost:8000 · API docs: http://localhost:8000/docs
- There is no test suite, linter, or build step configured.
- The server must be started from `backend/`: paths like `../docs`, `../frontend`, and `./chroma_db` are relative to it.
- Root `main.py` is an unused placeholder; the entry point is `backend/app.py`.

## Architecture

A RAG chatbot over course transcripts: FastAPI backend, ChromaDB vector store, Claude via the Anthropic SDK, and a vanilla HTML/JS frontend served as static files by the same FastAPI app.

**Ingestion (on startup).** `app.py` calls `RAGSystem.add_course_folder("../docs")`. `DocumentProcessor` parses each file, expecting a header of `Course Title:` / `Course Link:` / `Course Instructor:` followed by `Lesson N: <title>` markers (each optionally followed by `Lesson Link:`). Text is split into sentence-based chunks (`CHUNK_SIZE`/`CHUNK_OVERLAP` in `config.py`) tagged with course title and lesson number. Courses whose title already exists in ChromaDB are skipped, so the persisted DB in `backend/chroma_db/` survives restarts — delete it (or use `clear_existing=True`) to force re-ingestion after changing chunking or document format. Only `.txt` really works despite `.pdf`/`.docx` being accepted.

**Two ChromaDB collections** (`vector_store.py`), both embedded with `all-MiniLM-L6-v2`:
- `course_catalog` — one entry per course (title is the ID; lessons stored as JSON in metadata). Used to fuzzy-resolve a course name via vector search.
- `course_content` — the chunks, filterable by `course_title` and `lesson_number`.

**Query flow (tool-based RAG, not retrieve-then-generate).** `POST /api/query` → `RAGSystem.query()` → `AIGenerator.generate_response()`. Claude is given a single tool, `search_course_content` (`search_tools.py`), and decides whether to call it. If it does, `CourseSearchTool` → `VectorStore.search()` resolves the course name against `course_catalog`, then queries `course_content` with metadata filters. Results go back to Claude in a second API call **without tools**, so at most one round of searching happens per query.

**Sources are passed via side-channel state**: `CourseSearchTool._format_results` stores `last_sources` on the tool instance; `RAGSystem.query()` reads them via `ToolManager.get_last_sources()` and then resets them. New tools that should surface sources must expose a `last_sources` attribute. This shared state is not safe under concurrent requests.

**Sessions** (`session_manager.py`) are in-memory only (lost on restart) and keep the last `MAX_HISTORY` exchanges. History is injected as plain text into the system prompt, not as message turns. The frontend gets its `session_id` from the first response and sends it back on later queries.

**Adding a tool**: subclass `Tool` in `search_tools.py` (implement `get_tool_definition()` returning an Anthropic tool schema and `execute(**kwargs)`), then register it with `tool_manager.register_tool()` in `RAGSystem.__init__`.

## Claude API notes

- Model is set in `config.py` (`claude-sonnet-5-5`); SDK is `anthropic` 2.x, which sends API version `2026-10-21`.
- Do not add `temperature`/`top_p`/`top_k` — they are rejected on this API version.
- Thinking is on by default, so responses can contain `thinking` blocks before text; always extract text via `AIGenerator._extract_text()` rather than `response.content[0].text`. Thinking tokens count toward `max_tokens`.
- Effort is set via `output_config={"effort": "low"}` in `AIGenerator.base_params`.
- `backend/ai_generator.py` uses CRLF line endings; preserve them when editing.
