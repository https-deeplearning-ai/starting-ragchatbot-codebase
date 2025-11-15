"""
Unit tests for CourseSearchTool and ToolManager

Tests the execute() method of CourseSearchTool to ensure:
- Proper search execution
- Correct result formatting
- Source tracking
- Error handling
"""
import pytest
from unittest.mock import Mock
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


@pytest.mark.unit
class TestCourseSearchToolExecute:
    """Tests for CourseSearchTool.execute() method"""

    def test_successful_search_with_results(self, mock_vector_store, sample_search_results):
        """Test 1: Successful search returns formatted results"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?")

        # Verify search was called correctly
        mock_vector_store.search.assert_called_once_with(
            query="What is RAG?",
            course_name=None,
            lesson_number=None
        )

        # Verify result contains content
        assert isinstance(result, str)
        assert len(result) > 0
        assert "RAG stands for Retrieval-Augmented Generation" in result
        assert "[Test Course: Introduction to RAG" in result

    def test_empty_search_results(self, mock_vector_store_empty):
        """Test 2: Empty search results return appropriate message"""
        tool = CourseSearchTool(mock_vector_store_empty)

        result = tool.execute(query="nonexistent content")

        # Verify message indicates no content found
        assert isinstance(result, str)
        assert "No relevant content found" in result

    def test_search_with_course_name_filter(self, mock_vector_store):
        """Test 3: Search with course_name filter passes filter correctly"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?", course_name="Introduction to RAG")

        # Verify search was called with course filter
        mock_vector_store.search.assert_called_once_with(
            query="What is RAG?",
            course_name="Introduction to RAG",
            lesson_number=None
        )
        assert isinstance(result, str)

    def test_search_with_lesson_number_filter(self, mock_vector_store):
        """Test 4: Search with lesson_number filter passes filter correctly"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="vector databases", lesson_number=1)

        # Verify search was called with lesson filter
        mock_vector_store.search.assert_called_once_with(
            query="vector databases",
            course_name=None,
            lesson_number=1
        )
        assert isinstance(result, str)

    def test_search_with_combined_filters(self, mock_vector_store):
        """Test 5: Search with both course and lesson filters"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(
            query="tools",
            course_name="Introduction to RAG",
            lesson_number=2
        )

        # Verify both filters were passed
        mock_vector_store.search.assert_called_once_with(
            query="tools",
            course_name="Introduction to RAG",
            lesson_number=2
        )
        assert isinstance(result, str)

    def test_search_error_from_vector_store(self, mock_vector_store_error):
        """Test 6: VectorStore error is handled and returned"""
        tool = CourseSearchTool(mock_vector_store_error)

        result = tool.execute(query="test query")

        # Verify error message is returned
        assert isinstance(result, str)
        assert "Database connection failed" in result

    def test_source_tracking(self, mock_vector_store, sample_search_results):
        """Test 7: last_sources attribute is populated correctly"""
        tool = CourseSearchTool(mock_vector_store)

        # Initially no sources
        assert tool.last_sources == []

        result = tool.execute(query="What is RAG?")

        # After execution, sources should be populated
        assert len(tool.last_sources) > 0
        assert isinstance(tool.last_sources, list)

        # Check source structure
        for source in tool.last_sources:
            assert isinstance(source, dict)
            assert "text" in source
            assert "url" in source

        # Check specific source content
        first_source = tool.last_sources[0]
        assert "Test Course: Introduction to RAG" in first_source["text"]
        assert first_source["url"] is not None

    def test_result_formatting_with_metadata(self, mock_vector_store, sample_search_results):
        """Test 8: Results are formatted correctly with course and lesson info"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="What is RAG?")

        # Check formatting structure
        assert "[Test Course: Introduction to RAG" in result
        assert "Lesson 0]" in result or "Lesson 1]" in result or "Lesson 2]" in result

        # Check content is included
        assert "RAG stands for Retrieval-Augmented Generation" in result

    def test_missing_metadata_handling(self, mock_vector_store):
        """Test 9: Missing metadata fields are handled gracefully"""
        # Create search results with missing metadata fields
        incomplete_results = SearchResults(
            documents=["Some content without full metadata"],
            metadata=[{"course_title": "Test Course"}],  # Missing lesson_number and links
            distances=[0.1],
            error=None
        )
        mock_vector_store.search.return_value = incomplete_results

        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test")

        # Should not crash and should return formatted result
        assert isinstance(result, str)
        assert "Test Course" in result
        assert "Some content without full metadata" in result


@pytest.mark.unit
class TestToolManager:
    """Tests for ToolManager class"""

    def test_register_and_execute_tool(self, mock_vector_store):
        """Test tool registration and execution"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)

        # Register tool
        manager.register_tool(tool)

        # Verify tool is registered
        assert "search_course_content" in manager.tools

        # Execute tool
        result = manager.execute_tool("search_course_content", query="test query")

        # Verify execution
        assert isinstance(result, str)
        mock_vector_store.search.assert_called_once()

    def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist"""
        manager = ToolManager()

        result = manager.execute_tool("nonexistent_tool", query="test")

        # Should return error message
        assert "Tool 'nonexistent_tool' not found" in result

    def test_get_tool_definitions(self, mock_vector_store):
        """Test retrieving tool definitions"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        definitions = manager.get_tool_definitions()

        # Should return list of definitions
        assert isinstance(definitions, list)
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"
        assert "description" in definitions[0]
        assert "input_schema" in definitions[0]

    def test_get_last_sources(self, mock_vector_store, sample_search_results):
        """Test retrieving sources from last search"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute search
        manager.execute_tool("search_course_content", query="test")

        # Get sources
        sources = manager.get_last_sources()

        # Verify sources are returned
        assert isinstance(sources, list)
        assert len(sources) > 0

    def test_reset_sources(self, mock_vector_store, sample_search_results):
        """Test resetting sources after retrieval"""
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(tool)

        # Execute and verify sources exist
        manager.execute_tool("search_course_content", query="test")
        assert len(manager.get_last_sources()) > 0

        # Reset sources
        manager.reset_sources()

        # Verify sources are cleared
        assert len(manager.get_last_sources()) == 0


@pytest.mark.unit
class TestCourseSearchToolEdgeCases:
    """Edge case tests for CourseSearchTool"""

    def test_empty_query_string(self, mock_vector_store):
        """Test with empty query string"""
        tool = CourseSearchTool(mock_vector_store)

        result = tool.execute(query="")

        # Should still make the call
        mock_vector_store.search.assert_called_once()
        assert isinstance(result, str)

    def test_very_long_query(self, mock_vector_store):
        """Test with very long query string"""
        tool = CourseSearchTool(mock_vector_store)
        long_query = "What is RAG? " * 100  # Very long repeated query

        result = tool.execute(query=long_query)

        # Should handle long queries
        mock_vector_store.search.assert_called_once()
        assert isinstance(result, str)

    def test_special_characters_in_query(self, mock_vector_store):
        """Test query with special characters"""
        tool = CourseSearchTool(mock_vector_store)
        special_query = "What is RAG? <script>alert('test')</script>"

        result = tool.execute(query=special_query)

        # Should handle special characters
        mock_vector_store.search.assert_called_once()
        assert isinstance(result, str)

    def test_exception_during_search(self, mock_vector_store_exception):
        """Test that exceptions during search are propagated"""
        tool = CourseSearchTool(mock_vector_store_exception)

        # This should raise an exception
        with pytest.raises(Exception) as exc_info:
            tool.execute(query="test")

        assert "ChromaDB connection lost" in str(exc_info.value)
