# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

**Prerequisites:** Python 3.13+, `uv`, and an Anthropic API key in a `.env` file:
```
ANTHROPIC_API_KEY=your-key-here
```

**Start the server:**
```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Install / sync dependencies:**
```bash
uv sync
```

> **Always use `uv` for all dependency management and running Python — never use `pip`, `pip install`, or bare `python` directly.**
> - Add packages: `uv add <package>`
> - Remove packages: `uv remove <package>`
> - Sync environment: `uv sync`
> - Run a script: `uv run <script>`

App runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

There is no test suite and no linter configured in this project.

## Architecture

This is a full-stack RAG (Retrieval-Augmented Generation) app. The backend is a FastAPI server that serves both the REST API and the static frontend files.

### Query flow (the critical path)

```
Frontend (script.js)
  → POST /api/query  (app.py)
  → RAGSystem.query()  (rag_system.py)
  → AIGenerator.generate_response()  (ai_generator.py)
      Round 1: Claude decides whether to call the search tool
      If tool_use → ToolManager.execute_tool()
                  → CourseSearchTool.execute()
                  → VectorStore.search()  [ChromaDB]
      Round 2: Claude synthesises the final answer
  → SessionManager.add_exchange()  stores history
  → returns { answer, sources, session_id }
```

Claude makes **two API calls per RAG query**: once to decide if search is needed, once to synthesise. General-knowledge questions skip retrieval entirely.

### Key design decisions

- **Tool-based retrieval:** Claude autonomously decides when to call `search_course_content`. The tool accepts `query`, optional `course_name` (fuzzy-matched), and optional `lesson_number`.
- **Two ChromaDB collections:** `course_catalog` resolves fuzzy course names via semantic search; `course_content` stores the actual text chunks for retrieval.
- **Session history as plain text:** Conversation history is formatted as `"User: ...\nAssistant: ..."` and injected into the system prompt (not as structured messages). Capped at `MAX_HISTORY * 2 = 4` messages.
- **ChromaDB persisted locally** at `./chroma_db` (relative to the `backend/` directory). The vector store is populated automatically on startup from the `../docs/` folder.
- **All config lives in `config.py`:** model name, chunk size/overlap, max results, history length, ChromaDB path. The active Claude model is `claude-sonnet-4-20250514`.

### Course document format

Documents in `docs/` must follow this plain-text format for `DocumentProcessor` to parse them correctly:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <lesson title>
Lesson Link: <url>
<lesson content...>

Lesson 2: <lesson title>
Lesson Link: <url>
<lesson content...>
```

The `course_title` field is used as the unique ID in ChromaDB — duplicate titles are skipped on startup.

### Adding a new tool

1. Subclass `Tool` (abstract base in `search_tools.py`) and implement `get_tool_definition()` + `execute()`.
2. Register it via `tool_manager.register_tool(your_tool)` in `RAGSystem.__init__`.
3. If the tool produces sources for the UI, add a `last_sources` list attribute — `ToolManager.get_last_sources()` checks for it automatically.
