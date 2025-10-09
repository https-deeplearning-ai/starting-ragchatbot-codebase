# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application

```bash
# Quick start using the provided script
./run.sh

# Manual start (from backend directory)
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Package Management

```bash
# Install dependencies
uv sync

# Add new dependencies
uv add <package-name>
```

### Environment Setup

Create `.env` file in root directory with:

```env
ANTHROPIC_API_KEY=your_api_key_here
```

## Architecture Overview

This is a **Retrieval-Augmented Generation (RAG) chatbot** system that answers questions about course materials using semantic search and AI generation.

### Core Components

**Backend Architecture (`/backend/`):**

- `app.py` - FastAPI server with CORS, serves frontend static files, provides `/api/query` and `/api/courses` endpoints
- `rag_system.py` - Main orchestrator that coordinates all components
- `vector_store.py` - ChromaDB wrapper for vector storage and semantic search
- `ai_generator.py` - Anthropic Claude API wrapper with tool support
- `document_processor.py` - Processes course documents into chunks
- `search_tools.py` - Tool-based search system for Claude AI
- `session_manager.py` - Manages conversation history
- `models.py` - Data models for Course, Lesson, CourseChunk
- `config.py` - Configuration settings loaded from environment

**Frontend (`/frontend/`):**

- Static HTML/CSS/JS files served by FastAPI
- Web interface for chatbot interactions

### Data Flow

1. Documents in `/docs/` are processed into chunks and stored in ChromaDB
2. User queries hit `/api/query` endpoint
3. RAGSystem uses AI with search tools to find relevant content
4. Claude generates responses using retrieved context
5. Session manager maintains conversation history

### Key Technical Details

- Uses **ChromaDB** for vector storage with `all-MiniLM-L6-v2` embeddings
- **Anthropic Claude Sonnet 4** model with function calling for search tools
- Document chunking: 800 characters with 100 character overlap
- Supports PDF, DOCX, and TXT documents
- Session-based conversation history (max 2 exchanges)
- Tool-based search approach rather than direct RAG retrieval

### Configuration

Key settings in `config.py`:

- `CHUNK_SIZE`: 800 (document chunk size)
- `CHUNK_OVERLAP`: 100 (overlap between chunks)
- `MAX_RESULTS`: 5 (search results returned)
- `MAX_HISTORY`: 2 (conversation exchanges remembered)
- `CHROMA_PATH`: "./chroma_db" (vector database location)
