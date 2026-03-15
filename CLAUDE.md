# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
cp .env.example .env   # add ANTHROPIC_API_KEY
./run.sh               # starts FastAPI on http://localhost:8000
```

The frontend is served as static files from the same FastAPI server — no separate frontend build step.

Manual start (equivalent to run.sh):
```bash
cd backend && uv run uvicorn app:app --reload --port 8000
```

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot with a FastAPI backend and vanilla JS frontend. The backend uses **two-pass Claude API calls** per query: the first call decides whether to invoke the `search_course_content` tool; if it does, search results are injected and a second call generates the final answer.

### Component responsibilities

- **`rag_system.py`** — top-level orchestrator; wires together all components and is the single entry point for `app.py`
- **`ai_generator.py`** — owns all Claude API interaction; handles the tool-use loop in `_handle_tool_execution()`
- **`vector_store.py`** — ChromaDB wrapper with two collections: `course_catalog` (course metadata for fuzzy name resolution) and `course_content` (chunked text for semantic search)
- **`search_tools.py`** — defines the `search_course_content` tool Claude can call; `CourseSearchTool` stores `last_sources` after each search for the UI to display
- **`document_processor.py`** — parses `.txt`/`.pdf`/`.docx` course files into `Course` + `CourseChunk` objects; expects a specific header format (see below)
- **`session_manager.py`** — in-memory session store; history is capped at `MAX_HISTORY * 2` messages and injected into the system prompt as plain text
- **`config.py`** — all tuneable parameters (`CHUNK_SIZE`, `CHUNK_OVERLAP`, `MAX_RESULTS`, `MAX_HISTORY`, model name, ChromaDB path)

### Course document format

Documents in `/docs` must follow this header format for metadata to be parsed correctly:

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

Course title is used as the unique ID in ChromaDB — duplicate titles are skipped on startup.

### Data flow

```
POST /api/query → RAGSystem.query()
  → SessionManager (fetch history)
  → AIGenerator.generate_response()     [1st Claude call]
      → if tool_use: CourseSearchTool.execute()
          → VectorStore.search()
              → course_catalog query (resolve course name)
              → course_content query  (semantic search)
      → AIGenerator._handle_tool_execution() [2nd Claude call]
  → ToolManager.get_last_sources()
  → SessionManager (save exchange)
← (answer, sources)
```

## Key Configuration (`config.py`)

| Setting | Default | Effect |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model used for all generation |
| `CHUNK_SIZE` | `800` | Max characters per vector chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between consecutive chunks |
| `MAX_RESULTS` | `5` | Max chunks returned per search |
| `MAX_HISTORY` | `2` | Conversation turns kept in context |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence path (relative to `backend/`) |
