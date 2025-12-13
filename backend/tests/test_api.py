"""API endpoint tests for the FastAPI application

Tests the /api/query and /api/courses endpoints for proper request/response
handling, error conditions, and integration with the RAG system.
"""
import pytest
from unittest.mock import Mock
from fastapi import HTTPException


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for POST /api/query endpoint"""

    def test_query_with_new_session_creates_session_and_returns_response(
        self, test_client, mock_rag_system, mock_session_manager
    ):
        """Test that a query without session_id creates a new session"""
        # Arrange
        request_data = {
            "query": "What is MCP?"
        }

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify session was created
        mock_session_manager.create_session.assert_called_once()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"
        assert data["answer"] == "MCP stands for Model Context Protocol."
        assert len(data["sources"]) == 2
        assert data["sources"][0]["text"] == "MCP: Build Rich-Context AI Apps - Lesson 1"
        assert data["sources"][0]["url"] == "https://example.com/mcp/lesson1"

    def test_query_with_existing_session_uses_provided_session(
        self, test_client, mock_rag_system, mock_session_manager
    ):
        """Test that a query with session_id uses the provided session"""
        # Arrange
        request_data = {
            "query": "What is MCP?",
            "session_id": "existing-session-456"
        }

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify session was NOT created (existing session used)
        mock_session_manager.create_session.assert_not_called()

        # Verify RAG system was called with the provided session
        mock_rag_system.query.assert_called_once_with(
            "What is MCP?",
            "existing-session-456"
        )

        # Verify response contains the provided session_id
        assert data["session_id"] == "existing-session-456"

    def test_query_returns_correct_response_structure(self, test_client):
        """Test that the response follows the QueryResponse schema"""
        # Arrange
        request_data = {"query": "Test query"}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Validate schema
        assert isinstance(data, dict)
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Validate source structure
        for source in data["sources"]:
            assert "text" in source
            assert "url" in source
            assert isinstance(source["text"], str)
            # url can be str or None
            assert source["url"] is None or isinstance(source["url"], str)

    def test_query_handles_rag_system_errors_gracefully(
        self, test_client, mock_rag_system
    ):
        """Test that RAG system errors return 500 with error detail"""
        # Arrange
        mock_rag_system.query.side_effect = Exception("Database connection failed")
        request_data = {"query": "Test query"}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database connection failed" in data["detail"]

    def test_query_validates_request_body(self, test_client):
        """Test that invalid request bodies are rejected with 422"""
        # Test missing query field
        response = test_client.post("/api/query", json={})
        assert response.status_code == 422

        # Test invalid query type
        response = test_client.post("/api/query", json={"query": 123})
        assert response.status_code == 422

        # Test invalid session_id type
        response = test_client.post("/api/query", json={
            "query": "valid query",
            "session_id": 123  # should be string
        })
        assert response.status_code == 422

    def test_query_with_empty_sources(self, test_client, mock_rag_system):
        """Test query response when RAG system returns no sources"""
        # Arrange
        mock_rag_system.query.return_value = (
            "No relevant information found.",
            []  # Empty sources
        )
        request_data = {"query": "Unknown topic"}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "No relevant information found."
        assert data["sources"] == []
        assert len(data["sources"]) == 0

    def test_query_with_sources_without_urls(self, test_client, mock_rag_system):
        """Test query response when sources have no URLs"""
        # Arrange
        mock_rag_system.query.return_value = (
            "Answer from sources without URLs.",
            [
                {"text": "Source 1", "url": None},
                {"text": "Source 2", "url": None}
            ]
        )
        request_data = {"query": "Test"}

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["sources"]) == 2
        assert data["sources"][0]["url"] is None
        assert data["sources"][1]["url"] is None


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint"""

    def test_get_courses_returns_analytics(self, test_client, mock_rag_system):
        """Test that /api/courses returns course analytics"""
        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify RAG system method was called
        mock_rag_system.get_course_analytics.assert_called_once()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "MCP: Build Rich-Context AI Apps with Anthropic" in data["course_titles"]
        assert "Advanced Retrieval for AI with Chroma" in data["course_titles"]

    def test_get_courses_handles_rag_system_errors(
        self, test_client, mock_rag_system
    ):
        """Test that analytics errors return 500 with error detail"""
        # Arrange
        mock_rag_system.get_course_analytics.side_effect = Exception(
            "Failed to retrieve analytics"
        )

        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Failed to retrieve analytics" in data["detail"]

    def test_get_courses_returns_correct_structure(self, test_client):
        """Test that the response follows the CourseStats schema"""
        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Validate schema
        assert isinstance(data, dict)
        assert "total_courses" in data
        assert "course_titles" in data
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert all(isinstance(title, str) for title in data["course_titles"])

    def test_get_courses_with_empty_catalog(self, test_client, mock_rag_system):
        """Test analytics with no courses in catalog"""
        # Arrange
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        # Act
        response = test_client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []
        assert len(data["course_titles"]) == 0


@pytest.mark.api
class TestAPIErrorHandling:
    """Tests for general API error handling and validation"""

    def test_invalid_json_returns_422(self, test_client):
        """Test that malformed JSON returns 422"""
        # Act
        response = test_client.post(
            "/api/query",
            data="this is not json",
            headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == 422

    def test_missing_required_fields_returns_422(self, test_client):
        """Test that missing required fields return 422"""
        # Missing 'query' field
        response = test_client.post("/api/query", json={"session_id": "test"})
        assert response.status_code == 422

    def test_invalid_content_type_returns_422(self, test_client):
        """Test that requests without JSON content type are rejected"""
        # Act
        response = test_client.post(
            "/api/query",
            data="query=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Assert - FastAPI should reject non-JSON for JSON endpoints
        assert response.status_code == 422

    def test_extra_fields_are_ignored(self, test_client):
        """Test that extra fields in request body are ignored"""
        # Arrange
        request_data = {
            "query": "Test query",
            "extra_field": "should be ignored",
            "another_field": 123
        }

        # Act
        response = test_client.post("/api/query", json=request_data)

        # Assert - Should succeed, extra fields ignored
        assert response.status_code == 200


@pytest.mark.api
class TestAPIIntegration:
    """Integration tests for API endpoint interactions"""

    def test_multiple_queries_with_same_session(
        self, test_client, mock_rag_system, mock_session_manager
    ):
        """Test multiple queries using the same session_id"""
        # Arrange
        session_id = "persistent-session-789"

        # Act - Make multiple requests with same session
        response1 = test_client.post("/api/query", json={
            "query": "What is MCP?",
            "session_id": session_id
        })
        response2 = test_client.post("/api/query", json={
            "query": "Tell me more about MCP",
            "session_id": session_id
        })

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify same session used
        assert response1.json()["session_id"] == session_id
        assert response2.json()["session_id"] == session_id

        # Verify RAG system was called twice with same session
        assert mock_rag_system.query.call_count == 2
        call_args_list = mock_rag_system.query.call_args_list
        assert call_args_list[0][0][1] == session_id
        assert call_args_list[1][0][1] == session_id

    def test_query_and_courses_endpoints_work_together(
        self, test_client, mock_rag_system
    ):
        """Test that query and courses endpoints can be called in sequence"""
        # Act
        query_response = test_client.post("/api/query", json={
            "query": "What courses are available?"
        })
        courses_response = test_client.get("/api/courses")

        # Assert
        assert query_response.status_code == 200
        assert courses_response.status_code == 200

        # Verify both endpoints returned expected data
        assert "answer" in query_response.json()
        assert "total_courses" in courses_response.json()
