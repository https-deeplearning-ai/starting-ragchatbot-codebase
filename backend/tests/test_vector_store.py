"""
Tests for VectorStore functionality and ChromaDB operations
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


class TestSearchResults:
    """Test cases for SearchResults class"""

    def test_from_chroma_success(self):
        """Test creating SearchResults from successful ChromaDB response"""
        chroma_results = {
            'documents': [['Document 1', 'Document 2']],
            'metadatas': [[{'key': 'value1'}, {'key': 'value2'}]],
            'distances': [[0.1, 0.2]]
        }

        results = SearchResults.from_chroma(chroma_results)

        assert results.documents == ['Document 1', 'Document 2']
        assert results.metadatas == [{'key': 'value1'}, {'key': 'value2'}]
        assert results.distances == [0.1, 0.2]
        assert results.error is None
        assert not results.is_empty()

    def test_from_chroma_empty_results(self):
        """Test creating SearchResults from empty ChromaDB response"""
        chroma_results = {
            'documents': [],
            'metadatas': [],
            'distances': []
        }

        results = SearchResults.from_chroma(chroma_results)

        assert results.documents == []
        assert results.metadatas == []
        assert results.distances == []
        assert results.error is None
        assert results.is_empty()

    def test_from_chroma_missing_keys(self):
        """Test creating SearchResults from ChromaDB response with missing keys"""
        chroma_results = {}

        results = SearchResults.from_chroma(chroma_results)

        assert results.documents == []
        assert results.metadatas == []
        assert results.distances == []
        assert results.error is None
        assert results.is_empty()

    def test_empty_with_error(self):
        """Test creating empty SearchResults with error message"""
        error_msg = "Search failed: Database error"
        results = SearchResults.empty(error_msg)

        assert results.documents == []
        assert results.metadatas == []
        assert results.distances == []
        assert results.error == error_msg
        assert results.is_empty()

    def test_is_empty_true(self):
        """Test is_empty returns True for empty results"""
        results = SearchResults([], [], [])
        assert results.is_empty() is True

    def test_is_empty_false(self):
        """Test is_empty returns False for non-empty results"""
        results = SearchResults(['Document'], [{'key': 'value'}], [0.1])
        assert results.is_empty() is False


class TestVectorStore:
    """Test cases for VectorStore class"""

    def test_initialization(self, temp_chroma_db):
        """Test VectorStore initialization"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction') as mock_embedding:

            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance
            mock_embedding_instance = Mock()
            mock_embedding.return_value = mock_embedding_instance

            # Create VectorStore
            store = VectorStore(temp_chroma_db, "test-model", 5)

            # Verify client initialization
            mock_client.assert_called_once_with(
                path=temp_chroma_db,
                settings=mock_client.ANY  # Settings object
            )

            # Verify embedding function
            mock_embedding.assert_called_once_with(model_name="test-model")

            # Verify collections were created
            assert mock_client_instance.get_or_create_collection.call_count == 2
            mock_client_instance.get_or_create_collection.assert_any_call(
                "course_catalog",
                embedding_function=mock_embedding_instance
            )
            mock_client_instance.get_or_create_collection.assert_any_call(
                "course_content",
                embedding_function=mock_embedding_instance
            )

            # Verify attributes
            assert store.max_results == 5
            assert store.client == mock_client_instance
            assert store.embedding_function == mock_embedding_instance
            assert store.course_catalog is not None
            assert store.course_content is not None

    def test_search_successful(self, sample_course_chunks):
        """Test successful search operation"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client and collections
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup search results
            mock_course_content.query.return_value = {
                'documents': [['Found content about machine learning']],
                'metadatas': [[{
                    'course_title': 'Machine Learning Fundamentals',
                    'lesson_number': 1,
                    'chunk_index': 0
                }]],
                'distances': [[0.1]]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test search
            results = store.search("machine learning")

            # Verify search was performed
            mock_course_content.query.assert_called_once_with(
                query_texts=["machine learning"],
                n_results=5,
                where=None
            )

            # Verify results
            assert not results.is_empty()
            assert len(results.documents) == 1
            assert "Found content about machine learning" in results.documents[0]
            assert results.metadatas[0]['course_title'] == "Machine Learning Fundamentals"
            assert results.metadatas[0]['lesson_number'] == 1

    def test_search_with_course_filter(self):
        """Test search with course name filter"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup course name resolution
            mock_course_catalog.query.return_value = {
                'documents': [['Machine Learning Fundamentals']],
                'metadatas': [[{'title': 'Machine Learning Fundamentals'}]]
            }

            # Setup search results
            mock_course_content.query.return_value = {
                'documents': [['Course-specific content']],
                'metadatas': [[{'course_title': 'Machine Learning Fundamentals'}]],
                'distances': [[0.1]]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test search with course filter
            results = store.search("linear regression", course_name="Machine Learning")

            # Verify course resolution
            mock_course_catalog.query.assert_called_once_with(
                query_texts=["Machine Learning"],
                n_results=1
            )

            # Verify search with filter
            mock_course_content.query.assert_called_once_with(
                query_texts=["linear regression"],
                n_results=5,
                where={"course_title": "Machine Learning Fundamentals"}
            )

    def test_search_with_lesson_filter(self):
        """Test search with lesson number filter"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup search results
            mock_course_content.query.return_value = {
                'documents': [['Lesson-specific content']],
                'metadatas': [[{'lesson_number': 2}]],
                'distances': [[0.1]]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test search with lesson filter
            results = store.search("topic", lesson_number=2)

            # Verify search with filter
            mock_course_content.query.assert_called_once_with(
                query_texts=["topic"],
                n_results=5,
                where={"lesson_number": 2}
            )

    def test_search_with_both_filters(self):
        """Test search with both course and lesson filters"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup course resolution
            mock_course_catalog.query.return_value = {
                'documents': [['ML Course']],
                'metadatas': [[{'title': 'Machine Learning Fundamentals'}]]
            }

            # Setup search results
            mock_course_content.query.return_value = {
                'documents': [['Filtered content']],
                'metadatas': [[{'course_title': 'Machine Learning Fundamentals', 'lesson_number': 3}]],
                'distances': [[0.1]]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test search with both filters
            results = store.search("topic", course_name="ML", lesson_number=3)

            # Verify search with combined filter
            mock_course_content.query.assert_called_once_with(
                query_texts=["topic"],
                n_results=5,
                where={"$and": [
                    {"course_title": "Machine Learning Fundamentals"},
                    {"lesson_number": 3}
                ]}
            )

    def test_search_course_not_found(self):
        """Test search when course name resolution fails"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup course resolution to return empty results
            mock_course_catalog.query.return_value = {
                'documents': [[]],
                'metadatas': [[]]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test search with non-existent course
            results = store.search("topic", course_name="Nonexistent Course")

            # Verify error result
            assert results.is_empty()
            assert "No course found matching 'Nonexistent Course'" in results.error

            # Verify search was not performed
            mock_course_content.query.assert_not_called()

    def test_search_with_custom_limit(self):
        """Test search with custom result limit"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup search results
            mock_course_content.query.return_value = {
                'documents': [['Limited results']],
                'metadatas': [[{}]],
                'distances': [[0.1]]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test search with custom limit
            results = store.search("topic", limit=2)

            # Verify search used custom limit
            mock_course_content.query.assert_called_once_with(
                query_texts=["topic"],
                n_results=2,
                where=None
            )

    def test_search_exception_handling(self):
        """Test search exception handling"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup search to raise exception
            mock_course_content.query.side_effect = Exception("Database connection failed")

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test search exception handling
            results = store.search("topic")

            # Verify error result
            assert results.is_empty()
            assert "Search error: Database connection failed" in results.error

    def test_resolve_course_name_success(self):
        """Test successful course name resolution"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup course resolution
            mock_course_catalog.query.return_value = {
                'documents': [['Machine Learning Fundamentals']],
                'metadatas': [[{'title': 'Machine Learning Fundamentals'}]]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test course resolution
            resolved_title = store._resolve_course_name("Machine Learning")

            # Verify resolution
            assert resolved_title == "Machine Learning Fundamentals"
            mock_course_catalog.query.assert_called_once_with(
                query_texts=["Machine Learning"],
                n_results=1
            )

    def test_resolve_course_name_not_found(self):
        """Test course name resolution when course not found"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup empty resolution
            mock_course_catalog.query.return_value = {
                'documents': [[]],
                'metadatas': [[]]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test course resolution
            resolved_title = store._resolve_course_name("Nonexistent Course")

            # Verify resolution failed
            assert resolved_title is None

    def test_resolve_course_name_exception(self):
        """Test course name resolution exception handling"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup resolution to raise exception
            mock_course_catalog.query.side_effect = Exception("Resolution error")

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test course resolution
            resolved_title = store._resolve_course_name("Some Course")

            # Verify exception was handled
            assert resolved_title is None

    def test_add_course_metadata(self, sample_course):
        """Test adding course metadata"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test adding course metadata
            store.add_course_metadata(sample_course)

            # Verify metadata was added
            mock_course_catalog.add.assert_called_once()
            call_args = mock_course_catalog.add.call_args

            assert call_args[1]["documents"] == ["Machine Learning Fundamentals"]
            assert call_args[1]["ids"] == ["Machine Learning Fundamentals"]

            metadata = call_args[1]["metadatas"][0]
            assert metadata["title"] == "Machine Learning Fundamentals"
            assert metadata["instructor"] == "Dr. Test Instructor"
            assert metadata["course_link"] == "https://example.com/ml-course"
            assert metadata["lesson_count"] == 3
            assert "lessons_json" in metadata

    def test_add_course_content(self, sample_course_chunks):
        """Test adding course content chunks"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test adding course content
            store.add_course_content(sample_course_chunks)

            # Verify content was added
            mock_course_content.add.assert_called_once()
            call_args = mock_course_content.add.call_args

            # Verify documents
            expected_docs = [chunk.content for chunk in sample_course_chunks]
            assert call_args[1]["documents"] == expected_docs

            # Verify metadata
            expected_metadata = [
                {
                    "course_title": chunk.course_title,
                    "lesson_number": chunk.lesson_number,
                    "chunk_index": chunk.chunk_index
                }
                for chunk in sample_course_chunks
            ]
            assert call_args[1]["metadatas"] == expected_metadata

            # Verify IDs
            expected_ids = [
                f"{chunk.course_title.replace(' ', '_')}_{chunk.chunk_index}"
                for chunk in sample_course_chunks
            ]
            assert call_args[1]["ids"] == expected_ids

    def test_clear_all_data(self):
        """Test clearing all data"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test clearing data
            store.clear_all_data()

            # Verify collections were deleted
            mock_client_instance.delete_collection.assert_has_calls([
                call("course_catalog"),
                call("course_content")
            ])

            # Verify collections were recreated
            assert mock_client_instance.get_or_create_collection.call_count == 4  # 2 for init + 2 for recreate

    def test_get_existing_course_titles(self):
        """Test getting existing course titles"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup course titles
            mock_course_catalog.get.return_value = {
                'ids': ['Course 1', 'Course 2', 'Course 3']
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test getting course titles
            titles = store.get_existing_course_titles()

            # Verify results
            assert titles == ['Course 1', 'Course 2', 'Course 3']
            mock_course_catalog.get.assert_called_once()

    def test_get_course_count(self):
        """Test getting course count"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup course data
            mock_course_catalog.get.return_value = {
                'ids': ['Course 1', 'Course 2', 'Course 3', 'Course 4']
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test getting course count
            count = store.get_course_count()

            # Verify results
            assert count == 4
            mock_course_catalog.get.assert_called_once()

    def test_get_all_courses_metadata(self):
        """Test getting all courses metadata"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Setup metadata with JSON lessons
            mock_course_catalog.get.return_value = {
                'metadatas': [
                    {
                        'title': 'Course 1',
                        'instructor': 'Instructor 1',
                        'lessons_json': '[{"lesson_number": 1, "lesson_title": "Lesson 1"}]'
                    },
                    {
                        'title': 'Course 2',
                        'instructor': 'Instructor 2',
                        'lessons_json': '[{"lesson_number": 1, "lesson_title": "Lesson 1"}]'
                    }
                ]
            }

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test getting courses metadata
            metadata = store.get_all_courses_metadata()

            # Verify results
            assert len(metadata) == 2
            assert metadata[0]['title'] == 'Course 1'
            assert metadata[0]['instructor'] == 'Instructor 1'
            assert 'lessons' in metadata[0]
            assert 'lessons_json' not in metadata[0]  # Should be parsed and removed
            assert isinstance(metadata[0]['lessons'], list)

    def test_build_filter_none(self):
        """Test _build_filter with no filters"""
        store = VectorStore("./test_db", "test-model", 5)
        filter_dict = store._build_filter(None, None)
        assert filter_dict is None

    def test_build_filter_course_only(self):
        """Test _build_filter with only course filter"""
        store = VectorStore("./test_db", "test-model", 5)
        filter_dict = store._build_filter("Test Course", None)
        assert filter_dict == {"course_title": "Test Course"}

    def test_build_filter_lesson_only(self):
        """Test _build_filter with only lesson filter"""
        store = VectorStore("./test_db", "test-model", 5)
        filter_dict = store._build_filter(None, 2)
        assert filter_dict == {"lesson_number": 2}

    def test_build_filter_both(self):
        """Test _build_filter with both filters"""
        store = VectorStore("./test_db", "test-model", 5)
        filter_dict = store._build_filter("Test Course", 2)
        assert filter_dict == {"$and": [
            {"course_title": "Test Course"},
            {"lesson_number": 2}
        ]}

    def test_edge_cases(self, sample_course_chunks):
        """Test edge cases and error conditions"""
        with patch('vector_store.chromadb.PersistentClient') as mock_client, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):

            # Setup mock client
            mock_client_instance = Mock()
            mock_client.return_value = mock_client_instance

            mock_course_catalog = Mock()
            mock_course_content = Mock()
            mock_client_instance.get_or_create_collection.side_effect = [
                mock_course_catalog,
                mock_course_content
            ]

            # Create VectorStore
            store = VectorStore("./test_db", "test-model", 5)

            # Test adding empty chunks
            store.add_course_content([])  # Should not raise error
            mock_course_content.add.assert_not_called()

            # Reset mock
            mock_course_content.add.reset_mock()

            # Test getting course titles with error
            mock_course_catalog.get.side_effect = Exception("Database error")
            titles = store.get_existing_course_titles()
            assert titles == []

            # Test getting course count with error
            count = store.get_course_count()
            assert count == 0

            # Test getting metadata with error
            metadata = store.get_all_courses_metadata()
            assert metadata == []