"""
Shared fixtures for the RAG system test suite.

The production app.py mounts static files from ../frontend and initialises
RAGSystem at import time, both of which fail in the test environment.
To avoid that, conftest.py defines a create_test_app() factory that
mirrors every API route with a caller-supplied (mock) RAGSystem and
no static-file mount.  All test modules should use the test_client
fixture rather than importing app directly.
"""
import sys
import os
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from pydantic import BaseModel
from typing import List, Optional

# Make the backend package importable from within the tests/ sub-directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Course, Lesson, CourseChunk  # noqa: E402


# ---------------------------------------------------------------------------
# Pydantic request / response models (mirrored from app.py)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# ---------------------------------------------------------------------------
# Test-app factory
# ---------------------------------------------------------------------------

def create_test_app(rag_system) -> FastAPI:
    """Return a FastAPI app wired to *rag_system* with no static-file mount."""
    app = FastAPI(title="Test RAG App")

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.delete("/api/session/{session_id}")
    async def delete_session(session_id: str):
        rag_system.session_manager.clear_session(session_id)
        return {"status": "cleared"}

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """MagicMock standing in for RAGSystem with sensible default return values."""
    mock = MagicMock()
    mock.session_manager = MagicMock()
    mock.session_manager.create_session.return_value = "session_1"
    mock.query.return_value = ("Test answer about Python.", ["Course A - Lesson 1"])
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Course A", "Course B"],
    }
    return mock


@pytest.fixture
def test_client(mock_rag_system):
    """Starlette TestClient backed by the test app and a fresh mock RAGSystem."""
    app = create_test_app(mock_rag_system)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_query_request():
    """Minimal valid /api/query payload."""
    return {"query": "What is Python?"}


@pytest.fixture
def sample_course():
    """A fully-populated Course model for unit tests that need one."""
    return Course(
        title="Python Basics",
        course_link="https://example.com/python",
        instructor="Jane Doe",
        lessons=[
            Lesson(lesson_number=1, title="Introduction", lesson_link="https://example.com/l1"),
            Lesson(lesson_number=2, title="Variables", lesson_link="https://example.com/l2"),
        ],
    )


@pytest.fixture
def sample_chunk():
    """A single CourseChunk for unit tests that need vector-store content."""
    return CourseChunk(
        content="Python is a high-level programming language.",
        course_title="Python Basics",
        lesson_number=1,
        chunk_index=0,
    )


@pytest.fixture
def sample_course_no_optionals():
    """A Course where instructor and course_link are None."""
    return Course(
        title="Sparse Course",
        course_link=None,
        instructor=None,
        lessons=[],
    )


@pytest.fixture
def sample_chunks():
    """A list of CourseChunks including one with lesson_number=None."""
    return [
        CourseChunk(content="chunk 0 text", course_title="Python Basics", lesson_number=1, chunk_index=0),
        CourseChunk(content="chunk 1 text", course_title="Python Basics", lesson_number=2, chunk_index=1),
        CourseChunk(content="chunk 2 no lesson", course_title="Python Basics", lesson_number=None, chunk_index=2),
    ]


@pytest.fixture
def mock_vector_store():
    """A MagicMock that mimics VectorStore's public interface."""
    store = MagicMock()
    store.search.return_value = MagicMock(
        documents=["result doc"],
        metadata=[{"course_title": "Python Basics", "lesson_number": 1}],
        distances=[0.1],
        error=None,
        is_empty=MagicMock(return_value=False),
    )
    store.get_lesson_link.return_value = "https://example.com/python/1"
    return store
