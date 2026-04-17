"""
API endpoint tests for the FastAPI application.

Uses an inline test app (build_test_app from conftest) that mirrors the real
app.py routes without mounting StaticFiles or instantiating a real RAGSystem,
so these tests run without a frontend directory or ChromaDB instance.

Endpoints covered:
  POST /api/query
  GET  /api/courses
  DELETE /api/session/{session_id}
"""
import pytest
from fastapi.testclient import TestClient
from tests.conftest import build_test_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(mock_rag_system):
    """TestClient wired to the inline test app and a fresh RAGSystem mock."""
    return TestClient(build_test_app(mock_rag_system))


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:

    def test_returns_200_with_required_fields(self, client):
        """
        WHAT: Valid query returns 200 and a body that contains answer, sources, session_id.
        ASSERT: All three keys present; answer is a non-empty string.
        FAILURE MEANS: Response contract broken — frontend crashes unpacking the JSON.
        """
        response = client.post("/api/query", json={"query": "What is Python?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0

    def test_auto_creates_session_when_none_provided(self, client, mock_rag_system):
        """
        WHAT: Omitting session_id triggers session_manager.create_session().
        ASSERT: Returned session_id equals the value produced by the mock.
        FAILURE MEANS: Anonymous (stateless) queries never get a session — frontend
                       cannot maintain conversation continuity.
        """
        response = client.post("/api/query", json={"query": "Hello"})
        assert response.status_code == 200
        assert response.json()["session_id"] == "auto-session-id"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, mock_rag_system):
        """
        WHAT: When session_id is supplied, create_session is NOT called; the provided
              id is passed directly to rag_system.query and echoed back.
        ASSERT: create_session not called; session_id in response matches the input.
        FAILURE MEANS: Existing sessions are silently discarded, breaking multi-turn chat.
        """
        response = client.post(
            "/api/query",
            json={"query": "Follow-up question", "session_id": "existing-session-42"},
        )
        assert response.status_code == 200
        assert response.json()["session_id"] == "existing-session-42"
        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with(
            "Follow-up question", "existing-session-42"
        )

    def test_sources_list_forwarded_from_rag(self, client, mock_rag_system):
        """
        WHAT: Sources returned by rag_system.query appear in the response body.
        ASSERT: sources list matches what the mock returns.
        FAILURE MEANS: Frontend never displays source links even when search succeeds.
        """
        mock_rag_system.query.return_value = (
            "Python is great.",
            [{"label": "Python Fundamentals - Lesson 1", "url": "https://example.com"}],
        )
        response = client.post("/api/query", json={"query": "What is Python?"})
        assert response.status_code == 200
        sources = response.json()["sources"]
        assert len(sources) == 1
        assert sources[0]["label"] == "Python Fundamentals - Lesson 1"

    def test_returns_500_when_rag_raises(self, client, mock_rag_system):
        """
        WHAT: If rag_system.query raises, the endpoint returns HTTP 500.
        ASSERT: status_code == 500 and detail string is present.
        FAILURE MEANS: Exception propagates unhandled → Starlette returns a generic 500
                       without the error detail, making debugging harder.
        """
        mock_rag_system.query.side_effect = RuntimeError("ChromaDB connection lost")
        response = client.post("/api/query", json={"query": "What is Python?"})
        assert response.status_code == 500
        assert "ChromaDB connection lost" in response.json()["detail"]

    def test_query_field_is_required(self, client):
        """
        WHAT: A request body missing the required 'query' field is rejected with 422.
        ASSERT: status_code == 422 (Unprocessable Entity).
        FAILURE MEANS: Pydantic validation is bypassed or the model definition changed.
        """
        response = client.post("/api/query", json={"session_id": "abc"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:

    def test_returns_200_with_course_stats(self, client):
        """
        WHAT: GET /api/courses returns total_courses and course_titles from the RAG system.
        ASSERT: 200; total_courses == 2; course_titles is a list of 2 strings.
        FAILURE MEANS: Analytics endpoint broken — dashboard always shows stale/zero data.
        """
        response = client.get("/api/courses")
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 2
        assert data["course_titles"] == ["Python Fundamentals", "Data Science Basics"]

    def test_delegates_to_get_course_analytics(self, client, mock_rag_system):
        """
        WHAT: /api/courses calls rag_system.get_course_analytics() exactly once.
        ASSERT: get_course_analytics called once.
        FAILURE MEANS: Route is using a cached value or wrong method — data could be stale.
        """
        client.get("/api/courses")
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_returns_500_when_analytics_raises(self, client, mock_rag_system):
        """
        WHAT: If get_course_analytics raises, the endpoint returns HTTP 500.
        ASSERT: status_code == 500 with an error detail string.
        FAILURE MEANS: Unhandled exception crashes the server process instead of
                       returning a structured error to the frontend.
        """
        mock_rag_system.get_course_analytics.side_effect = Exception("DB error")
        response = client.get("/api/courses")
        assert response.status_code == 500
        assert "DB error" in response.json()["detail"]

    def test_empty_course_list(self, client, mock_rag_system):
        """
        WHAT: When no courses are loaded, endpoint returns total_courses=0 and [].
        ASSERT: total_courses == 0; course_titles == [].
        FAILURE MEANS: Empty-state handling crashes or returns unexpected data types.
        """
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        response = client.get("/api/courses")
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

class TestDeleteSessionEndpoint:

    def test_returns_200_with_cleared_status(self, client):
        """
        WHAT: DELETE /api/session/{id} returns 200 and {"status": "cleared"}.
        ASSERT: status_code == 200; body matches exactly.
        FAILURE MEANS: Session cleanup endpoint broken — conversation history leaks
                       across users or stale sessions accumulate in memory.
        """
        response = client.delete("/api/session/test-session-id")
        assert response.status_code == 200
        assert response.json() == {"status": "cleared"}

    def test_calls_clear_session_with_correct_id(self, client, mock_rag_system):
        """
        WHAT: The session_id path parameter is forwarded to session_manager.clear_session.
        ASSERT: clear_session called once with the exact id from the URL.
        FAILURE MEANS: Wrong session is cleared, or the call is silently skipped.
        """
        client.delete("/api/session/my-specific-session")
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "my-specific-session"
        )
