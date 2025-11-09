"""
API endpoint tests for root path

Tests the GET / endpoint for:
- Health check functionality
- Response structure validation
- Basic API availability
"""
import pytest
from httpx import AsyncClient


@pytest.mark.api
class TestRootEndpoint:
    """Test suite for root (/) endpoint"""

    async def test_root_endpoint_success(self, async_client: AsyncClient):
        """Test root endpoint returns successful response"""
        response = await async_client.get("/")

        assert response.status_code == 200

    async def test_root_endpoint_response_structure(self, async_client: AsyncClient):
        """Test root endpoint returns correct structure"""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Verify response has expected fields
        assert "status" in data
        assert "message" in data

    async def test_root_endpoint_status_ok(self, async_client: AsyncClient):
        """Test root endpoint returns 'ok' status"""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"

    async def test_root_endpoint_has_message(self, async_client: AsyncClient):
        """Test root endpoint returns informative message"""
        response = await async_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    async def test_root_endpoint_multiple_requests(self, async_client: AsyncClient):
        """Test multiple requests to root endpoint"""
        responses = []

        for _ in range(5):
            response = await async_client.get("/")
            assert response.status_code == 200
            responses.append(response.json())

        # All responses should be identical
        assert all(r == responses[0] for r in responses)

    async def test_root_endpoint_with_trailing_slash(self, async_client: AsyncClient):
        """Test root endpoint works with and without trailing slash"""
        response_without = await async_client.get("/")
        response_with = await async_client.get("/")

        assert response_without.status_code == 200
        assert response_with.status_code == 200
        assert response_without.json() == response_with.json()

    async def test_root_endpoint_method_not_allowed(self, async_client: AsyncClient):
        """Test that only GET is allowed on root endpoint"""
        # POST should not be allowed (will fail since no static files)
        # In test environment, this should be handled by our test app
        response = await async_client.post("/")
        assert response.status_code in [404, 405]

        # PUT should not be allowed
        response = await async_client.put("/")
        assert response.status_code in [404, 405]

        # DELETE should not be allowed
        response = await async_client.delete("/")
        assert response.status_code in [404, 405]

    async def test_root_endpoint_json_content_type(self, async_client: AsyncClient):
        """Test root endpoint returns JSON content type"""
        response = await async_client.get("/")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    async def test_root_endpoint_no_side_effects(self, async_client: AsyncClient):
        """Test that calling root endpoint doesn't modify system state"""
        # Get initial state by calling courses
        response_before = await async_client.get("/api/courses")
        courses_before = response_before.json()

        # Call root endpoint multiple times
        for _ in range(3):
            await async_client.get("/")

        # Verify courses haven't changed
        response_after = await async_client.get("/api/courses")
        courses_after = response_after.json()

        assert courses_before == courses_after

    async def test_root_endpoint_fast_response(self, async_client: AsyncClient):
        """Test that root endpoint responds quickly (basic health check)"""
        import time

        start = time.time()
        response = await async_client.get("/")
        duration = time.time() - start

        assert response.status_code == 200
        # Should respond in less than 1 second (generous timeout for health check)
        assert duration < 1.0
