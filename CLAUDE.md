# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) chatbot system for querying course materials. Uses ChromaDB for vector storage, Anthropic's Claude with tool calling for AI generation, and FastAPI for the backend with a vanilla JavaScript frontend.

## Running the Application

**IMPORTANT**: This project uses `uv` for package management. Always use `uv` commands - never use `pip` directly.

### Setup
```bash
# Install dependencies
uv sync

# Create .env file (copy from .env.example)
ANTHROPIC_API_KEY=your_api_key_here
```

### Start Server
```bash
# Quick start
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

Access: http://localhost:8000

### Package Management
```bash
# Add new dependency
uv add <package-name>

# Run any Python command
uv run <command>

# DO NOT use pip install - always use uv
```

## Core Architecture

### Request Flow: Frontend → Backend
1. **Frontend** (`frontend/script.js`): User query → POST `/api/query` with `{query, session_id}`
2. **API** (`backend/app.py`): FastAPI endpoint → `rag_system.query()`
3. **RAG System** (`backend/rag_system.py`): Orchestrates query processing
   - Retrieves conversation history from SessionManager
   - Calls AIGenerator with tool definitions
   - Collects sources from ToolManager
4. **AI Generator** (`backend/ai_generator.py`): Claude API interaction
   - If Claude decides to use tools → executes via ToolManager
   - Tool results sent back to Claude for synthesis
5. **Search Tool** (`backend/search_tools.py`): CourseSearchTool.execute()
   - Calls VectorStore.search() with optional filters
6. **Vector Store** (`backend/vector_store.py`): ChromaDB semantic search
   - Resolves course names via semantic matching in `course_catalog` collection
   - Searches course content in `course_content` collection
   - Returns SearchResults with documents + metadata

### Two-Collection Strategy
- **`course_catalog`**: Course metadata (title, instructor, lessons) for semantic course name matching
- **`course_content`**: Chunked course content with metadata (course_title, lesson_number, chunk_index)

### Document Processing
Course documents must follow this format:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [instructor]

Lesson 0: [lesson title]
Lesson Link: [lesson url]
[lesson content]

Lesson 1: [lesson title]
...
```

`DocumentProcessor` (`backend/document_processor.py`):
- Parses metadata from first 3-4 lines
- Extracts lessons with regex pattern `Lesson \d+:`
- Chunks text using sentence-based splitting with overlap (configurable in `config.py`)
- Creates `Course` and `CourseChunk` objects

### Configuration
All settings in `backend/config.py`:
- `CHUNK_SIZE`: 800 chars (text chunk size)
- `CHUNK_OVERLAP`: 100 chars (overlap between chunks)
- `MAX_RESULTS`: 5 (search results limit)
- `MAX_HISTORY`: 2 (conversation messages to remember)
- `ANTHROPIC_MODEL`: claude-sonnet-4-20250514
- `EMBEDDING_MODEL`: all-MiniLM-L6-v2

### Session Management
`SessionManager` (`backend/session_manager.py`):
- Creates unique session IDs (`session_1`, `session_2`, etc.)
- Maintains conversation history (max 2 exchanges = 4 messages)
- Formats history for AI context as: `"User: [msg]\nAssistant: [msg]"`

### Tool-Based Search
AI can call `search_course_content` tool with:
- `query` (required): What to search for
- `course_name` (optional): Course filter (partial matches work via semantic search)
- `lesson_number` (optional): Specific lesson filter

Tool execution returns formatted results: `[Course Title - Lesson N]\n{content}`

## Key Components

### Backend (`backend/`)
- `app.py`: FastAPI application, CORS setup, static file serving
- `rag_system.py`: Main orchestrator coordinating all components
- `ai_generator.py`: Claude API wrapper with tool execution loop
- `vector_store.py`: ChromaDB interface with dual collections
- `search_tools.py`: Tool definitions and execution (CourseSearchTool, ToolManager)
- `document_processor.py`: Course parsing and text chunking
- `session_manager.py`: Conversation history tracking
- `models.py`: Pydantic models (Course, Lesson, CourseChunk)
- `config.py`: Centralized configuration

### Frontend (`frontend/`)
- `index.html`: Chat interface
- `script.js`: API calls, message rendering (uses marked.js for markdown), session management
- `styles.css`: UI styling

### Data Storage
- `docs/`: Course documents (auto-loaded on startup)
- `chroma_db/`: Persistent vector database (created automatically)

## Development Notes

### Adding New Tools
1. Create tool class inheriting from `Tool` in `search_tools.py`
2. Implement `get_tool_definition()` and `execute()`
3. Register with `ToolManager` in `rag_system.py`

### Modifying Search Behavior
- Course name resolution: `VectorStore._resolve_course_name()` (semantic search in catalog)
- Filter logic: `VectorStore._build_filter()` (ChromaDB where clauses)
- Result formatting: `CourseSearchTool._format_results()`

### AI Response Tuning
- System prompt: `AIGenerator.SYSTEM_PROMPT` (instructions for Claude)
- Temperature: `AIGenerator.base_params["temperature"]` (currently 0 for deterministic)
- Max tokens: `AIGenerator.base_params["max_tokens"]` (currently 800)

### Windows Development
Use Git Bash for running shell scripts (`run.sh`). Commands are POSIX-compatible.

## Data Flow Diagram

See `query-flow-diagram.md` for detailed visual flow from user input to response display.
