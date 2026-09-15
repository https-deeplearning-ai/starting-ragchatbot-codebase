# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A Retrieval-Augmented Generation (RAG) system that answers questions about course materials. FastAPI backend + vanilla JS frontend, ChromaDB for vector storage, Anthropic Claude for response generation.

## Commands

This project uses `uv` for Python dependency management (Python 3.13+, no pip/venv directly). On Windows, run these from Git Bash.

```bash
# Install dependencies
uv sync

# Run the app (starts backend on :8000, serves frontend at /)
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

There is no test suite, lint config, or build step in this repository — don't invent commands for these.

The app requires a `.env` file in the project root with `ANTHROPIC_API_KEY=...` (see [.env.example](.env.example)).

Course documents are loaded automatically from `docs/` on server startup (`backend/app.py`'s `startup_event`), skipping any course whose title already exists in ChromaDB. To force a full rebuild of the vector store, delete the `backend/chroma_db/` directory before starting.

## Architecture

### Request flow

`frontend/script.js` → `POST /api/query` (`backend/app.py`) → [`RAGSystem.query`](backend/rag_system.py) → [`AIGenerator.generate_response`](backend/ai_generator.py) → Claude API (with tool definitions) → if Claude calls the search tool, [`ToolManager`](backend/search_tools.py) dispatches to `CourseSearchTool.execute` → [`VectorStore.search`](backend/vector_store.py) → ChromaDB → tool results are fed back to Claude for a final synthesized answer.

Key design point: **Claude decides whether to search**, via Anthropic tool-calling (`tool_choice: auto`), rather than the RAG system always retrieving context up front. The system prompt in `AIGenerator.SYSTEM_PROMPT` instructs Claude to search only for course-specific questions and answer general questions from its own knowledge, one search per query max.

### Core components (all in `backend/`)

- **`app.py`** — FastAPI app. Two endpoints: `POST /api/query` (main chat) and `GET /api/courses` (analytics). Mounts `frontend/` as static files at `/`. Session ID is created server-side if the client doesn't supply one.
- **`rag_system.py`** — `RAGSystem` orchestrates all components and is the only class `app.py` talks to directly. Owns document ingestion (`add_course_document`, `add_course_folder`) and query handling (`query`).
- **`document_processor.py`** — Parses course text files into `Course`/`Lesson`/`CourseChunk` objects and chunks lesson text into overlapping sentence-based chunks (`chunk_text`). Expects a specific file format (see "Course document format" below).
- **`vector_store.py`** — Wraps ChromaDB with two collections: `course_catalog` (one entry per course, used to resolve fuzzy course-name queries to an exact title via semantic search) and `course_content` (chunked lesson text, used for actual content search). `search()` first resolves `course_name` to an exact title, then filters `course_content` by course title/lesson number.
- **`ai_generator.py`** — Wraps the Anthropic Messages API. Handles the two-round trip needed for tool use: initial call with tools → if `stop_reason == "tool_use"`, execute tools via `ToolManager` and make a second call (without tools) to get the final synthesized text.
- **`search_tools.py`** — `Tool` ABC + `CourseSearchTool` (the one tool currently registered) + `ToolManager` (registry Claude's tool calls are dispatched through). `CourseSearchTool` tracks `last_sources` from its most recent execution so the API layer can return source citations alongside the answer; `RAGSystem.query` reads and resets these via `ToolManager.get_last_sources()`/`reset_sources()`.
- **`session_manager.py`** — In-memory (non-persistent) conversation history keyed by session ID, capped at `MAX_HISTORY` exchanges. History is serialized to a plain text block and injected into the system prompt, not passed as structured message turns.
- **`config.py`** — Single `Config` dataclass, instantiated once as `config`, loaded from `.env`. Key tunables: `CHUNK_SIZE`/`CHUNK_OVERLAP` (document chunking), `MAX_RESULTS` (search results per query), `MAX_HISTORY` (conversation turns retained), `ANTHROPIC_MODEL`, `EMBEDDING_MODEL`.
- **`models.py`** — Pydantic models: `Course`, `Lesson`, `CourseChunk`. Course title is used as the unique ID throughout (vector store IDs, dedup checks).

### Course document format

Files in `docs/` (`.txt`, `.pdf`, or `.docx`) are expected to follow this structure, parsed by `DocumentProcessor.process_course_document`:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <lesson title>
Lesson Link: <url>
<lesson content...>

Lesson 1: <lesson title>
...
```

The course title is the dedup key when re-running ingestion — a course already present in `course_catalog` is skipped on subsequent startups.

### Frontend

Plain HTML/CSS/JS (no build step, no framework) in `frontend/`. `script.js` calls the two API endpoints directly and renders markdown-ish responses. Static files are served with no-cache headers in `app.py`'s `DevStaticFiles` for development convenience.
