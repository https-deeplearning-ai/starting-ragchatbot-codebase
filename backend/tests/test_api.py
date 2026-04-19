"""
API endpoint tests for the RAG chatbot.

All tests use the test_client and mock_rag_system fixtures defined in
conftest.py.  The test app mirrors every route in app.py but omits the
static-file mount and the module-level RAGSystem initialisation, so these
tests run without a real database, Anthropic key, or frontend directory.
"""
import pytest


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:

    def test_returns_200_with_answer_and_sources(self, test_client):
        response = test_client.post("/api/query", json={"query": "What is Python?"})

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Test answer about Python."
        assert data["sources"] == ["Course A - Lesson 1"]

    def test_auto_creates_session_when_none_provided(self, test_client, mock_rag_system):
        response = test_client.post("/api/query", json={"query": "What is Python?"})

        assert response.status_code == 200
        assert response.json()["session_id"] == "session_1"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_uses_caller_supplied_session_id(self, test_client, mock_rag_system):
        response = test_client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "existing_session"},
        )

        assert response.status_code == 200
        assert response.json()["session_id"] == "existing_session"
        # No new session should have been created
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_passes_query_and_session_to_rag(self, test_client, mock_rag_system):
        test_client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "session_1"},
        )

        mock_rag_system.query.assert_called_once_with("What is Python?", "session_1")

    def test_returns_500_when_rag_raises(self, test_client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("Vector store unavailable")

        response = test_client.post("/api/query", json={"query": "crash?"})

        assert response.status_code == 500
        assert "Vector store unavailable" in response.json()["detail"]

    def test_returns_422_when_query_field_missing(self, test_client):
        response = test_client.post("/api/query", json={"session_id": "s1"})

        assert response.status_code == 422

    def test_empty_sources_list_is_valid(self, test_client, mock_rag_system):
        mock_rag_system.query.return_value = ("No sources answer.", [])

        response = test_client.post("/api/query", json={"query": "obscure question"})

        assert response.status_code == 200
        assert response.json()["sources"] == []


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:

    def test_returns_200_with_course_stats(self, test_client):
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Course A", "Course B"]

    def test_calls_get_course_analytics(self, test_client, mock_rag_system):
        test_client.get("/api/courses")

        mock_rag_system.get_course_analytics.assert_called_once()

    def test_returns_500_when_analytics_raises(self, test_client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = Exception("DB connection error")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        assert "DB connection error" in response.json()["detail"]

    def test_empty_catalog_returns_zero_courses(self, test_client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

class TestSessionEndpoint:

    def test_returns_200_with_cleared_status(self, test_client):
        response = test_client.delete("/api/session/session_1")

        assert response.status_code == 200
        assert response.json() == {"status": "cleared"}

    def test_passes_session_id_to_clear_session(self, test_client, mock_rag_system):
        test_client.delete("/api/session/my_session")

        mock_rag_system.session_manager.clear_session.assert_called_once_with("my_session")

    def test_clears_arbitrary_session_id(self, test_client, mock_rag_system):
        test_client.delete("/api/session/some-uuid-1234")

        mock_rag_system.session_manager.clear_session.assert_called_once_with("some-uuid-1234")
