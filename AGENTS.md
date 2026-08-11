# AGENTS.md

## Project overview

This repository contains a course-materials RAG chatbot:

- FastAPI serves the API and static frontend.
- OpenAI's Responses API generates answers and calls the local course-search tool.
- ChromaDB stores course metadata and embedded transcript chunks.
- Sentence Transformers generates local embeddings.
- The frontend is plain HTML, CSS, and JavaScript.

## Important paths

- `backend/app.py`: FastAPI application and HTTP endpoints.
- `backend/rag_system.py`: orchestration for ingestion, retrieval, generation, and sessions.
- `backend/ai_generator.py`: OpenAI Responses API integration and tool-call handling.
- `backend/document_processor.py`: transcript parsing and chunking.
- `backend/vector_store.py`: ChromaDB collections and semantic search.
- `backend/search_tools.py`: model-facing course-search tool.
- `frontend/`: browser interface.
- `docs/`: source course transcripts.

## Setup and run

Use `uv` for Python dependencies. The application requires Python 3.13 or newer.

```bash
uv sync
./run.sh
```

The application runs at `http://localhost:8000`; FastAPI documentation is at
`http://localhost:8000/docs`.

The required environment variable is:

```dotenv
OPENAI_API_KEY=your_key
```

Never print, log, hard-code, or commit API keys. Do not read or modify `.env`
unless the user explicitly asks for environment configuration.

## Architecture and behavior

- Preserve the public API contracts for `POST /api/query` and `GET /api/courses`.
- Keep retrieval source labels available to the frontend.
- Course-specific questions should use semantic retrieval; general questions may
  be answered without retrieval.
- The model may perform at most one course search for each user query.
- Conversation sessions are intentionally in-memory and retain a small history.
- ChromaDB uses separate `course_catalog` and `course_content` collections.
- Start the server through `run.sh`; current imports and data paths assume Uvicorn
  runs from the `backend` directory.

## Development conventions

- Keep changes small and consistent with the current straightforward architecture.
- Prefer type hints for new Python functions and Pydantic models for API schemas.
- Keep provider-specific API handling inside `backend/ai_generator.py`.
- Do not replace the local embedding or ChromaDB stack unless explicitly requested.
- Do not edit the course transcripts or generated `chroma_db` data unless the task
  concerns ingestion or the knowledge base.
- Avoid adding frontend frameworks for small UI changes.
- Update `README.md` when setup, configuration, endpoints, or runtime behavior changes.
- Update both `pyproject.toml` and `uv.lock` when dependencies change.

## Verification

There is currently no automated test suite. At minimum, after backend changes run:

```bash
uv run python -m compileall -q backend
git diff --check
```

For changes to retrieval or generation, add an API-free focused test or smoke check
when practical. Do not make a live OpenAI request unless the user explicitly asks
for live integration testing and a valid key is configured.

For API or frontend behavior changes, start the app and verify the affected endpoint
or browser flow. Report any verification that could not be run.

## Security and repository hygiene

- Treat model output and retrieved documents as untrusted input.
- Do not expose stack traces, secrets, or environment values through API responses.
- Preserve unrelated user changes in the working tree.
- Do not commit `.env`, `.venv`, ChromaDB data, caches, or generated artifacts.
