"""
pytest conftest: auto-loaded by pytest for all test files in this directory.

Mock factories and helper functions live in helpers.py (importable directly).
Shared fixtures for API testing live here.
"""
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_rag_system():
    """Fully mocked RAGSystem for use in API tests."""
    system = MagicMock()
    system.query.return_value = ("Test answer", [])
    system.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Python Basics", "Deep Learning"],
    }
    system.session_manager.create_session.return_value = "generated-session-id"
    return system


@pytest.fixture
def api_client(mock_rag_system):
    """
    TestClient backed by a minimal FastAPI app that mirrors the real app.py
    endpoints without the static-file mount or module-level RAGSystem init.
    """

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

    test_app = FastAPI()

    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            answer, sources = mock_rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.delete("/api/sessions/{session_id}")
    async def delete_session(session_id: str):
        mock_rag_system.session_manager.clear_session(session_id)
        return {"status": "ok"}

    return TestClient(test_app)
