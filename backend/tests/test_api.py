"""API endpoint tests for the RAG FastAPI application.

Uses a test app (see conftest.create_test_app) that mirrors production routes
without mounting StaticFiles, so tests do not depend on ../frontend existing.
"""

from fastapi.testclient import TestClient

from tests.conftest import create_test_app


class TestQueryEndpoint:
    def test_query_without_session_creates_session_and_returns_answer(
        self, client, mock_rag_system, sample_query_response_data
    ):
        response = client.post(
            "/api/query",
            json={"query": "What is RAG?"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == sample_query_response_data["answer"]
        assert data["sources"] == sample_query_response_data["sources"]
        assert data["session_id"] == sample_query_response_data["session_id"]

        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with(
            "What is RAG?",
            sample_query_response_data["session_id"],
        )

    def test_query_with_existing_session_reuses_session_id(
        self, client, mock_rag_system
    ):
        response = client.post(
            "/api/query",
            json={"query": "Explain embeddings", "session_id": "existing-session"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session"
        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with(
            "Explain embeddings",
            "existing-session",
        )

    def test_query_missing_query_field_returns_422(self, client):
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_query_rag_failure_returns_500(self, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("vector store unavailable")
        client = TestClient(create_test_app(mock_rag_system))

        response = client.post("/api/query", json={"query": "What is MCP?"})

        assert response.status_code == 500
        assert "vector store unavailable" in response.json()["detail"]


class TestCoursesEndpoint:
    def test_courses_returns_analytics(
        self, client, mock_rag_system, sample_course_analytics
    ):
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == sample_course_analytics["total_courses"]
        assert data["course_titles"] == sample_course_analytics["course_titles"]
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_failure_returns_500(self, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("chroma down")
        client = TestClient(create_test_app(mock_rag_system))

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "chroma down" in response.json()["detail"]


class TestRootEndpoint:
    def test_root_returns_ok(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert response.json()["message"] == "Course Materials RAG System"


class TestClearSessionEndpoint:
    def test_clear_session_returns_success(self, client, mock_rag_system):
        response = client.delete("/api/session/session-abc-123")

        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "session-abc-123"
        )
