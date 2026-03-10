"""
Shared pytest fixtures for all backend tests.

sys.path is managed by [tool.pytest.ini_options] pythonpath in pyproject.toml,
which adds both backend/ and backend/tests/ before any test module is imported.
"""

import pytest
from unittest.mock import MagicMock
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from vector_store import SearchResults


@pytest.fixture
def sample_search_results():
    """SearchResults with one document and full metadata"""
    return SearchResults(
        documents=["This is lesson content about Python basics"],
        metadata=[{"course_title": "Intro to Python", "lesson_number": 1}],
        distances=[0.1],
    )


@pytest.fixture
def empty_search_results():
    """SearchResults with no documents"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[],
    )


@pytest.fixture
def error_search_results():
    """SearchResults carrying an error message"""
    return SearchResults.empty("Search error: connection refused")


@pytest.fixture
def mock_vector_store():
    """MagicMock VectorStore with get_lesson_link pre-configured"""
    store = MagicMock()
    store.get_lesson_link.return_value = "https://example.com/lesson/1"
    return store


# ── API / endpoint fixtures ───────────────────────────────────────────────────

@pytest.fixture
def mock_rag_system():
    """MagicMock RAGSystem with sensible defaults for API endpoint tests"""
    rag = MagicMock()
    rag.query.return_value = (
        "Test answer",
        [{"label": "Intro to Python - Lesson 1", "url": "http://example.com/lesson/1"}],
    )
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Intro to Python", "Advanced Python"],
    }
    rag.session_manager.create_session.return_value = "generated-session-id"
    return rag


@pytest.fixture
def test_app(mock_rag_system):
    """
    Minimal FastAPI app that mirrors app.py's API endpoints without static
    file mounting or real RAGSystem initialisation — safe to import in tests.
    """
    app = FastAPI()

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Any]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            answer, sources = mock_rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        try:
            mock_rag_system.session_manager.clear_session(session_id)
            return {"success": True, "session_id": session_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


@pytest.fixture
def client(test_app):
    """Starlette TestClient wrapping the minimal test FastAPI app"""
    return TestClient(test_app)
