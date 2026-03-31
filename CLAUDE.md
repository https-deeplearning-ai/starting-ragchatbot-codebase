# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Run the application
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Install dependencies
uv sync

# Install dev dependencies (required for linting/formatting)
uv sync --group dev


# Add a new dependency
uv add package_name

# Run all tests
uv run pytest

# Run a single test file
uv run pytest backend/tests/test_rag_system.py

# Run a single test
uv run pytest backend/tests/test_rag_system.py::TestClassName::test_method_name

# Format code (modifies files: isort → black → flake8 → mypy)
./scripts/format.sh

# Lint only, no modifications
./scripts/lint.sh
```

- Web UI: http://localhost:8000
- API docs: http://localhost:8000/docs
- Requires `ANTHROPIC_API_KEY` in a `.env` file at the project root

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for course materials. FastAPI serves both the API and the vanilla JS frontend as static files.

### API endpoints

- `POST /api/query` — main query endpoint, returns `{ answer, sources, source_links, session_id }`
- `GET /api/courses` — returns course catalog stats `{ total_courses, course_titles }`
- `POST /api/clear-session` — clears a session by `{ session_id }`

### Query flow

1. Frontend (`frontend/script.js`) sends `POST /api/query` with `{ query, session_id }`
2. `app.py` creates a session if none exists, delegates to `RAGSystem.query()`
3. `RAGSystem` fetches conversation history from `SessionManager`, then calls `AIGenerator.generate_response()`
4. `AIGenerator` runs a **tool-calling loop** (max 2 rounds) with the Claude API:
   - Claude may call `search_course_content` (semantic chunk search) or `get_course_outline` (lesson list)
   - Tool results are appended to the message list and sent back to Claude
   - After max rounds, a final API call without tools forces a text response
5. `ToolManager` collects `last_sources` and `last_source_links` from whichever tool ran last
6. Response, sources, and lesson links are returned to the frontend
7. Frontend renders the answer as Markdown (`marked.js`) with a collapsible sources block

### Key design decisions

- **Course name resolution**: Partial/fuzzy course names are resolved via a semantic search against the `course_catalog` ChromaDB collection before filtering `course_content`. This lets Claude pass "MCP" and still find "Introduction to MCP Servers".
- **Dual ChromaDB collections**: `course_catalog` stores one document per course (title + metadata including `lessons_json`). `course_content` stores all text chunks with `course_title`/`lesson_number` metadata for filtered search.
- **Session storage**: Sessions are in-memory only — they are lost on server restart. `SessionManager` keeps the last 2 exchange pairs (4 messages) per session. Conversation history is injected into the system prompt, not the message list.
- **AI generation config**: `AIGenerator` uses `temperature=0` and `max_tokens=800`. Model is set in `config.py` (`ANTHROPIC_MODEL`). These are not exposed via env vars — change them in code.
- **Deduplication on startup**: `add_course_folder()` checks existing titles in `course_catalog` and skips already-ingested courses.

### Document format

Course files (`.txt`, `.pdf`, `.docx`) in `docs/` must follow this structure for `.txt` — `.pdf`/`.docx` support is parsed but the required header fields are the same:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <title>
Lesson Link: <url>
<lesson content>

Lesson 1: <title>
...
```

`DocumentProcessor` splits content into sentence-aware chunks (800 chars, 100 char overlap). The first chunk of each lesson is prefixed with `"Lesson N content: ..."` for retrieval context.

### Adding a new search tool

1. Create a class extending `Tool` (ABC in `search_tools.py`) implementing `get_tool_definition()` and `execute()`
2. Register it: `self.tool_manager.register_tool(your_tool)` in `RAGSystem.__init__()`
3. If it should surface sources in the UI, add `last_sources` and `last_source_links` instance attributes — `ToolManager.get_last_sources()` checks all registered tools for these
