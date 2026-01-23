# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the application:**
```bash
./run.sh
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

**Install dependencies:**
```bash
uv sync
```

**Access points when running:**
- Web interface: http://localhost:8000
- API docs: http://localhost:8000/docs

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for course materials. The system uses ChromaDB for vector storage and Claude API for response generation.

### Request Flow

```
User Query → FastAPI (app.py) → RAGSystem.query()
                                     ↓
                              AIGenerator (Claude API with tools)
                                     ↓
                              CourseSearchTool → VectorStore.search()
                                     ↓
                              ChromaDB semantic search
                                     ↓
                              Results → Claude synthesizes response
```

### Key Components (backend/)

- **RAGSystem** (`rag_system.py`): Main orchestrator that wires together all components. Entry point for queries via `query()` and document ingestion via `add_course_folder()`.

- **VectorStore** (`vector_store.py`): ChromaDB wrapper with two collections:
  - `course_catalog`: Course metadata for name resolution
  - `course_content`: Chunked content for semantic search
  - Key method: `search(query, course_name, lesson_number)` handles course name resolution then content search.

- **AIGenerator** (`ai_generator.py`): Claude API integration with tool-calling support. Handles the agentic loop: initial request → tool execution → follow-up response.

- **DocumentProcessor** (`document_processor.py`): Parses course documents with expected format (Course Title/Link/Instructor in first lines, then "Lesson N:" markers). Uses sentence-aware chunking with configurable overlap.

- **ToolManager/CourseSearchTool** (`search_tools.py`): Tool definitions for Claude's tool-use. CourseSearchTool wraps VectorStore and tracks sources.

### Document Format

Course documents in `docs/` must follow:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [lesson title]
Lesson Link: [url]
[content...]

Lesson 1: [lesson title]
[content...]
```

### Configuration

All settings in `backend/config.py`, loaded from `.env`:
- `ANTHROPIC_API_KEY`: Required
- `ANTHROPIC_MODEL`: Default `claude-sonnet-4-20250514`
- `CHUNK_SIZE`: 800 chars
- `CHUNK_OVERLAP`: 100 chars
- `MAX_RESULTS`: 5 search results
- `CHROMA_PATH`: `./chroma_db`

### Data Persistence

ChromaDB data stored in `backend/chroma_db/`. On startup, `app.py` loads documents from `docs/` folder, skipping already-indexed courses.
