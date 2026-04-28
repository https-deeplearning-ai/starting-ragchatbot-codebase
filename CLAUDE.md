# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package management

Always use `uv` to manage dependencies and run Python — never use `pip` or `python` directly.

```bash
uv sync          # install/update dependencies
uv run <cmd>     # run any Python command
```

## Setup

```bash
cp .env.example .env          # then add your ANTHROPIC_API_KEY
uv sync                       # install dependencies
```

## Running the app

```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

Server runs at `http://localhost:8000`. The backend also serves the frontend as static files.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot over course documents, using Claude's tool-use feature to decide when to search.

**Query flow:**
1. Frontend (`frontend/script.js`) sends `POST /api/query {query, session_id}` to FastAPI
2. `app.py` creates a session if needed, delegates to `RAGSystem.query()`
3. `RAGSystem` fetches conversation history, then calls `AIGenerator.generate_response()` with tools
4. Claude makes a **first API call** — if it decides to search, it invokes the `search_course_content` tool
5. `CourseSearchTool` → `VectorStore.search()` → ChromaDB returns top-5 chunks
6. Claude makes a **second API call** (without tools) to synthesize the chunks into a final answer
7. Sources and answer are returned to the frontend, which renders Markdown and a collapsible sources section

**Two-collection ChromaDB design:**
- `course_catalog` — one document per course (title, instructor, link, lessons serialized as JSON string in metadata)
- `course_content` — one document per text chunk, filterable by `course_title` and `lesson_number`

Course name resolution uses semantic search on `course_catalog` to find the best-matching title before filtering `course_content`.

**Adding a new tool:** implement the `Tool` ABC in `search_tools.py` (requires `get_tool_definition()` and `execute()`), then register it with `tool_manager.register_tool()` in `RAGSystem.__init__()`.

## Document format

Course files in `docs/` must follow this structure:
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

`course_title` is the unique key — duplicate titles are skipped on startup.

## Key config (`backend/config.py`)

| Setting | Default | Effect |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model for generation |
| `CHUNK_SIZE` | 800 chars | Max chunk size for vector storage |
| `CHUNK_OVERLAP` | 100 chars | Sentence-level overlap between chunks |
| `MAX_RESULTS` | 5 | ChromaDB results per search |
| `MAX_HISTORY` | 2 | Conversation turns kept in session |
| `CHROMA_PATH` | `./chroma_db` | Persistent vector DB location (relative to `backend/`) |

## Known quirk

In `document_processor.py`, the chunk context prefix is inconsistent: all lessons except the last use `"Lesson N content: <chunk>"`, while the last lesson uses `"Course <title> Lesson N content: <chunk>"`. This is likely an unfinished change.
