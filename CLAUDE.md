# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) system for querying course materials. The system uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a FastAPI-based web interface.

## Guidelines for Claude Code

**IMPORTANT: Do not automatically start the server or run the application.** The developer will manually start the server when ready. Never execute `./run.sh` or `uvicorn` commands unless explicitly requested by the developer.

## Development Commands

### Running the Application

**Quick start:**
```bash
./run.sh
```

**Manual start:**
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The app will be available at `http://localhost:8000` with API docs at `http://localhost:8000/docs`.

### Dependency Management

**Install dependencies:**
```bash
uv sync
```

**Note:** This project uses `uv` for Python package management, not pip. Python 3.13+ is required.

### Environment Setup

Create a `.env` file in the root directory with:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Architecture

### RAG System Flow

The system follows this flow for query processing:

1. **Query Reception** (`app.py`) - FastAPI receives user query via POST `/api/query`
2. **RAG Orchestration** (`rag_system.py`) - Coordinates all components:
   - Creates/retrieves session for conversation context
   - Passes query to AI generator with tool access
3. **Tool-Based Search** (`search_tools.py` + `ai_generator.py`):
   - Claude decides whether to use the search tool based on query type
   - If needed, executes `search_course_content` tool
4. **Vector Search** (`vector_store.py`):
   - Resolves course names semantically via `course_catalog` collection
   - Searches content in `course_content` collection with filters
   - Returns ranked results with metadata
5. **Response Generation** (`ai_generator.py`) - Claude synthesizes final answer from search results
6. **Session Management** (`session_manager.py`) - Stores conversation history (last 2 exchanges by default)

### Core Components

**RAGSystem** (`rag_system.py`) - Main orchestrator that wires together:
- `DocumentProcessor` - Parses course documents and creates chunks
- `VectorStore` - Manages ChromaDB collections and semantic search
- `AIGenerator` - Handles Claude API calls with tool support
- `SessionManager` - Tracks conversation history per session
- `ToolManager` + `CourseSearchTool` - Provides search capability to Claude

**VectorStore** (`vector_store.py`) - Two ChromaDB collections:
- `course_catalog` - Course metadata (title, instructor, lessons) for semantic course name resolution
- `course_content` - Text chunks with metadata (course_title, lesson_number, chunk_index)

**Document Processing** (`document_processor.py`) - Expects structured format:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 1: [title]
Lesson Link: [url]
[content...]
```

Chunks text into ~800 character segments with 100 character overlap, adding context markers like `"Course X Lesson Y content: ..."`.

**AI Tool System** (`search_tools.py`) - Claude uses tool calling to search when needed:
- Tool decides whether to search based on query type (general knowledge vs course-specific)
- Supports optional `course_name` and `lesson_number` filters
- Course names are fuzzy-matched semantically via vector search

### Configuration

All settings in `backend/config.py`:
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (sentence-transformers)
- `CHUNK_SIZE`: 800 chars, `CHUNK_OVERLAP`: 100 chars
- `MAX_RESULTS`: 5 search results returned
- `MAX_HISTORY`: 2 conversation exchanges remembered

### Data Flow

Documents → DocumentProcessor (parse + chunk) → VectorStore (embed + index) → RAG query → ToolManager (search if needed) → AIGenerator (synthesize response) → User

### Frontend

Static HTML/CSS/JS in `/frontend`:
- `index.html` - Main UI
- `script.js` - API calls to `/api/query` and `/api/courses`
- `style.css` - Styling

Served by FastAPI's StaticFiles with no-cache headers for development.

## Common Workflows

### Adding New Documents

Place `.txt`, `.pdf`, or `.docx` files in `/docs` folder. On startup, `app.py` automatically loads documents that don't already exist in the vector store (checks by course title).

To force a rebuild:
```python
# In backend/app.py startup_event(), add clear_existing=True:
courses, chunks = rag_system.add_course_folder(docs_path, clear_existing=True)
```

### Modifying Search Behavior

Search logic is in `vector_store.py` `search()` method:
- Course name resolution: `_resolve_course_name()` uses semantic search on catalog
- Content filtering: `_build_filter()` creates ChromaDB where clauses
- Adjust `MAX_RESULTS` in config to change number of chunks returned

### Changing AI Behavior

System prompt in `ai_generator.py` `SYSTEM_PROMPT` controls:
- When to use search tool (course-specific vs general knowledge)
- Response style (concise, educational, no meta-commentary)
- Tool usage limits (one search per query maximum)

## Project Structure Notes

- **No tests directory** - Tests not yet implemented
- **ChromaDB persistence** - Vector DB stored in `./chroma_db` (gitignored)
- **Windows compatibility** - Use Git Bash for shell scripts on Windows
- **Frontend integration** - Backend serves frontend files, no separate frontend server needed
