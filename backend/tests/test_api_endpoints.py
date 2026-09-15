"""
Objective 4: FastAPI endpoint tests.

Covers the request/response contract the frontend (frontend/script.js) relies
on: POST /api/query, GET /api/courses, DELETE /api/session/{id}, and the static
mount at "/". The app under test is built by conftest.create_test_app with a
mocked RAG system -- see the note there for why backend/app.py is not imported.
"""
import pytest
from fastapi.testclient import TestClient

from conftest import create_test_app

pytestmark = pytest.mark.api


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:

    def test_returns_answer_sources_and_session(self, api_client):
        response = api_client.post("/api/query", json={"query": "What is MCP?"})

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"answer", "sources", "session_id"}
        assert body["answer"] == "Claude answers here."
        assert body["session_id"] == "session_1"

    def test_sources_serialize_text_and_link(self, api_client):
        body = api_client.post("/api/query", json={"query": "What is MCP?"}).json()

        assert body["sources"] == [
            {"text": "MCP: Build Rich-Context AI Apps - Lesson 1", "link": "https://example.com/l1"},
            {"text": "Advanced Retrieval for AI - Lesson 3", "link": None},
        ]

    def test_creates_session_when_none_supplied(self, api_client, mock_rag):
        api_client.post("/api/query", json={"query": "What is MCP?"})

        mock_rag.session_manager.create_session.assert_called_once_with()
        mock_rag.query.assert_called_once_with("What is MCP?", "session_1")

    def test_reuses_supplied_session(self, api_client, mock_rag):
        response = api_client.post(
            "/api/query", json={"query": "And lesson 2?", "session_id": "session_42"}
        )

        assert response.json()["session_id"] == "session_42"
        mock_rag.session_manager.create_session.assert_not_called()
        mock_rag.query.assert_called_once_with("And lesson 2?", "session_42")

    def test_null_session_id_creates_a_new_one(self, api_client, mock_rag):
        response = api_client.post(
            "/api/query", json={"query": "What is MCP?", "session_id": None}
        )

        assert response.json()["session_id"] == "session_1"
        mock_rag.session_manager.create_session.assert_called_once_with()

    def test_empty_sources_list_is_valid(self, api_client, mock_rag):
        mock_rag.query.return_value = ("Paris is the capital of France.", [])

        body = api_client.post("/api/query", json={"query": "Capital of France?"}).json()

        assert body["sources"] == []
        assert body["answer"] == "Paris is the capital of France."

    def test_missing_query_field_is_422(self, api_client, mock_rag):
        response = api_client.post("/api/query", json={"session_id": "session_1"})

        assert response.status_code == 422
        mock_rag.query.assert_not_called()

    def test_wrong_query_type_is_422(self, api_client, mock_rag):
        response = api_client.post("/api/query", json={"query": {"nested": "object"}})

        assert response.status_code == 422
        mock_rag.query.assert_not_called()

    def test_malformed_json_body_is_422(self, api_client, mock_rag):
        response = api_client.post(
            "/api/query",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422
        mock_rag.query.assert_not_called()

    def test_unknown_fields_are_ignored(self, api_client, mock_rag):
        response = api_client.post(
            "/api/query", json={"query": "What is MCP?", "temperature": 0.9}
        )

        assert response.status_code == 200
        mock_rag.query.assert_called_once_with("What is MCP?", "session_1")

    def test_rag_failure_becomes_500_with_detail(self, api_client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("vector store unavailable")

        response = api_client.post("/api/query", json={"query": "What is MCP?"})

        assert response.status_code == 500
        assert response.json()["detail"] == "vector store unavailable"

    def test_get_is_not_allowed(self, api_client):
        assert api_client.get("/api/query").status_code == 405


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:

    def test_returns_course_stats(self, api_client, sample_analytics):
        response = api_client.get("/api/courses")

        assert response.status_code == 200
        body = response.json()
        assert set(body) == {"total_courses", "course_titles"}
        assert body["total_courses"] == sample_analytics["total_courses"]
        assert body["course_titles"] == sample_analytics["course_titles"]

    def test_empty_catalog(self, api_client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        body = api_client.get("/api/courses").json()

        assert body == {"total_courses": 0, "course_titles": []}

    def test_analytics_failure_becomes_500(self, api_client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("chroma is down")

        response = api_client.get("/api/courses")

        assert response.status_code == 500
        assert response.json()["detail"] == "chroma is down"


# ---------------------------------------------------------------------------
# DELETE /api/session/{session_id}
# ---------------------------------------------------------------------------

class TestDeleteSessionEndpoint:

    def test_deletes_the_named_session(self, api_client, mock_rag):
        response = api_client.delete("/api/session/session_7")

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_rag.session_manager.delete_session.assert_called_once_with("session_7")

    def test_unknown_session_still_succeeds(self, api_client, mock_rag):
        # delete_session is a no-op for unknown ids, so the endpoint stays 200.
        response = api_client.delete("/api/session/never-existed")

        assert response.status_code == 200
        assert response.json() == {"success": True}

    def test_delete_failure_becomes_500(self, api_client, mock_rag):
        mock_rag.session_manager.delete_session.side_effect = RuntimeError("boom")

        response = api_client.delete("/api/session/session_7")

        assert response.status_code == 500
        assert response.json()["detail"] == "boom"


# ---------------------------------------------------------------------------
# GET / (static frontend mount)
# ---------------------------------------------------------------------------

class TestStaticFrontend:

    def test_root_serves_index_html(self, full_client):
        response = full_client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "Course Materials Assistant" in response.text

    def test_static_assets_are_served(self, full_client):
        assert full_client.get("/style.css").status_code == 200
        assert full_client.get("/script.js").status_code == 200

    def test_no_cache_headers_on_static_files(self, full_client):
        headers = full_client.get("/").headers

        assert headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
        assert headers["Pragma"] == "no-cache"
        assert headers["Expires"] == "0"

    def test_missing_asset_is_404(self, full_client):
        assert full_client.get("/does-not-exist.js").status_code == 404

    def test_api_routes_win_over_the_static_mount(self, full_client):
        # The mount is at "/", so it must not shadow /api/* once both exist.
        assert full_client.get("/api/courses").status_code == 200
        assert full_client.post("/api/query", json={"query": "hi"}).status_code == 200

    def test_api_only_app_has_no_static_mount(self, api_client):
        assert api_client.get("/").status_code == 404


# ---------------------------------------------------------------------------
# Cross-cutting: CORS, app construction
# ---------------------------------------------------------------------------

class TestAppConfiguration:

    def test_cors_headers_present_on_api_responses(self, api_client):
        response = api_client.get("/api/courses", headers={"Origin": "http://localhost:3000"})

        # allow_origins=["*"] echoes "*" for uncredentialed requests.
        assert response.headers["access-control-allow-origin"] == "*"
        assert response.headers["access-control-allow-credentials"] == "true"

    def test_cors_echoes_origin_for_credentialed_requests(self, api_client):
        response = api_client.get(
            "/api/courses",
            headers={"Origin": "http://localhost:3000", "Cookie": "sid=abc"},
        )

        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    def test_cors_preflight_allows_post(self, api_client):
        response = api_client.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert "POST" in response.headers["access-control-allow-methods"]

    def test_openapi_schema_exposes_the_api_routes(self, api_client):
        paths = api_client.get("/openapi.json").json()["paths"]

        assert "/api/query" in paths
        assert "/api/courses" in paths
        assert "/api/session/{session_id}" in paths

    def test_factory_builds_independent_apps(self, mock_rag):
        # Two clients over two apps must not share state or interfere.
        with TestClient(create_test_app(mock_rag)) as first, \
             TestClient(create_test_app(mock_rag)) as second:
            assert first.get("/api/courses").status_code == 200
            assert second.get("/api/courses").status_code == 200
