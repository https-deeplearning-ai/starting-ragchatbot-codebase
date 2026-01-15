# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) system for querying course materials. It combines semantic search (ChromaDB) with AI generation (Claude API) to provide intelligent, context-aware answers about educational content.

**Tech Stack**: FastAPI backend, vanilla JavaScript frontend, ChromaDB vector store, Claude Sonnet 4, sentence-transformers for embeddings.

## Development Commands

**CRITICAL: Always use `uv` to run this service.** This project uses `uv` for Python package management and virtual environment management. Never use `pip`, `python`, or `python -m` directly - always prefix commands with `uv run` or use `uv sync` for dependency management.

### Running the Application

```bash
# Quick start (recommended)
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

Access points:
- Web UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

### Package Management

```bash
# Install/sync dependencies
uv sync

# Add a new dependency
uv add package-name

# Run Python commands in the virtual environment
uv run python script.py
```

### Environment Setup

Required `.env` file in root directory:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture Overview

### Request Flow (Frontend → Backend → AI → Response)

1. **Frontend** (`frontend/script.js`) sends POST to `/api/query` with `{query, session_id}`
2. **FastAPI** (`backend/app.py`) routes to RAG system
3. **RAG System** (`backend/rag_system.py`) orchestrates the entire flow:
   - Retrieves conversation history from SessionManager
   - Calls AIGenerator with query, history, and tool definitions
4. **AI Generator** (`backend/ai_generator.py`) makes **two Claude API calls**:
   - **Call #1**: Claude decides whether to use the search tool
   - If tool use requested: ToolManager executes search
   - **Call #2**: Claude generates final answer using search results
5. **Tool Execution** (`backend/search_tools.py`):
   - CourseSearchTool calls VectorStore.search()
   - Formats results with course/lesson context
   - Tracks sources for UI display
6. **Vector Store** (`backend/vector_store.py`):
   - Resolves fuzzy course names via semantic search in `course_catalog`
   - Searches content in `course_content` collection with filters
   - Returns top 5 most relevant chunks
7. **Response**: Answer + sources returned to frontend, conversation history updated

### Two-Collection Vector Store Design

**Why two collections?**
- `course_catalog`: Stores course metadata (title, instructor, lessons) for course name resolution
- `course_content`: Stores actual text chunks for semantic content search

This separation enables fuzzy course name matching (e.g., "MCP" → "Introduction to MCP Servers") before filtering content.

### Document Processing Pipeline

**Location**: `backend/document_processor.py`

Documents in `docs/` folder are processed on startup (`app.py:startup_event`):

1. **Parse metadata** from first 3 lines:
   ```
   Course Title: [title]
   Course Link: [url]
   Course Instructor: [name]
   ```

2. **Extract lessons** using regex pattern `Lesson \d+: [title]`
   - Optionally followed by `Lesson Link: [url]`

3. **Chunk text** (sentence-based):
   - Chunk size: 800 characters
   - Overlap: 100 characters
   - Preserves sentence boundaries

4. **Add context** to chunks:
   - Format: `"Course {title} Lesson {N} content: {text}"`
   - Helps AI understand source during retrieval

5. **Store in ChromaDB**:
   - Course metadata → `course_catalog` collection
   - Text chunks → `course_content` collection

**Deduplication**: Existing course titles are checked before adding to avoid duplicates.

### Session Management

**Location**: `backend/session_manager.py`

- Each user gets a unique `session_id` (format: `session_N`)
- Conversation history limited to **2 exchanges** (4 messages total)
- History is formatted and injected into Claude's system prompt
- Enables context-aware multi-turn conversations

### Tool-Based Search Pattern

**Key insight**: Claude autonomously decides when to search, not the application.

The system provides Claude with a `search_course_content` tool definition. Claude:
1. Analyzes the user query
2. Decides if search is needed (general knowledge vs. course-specific)
3. Calls tool with appropriate parameters (query, course_name, lesson_number)
4. Receives formatted results
5. Synthesizes final answer

This pattern keeps search logic in AI reasoning, not hardcoded rules.

## Key Configuration Parameters

**Location**: `backend/config.py`

```python
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 800          # Characters per chunk
CHUNK_OVERLAP = 100       # Character overlap between chunks
MAX_RESULTS = 5           # Max search results returned
MAX_HISTORY = 2           # Max conversation exchanges stored
CHROMA_PATH = "./chroma_db"  # Persistent vector store location
```

**AI Generator settings** (`ai_generator.py`):
- Temperature: 0 (deterministic responses)
- Max tokens: 800
- System prompt emphasizes brevity and educational value

## Important Implementation Details

### Adding New Documents

Place `.txt` files in `docs/` folder with the expected format. On next server restart, they'll be automatically processed and indexed. The system skips documents with duplicate course titles.

To force rebuild:
```python
# In app.py startup_event
rag_system.add_course_folder(docs_path, clear_existing=True)
```

### Adding New Tools

1. Create a class inheriting from `Tool` in `search_tools.py`
2. Implement `get_tool_definition()` and `execute()` methods
3. Register with ToolManager in `rag_system.py:__init__`
4. Claude will automatically have access to the new tool

### Data Models

**Location**: `backend/models.py`

- `Course`: Represents a course with title, link, instructor, and lessons list
- `Lesson`: Individual lesson with number, title, and optional link
- `CourseChunk`: Text chunk with course context (course_title, lesson_number, chunk_index)

These models ensure type safety and consistent data structure throughout the pipeline.

## Critical Architectural Decisions

### Why Two API Calls to Claude?

The AI Generator makes two sequential API calls when tools are used:

1. **First call**: Claude receives the query + tool definitions, decides to use `search_course_content`
2. **Tool execution**: System runs the search and gets results
3. **Second call**: Claude receives the search results and generates the final answer

This pattern is required by Anthropic's tool use API - the tool results must be sent back as a user message for Claude to synthesize the final response.

### Why Sentence-Based Chunking?

The document processor uses sentence boundaries (not fixed character splits) to:
- Preserve semantic coherence within chunks
- Avoid cutting sentences mid-way
- Maintain context through 100-character overlap

This improves retrieval quality compared to naive character-based splitting.

### ChromaDB Persistence

The vector database persists to disk at `./chroma_db/`. This means:
- Documents are indexed once and survive server restarts
- No need to re-process documents on every startup
- Deduplication prevents duplicate indexing

To reset the database, delete the `chroma_db/` directory.

## Frontend Architecture

**Location**: `frontend/` directory

- **Vanilla JavaScript** (no framework) - keeps it simple and lightweight
- **Marked.js** for Markdown rendering of AI responses
- **Session management**: Stores `session_id` in memory, creates new session on page load
- **Loading states**: Shows animated dots while waiting for API response
- **Source attribution**: Displays collapsible `<details>` element with sources

Key files:
- `index.html`: Layout with sidebar (course stats, suggested questions) and chat area
- `script.js`: API calls, message rendering, event handling
- `style.css`: Responsive design with CSS variables

## Troubleshooting

### ChromaDB Issues

If you see ChromaDB errors on startup:
```bash
# Delete the database and restart
rm -rf backend/chroma_db
./run.sh
```

### Missing API Key

Error: `anthropic.APIConnectionError` or `401 Unauthorized`
- Ensure `.env` file exists in root directory
- Verify `ANTHROPIC_API_KEY` is set correctly
- Restart the server after adding the key

### Port Already in Use

If port 8000 is occupied:
```bash
# Find and kill the process
lsof -ti:8000 | xargs kill -9

# Or use a different port
cd backend
uv run uvicorn app:app --reload --port 8001
```

