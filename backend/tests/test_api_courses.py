"""
API endpoint tests for /api/courses

Tests the GET /api/courses endpoint for:
- Successful retrieval of course statistics
- Response structure validation
- Error handling
- Empty course catalog handling
"""
import pytest
from httpx import AsyncClient


@pytest.mark.api
class TestCoursesEndpoint:
    """Test suite for /api/courses endpoint"""

    async def test_get_courses_success(self, async_client: AsyncClient, mock_rag_system):
        """Test successful retrieval of course statistics"""
        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data

        # Verify RAG system method was called
        mock_rag_system.get_course_analytics.assert_called_once()

    async def test_get_courses_response_structure(self, async_client: AsyncClient):
        """Test that courses response has correct structure and types"""
        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)

        # Verify content matches expected values from mock
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Python Course" in data["course_titles"]
        assert "JavaScript Course" in data["course_titles"]

    async def test_get_courses_titles_list(self, async_client: AsyncClient):
        """Test that course_titles is a list of strings"""
        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # All titles should be strings
        assert all(isinstance(title, str) for title in data["course_titles"])

    async def test_get_courses_total_matches_list_length(self, async_client: AsyncClient):
        """Test that total_courses matches length of course_titles"""
        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Total should match list length
        assert data["total_courses"] == len(data["course_titles"])

    async def test_get_courses_empty_catalog(
        self,
        async_client: AsyncClient,
        mock_rag_system
    ):
        """Test courses endpoint when no courses exist"""
        # Mock empty course catalog
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    async def test_get_courses_large_catalog(
        self,
        async_client: AsyncClient,
        mock_rag_system
    ):
        """Test courses endpoint with large number of courses"""
        # Mock large course catalog
        large_catalog = {
            "total_courses": 100,
            "course_titles": [f"Course {i}" for i in range(100)]
        }
        mock_rag_system.get_course_analytics.return_value = large_catalog

        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 100
        assert len(data["course_titles"]) == 100

    async def test_get_courses_rag_system_error(
        self,
        async_client: AsyncClient,
        mock_rag_system
    ):
        """Test courses endpoint when RAG system raises an error"""
        # Make RAG system raise an exception
        mock_rag_system.get_course_analytics.side_effect = Exception(
            "Vector store connection failed"
        )

        response = await async_client.get("/api/courses")

        # Should return 500 Internal Server Error
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "Vector store connection failed" in response.json()["detail"]

    async def test_get_courses_no_query_params(self, async_client: AsyncClient):
        """Test that courses endpoint doesn't accept query parameters"""
        # Endpoint should work the same with or without params
        response = await async_client.get("/api/courses?filter=test")

        assert response.status_code == 200

    async def test_get_courses_multiple_requests(
        self,
        async_client: AsyncClient,
        mock_rag_system
    ):
        """Test multiple sequential requests to courses endpoint"""
        # First request
        response1 = await async_client.get("/api/courses")
        assert response1.status_code == 200

        # Second request
        response2 = await async_client.get("/api/courses")
        assert response2.status_code == 200

        # Both should return same data
        assert response1.json() == response2.json()

        # RAG system should be called twice
        assert mock_rag_system.get_course_analytics.call_count == 2

    async def test_get_courses_special_characters_in_titles(
        self,
        async_client: AsyncClient,
        mock_rag_system
    ):
        """Test courses endpoint with special characters in course titles"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": [
                "C++ Programming",
                "HTML & CSS: Web Design",
                "Python 3.11+ Features"
            ]
        }

        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 3
        assert "C++ Programming" in data["course_titles"]
        assert "HTML & CSS: Web Design" in data["course_titles"]

    async def test_get_courses_unicode_titles(
        self,
        async_client: AsyncClient,
        mock_rag_system
    ):
        """Test courses endpoint with unicode characters in titles"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": [
                "Python 编程",
                "JavaScript للمبتدئين"
            ]
        }

        response = await async_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 2
        assert "Python 编程" in data["course_titles"]
        assert "JavaScript للمبتدئين" in data["course_titles"]

    async def test_get_courses_method_not_allowed(self, async_client: AsyncClient):
        """Test that POST/PUT/DELETE methods are not allowed"""
        # POST should not be allowed
        response = await async_client.post("/api/courses")
        assert response.status_code == 405

        # PUT should not be allowed
        response = await async_client.put("/api/courses")
        assert response.status_code == 405

        # DELETE should not be allowed
        response = await async_client.delete("/api/courses")
        assert response.status_code == 405

    async def test_get_courses_consistent_ordering(
        self,
        async_client: AsyncClient,
        mock_rag_system
    ):
        """Test that course titles maintain consistent ordering"""
        # Make multiple requests
        responses = []
        for _ in range(3):
            response = await async_client.get("/api/courses")
            responses.append(response.json()["course_titles"])

        # All responses should have same ordering
        assert responses[0] == responses[1] == responses[2]
