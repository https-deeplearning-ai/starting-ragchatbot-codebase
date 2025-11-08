# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) system for course materials that enables users to query educational content and receive AI-powered responses. The system uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.

## Development Commands

### Running the Application

**Quick Start (Recommended):**
```bash
chmod +x run.sh
./run.sh
```

**Manual Start:**
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

### Environment Setup

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

### Development Tools

- **Python package management:** Uses `uv` instead of pip
- **Python version:** Requires Python 3.13 or higher
- **Live reload:** Enabled with `--reload` flag during development

## Architecture Overview

### Core Components

The RAG system follows a modular architecture with clear separation of concerns:

**Backend Layer (`backend/`):**
- `app.py` - FastAPI web server and API endpoints
- `rag_system.py` - Main orchestrator coordinating all components
- `document_processor.py` - Handles parsing and chunking of course documents
- `vector_store.py` - ChromaDB integration for semantic search
- `ai_generator.py` - Claude API integration with tool calling
- `search_tools.py` - Tool system for intelligent course content searching
- `session_manager.py` - Conversation history and session management

**Frontend Layer (`frontend/`):**
- Vanilla JavaScript web interface
- Real-time chat interface with loading states
- Source attribution display

**Data Layer:**
- `docs/` - Course materials in structured text format
- `chroma_db/` - Vector database storage (auto-created)

### Key Architectural Patterns

**RAG Flow:**
1. User query → FastAPI endpoint
2. RAG system constructs prompt with conversation history
3. Claude AI determines if course content search is needed
4. If needed: Vector search → Formatted results → Claude generates response
5. Response + sources returned to frontend

**Document Processing Pipeline:**
- Documents follow structured format: Course metadata → Lesson markers → Content
- Smart chunking with overlap for context preservation
- Context enrichment: Each chunk gets course/lesson metadata

**Tool System:**
- Claude can call `search_course_content` tool with filters (course name, lesson number)
- Tools managed through `ToolManager` with source tracking
- Enables intelligent, context-aware course content retrieval

**Session Management:**
- Stateless API with session IDs for conversation continuity
- Limited history (2 rounds) to manage context window
- Automatic session creation on first interaction

### Document Format Requirements

Course documents must follow this structure:
```
Course Title: [title]
Course Link: [url] (optional)
Course Instructor: [name] (optional)

Lesson 0: [lesson title]
Lesson Link: [url] (optional)
[lesson content...]

Lesson 1: [next lesson title]
[lesson content...]
```

### Configuration

Key settings in `backend/config.py`:
- `CHUNK_SIZE: 800` - Text chunk size for vector storage
- `CHUNK_OVERLAP: 100` - Overlap between chunks for context
- `MAX_RESULTS: 5` - Search results limit
- `MAX_HISTORY: 2` - Conversation rounds to remember
- `ANTHROPIC_MODEL: "claude-sonnet-4-20250514"` - AI model version

## API Endpoints

- `POST /api/query` - Main chat endpoint with session management
- `GET /api/courses` - Course statistics and available titles
- `GET /docs` - Interactive API documentation (Swagger UI)

## Important Implementation Details

**Tool Calling Integration:**
- The system uses Anthropic's tool calling feature for intelligent search
- Search results are automatically tracked for source attribution
- Tools are designed to be stateless and composable

**Vector Search Strategy:**
- Semantic search with metadata filtering capabilities
- Supports course name partial matching and lesson-specific filtering
- Results include context headers for better AI understanding

**Error Handling:**
- Graceful degradation when documents are missing
- Input validation with helpful error messages
- Frontend loading states for better UX

**Development Considerations:**
- No test suite currently implemented
- Uses SQLite-backed ChromaDB for development
- Frontend uses marked.js for Markdown rendering