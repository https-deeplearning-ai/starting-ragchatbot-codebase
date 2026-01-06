"""
Tests for VectorStore class - Focus on edge cases and error handling
"""

import json
from unittest.mock import Mock, patch

from vector_store import SearchResults, VectorStore


class TestSearchResults:
    """Test SearchResults.from_chroma() method for IndexError bug"""

    def test_from_chroma_empty_metadatas_bug(self):
        """
        CRITICAL TEST: Tests Bug #3 - IndexError in SearchResults.from_chroma()

        This test will FAIL with current code due to:
        metadata=chroma_results['metadatas'][0] if chroma_results['metadatas'][0] else [],

        When metadatas is an empty list [], the condition tries to access [0]
        which raises IndexError.
        """
        chroma_results = {
            "documents": [[]],  # Empty documents
            "metadatas": [[]],  # Empty metadatas list
            "distances": [[]],
        }

        # This should NOT raise IndexError
        result = SearchResults.from_chroma(chroma_results)

        assert result.documents == []
        assert result.metadata == []
        assert result.distances == []

    def test_from_chroma_none_metadatas(self):
        """Test handling when metadatas is None"""
        chroma_results = {"documents": [["doc1"]], "metadatas": None, "distances": [[0.5]]}

        result = SearchResults.from_chroma(chroma_results)

        # Should handle None gracefully
        assert result.documents == ["doc1"]
        assert result.metadata == []

    def test_from_chroma_successful(self):
        """Test normal case with valid data"""
        chroma_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"course_title": "Test"}, {"course_title": "Test2"}]],
            "distances": [[0.5, 0.7]],
        }

        result = SearchResults.from_chroma(chroma_results)

        assert len(result.documents) == 2
        assert len(result.metadata) == 2
        assert result.metadata[0]["course_title"] == "Test"

    def test_empty_search_results(self):
        """Test creating empty search results with error message"""
        result = SearchResults.empty("Test error message")

        assert result.is_empty()
        assert result.error == "Test error message"
        assert result.documents == []


class TestVectorStoreLinkRetrieval:
    """Test link retrieval methods for explicit return bug"""

    @patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction")
    @patch("chromadb.PersistentClient")
    def test_get_lesson_link_exception_handling(self, mock_chroma_client, mock_embedding_func):
        """
        Tests Bug #2 - Missing explicit return in exception handler

        Current code implicitly returns None when exception occurs.
        Should explicitly return None for clarity.
        """
        # Create VectorStore instance with mocked ChromaDB
        mock_collection = Mock()
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        # Simulate ChromaDB raising an exception
        mock_collection.get.side_effect = Exception("Database connection lost")

        store = VectorStore(chroma_path="./test_db", embedding_model="test-model", max_results=5)

        # Should return None, not raise exception
        result = store.get_lesson_link("Test Course", 1)

        # Currently this works but we want EXPLICIT return None in the code
        assert result is None

    @patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction")
    @patch("chromadb.PersistentClient")
    def test_get_course_link_exception_handling(self, mock_chroma_client, mock_embedding_func):
        """
        Tests Bug #2 - Missing explicit return in get_course_link exception handler
        """
        mock_collection = Mock()
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        mock_collection.get.side_effect = Exception("Database error")

        store = VectorStore(chroma_path="./test_db", embedding_model="test-model", max_results=5)

        result = store.get_course_link("Test Course")

        assert result is None

    @patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction")
    @patch("chromadb.PersistentClient")
    def test_get_lesson_link_json_parse_error(self, mock_chroma_client, mock_embedding_func):
        """Test handling of corrupted lessons_json data"""
        mock_collection = Mock()
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        # Return corrupted JSON
        mock_collection.get.return_value = {"metadatas": [{"lessons_json": "invalid json {{{"}]}

        store = VectorStore(chroma_path="./test_db", embedding_model="test-model", max_results=5)

        # Should handle JSON parse error gracefully
        result = store.get_lesson_link("Test Course", 1)

        assert result is None

    @patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction")
    @patch("chromadb.PersistentClient")
    def test_get_lesson_link_successful(self, mock_chroma_client, mock_embedding_func):
        """Test successful lesson link retrieval"""
        mock_collection = Mock()
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        lessons_data = [
            {
                "lesson_number": 1,
                "lesson_title": "Intro",
                "lesson_link": "https://example.com/lesson/1",
            },
            {
                "lesson_number": 2,
                "lesson_title": "Advanced",
                "lesson_link": "https://example.com/lesson/2",
            },
        ]

        mock_collection.get.return_value = {
            "metadatas": [{"lessons_json": json.dumps(lessons_data)}]
        }

        store = VectorStore(chroma_path="./test_db", embedding_model="test-model", max_results=5)

        result = store.get_lesson_link("Test Course", 1)

        assert result == "https://example.com/lesson/1"

    @patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction")
    @patch("chromadb.PersistentClient")
    def test_get_lesson_link_not_found(self, mock_chroma_client, mock_embedding_func):
        """Test when lesson number doesn't exist"""
        mock_collection = Mock()
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        lessons_data = [
            {
                "lesson_number": 1,
                "lesson_title": "Intro",
                "lesson_link": "https://example.com/lesson/1",
            }
        ]

        mock_collection.get.return_value = {
            "metadatas": [{"lessons_json": json.dumps(lessons_data)}]
        }

        store = VectorStore(chroma_path="./test_db", embedding_model="test-model", max_results=5)

        # Request lesson 99 which doesn't exist
        result = store.get_lesson_link("Test Course", 99)

        assert result is None


class TestVectorStoreSearchEdgeCases:
    """Test search method edge cases"""

    @patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction")
    @patch("chromadb.PersistentClient")
    def test_search_with_chroma_exception(self, mock_chroma_client, mock_embedding_func):
        """Test search error handling"""
        mock_collection = Mock()
        mock_chroma_client.return_value.get_or_create_collection.return_value = mock_collection

        # Simulate ChromaDB query failure
        mock_collection.query.side_effect = Exception("ChromaDB query failed")

        store = VectorStore(chroma_path="./test_db", embedding_model="test-model", max_results=5)

        result = store.search(query="test query")

        # Should return error in SearchResults, not raise exception
        assert result.is_empty()
        assert "Search error" in result.error
