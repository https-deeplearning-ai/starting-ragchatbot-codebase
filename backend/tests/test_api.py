"""API endpoint tests for the RAG system."""

import pytest
from unittest.mock import Mock


class TestQueryEndpoint:
    """Tests for POST /api/query endpoint."""

    async def test_query_returns_response(self, client, sample_query_request):
        """Test that query endpoint returns a valid response."""
        response = await client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

    async def test_query_creates_session_when_not_provided(
        self, client, sample_query_request, mock_rag_system
    ):
        """Test that a new session is created when not provided."""
        response = await client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test_session_123"
        mock_rag_system.session_manager.create_session.assert_called_once()

    async def test_query_uses_existing_session(
        self, client, sample_query_with_session, mock_rag_system
    ):
        """Test that existing session ID is used when provided."""
        response = await client.post("/api/query", json=sample_query_with_session)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing_session_456"
        mock_rag_system.query.assert_called_once_with(
            "Tell me more about neural networks",
            "existing_session_456"
        )

    async def test_query_returns_sources(self, client, sample_query_request):
        """Test that query returns sources in response."""
        response = await client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) > 0
        assert "title" in data["sources"][0]
        assert "url" in data["sources"][0]

    async def test_query_handles_error(self, client, test_app, sample_query_request):
        """Test that query endpoint handles errors gracefully."""
        test_app.state.rag_system.query.side_effect = Exception("Test error")

        response = await client.post("/api/query", json=sample_query_request)

        assert response.status_code == 500
        assert "Test error" in response.json()["detail"]

    async def test_query_requires_query_field(self, client):
        """Test that query field is required."""
        response = await client.post("/api/query", json={})

        assert response.status_code == 422  # Validation error

    async def test_query_with_empty_string(self, client):
        """Test query with empty string."""
        response = await client.post("/api/query", json={"query": ""})

        # Empty string is valid, just returns a response
        assert response.status_code == 200


class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint."""

    async def test_courses_returns_stats(self, client):
        """Test that courses endpoint returns course statistics."""
        response = await client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3

    async def test_courses_returns_course_titles(self, client):
        """Test that courses endpoint returns list of course titles."""
        response = await client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "Course A" in data["course_titles"]
        assert "Course B" in data["course_titles"]
        assert "Course C" in data["course_titles"]

    async def test_courses_handles_error(self, client, test_app):
        """Test that courses endpoint handles errors gracefully."""
        test_app.state.rag_system.get_course_analytics.side_effect = Exception(
            "Analytics error"
        )

        response = await client.get("/api/courses")

        assert response.status_code == 500
        assert "Analytics error" in response.json()["detail"]


class TestSessionEndpoint:
    """Tests for POST /api/session/new endpoint."""

    async def test_new_session_creates_session(self, client, mock_rag_system):
        """Test that new session endpoint creates a session."""
        response = await client.post("/api/session/new")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == "test_session_123"

    async def test_new_session_clears_old_session(self, client, mock_rag_system):
        """Test that new session clears old session when provided."""
        response = await client.post(
            "/api/session/new",
            json={"session_id": "old_session_789"}
        )

        assert response.status_code == 200
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "old_session_789"
        )


class TestRootEndpoint:
    """Tests for GET / endpoint."""

    async def test_root_returns_status(self, client):
        """Test that root endpoint returns status."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestRequestValidation:
    """Tests for request validation."""

    async def test_query_invalid_json(self, client):
        """Test that invalid JSON returns error."""
        response = await client.post(
            "/api/query",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    async def test_query_wrong_content_type(self, client):
        """Test query with wrong content type."""
        response = await client.post(
            "/api/query",
            content="query=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 422
