"""Shared fixtures. Tests mock ChromaDB and the Anthropic client: no network, no embeddings.

`backend/` is on sys.path via `pythonpath` in pyproject.toml's [tool.pytest.ini_options].
"""

from types import SimpleNamespace
from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from pydantic import BaseModel

from vector_store import SearchResults

MCP = "MCP: Build Rich-Context AI Apps with Anthropic"


def make_results(chunks, error=None):
    """chunks: list of (text, course_title, lesson_number, chunk_index)"""
    if error:
        return SearchResults.empty(error)
    return SearchResults(
        documents=[c[0] for c in chunks],
        metadata=[
            {"course_title": c[1], "lesson_number": c[2], "chunk_index": c[3]}
            for c in chunks
        ],
        distances=[0.1 * i for i in range(len(chunks))],
    )


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_lesson_link.side_effect = (
        lambda title, n: f"https://example.com/{title[:3].lower()}/lesson{n}"
    )
    return store


# --- Fake Anthropic responses -------------------------------------------------


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def thinking_block(thinking="hmm"):
    return SimpleNamespace(type="thinking", thinking=thinking)


def tool_use_block(name, tool_input, block_id="toolu_1"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=block_id)


def response(*blocks, stop_reason="end_turn"):
    return SimpleNamespace(content=list(blocks), stop_reason=stop_reason)


# --- API test app -------------------------------------------------------------
# backend/app.py can't be imported in tests: at import time it builds a real
# RAGSystem (ChromaDB + sentence-transformers) and mounts ../frontend relative to
# the cwd. This app copies its models and endpoints but takes the RAG system and
# static directory as arguments. KEEP IN SYNC with backend/app.py.


class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class Source(BaseModel):
    label: str
    url: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


def create_test_app(rag, static_dir) -> FastAPI:
    """Copy of backend/app.py's routes, backed by `rag`, with no startup doc loading."""
    app = FastAPI(title="Course Materials RAG System (test)")

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag.session_manager.create_session()
            answer, sources = rag.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        return {"deleted": rag.session_manager.delete_session(session_id)}

    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    return app


INDEX_TITLE = "Course Materials Assistant"


@pytest.fixture
def mock_rag():
    """Stand-in for RAGSystem with canned answers for every method the API uses."""
    rag = MagicMock()
    rag.query.return_value = (
        "MCP is a protocol.",
        [{"label": f"{MCP} - Lesson 1", "url": "https://example.com/mcp/lesson1"}],
    )
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": [MCP, "Other Course"],
    }
    rag.session_manager.create_session.return_value = "session_1"
    rag.session_manager.delete_session.return_value = True
    return rag


@pytest.fixture
def static_dir(tmp_path):
    """Minimal frontend so the "/" mount works without the real ../frontend."""
    (tmp_path / "index.html").write_text(
        f"<!DOCTYPE html><html><head><title>{INDEX_TITLE}</title></head><body></body></html>"
    )
    return tmp_path


@pytest.fixture
def client(mock_rag, static_dir):
    with TestClient(create_test_app(mock_rag, static_dir)) as c:
        yield c
