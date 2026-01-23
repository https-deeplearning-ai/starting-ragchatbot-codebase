"""Tests for FastAPI endpoints

This module defines a test app inline to avoid import issues with the main app,
which mounts static files that don't exist in the test environment.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================================
# Test App Definition (mirrors app.py endpoints without static file mounts)
# ============================================================================

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


def create_test_app(mock_rag_system):
    """Create a test FastAPI app with injected mock RAGSystem"""
    app = FastAPI(title="Test Course Materials RAG System")

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            # Convert source dicts to strings if needed
            source_strings = []
            for s in sources:
                if isinstance(s, dict):
                    source_strings.append(f"{s.get('text', '')} - {s.get('link', '')}")
                else:
                    source_strings.append(str(s))

            return QueryResponse(
                answer=answer,
                sources=source_strings,
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

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        """Clear a conversation session"""
        try:
            mock_rag_system.session_manager.clear_session(session_id)
            return {"status": "success"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app


# ============================================================================
# Query Endpoint Tests
# ============================================================================

class TestQueryEndpoint:
    """Tests for POST /api/query endpoint"""

    def test_query_success(self, mock_rag_system):
        """Test successful query returns answer and sources"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.post(
            "/api/query",
            json={"query": "What is machine learning?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["answer"] == "This is a test answer about the course material."

    def test_query_creates_session_when_not_provided(self, mock_rag_system):
        """Test that a new session is created when session_id is not provided"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.post(
            "/api/query",
            json={"query": "Test question"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_query_uses_existing_session(self, mock_rag_system):
        """Test that existing session_id is used when provided"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.post(
            "/api/query",
            json={"query": "Follow up question", "session_id": "existing-session"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing-session"
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_query_calls_rag_system(self, mock_rag_system):
        """Test that query endpoint calls RAGSystem.query with correct args"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        client.post(
            "/api/query",
            json={"query": "What is Python?", "session_id": "my-session"}
        )

        mock_rag_system.query.assert_called_once_with("What is Python?", "my-session")

    def test_query_returns_sources(self, mock_rag_system):
        """Test that sources are returned in the response"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.post(
            "/api/query",
            json={"query": "Tell me about lessons"}
        )

        data = response.json()
        assert len(data["sources"]) == 1
        assert "ML Fundamentals" in data["sources"][0]

    def test_query_empty_query_validation(self, mock_rag_system):
        """Test that empty query returns validation error"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.post(
            "/api/query",
            json={}
        )

        assert response.status_code == 422  # Validation error

    def test_query_error_returns_500(self, mock_rag_system_error):
        """Test that RAGSystem errors return 500 status"""
        app = create_test_app(mock_rag_system_error)
        client = TestClient(app)

        response = client.post(
            "/api/query",
            json={"query": "This will fail"}
        )

        assert response.status_code == 500
        assert "Database connection failed" in response.json()["detail"]

    def test_query_with_empty_sources(self, mock_rag_system_empty):
        """Test query when no sources are found"""
        app = create_test_app(mock_rag_system_empty)
        client = TestClient(app)

        response = client.post(
            "/api/query",
            json={"query": "Unknown topic"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["sources"] == []


# ============================================================================
# Courses Endpoint Tests
# ============================================================================

class TestCoursesEndpoint:
    """Tests for GET /api/courses endpoint"""

    def test_get_courses_success(self, mock_rag_system):
        """Test successful retrieval of course statistics"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3
        assert "ML Fundamentals" in data["course_titles"]

    def test_get_courses_empty(self, mock_rag_system_empty):
        """Test courses endpoint when no courses exist"""
        app = create_test_app(mock_rag_system_empty)
        client = TestClient(app)

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_get_courses_error(self, mock_rag_system_error):
        """Test courses endpoint when error occurs"""
        app = create_test_app(mock_rag_system_error)
        client = TestClient(app)

        response = client.get("/api/courses")

        assert response.status_code == 500
        assert "Analytics unavailable" in response.json()["detail"]


# ============================================================================
# Session Endpoint Tests
# ============================================================================

class TestSessionEndpoint:
    """Tests for DELETE /api/session/{session_id} endpoint"""

    def test_clear_session_success(self, mock_rag_system):
        """Test successful session clearing"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        response = client.delete("/api/session/test-session-123")

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "test-session-123"
        )

    def test_clear_session_not_found(self, mock_rag_system_error):
        """Test clearing non-existent session returns error"""
        app = create_test_app(mock_rag_system_error)
        client = TestClient(app)

        response = client.delete("/api/session/nonexistent")

        assert response.status_code == 500
        assert "Session not found" in response.json()["detail"]


# ============================================================================
# Request/Response Model Tests
# ============================================================================

class TestRequestModels:
    """Tests for Pydantic request/response models"""

    def test_query_request_with_all_fields(self):
        """Test QueryRequest with all fields"""
        request = QueryRequest(query="test", session_id="abc123")
        assert request.query == "test"
        assert request.session_id == "abc123"

    def test_query_request_with_optional_session(self):
        """Test QueryRequest with optional session_id"""
        request = QueryRequest(query="test")
        assert request.query == "test"
        assert request.session_id is None

    def test_query_response_model(self):
        """Test QueryResponse model"""
        response = QueryResponse(
            answer="Test answer",
            sources=["Source 1", "Source 2"],
            session_id="session-123"
        )
        assert response.answer == "Test answer"
        assert len(response.sources) == 2
        assert response.session_id == "session-123"

    def test_course_stats_model(self):
        """Test CourseStats model"""
        stats = CourseStats(
            total_courses=5,
            course_titles=["Course A", "Course B"]
        )
        assert stats.total_courses == 5
        assert len(stats.course_titles) == 2


# ============================================================================
# Integration-style Tests (with more realistic mock behavior)
# ============================================================================

class TestAPIIntegration:
    """Integration-style tests for API workflows"""

    def test_query_then_clear_session_workflow(self, mock_rag_system):
        """Test typical user workflow: query then clear session"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Make initial query
        query_response = client.post(
            "/api/query",
            json={"query": "What is ML?"}
        )
        session_id = query_response.json()["session_id"]

        # Clear the session
        clear_response = client.delete(f"/api/session/{session_id}")

        assert query_response.status_code == 200
        assert clear_response.status_code == 200

    def test_multiple_queries_same_session(self, mock_rag_system):
        """Test multiple queries with the same session"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # First query
        response1 = client.post(
            "/api/query",
            json={"query": "First question"}
        )
        session_id = response1.json()["session_id"]

        # Second query with same session
        response2 = client.post(
            "/api/query",
            json={"query": "Follow up", "session_id": session_id}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    def test_get_courses_and_query(self, mock_rag_system):
        """Test getting courses then querying"""
        app = create_test_app(mock_rag_system)
        client = TestClient(app)

        # Get available courses
        courses_response = client.get("/api/courses")
        courses = courses_response.json()["course_titles"]

        # Query about first course
        query_response = client.post(
            "/api/query",
            json={"query": f"Tell me about {courses[0]}"}
        )

        assert courses_response.status_code == 200
        assert query_response.status_code == 200
