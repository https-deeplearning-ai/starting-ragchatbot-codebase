# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands use `uv` as the package manager. Dependencies are declared in `pyproject.toml`. **Never use `pip` directly — always use `uv run` or `uv sync`.**

```bash
# Install dependencies
uv sync

# Run the server (from repo root)
./run.sh

# Or manually from the backend directory
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

**Environment:** Create a `.env` file in the repo root with `ANTHROPIC_API_KEY=...` before running.

## Architecture

This is a RAG (Retrieval-Augmented Generation) system using **Claude's tool-use feature** — rather than injecting retrieved context directly into a prompt, Claude is given a search tool and autonomously decides when and what to search.

### Request Flow

```
POST /api/query
  → RAGSystem.query()
    → AIGenerator.generate_response()  [first Claude call]
      → Claude decides to call search_course_content tool
        → CourseSearchTool.execute()
          → VectorStore.search()  [ChromaDB semantic search]
      → AIGenerator._handle_tool_execution()  [second Claude call with results]
    → SessionManager.add_exchange()  [store to history]
  → return (answer, sources)
```

### Key Components (`backend/`)

- **`rag_system.py`** — Top-level orchestrator. Owns all components and exposes `query()` and `add_course_folder()`.
- **`ai_generator.py`** — Wraps the Anthropic SDK. Handles the two-turn tool-use loop: initial call → tool execution → final response.
- **`vector_store.py`** — ChromaDB wrapper with two collections:
  - `course_catalog`: course-level metadata for fuzzy course name resolution
  - `course_content`: chunked lesson text for semantic similarity search
- **`document_processor.py`** — Parses structured `.txt` course files into `Course`/`Lesson`/`CourseChunk` objects, then splits content into overlapping chunks.
- **`search_tools.py`** — Defines the `search_course_content` tool in Anthropic's tool-calling schema. `ToolManager` registers tools and routes execution.
- **`session_manager.py`** — In-memory conversation history, keyed by session ID. History is appended to the system prompt as plain text.
- **`config.py`** — Single `Config` dataclass. Key tunables: `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`, `MAX_RESULTS=5`, `MAX_HISTORY=2`, model `claude-sonnet-4-20250514`.

### Course Document Format

Files in `docs/` must follow this structure for `DocumentProcessor` to parse them correctly:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <lesson title>
Lesson Link: <url>
<lesson content...>

Lesson 2: <lesson title>
...
```

The course title doubles as the unique ID in ChromaDB. On server startup, existing courses are skipped (deduplication by title).

### Frontend

A plain HTML/CSS/JS chat UI served as static files by FastAPI from `../frontend`. No build step required.
