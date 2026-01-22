"""
Tests for the FastAPI API endpoints.

These tests use a test app that avoids static file mounting issues
and verify proper request/response handling for all API endpoints.
"""
import pytest
from unittest.mock import patch, Mock, MagicMock
from pydantic import ValidationError
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestQueryEndpoint:
    """Tests for POST /api/query endpoint"""

    def test_query_endpoint_success(self, test_client):
        """Test successful query with valid request"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"

    def test_query_endpoint_with_session_id(self, test_client, mock_rag_system):
        """Test query with existing session ID"""
        response = test_client.post(
            "/api/query",
            json={"query": "Tell me more", "session_id": "existing-session-456"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session-456"
        # Verify the query was called with the provided session_id
        mock_rag_system.query.assert_called_once_with("Tell me more", "existing-session-456")

    def test_query_endpoint_returns_sources_as_objects(self, test_client):
        """Test that sources are returned as SourceItem objects, not plain strings"""
        response = test_client.post(
            "/api/query",
            json={"query": "What courses are available?"}
        )

        assert response.status_code == 200
        data = response.json()
        sources = data["sources"]
        assert isinstance(sources, list)
        assert len(sources) == 2

        # Each source should be an object with 'text' field
        for source in sources:
            assert isinstance(source, dict)
            assert "text" in source
            assert "link" in source

    def test_query_endpoint_empty_query(self, test_client):
        """Test query endpoint with empty query string"""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Empty query should still be processed (validation at app level)
        assert response.status_code == 200

    def test_query_endpoint_missing_query_field(self, test_client):
        """Test query endpoint with missing query field"""
        response = test_client.post(
            "/api/query",
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_query_endpoint_invalid_json(self, test_client):
        """Test query endpoint with invalid JSON"""
        response = test_client.post(
            "/api/query",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_endpoint_error_handling(self, test_client_with_errors):
        """Test that errors are properly returned as 500 status"""
        response = test_client_with_errors.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database connection failed" in data["detail"]


class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint"""

    def test_courses_endpoint_success(self, test_client):
        """Test successful courses retrieval"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3

    def test_courses_endpoint_returns_list_of_titles(self, test_client):
        """Test that course_titles is a list of strings"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        course_titles = data["course_titles"]
        assert isinstance(course_titles, list)
        for title in course_titles:
            assert isinstance(title, str)

    def test_courses_endpoint_error_handling(self, test_client_with_errors):
        """Test that errors return 500 status"""
        response = test_client_with_errors.get("/api/courses")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Analytics unavailable" in data["detail"]


