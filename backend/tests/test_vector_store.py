"""Tests for VectorStore search functionality"""
import pytest
from unittest.mock import patch, Mock
from vector_store import VectorStore, SearchResults


class TestVectorStoreSearch:
    """Test VectorStore.search() with various configurations"""

    def test_search_with_max_results_zero(self, mock_vector_store_with_zero_max_results):
        """
        CRITICAL TEST: This should expose the MAX_RESULTS=0 bug

        When max_results=0, the VectorStore searches with n_results=0,
        which causes ChromaDB to return no results even when content exists.
        """
        store = mock_vector_store_with_zero_max_results

        # Mock the collection to return results (simulating existing content)
        store.course_content.query.return_value = {
            'documents': [["Test content about MCP"]],
            'metadatas': [[{"course_title": "MCP", "lesson_number": 1}]],
            'distances': [[0.15]]
        }

        # Search without explicit limit (uses max_results=0)
        results = store.search(query="What is MCP?")

        # Verify that n_results=0 was passed to ChromaDB
        call_args = store.course_content.query.call_args
        assert call_args[1]['n_results'] == 0, "Bug detected: searching with n_results=0"

        # This test documents the buggy behavior
        # With n_results=0, even though content exists, results will be empty
        assert results.is_empty() or results.error is not None, \
            "With max_results=0, search should fail or return empty results"

    def test_search_with_max_results_positive(self, mock_vector_store):
        """
        Test that search works correctly with positive max_results
        """
        store = mock_vector_store

        # Mock successful search results
        store.course_content.query.return_value = {
            'documents': [["MCP content 1", "MCP content 2", "MCP content 3"]],
            'metadatas': [[
                {"course_title": "MCP", "lesson_number": 1},
                {"course_title": "MCP", "lesson_number": 1},
                {"course_title": "MCP", "lesson_number": 2}
            ]],
            'distances': [[0.1, 0.2, 0.3]]
        }

        # Search without explicit limit (uses max_results=5)
        results = store.search(query="What is MCP?")

        # Verify n_results=5 was used
        call_args = store.course_content.query.call_args
        assert call_args[1]['n_results'] == 5

        # Verify results are returned
        assert not results.is_empty()
        assert len(results.documents) == 3
        assert results.error is None

    def test_search_with_explicit_limit_overrides_max_results(self, mock_vector_store_with_zero_max_results):
        """
        Test that explicit limit parameter overrides max_results

        This shows the workaround: even with max_results=0, passing an explicit
        limit should work correctly.
        """
        store = mock_vector_store_with_zero_max_results

        # Mock search results
        store.course_content.query.return_value = {
            'documents': [["MCP content 1", "MCP content 2"]],
            'metadatas': [[
                {"course_title": "MCP", "lesson_number": 1},
                {"course_title": "MCP", "lesson_number": 1}
            ]],
            'distances': [[0.1, 0.2]]
        }

        # Search WITH explicit limit (should override max_results=0)
        results = store.search(query="What is MCP?", limit=3)

        # Verify explicit limit was used instead of max_results
        call_args = store.course_content.query.call_args
        assert call_args[1]['n_results'] == 3, "Explicit limit should override max_results"

        # Results should be returned successfully
        assert not results.is_empty()
        assert len(results.documents) == 2

    def test_search_with_no_matching_course(self, mock_vector_store):
        """Test search with non-existent course name"""
        store = mock_vector_store

        # Mock course_catalog to return no matching course
        store.course_catalog.query.return_value = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }

        # Search for non-existent course
        results = store.search(query="test", course_name="NonExistentCourse")

        # Should return error
        assert results.error is not None
        assert "No course found matching" in results.error
        assert "NonExistentCourse" in results.error

    def test_search_with_course_name_resolution(self, mock_vector_store, sample_course_metadata):
        """Test that course names are resolved semantically"""
        store = mock_vector_store

        # Mock course_catalog to resolve "MCP" to full title
        store.course_catalog.query.return_value = {
            'documents': [["MCP: Build Rich-Context AI Apps with Anthropic"]],
            'metadatas': [[sample_course_metadata]],
            'distances': [[0.05]]
        }

        # Mock course_content search results
        store.course_content.query.return_value = {
            'documents': [["MCP content"]],
            'metadatas': [[{"course_title": "MCP: Build Rich-Context AI Apps with Anthropic", "lesson_number": 1}]],
            'distances': [[0.1]]
        }

        # Search with partial course name
        results = store.search(query="What is MCP?", course_name="MCP")

        # Verify course_catalog was queried for semantic matching
        assert store.course_catalog.query.called
        catalog_call_args = store.course_catalog.query.call_args
        assert catalog_call_args[1]['query_texts'] == ["MCP"]

        # Verify course_content was searched with resolved title
        content_call_args = store.course_content.query.call_args
        where_filter = content_call_args[1]['where']
        assert where_filter == {"course_title": "MCP: Build Rich-Context AI Apps with Anthropic"}

        # Results should be successful
        assert not results.is_empty()

    def test_search_with_course_and_lesson_filters(self, mock_vector_store, sample_course_metadata):
        """Test search with both course name and lesson number filters"""
        store = mock_vector_store

        # Mock course resolution
        store.course_catalog.query.return_value = {
            'documents': [["MCP"]],
            'metadatas': [[sample_course_metadata]],
            'distances': [[0.05]]
        }

        # Mock search results
        store.course_content.query.return_value = {
            'documents': [["Lesson 2 content"]],
            'metadatas': [[{"course_title": "MCP: Build Rich-Context AI Apps with Anthropic", "lesson_number": 2}]],
            'distances': [[0.1]]
        }

        # Search with both filters
        results = store.search(query="test", course_name="MCP", lesson_number=2)

        # Verify combined filter was used
        content_call_args = store.course_content.query.call_args
        where_filter = content_call_args[1]['where']

        assert "$and" in where_filter
        assert {"course_title": "MCP: Build Rich-Context AI Apps with Anthropic"} in where_filter["$and"]
        assert {"lesson_number": 2} in where_filter["$and"]

    def test_search_handles_chroma_exceptions(self, mock_vector_store):
        """Test that search handles ChromaDB exceptions gracefully"""
        store = mock_vector_store

        # Mock ChromaDB to raise an exception
        store.course_content.query.side_effect = Exception("ChromaDB connection error")

        # Search should handle exception and return error in SearchResults
        results = store.search(query="test")

        # Should return error, not raise exception
        assert results.error is not None
        assert "Search error" in results.error
        assert results.is_empty()


