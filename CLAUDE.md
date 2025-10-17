# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Retrieval-Augmented Generation (RAG) chatbot system that uses Anthropic's Claude with tool-based search over course materials stored in ChromaDB. The system indexes course transcripts, performs semantic search, and generates context-aware responses.

## Development Setup

**Prerequisites:** Python 3.13+, uv package manager, Anthropic API key

**Installation:**
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Set up environment
echo "ANTHROPIC_API_KEY=your_key_here" > .env
```

**Running the application:**
```bash
# Quick start
./run.sh

# Manual start (from backend/)
cd backend
uv run uvicorn app:app --reload --port 8000

# Access at http://localhost:8000
```

## Architecture Overview

### Core Design: Tool-Based RAG

Unlike traditional RAG systems that always retrieve context, this system uses **Anthropic tool calling** where Claude decides whether to search course materials or answer from general knowledge. This happens in two API calls:

1. **First call**: Claude receives user query + tool definition, decides whether to use `search_course_content` tool
2. **Second call** (if tool used): Claude receives search results as tool output, synthesizes final answer

See `backend/ai_generator.py:43-135` for the two-call pattern implementation.

### Data Flow Architecture

**Indexing Pipeline** (startup):
```
/docs/*.txt → DocumentProcessor → Course + CourseChunks → VectorStore → ChromaDB
```

**Query Pipeline** (runtime):
```
User Query → RAGSystem → AIGenerator → Claude (decides to search)
          ↓
ChromaDB semantic search ← ToolManager.execute_tool()
          ↓
Claude (synthesizes answer) → Response + Sources
```

### Two-Collection ChromaDB Strategy

The vector store uses two separate collections (`backend/vector_store.py:51-52`):

1. **`course_catalog`**: Stores course metadata (title, instructor, lessons). Used for fuzzy course name matching (e.g., "MCP" → "MCP: Build Rich-Context AI Apps with Anthropic")

2. **`course_content`**: Stores 800-character text chunks with embeddings. Used for semantic content search.

This separation enables:
- Partial course name queries (search catalog first, then filter content)
- Course-level vs content-level search strategies
- Efficient lesson filtering without scanning all content

### Document Processing Details

**File format** (`backend/document_processor.py:97-259`):
- Expected structure: `Course Title:`, `Course Link:`, `Course Instructor:` headers
- Lesson markers: `Lesson N: Title` followed by optional `Lesson Link:`
- Content extracted per-lesson, then chunked

**Chunking strategy** (`backend/document_processor.py:25-91`):
- Sentence-based splitting (800 chars, 100 char overlap)
- Preserves semantic boundaries (doesn't split mid-sentence)
- Adds context prefix: `"Course {title} Lesson {num} content: {text}"`
- Overlap ensures no information loss at chunk boundaries

### Session Management

Conversation history is maintained per session (`backend/session_manager.py`):
- Sliding window: Last 2 exchanges (4 messages max) kept in memory
- Config: `MAX_HISTORY = 2` in `backend/config.py:22`
- History injected into system prompt for follow-up question context

### Configuration

All tunable parameters in `backend/config.py`:
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (384-dimensional vectors)
- `CHUNK_SIZE`: 800 chars
- `CHUNK_OVERLAP`: 100 chars
- `MAX_RESULTS`: 5 (top-k search results)
- `MAX_HISTORY`: 2 (conversation exchanges to remember)

## Key Implementation Patterns

### Tool Definition and Execution

Tools are defined using Anthropic's tool schema (`backend/search_tools.py:27-50`). The `ToolManager` class:
- Registers tools dynamically
- Executes tools by name with kwargs
- Tracks sources from last search for UI display

When adding new tools, implement the `Tool` ABC and register with `ToolManager.register_tool()`.

### AI System Prompt Strategy

The system prompt (`backend/ai_generator.py:8-30`) enforces:
- **One search per query maximum** (cost control)
- Only search for course-specific questions (use general knowledge otherwise)
- No meta-commentary in responses (no "based on search results...")
- Brief, concise, educational tone

This prompt is critical for controlling Claude's tool usage behavior.

### Vector Search with Filters

The `VectorStore.search()` method (`backend/vector_store.py:61-100`) supports:
- Course name filtering (with fuzzy matching via `_resolve_course_name()`)
- Lesson number filtering
- Combined filters using ChromaDB's `$and` operator

Filters are built dynamically based on tool parameters.

### Context Injection

Each chunk includes metadata that becomes part of search results:
```python
# Chunk content format:
"Course {title} Lesson {num} content: {actual_text}"

# Metadata stored separately:
{
  "course_title": "...",
  "lesson_number": 0,
  "chunk_index": 15
}
```

This dual approach enables both semantic search (content) and provenance tracking (metadata).

## Important Data Locations

- **Vector DB**: `backend/chroma_db/` (persistent ChromaDB storage)
- **Course materials**: `/docs/*.txt` (loaded on startup)
- **Sessions**: In-memory only (cleared on restart)

To rebuild the vector index: delete `backend/chroma_db/` directory and restart.

## Frontend-Backend Contract

**POST `/api/query`**:
```json
Request: { "query": "string", "session_id": "string | null" }
Response: { "answer": "string", "sources": ["string"], "session_id": "string" }
```

**GET `/api/courses`**:
```json
Response: { "total_courses": int, "course_titles": ["string"] }
```

Sources are formatted as: `"{course_title} - Lesson {num}"` for UI display.

## Testing/Debugging

To test the search tool directly:
```python
# From backend/ directory
uv run python -c "
from vector_store import VectorStore
from config import config
store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, 5)
results = store.search('your query here')
print(results.documents)
"
```

To add new courses: place `.txt` files in `/docs` with proper format, restart server (auto-indexes on startup).
