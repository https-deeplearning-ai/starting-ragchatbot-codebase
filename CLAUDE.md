# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Install dependencies
uv sync

# Run a specific backend file directly (useful for quick testing)
cd backend && uv run python <file>.py
```

The app is served at `http://localhost:8000`. FastAPI's auto-generated API docs are at `http://localhost:8000/docs`.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot that answers questions about course materials. FastAPI serves both the API and the static frontend from a single process.

**Request flow:**
1. Frontend (`frontend/script.js`) POSTs `{ query, session_id }` to `/api/query`
2. `app.py` routes to `RAGSystem.query()` — the main orchestrator in `rag_system.py`
3. `RAGSystem` fetches conversation history from `SessionManager`, then calls `AIGenerator`
4. `AIGenerator` calls Claude (claude-sonnet-4) with a `search_course_content` tool available
5. If Claude invokes the tool, `CourseSearchTool` runs a semantic search against ChromaDB and returns formatted chunks
6. Claude makes a second API call to synthesize a final answer from the retrieved chunks
7. Sources and response are returned up the chain to the frontend

**Key design decisions:**
- Claude drives retrieval via tool use — it decides whether to search and what to search for, rather than always retrieving before generating
- Two ChromaDB collections: `course_catalog` (one entry per course, used for fuzzy course-name resolution) and `course_content` (chunked text, used for semantic search)
- Conversation history is stored in-memory in `SessionManager` — it is lost on server restart
- The session ID is minted server-side on first request and returned to the frontend, which holds it in `currentSessionId` for the rest of the browser session

**Document format** (`docs/*.txt`):
```
Course Title: ...
Course Link: ...
Course Instructor: ...
Lesson 1: Title
Lesson Link: ...
<lesson content>
```
`DocumentProcessor` parses this format and chunks each lesson's content into ~800-character overlapping segments. Course documents are loaded at startup via `app.py`'s `startup_event`.

**Configuration** (`backend/config.py`):
- `ANTHROPIC_MODEL` — Claude model used for generation
- `EMBEDDING_MODEL` — SentenceTransformer model used for ChromaDB embeddings (`all-MiniLM-L6-v2`)
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — control document chunking
- `MAX_HISTORY` — number of conversation exchanges retained per session
- `CHROMA_PATH` — local path for persisted ChromaDB data
