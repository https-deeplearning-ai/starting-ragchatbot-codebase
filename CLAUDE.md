# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important: Package Management

Always use `uv` to manage packages and run Python files. Never use `pip` or bare `python` directly.

## Build & Run Commands

```bash
# Install dependencies
uv sync

# Start the server (from project root)
./run.sh
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Access points
# Web UI: http://localhost:8000
# API docs: http://localhost:8000/docs
```

There are no tests, linters, or CI configured for this project.

## Environment

- Python 3.13 (managed by uv)
- Requires `.env` in project root with `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_BASE_URL` for proxy setups)

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for querying course materials. It has a FastAPI backend, a vanilla JS frontend, and uses ChromaDB for vector storage.

### Query Flow

Frontend (`script.js`) POSTs to `/api/query` → `app.py` routes to `RAGSystem.query()` → `AIGenerator` calls Claude with tool definitions → Claude may invoke `search_course_content` tool → `CourseSearchTool` executes against `VectorStore` (ChromaDB) → results returned to Claude for final answer → response with sources sent back to frontend.

Claude's tool calling uses a two-step API pattern: first call with tools enabled, then if `stop_reason == "tool_use"`, execute the tool and make a second call with results (without tools) for the final answer. This is in `ai_generator.py:_handle_tool_execution()`.

### Document Ingestion Flow

On startup, `app.py` loads all `.txt/.pdf/.docx` files from `docs/` → `DocumentProcessor` parses a specific header format (Course Title/Link/Instructor, then `Lesson N:` markers) → text is chunked by sentences (800 chars, 100 overlap) → chunks and course metadata stored in two separate ChromaDB collections (`course_content` for chunks, `course_catalog` for metadata).

### Key Design Decisions

- **Two ChromaDB collections**: `course_catalog` stores course-level metadata (used for fuzzy course name resolution via semantic search); `course_content` stores text chunks (used for actual content retrieval).
- **Course name resolution**: When a query filters by course name, `VectorStore._resolve_course_name()` does a semantic search against the catalog to fuzzy-match partial names before filtering content.
- **Tool-based search**: Rather than always searching, Claude decides whether to search via Anthropic's tool calling API. The `ToolManager` / `Tool` abstraction in `search_tools.py` supports registering additional tools.
- **Session management**: In-memory only (lost on restart). History is formatted as a string and appended to the system prompt, not passed as message history.
- **Static frontend**: Served directly by FastAPI's StaticFiles mount at `/`. No build step.

### Re-chunking Documents

To force re-processing of all documents, delete `backend/chroma_db/` and restart the server. The startup event will reprocess everything from `docs/`. Alternatively, pass `clear_existing=True` to `add_course_folder()`.

### Configuration

All tunable parameters are in `config.py` as a dataclass: `CHUNK_SIZE`, `CHUNK_OVERLAP`, `MAX_RESULTS`, `MAX_HISTORY`, `CHROMA_PATH`, `ANTHROPIC_MODEL`, `EMBEDDING_MODEL`. Changes to chunking parameters require re-chunking to take effect.
