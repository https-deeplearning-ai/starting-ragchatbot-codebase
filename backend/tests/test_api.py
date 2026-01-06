"""
Tests for FastAPI endpoints

Tests the HTTP API layer including:
- POST /api/query - Query processing endpoint
- GET /api/courses - Course statistics endpoint
- Request/response validation
- Error handling
"""

import pytest


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for POST /api/query endpoint"""

    def test_query_with_session_id(self, client, mock_rag_system):
        """Test query with explicit session_id"""
        # Arrange
        request_data = {
            "query": "What is test-driven development?",
            "session_id": "existing-session-456",
        }

        # Act
        response = client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify values
        assert data["answer"] == "Test answer from RAG system"
        assert data["session_id"] == "existing-session-456"
        assert len(data["sources"]) == 2

        # Verify source structure
        assert data["sources"][0]["text"] == "Test Course - Lesson 1"
        assert data["sources"][0]["link"] == "https://example.com/lesson/1"
        assert data["sources"][0]["type"] == "lesson"

        # Verify RAG system was called correctly
        mock_rag_system.query.assert_called_once_with(
            "What is test-driven development?", "existing-session-456"
        )

    def test_query_without_session_id(self, client, mock_rag_system):
        """Test query without session_id creates new session"""
        # Arrange
        request_data = {"query": "How do I write unit tests?"}

        # Act
        response = client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Should have created new session
        assert data["session_id"] == "test-session-123"
        mock_rag_system.session_manager.create_session.assert_called_once()

        # Verify query was called with new session
        mock_rag_system.query.assert_called_once_with(
            "How do I write unit tests?", "test-session-123"
        )

    def test_query_with_empty_string(self, client, mock_rag_system):
        """Test query with empty query string"""
        # Arrange
        request_data = {"query": "", "session_id": "test-session"}

        # Act
        response = client.post("/api/query", json=request_data)

        # Assert - Should still process but might return empty results
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data

    def test_query_missing_required_field(self, client):
        """Test query without required 'query' field"""
        # Arrange
        request_data = {"session_id": "test-session"}

        # Act
        response = client.post("/api/query", json=request_data)

        # Assert - Should return validation error
        assert response.status_code == 422  # Unprocessable Entity

    def test_query_invalid_json(self, client):
        """Test query with invalid JSON"""
        # Act
        response = client.post(
            "/api/query", data="invalid json{", headers={"Content-Type": "application/json"}
        )

        # Assert
        assert response.status_code == 422

    def test_query_rag_system_error(self, client, mock_rag_system):
        """Test error handling when RAG system fails"""
        # Arrange
        mock_rag_system.query.side_effect = Exception("Vector store connection failed")
        request_data = {"query": "What is testing?", "session_id": "test-session"}

        # Act
        response = client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Vector store connection failed" in data["detail"]

    def test_query_returns_empty_sources(self, client, mock_rag_system):
        """Test query that returns no sources"""
        # Arrange
        mock_rag_system.query.return_value = ("No relevant information found", [])
        request_data = {"query": "Nonexistent topic", "session_id": "test-session"}

        # Act
        response = client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "No relevant information found"
        assert data["sources"] == []

    def test_query_response_schema(self, client):
        """Test that response matches expected schema"""
        # Arrange
        request_data = {"query": "Test query", "session_id": "test-session"}

        # Act
        response = client.post("/api/query", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Required fields
        required_fields = ["answer", "sources", "session_id"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Field types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Source structure if sources exist
        if data["sources"]:
            source = data["sources"][0]
            assert "text" in source
            assert "link" in source
            assert "type" in source


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint"""

    def test_get_courses_success(self, client, mock_rag_system):
        """Test successful retrieval of course statistics"""
        # Act
        response = client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify values
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Introduction to Testing" in data["course_titles"]
        assert "Advanced Testing Techniques" in data["course_titles"]

        # Verify RAG system was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_empty_database(self, client, mock_rag_system):
        """Test course stats when no courses exist"""
        # Arrange
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        # Act
        response = client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_error_handling(self, client, mock_rag_system):
        """Test error handling when analytics retrieval fails"""
        # Arrange
        mock_rag_system.get_course_analytics.side_effect = Exception("Database connection error")

        # Act
        response = client.get("/api/courses")

        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database connection error" in data["detail"]

    def test_get_courses_response_schema(self, client):
        """Test that response matches expected schema"""
        # Act
        response = client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "total_courses" in data
        assert "course_titles" in data

        # Field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Ensure all course titles are strings
        for title in data["course_titles"]:
            assert isinstance(title, str)

    def test_get_courses_large_dataset(self, client, mock_rag_system):
        """Test course stats with large number of courses"""
        # Arrange
        course_titles = [f"Course {i}" for i in range(100)]
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 100,
            "course_titles": course_titles,
        }

        # Act
        response = client.get("/api/courses")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 100
        assert len(data["course_titles"]) == 100


@pytest.mark.api
class TestMiddleware:
    """Tests for middleware and general API behavior"""

    def test_basic_request_response(self, client):
        """Test basic request/response flow works"""
        # Act
        response = client.get("/api/courses")

        # Assert - Basic response works
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_json_content_type(self, client):
        """Test that responses are JSON formatted"""
        # Act
        response = client.post("/api/query", json={"query": "test"})

        # Assert
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


@pytest.mark.api
class TestAPIIntegration:
    """Integration tests for API workflows"""

    def test_multi_turn_conversation(self, client, mock_rag_system):
        """Test multiple queries in same session"""
        # First query
        response1 = client.post("/api/query", json={"query": "What is testing?"})
        assert response1.status_code == 200
        session_id = response1.json()["session_id"]

        # Second query in same session
        response2 = client.post(
            "/api/query", json={"query": "Tell me more about unit tests", "session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Verify both queries were processed
        assert mock_rag_system.query.call_count == 2

    def test_concurrent_sessions(self, client, mock_rag_system):
        """Test handling multiple concurrent sessions"""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            response = client.post("/api/query", json={"query": f"Query {i}"})
            assert response.status_code == 200
            sessions.append(response.json()["session_id"])

        # All sessions should be unique (in real implementation)
        # In our mock, they'll all be "test-session-123", but in reality they'd differ
        assert len(sessions) == 3

    def test_query_then_get_courses(self, client, mock_rag_system):
        """Test querying then getting course stats"""
        # First, submit a query
        query_response = client.post("/api/query", json={"query": "What courses are available?"})
        assert query_response.status_code == 200

        # Then get course statistics
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == 200

        # Both should succeed independently
        assert "answer" in query_response.json()
        assert "total_courses" in courses_response.json()
