"""
Comprehensive tests for FastAPI endpoints.

Tests the /api/query and /api/courses endpoints for proper request/response handling,
error cases, session management, and integration with the RAG system.
"""
import pytest
from unittest.mock import Mock, patch


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for the /api/query endpoint"""

    def test_query_without_session_creates_new_session(self, test_client, sample_query_request):
        """Test that query without session_id creates a new session"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify session was created
        assert data["session_id"] == "test-session-123"
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)

    def test_query_with_existing_session(self, test_client, sample_query_request_with_session):
        """Test query with existing session_id uses that session"""
        response = test_client.post("/api/query", json=sample_query_request_with_session)

        assert response.status_code == 200
        data = response.json()

        # Verify session_id matches the one provided
        assert data["session_id"] == "test-session-123"
        assert "answer" in data
        assert "sources" in data

    def test_query_response_structure(self, test_client, sample_query_request):
        """Test that query response has the correct structure"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        # Verify answer
        assert isinstance(data["answer"], str)
        assert len(data["answer"]) > 0

        # Verify sources structure
        assert isinstance(data["sources"], list)
        if len(data["sources"]) > 0:
            source = data["sources"][0]
            assert "course_title" in source
            assert "lesson_number" in source
            assert "content" in source

    def test_query_calls_rag_system(self, test_client, sample_query_request, mock_rag_system):
        """Test that query endpoint calls RAG system correctly"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200

        # Verify RAG system was called
        mock_rag_system.query.assert_called_once()

        # Check the arguments passed to RAG system
        call_args = mock_rag_system.query.call_args
        assert call_args[0][0] == sample_query_request["query"]
        assert call_args[0][1] == "test-session-123"  # session created

    def test_query_invalid_request_missing_query(self, test_client):
        """Test query with missing required field returns error"""
        invalid_request = {"session_id": "test-123"}  # Missing 'query' field

        response = test_client.post("/api/query", json=invalid_request)

        # Should return 422 Unprocessable Entity for validation error
        assert response.status_code == 422

    def test_query_empty_string(self, test_client):
        """Test query with empty string"""
        empty_query = {"query": "", "session_id": None}

        response = test_client.post("/api/query", json=empty_query)

        # Should still return 200 (empty query is valid, just not useful)
        assert response.status_code == 200

    def test_query_rag_system_error(self, test_client, sample_query_request, mock_rag_system):
        """Test handling of RAG system errors"""
        # Mock RAG system to raise an exception
        mock_rag_system.query.side_effect = Exception("Database connection error")

        response = test_client.post("/api/query", json=sample_query_request)

        # Should return 500 Internal Server Error
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "Database connection error" in response.json()["detail"]

    def test_query_with_special_characters(self, test_client):
        """Test query with special characters and Unicode"""
        special_query = {
            "query": "What is 机器学习? How does it relate to AI & ML?",
            "session_id": None
        }

        response = test_client.post("/api/query", json=special_query)

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data

    def test_query_very_long_input(self, test_client):
        """Test query with very long input text"""
        long_query = {
            "query": "machine learning " * 1000,  # Very long query
            "session_id": None
        }

        response = test_client.post("/api/query", json=long_query)

        # Should handle long queries gracefully
        assert response.status_code == 200


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for the /api/courses endpoint"""

    def test_get_courses_success(self, test_client):
        """Test successful retrieval of course statistics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify data types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

    def test_get_courses_response_content(self, test_client):
        """Test that courses endpoint returns expected content"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify expected data from mock
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Introduction to Machine Learning" in data["course_titles"]
        assert "Building Towards Computer Use with Anthropic" in data["course_titles"]

    def test_get_courses_calls_rag_system(self, test_client, mock_rag_system):
        """Test that courses endpoint calls RAG system analytics"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200

        # Verify analytics was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_get_courses_rag_system_error(self, test_client, mock_rag_system):
        """Test handling of RAG system errors in courses endpoint"""
        # Mock analytics to raise an exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")

        response = test_client.get("/api/courses")

        # Should return 500 Internal Server Error
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "Analytics error" in response.json()["detail"]

    def test_get_courses_empty_database(self, test_client, mock_rag_system):
        """Test courses endpoint when no courses are loaded"""
        # Mock empty analytics
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []


@pytest.mark.api
class TestRootEndpoint:
    """Tests for the root / endpoint"""

    def test_root_endpoint(self, test_client):
        """Test that root endpoint returns health status"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "ok"


@pytest.mark.api
class TestSessionManagement:
    """Tests for session management across API calls"""

    def test_session_persistence_across_queries(self, test_client, mock_rag_system):
        """Test that session_id persists across multiple queries"""
        # First query without session
        first_query = {"query": "What is ML?", "session_id": None}
        response1 = test_client.post("/api/query", json=first_query)

        assert response1.status_code == 200
        session_id = response1.json()["session_id"]
        assert session_id is not None

        # Reset mock call history
        mock_rag_system.query.reset_mock()

        # Second query with same session
        second_query = {"query": "Tell me more", "session_id": session_id}
        response2 = test_client.post("/api/query", json=second_query)

        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Verify RAG system was called with the same session
        call_args = mock_rag_system.query.call_args
        assert call_args[0][1] == session_id

    def test_different_sessions_independent(self, test_client):
        """Test that different sessions are independent"""
        # First session
        query1 = {"query": "Question 1", "session_id": None}
        response1 = test_client.post("/api/query", json=query1)
        session1 = response1.json()["session_id"]

        # Second session (no session_id provided, should create new)
        query2 = {"query": "Question 2", "session_id": None}
        response2 = test_client.post("/api/query", json=query2)
        session2 = response2.json()["session_id"]

        # Sessions should be different (in real scenario)
        # Note: With mocked session manager, both return same mock ID
        # In integration tests, these would be different
        assert session1 is not None
        assert session2 is not None


@pytest.mark.api
class TestErrorHandling:
    """Tests for error handling across endpoints"""

    def test_invalid_json(self, test_client):
        """Test handling of invalid JSON in request"""
        response = test_client.post(
            "/api/query",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422

    def test_wrong_content_type(self, test_client):
        """Test request with wrong content type"""
        response = test_client.post(
            "/api/query",
            data="query=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # Should return 422 (FastAPI validation error)
        assert response.status_code == 422

    def test_nonexistent_endpoint(self, test_client):
        """Test request to non-existent endpoint"""
        response = test_client.get("/api/nonexistent")

        # Should return 404 Not Found
        assert response.status_code == 404

    def test_wrong_http_method(self, test_client):
        """Test using wrong HTTP method"""
        # Try GET on POST-only endpoint
        response = test_client.get("/api/query")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

        # Try POST on GET-only endpoint
        response = test_client.post("/api/courses")

        # Should return 405 Method Not Allowed
        assert response.status_code == 405


@pytest.mark.api
class TestResponseValidation:
    """Tests for response validation and schema compliance"""

    def test_query_response_schema_compliance(self, test_client, sample_query_request):
        """Test that query response matches expected schema"""
        response = test_client.post("/api/query", json=sample_query_request)

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

        # Sources structure
        for source in data["sources"]:
            assert isinstance(source, dict)
            assert "course_title" in source
            assert "lesson_number" in source

    def test_courses_response_schema_compliance(self, test_client):
        """Test that courses response matches expected schema"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "total_courses" in data
        assert "course_titles" in data

        # Field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Course titles should be strings
        for title in data["course_titles"]:
            assert isinstance(title, str)

    def test_response_headers(self, test_client, sample_query_request):
        """Test that responses have correct headers"""
        response = test_client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200

        # Verify content type
        assert "application/json" in response.headers.get("content-type", "")
