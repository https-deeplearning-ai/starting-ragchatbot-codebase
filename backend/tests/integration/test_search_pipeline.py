"""Integration tests for the search pipeline: ToolManager -> CourseSearchTool -> VectorStore"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import VectorStore, SearchResults


class TestSearchPipelineIntegration:
    """Integration tests for the complete search pipeline"""

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_full_search_pipeline_with_results(self, mock_transformer, mock_chromadb,
                                                mock_chroma_query_response):
        """Test complete search pipeline returns properly formatted results"""
        # Setup ChromaDB mocks
        mock_collection = MagicMock()
        mock_collection.query.return_value = mock_chroma_query_response

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        # Create real components
        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        search_tool = CourseSearchTool(store)

        manager = ToolManager()
        manager.register_tool(search_tool)

        # Execute search through tool manager (simulating AI tool call)
        result = manager.execute_tool(
            "search_course_content",
            query="computer use"
        )

        # Verify results
        assert result is not None
        assert "Content chunk" in result or "[Test Course" in result

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_search_pipeline_captures_sources(self, mock_transformer, mock_chromadb,
                                               mock_chroma_query_response):
        """Test that search pipeline captures sources for citation"""
        mock_collection = MagicMock()
        mock_collection.query.return_value = mock_chroma_query_response
        mock_collection.get.return_value = {
            'metadatas': [{'course_link': 'https://example.com'}]
        }

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        search_tool = CourseSearchTool(store)

        manager = ToolManager()
        manager.register_tool(search_tool)

        manager.execute_tool("search_course_content", query="test")
        sources = manager.get_last_sources()

        assert len(sources) > 0

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_search_pipeline_empty_results_handling(self, mock_transformer, mock_chromadb,
                                                     mock_empty_chroma_response):
        """Test search pipeline handles empty results gracefully"""
        mock_collection = MagicMock()
        mock_collection.query.return_value = mock_empty_chroma_response

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        search_tool = CourseSearchTool(store)

        manager = ToolManager()
        manager.register_tool(search_tool)

        result = manager.execute_tool(
            "search_course_content",
            query="nonexistent topic that won't match anything"
        )

        assert "No relevant content found" in result

        # Sources should be empty
        sources = manager.get_last_sources()
        assert len(sources) == 0


class TestCourseNameResolution:
    """Test course name resolution in search pipeline"""

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_course_name_resolution_success(self, mock_transformer, mock_chromadb,
                                             mock_chroma_query_response,
                                             mock_course_catalog_response):
        """Test search with course name that gets resolved"""
        mock_catalog_collection = MagicMock()
        mock_catalog_collection.query.return_value = mock_course_catalog_response

        mock_content_collection = MagicMock()
        mock_content_collection.query.return_value = mock_chroma_query_response

        mock_client = MagicMock()
        # Return different collections based on call order
        mock_client.get_or_create_collection.side_effect = [
            mock_catalog_collection,
            mock_content_collection
        ]
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        search_tool = CourseSearchTool(store)

        manager = ToolManager()
        manager.register_tool(search_tool)

        # Search with partial course name
        result = manager.execute_tool(
            "search_course_content",
            query="agents",
            course_name="Computer Use"  # Partial name
        )

        # Should not return error
        assert "No course found" not in result

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_course_name_resolution_failure(self, mock_transformer, mock_chromadb,
                                             mock_empty_chroma_response):
        """Test search with course name that doesn't resolve"""
        mock_catalog_collection = MagicMock()
        mock_catalog_collection.query.return_value = mock_empty_chroma_response

        mock_content_collection = MagicMock()

        mock_client = MagicMock()
        mock_client.get_or_create_collection.side_effect = [
            mock_catalog_collection,
            mock_content_collection
        ]
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        search_tool = CourseSearchTool(store)

        manager = ToolManager()
        manager.register_tool(search_tool)

        result = manager.execute_tool(
            "search_course_content",
            query="anything",
            course_name="NonExistent Course Name"
        )

        assert "No course found" in result


