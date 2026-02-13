# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retrieval-Augmented Generation (RAG) System for Course Materials** — a full-stack web application that allows users to ask questions about course materials and receive context-aware responses. It combines semantic vector search with Claude AI's tool calling to provide accurate, sourced answers.

**Key Technologies:**
- **Backend**: FastAPI + Python 3.13+
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Vector Storage**: ChromaDB with SentenceTransformer embeddings
- **AI**: Anthropic Claude API (claude-sonnet-4-20250514)
- **Package Manager**: `uv`

## Development Commands

### Setup & Installation

```bash
# Install dependencies
uv sync

# Set up environment
# Create .env file in the root directory with:
# ANTHROPIC_API_KEY=your_key_here
```

### Running the Application

```bash
# Quick start (recommended)
chmod +x run.sh
./run.sh

# Or manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

The application runs on `http://localhost:8000` with API docs at `http://localhost:8000/docs`

### Linting & Code Quality

No linting/formatting tools are currently configured. Consider adding Ruff/Black if code quality checks are needed.

### Testing

No test framework is currently set up. Tests would go in a `tests/` directory and should cover:
- RAG query pipeline (end-to-end)
- Vector search with filters
- Tool execution
- Session management
- Document processing and chunking

## Architecture Overview

### High-Level Data Flow

```
User Query → Frontend (JS) → FastAPI Endpoint
                                     ↓
                          RAGSystem Orchestrator
                                     ↓
                    AI Generator (with Tool Calling)
                       ↓ (if tool needed)
                    Course Search Tool
                       ↓
                    Vector Store (ChromaDB)
                       ↓
                    Return Results → Claude Synthesis
                                     ↓
                    Response + Sources → Frontend
```

### Core Components & Responsibilities

#### **Frontend** (`frontend/`)
- `frontend/script.js`: Single entry point for user interactions
  - Sends POST requests to `/api/query` with `{ query, session_id }`
  - Manages UI state, loading states, and markdown rendering
  - Persists session_id for multi-turn conversations
  - Displays sources in collapsible details
- `frontend/index.html`: Chat interface layout
- `frontend/style.css`: Styling

#### **Backend** (`backend/`)

**API Layer** (`backend/app.py`)
- `POST /api/query`: Main query endpoint (request → response flow)
- `GET /api/courses`: Returns course statistics for UI
- On startup: loads all documents from `docs/` folder into vector store

**RAG Orchestration** (`backend/rag_system.py`)
- Coordinates the complete query pipeline
- Gets conversation history from session
- Calls AI generator and collects output
- Manages tool execution and source tracking
- Stores exchanges in session for context

**AI Generation** (`backend/ai_generator.py`)
- Calls Anthropic Claude API with tool definitions
- **Uses tool calling**, not prompt injection
- Handles Claude's tool_use responses by executing the tool and feeding results back
- System prompt instructs Claude to only use search tool for course-specific questions
- Returns synthesized response with source tracking

**Tool Management** (`backend/search_tools.py`)
- Defines `search_course_content` tool for Claude
- Tool parameters: `query` (required), `course_name` (optional), `lesson_number` (optional)
- Executes searches via VectorStore and tracks results in `last_sources`
- Results formatted as markdown for Claude consumption

**Vector Store** (`backend/vector_store.py`)
- ChromaDB interface with two collections:
  - `course_catalog`: Course metadata for fuzzy name resolution
  - `course_content`: Chunked course material with embeddings
- Semantic search with metadata filtering (course + lesson)
- Returns top 5 results (configurable via `MAX_RESULTS`)
- Fuzzy course name matching (e.g., "MCP" → "MCP: Build Rich-Context AI Apps...")

**Document Processing** (`backend/document_processor.py`)
- Parses course documents from `docs/` folder
- Expected format: course metadata (title, link, instructor) followed by "Lesson N:" markers
- Chunks content into 800-char segments with 100-char overlap
- Creates `CourseChunk` objects with course_title, lesson_number, and chunk_index metadata

**Session Management** (`backend/session_manager.py`)
- In-memory session storage (one instance per backend)
- Creates unique session IDs for conversations
- Stores conversation history (user + assistant messages)
- Returns formatted history to be passed to Claude for context
- Limits history to last 10 messages (5 turns) to manage token usage

