# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Course Materials RAG System** - A full-stack web application that answers questions about course materials using Retrieval-Augmented Generation (RAG). Users submit queries through a web interface, the backend searches a vector database of course content, and Claude synthesizes results into intelligent answers.

**Key Technologies:**
- Backend: FastAPI (Python 3.13+)
- Frontend: Vanilla JavaScript + HTML/CSS
- Vector DB: ChromaDB with SentenceTransformer embeddings
- AI: Anthropic Claude API (claude-haiku-4-5 by default, upgradeable to Sonnet or Opus)
- Package Manager: `uv`

---

## Architecture

### High-Level Flow

```
User Query (Frontend) 
  → FastAPI REST endpoint (/api/query)
  → RAG System Orchestrator
  → Claude with Tool Use (decides: search needed or direct answer?)
  → Optional: Vector Search + Tool Execution
  → Claude synthesizes final answer
  → QueryResponse (answer, sources, session_id) back to frontend
```

### Core Components

**Backend (python):**
- `app.py` - FastAPI server, REST endpoints, CORS/middleware setup
- `rag_system.py` - Orchestrates query flow, coordinates all RAG components
- `ai_generator.py` - Claude API integration, handles tool use decisions and multi-turn conversations
- `search_tools.py` - Tool definitions (CourseSearchTool) and ToolManager for execution
- `vector_store.py` - ChromaDB operations, semantic search with filters
- `session_manager.py` - In-memory conversation history per session
- `document_processor.py` - Loads documents, creates chunks for vector store
- `config.py` - Configuration from environment variables
- `models.py` - Pydantic models (Course, Lesson, CourseChunk)

**Frontend (javascript):**
- `script.js` - Chat UI logic, API calls, session management, message display
- `index.html` - Chat interface layout, course stats section
- `style.css` - Styling for chat, messages, sources

**Supporting:**
- `docs/` - Directory for course documents (PDF, DOCX, TXT)
- `chroma_db/` - ChromaDB persistent storage (created on startup)
- `.env` - API key and configuration
- `run.sh` - Startup script

### Important Design Patterns

**1. Tool-Based Search (Claude Decides)**
- Claude receives tool definition for `search_course_content`
- Claude decides whether to use the tool based on query type
- General knowledge → direct answer (1 API call)
- Course-specific → search + synthesize (2 API calls)
- System prompt guides this behavior (see ai_generator.py SYSTEM_PROMPT)

**2. Session-Based Conversation**
- Sessions created on-demand (session_1, session_2, etc.)
- Conversation history maintained in SessionManager (in-memory, limited to MAX_HISTORY)
- Frontend stores currentSessionId in browser memory
- Each query includes session_id to provide context to Claude

**3. Vector Search with Filters**
- Two ChromaDB collections: course_catalog (metadata) + course_content (actual material)
- Course name resolution: semantic search to find exact course title
- Filtering: Multi-condition filters (course_title AND lesson_number)
- Embedding model: all-MiniLM-L6-v2 (sentence-transformers)

**4. Multi-Turn API Calls**
- First call: User query + tools → Claude decides on action
- Tool execution: Run search, format results
- Second call: Original query + tool results → Claude synthesizes answer
- Only single response sent to frontend (multi-turn internal to backend)

---

## Common Development Commands

**IMPORTANT:** Always use `uv` to run commands and manage dependencies. Do **not** use `pip` directly in this project.

### Setup & Installation

```bash
# Install dependencies (first time)
uv sync

# Update dependencies
uv lock
```

### Running the Application

```bash
# Quick start (from project root)
chmod +x run.sh
./run.sh

# OR manual start (from project root)
cd backend
uv run uvicorn app:app --reload --port 8000
```

The app runs on `http://localhost:8000`
- Web Interface: `http://localhost:8000`
- Swagger API Docs: `http://localhost:8000/docs`

### Development Workflow

```bash
# Make code changes in frontend or backend
# Changes auto-reload with --reload flag
# Refresh browser to see frontend changes
# API changes reflect immediately

# To add course documents:
# 1. Place PDF/DOCX/TXT files in docs/ folder
# 2. Restart server (it loads docs on startup)
# 3. Files are processed into chunks and added to ChromaDB

# Check what courses are loaded:
# Visit http://localhost:8000/docs → Try GET /api/courses
```

### Adding Dependencies

```bash
# Add new package (always use uv, never pip)
uv add package-name

# Remove package
uv remove package-name

# This updates both pyproject.toml and uv.lock
```

### Checking Python Version

```bash
python --version  # Should be 3.13+
```

---

## Configuration

### Environment Variables (.env)

```bash
ANTHROPIC_API_KEY=your_key_here
```

Required for Claude API access. Get key from https://console.anthropic.com

### Code Configuration (backend/config.py)

