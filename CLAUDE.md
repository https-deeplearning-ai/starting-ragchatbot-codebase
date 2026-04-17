# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

**Quick start (from repo root):**
```bash
./run.sh
```

**Manual start (must run from `backend/` directory):**
```bash
cd backend && uv run uvicorn app:app --reload --port 8000
```

The server runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

**Install dependencies:**
```bash
uv sync
```

> Always use `uv` to run the server and manage packages. Never use `pip` directly.

**Required environment variable** — create a `.env` file in the repo root:
```
ANTHROPIC_API_KEY=your-key-here
```

## Architecture Overview

This is a full-stack RAG (Retrieval-Augmented Generation) chatbot for querying course materials.

**Backend** (`backend/`) is a FastAPI app that must be started from within the `backend/` directory (relative paths like `../docs` and `../frontend` depend on this).

**Data flow for a query:**
1. `app.py` receives POST `/api/query` → calls `RAGSystem.query()`
2. `RAGSystem` (`rag_system.py`) builds a prompt and passes it to `AIGenerator` with the `search_course_content` tool available
3. `AIGenerator` (`ai_generator.py`) calls the Claude API; if Claude decides to search, it invokes the tool
4. `ToolManager` routes tool calls to `CourseSearchTool` (`search_tools.py`), which queries `VectorStore`
5. `VectorStore` (`vector_store.py`) uses ChromaDB with two collections:
   - `course_catalog` — course-level metadata (title, instructor, links, lesson list as JSON)
   - `course_content` — chunked lesson text for semantic search
6. The final Claude response + sources are returned to the frontend

**Document ingestion** (happens at startup from `docs/` folder):
- `DocumentProcessor` (`document_processor.py`) parses `.txt`/`.pdf`/`.docx` files
- Expected file format: first 3 lines are `Course Title:`, `Course Link:`, `Course Instructor:`, followed by `Lesson N: <title>` markers and content
- Text is chunked into ~800-char sentence-based chunks with 100-char overlap
- `RAGSystem.add_course_folder()` skips courses already present in ChromaDB (deduplication by title)

**Session management:** `SessionManager` keeps in-memory conversation history (default: last 2 exchanges = 4 messages). Sessions are identified by a string ID returned to and echoed back by the frontend.

**Frontend** (`frontend/`) is plain HTML/JS/CSS served as static files by FastAPI from the `../frontend` path.

**Configuration** (`backend/config.py`): all tuneable parameters (model, chunk size, ChromaDB path, max results, history length) are in the `Config` dataclass. ChromaDB is stored at `backend/chroma_db/` (relative to where uvicorn runs).

**Tool extension:** To add a new tool, implement the `Tool` ABC in `search_tools.py` and call `tool_manager.register_tool(your_tool)` in `RAGSystem.__init__()`.

## Rules
- Never read or write files outside this project folder without explicit permission
- Always ask before saving anything to memory or external locations
- Never access C:\Users\haddad\.claude\ without explicit permission
- Always use `uv` to add dependencies (e.g., `uv add <package>`); never use `pip` directly