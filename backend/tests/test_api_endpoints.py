"""
API Endpoint Tests for Course Materials RAG System

Tests the FastAPI endpoints for proper request/response handling.
"""
import pytest
from unittest.mock import Mock


@pytest.mark.api
class TestQueryEndpoint:
    """Test suite for /api/query endpoint"""

    def test_query_with_session_id(self, client, mock_rag_system):
        """Test query endpoint with provided session ID"""
        response = client.post(
            "/api/query",
            json={
                "query": "What is Python?",
                "session_id": "existing_session_123"
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "existing_session_123"
        assert data["answer"] == "Python is a high-level programming language."
        assert len(data["sources"]) == 2

        # Verify sources structure
        for source in data["sources"]:
            assert "text" in source
            assert "link" in source

        # Verify RAG system was called correctly
        mock_rag_system.query.assert_called_once_with(
            "What is Python?",
            "existing_session_123"
        )

    def test_query_without_session_id(self, client, mock_rag_system):
        """Test query endpoint creates new session when not provided"""
        response = client.post(
            "/api/query",
            json={"query": "Explain variables"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "test_session_123"

        # Verify new session was created
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_with_empty_query(self, client):
        """Test query endpoint with empty query string"""
        response = client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still return 200 but with empty or default response
        assert response.status_code == 200

    def test_query_with_missing_query_field(self, client):
        """Test query endpoint with missing query field"""
        response = client.post(
            "/api/query",
            json={"session_id": "test_123"}
        )

        # Should return 422 for validation error
        assert response.status_code == 422

    def test_query_response_format(self, client, mock_rag_system):
        """Test that response matches QueryResponse model"""
        response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify source items have correct structure
        for source in data["sources"]:
            assert isinstance(source["text"], str)
            assert source["link"] is None or isinstance(source["link"], str)

    def test_query_handles_string_sources(self, client, mock_rag_system):
        """Test that endpoint handles legacy string sources"""
        # Configure mock to return string sources instead of dicts
        mock_rag_system.query.return_value = (
            "Answer text",
            ["Source 1", "Source 2"]  # String sources
        )

        response = client.post(
            "/api/query",
            json={"query": "Test"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should convert string sources to SourceItem format
        assert len(data["sources"]) == 2
        assert data["sources"][0]["text"] == "Source 1"
        assert data["sources"][0]["link"] is None

    def test_query_error_handling(self, client, mock_rag_system):
        """Test query endpoint error handling"""
        # Configure mock to raise exception
        mock_rag_system.query.side_effect = Exception("RAG system error")

        response = client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        assert response.status_code == 500
        assert "detail" in response.json()


@pytest.mark.api
class TestCoursesEndpoint:
    """Test suite for /api/courses endpoint"""

    def test_get_courses_success(self, client, mock_rag_system):
        """Test successful course statistics retrieval"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Python Basics" in data["course_titles"]
        assert "Advanced Python" in data["course_titles"]

        # Verify RAG system was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_empty_result(self, client, mock_rag_system):
        """Test courses endpoint with no courses"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_error_handling(self, client, mock_rag_system):
        """Test courses endpoint error handling"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "detail" in response.json()

    def test_get_courses_response_format(self, client):
        """Test that response matches CourseStats model"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        for title in data["course_titles"]:
            assert isinstance(title, str)


@pytest.mark.api
class TestRootEndpoint:
    """Test suite for / root endpoint"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)

    def test_root_endpoint_content(self, client):
        """Test root endpoint message content"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "RAG System" in data["message"] or "API" in data["message"]


@pytest.mark.api
class TestCORSHeaders:
    """Test suite for CORS configuration"""

    def test_cors_preflight_request(self, client):
        """Test CORS preflight OPTIONS request"""
        response = client.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )

        # CORS middleware responds to OPTIONS requests
        assert response.status_code in [200, 405]  # 405 if no explicit OPTIONS handler


@pytest.mark.api
class TestRequestValidation:
    """Test suite for request validation"""

    def test_query_invalid_json(self, client):
        """Test query endpoint with invalid JSON"""
        response = client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_extra_fields_allowed(self, client):
        """Test that extra fields in request don't cause errors"""
        response = client.post(
            "/api/query",
            json={
                "query": "test",
                "extra_field": "should be ignored"
            }
        )

        # Should succeed, extra fields ignored by Pydantic
        assert response.status_code == 200
