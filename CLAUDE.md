# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A full-stack RAG (Retrieval-Augmented Generation) chatbot for querying course materials. Users ask questions about course content, and Claude uses semantic search tools to retrieve relevant chunks before generating an answer.

## Commands

### Setup
```bash
# Install UV package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python dependencies
uv sync
```

### Running
```bash
./run.sh
```

The app is available at `http://localhost:8000`. FastAPI auto-generated docs are at `http://localhost:8000/docs`.

### Environment
Copy `.env.example` to `.env` and configure:
```
ANTHROPIC_MODEL=arn:aws:bedrock:<region>:<account>:application-inference-profile/<id>
EMBED_MODEL=arn:aws:bedrock:<region>:<account>:application-inference-profile/<id>
AWS_PROFILE=your-aws-profile-name  # if not already set in shell environment
```

## AWS Bedrock Migration

The codebase was originally written using the Anthropic Python SDK (`anthropic.Anthropic`) with a direct API key, and `sentence-transformers` (all-MiniLM-L6-v2) for local embeddings. It has been rewritten to use AWS Bedrock exclusively via `boto3`:

- **LLM**: Claude via `boto3` `bedrock-runtime.converse()`
- **Embeddings**: Cohere Embed Multilingual v3 via `boto3` `bedrock-runtime.invoke_model()`
- **Tool calling**: Migrated from Anthropic SDK tool format (`input_schema`, `messages.create`) to boto3 converse format (`inputSchema` nested under `toolSpec`, `toolConfig` with `toolChoice`)

## Architecture

### Request Flow

```
Browser → FastAPI (app.py) → RAGSystem (rag_system.py)
                                    ├── DocumentProcessor → VectorStore (ChromaDB)
                                    ├── SessionManager (conversation history)
                                    └── AIGenerator → boto3 bedrock-runtime.converse()
                                                          ↓ tool call
                                                  ToolManager → CourseSearchTool → VectorStore
                                                                                        ↓
                                                                         boto3 bedrock-runtime.invoke_model()
                                                                         (Cohere Embed Multilingual v3)
```

### Key Components

- **`backend/app.py`** — FastAPI entry point. Serves static frontend, exposes `POST /api/query` and `GET /api/courses`. Auto-loads documents from `../docs/` on startup.
- **`backend/rag_system.py`** — Main orchestrator. Coordinates document ingestion and query processing across all components.
- **`backend/ai_generator.py`** — boto3 wrapper for Claude via Bedrock. Uses the `converse` API which supports tool calling and multi-turn conversations.
- **`backend/vector_store.py`** — ChromaDB interface with two collections: `course_catalog` (metadata) and `course_content` (chunked text). Uses `CohereBedrockEmbeddingFunction` (a custom ChromaDB `EmbeddingFunction`) to embed via Bedrock. Batches embedding requests in groups of 96 (Cohere's limit is 128).
- **`backend/search_tools.py`** — Tool definitions for Claude's tool calling in boto3 `converse` format. `CourseSearchTool` does semantic search with fuzzy course name matching.
- **`backend/document_processor.py`** — Parses structured `.txt` course files and splits content into ~800-char chunks with 100-char overlap at sentence boundaries.
- **`backend/session_manager.py`** — Stores the last 2 conversation exchanges per session for follow-up context.
- **`backend/config.py`** — All tunable settings (model ARNs, chunk size, max results, etc.) read from environment variables.

### ChromaDB Persistence

Indexed vectors are persisted to `backend/chroma_db/`. Documents are only re-embedded if not already present. If you change the embedding model, delete `backend/chroma_db/` before restarting to force re-indexing.

### Course Document Format

Documents in `docs/` must follow this structure for the parser to work:

```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [title]
Lesson Link: [url]
[lesson content...]

Lesson 1: [title]
...
```

### Frontend

Vanilla JS single-page app in `frontend/`. Uses relative API paths so it works behind proxies. Renders markdown via Marked.js and displays collapsible source citations.
