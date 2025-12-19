# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run Commands

```bash
# Install dependencies
uv sync

# Run the application (from project root)
./run.sh

# Manual start (from backend directory)
cd backend && uv run uvicorn app:app --reload --port 8000
```

The application serves at `http://localhost:8000` with API docs at `/docs`.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot for course materials using FastAPI, ChromaDB, and Claude.

### Core Flow
1. **Document Ingestion**: Course documents (`.txt`, `.pdf`, `.docx`) from `docs/` are processed on startup
2. **Chunking**: Documents are split into sentence-based chunks with overlap for vector storage
3. **Query Processing**: User queries trigger AI-driven tool use to search the vector store
4. **Response Generation**: Claude generates responses using retrieved context

### Key Components

**Backend (`backend/`)**
- `app.py` - FastAPI server with `/api/query` and `/api/courses` endpoints
- `rag_system.py` - Main orchestrator connecting all components
- `vector_store.py` - ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (chunks)
- `ai_generator.py` - Claude API integration with tool-use support
- `document_processor.py` - Parses course documents and chunks text
- `search_tools.py` - Tool interface for AI to search course content
- `session_manager.py` - Conversation history management
- `models.py` - Pydantic models: `Course`, `Lesson`, `CourseChunk`

**Frontend (`frontend/`)** - Static HTML/CSS/JS served by FastAPI

### Document Format
Course documents follow a specific format:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: Introduction
Lesson Link: [url]
[content]

Lesson 1: [title]
...
```

### Configuration
- `config.py` - Settings loaded from environment (`.env` file required with `ANTHROPIC_API_KEY`)
- Default embedding model: `all-MiniLM-L6-v2`
- Default Claude model: `claude-sonnet-4-20250514`
