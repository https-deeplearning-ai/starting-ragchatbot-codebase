# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Quick start (from project root)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

App runs at http://localhost:8000. Requires `ANTHROPIC_API_KEY` in a `.env` file at the project root.

Install dependencies: `uv sync`

**Always use `uv` for all dependency management — never `pip` directly.**
- Add a package: `uv add <package>`
- Remove a package: `uv remove <package>`

## Architecture

This is a full-stack RAG chatbot. The **backend** is a FastAPI app served from the `backend/` directory; it also serves the **frontend** (`frontend/`) as static files mounted at `/`. There is no build step for the frontend.

### Query pipeline (the core flow)

1. `app.py` — receives `POST /api/query`, creates a session if needed, delegates to `RAGSystem`
2. `rag_system.py` — orchestrates the pipeline: fetches conversation history, calls `AIGenerator`
3. `ai_generator.py` — makes the first Claude API call with `tool_choice: auto` and the search tool definition. If Claude invokes the tool, `_handle_tool_execution()` runs it and makes a second Claude call (without tools) to produce the final answer
4. `search_tools.py` — `CourseSearchTool` wraps `VectorStore.search()` and formats results for Claude; `ToolManager` registers tools and exposes them as Anthropic tool definitions
5. `vector_store.py` — two ChromaDB collections: `course_catalog` (one doc per course, for fuzzy name resolution) and `course_content` (chunked lesson text, for semantic search). Embeddings use `all-MiniLM-L6-v2`
6. `session_manager.py` — in-memory session store; keeps last 2 exchanges (configurable via `MAX_HISTORY`) formatted as a string injected into the system prompt

### Document ingestion

`document_processor.py` parses `.txt`/`.pdf`/`.docx` files from `docs/` at startup. Expected file format:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>
Lesson 0: <lesson title>
Lesson Link: <url>
<lesson content...>
Lesson 1: <lesson title>
...
```

Chunks are sentence-aware with configurable size (800 chars) and overlap (100 chars).

### Configuration

All tunable parameters live in `backend/config.py` (`Config` dataclass):
- `ANTHROPIC_MODEL` — Claude model to use
- `EMBEDDING_MODEL` — sentence-transformers model
- `CHUNK_SIZE`, `CHUNK_OVERLAP`, `MAX_RESULTS`, `MAX_HISTORY`
- `CHROMA_PATH` — where ChromaDB persists data (`./chroma_db` relative to `backend/`)

### Key design decisions
- The server must be started from the `backend/` directory (paths like `../docs` and `../frontend` are relative to that working directory)
- Course deduplication is by title — re-ingesting the same course title is a no-op
- Tool sources (`last_sources`) are stored on the tool instance and reset after each query cycle
- The second Claude call omits tools to prevent recursive tool use
