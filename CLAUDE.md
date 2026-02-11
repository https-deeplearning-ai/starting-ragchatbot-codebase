# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application

**Quick Start:**
```bash
./run.sh
```

**Manual Start:**
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

**Install Dependencies:**
```bash
uv sync
```

**Environment Setup:**
Create a `.env` file in the project root with:
```
ANTHROPIC_API_KEY=your_api_key_here
```

**Windows Users:** Use Git Bash to run shell commands and scripts.

### Data Management

**Clear ChromaDB Data:**
Delete the `./chroma_db` directory to start fresh. On next startup, documents will be re-indexed from `../docs`.

**Add New Course Documents:**
Place `.txt`, `.pdf`, or `.docx` files in the `docs/` directory. Documents are auto-loaded on startup with deduplication by course title.

### Access Points
- Web Interface: http://localhost:8000
- API Documentation (Swagger): http://localhost:8000/docs
- Health Check: http://localhost:8000/api/courses

## Architecture Overview

### RAG Pipeline with Tool-Based AI

This is a Retrieval-Augmented Generation (RAG) chatbot with a two-stage Claude API interaction pattern:

1. **Stage 1**: User query sent to Claude with tool definitions (tool-based approach, not retrieval-then-generate)
2. **Tool Decision**: Claude decides if search is needed and calls `search_course_content` tool with parameters
3. **Tool Execution**: System executes semantic search via ChromaDB and formats results
4. **Stage 2**: Tool results sent back to Claude for synthesis into final answer

**Key Insight**: The AI decides when to search rather than always searching first. This reduces unnecessary searches for general questions.

### Component Interaction Flow

```
FastAPI (app.py)
    ↓
RAGSystem (rag_system.py) - orchestrates everything
    ↓
AIGenerator (ai_generator.py) - manages Claude API calls with tools
    ↓
ToolManager (search_tools.py) - dispatches tool execution
    ↓
CourseSearchTool → VectorStore (vector_store.py) → ChromaDB
```

### Dual-Collection Vector Store Design

The `VectorStore` uses **two separate ChromaDB collections**:

1. **`course_catalog`**: Stores course metadata (title, instructor, lessons as JSON)
   - Used for semantic course name resolution (fuzzy matching)
   - Example: "Computer Use" matches "Building Towards Computer Use with Anthropic"

2. **`course_content`**: Stores actual text chunks with metadata
   - Used for content search with precise filtering
   - Metadata: `course_title`, `lesson_number`, `chunk_index`

**Why Two Collections?**
This enables a two-stage search: first resolve fuzzy course names semantically, then filter content precisely by resolved title.

### Session Management Pattern

Sessions are **in-memory only** (not persisted):
- Session IDs use simple counter: `session_1`, `session_2`, etc. (see session_manager.py:18-23)
- `max_history=2` means last 2 exchanges (4 messages total: 2 user + 2 assistant)
- History formatted as plain text and injected into system prompt
- Sessions created on-demand if not provided in request
- No cleanup/TTL mechanism - sessions persist for app lifetime and reset on server restart

### Source Tracking Mechanism

Sources tracked via **side effects**, not return values:
1. `CourseSearchTool.execute()` stores formatted sources in `self.last_sources`
2. `ToolManager.get_last_sources()` retrieves from any tool with `last_sources` attribute
3. `RAGSystem.query()` extracts sources after response generation
4. `tool_manager.reset_sources()` clears to prevent stale sources

This keeps tool execution logic clean while enabling UI source display.

## Critical Implementation Details

### Document Format Convention

Course documents **must** follow this exact format (parsed via regex):
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[lesson content]

