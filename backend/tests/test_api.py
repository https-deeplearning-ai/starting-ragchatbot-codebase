"""Tests for the FastAPI API endpoints."""

import pytest
from unittest.mock import MagicMock


# ── POST /api/query ─────────────────────────────────────────────────────


class TestQueryEndpoint:
    """Tests for the /api/query endpoint."""

    def test_query_returns_answer_and_sources(self, client, mock_rag_system):
        resp = client.post("/api/query", json={"query": "What is RAG?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "RAG stands for Retrieval-Augmented Generation."
        assert len(data["sources"]) == 1
        assert data["sources"][0]["title"] == "Building RAG Chatbots"

    def test_query_creates_session_when_not_provided(self, client, mock_rag_system):
        resp = client.post("/api/query", json={"query": "Hello"})
        data = resp.json()
        assert data["session_id"] == "session_1"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_uses_provided_session_id(self, client, mock_rag_system):
        resp = client.post(
            "/api/query",
            json={"query": "Hello", "session_id": "existing_session"},
        )
        data = resp.json()
        assert data["session_id"] == "existing_session"
        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with("Hello", "existing_session")

    def test_query_passes_query_to_rag_system(self, client, mock_rag_system):
        client.post("/api/query", json={"query": "Tell me about MCP"})
        mock_rag_system.query.assert_called_once()
        assert mock_rag_system.query.call_args[0][0] == "Tell me about MCP"

    def test_query_missing_query_field_returns_422(self, client):
        resp = client.post("/api/query", json={})
        assert resp.status_code == 422

    def test_query_empty_string_passes_through(self, client, mock_rag_system):
        resp = client.post("/api/query", json={"query": ""})
        # FastAPI doesn't block empty strings by default; the endpoint processes it
        assert resp.status_code == 200

    def test_query_rag_exception_returns_500(self, client, mock_rag_system):
        mock_rag_system.query.side_effect = RuntimeError("Ollama unreachable")
        resp = client.post("/api/query", json={"query": "anything"})
        assert resp.status_code == 500
        assert "Ollama unreachable" in resp.json()["detail"]

    def test_query_sources_with_no_link(self, client, mock_rag_system):
        mock_rag_system.query.return_value = (
            "Answer",
            [{"title": "Some Course"}],
        )
        resp = client.post("/api/query", json={"query": "test"})
        data = resp.json()
        assert data["sources"][0]["link"] is None

    def test_query_empty_sources(self, client, mock_rag_system):
        mock_rag_system.query.return_value = ("No results", [])
        resp = client.post("/api/query", json={"query": "obscure question"})
        data = resp.json()
        assert data["sources"] == []


# ── POST /api/sessions/clear ────────────────────────────────────────────


class TestClearSessionEndpoint:
    """Tests for the /api/sessions/clear endpoint."""

    def test_clear_session_returns_ok(self, client, mock_rag_system):
        resp = client.post(
            "/api/sessions/clear", json={"session_id": "session_1"}
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_clear_session_calls_session_manager(self, client, mock_rag_system):
        client.post("/api/sessions/clear", json={"session_id": "session_42"})
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "session_42"
        )

    def test_clear_session_missing_body_returns_422(self, client):
        resp = client.post("/api/sessions/clear", json={})
        assert resp.status_code == 422

    def test_clear_session_exception_returns_500(self, client, mock_rag_system):
        mock_rag_system.session_manager.clear_session.side_effect = RuntimeError("boom")
        resp = client.post(
            "/api/sessions/clear", json={"session_id": "bad"}
        )
        assert resp.status_code == 500


# ── GET /api/courses ────────────────────────────────────────────────────


class TestCoursesEndpoint:
    """Tests for the /api/courses endpoint."""

    def test_courses_returns_stats(self, client, mock_rag_system):
        resp = client.get("/api/courses")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 2
        assert "Building RAG Chatbots" in data["course_titles"]
        assert "Intro to MCP" in data["course_titles"]

    def test_courses_empty_catalog(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        resp = client.get("/api/courses")
        data = resp.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_exception_returns_500(self, client, mock_rag_system):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("db down")
        resp = client.get("/api/courses")
        assert resp.status_code == 500
