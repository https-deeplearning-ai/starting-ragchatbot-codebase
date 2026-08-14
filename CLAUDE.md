# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A RAG chatbot over course transcripts: FastAPI backend, ChromaDB vector store, Anthropic Claude for generation, static HTML/JS/CSS frontend served by the same process.

**Retrieval is agentic, not fixed-pipeline**: Claude decides per-query (via native tool calling) whether to search course content at all. General-knowledge questions get answered directly on the first Claude call; course-specific ones trigger a `search_course_content` tool call, then a second Claude call to synthesize the final answer. At most one search per query — enforced structurally (only one tool round-trip is coded in `AIGenerator._handle_tool_execution`), not just by prompt instruction.

## Running it

```bash
uv sync                                              # install deps
# create .env at repo root: ANTHROPIC_API_KEY=...
cd backend && uv run uvicorn app:app --reload --port 8000
# or: ./run.sh (Git Bash required on Windows)
```
Web UI at `http://localhost:8000`, API docs at `http://localhost:8000/docs`.

**`main.py` at the repo root is an unused `uv init` stub** ("Hello from starting-codebase!") — it is not the app entrypoint. The real entrypoint is `backend/app.py`, run via Uvicorn.

## Gotchas

- **Startup ingestion is dedup'd by course title.** `app.py`'s startup event loads every file in `docs/` into ChromaDB via `RAGSystem.add_course_folder()`, but skips any course whose title already exists in the `course_catalog` collection. Editing a transcript in `docs/` or changing `CHUNK_SIZE`/`CHUNK_OVERLAP` in `config.py` has **no effect** on an already-running index — the ChromaDB data at `backend/chroma_db` must be cleared and re-ingested to see the change. Use the `/rebuild-index` skill for this.
- **Document format is rigid.** Course files in `docs/` must start with exactly `Course Title:` / `Course Link:` / `Course Instructor:` on the first three lines, followed by `Lesson N: <title>` markers. `document_processor.py` parses this positionally; malformed headers silently fall back to using the filename as the title.
- **Sources are a side-channel, not a return value.** `CourseSearchTool` stashes `"Course - Lesson N"` strings on `self.last_sources` as a side effect of formatting search results; `RAGSystem.query()` pulls them via `ToolManager.get_last_sources()` *after* generation and immediately resets them. If you add a second source-tracking tool, `ToolManager.get_last_sources()` only returns the first tool found with a non-empty `last_sources`.
- **Conversation history is in-memory only** (`SessionManager`), capped at `MAX_HISTORY` (2) exchanges, and not persisted across server restarts.
- No test suite, linter, formatter, or CI exists in this repo currently.
