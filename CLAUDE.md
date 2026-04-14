# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# From repo root — starts FastAPI on http://localhost:8000
./run.sh

# Or manually
cd backend && uv run uvicorn app:app --reload --port 8000
```

Requires a `.env` file at the repo root (copy from `.env.example`):
```
ANTHROPIC_API_KEY=your-key-here
```

The frontend is served as static files by FastAPI — no separate frontend server needed.

## Package Management

Uses `uv`. To add/sync dependencies:
```bash
uv sync
uv add <package>
```

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot with a **tool-use agentic loop** at its core.

### Request lifecycle

1. Frontend POSTs `{query, session_id}` to `POST /api/query`
2. `app.py` delegates to `RAGSystem.query()`
3. `RAGSystem` sends the query to Claude via `AIGenerator` with the `search_course_content` tool available
4. Claude decides whether to invoke the tool; if so, `ToolManager` dispatches to `CourseSearchTool`
5. `CourseSearchTool` queries ChromaDB via `VectorStore.search()` using sentence-transformer embeddings
6. Tool results are fed back to Claude in a second API call, which generates the final answer
7. Conversation exchange is saved to `SessionManager` (in-memory, keyed by session ID)

### Document ingestion (startup)

On server startup, `app.py` calls `RAGSystem.add_course_folder("../docs")`. `DocumentProcessor` parses structured `.txt` files into `Course`/`Lesson`/`CourseChunk` models, then `VectorStore` stores them in two ChromaDB collections:
- `course_catalog` — one document per course (title, instructor, lesson links)
- `course_content` — chunked lesson text, used for semantic search

Ingestion is idempotent: courses already in the catalog are skipped.

### Course document format

Files in `docs/` must follow this structure for the parser to extract metadata correctly:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <title>
Lesson Link: <url>
<lesson content...>

Lesson 2: <title>
...
```

### Key configuration (`backend/config.py`)

| Setting | Default | Notes |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Change here to swap models |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | SentenceTransformer model |
| `CHUNK_SIZE` | 800 chars | Affects retrieval granularity |
| `CHUNK_OVERLAP` | 100 chars | Sentence-aware overlap |
| `MAX_RESULTS` | 5 | ChromaDB results per search |
| `MAX_HISTORY` | 2 | Conversation turns remembered |
| `CHROMA_PATH` | `./chroma_db` | Relative to `backend/` |

### Extending the system

**Adding a new tool:** implement the `Tool` ABC in `search_tools.py` (requires `get_tool_definition()` and `execute()`), then register it with `tool_manager.register_tool()` in `RAGSystem.__init__()`.

**Adding a new API endpoint:** add it in `backend/app.py` and call methods on the `rag_system` instance already initialized there.

**Resetting the vector DB:** call `vector_store.clear_all_data()` or delete the `backend/chroma_db/` directory.
