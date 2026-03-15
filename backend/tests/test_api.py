"""
Tests for FastAPI endpoints: /api/query, /api/courses, /api/sessions/{id}.

Uses a test app defined in conftest.py (api_client fixture) that mirrors the
real app.py endpoints without the static-file mount or module-level RAGSystem
initialization, so these tests run without ChromaDB or Anthropic credentials.

Covers:
- POST /api/query  — success, auto session creation, provided session, 500 on error
- GET  /api/courses — success, correct shape, 500 on error
- DELETE /api/sessions/{id} — delegates to session_manager.clear_session
"""
import pytest


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:

    def test_returns_200_on_success(self, api_client):
        response = api_client.post("/api/query", json={"query": "What is backprop?"})
        assert response.status_code == 200

    def test_response_contains_required_fields(self, api_client):
        response = api_client.post("/api/query", json={"query": "What is backprop?"})
        body = response.json()
        assert "answer" in body
        assert "sources" in body
        assert "session_id" in body

    def test_answer_matches_mock(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Backprop answer", [])
        response = api_client.post("/api/query", json={"query": "What is backprop?"})
        assert response.json()["answer"] == "Backprop answer"

    def test_sources_list_returned(self, api_client, mock_rag_system):
        mock_rag_system.query.return_value = ("Answer", ["Course A - Lesson 1||https://url"])
        response = api_client.post("/api/query", json={"query": "q"})
        assert response.json()["sources"] == ["Course A - Lesson 1||https://url"]

    def test_auto_creates_session_when_none_provided(self, api_client, mock_rag_system):
        """When no session_id is sent, create_session() is called and its value is returned."""
        mock_rag_system.session_manager.create_session.return_value = "new-session-99"
        response = api_client.post("/api/query", json={"query": "q"})
        assert response.json()["session_id"] == "new-session-99"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, api_client, mock_rag_system):
        """When session_id is supplied, it is forwarded to rag_system.query() as-is."""
        response = api_client.post(
            "/api/query", json={"query": "q", "session_id": "existing-session"}
        )
        assert response.json()["session_id"] == "existing-session"
        mock_rag_system.query.assert_called_once_with("q", "existing-session")

    def test_does_not_create_session_when_one_is_provided(self, api_client, mock_rag_system):
        api_client.post("/api/query", json={"query": "q", "session_id": "s1"})
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_returns_500_when_rag_system_raises(self, api_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("API failure")
        response = api_client.post("/api/query", json={"query": "q"})
        assert response.status_code == 500

    def test_500_detail_contains_error_message(self, api_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("API failure")
        response = api_client.post("/api/query", json={"query": "q"})
        assert "API failure" in response.json()["detail"]

    def test_missing_query_field_returns_422(self, api_client):
        """FastAPI validates request bodies — missing required field yields 422."""
        response = api_client.post("/api/query", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:

    def test_returns_200_on_success(self, api_client):
        response = api_client.get("/api/courses")
        assert response.status_code == 200

    def test_response_contains_total_courses(self, api_client):
        response = api_client.get("/api/courses")
        assert "total_courses" in response.json()

    def test_response_contains_course_titles(self, api_client):
        response = api_client.get("/api/courses")
        assert "course_titles" in response.json()

    def test_total_courses_matches_mock(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["A", "B", "C"],
        }
        response = api_client.get("/api/courses")
        assert response.json()["total_courses"] == 3

    def test_course_titles_matches_mock(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Python Basics", "Deep Learning"],
        }
        response = api_client.get("/api/courses")
        assert response.json()["course_titles"] == ["Python Basics", "Deep Learning"]

    def test_returns_500_when_analytics_raises(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB error")
        response = api_client.get("/api/courses")
        assert response.status_code == 500

    def test_500_detail_contains_error_message(self, api_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("DB error")
        response = api_client.get("/api/courses")
        assert "DB error" in response.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/sessions/{session_id}
# ---------------------------------------------------------------------------

class TestDeleteSessionEndpoint:

    def test_returns_200_on_success(self, api_client):
        response = api_client.delete("/api/sessions/my-session")
        assert response.status_code == 200

    def test_response_status_ok(self, api_client):
        response = api_client.delete("/api/sessions/my-session")
        assert response.json() == {"status": "ok"}

    def test_delegates_to_session_manager_clear_session(self, api_client, mock_rag_system):
        api_client.delete("/api/sessions/sess-42")
        mock_rag_system.session_manager.clear_session.assert_called_once_with("sess-42")

    def test_session_id_forwarded_correctly(self, api_client, mock_rag_system):
        api_client.delete("/api/sessions/unique-id-xyz")
        args, _ = mock_rag_system.session_manager.clear_session.call_args
        assert args[0] == "unique-id-xyz"
