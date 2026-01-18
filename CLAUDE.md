# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Course Materials RAG (Retrieval-Augmented Generation) chatbot - a full-stack web application that answers questions about course materials using semantic search and Claude AI.

## Commands

**Always use UV to run the server and manage dependencies, never pip.**

```bash
# Install dependencies
uv sync

# Run the application (starts FastAPI server on port 8000)
./run.sh
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Web interface: http://localhost:8000
# API docs: http://localhost:8000/docs
```

## Environment Setup

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

## Architecture

### Query Flow

```
Frontend (script.js)
    → POST /api/query
    → app.py endpoint
    → rag_system.query()
    → ai_generator.generate_response() [calls Claude API with tools]
    → Claude decides whether to use search_course_content tool
    → If tool used: search_tools.py → vector_store.py → ChromaDB
    → Response + sources returned to frontend
```

### Key Components

- **rag_system.py**: Central orchestrator that coordinates all subsystems
- **ai_generator.py**: Claude API integration with tool-use support. Claude decides when to search (tool_choice: auto)
- **search_tools.py**: Tool definitions for Claude's function calling. `CourseSearchTool` wraps vector store searches
- **vector_store.py**: ChromaDB wrapper with two collections:
  - `course_catalog`: Course metadata for semantic course name resolution
  - `course_content`: Document chunks for content search
- **document_processor.py**: Parses course documents, identifies lessons, chunks text with sentence-aware splitting
- **session_manager.py**: Conversation history management per session

### Configuration (backend/config.py)

Key settings: `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`, `MAX_RESULTS=5`, `MAX_HISTORY=2`

### Data Models (backend/models.py)

- `Course`: Title, link, instructor, lessons
- `Lesson`: Number, title, link
- `CourseChunk`: Text chunk with course/lesson metadata

### Frontend

Vanilla HTML/CSS/JS in `frontend/`. Uses marked.js for markdown rendering. No build step required.

### Course Documents

Sample documents in `docs/` are auto-loaded on server startup by `app.py` lifespan handler.
