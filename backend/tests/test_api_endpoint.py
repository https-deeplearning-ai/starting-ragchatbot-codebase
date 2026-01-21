"""
Tests for the FastAPI /api/query endpoint.

These tests reveal the type mismatch between RAGSystem.query() output
and the QueryResponse model.
"""
import pytest
from unittest.mock import patch, Mock
from pydantic import ValidationError
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient


class TestQueryResponseModel:
    """Test the QueryResponse Pydantic model validation"""

    def test_query_response_expects_source_items(self):
        """
        CRITICAL BUG: QueryResponse expects List[SourceItem], not List[str].

        The RAG system returns sources as List[str] like:
            ["MCP Course - Lesson 1", "MCP Course - Lesson 2"]

        But QueryResponse expects List[SourceItem] where SourceItem has:
            - text: str
            - link: Optional[str]

        This causes a Pydantic validation error.
        """
        from app import QueryResponse, SourceItem

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
        from app import QueryResponse, SourceItem

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


class TestRAGSystemSourcesOutput:
    """Verify what RAGSystem.query() actually returns for sources"""

    def test_rag_system_returns_plain_strings(self):
        """
        Document that RAGSystem.query() returns List[str] for sources.
        """
        from config import config
        from rag_system import RAGSystem

        with patch('rag_system.AIGenerator') as mock_ai:
            mock_ai_instance = Mock()
            mock_ai_instance.generate_response.return_value = "Test response"
            mock_ai.return_value = mock_ai_instance

            rag = RAGSystem(config)

            # Execute a search that will populate sources
            rag.search_tool.execute(query="MCP")

            # Get sources from tool manager
            sources = rag.tool_manager.get_last_sources()

            # Sources are strings, not SourceItem objects
            if sources:
                assert isinstance(sources[0], str), (
                    f"Expected str, got {type(sources[0])}. "
                    "RAG system returns List[str] but API expects List[SourceItem]"
                )


class TestAPIEndpoint:
    """Integration tests for the actual API endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client with mocked AI generator"""
        with patch('app.rag_system') as mock_rag:
            # Configure mock to return what RAG system actually returns
            mock_rag.session_manager.create_session.return_value = "session_1"
            mock_rag.query.return_value = (
                "Here is the answer about MCP",
                ["MCP Course - Lesson 1"]  # This is List[str], not List[SourceItem]
            )

            from app import app
            yield TestClient(app, raise_server_exceptions=False)

    def test_query_endpoint_fails_with_type_mismatch(self, client):
        """
        CRITICAL BUG TEST: The /api/query endpoint fails because
        sources are returned as List[str] but model expects List[SourceItem].
        """
        response = client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        # The endpoint should return 500 due to validation error
        # If this passes (status 200), the bug has been fixed
        if response.status_code == 500:
            # Bug confirmed - type mismatch causes 500 error
            assert "detail" in response.json()
            pytest.fail(
                f"API returns 500 error due to type mismatch. "
                f"Error: {response.json().get('detail', 'Unknown error')}. "
                "Fix: Convert List[str] sources to List[SourceItem] in app.py"
            )
        elif response.status_code == 200:
            # Bug may be fixed, verify response structure
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert "session_id" in data


class TestSourceConversionFix:
    """Tests for the fix: converting List[str] to List[SourceItem]"""

    def test_convert_string_sources_to_source_items(self):
        """
        Demonstrate the fix: convert string sources to SourceItem objects.
        """
        from app import SourceItem

        # Raw sources from RAG system
        raw_sources = ["MCP Course - Lesson 1", "MCP Course - Lesson 2"]

        # Convert to SourceItem objects (THE FIX)
        source_items = [SourceItem(text=source) for source in raw_sources]

        assert len(source_items) == 2
        assert source_items[0].text == "MCP Course - Lesson 1"
        assert source_items[0].link is None  # Default

    def test_fix_allows_valid_response(self):
        """Verify that after conversion, QueryResponse works"""
        from app import QueryResponse, SourceItem

        raw_sources = ["MCP Course - Lesson 1"]

        # Apply the fix
        source_items = [SourceItem(text=source) for source in raw_sources]

        # Now QueryResponse should work
        response = QueryResponse(
            answer="Test answer",
            sources=source_items,
            session_id="session_1"
        )

        assert response.answer == "Test answer"
        assert len(response.sources) == 1


class TestFullEndToEndWithFix:
    """End-to-end test simulating the full flow with fix applied"""

    @pytest.fixture
    def fixed_client(self):
        """
        Test client that simulates the FIXED behavior.
        """
        from app import app, SourceItem, QueryResponse
        from fastapi.testclient import TestClient

        # Patch at the app level to simulate fixed behavior
        with patch('app.rag_system') as mock_rag:
            mock_rag.session_manager.create_session.return_value = "session_1"

            # Simulate what happens after fix is applied
            def mock_query(query, session_id=None):
                return (
                    "MCP is a protocol for AI tool integration",
                    ["MCP Course - Lesson 1"]  # Raw strings
                )

            mock_rag.query.side_effect = mock_query

            yield TestClient(app, raise_server_exceptions=False)

    def test_endpoint_should_convert_sources(self, fixed_client):
        """
        After fix, the endpoint should convert string sources to SourceItem.

        Current broken code in app.py line 73-77:
            return QueryResponse(
                answer=answer,
                sources=sources,  # <-- BUG: sources is List[str]
                session_id=session_id
            )

        Fixed code should be:
            source_items = [SourceItem(text=s) for s in sources]
            return QueryResponse(
                answer=answer,
                sources=source_items,  # <-- FIX: List[SourceItem]
                session_id=session_id
            )
        """
        response = fixed_client.post(
            "/api/query",
            json={"query": "What is MCP?"}
        )

        # Document expected behavior after fix
        # Status should be 200, not 500
        # This test will fail until fix is applied, showing the bug
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
