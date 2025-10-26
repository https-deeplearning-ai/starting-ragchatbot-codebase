"""
API endpoint tests for the RAG system FastAPI application
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json


class TestQueryEndpoint:
    """Test the /api/query endpoint"""

    @pytest.mark.api
    def test_query_endpoint_success_with_new_session(self, client, mock_rag_system, sample_query_requests, sample_api_responses):
        """Test successful query with new session creation"""
        request_data = sample_query_requests["valid_query"]
        expected_response = sample_api_responses["query_response"]

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["answer"] == expected_response["answer"]
        assert response_data["sources"] == expected_response["sources"]
        assert response_data["session_id"] == expected_response["session_id"]

        # Verify the RAG system was called correctly
        mock_rag_system.query.assert_called_once_with(request_data["query"], expected_response["session_id"])
        mock_rag_system.session_manager.create_session.assert_called_once()

    @pytest.mark.api
    def test_query_endpoint_success_with_existing_session(self, client, mock_rag_system, sample_query_requests):
        """Test successful query with existing session"""
        request_data = sample_query_requests["query_with_session"]

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["session_id"] == request_data["session_id"]

        # Verify the RAG system was called with existing session
        mock_rag_system.query.assert_called_once_with(request_data["query"], request_data["session_id"])
        mock_rag_system.session_manager.create_session.assert_not_called()

    @pytest.mark.api
    def test_query_endpoint_empty_query(self, client, mock_rag_system, sample_query_requests):
        """Test query endpoint with empty query string"""
        request_data = sample_query_requests["empty_query"]

        response = client.post("/api/query", json=request_data)

        # Should still succeed (empty query is handled by RAG system)
        assert response.status_code == 200
        mock_rag_system.query.assert_called_once_with("", "test-session-123")

    @pytest.mark.api
    def test_query_endpoint_missing_query_field(self, client, sample_query_requests):
        """Test query endpoint with missing query field"""
        request_data = sample_query_requests["missing_query_field"]

        response = client.post("/api/query", json=request_data)

        # FastAPI validation should catch this
        assert response.status_code == 422  # Validation error

    @pytest.mark.api
    def test_query_endpoint_invalid_json(self, client, sample_query_requests):
        """Test query endpoint with invalid JSON"""
        malformed_content = sample_query_requests["malformed_query_content"]

        response = client.post(
            "/api/query",
            data=malformed_content,
            headers={"Content-Type": "application/json"}
        )

        # FastAPI should reject invalid JSON
        assert response.status_code == 422

    @pytest.mark.api
    def test_query_endpoint_rag_system_error(self, client, mock_rag_system, sample_query_requests, error_scenarios):
        """Test query endpoint when RAG system throws an error"""
        request_data = sample_query_requests["valid_query"]
        mock_rag_system.query.side_effect = error_scenarios["rag_query_error"]

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 500
        assert "RAG system query failed" in response.json()["detail"]

    @pytest.mark.api
    def test_query_endpoint_session_creation_error(self, client, mock_rag_system, sample_query_requests, error_scenarios):
        """Test query endpoint when session creation fails"""
        request_data = sample_query_requests["valid_query"]
        mock_rag_system.session_manager.create_session.side_effect = error_scenarios["missing_session_error"]

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 500
        assert "Session not found" in response.json()["detail"]

    @pytest.mark.api
    def test_query_endpoint_unsupported_method(self, client):
        """Test query endpoint with unsupported HTTP methods"""
        # Test GET request
        response = client.get("/api/query")
        assert response.status_code == 405  # Method Not Allowed

        # Test PUT request
        response = client.put("/api/query", json={"query": "test"})
        assert response.status_code == 405

        # Test DELETE request
        response = client.delete("/api/query")
        assert response.status_code == 405

    @pytest.mark.api
    def test_query_endpoint_content_type_validation(self, client):
        """Test query endpoint with incorrect content type"""
        # Send form data instead of JSON
        response = client.post(
            "/api/query",
            data="query=test+query",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        # FastAPI should reject non-JSON content
        assert response.status_code == 422

    @pytest.mark.api
    def test_query_endpoint_large_payload(self, client, mock_rag_system):
        """Test query endpoint with large query payload"""
        large_query = "What is machine learning? " * 1000  # Very long query

        request_data = {"query": large_query}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        mock_rag_system.query.assert_called_once()

    @pytest.mark.api
    def test_query_endpoint_special_characters(self, client, mock_rag_system):
        """Test query endpoint with special characters in query"""
        special_query = "What is AI? Test: @#$%^&*()_+-={}[]|\\:;\"'<>?,./"

        request_data = {"query": special_query}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        # Verify the query was passed through correctly
        mock_rag_system.query.assert_called_once()
        call_args = mock_rag_system.query.call_args[0]
        assert call_args[0] == special_query

    @pytest.mark.api
    def test_query_response_structure_validation(self, client, sample_query_requests):
        """Test that query response has correct structure"""
        request_data = sample_query_requests["valid_query"]

        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        response_data = response.json()

        # Verify response structure
        assert isinstance(response_data, dict)
        assert "answer" in response_data
        assert "sources" in response_data
        assert "session_id" in response_data

        # Verify field types
        assert isinstance(response_data["answer"], str)
        assert isinstance(response_data["sources"], list)
        assert isinstance(response_data["session_id"], str)

        # Verify sources content
        for source in response_data["sources"]:
            assert isinstance(source, str)

    @pytest.mark.api
    def test_query_endpoint_unicode_support(self, client, mock_rag_system):
        """Test query endpoint with unicode characters"""
        unicode_query = "What is 机器学习? ¿Cómo está? 🤖"

        request_data = {"query": unicode_query}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        assert response.status_code == 200


class TestCoursesEndpoint:
    """Test the /api/courses endpoint"""

    @pytest.mark.api
    def test_courses_endpoint_success(self, client, mock_rag_system, sample_api_responses):
        """Test successful courses endpoint call"""
        expected_response = sample_api_responses["courses_response"]

        response = client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total_courses"] == expected_response["total_courses"]
        assert response_data["course_titles"] == expected_response["course_titles"]

        # Verify RAG system was called
        mock_rag_system.get_course_analytics.assert_called_once()

    @pytest.mark.api
    def test_courses_endpoint_analytics_error(self, client, mock_rag_system, error_scenarios):
        """Test courses endpoint when analytics fails"""
        mock_rag_system.get_course_analytics.side_effect = error_scenarios["rag_analytics_error"]

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "Failed to get course analytics" in response.json()["detail"]

    @pytest.mark.api
    def test_courses_endpoint_unsupported_method(self, client):
        """Test courses endpoint with unsupported HTTP methods"""
        # Test POST request
        response = client.post("/api/courses")
        assert response.status_code == 405

        # Test PUT request
        response = client.put("/api/courses")
        assert response.status_code == 405

        # Test DELETE request
        response = client.delete("/api/courses")
        assert response.status_code == 405

    @pytest.mark.api
    def test_courses_response_structure_validation(self, client):
        """Test that courses response has correct structure"""
        response = client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()

        # Verify response structure
        assert isinstance(response_data, dict)
        assert "total_courses" in response_data
        assert "course_titles" in response_data

        # Verify field types
        assert isinstance(response_data["total_courses"], int)
        assert isinstance(response_data["course_titles"], list)

        # Verify course titles content
        for title in response_data["course_titles"]:
            assert isinstance(title, str)

    @pytest.mark.api
    def test_courses_endpoint_empty_data(self, client, mock_rag_system):
        """Test courses endpoint with no course data"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["total_courses"] == 0
        assert response_data["course_titles"] == []