**Data Models** (`backend/models.py`)
- `QueryRequest`: { query: str, session_id: Optional[str] }
- `QueryResponse`: { answer: str, sources: List[str], session_id: str }
- `CourseChunk`: Internal representation with metadata

**Configuration** (`backend/config.py`)
- API keys, model names, vector store settings
- Loads ANTHROPIC_API_KEY from environment

### Key Architectural Patterns

#### 1. **Tool Calling (Not Prompt Injection)**
Claude is given a tool definition and decides whether to call it. Flow:
1. Send query + tools to Claude
2. If Claude returns `stop_reason="tool_use"`, extract tool name and input
3. Execute the tool and return results to Claude
4. Claude uses results to generate final response

This is more reliable and interpretable than embedding search results in prompts.

#### 2. **Semantic Search with Metadata Filtering**
- Documents are chunked and embedded using `all-MiniLM-L6-v2` model
- Metadata (course_title, lesson_number) attached to each chunk
- Search can filter by course/lesson before doing semantic ranking
- Fuzzy course name resolution handles user input variations

#### 3. **Session-Based Conversation Context**
- Each query creates or reuses a session
- Session stores previous exchanges as formatted history
- History passed to Claude to maintain context across turns
- Prevents token explosion by keeping last 5 turns (configurable)

#### 4. **Source Tracking**
- Tool execution records which chunks were used
- Sources extracted and returned to frontend
- Frontend displays sources as references (e.g., "MCP - Lesson 5")

### Document Format & Processing

Documents in `docs/` must follow this structure:

```
Course Title: [Title]
Course Link: [Optional URL]
Course Instructor: [Name]

Lesson 0: [Title]
[Content...]

Lesson 1: [Title]
[Content...]
```

Processing pipeline:
1. Extract metadata from first 3 lines
2. Split by "Lesson N:" markers
3. Chunk each lesson (800 chars, 100 char overlap)
4. Create CourseChunk with metadata
5. Store in ChromaDB with embeddings

### Database: ChromaDB Architecture

Two collections:
- **course_catalog**: Stores all course titles for fuzzy matching (resolve_course_name)
- **course_content**: Stores all chunks with:
  - `content`: The actual text
  - `course_title`: Full course name (for metadata filtering)
  - `lesson_number`: Lesson index (for metadata filtering)
  - `chunk_index`: Position within lesson (for tracking)

Metadata filtering in search:
```python
filter = {"$and": [
    {"course_title": "Exact Title"},
    {"lesson_number": 5}
]}
```

## Important Development Notes

### Adding New Documents
1. Add `.txt` file to `docs/` folder following the format above
2. Restart backend — documents are loaded on startup
3. Deduplication prevents re-processing existing documents

### Modifying the AI Behavior
- Edit system prompt in `backend/ai_generator.py` (SYSTEM_PROMPT)
- Tool definitions controlled in `backend/search_tools.py` (get_tool_definition)
- Claude model and parameters in `backend/config.py`

### Extending Tool Functionality
1. Add new tool definition in `backend/search_tools.py`
2. Implement tool execution in `CourseSearchTool` or create new tool class
3. Register in `backend/rag_system.py` ToolManager
4. Claude will automatically use tools if needed

### Session Persistence
Current implementation uses in-memory storage — sessions are lost on restart. For production:
- Replace `SessionManager.sessions` dict with database
- Recommend: SQLite or PostgreSQL with schema for sessions + messages

### Frontend-Backend Communication
- All requests are JSON POST to `/api/query`
- Frontend handles all rendering and state
- API response includes session_id for client to persist

## Common Debugging Scenarios

**"No sources found"**: Check that documents are in `docs/` folder and follow the format. Restart the backend.

**"Tool not called"**: Check AI generator's SYSTEM_PROMPT — it might be configured to not use tools. Review Claude's temperature and tool_choice settings.

**"Slow responses"**: Vector search with many documents. Monitor ChromaDB query times. Consider:
- Increasing MAX_RESULTS filtering
- Adding more specific course/lesson filters
- Profiling vector store performance

**"Lost conversation context"**: Sessions are in-memory. Reload page creates new session. Replace with persistent storage for multi-session support.

## Environment Variables

Required:
- `ANTHROPIC_API_KEY`: Your Anthropic API key

Optional (defaults in `backend/config.py`):
- Model name, temperature, max tokens, vector store paths

# Add new dependencies
uv add package_name

# install dependecies
uv sync