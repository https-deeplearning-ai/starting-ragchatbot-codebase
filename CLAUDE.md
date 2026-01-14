# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Course Materials RAG (Retrieval-Augmented Generation) system - a full-stack web application that enables users to query course materials using semantic search and AI-powered responses. It combines a Python FastAPI backend with ChromaDB vector storage and a vanilla JavaScript frontend.

## Build and Run Commands

**Always use `uv` to run the server and manage all dependencies - never use `pip` directly.**

```bash
# Install dependencies (requires uv package manager)
uv sync

# Run the application (from backend directory)
cd backend
uv run uvicorn app:app --reload --port 8000

# Alternative: Quick start from root
./run.sh
```

The application serves both the API and frontend at `http://localhost:8000`.

## Architecture

### Backend Components (backend/)

- **app.py**: FastAPI application with `/api/query` (POST) and `/api/courses` (GET) endpoints. Serves frontend as static files.
- **rag_system.py**: Main orchestrator that coordinates document processing, vector search, AI generation, and session management.
- **ai_generator.py**: Anthropic Claude API integration with tool-calling support. Uses claude-sonnet-4 with temperature 0.
- **vector_store.py**: ChromaDB wrapper with two collections: `course_catalog` (metadata) and `course_content` (text chunks). Uses all-MiniLM-L6-v2 for embeddings.
- **document_processor.py**: Parses course documents into structured data. Expects format with `Course Title:`, `Course Link:`, `Course Instructor:`, and `Lesson N:` markers.
- **search_tools.py**: Tool definitions for Claude's tool-calling. `CourseSearchTool` implements the `search_course_content` tool with optional course/lesson filtering.
- **session_manager.py**: In-memory conversation history storage per session (max 2 messages).
- **config.py**: Configuration loaded from `.env` file (ANTHROPIC_API_KEY required).
- **models.py**: Pydantic models for Course, Lesson, and CourseChunk.

### Frontend (frontend/)

Vanilla JavaScript SPA with chat interface. Uses marked.js for markdown rendering. Maintains session_id for conversation continuity.

### Data Flow

1. User query → `/api/query` endpoint
2. RAG system retrieves session history
3. AI generator calls Claude with available tools
4. Claude may invoke `search_course_content` tool → vector store query
5. Tool results fed back to Claude for final response
6. Response with sources returned to frontend

## Configuration

Key settings in `config.py`:
- `CHUNK_SIZE`: 800 characters
- `CHUNK_OVERLAP`: 100 characters
- `MAX_RESULTS`: 5 search results
- `MAX_HISTORY`: 2 conversation exchanges

## Course Document Format

Documents in `docs/` follow this structure:
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

Documents are auto-loaded from `../docs` on application startup.
