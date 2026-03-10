"""
Tests for FastAPI API endpoints: POST /api/query, GET /api/courses,
DELETE /api/session/{session_id}.

Uses a minimal test app and TestClient defined in conftest.py to avoid
importing app.py directly (which mounts static files and initialises
RAGSystem at module level).
"""
import pytest


# ── POST /api/query ───────────────────────────────────────────────────────────

def test_query_returns_200_for_valid_request(client):
    response = client.post("/api/query", json={"query": "What is Python?"})
    assert response.status_code == 200


def test_query_response_has_required_fields(client):
    body = client.post("/api/query", json={"query": "What is Python?"}).json()
    assert "answer" in body
    assert "sources" in body
    assert "session_id" in body


def test_query_answer_comes_from_rag_system(client, mock_rag_system):
    mock_rag_system.query.return_value = ("Custom answer", [])
    body = client.post("/api/query", json={"query": "What is Python?"}).json()
    assert body["answer"] == "Custom answer"


def test_query_sources_come_from_rag_system(client, mock_rag_system):
    sources = [{"label": "Course - Lesson 1", "url": "http://example.com"}]
    mock_rag_system.query.return_value = ("Answer", sources)
    body = client.post("/api/query", json={"query": "What is Python?"}).json()
    assert body["sources"] == sources


def test_query_creates_session_when_session_id_not_provided(client, mock_rag_system):
    mock_rag_system.session_manager.create_session.return_value = "new-session-abc"
    body = client.post("/api/query", json={"query": "What is Python?"}).json()
    assert body["session_id"] == "new-session-abc"
    mock_rag_system.session_manager.create_session.assert_called_once()


def test_query_uses_provided_session_id(client, mock_rag_system):
    body = client.post(
        "/api/query", json={"query": "What is Python?", "session_id": "existing-session"}
    ).json()
    assert body["session_id"] == "existing-session"
    mock_rag_system.session_manager.create_session.assert_not_called()


def test_query_forwards_query_and_session_id_to_rag_system(client, mock_rag_system):
    client.post("/api/query", json={"query": "What is Python?", "session_id": "sess-1"})
    mock_rag_system.query.assert_called_once_with("What is Python?", "sess-1")


def test_query_returns_422_for_missing_query_field(client):
    response = client.post("/api/query", json={})
    assert response.status_code == 422


def test_query_returns_500_when_rag_system_raises(client, mock_rag_system):
    mock_rag_system.query.side_effect = RuntimeError("RAG failure")
    response = client.post("/api/query", json={"query": "What is Python?"})
    assert response.status_code == 500
    assert "RAG failure" in response.json()["detail"]


# ── GET /api/courses ──────────────────────────────────────────────────────────

def test_courses_returns_200(client):
    assert client.get("/api/courses").status_code == 200


def test_courses_response_has_required_fields(client):
    body = client.get("/api/courses").json()
    assert "total_courses" in body
    assert "course_titles" in body


def test_courses_total_courses_from_rag_system(client, mock_rag_system):
    mock_rag_system.get_course_analytics.return_value = {
        "total_courses": 5,
        "course_titles": ["A", "B", "C", "D", "E"],
    }
    assert client.get("/api/courses").json()["total_courses"] == 5


def test_courses_titles_from_rag_system(client, mock_rag_system):
    titles = ["Intro to Python", "Advanced Python"]
    mock_rag_system.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": titles,
    }
    assert client.get("/api/courses").json()["course_titles"] == titles


def test_courses_returns_500_on_analytics_error(client, mock_rag_system):
    mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB error")
    response = client.get("/api/courses")
    assert response.status_code == 500
    assert "DB error" in response.json()["detail"]


# ── DELETE /api/session/{session_id} ─────────────────────────────────────────

def test_clear_session_returns_200(client):
    assert client.delete("/api/session/session-abc").status_code == 200


def test_clear_session_response_contains_session_id_and_success(client):
    body = client.delete("/api/session/session-abc").json()
    assert body["session_id"] == "session-abc"
    assert body["success"] is True


def test_clear_session_calls_session_manager_clear(client, mock_rag_system):
    client.delete("/api/session/session-xyz")
    mock_rag_system.session_manager.clear_session.assert_called_once_with("session-xyz")


def test_clear_session_returns_500_on_error(client, mock_rag_system):
    mock_rag_system.session_manager.clear_session.side_effect = RuntimeError("Session error")
    response = client.delete("/api/session/session-abc")
    assert response.status_code == 500
    assert "Session error" in response.json()["detail"]
