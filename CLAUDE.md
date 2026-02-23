# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) chatbot system that answers questions about DeepLearning.AI course materials. It uses ChromaDB for vector storage, Anthropic's Claude API with tool calling, and provides a web interface for conversational queries.

## Development Commands

### Setup
```bash
# Install dependencies (uses uv package manager)
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Running the Application
```bash
# Quick start (recommended)
./run.sh

# Manual start (from project root)
cd backend && uv run uvicorn app:app --reload --port 8000

# Access points
# - Web UI: http://localhost:8000
# - API docs: http://localhost:8000/docs
```

### Adding Course Documents
Place text files in the `docs/` folder. Files are automatically loaded on server startup. See "Document Format Requirements" below.

## Architecture

### RAG Pipeline Flow

The system implements a **tool-based RAG architecture** where Claude decides when to search:

```
User Query → FastAPI → RAGSystem → AIGenerator → Claude API
                                                      ↓
                                            (Claude calls tool)
                                                      ↓
                                    SearchTool → VectorStore → ChromaDB
                                                      ↓
                                         (search results returned)
                                                      ↓
                                            Claude synthesizes response
                                                      ↓
                                          SessionManager stores history
                                                      ↓
                                            Return answer + sources
```

**Key architectural decision**: Claude has search as a *callable tool*, not an always-on feature. The system prompt instructs Claude to call `search_course_content` when needed, making searches contextual rather than automatic.

### Dual Collection Strategy

ChromaDB uses **two separate collections** with different purposes:

1. **`course_catalog`** (vector_store.py:51)
   - Purpose: Fuzzy matching of course names for search filtering
   - Documents: Course titles only
   - Metadata: Full course info (instructor, links, lesson metadata)
   - IDs: Course title (serves as unique identifier)
   - Usage: When user specifies a course name, semantic search finds the best match

2. **`course_content`** (vector_store.py:52)
   - Purpose: Actual semantic search of course material
   - Documents: Text chunks with enriched context
   - Metadata: `{course_title, lesson_number, chunk_index}`
   - IDs: `"{course_title_snake_case}_{chunk_index}"`
   - Usage: Primary search collection for answering queries

This separation enables fuzzy course name matching (e.g., "MCP" → "MCP: Build Rich-Context AI Apps") before searching content.

### Component Relationships

**rag_system.py** is the orchestration layer that:
- Coordinates all components (VectorStore, AIGenerator, SearchTool, SessionManager)
- Manages document ingestion and deduplication
- Handles query flow from input to response

**ai_generator.py** handles Claude API interactions:
- Builds API requests with system prompt, history, and tool definitions
- Processes tool calls from Claude
- Extracts responses and sources from Claude's output
- Uses temperature=0 for deterministic responses

**session_manager.py** maintains conversation state:
- Thread-safe session storage with dict-based in-memory storage
- Automatically trims history to last `MAX_HISTORY` exchanges (default: 2)
- Each session tracks conversation context for multi-turn queries

### Text Chunking Strategy

**document_processor.py:25-91** implements sentence-aware chunking:

1. **Sentence splitting** using regex that handles abbreviations (Mr., Dr., etc.)
2. **Chunk building** up to 800 characters per chunk
3. **Overlap calculation** - 100 characters shared between consecutive chunks by counting backwards from chunk end
4. **Context enrichment** - First chunk of each lesson prefixed with `"Lesson N content: ..."`, last lesson chunks include course title

This preserves semantic boundaries and context across chunk boundaries.

## Document Format Requirements

Course documents must follow this structure:

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

**Processing behavior**:
- Lines 1-3: Metadata extraction with regex matching
- Remaining lines: Parsed for `^Lesson\s+(\d+):\s*(.+)$` markers
- Content between lesson markers becomes lesson content
- Lesson links (optional) must appear immediately after lesson headers
- If no lesson markers found, entire file treated as single document

## Configuration

All configuration in **backend/config.py** as a dataclass:

- `CHUNK_SIZE`: 800 characters (sentence-aware, not hard cutoff)
- `CHUNK_OVERLAP`: 100 characters between chunks
- `MAX_RESULTS`: 5 search results per query
- `MAX_HISTORY`: 2 conversation exchanges retained
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (384-dimensional embeddings)
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"
- `CHROMA_PATH`: "./chroma_db" (persistent vector storage)

## Important Patterns

### Document Deduplication
**rag_system.py:76** checks existing course titles before processing. If a course with the same title already exists in the vector store, it's skipped. To reload a course, clear the vector store first.

### Tool Definition
**search_tools.py** defines the `search_course_content` tool with three parameters:
- `query` (required): What to search for
- `course_name` (optional): Fuzzy-matched against course_catalog
- `lesson_number` (optional): Filter to specific lesson

The system prompt instructs Claude to use this tool strategically, not for every query.

### Search Filtering
**vector_store.py:118-133** builds ChromaDB filters:
- Both course + lesson: `{"$and": [{"course_title": "..."}, {"lesson_number": N}]}`
- Course only: `{"course_title": "..."}`
- Lesson only: `{"lesson_number": N}`
- Neither: No filter (search all content)

### Session Management
Sessions are created implicitly if no `session_id` is provided. Frontend passes `session_id` back to maintain conversation context. Sessions are stored in-memory (lost on restart).

## Key Files

- **app.py**: FastAPI application, startup document loading, API endpoints
- **rag_system.py**: Main orchestration, coordinates all components
- **vector_store.py**: ChromaDB wrapper, dual collection management, search logic
- **ai_generator.py**: Claude API integration, tool call handling
- **document_processor.py**: Metadata extraction, chunking algorithm
- **search_tools.py**: Tool definitions for Claude function calling
- **session_manager.py**: Conversation history management
- **config.py**: Centralized configuration
- **models.py**: Pydantic data models (Course, Lesson, CourseChunk)

## Frontend

Vanilla JavaScript application (frontend/) with no framework dependencies:
- **index.html**: Chat UI structure
- **script.js**: API communication, message handling
- **style.css**: Responsive styling

Frontend communicates with backend via `/api/query` POST endpoint, receives responses with `{answer, sources, session_id}`.

## Extending the System

### Adding New Course Sources
Place files in `docs/` folder matching the required format. Supported extensions: `.txt`, `.pdf`, `.docx`. Server automatically loads on startup.

### Modifying Chunking Behavior
Edit `CHUNK_SIZE` and `CHUNK_OVERLAP` in config.py. Larger chunks provide more context but reduce granularity. More overlap improves context preservation but increases storage.

### Changing Search Results1
Modify `MAX_RESULTS` in config.py to return more/fewer chunks per search. More results give Claude more context but increase token usage.

### Adjusting Conversation Memory
Change `MAX_HISTORY` in config.py. Higher values retain more context but increase token costs. Each exchange = 2 messages (user + assistant).
