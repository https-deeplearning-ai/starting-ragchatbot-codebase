import sys
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


def _import_app():
    """Import app.py with all external dependencies mocked out.

    app.py runs `rag_system = RAGSystem(config)` at module level, which would
    try to connect to ChromaDB and load SentenceTransformer. The final line
    also mounts StaticFiles from ../frontend, which doesn't exist during tests.
    We patch all of these before the first import so initialization succeeds
    without real infrastructure or the filesystem layout of a running server.
    """
    with patch("vector_store.chromadb.PersistentClient") as mock_chroma, \
         patch("vector_store.SentenceTransformer"), \
         patch("ai_generator.anthropic.Anthropic"), \
         patch("starlette.staticfiles.StaticFiles.__init__", return_value=None):
        mock_chroma.return_value.get_or_create_collection.return_value = MagicMock()
        sys.modules.pop("app", None)
        import app as m
        return m


_app_module = _import_app()


@pytest.fixture
def mock_rag():
    """Replace the module-level rag_system with a clean MagicMock for each test."""
    mock = MagicMock()
    original = _app_module.rag_system
    _app_module.rag_system = mock
    yield mock
    _app_module.rag_system = original


@pytest.fixture
def client(mock_rag):
    return TestClient(_app_module.app)


class TestQueryEndpoint:

    def test_query_with_session_id_returns_answer_and_sources(self, client, mock_rag):
        mock_rag.query.return_value = (
            "Python is great.",
            [{"text": "Intro Course - Lesson 1", "url": "https://example.com/l1"}],
        )

        response = client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "sess_abc"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "Python is great."
        assert body["sources"] == [{"text": "Intro Course - Lesson 1", "url": "https://example.com/l1"}]
        assert body["session_id"] == "sess_abc"
        mock_rag.query.assert_called_once_with("What is Python?", "sess_abc")

    def test_query_without_session_id_creates_one(self, client, mock_rag):
        mock_rag.session_manager.create_session.return_value = "auto_session_1"
        mock_rag.query.return_value = ("Auto answer.", [])

        response = client.post("/api/query", json={"query": "Hello?"})

        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == "auto_session_1"
        mock_rag.session_manager.create_session.assert_called_once()

    def test_query_returns_500_on_rag_exception(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("DB connection failed")

        response = client.post(
            "/api/query",
            json={"query": "Crash?", "session_id": "s1"},
        )

        assert response.status_code == 500
        assert "DB connection failed" in response.json()["detail"]


class TestSessionEndpoint:

    def test_delete_session_calls_clear_and_returns_ok(self, client, mock_rag):
        response = client.delete("/api/session/test_session")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_rag.session_manager.clear_session.assert_called_once_with("test_session")


class TestCoursesEndpoint:

    def test_get_courses_returns_stats(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Python Basics", "Advanced RAG"],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        body = response.json()
        assert body["total_courses"] == 2
        assert body["course_titles"] == ["Python Basics", "Advanced RAG"]

    def test_get_courses_returns_500_on_exception(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("Analytics unavailable")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "Analytics unavailable" in response.json()["detail"]
