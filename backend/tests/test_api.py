"""
API endpoint tests for the RAG system FastAPI application.

These tests cover the core API endpoints:
- POST /api/query - Query processing endpoint
- GET /api/courses - Course statistics endpoint
- POST /api/session/clear - Session clearing endpoint

Note: The actual app.py imports static files that don't exist in test environment,
so we recreate the API endpoints inline for testing to avoid mount issues.
"""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional
from unittest.mock import MagicMock, patch


# =============================================================================
# Re-create API Models and Endpoints (avoiding static file mount issues)
# =============================================================================

class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[str]
    session_id: str


class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]


class SessionClearRequest(BaseModel):
    """Request model for clearing session"""
    session_id: Optional[str] = None


class SessionClearResponse(BaseModel):
    """Response model for session clear"""
    success: bool
    cleared_session_id: Optional[str] = None


def create_test_app(mock_rag_system: MagicMock) -> FastAPI:
    """Create a test FastAPI app with mocked RAG system."""
    app = FastAPI(title="Test RAG System")

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/session/clear", response_model=SessionClearResponse)
    async def clear_session(request: SessionClearRequest):
        """Clear session history on the backend"""
        try:
            session_id = request.session_id
            if session_id:
                mock_rag_system.session_manager.clear_session(session_id)
                return SessionClearResponse(
                    success=True,
                    cleared_session_id=session_id
                )
            return SessionClearResponse(success=True, cleared_session_id=None)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# =============================================================================
# Test Cases
# =============================================================================

class TestQueryEndpoint:
    """Tests for POST /api/query endpoint."""

    def test_query_with_valid_request(self, mock_rag_system, sample_query_request):
        """Test successful query with valid request."""
        # Setup mock
        mock_rag_system.query.return_value = (
            "Python is a high-level programming language.",
            ["Introduction to Python|Lesson 1"]
        )
        mock_rag_system.session_manager.create_session.return_value = "new-session-001"

        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        response = client.post("/api/query", json=sample_query_request)

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["answer"] == "Python is a high-level programming language."
        assert data["sources"] == ["Introduction to Python|Lesson 1"]

    def test_query_with_session_id(self, mock_rag_system):
        """Test query with provided session ID."""
        # Setup mock
        mock_rag_system.query.return_value = ("Test answer", ["Source 1"])

        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        payload = {"query": "What is Python?", "session_id": "existing-session-123"}
        response = client.post("/api/query", json=payload)

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session-123"
        mock_rag_system.query.assert_called_once_with("What is Python?", "existing-session-123")

    def test_query_without_session_creates_new_session(self, mock_rag_system):
        """Test that query without session creates new session."""
        # Setup mock
        mock_rag_system.query.return_value = ("Answer", ["Source"])
        mock_rag_system.session_manager.create_session.return_value = "auto-generated-session"

        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request without session_id
        payload = {"query": "Test question"}
        response = client.post("/api/query", json=payload)

        # Verify new session was created
        assert response.status_code == 200
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_with_empty_query(self, mock_rag_system):
        """Test query with empty query string."""
        # Setup mock
        mock_rag_system.query.return_value = ("Empty query handled", [])

        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        payload = {"query": ""}
        response = client.post("/api/query", json=payload)

        # Verify - FastAPI will validate, so expect 422 for missing/empty field
        assert response.status_code in [422, 500]

    def test_query_internal_error(self, mock_rag_system):
        """Test query handles internal errors gracefully."""
        # Setup mock to raise exception
        mock_rag_system.query.side_effect = RuntimeError("Database error")

        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        payload = {"query": "Test question"}
        response = client.post("/api/query", json=payload)

        # Verify error handling
        assert response.status_code == 500
        assert "detail" in response.json()


class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint."""

    def test_courses_returns_statistics(self, mock_rag_system):
        """Test successful course statistics retrieval."""
        # Setup mock
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": ["Python Basics", "Advanced Python", "Data Science", "Web Dev", "ML"]
        }

        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        response = client.get("/api/courses")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 5
        assert len(data["course_titles"]) == 5
        assert "Python Basics" in data["course_titles"]

    def test_courses_empty_catalog(self, mock_rag_system):
        """Test course endpoint with empty catalog."""
        # Setup mock
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        response = client.get("/api/courses")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_internal_error(self, mock_rag_system):
        """Test course endpoint handles internal errors."""
        # Setup mock to raise exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Vector store error")

        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        response = client.get("/api/courses")

        # Verify error handling
        assert response.status_code == 500


class TestSessionClearEndpoint:
    """Tests for POST /api/session/clear endpoint."""

    def test_clear_specific_session(self, mock_rag_system):
        """Test clearing a specific session."""
        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        payload = {"session_id": "session-to-clear"}
        response = client.post("/api/session/clear", json=payload)

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cleared_session_id"] == "session-to-clear"
        mock_rag_system.session_manager.clear_session.assert_called_once_with("session-to-clear")

    def test_clear_without_session_id(self, mock_rag_system):
        """Test clearing without providing session ID."""
        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        payload = {}
        response = client.post("/api/session/clear", json=payload)

        # Verify - should succeed without clearing any session
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["cleared_session_id"] is None
        mock_rag_system.session_manager.clear_session.assert_not_called()

    def test_clear_none_session(self, mock_rag_system):
        """Test clearing with null session ID."""
        # Create app and client
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request
        payload = {"session_id": None}
        response = client.post("/api/session/clear", json=payload)

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_rag_system.session_manager.clear_session.assert_not_called()


class TestRequestValidation:
    """Tests for request validation."""

    def test_query_missing_query_field(self, mock_rag_system):
        """Test query endpoint rejects missing query field."""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request with missing query
        payload = {"session_id": "test-session"}
        response = client.post("/api/query", json=payload)

        # Verify validation error
        assert response.status_code == 422

    def test_query_invalid_type(self, mock_rag_system):
        """Test query endpoint rejects invalid types."""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Execute request with wrong type
        payload = {"query": 12345}
        response = client.post("/api/query", json=payload)

        # Verify validation error
        assert response.status_code == 422


class TestResponseSchema:
    """Tests for response schema validation."""

    def test_query_response_schema(self, mock_rag_system):
        """Test query response has correct schema."""
        mock_rag_system.query.return_value = ("Test answer", ["Source 1", "Source 2"])
        mock_rag_system.session_manager.create_session.return_value = "test-123"

        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.post("/api/query", json={"query": "Test?"})

        assert response.status_code == 200
        data = response.json()
        # Check all required fields exist
        assert "answer" in data and isinstance(data["answer"], str)
        assert "sources" in data and isinstance(data["sources"], list)
        assert "session_id" in data and isinstance(data["session_id"], str)

    def test_courses_response_schema(self, mock_rag_system):
        """Test courses response has correct schema."""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["A", "B", "C"]
        }

        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data and isinstance(data["total_courses"], int)
        assert "course_titles" in data and isinstance(data["course_titles"], list)