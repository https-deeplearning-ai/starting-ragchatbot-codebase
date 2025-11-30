# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Course Materials RAG (Retrieval-Augmented Generation) System - a web application that allows users to ask questions about educational content and receive AI-powered responses. The system uses semantic search over course documents combined with Anthropic's Claude for intelligent response generation.

## Development Commands

### Running the Application
```bash
# Quick start using provided script
chmod +x run.sh
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add package_name

# Remove dependency
uv remove package_name

# Format code
uv format
```

### Environment Setup
- Create `.env` file in root with: `ANTHROPIC_API_KEY=your_anthropic_api_key_here`
- Application runs on `http://localhost:8000`
- API docs available at `http://localhost:8000/docs`

## Architecture Overview

### Core RAG Flow
The system follows a tool-enabled RAG pattern where Claude intelligently decides when to search course materials:

1. **Query Processing**: User queries enter through FastAPI endpoint (`backend/app.py`)
2. **RAG Orchestration**: `RAGSystem` (`backend/rag_system.py`) coordinates all components
3. **AI Generation**: Claude receives queries with search tool access (`backend/ai_generator.py`)
4. **Tool-Based Search**: Claude calls `CourseSearchTool` when course-specific content needed
5. **Vector Search**: Semantic search using ChromaDB and sentence transformers
6. **Response Assembly**: Claude synthesizes search results into natural responses

### Key Components

**Backend Services** (all in `backend/`):
- `app.py` - FastAPI web server and API endpoints
- `rag_system.py` - Main orchestrator for RAG operations
- `ai_generator.py` - Anthropic Claude API integration with tool support
- `search_tools.py` - Tool manager and course search tool implementation
- `vector_store.py` - ChromaDB interface for semantic search
- `document_processor.py` - Text chunking and course document parsing
- `session_manager.py` - Conversation history management
- `models.py` - Pydantic models (Course, Lesson, CourseChunk)
- `config.py` - Configuration management with environment variables

**Frontend**: Simple HTML/CSS/JS interface (`frontend/`) for chat interaction

**Data Models**:
- `Course`: Contains title, instructor, lessons list
- `Lesson`: Individual lessons with numbers and titles
- `CourseChunk`: Text segments for vector storage with metadata

### Configuration Settings
Located in `backend/config.py`:
- `CHUNK_SIZE`: 800 characters (for vector storage)
- `CHUNK_OVERLAP`: 100 characters (between chunks)
- `MAX_RESULTS`: 5 (semantic search results)
- `MAX_HISTORY`: 2 (conversation messages remembered)
- `EMBEDDING_MODEL`: "all-MiniLM-L6-v2" (sentence transformers)
- `ANTHROPIC_MODEL`: "claude-sonnet-4-20250514"

### Document Processing
Course documents in `docs/` folder are automatically processed on startup:
- Supports `.txt`, `.pdf`, `.docx` files
- Creates course metadata and text chunks
- Stores embeddings in ChromaDB (`backend/chroma_db/`)
- Avoids reprocessing existing courses

### Tool-Enabled Search Pattern
Unlike traditional RAG that always retrieves context, this system uses Claude's tool calling:
- Claude decides when course search is needed vs. general knowledge
- `CourseSearchTool` provides semantic search with course/lesson filtering
- Sources are tracked and returned to user for transparency
- Supports both broad queries and specific course/lesson targeting

## Key Files to Understand

When modifying the system, focus on these architectural components:
- `backend/rag_system.py` - Central coordination logic
- `backend/ai_generator.py` - Tool integration and prompt engineering
- `backend/search_tools.py` - Search tool implementation
- `backend/vector_store.py` - Vector database operations
- `backend/models.py` - Data structure definitions

The frontend is intentionally simple - the intelligence is in the backend RAG pipeline.