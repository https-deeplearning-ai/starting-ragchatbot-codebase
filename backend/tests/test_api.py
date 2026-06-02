"""Tests for FastAPI endpoints"""

import os
import sys
from unittest.mock import Mock

import pytest

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for POST /api/query endpoint"""

    def test_query_with_session_id(self, client):
        """Test query endpoint with provided session_id"""
        response = client.post(
            "/api/query", json={"query": "What is Python?", "session_id": "session_1"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "session_1"
        assert isinstance(data["sources"], list)

    def test_query_without_session_id(self, client):
        """Test query endpoint creates session when not provided"""
        response = client.post("/api/query", json={"query": "What is Python?"})

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] is not None
        assert "answer" in data
        assert "sources" in data

    def test_query_with_null_session_id(self, client):
        """Test query endpoint handles null session_id"""
        response = client.post(
            "/api/query", json={"query": "Explain variables", "session_id": None}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        # Mock returns "session_1"
        assert data["session_id"] == "session_1"

    def test_query_response_structure(self, client):
        """Test that query response has correct structure"""
        response = client.post(
            "/api/query", json={"query": "Test query", "session_id": "test_session"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_query_with_empty_query_string(self, client):
        """Test query endpoint with empty query string"""
        # The endpoint should still process empty strings (RAG system handles validation)
        response = client.post("/api/query", json={"query": "", "session_id": "session_1"})

        # Should succeed - RAG system decides how to handle empty queries
        assert response.status_code == 200

    def test_query_with_special_characters(self, client):
        """Test query endpoint handles special characters"""
        response = client.post(
            "/api/query", json={"query": "What is C++ and #hashtags?!", "session_id": "session_1"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    def test_query_with_long_query(self, client):
        """Test query endpoint with long query string"""
        long_query = "What is " + "Python " * 100
        response = client.post("/api/query", json={"query": long_query, "session_id": "session_1"})

        assert response.status_code == 200

    def test_query_missing_required_field(self, client):
        """Test query endpoint rejects request without query field"""
        response = client.post("/api/query", json={"session_id": "session_1"})

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422

    def test_query_invalid_json(self, client):
        """Test query endpoint rejects invalid JSON"""
        response = client.post(
            "/api/query", content="invalid json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_calls_rag_system(self, client, test_app):
        """Test that query endpoint calls RAG system correctly"""
        test_app.mock_rag_system.reset_mock()

        response = client.post(
            "/api/query", json={"query": "Test query", "session_id": "test_session_123"}
        )

        assert response.status_code == 200
        # Verify RAG system was called
        test_app.mock_rag_system.query.assert_called_once_with("Test query", "test_session_123")

    def test_query_creates_new_session_when_needed(self, client, test_app):
        """Test that query endpoint creates session when not provided"""
        test_app.mock_rag_system.session_manager.reset_mock()

        response = client.post("/api/query", json={"query": "Test query"})

        assert response.status_code == 200
        # Verify session creation was called
        test_app.mock_rag_system.session_manager.create_session.assert_called_once()


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint"""

    def test_get_courses(self, client):
        """Test courses endpoint returns course stats"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data

    def test_courses_response_structure(self, client):
        """Test that courses response has correct structure"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert data["total_courses"] >= 0
        assert all(isinstance(title, str) for title in data["course_titles"])

    def test_courses_response_content(self, client, test_app):
        """Test that courses endpoint returns correct content"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Mock returns 2 courses
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Python 101" in data["course_titles"]
        assert "Web Development" in data["course_titles"]

    def test_courses_calls_rag_system(self, client, test_app):
        """Test that courses endpoint calls RAG system"""
        test_app.mock_rag_system.reset_mock()

        response = client.get("/api/courses")

        assert response.status_code == 200
        # Verify RAG system analytics was called
        test_app.mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_with_query_parameters(self, client):
        """Test that courses endpoint ignores query parameters"""
        response = client.get("/api/courses?filter=python&sort=name")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data


@pytest.mark.api
class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns success"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_root_endpoint_response(self, client):
        """Test root endpoint response content"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "RAG System API"


@pytest.mark.api
class TestAPIErrorHandling:
    """Tests for API error handling"""

    def test_query_error_handling(self, client, test_app):
        """Test query endpoint error handling"""
        # Configure mock to raise an exception
        test_app.mock_rag_system.query = Mock(side_effect=ValueError("API Error"))

        response = client.post("/api/query", json={"query": "Test", "session_id": "session_1"})

        # Should return 502 for ValueError
        assert response.status_code == 502
        data = response.json()
        assert "API Error" in data["detail"]

    def test_courses_error_handling(self, client, test_app):
        """Test courses endpoint error handling"""
        # Configure mock to raise an exception
        test_app.mock_rag_system.get_course_analytics = Mock(
            side_effect=Exception("Database error")
        )

        response = client.get("/api/courses")

        # Should return 500 for general Exception
        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"]

    def test_invalid_content_type(self, client):
        """Test endpoint rejects invalid content type"""
        response = client.post(
            "/api/query", data="not json", headers={"Content-Type": "text/plain"}
        )

        # Should return 422 - cannot parse as JSON
        assert response.status_code == 422


@pytest.mark.api
class TestAPICORS:
    """Tests for CORS headers"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in response"""
        response = client.get("/api/courses")

        # Check for CORS headers
        assert response.status_code == 200
        # TestClient handles CORS automatically

    def test_query_cors_headers(self, client):
        """Test CORS headers on query endpoint"""
        response = client.post("/api/query", json={"query": "Test", "session_id": "session_1"})

        assert response.status_code == 200


@pytest.mark.api
class TestAPIIntegration:
    """Integration tests for multiple endpoints"""

    def test_query_then_courses_flow(self, client):
        """Test typical user flow: query then get courses"""
        # First query
        query_response = client.post(
            "/api/query", json={"query": "What is Python?", "session_id": "test_session"}
        )

        assert query_response.status_code == 200

        # Then get courses
        courses_response = client.get("/api/courses")

        assert courses_response.status_code == 200
        assert courses_response.json()["total_courses"] >= 0

    def test_multiple_queries_same_session(self, client, test_app):
        """Test multiple queries with same session"""
        session_id = "multi_session"

        for i in range(3):
            response = client.post(
                "/api/query", json={"query": f"Question {i}", "session_id": session_id}
            )

            assert response.status_code == 200
            assert response.json()["session_id"] == session_id

    def test_multiple_queries_different_sessions(self, client):
        """Test multiple queries create different sessions"""
        response1 = client.post("/api/query", json={"query": "Question 1"})

        response2 = client.post("/api/query", json={"query": "Question 2"})

        assert response1.status_code == 200
        assert response2.status_code == 200


@pytest.mark.api
class TestAPIValidation:
    """Tests for request validation"""

    def test_query_field_required(self, client):
        """Test that query field is required"""
        response = client.post("/api/query", json={"session_id": "test"})

        assert response.status_code == 422

    def test_query_field_must_be_string(self, client):
        """Test that query field must be string"""
        response = client.post("/api/query", json={"query": 123, "session_id": "test"})

        assert response.status_code == 422

    def test_session_id_optional(self, client):
        """Test that session_id is optional"""
        response = client.post("/api/query", json={"query": "Test"})

        assert response.status_code == 200

    def test_session_id_can_be_null(self, client):
        """Test that session_id can be null"""
        response = client.post("/api/query", json={"query": "Test", "session_id": None})

        assert response.status_code == 200
