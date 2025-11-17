# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

### Quick Start
```bash
./run.sh
```

### Manual Start
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Dependencies Installation
```bash
uv sync
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

### Environment Setup
Requires `.env` file in root directory with:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Architecture Overview

This is a **Retrieval-Augmented Generation (RAG) system** for querying course materials using semantic search and Claude AI.

### Data Flow Architecture

The system follows a **tool-based RAG pattern** where Claude decides when to search:

```
User Query → FastAPI → RAG System → AI Generator → Claude API
                                         ↓
                                   Tool Decision?
                                         ↓
                            [Search] ← Tool Manager → Search Tool
                                         ↓
                                   Vector Store (ChromaDB)
                                         ↓
                                   Search Results
                                         ↓
                              Claude + Context → Final Response
```

### Core Components (Backend)

**1. app.py (Entry Point)**
- Defines FastAPI endpoints: `POST /api/query` and `GET /api/courses`
- Initializes RAGSystem on startup
- Auto-loads documents from `../docs` folder
- Serves frontend static files from `../frontend`

**2. rag_system.py (Orchestrator)**
- Central coordinator for all RAG operations
- Manages lifecycle of queries from input to response
- Bridges between AI Generator, Vector Store, and Tool Manager
- Handles conversation context via SessionManager
- Key method: `query(query, session_id)` returns `(answer, sources)`

**3. ai_generator.py (Claude Integration)**
- Wraps Anthropic Claude API with tool-calling support
- Two-phase response generation:
  - Phase 1: Initial API call with tools available
  - Phase 2: If tool used, collect results and make final call without tools
- Method `_handle_tool_execution()` manages tool execution loop
- Static system prompt instructs Claude on tool usage patterns

**4. vector_store.py (Semantic Search)**
- ChromaDB wrapper with two collections:
  - `course_catalog`: Course metadata (titles, instructors, links)
  - `course_content`: Chunked course material with embeddings
- Uses SentenceTransformer (all-MiniLM-L6-v2) for embeddings
- Key method: `search(query, course_name, lesson_number)` with smart course name resolution
- Course name resolution uses semantic search on catalog to handle fuzzy matching

**5. search_tools.py (Tool System)**
- `Tool` abstract base class for creating Claude-callable tools
- `CourseSearchTool`: Implements search with Anthropic tool definition schema
- `ToolManager`: Registry for tools, handles execution and tracks sources
- Tool definition includes input schema with optional parameters (course_name, lesson_number)

**6. document_processor.py (Content Pipeline)**
- Parses course documents with expected format:
  ```
  Course Title: [title]
  Course Link: [url]
  Course Instructor: [name]

  Lesson 0: [title]
  Lesson Link: [url]
  [content]

  Lesson 1: [title]
  ...
  ```
- Sentence-based chunking with overlap (default: 800 chars, 100 overlap)
- Creates `Course` and `CourseChunk` objects for vector storage
- Adds lesson context to chunks: "Course X Lesson Y content: ..."

**7. session_manager.py (Conversation History)**
- Manages user conversation sessions with configurable history depth
- Stores message pairs (user/assistant) in memory
- Returns formatted history string for context injection
- Default: Keeps last 2 exchanges (4 messages)

**8. models.py (Data Models)**
- Pydantic models: `Course`, `Lesson`, `CourseChunk`
- Course title serves as unique identifier
- Chunks include metadata: course_title, lesson_number, chunk_index

### Frontend (Vanilla JavaScript)

**script.js** handles:
- API calls to `/api/query` and `/api/courses`
- Session management (session_id persistence)
- Message rendering with markdown support (marked.js)
- Loading states and error handling

### Key Configuration (config.py)

```python
ANTHROPIC_MODEL: "claude-sonnet-4-20250514"
EMBEDDING_MODEL: "all-MiniLM-L6-v2"
CHUNK_SIZE: 800
CHUNK_OVERLAP: 100
MAX_RESULTS: 5
MAX_HISTORY: 2  # conversation exchanges
CHROMA_PATH: "./chroma_db"
```

## Tool-Based RAG Pattern

**Critical Design Decision**: This system uses Claude's tool-calling capability rather than always searching:

1. User query reaches `ai_generator.py`
2. Claude receives query + system prompt + tool definitions
3. Claude decides: "Do I need to search course content?"
   - **Yes**: Invokes `search_course_content` tool → retrieves context → generates answer
   - **No**: Answers directly from general knowledge
4. Tool results are injected as a new user message
5. Final response generated without tools

This allows Claude to:
- Answer general questions without searching
- Use semantic search only for course-specific queries
- Make intelligent decisions about course/lesson filtering

## Document Format Requirements

Course documents in `docs/` must follow this structure:

```
Course Title: [Required - First line]
Course Link: [Optional - URL]
Course Instructor: [Optional - Name]

Lesson 0: [Lesson title]
Lesson Link: [Optional - URL]
[Lesson content...]

Lesson 1: [Next lesson title]
...
```

Missing metadata will use defaults. Documents without lesson markers are treated as single documents.

## ChromaDB Persistence

- Database stored in `./chroma_db` (relative to backend directory)
- Persistent across restarts
- Startup checks for existing courses before adding
- Duplicate courses (by title) are skipped
- Use `clear_existing=True` in `add_course_folder()` to rebuild from scratch

## Common Issues

**API Key**: Ensure `.env` exists in root directory (not backend/) with valid Anthropic API key.

**Port Conflicts**: Default port 8000. Change with `--port` flag in uvicorn command.

**ChromaDB Warnings**: Resource tracker warnings are suppressed via warnings filter in app.py.

**Course Not Loading**: Check `docs/` path is relative to backend directory (`../docs`). Startup logs show load status.

**Session Context**: Frontend manages session_id. Backend creates new session if missing. Sessions are in-memory only.
- always use uv to run the server do not use pip directly.
- make sure use uv to manage all dependencies
- make sure use uv to manage all dependencies use uv add
- use uv to run python files