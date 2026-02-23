"""Tests for FastAPI API endpoints.

Because the production app.py mounts static files from ../frontend (which
doesn't exist in the test environment), we define a lightweight test app that
mirrors the endpoint logic and wires in a mock RAGSystem.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional, Dict, Union


# ---------------------------------------------------------------------------
# Pydantic models (duplicated from app.py to avoid import side-effects)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Union[str, Dict[str, str]]]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


class ClearSessionRequest(BaseModel):
    session_id: str


# ---------------------------------------------------------------------------
# Test app factory
# ---------------------------------------------------------------------------

def _create_test_app(rag_system: MagicMock) -> FastAPI:
    """Build a minimal FastAPI app with the same endpoints as production."""
    test_app = FastAPI()

    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources, _links = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.post("/api/session/clear")
    async def clear_session(request: ClearSessionRequest):
        try:
            rag_system.session_manager.clear_session(request.session_id)
            return {"status": "success", "message": f"Session {request.session_id} cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return test_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(mock_rag_system):
    """TestClient wired to the mock RAG system."""
    app = _create_test_app(mock_rag_system)
    return TestClient(app)


# ---------------------------------------------------------------------------
# /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    def test_query_with_session_id(self, client, mock_rag_system):
        resp = client.post("/api/query", json={"query": "What is RAG?", "session_id": "s1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "This is a test answer."
        assert data["sources"] == ["Source A", "Source B"]
        assert data["session_id"] == "s1"
        mock_rag_system.query.assert_called_once_with("What is RAG?", "s1")

    def test_query_creates_session_when_missing(self, client, mock_rag_system):
        resp = client.post("/api/query", json={"query": "Hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "test-session-123"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_returns_dict_sources(self, client, mock_rag_system):
        mock_rag_system.query.return_value = (
            "Answer",
            [{"title": "Lesson 1", "link": "http://example.com"}],
            [],
        )
        resp = client.post("/api/query", json={"query": "test"})
        assert resp.status_code == 200
        assert resp.json()["sources"] == [{"title": "Lesson 1", "link": "http://example.com"}]

    def test_query_missing_body_returns_422(self, client):
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_query_rag_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("boom")
        resp = client.post("/api/query", json={"query": "fail", "session_id": "s1"})
        assert resp.status_code == 500
        assert "boom" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    def test_get_courses(self, client):
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Course A", "Course B"]

    def test_courses_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("db down")
        resp = client.get("/api/courses")
        assert resp.status_code == 500
        assert "db down" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /api/session/clear
# ---------------------------------------------------------------------------

class TestClearSessionEndpoint:
    def test_clear_session_success(self, client, mock_rag_system):
        resp = client.post("/api/session/clear", json={"session_id": "s1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        mock_rag_system.session_manager.clear_session.assert_called_once_with("s1")

    def test_clear_session_missing_id_returns_422(self, client):
        resp = client.post("/api/session/clear", json={})
        assert resp.status_code == 422

    def test_clear_session_error_returns_500(self, client, mock_rag_system):
        mock_rag_system.session_manager.clear_session.side_effect = KeyError("no session")
        resp = client.post("/api/session/clear", json={"session_id": "bad"})
        assert resp.status_code == 500
