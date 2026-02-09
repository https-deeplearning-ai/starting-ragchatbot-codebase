# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Start dev server (from repo root)
cd backend && uv run uvicorn app:app --reload --port 8000

# Or use the startup script
./run.sh
```

Web UI: <http://localhost:8000> | API docs: <http://localhost:8000/docs>

Always use `uv run` to execute Python commands (never `pip` or bare `python`). For example: `uv run python some_script.py`, `uv run pytest`, `uv add <package>`.

No tests or linting are configured.

## Architecture

RAG chatbot that answers questions about course materials using ChromaDB vector search and Claude AI with tool-calling.

**Query flow:** Frontend `POST /api/query` → `app.py` → `RAGSystem.query()` → `AIGenerator` calls Claude API with `search_course_content` tool → Claude may invoke tool → `CourseSearchTool` → `VectorStore.search()` (ChromaDB) → results fed back to Claude for final answer → response with sources returned to frontend.

**Backend modules (all in `backend/`):**

- `app.py` — FastAPI entry point. Serves frontend static files from `../frontend`. On startup, auto-loads course docs from `../docs`. Two API endpoints: `POST /api/query`, `GET /api/courses`.
- `rag_system.py` — Orchestrator that wires together all components. The `query()` method is the main pipeline entry.
- `ai_generator.py` — Claude API wrapper. Sends user query with tool definitions, handles tool_use loop (executes tool, sends results back to Claude for final answer). System prompt is a static class variable.
- `search_tools.py` — `Tool` ABC + `CourseSearchTool` implementation + `ToolManager` registry. Tool tracks `last_sources` for the response; sources are reset after each query.
- `vector_store.py` — ChromaDB wrapper with two collections: `course_catalog` (course metadata, used for fuzzy course name resolution) and `course_content` (text chunks, used for semantic search). Uses `SentenceTransformerEmbeddingFunction`.
- `document_processor.py` — Reads `.txt/.pdf/.docx` files, extracts course/lesson metadata via regex, chunks text with sentence-boundary splitting.
- `session_manager.py` — In-memory conversation history per session. History is injected into the system prompt as plain text, not as message array.
- `models.py` — Pydantic models: `Course`, `Lesson`, `CourseChunk`.
- `config.py` — Reads `.env`, exposes constants (model names, chunk size/overlap, max results).

**Frontend (`frontend/`):** Vanilla HTML/CSS/JS single-page app. Uses `marked.js` for markdown rendering. Manages `currentSessionId` for multi-turn conversations.

**Key design details:**

- Course title is used as the unique identifier (ChromaDB document ID).
- `_resolve_course_name()` does a vector similarity search on `course_catalog` to fuzzy-match user-provided course names to actual titles.
- The AI generator makes two Claude API calls when tools are used: first with tools enabled, second without tools (using tool results as context).
- Conversation history is capped at `MAX_HISTORY * 2` messages (default: 4) and formatted as `"User: ...\nAssistant: ..."` strings appended to the system prompt.
