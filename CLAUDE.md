# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Always use `uv` to run the server and manage dependencies. Do not use `pip` directly.

Uses `uv` and Python 3.13+. Requires `ANTHROPIC_API_KEY` in `.env` (see `.env.example`).

```bash
uv sync                     # install dependencies
./run.sh                    # start server on :8000 (UI at /, Swagger at /docs)
# or manually; must run from backend/ because paths are relative to it:
cd backend && uv run uvicorn app:app --reload --port 8000
```

There is no test suite, linter, or build step configured. `main.py` at the root is an unused stub.

## Architecture

A course-transcript RAG chatbot: FastAPI backend serving a static vanilla-JS frontend (`frontend/`, mounted by `app.py`), ChromaDB for vectors, Claude for generation.

**Retrieval is tool-based, not retrieve-then-prompt.** `RAGSystem.query` (`rag_system.py`) does not search up front. It gives Claude a `search_course_content` tool and Claude decides whether to call it. `AIGenerator.generate_response` therefore makes up to three Anthropic calls per question (at most 2 sequential tool rounds):
1. Call with tools. If `stop_reason == "tool_use"`, the tools run locally through `ToolManager` and the results are appended to the message list, then Claude is called again (still with tools) so it can reason on the results and make a second, dependent call (e.g. `get_course_outline` then `search_course_content`).
2. The loop ends when a response has no `tool_use`, after 2 rounds (`AIGenerator.MAX_ROUNDS`), or when a tool raises (returned as an `is_error` tool_result). If it ended on rounds/error, one final call with `tool_choice: none` produces the answer.

New tools go through the `Tool` ABC in `search_tools.py` and `ToolManager.register_tool`, then get registered in `RAGSystem.__init__`.

**Sources reach the UI via side-channel state.** `CourseSearchTool` stores `last_sources` (a de-duplicated list of `{text, url}` dicts; lesson URLs come from the `course_catalog` collection via `VectorStore.get_lesson_link`, since chunk metadata has no links) on the tool instance; `RAGSystem.query` reads and resets it after generation. This is shared mutable state on a singleton, so it is not safe for concurrent requests.

**Vector store** (`vector_store.py`) has two Chroma collections: `course_catalog` (one doc per course, used to fuzzy-resolve a partial `course_name` like "MCP" to the exact title via top-1 semantic match) and `course_content` (lesson chunks, filtered by `course_title` and/or `lesson_number` metadata). Embeddings are computed locally with `all-MiniLM-L6-v2`; only the Claude calls are remote.

**Ingestion** happens at app startup (`startup_event` in `app.py`, reading `../docs`). Course files must follow this format, which `DocumentProcessor` parses: a header of `Course Title:`, `Course Link:`, `Course Instructor:`, then `Lesson N: <title>` sections. Chunking is sentence-based (`CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`). Courses are de-duplicated by title, so **editing an existing doc in `docs/` is not re-ingested**; delete `backend/chroma_db/` (or call `add_course_folder(..., clear_existing=True)`) to rebuild.

**Sessions** (`session_manager.py`) are in-memory only, keyed `session_N`, and lost on restart. The stored history is the raw user question plus the answer (not the wrapped prompt), injected into the system prompt as text, capped at `MAX_HISTORY` exchanges.

Tunables (model, chunk sizes, result count, history length, Chroma path) all live in `backend/config.py`.

## Gotchas

- Chroma is created at `./chroma_db` relative to the working directory, so running from the repo root vs `backend/` yields different databases. Always run from `backend/` (as `run.sh` does).
- Do not pass `temperature` to the Claude API. The configured model rejects it with a 400. Retired model IDs return a 404; both surface to the browser as a generic 500 from `/api/query` with the Anthropic error in `detail`.