Lesson 1: [next title]
...
```

Lesson detection regex: `r'^Lesson\s+(\d+):\s*(.+)$'`

### Text Chunking Strategy

**Sentence-aware chunking** (not token-based):
- Target: 800 characters per chunk with 100 character overlap
- Smart sentence splitting handles abbreviations: `(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+(?=[A-Z])`
- Overlap calculated backwards from chunk end (last N sentences)
- First chunk of each lesson gets prefix: `"Lesson N content: {chunk}"`

**Known Issue**: Last lesson uses `"Course {title} Lesson N content:"` but earlier lessons use `"Lesson N content:"` (document_processor.py:186 vs 234)

### ChromaDB Usage Patterns

**ID Generation:**
- Course metadata: `course.title` (title is unique identifier)
- Content chunks: `f"{course_title.replace(' ', '_')}_{chunk_index}"`

**Filtering:**
ChromaDB `where` parameter supports:
```python
{"course_title": "exact_match"}  # Single filter
{"$and": [{"course_title": ...}, {"lesson_number": ...}]}  # Combined
```

**Result Structure:**
Results are nested lists (first index is batch):
```python
results['documents'][0]  # List of document strings
results['metadatas'][0]  # List of metadata dicts
results['distances'][0]  # List of similarity scores
```

### Anthropic SDK Tool Usage

**Tool Call Pattern:**
```python
# First call with tools
response = client.messages.create(
    tools=[tool_definition],
    tool_choice={"type": "auto"}
)

# If stop_reason == "tool_use":
for block in response.content:
    if block.type == "tool_use":
        result = execute_tool(block.name, **block.input)

# Second call with tool results
messages.append({"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": block.id, "content": result}
]})
response = client.messages.create(messages=messages)  # No tools
```

**Configuration:**
- Model: `claude-sonnet-4-20250514`
- Temperature: `0` (deterministic for Q&A)
- Max tokens: `800`

## Configuration Reference

Key settings in `config.py`:
- `CHUNK_SIZE`: 800 characters
- `CHUNK_OVERLAP`: 100 characters
- `MAX_RESULTS`: 5 search results per query
- `MAX_HISTORY`: 2 exchanges (4 messages total)
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (384 dimensions)
- `CHROMA_PATH`: "./chroma_db"

## Extension Points

**Adding Tools:** Extend the `Tool` base class (search_tools.py:6-17) and register in `RAGSystem.__init__()` via `tool_manager.register_tool()`.

**Search Filters:** Modify `VectorStore._build_filter()` (vector_store.py:118-133) to add metadata filters. All searches route through this method.

**Document Format:** Update regex in `DocumentProcessor.process_course_document()` (document_processor.py:97-260). Current pattern requires "Course Title:", "Course Link:", "Course Instructor:", then "Lesson N:" sections.

## Startup Sequence

1. Load `.env` file (python-dotenv)
2. Create `Config` from environment variables
3. Initialize FastAPI with CORS/TrustedHost middleware
4. Create `RAGSystem` which initializes:
   - `DocumentProcessor` (chunking config)
   - `VectorStore` (creates ChromaDB persistent client at `./chroma_db`)
   - `AIGenerator` (Anthropic client)
   - `SessionManager` (in-memory sessions)
   - `ToolManager` with `CourseSearchTool` registered
5. On startup event: `add_course_folder("../docs")` loads initial documents
6. Documents checked against existing course titles (deduplication)
7. New courses processed: metadata → `course_catalog`, chunks → `course_content`

## Important Files

- `app.py:88-99` - Startup event that loads initial documents
- `rag_system.py:102-140` - Main query orchestration logic
- `ai_generator.py:89-135` - Tool execution loop handling
- `vector_store.py:61-100` - Two-stage search with course name resolution
- `search_tools.py:88-114` - Result formatting and source tracking
- `document_processor.py:97-260` - Document parsing and chunking
- `config.py` - All configuration constants

## Dependencies

- **ChromaDB 1.0.15**: Persistent vector database (stores to disk)
- **Anthropic SDK 0.58.2**: Claude API with tool support
- **sentence-transformers 5.0.0**: Embedding model (wrapped by ChromaDB)
- **FastAPI 0.116.1**: Web framework
- **uvicorn 0.35.0**: ASGI server

Python 3.13+ required.
