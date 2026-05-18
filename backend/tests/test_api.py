"""
Tests for the FastAPI API endpoints (/api/query, /api/courses, /api/session).

app.py mounts static files from ../frontend and instantiates RAGSystem at
module level — both fail in the test environment. Instead, this file builds
a minimal test app that mirrors the same routes and Pydantic models, backed
by the mock_rag_system fixture from conftest.py.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Minimal test app — same routes and models as app.py, no static files
# ---------------------------------------------------------------------------

def _build_test_app(rag_system) -> FastAPI:
    """Return a FastAPI app with the same routes as app.py."""
    app = FastAPI()

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[dict]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        rag_system.session_manager.clear_session(session_id)
        return {"status": "cleared"}

    return app


@pytest.fixture
def client(mock_rag_system):
    with TestClient(_build_test_app(mock_rag_system)) as c:
        yield c


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    def test_returns_200_with_valid_body(self, client):
        resp = client.post("/api/query", json={"query": "What is RAG?"})
        assert resp.status_code == 200

    def test_response_contains_required_fields(self, client):
        resp = client.post("/api/query", json={"query": "What is RAG?"})
        data = resp.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    def test_answer_and_sources_come_from_rag(self, client):
        resp = client.post("/api/query", json={"query": "What is RAG?"})
        data = resp.json()
        assert "RAG" in data["answer"]
        assert data["sources"][0]["label"] == "AI Course - Lesson 1"

    def test_creates_session_when_none_provided(self, client, mock_rag_system):
        resp = client.post("/api/query", json={"query": "Hello"})
        assert resp.json()["session_id"] == "session-abc123"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, mock_rag_system):
        resp = client.post("/api/query", json={"query": "Hello", "session_id": "existing"})
        assert resp.json()["session_id"] == "existing"
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_query_forwarded_to_rag(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Tell me about transformers"})
        call_args = mock_rag_system.query.call_args
        assert "Tell me about transformers" in call_args[0][0]

    def test_returns_422_for_missing_query_field(self, client):
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_returns_500_when_rag_raises(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("DB failure")
        resp = client.post("/api/query", json={"query": "crash"})
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/courses")
        assert resp.status_code == 200

    def test_response_contains_total_courses(self, client):
        resp = client.get("/api/courses")
        assert resp.json()["total_courses"] == 2

    def test_response_contains_course_titles(self, client):
        titles = client.get("/api/courses").json()["course_titles"]
        assert "Python 101" in titles
        assert "AI Fundamentals" in titles

    def test_returns_500_when_analytics_raises(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB error")
        resp = client.get("/api/courses")
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

class TestSessionEndpoint:
    def test_returns_200_with_cleared_status(self, client):
        resp = client.delete("/api/session/abc-123")
        assert resp.status_code == 200
        assert resp.json() == {"status": "cleared"}

    def test_calls_clear_session_with_correct_id(self, client, mock_rag_system):
        client.delete("/api/session/my-session-42")
        mock_rag_system.session_manager.clear_session.assert_called_once_with("my-session-42")
