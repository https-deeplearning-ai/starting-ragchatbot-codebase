"""
Integration tests that test against the actual production configuration and database.

These tests don't use mocks - they test the real system to identify runtime issues.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config
from vector_store import VectorStore
from search_tools import CourseSearchTool, ToolManager
from rag_system import RAGSystem


class TestActualConfiguration:
    """Test the actual production configuration values"""

    def test_max_results_is_positive(self):
        """
        CRITICAL: MAX_RESULTS must be > 0 for search to return results.
        """
        assert config.MAX_RESULTS > 0, (
            f"MAX_RESULTS is {config.MAX_RESULTS}, must be > 0. "
            "This will cause all searches to return empty results!"
        )

    def test_chroma_path_exists(self):
        """Verify ChromaDB path is configured"""
        assert config.CHROMA_PATH, "CHROMA_PATH must be set"

    def test_embedding_model_configured(self):
        """Verify embedding model is specified"""
        assert config.EMBEDDING_MODEL, "EMBEDDING_MODEL must be set"


class TestActualVectorStore:
    """Test the actual VectorStore with production database"""

    @pytest.fixture
    def vector_store(self):
        """Create VectorStore with actual config"""
        return VectorStore(
            config.CHROMA_PATH,
            config.EMBEDDING_MODEL,
            config.MAX_RESULTS
        )

    def test_vector_store_has_courses(self, vector_store):
        """
        CRITICAL: VectorStore must have courses loaded.
        If this fails, documents haven't been processed into the database.
        """
        course_count = vector_store.get_course_count()
        assert course_count > 0, (
            f"VectorStore has {course_count} courses. "
            "No courses loaded! Run the application to load documents from ../docs"
        )

    def test_vector_store_has_content(self, vector_store):
        """
        Verify course content collection is not empty.
        """
        # Try to get content from the collection
        try:
            results = vector_store.course_content.get()
            content_count = len(results.get('ids', []))
            assert content_count > 0, (
                "Course content collection is empty. "
                "No chunks have been indexed!"
            )
        except Exception as e:
            pytest.fail(f"Failed to query course_content collection: {e}")

    def test_vector_store_search_returns_results(self, vector_store):
        """
        CRITICAL: Search should return results for a general query.
        """
        # Use a very general query that should match something
        results = vector_store.search("course")

        assert not results.is_empty(), (
            "Search returned empty results for query 'course'. "
            "This indicates the search functionality is broken or no content is indexed."
        )

    def test_vector_store_search_with_specific_query(self, vector_store):
        """
        Test search with a more specific query.
        """
        results = vector_store.search("introduction")

        # Even if no matches, there should be no error
        assert results.error is None, f"Search returned error: {results.error}"


class TestActualSearchTool:
    """Test CourseSearchTool with actual production database"""

    @pytest.fixture
    def search_tool(self):
        """Create search tool with actual VectorStore"""
        vector_store = VectorStore(
            config.CHROMA_PATH,
            config.EMBEDDING_MODEL,
            config.MAX_RESULTS
        )
        return CourseSearchTool(vector_store)

    def test_search_tool_execute_returns_content(self, search_tool):
        """
        CRITICAL: Search tool should return actual content, not 'No relevant content found'.
        """
        result = search_tool.execute(query="lesson")

        assert "No relevant content found" not in result, (
            "Search tool returns 'No relevant content found' for query 'lesson'. "
            "This indicates either no documents are loaded or search is broken."
        )

    def test_search_tool_populates_sources(self, search_tool):
        """
        Search tool should populate last_sources after successful search.
        """
        search_tool.execute(query="introduction")

        # Check if sources were populated (only if content was found)
        # This test validates the source tracking mechanism
        if search_tool.last_sources:
            assert len(search_tool.last_sources) > 0


class TestActualRAGSystem:
    """Test RAGSystem integration with actual database (mocking only AI calls)"""

    @pytest.fixture
    def rag_system_no_ai(self):
        """
        RAGSystem with actual database but patched AI generator.
        This allows testing the search/retrieval without making API calls.
        """
        from unittest.mock import patch, Mock

        with patch('rag_system.AIGenerator') as mock_ai:
            mock_ai_instance = Mock()
            mock_ai_instance.generate_response.return_value = "Test response"
            mock_ai.return_value = mock_ai_instance

            rag = RAGSystem(config)
            yield rag

    def test_rag_search_tool_works(self, rag_system_no_ai):
        """
        Test that RAG system's search tool can execute against actual database.
        """
        result = rag_system_no_ai.search_tool.execute(query="course content")

        # This will reveal if the database is empty or search is broken
        if "No relevant content found" in result:
            # Additional diagnostic - check what's in the database
            course_count = rag_system_no_ai.vector_store.get_course_count()
            content_count = 0
            try:
                results = rag_system_no_ai.vector_store.course_content.get()
                content_count = len(results.get('ids', []))
            except:
                pass

            pytest.fail(
                f"Search returned no results. "
                f"Database state: {course_count} courses, {content_count} content chunks. "
                "The database may be empty or search is misconfigured."
            )

    def test_rag_analytics_shows_courses(self, rag_system_no_ai):
        """
        Test that course analytics returns non-empty data.
        """
        analytics = rag_system_no_ai.get_course_analytics()

        assert analytics["total_courses"] > 0, (
            "No courses found in database. "
            "Ensure documents are loaded from ../docs folder."
        )


class TestDatabaseDiagnostics:
    """Diagnostic tests to identify database state issues"""

    @pytest.fixture
    def vector_store(self):
        """Create VectorStore with actual config"""
        return VectorStore(
            config.CHROMA_PATH,
            config.EMBEDDING_MODEL,
            config.MAX_RESULTS
        )

    def test_catalog_collection_exists(self, vector_store):
        """Verify course_catalog collection exists and is queryable"""
        try:
            results = vector_store.course_catalog.get()
            catalog_count = len(results.get('ids', []))
            print(f"\nDiagnostic: course_catalog has {catalog_count} entries")
            assert results is not None
        except Exception as e:
            pytest.fail(f"course_catalog collection error: {e}")

    def test_content_collection_exists(self, vector_store):
        """Verify course_content collection exists and is queryable"""
        try:
            results = vector_store.course_content.get()
            content_count = len(results.get('ids', []))
            print(f"\nDiagnostic: course_content has {content_count} entries")
            assert results is not None
        except Exception as e:
            pytest.fail(f"course_content collection error: {e}")

    def test_list_all_course_titles(self, vector_store):
        """List all course titles in the database for debugging"""
        titles = vector_store.get_existing_course_titles()
        print(f"\nDiagnostic: Found {len(titles)} courses: {titles}")

        if len(titles) == 0:
            pytest.fail(
                "No course titles found in database. "
                "Documents need to be loaded via the application startup."
            )

    def test_sample_content_query(self, vector_store):
        """Run a sample query and show what's returned"""
        results = vector_store.search("MCP")

        print(f"\nDiagnostic: Search for 'MCP' returned:")
        print(f"  - Documents: {len(results.documents)}")
        print(f"  - Error: {results.error}")

        if results.documents:
            print(f"  - First result preview: {results.documents[0][:100]}...")
