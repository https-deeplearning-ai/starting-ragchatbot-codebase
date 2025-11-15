# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running Commands

**IMPORTANT:** This project uses `uv` as the package manager. **Always use `uv` commands - never use `pip` directly.**

### Start the Application
```bash
./run.sh
```
This starts the FastAPI server on port 8000 with auto-reload enabled. The application will:
1. Load course documents from `docs/` folder
2. Process them into 800-char chunks with 100-char overlap
3. Create/load ChromaDB embeddings (first run downloads 90MB embedding model)
4. Serve the web interface at http://localhost:8000

The `run.sh` script uses `uv run` internally.

### Manual Start (Development)
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Install Dependencies
```bash
uv sync
```

### Add New Dependencies
```bash
# Add a new package
uv add package-name

# Add a dev dependency
uv add --dev package-name
```

### Run Python Scripts
```bash
# Always use uv run to execute Python code
uv run python script.py

# NOT: python script.py
# NOT: pip install ...
```

### Environment Setup
Create `.env` file with:
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

## Architecture Overview

### RAG System Flow (Tool-Based Architecture)

This is a **tool-based RAG system** where Claude decides when to search, not a traditional "always search" RAG.

**Query Processing Flow:**
1. User query → FastAPI endpoint (`/api/query`)
2. RAG System orchestrates the flow
3. **First Claude API call**: Claude receives query + tool definition, decides if search is needed
4. If search needed: Tool execution → Vector search → Format results
5. **Second Claude API call**: Claude receives search results, synthesizes final answer
6. Response + sources returned to frontend

**Key Insight:** There are **two Claude API calls per query** - one for decision-making, one for synthesis.

### Component Architecture

**Frontend** (`frontend/`)
- Vanilla JS (no framework)
- Uses `marked.js` for markdown rendering
- Session-based conversation tracking
- Displays collapsible source citations

**Backend** (`backend/`)
- **app.py**: FastAPI server, REST endpoints, startup document loading
- **rag_system.py**: Main orchestrator - coordinates all components
- **ai_generator.py**: Claude API wrapper with tool calling support
  - System prompt defines search behavior (one search max, no meta-commentary)
  - Handles two-phase tool execution (request → execute → synthesize)
- **vector_store.py**: ChromaDB interface with two collections
  - `course_catalog`: For fuzzy course name matching (e.g., "MCP" → full title)
  - `course_content`: Actual content chunks for semantic search
- **document_processor.py**: Parses structured course documents into chunks
  - Sentence-based chunking (preserves semantic boundaries)
  - Adds context prefixes: "Course X Lesson Y content: ..."
- **search_tools.py**: Tool abstraction layer
  - `CourseSearchTool`: Implements search with course/lesson filtering
  - `ToolManager`: Registers and routes tool calls from Claude
- **session_manager.py**: Conversation history (max 2 exchanges by default)
- **config.py**: Centralized configuration (see below)

### Data Models (`models.py`)

**Important:** `Course.title` is used as the unique identifier throughout the system.

- **Course**: Contains title (ID), instructor, link, and list of Lessons
- **Lesson**: Contains lesson_number, title, and link
- **CourseChunk**: Contains content, course_title (FK), lesson_number, chunk_index

### Vector Store Design

**Two-Collection Architecture:**
1. **course_catalog** collection:
   - Purpose: Fuzzy course name resolution
   - Documents: "Course: {title} taught by {instructor}" + lesson entries
   - Used when user says "MCP course" → resolves to full title

2. **course_content** collection:
   - Purpose: Semantic search of actual content
   - Documents: Text chunks with context prefixes
   - Metadata: course_title, lesson_number, chunk_index, links
   - Filtering: Can filter by exact course_title AND/OR lesson_number

**Search Flow:**
1. If course_name provided: Query `course_catalog` to resolve fuzzy name
2. Build ChromaDB filter: `{"$and": [{"course_title": "X"}, {"lesson_number": Y}]}`
3. Query `course_content` with semantic search + filters
4. Return top 5 chunks by cosine similarity

### Document Format

Course documents in `docs/` must follow this structure:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[content...]

Lesson 1: [title]
Lesson Link: [url]
[content...]
```

The parser (`document_processor.py`) extracts this metadata and creates chunks with context.

### Configuration (`backend/config.py`)

Key settings to be aware of:
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514" (Claude Sonnet 4)
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (384-dim vectors)
- `CHUNK_SIZE`: 800 chars (with CHUNK_OVERLAP: 100 chars)
- `MAX_RESULTS`: 5 search results returned to Claude
- `MAX_HISTORY`: 2 conversation exchanges kept in context
- `CHROMA_PATH`: "./chroma_db" (persistent vector storage)

### AI System Prompt Behavior

The system prompt in `ai_generator.py` defines critical behavior:
- **Use search tool ONLY for course-specific questions**
- **One search per query maximum** (prevents multiple searches)
- **No meta-commentary** (no "based on the search results" phrases)
- Responses must be: brief, educational, clear, example-supported

### Session Management

Sessions track conversation history:
- Session ID created on first query (e.g., "session_1")
- Stores last `MAX_HISTORY * 2` messages (user + assistant pairs)
- History formatted as: "User: ...\nAssistant: ...\n..." for context
- Appended to system prompt on subsequent queries in same session

### API Endpoints

**POST /api/query**
- Request: `{ "query": "...", "session_id": "session_1" (optional) }`
- Response: `{ "answer": "...", "sources": ["..."], "session_id": "..." }`
- Creates session if not provided

**GET /api/courses**
- Response: `{ "total_courses": 4, "course_titles": ["..."] }`
- Used by frontend sidebar

### ChromaDB Persistence

- First run: Downloads embedding model, creates collections, processes documents (~30-60 seconds)
- Subsequent runs: Loads existing ChromaDB from `./chroma_db` (fast startup)
- Documents only reprocessed if course title doesn't exist in catalog
- To rebuild: Delete `./chroma_db` folder and restart

### Development Notes

**Adding New Documents:**
1. Place `.txt`, `.pdf`, or `.docx` files in `docs/` folder
2. Follow the document format structure above
3. Restart server - documents auto-loaded on startup
4. Check logs for: "Added new course: X (Y chunks)"

**Modifying Chunk Size:**
- Edit `config.py`: `CHUNK_SIZE` and `CHUNK_OVERLAP`
- Delete `./chroma_db` folder to force reprocessing
- Restart application

**Debugging Search:**
- Search tool tracks sources in `last_sources` attribute
- Sources shown in UI as collapsible section
- Check `vector_store.py` for filter logic

**Conversation Context:**
- Modify `MAX_HISTORY` in `config.py` to change context window
- History is string-formatted and prepended to system prompt
- Trade-off: More history = more context but higher token usage

### Tool-Based vs Traditional RAG

**This system is NOT a traditional RAG** where every query triggers a search. Instead:
- Claude analyzes each query and decides if search is warranted
- General knowledge questions answered without search
- Course-specific questions trigger tool use
- This reduces unnecessary vector searches and improves response quality

### Frontend-Backend Contract

**Frontend maintains:**
- Current session_id in memory
- Sends with each query for conversation continuity

**Backend returns:**
- answer: The synthesized response from Claude
- sources: List of "Course Title - Lesson N" strings for UI
- session_id: Same or newly created session ID

**Source Tracking:**
- Search tool stores sources during execution
- RAG system retrieves after AI generation completes
- Sources reset after each query to prevent leakage
