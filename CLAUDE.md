# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
uv sync
```

**Run the server** (from the `backend/` directory):
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The web UI is at `http://localhost:8000` and the auto-generated API docs are at `http://localhost:8000/docs`.

**Environment setup:** Copy `.env` and set `ANTHROPIC_API_KEY`.

There are no tests in this codebase.

## Architecture

This is a full-stack RAG chatbot. The backend is a FastAPI app (`backend/app.py`) that serves both the REST API and the static frontend (`frontend/`). All backend modules run from within the `backend/` directory, so relative imports and paths (e.g. `../docs`, `./chroma_db`) are relative to that directory.

### Request flow

1. The browser (`frontend/script.js`) POSTs a query to `POST /api/query`.
2. `app.py` delegates to `RAGSystem.query()` (`rag_system.py`).
3. `RAGSystem` calls `AIGenerator.generate_response()` (`ai_generator.py`), passing the Claude API client, conversation history (from `SessionManager`), and the registered `search_course_content` tool definition.
4. If Claude decides to search, it calls the tool; `AIGenerator._handle_tool_execution()` routes this to `ToolManager.execute_tool()` → `CourseSearchTool.execute()` (`search_tools.py`), which queries `VectorStore` (`vector_store.py`).
5. Search results are injected back into the Claude conversation as a `tool_result` message, and Claude generates the final answer.
6. Sources collected by `CourseSearchTool` are returned to the browser alongside the answer.

### Key components

- **`RAGSystem`** (`rag_system.py`) — top-level orchestrator; the only component that coordinates all others.
- **`VectorStore`** (`vector_store.py`) — wraps ChromaDB with two collections: `course_catalog` (course titles/metadata, used for fuzzy course-name resolution) and `course_content` (chunked text, used for semantic search). Embeddings are generated locally via `sentence-transformers` (`all-MiniLM-L6-v2`). The ChromaDB store is persisted at `backend/chroma_db/`.
- **`DocumentProcessor`** (`document_processor.py`) — parses `.txt`/`.pdf`/`.docx` files from `docs/` into `Course` + `CourseChunk` objects. Expects a specific header format (see below) but falls back to flat chunking if no `Lesson N:` markers are found.
- **`AIGenerator`** (`ai_generator.py`) — thin wrapper around `anthropic.Anthropic`. Uses `tool_choice: auto` and handles one round of tool use (search → final answer). Model and token limits are configured here.
- **`ToolManager` / `CourseSearchTool`** (`search_tools.py`) — extensible tool registry. Adding a new tool means subclassing `Tool` and calling `tool_manager.register_tool()`.
- **`SessionManager`** (`session_manager.py`) — in-memory conversation history, keyed by `session_id`. History is serialized as a plain string and injected into the system prompt.

### Document format

Documents in `docs/` must follow this structure for full metadata extraction:

```
Course Title: <title>          ← used as the unique ID in ChromaDB
Course Link: <url>             ← optional
Course Instructor: <name>      ← optional

Lesson 0: <lesson title>
Lesson Link: <url>             ← optional, must immediately follow lesson header
<lesson content>

Lesson 1: <next lesson title>
...
```

If no `Lesson N:` markers are present, the entire file body is chunked as a single flat document.

### Adding a new document source

1. Drop `.txt`, `.pdf`, or `.docx` files into `docs/`.
2. Delete `backend/chroma_db/` to clear stale embeddings.
3. Restart the server — `startup_event()` in `app.py` re-indexes everything.

To clear and re-index programmatically, call `rag_system.add_course_folder(path, clear_existing=True)`.

### Configuration

All tuneable parameters are in `backend/config.py` via the `Config` dataclass: chunk size/overlap, max search results, conversation history length, ChromaDB path, and the Anthropic model name.