class TestDiagnosticScenarios:
    """Tests specifically designed to diagnose 'not detail content' issues"""

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_diagnose_empty_database(self, mock_transformer, mock_chromadb):
        """Diagnose: ChromaDB is empty (no documents ingested)"""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]],
            'ids': [[]]
        }
        mock_collection.count.return_value = 0

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        results = store.search("any query")

        assert results.is_empty(), "Empty database should return empty results"

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_diagnose_search_returns_content(self, mock_transformer, mock_chromadb,
                                              mock_chroma_query_response):
        """Diagnose: Verify search actually returns document content"""
        mock_collection = MagicMock()
        mock_collection.query.return_value = mock_chroma_query_response

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        results = store.search("test query")

        assert not results.is_empty(), "Search should return results"
        assert len(results.documents) > 0, "Should have documents"
        assert all(doc for doc in results.documents), "Documents should not be empty strings"

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_diagnose_tool_formats_results_correctly(self, mock_transformer, mock_chromadb,
                                                      mock_chroma_query_response):
        """Diagnose: Verify CourseSearchTool formats results with content"""
        mock_collection = MagicMock()
        mock_collection.query.return_value = mock_chroma_query_response
        mock_collection.get.return_value = {
            'metadatas': [{'course_link': 'https://example.com'}]
        }

        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        tool = CourseSearchTool(store)

        result = tool.execute(query="test")

        # Result should contain actual content, not error messages
        assert "No relevant content found" not in result
        assert "Content chunk" in result  # From mock_chroma_query_response

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_diagnose_lesson_filter_too_restrictive(self, mock_transformer, mock_chromadb,
                                                     mock_course_catalog_response):
        """Diagnose: Lesson filter may be too restrictive"""
        mock_catalog = MagicMock()
        mock_catalog.query.return_value = mock_course_catalog_response

        mock_content = MagicMock()
        # Content search with lesson filter returns nothing
        mock_content.query.return_value = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }

        mock_client = MagicMock()
        mock_client.get_or_create_collection.side_effect = [mock_catalog, mock_content]
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2", max_results=5)
        results = store.search("query", lesson_number=999)

        assert results.is_empty(), "Non-existent lesson should return empty"


class TestVectorStoreFilterBuilding:
    """Test VectorStore filter building logic"""

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_build_filter_course_only(self, mock_transformer, mock_chromadb):
        """Test building filter with only course title"""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2")
        filter_dict = store._build_filter("Test Course", None)

        assert filter_dict == {"course_title": "Test Course"}

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_build_filter_lesson_only(self, mock_transformer, mock_chromadb):
        """Test building filter with only lesson number"""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2")
        filter_dict = store._build_filter(None, 3)

        assert filter_dict == {"lesson_number": 3}

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_build_filter_both(self, mock_transformer, mock_chromadb):
        """Test building filter with both course and lesson"""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2")
        filter_dict = store._build_filter("Test Course", 2)

        assert filter_dict == {
            "$and": [
                {"course_title": "Test Course"},
                {"lesson_number": 2}
            ]
        }

    @patch('vector_store.chromadb')
    @patch('vector_store.SentenceTransformer')
    def test_build_filter_none(self, mock_transformer, mock_chromadb):
        """Test building filter with no parameters"""
        mock_client = MagicMock()
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore("./test_db", "all-MiniLM-L6-v2")
        filter_dict = store._build_filter(None, None)

        assert filter_dict is None


class TestSearchResultsDataclass:
    """Test SearchResults dataclass functionality"""

    def test_from_chroma_with_valid_data(self, mock_chroma_query_response):
        """Test creating SearchResults from valid ChromaDB response"""
        results = SearchResults.from_chroma(mock_chroma_query_response)

        assert len(results.documents) == 3
        assert len(results.metadata) == 3
        assert len(results.distances) == 3
        assert results.error is None
        assert not results.is_empty()

    def test_from_chroma_with_empty_data(self, mock_empty_chroma_response):
        """Test creating SearchResults from empty ChromaDB response"""
        results = SearchResults.from_chroma(mock_empty_chroma_response)

        assert len(results.documents) == 0
        assert results.is_empty()

    def test_empty_results_with_error(self):
        """Test creating empty results with error message"""
        results = SearchResults.empty("Course not found")

        assert results.is_empty()
        assert results.error == "Course not found"

    def test_is_empty_true_when_no_documents(self):
        """Test is_empty returns True when no documents"""
        results = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        assert results.is_empty()

    def test_is_empty_false_with_documents(self, valid_search_results):
        """Test is_empty returns False when documents exist"""
        assert not valid_search_results.is_empty()