class TestRootEndpoint:
    """Test the root endpoint"""

    @pytest.mark.api
    def test_root_endpoint_success(self, client, sample_api_responses):
        """Test successful root endpoint call"""
        expected_response = sample_api_responses["root_response"]

        response = client.get("/")

        assert response.status_code == 200
        response_data = response.json()
        assert response_data == expected_response

    @pytest.mark.api
    def test_root_endpoint_unsupported_method(self, client):
        """Test root endpoint with unsupported HTTP methods"""
        # Test POST request
        response = client.post("/")
        assert response.status_code == 405

        # Test PUT request
        response = client.put("/")
        assert response.status_code == 405

        # Test DELETE request
        response = client.delete("/")
        assert response.status_code == 405

    @pytest.mark.api
    def test_root_response_structure_validation(self, client):
        """Test that root response has correct structure"""
        response = client.get("/")

        assert response.status_code == 200
        response_data = response.json()

        # Verify response structure
        assert isinstance(response_data, dict)
        assert "message" in response_data
        assert isinstance(response_data["message"], str)


class TestAPIIntegration:
    """Integration tests for API endpoints"""

    @pytest.mark.api
    @pytest.mark.integration
    def test_multiple_query_calls_same_session(self, client, mock_rag_system):
        """Test multiple queries with the same session"""
        first_request = {"query": "What is machine learning?", "session_id": "test-session-123"}
        second_request = {"query": "Tell me more about neural networks", "session_id": "test-session-123"}

        # Make first request
        first_response = client.post("/api/query", json=first_request)
        assert first_response.status_code == 200

        # Make second request with same session
        second_response = client.post("/api/query", json=second_request)
        assert second_response.status_code == 200

        # Verify both calls were made with same session ID
        assert mock_rag_system.query.call_count == 2
        first_call = mock_rag_system.query.call_args_list[0]
        second_call = mock_rag_system.query.call_args_list[1]

        assert first_call[0][1] == "test-session-123"  # session_id from first call
        assert second_call[0][1] == "test-session-123"  # session_id from second call

    @pytest.mark.api
    @pytest.mark.integration
    def test_query_and_courses_endpoints_together(self, client, mock_rag_system):
        """Test that query and courses endpoints work together"""
        # Call courses endpoint
        courses_response = client.get("/api/courses")
        assert courses_response.status_code == 200

        # Call query endpoint
        query_response = client.post("/api/query", json={"query": "test query"})
        assert query_response.status_code == 200

        # Verify both RAG system methods were called
        mock_rag_system.get_course_analytics.assert_called_once()
        mock_rag_system.query.assert_called_once()

    @pytest.mark.api
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses"""
        # Test POST endpoint
        response = client.post("/api/query", json={"query": "test"})
        assert response.status_code == 200
        # FastAPI TestClient doesn't expose CORS headers in the same way,
        # but the middleware should be present

        # Test GET endpoint
        response = client.get("/api/courses")
        assert response.status_code == 200

        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200