# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A RAG (Retrieval-Augmented Generation) chatbot for querying course materials. Uses ChromaDB for vector storage, Anthropic Claude for AI generation, sentence-transformers for embeddings, and FastAPI for the backend. The frontend is a static HTML/JS/CSS app served by FastAPI.

## Commands

- **Install dependencies**: `uv sync`
- **Run the app**: `./run.sh` (or `cd backend && uv run uvicorn app:app --reload --port 8000`)
- **Run any Python command**: Always use `uv run <command>`, never `pip install` or bare `python` directly.
- **App URL**: http://localhost:8000 (API docs at /docs)

## Architecture

The backend follows a pipeline pattern orchestrated by `RAGSystem` (`backend/rag_system.py`):

1. **Document ingestion**: `DocumentProcessor` reads course text files from `docs/`, extracts structured metadata (title, instructor, lessons), and chunks content with sentence-aware splitting and configurable overlap.
2. **Vector storage**: `VectorStore` manages two ChromaDB collections — `course_catalog` (course-level metadata for name resolution) and `course_content` (chunked lesson text for semantic search). Course titles serve as unique IDs.
3. **Tool-based search**: Claude uses Anthropic tool calling to invoke `CourseSearchTool` during query processing. The `ToolManager` registers tools and handles execution. This means search is AI-driven, not hardcoded in the query pipeline.
4. **AI generation**: `AIGenerator` sends the user query to Claude with available tools. If Claude decides to search, it makes a tool call, results are executed and fed back, then Claude generates the final answer.
5. **Session management**: `SessionManager` maintains in-memory conversation history per session, formatted as text and injected into the system prompt.

### Key design decisions

- **Tool-based RAG**: Instead of always retrieving context, the AI decides when to search via Anthropic tool use. The search tool supports optional course name and lesson number filters.
- **Two-collection vector store**: Course metadata is stored separately from content chunks, enabling semantic course name resolution before content search.
- **Course document format**: Text files in `docs/` must follow a specific format — first 3 lines are metadata (`Course Title:`, `Course Link:`, `Course Instructor:`), followed by `Lesson N: Title` markers with optional `Lesson Link:` lines.
- **Static frontend**: Served directly by FastAPI via `StaticFiles` mount at `/`, no build step needed.

## Configuration

All tunable parameters are in `backend/config.py` as a dataclass: embedding model, chunk size/overlap, max search results, max conversation history, ChromaDB path, and Anthropic model. The Anthropic API key is loaded from `.env`.
