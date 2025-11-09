# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) chatbot system for educational course materials. The system uses:
- **Agentic AI architecture** with Claude's tool-calling capabilities
- **Dual-collection vector storage** (ChromaDB) for metadata and content
- **Semantic fuzzy matching** for course name resolution
- **Session-based conversation memory** for multi-turn interactions

## Development Commands

### Running the Application

```bash
# Quick start (from root)
./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000

# Access points:
# - Web UI: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - API: /api/query (POST), /api/courses (GET)
```

### Dependency Management

```bash
# Install dependencies (uses uv)
uv sync

# Add new package
uv add <package-name>

# Update lock file
uv lock
```

### Environment Setup

Required `.env` file in root:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture

### Core RAG Pipeline Flow

1. **User Query** → FastAPI endpoint (`app.py`)
2. **Session Retrieval** → `SessionManager` fetches conversation history
3. **AI Tool Decision** → `AIGenerator` sends query + tool definitions to Claude
4. **Tool Execution** → `ToolManager` routes to `CourseSearchTool`
5. **Vector Search** → `VectorStore` performs semantic search with filters
6. **AI Synthesis** → Claude generates answer from search results
7. **Response + Sources** → Backend returns structured response

### Dual Collection Strategy

The vector store maintains **two separate ChromaDB collections**:

**`course_catalog` collection:**
- Stores course metadata (title, instructor, lesson list)
- Used for **fuzzy course name resolution**
- Enables queries like "MCP course" → "MCP: Build Rich-Context AI Apps with Anthropic"
- Small dataset (~10s of records)

**`course_content` collection:**
- Stores chunked course material (800 char chunks, 100 char overlap)
- Used for semantic search of actual content
- Filtered by resolved course name and/or lesson number
- Large dataset (~1000s of records)

**Why this matters:** When implementing search functionality, always resolve the course name via catalog search FIRST (in `VectorStore.search()`), then use the resolved exact title to filter content searches. This two-step process enables natural language course references.

### Tool-Based Search System

The system uses **Anthropic's tool calling** (not RAG prompt stuffing):

1. `search_tools.py` defines `CourseSearchTool` with Anthropic-compatible schema
2. `ToolManager` registers tools and provides definitions to AI
3. Claude autonomously decides when to call `search_course_content`
4. Multi-turn execution: AI can make multiple tool calls before responding
5. Sources tracked separately via `last_sources` for UI display

**Key pattern:** The AI has full autonomy over search decisions. Don't hardcode search triggers - let Claude determine when to use tools.

### Session Management

- Each user gets a unique `session_id` (created on first query if missing)
- History stored in-memory: last N message pairs (configurable via `MAX_HISTORY`)
- Format: List of `{"role": "user/assistant", "content": str}` dicts
- History injected into AI context on subsequent queries
- **Limitation:** Sessions reset on server restart (no persistence)

### Document Processing

Course documents must follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[content...]

Lesson 1: [title]
...
```

Processing pipeline:
1. `DocumentProcessor` parses structured format into `Course` + `Lesson` objects
2. Content chunked via **sentence-based splitting** (respects boundaries)
3. Each chunk tagged with `course_title` and `lesson_number` metadata
4. Lesson context prepended to first chunk of each lesson
5. Chunks stored as `CourseChunk` objects with full attribution

**Supported formats:** `.txt`, `.pdf`, `.docx`

## Key Implementation Details

### Adding New Search Tools

To add a tool (e.g., web search, calculator):

1. Create class inheriting from `Tool` (in `search_tools.py`)
2. Implement `get_tool_definition()` returning Anthropic tool schema
3. Implement `execute(**kwargs)` with tool logic
4. Register in `RAGSystem.__init__()`: `self.tool_manager.register_tool(MyTool())`
5. AI will automatically discover and use the new tool

### Configuration System

All settings centralized in `backend/config.py`:
- Uses `@dataclass` with environment variable loading
- Embedding model: `all-MiniLM-L6-v2` (384-dim vectors)
- Claude model: `claude-sonnet-4-20250514`
- Chunk size: 800 chars with 100 char overlap
- Max search results: 5
- Conversation history: 2 message pairs

**To modify settings:** Edit `Config` dataclass or add env vars to `.env`

### Frontend Integration

Frontend is vanilla JS (`frontend/script.js`):
- Maintains single `sessionId` across conversation
- Sends POST to `/api/query` with `{query, session_id}`
- Receives `{answer, sources, session_id}`
- Renders markdown with `marked.js`
- Sources displayed as collapsible list

**Static file serving:** FastAPI mounts `frontend/` directory at root path

### Incremental Document Loading

Startup behavior (`app.py` - `startup_event()`):
1. Loads all docs from `../docs` folder
2. Checks existing course titles in ChromaDB
3. Only adds **new courses** (skips duplicates by title match)
4. Set `clear_existing=True` in `add_course_folder()` for full rebuild

**Important:** Course identity determined by exact title match. Renaming a course in the file = new course entry.

## Common Pitfalls

1. **ChromaDB persistence:** Data stored in `./chroma_db` directory. Delete to reset.
2. **Virtual env mismatch:** Code uses `.venv` at root; ignore `backend/venv` warning.
3. **Course name resolution:** Always use `VectorStore.search()` unified interface, not direct collection queries.
4. **Tool execution order:** AI may call tools multiple times; don't assume single search per query.
5. **Source tracking:** Sources come from `ToolManager.get_last_sources()`, not AI response text.
6. **Windows compatibility:** Use Git Bash for running shell scripts on Windows.

## Extending the System

### Adding New Document Types

1. Add file extension to `add_course_folder()` filter (line 81 in `rag_system.py`)
2. Implement parser in `DocumentProcessor.process_course_document()`
3. Maintain same output format: `(Course, List[CourseChunk])`

### Adding Authentication

Currently no auth. To add:
1. Implement auth middleware in `app.py`
2. Add user context to `SessionManager`
3. Scope sessions and queries by user ID
4. Update API endpoints to require auth headers

### Improving Search Quality

1. **Re-ranking:** Add cross-encoder scoring after vector search
2. **Hybrid search:** Combine semantic + keyword (BM25) scores
3. **Query expansion:** Use Claude to generate alternative phrasings
4. **Metadata filtering:** Expand filters (instructor, course date, etc.)

All modifications should maintain the tool-based architecture pattern.
- always uv to run the server do not use pip directory
- make sure to use uv to manage all dependency