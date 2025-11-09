"""
API endpoint tests for /api/query

Tests the POST /api/query endpoint for:
- Successful query processing with and without session_id
- Response structure validation
- Error handling
- Session management
"""
import pytest
from httpx import AsyncClient


@pytest.mark.api
class TestQueryEndpoint:
    """Test suite for /api/query endpoint"""

    async def test_query_without_session_id(self, async_client: AsyncClient, mock_rag_system):
        """Test query endpoint without providing session_id - should create new session"""
        response = await async_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "source_links" in data
        assert "session_id" in data

        # Verify session was created
        assert data["session_id"] == "test_session_id"
        mock_rag_system.session_manager.create_session.assert_called_once()

        # Verify RAG system was called
        mock_rag_system.query.assert_called_once()

    async def test_query_with_session_id(self, async_client: AsyncClient, mock_rag_system):
        """Test query endpoint with existing session_id"""
        session_id = "existing_session_123"
        response = await async_client.post(
            "/api/query",
            json={
                "query": "Tell me about advanced topics",
                "session_id": session_id
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify session_id is preserved
        assert data["session_id"] == session_id

        # Verify session creation was NOT called since we provided one
        mock_rag_system.session_manager.create_session.assert_not_called()

        # Verify RAG system was called with correct session
        mock_rag_system.query.assert_called_once_with(
            "Tell me about advanced topics",
            session_id
        )

    async def test_query_response_structure(self, async_client: AsyncClient):
        """Test that query response has correct structure and types"""
        response = await async_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify field types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["source_links"], list)
        assert isinstance(data["session_id"], str)

        # Verify content
        assert len(data["answer"]) > 0
        assert len(data["sources"]) > 0
        assert len(data["source_links"]) > 0

    async def test_query_with_empty_query(self, async_client: AsyncClient):
        """Test query endpoint with empty query string"""
        response = await async_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still return 200 but might have different behavior
        assert response.status_code == 200

    async def test_query_missing_query_field(self, async_client: AsyncClient):
        """Test query endpoint with missing query field"""
        response = await async_client.post(
            "/api/query",
            json={"session_id": "test"}
        )

        # Should return 422 Unprocessable Entity due to validation error
        assert response.status_code == 422

    async def test_query_invalid_json(self, async_client: AsyncClient):
        """Test query endpoint with invalid JSON"""
        response = await async_client.post(
            "/api/query",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422

    async def test_query_rag_system_error(self, async_client: AsyncClient, mock_rag_system):
        """Test query endpoint when RAG system raises an error"""
        # Make RAG system raise an exception
        mock_rag_system.query.side_effect = Exception("Database connection failed")

        response = await async_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        # Should return 500 Internal Server Error
        assert response.status_code == 500
        assert "detail" in response.json()
        assert "Database connection failed" in response.json()["detail"]

    async def test_query_sources_match_links(self, async_client: AsyncClient):
        """Test that sources and source_links arrays have matching lengths"""
        response = await async_client.post(
            "/api/query",
            json={"query": "What is Python?"}
        )

        assert response.status_code == 200
        data = response.json()

        # Sources and links should have same length
        assert len(data["sources"]) == len(data["source_links"])

    async def test_query_multiple_requests_same_session(
        self,
        async_client: AsyncClient,
        mock_rag_system
    ):
        """Test multiple queries with the same session_id"""
        session_id = "persistent_session_456"

        # First query
        response1 = await async_client.post(
            "/api/query",
            json={"query": "First question", "session_id": session_id}
        )
        assert response1.status_code == 200
        assert response1.json()["session_id"] == session_id

        # Second query with same session
        response2 = await async_client.post(
            "/api/query",
            json={"query": "Second question", "session_id": session_id}
        )
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

        # Both should use the same session
        assert mock_rag_system.query.call_count == 2

    async def test_query_long_query_string(self, async_client: AsyncClient):
        """Test query endpoint with very long query string"""
        long_query = "What is Python? " * 100  # 1800+ characters

        response = await async_client.post(
            "/api/query",
            json={"query": long_query}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    async def test_query_special_characters(self, async_client: AsyncClient):
        """Test query endpoint with special characters"""
        special_query = "What about C++, C#, and <html> tags?"

        response = await async_client.post(
            "/api/query",
            json={"query": special_query}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data

    async def test_query_unicode_characters(self, async_client: AsyncClient):
        """Test query endpoint with unicode characters"""
        unicode_query = "What is Python? 你好 مرحبا Привет"

        response = await async_client.post(
            "/api/query",
            json={"query": unicode_query}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