Edit `backend/config.py` to adjust:
- `ANTHROPIC_MODEL` - Which Claude model to use
- `EMBEDDING_MODEL` - Sentence transformer model name
- `CHUNK_SIZE` / `CHUNK_OVERLAP` - Document chunking strategy
- `MAX_RESULTS` - Results returned from vector search (default: 5)
- `MAX_HISTORY` - Conversation history depth (default: 2 exchanges, ~ 4-6 messages)
- `CHROMA_PATH` - Where ChromaDB stores data (default: ./chroma_db)

### Performance Tuning

1. **Vector Search**: Increase `MAX_RESULTS` for more context (slower), decrease for faster responses
2. **Conversation Memory**: Lower `MAX_HISTORY` reduces context window size, saves tokens
3. **Embedding Model**: Larger models are more accurate but slower; current model is lightweight
4. **Chunk Size**: Larger chunks = fewer API calls but less precise retrieval; smaller = more precise
5. **API Calls**: Some queries need 2 API calls (with tool use), some need 1. Total is dynamic.

---

## Important Files Reference

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `app.py` | FastAPI routes | `@app.post("/api/query")`, `@app.get("/api/courses")` |
| `rag_system.py` | RAG orchestration | `RAGSystem.query()`, `add_course_folder()` |
| `ai_generator.py` | Claude API | `AIGenerator.generate_response()`, `_handle_tool_execution()` |
| `search_tools.py` | Search tool | `CourseSearchTool.execute()`, `ToolManager` |
| `vector_store.py` | Semantic search | `VectorStore.search()`, `_resolve_course_name()` |
| `session_manager.py` | Conversation state | `SessionManager.create_session()`, `add_exchange()` |
| `document_processor.py` | Document loading | `DocumentProcessor.process_course_document()` |
| `script.js` | Frontend logic | `sendMessage()`, `loadCourseStats()` |

---

## Testing & Validation

**Note:** This project currently has no automated tests. To validate changes:

```bash
# 1. Start the server
./run.sh

# 2. Test through web interface
# - Open http://localhost:8000
# - Ask various questions (general knowledge, course-specific, filtered by lesson)
# - Check that answers are appropriate and sources are correct

# 3. Test API directly
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What is lesson 2 about?","session_id":null}'

# 4. Check course loading
curl http://localhost:8000/api/courses
```

---

## Key Development Notes

### Frontend-Backend Contract

**Frontend sends:**
```javascript
{
  "query": "string",
  "session_id": "string | null"
}
```

**Backend returns:**
```python
{
  "answer": "string (markdown-formatted)",
  "sources": ["CourseTitle - Lesson N", ...],
  "session_id": "string"
}
```

### Claude System Prompt Strategy

The system prompt (in `ai_generator.py`) is carefully designed to:
- Use search tool ONLY for course-specific questions
- Limit to 1 search per query maximum
- Avoid meta-commentary about search process
- Synthesize results into fact-based answers
- Answer general knowledge without searching

Modifying this prompt will significantly change behavior.

### Vector Store Structure

Two ChromaDB collections with different purposes:

1. **course_catalog** - Course metadata for semantic search
   - Documents: course titles
   - Metadata: title, instructor, course_link, lesson metadata (JSON)
   - Used to resolve partial course names

2. **course_content** - Actual course material chunks
   - Documents: text chunks from documents
   - Metadata: course_title, lesson_number, chunk_index
   - Used for content search with filters

### Document Processing Pipeline

1. `add_course_folder()` → iterates over files
2. `DocumentProcessor.process_course_document()` → extracts metadata, chunks content
3. `VectorStore.add_course_metadata()` → stores course info
4. `VectorStore.add_course_content()` → stores chunks with metadata
5. Embeddings created automatically by ChromaDB

---

## Common Debugging Tips

**Q: Changes not showing up?**
- Frontend: Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)
- Backend: Restart server (auto-reload watches Python files)

**Q: "No course found" or no search results?**
- Check if documents are in `docs/` folder
- Restart server to reload documents
- Visit `/api/courses` to see loaded courses
- Check console for document processing errors

**Q: API key not working?**
- Verify `.env` has correct `ANTHROPIC_API_KEY`
- Check key format: should start with `sk-ant-`
- API calls in terminal logs show full error details

**Q: Memory usage growing?**
- Session history is in-memory only
- Restarting server clears all sessions
- Increase `MAX_HISTORY` with caution (affects context window)

**Q: Slow responses?**
- Reduce `MAX_RESULTS` in config
- Reduce `MAX_HISTORY` for faster context building
- Check if second API call is happening (tool use) in logs

---

## Future Improvements to Consider

Based on current code:
1. Add persistence layer for sessions (database instead of in-memory)
2. Add user authentication
3. Add document upload UI (currently manual file copy)
4. Add tests and CI/CD pipeline
5. Cache embedding model between requests
6. Add request rate limiting
7. Implement session export/import
8. Add admin interface for document management
9. Implement vector store backup/restore

---

## Related Documentation

- `QUERY_FLOW.md` - Detailed step-by-step trace of request handling
- `FLOW_SUMMARY.txt` - Visual ASCII diagram of entire flow
- `README.md` - User-facing documentation

