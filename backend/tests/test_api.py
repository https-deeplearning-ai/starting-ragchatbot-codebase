"""
API endpoint tests for FastAPI application.

Tests all API endpoints: /health, /api/query, /api/courses,
/api/clear_session, and /api/course_outline
"""

import pytest
from fastapi import status


@pytest.mark.api
class TestHealthEndpoint:
    """Tests for /health endpoint"""

    def test_health_check_success(self, test_app):
        """Test health check returns healthy status"""
        response = test_app.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["environment"] == "test"
        assert "timestamp" in data
        assert "components" in data

    def test_health_check_has_components(self, test_app):
        """Test health check includes all component statuses"""
        response = test_app.get("/health")
        data = response.json()

        components = data["components"]
        assert "vector_store" in components
        assert "ai_generator" in components
        assert "system" in components

    def test_health_check_vector_store_status(self, test_app):
        """Test vector store component in health check"""
        response = test_app.get("/health")
        data = response.json()

        vector_store = data["components"]["vector_store"]
        assert vector_store["status"] == "healthy"
        assert "details" in vector_store


@pytest.mark.api
class TestQueryEndpoint:
    """Tests for /api/query endpoint"""

    def test_query_with_session_id(self, test_app, sample_query_request):
        """Test query with provided session ID"""
        response = test_app.post("/api/query", json=sample_query_request)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == sample_query_request["session_id"]

    def test_query_without_session_id(self, test_app):
        """Test query without session ID creates new session"""
        request_data = {"query": "What is machine learning?"}
        response = test_app.post("/api/query", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"].startswith("session_")

    def test_query_empty_string(self, test_app):
        """Test query with empty string returns validation error"""
        request_data = {"query": ""}
        response = test_app.post("/api/query", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_whitespace_only(self, test_app):
        """Test query with only whitespace returns validation error"""
        request_data = {"query": "   "}
        response = test_app.post("/api/query", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_missing_required_field(self, test_app):
        """Test query without required field returns validation error"""
        request_data = {"session_id": "session_test123"}
        response = test_app.post("/api/query", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_too_long(self, test_app):
        """Test query exceeding max length returns validation error"""
        request_data = {"query": "a" * 2001}  # Max is 2000
        response = test_app.post("/api/query", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_query_response_structure(self, test_app):
        """Test query response has correct structure"""
        request_data = {"query": "Test query"}
        response = test_app.post("/api/query", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)


@pytest.mark.api
class TestCoursesEndpoint:
    """Tests for /api/courses endpoint"""

    def test_get_courses_success(self, test_app):
        """Test getting course statistics"""
        response = test_app.get("/api/courses")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "total_courses" in data
        assert "course_titles" in data

    def test_get_courses_response_structure(self, test_app):
        """Test courses response has correct structure"""
        response = test_app.get("/api/courses")
        data = response.json()

        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert data["total_courses"] >= 0

    def test_get_courses_returns_titles(self, test_app):
        """Test courses endpoint returns course titles"""
        response = test_app.get("/api/courses")
        data = response.json()

        if data["total_courses"] > 0:
            assert len(data["course_titles"]) == data["total_courses"]
            assert all(isinstance(title, str) for title in data["course_titles"])


@pytest.mark.api
class TestClearSessionEndpoint:
    """Tests for /api/clear_session endpoint"""

    def test_clear_session_success(self, test_app):
        """Test clearing a session successfully"""
        request_data = {"session_id": "session_test123"}
        response = test_app.post("/api/clear_session", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "message" in data

    def test_clear_session_invalid_format(self, test_app):
        """Test clearing session with invalid ID format"""
        request_data = {"session_id": "invalid_format"}
        response = test_app.post("/api/clear_session", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_clear_session_missing_field(self, test_app):
        """Test clearing session without session ID"""
        request_data = {}
        response = test_app.post("/api/clear_session", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_clear_session_valid_prefix(self, test_app):
        """Test clearing session with valid session_ prefix"""
        request_data = {"session_id": "session_abc123"}
        response = test_app.post("/api/clear_session", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True


@pytest.mark.api
class TestCourseOutlineEndpoint:
    """Tests for /api/course_outline endpoint"""

    def test_get_course_outline_success(self, test_app):
        """Test getting course outline successfully"""
        request_data = {"course_title": "Test Course"}
        response = test_app.post("/api/course_outline", json=request_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "course_title" in data
        assert "course_link" in data
        assert "lessons" in data
        assert "total_lessons" in data
        assert "formatted_outline" in data

    def test_get_course_outline_response_structure(self, test_app):
        """Test course outline response structure"""
        request_data = {"course_title": "Test Course"}
        response = test_app.post("/api/course_outline", json=request_data)

        data = response.json()

        assert isinstance(data["course_title"], str)
        assert isinstance(data["lessons"], list)
        assert isinstance(data["total_lessons"], int)
        assert isinstance(data["formatted_outline"], str)
        assert data["total_lessons"] == len(data["lessons"])

    def test_get_course_outline_empty_title(self, test_app):
        """Test course outline with empty title"""
        request_data = {"course_title": ""}
        response = test_app.post("/api/course_outline", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_course_outline_whitespace_title(self, test_app):
        """Test course outline with whitespace-only title"""
        request_data = {"course_title": "   "}
        response = test_app.post("/api/course_outline", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_course_outline_missing_field(self, test_app):
        """Test course outline without required field"""
        request_data = {}
        response = test_app.post("/api/course_outline", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_course_outline_too_long(self, test_app):
        """Test course outline with title exceeding max length"""
        request_data = {"course_title": "a" * 201}  # Max is 200
        response = test_app.post("/api/course_outline", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.api
class TestAPIIntegration:
    """Integration tests across multiple API endpoints"""

    def test_query_and_clear_session_flow(self, test_app):
        """Test complete flow: query then clear session"""
        # Step 1: Make a query
        query_request = {"query": "What is the course about?"}
        query_response = test_app.post("/api/query", json=query_request)
        assert query_response.status_code == status.HTTP_200_OK

        session_id = query_response.json()["session_id"]

        # Step 2: Clear the session
        clear_request = {"session_id": session_id}
        clear_response = test_app.post("/api/clear_session", json=clear_request)
        assert clear_response.status_code == status.HTTP_200_OK
        assert clear_response.json()["success"] is True

    def test_get_courses_then_outline(self, test_app):
        """Test getting courses list then requesting outline"""
        # Step 1: Get courses
        courses_response = test_app.get("/api/courses")
        assert courses_response.status_code == status.HTTP_200_OK

        courses_data = courses_response.json()
        if courses_data["total_courses"] > 0:
            # Step 2: Get outline for first course
            course_title = courses_data["course_titles"][0]
            outline_request = {"course_title": course_title}
            outline_response = test_app.post("/api/course_outline", json=outline_request)
            assert outline_response.status_code == status.HTTP_200_OK

    def test_multiple_queries_same_session(self, test_app):
        """Test multiple queries using same session ID"""
        session_id = "session_multiquery"

        # First query
        query1 = {"query": "First question", "session_id": session_id}
        response1 = test_app.post("/api/query", json=query1)
        assert response1.status_code == status.HTTP_200_OK
        assert response1.json()["session_id"] == session_id

        # Second query with same session
        query2 = {"query": "Second question", "session_id": session_id}
        response2 = test_app.post("/api/query", json=query2)
        assert response2.status_code == status.HTTP_200_OK
        assert response2.json()["session_id"] == session_id


@pytest.mark.api
class TestAPIErrorHandling:
    """Tests for API error handling"""

    def test_invalid_json_payload(self, test_app):
        """Test API handles invalid JSON gracefully"""
        response = test_app.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_wrong_content_type(self, test_app):
        """Test API with wrong content type"""
        response = test_app.post(
            "/api/query",
            data="query=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_method_not_allowed(self, test_app):
        """Test using wrong HTTP method"""
        # GET instead of POST for query endpoint
        response = test_app.get("/api/query")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_endpoint_not_found(self, test_app):
        """Test accessing non-existent endpoint"""
        response = test_app.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.api
class TestAPICORS:
    """Tests for CORS configuration"""

    def test_cors_headers_present(self, test_app):
        """Test CORS headers are present in response"""
        response = test_app.options("/api/query")

        # Check that CORS headers are present
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_cors_preflight_request(self, test_app):
        """Test CORS preflight OPTIONS request"""
        response = test_app.options(
            "/api/query",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]