class TestVectorStoreConfiguration:
    """Test VectorStore initialization and configuration"""

    def test_vector_store_initialization_with_valid_max_results(self):
        """Test that VectorStore initializes correctly with valid max_results"""
        with patch('vector_store.chromadb.PersistentClient'):
            store = VectorStore(
                chroma_path="./test",
                embedding_model="all-MiniLM-L6-v2",
                max_results=5
            )

            assert store.max_results == 5

    def test_vector_store_initialization_with_zero_max_results(self):
        """
        Test that VectorStore accepts max_results=0 (current buggy behavior)

        Note: After the fix, this should raise ValueError
        """
        with patch('vector_store.chromadb.PersistentClient'):
            # Currently this doesn't raise an error (the bug)
            store = VectorStore(
                chroma_path="./test",
                embedding_model="all-MiniLM-L6-v2",
                max_results=0
            )

            # This documents the buggy behavior
            assert store.max_results == 0, "Bug: max_results=0 is accepted"

    def test_vector_store_default_max_results(self):
        """Test that VectorStore has correct default max_results"""
        with patch('vector_store.chromadb.PersistentClient'):
            store = VectorStore(
                chroma_path="./test",
                embedding_model="all-MiniLM-L6-v2"
                # No max_results specified
            )

            # Default should be 5 (as defined in the method signature)
            assert store.max_results == 5
