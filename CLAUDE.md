# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

Requires Python 3.13+ and `uv`. On Windows, use Git Bash. Always use `uv` to run Python and manage all dependencies — never use `pip` directly.

```bash
# Install dependencies
uv sync

# Copy and populate the environment file
cp .env.example .env   # then add ANTHROPIC_API_KEY

# Start the server (from repo root)
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

App runs at `http://localhost:8000`. On startup, course documents in `/docs` are automatically loaded into ChromaDB (skipping any already indexed).

## Architecture

This is a full-stack RAG (Retrieval-Augmented Generation) application. The FastAPI backend serves both the API and the static frontend from a single port.

### Query Flow

1. Frontend (`frontend/script.js`) POSTs `{ query, session_id }` to `/api/query`
2. `app.py` routes to `RAGSystem.query()`, creating a session if needed
3. `RAGSystem` fetches conversation history from `SessionManager` and calls `AIGenerator.generate_response()` with the `search_course_content` tool available
4. **First Claude call** — Claude decides to answer directly or invoke the search tool
5. If tool use: `CourseSearchTool` calls `VectorStore.search()`, which optionally resolves a fuzzy course name via semantic search on the `course_catalog` collection, then queries the `course_content` collection using `sentence-transformers` embeddings
6. **Second Claude call** — Claude synthesizes a final answer from the retrieved chunks
7. Sources (course + lesson labels) and the answer are returned to the frontend

### Key Design Decisions

- **Two ChromaDB collections**: `course_catalog` (course-level metadata for fuzzy name resolution) and `course_content` (chunked lesson text for semantic search)
- **Agentic tool loop**: Claude decides whether to search; the tool call and result are injected back into the message thread before a second API call forces a final text response
- **Session history** is passed in the system prompt as formatted text (not as message-role history), capped at `MAX_HISTORY=2` exchanges
- **Course title is the unique ID** in ChromaDB — re-ingesting the same course is a no-op
- **ChromaDB persists** to `backend/chroma_db/`. To force a full re-index, delete that directory or call `vector_store.clear_all_data()`

### Extending the Search Tool

New tools should implement the `Tool` ABC in `backend/search_tools.py` (implement `get_tool_definition()` and `execute()`), then register with `ToolManager.register_tool()` in `RAGSystem.__init__()`. The tool definition must follow the Anthropic tool schema format.

### Document Format

Course `.txt` files in `/docs` must follow this structure:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>
Lesson 0: <lesson title>
Lesson Link: <url>
<lesson content>
Lesson 1: <lesson title>
...
```

### Configuration (`backend/config.py`)

| Setting | Default | Purpose |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model for generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer for embeddings |
| `CHUNK_SIZE` | `800` | Max characters per chunk |
| `CHUNK_OVERLAP` | `100` | Character overlap between chunks |
| `MAX_RESULTS` | `5` | Max chunks returned per search |
| `MAX_HISTORY` | `2` | Conversation exchanges retained |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence directory |