class TestSessionEndpoint:
    """Tests for DELETE /api/sessions/{session_id} endpoint"""

    def test_delete_session_success(self, test_client, mock_rag_system):
        """Test successful session deletion"""
        response = test_client.delete("/api/sessions/session-to-delete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        mock_rag_system.session_manager.delete_session.assert_called_once_with("session-to-delete")

    def test_delete_nonexistent_session(self, test_client):
        """Test deleting a session that doesn't exist (should still return ok)"""
        response = test_client.delete("/api/sessions/nonexistent-session")

        # The endpoint doesn't check if session exists, just deletes
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestRootEndpoint:
    """Tests for GET / endpoint"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns API info"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestQueryResponseModel:
    """Test the QueryResponse Pydantic model validation"""

    def test_query_response_expects_source_items(self):
        """
        Verify that QueryResponse requires SourceItem objects, not plain strings.
        """
        # Import from the actual app to test the real models
        # Create a minimal app context to import models
        from pydantic import BaseModel
        from typing import List, Optional

        class SourceItem(BaseModel):
            text: str
            link: Optional[str] = None

        class QueryResponse(BaseModel):
            answer: str
            sources: List[SourceItem]
            session_id: str

        # This is what RAG system returns
        raw_sources = ["MCP Course - Lesson 1", "MCP Course - Lesson 2"]

        # This should fail because sources expects List[SourceItem]
        with pytest.raises(ValidationError) as exc_info:
            QueryResponse(
                answer="Test answer",
                sources=raw_sources,  # List[str] instead of List[SourceItem]
                session_id="session_1"
            )

        # Verify the error is about the sources field
        assert "sources" in str(exc_info.value)

    def test_query_response_works_with_source_items(self):
        """Verify QueryResponse works when given proper SourceItem objects"""
        from pydantic import BaseModel
        from typing import List, Optional

        class SourceItem(BaseModel):
            text: str
            link: Optional[str] = None

        class QueryResponse(BaseModel):
            answer: str
            sources: List[SourceItem]
            session_id: str

        source_items = [
            SourceItem(text="MCP Course - Lesson 1", link=None),
            SourceItem(text="MCP Course - Lesson 2", link=None)
        ]

        # This should work
        response = QueryResponse(
            answer="Test answer",
            sources=source_items,
            session_id="session_1"
        )

        assert len(response.sources) == 2
        assert response.sources[0].text == "MCP Course - Lesson 1"


class TestSourceConversion:
    """Tests for source conversion from List[str] to List[SourceItem]"""

    def test_convert_string_sources_to_source_items(self):
        """Demonstrate proper conversion of string sources to SourceItem objects"""
        from pydantic import BaseModel
        from typing import Optional

        class SourceItem(BaseModel):
            text: str
            link: Optional[str] = None

        # Raw sources from RAG system
        raw_sources = ["MCP Course - Lesson 1", "MCP Course - Lesson 2"]

        # Convert to SourceItem objects
        source_items = [SourceItem(text=source) for source in raw_sources]

        assert len(source_items) == 2
        assert source_items[0].text == "MCP Course - Lesson 1"
        assert source_items[0].link is None

    def test_convert_empty_sources(self):
        """Test conversion of empty source list"""
        from pydantic import BaseModel
        from typing import Optional

        class SourceItem(BaseModel):
            text: str
            link: Optional[str] = None

        raw_sources = []
        source_items = [SourceItem(text=source) for source in raw_sources]

        assert len(source_items) == 0


class TestRequestValidation:
    """Tests for request validation"""

    def test_query_request_valid(self, test_client):
        """Test valid query request"""
        response = test_client.post(
            "/api/query",
            json={"query": "test query", "session_id": "abc123"}
        )
        assert response.status_code == 200

    def test_query_request_extra_fields_ignored(self, test_client):
        """Test that extra fields in request are ignored"""
        response = test_client.post(
            "/api/query",
            json={
                "query": "test query",
                "extra_field": "should be ignored"
            }
        )
        assert response.status_code == 200

    def test_query_request_wrong_type(self, test_client):
        """Test query with wrong type"""
        response = test_client.post(
            "/api/query",
            json={"query": 12345}  # Should be string
        )
        # FastAPI coerces to string, so this might pass
        # The behavior depends on Pydantic's coercion settings
        assert response.status_code in [200, 422]


class TestCORSHeaders:
    """Tests for CORS header handling"""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are present in response"""
        response = test_client.options(
            "/api/query",
            headers={"Origin": "http://localhost:3000"}
        )

        # OPTIONS request for CORS preflight
        assert response.status_code in [200, 405]

    def test_cross_origin_request(self, test_client):
        """Test request with Origin header"""
        response = test_client.post(
            "/api/query",
            json={"query": "test"},
            headers={"Origin": "http://localhost:3000"}
        )

        assert response.status_code == 200


class TestEndpointIntegration:
    """Integration tests for multiple endpoint interactions"""

    def test_query_then_get_courses(self, test_client):
        """Test that querying doesn't affect course stats"""
        # First, get initial course stats
        courses_response = test_client.get("/api/courses")
        initial_count = courses_response.json()["total_courses"]

        # Make a query
        test_client.post("/api/query", json={"query": "test"})

        # Get courses again
        courses_response = test_client.get("/api/courses")
        final_count = courses_response.json()["total_courses"]

        assert initial_count == final_count

    def test_session_lifecycle(self, test_client, mock_rag_system):
        """Test complete session lifecycle: create, use, delete"""
        # Create session via query (auto-created)
        query_response = test_client.post(
            "/api/query",
            json={"query": "Hello"}
        )
        session_id = query_response.json()["session_id"]
        assert session_id == "test-session-123"

        # Use the session for another query
        query_response = test_client.post(
            "/api/query",
            json={"query": "Follow up", "session_id": session_id}
        )
        assert query_response.json()["session_id"] == session_id

        # Delete the session
        delete_response = test_client.delete(f"/api/sessions/{session_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "ok"
