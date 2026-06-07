"""
Tests for the FastAPI endpoints defined in app.py.

Uses the minimal test app from conftest.py (api_client fixture) so tests
run without importing app.py directly — avoiding the static-file mount and
ChromaDB initialisation that fail in a test environment.

Endpoints covered:
  POST   /api/query
  GET    /api/courses
  DELETE /api/session/{session_id}
"""

import pytest


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:

    def test_returns_200_for_valid_request(self, api_client):
        response = api_client.post("/api/query", json={"query": "What is RAG?"})
        assert response.status_code == 200

    def test_answer_matches_rag_system_response(self, api_client):
        response = api_client.post("/api/query", json={"query": "What is RAG?"})
        assert response.json()["answer"] == "Test answer"

    def test_sources_match_rag_system_response(self, api_client):
        response = api_client.post("/api/query", json={"query": "What is RAG?"})
        assert response.json()["sources"] == ["Introduction to RAG - Lesson 1"]

    def test_response_includes_session_id(self, api_client):
        response = api_client.post("/api/query", json={"query": "test"})
        assert "session_id" in response.json()

    def test_auto_creates_session_when_none_provided(self, api_client, mock_rag_system):
        api_client.post("/api/query", json={"query": "test"})
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_does_not_create_session_when_one_is_provided(self, api_client, mock_rag_system):
        api_client.post("/api/query", json={"query": "test", "session_id": "existing"})
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_provided_session_id_forwarded_to_rag_query(self, api_client, mock_rag_system):
        api_client.post("/api/query", json={"query": "test", "session_id": "existing"})
        mock_rag_system.query.assert_called_once_with("test", "existing")

    def test_missing_query_field_returns_422(self, api_client):
        response = api_client.post("/api/query", json={})
        assert response.status_code == 422

    def test_rag_exception_returns_500(self, api_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("DB unavailable")
        response = api_client.post("/api/query", json={"query": "test"})
        assert response.status_code == 500

    def test_500_detail_contains_exception_message(self, api_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("DB unavailable")
        response = api_client.post("/api/query", json={"query": "test"})
        assert "DB unavailable" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:

    def test_returns_200(self, api_client):
        response = api_client.get("/api/courses")
        assert response.status_code == 200

    def test_total_courses_matches_analytics(self, api_client):
        response = api_client.get("/api/courses")
        assert response.json()["total_courses"] == 1

    def test_course_titles_matches_analytics(self, api_client):
        response = api_client.get("/api/courses")
        assert response.json()["course_titles"] == ["Introduction to RAG"]

    def test_analytics_exception_returns_500(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("analytics failed")
        response = api_client.get("/api/courses")
        assert response.status_code == 500

    def test_500_detail_contains_exception_message(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("analytics failed")
        response = api_client.get("/api/courses")
        assert "analytics failed" in response.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

class TestClearSessionEndpoint:

    def test_returns_200(self, api_client):
        response = api_client.delete("/api/session/abc123")
        assert response.status_code == 200

    def test_response_body_is_cleared_status(self, api_client):
        response = api_client.delete("/api/session/abc123")
        assert response.json() == {"status": "cleared"}

    def test_calls_clear_session_with_correct_id(self, api_client, mock_rag_system):
        api_client.delete("/api/session/abc123")
        mock_rag_system.session_manager.clear_session.assert_called_once_with("abc123")
