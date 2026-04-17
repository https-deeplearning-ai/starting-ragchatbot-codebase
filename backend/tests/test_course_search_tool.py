"""
Unit tests for CourseSearchTool.execute() and _format_results().

Diagnostic focus: Does the tool correctly surface VectorStore errors?
Does it populate self.last_sources? Does it format results correctly?
"""
import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:

    def test_execute_returns_formatted_content_on_success(self, mock_vector_store, sample_search_results):
        """
        WHAT: execute() with a working VectorStore returns formatted content.
        ASSERT: returned string contains course title and document text.
        FAILURE MEANS: _format_results is broken or not called.
        """
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="what is python")
        assert "Python Fundamentals" in result
        assert "Lesson content about Python basics." in result

    def test_execute_calls_store_search_with_correct_args(self, mock_vector_store):
        """
        WHAT: execute() passes query/course_name/lesson_number through to store.search().
        ASSERT: store.search called with exactly the right keyword args.
        FAILURE MEANS: parameter forwarding broken → wrong ChromaDB filters applied.
        """
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="variables", course_name="Python", lesson_number=3)
        mock_vector_store.search.assert_called_once_with(
            query="variables", course_name="Python", lesson_number=3
        )

    def test_execute_populates_last_sources(self, mock_vector_store):
        """
        WHAT: After execute(), tool.last_sources is populated with one entry per result.
        ASSERT: last_sources has 2 entries with 'label' and 'url' keys.
        FAILURE MEANS: ToolManager.get_last_sources() returns [] even after successful search
                       → sources never reach the frontend.
        """
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="python basics")
        assert len(tool.last_sources) == 2
        for source in tool.last_sources:
            assert "label" in source
            assert "url" in source

    def test_execute_fetches_lesson_link_for_each_result(self, mock_vector_store):
        """
        WHAT: _format_results calls get_lesson_link once per result that has a lesson_number.
        ASSERT: get_lesson_link called exactly twice (for 2 results with lesson_number).
        FAILURE MEANS: source URLs always None in the frontend.
        """
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="python basics")
        assert mock_vector_store.get_lesson_link.call_count == 2

    def test_execute_returns_error_string_verbatim_when_store_errors(self, mock_vector_store):
        """
        WHAT: When store.search returns SearchResults with .error set,
              execute() returns that error string directly.
        ASSERT: return value IS the error string.
        FAILURE MEANS: ChromaDB error strings reach Claude as tool result,
                       causing Claude to report failure. THIS IS THE LIKELY ROOT CAUSE.
        """
        error_msg = (
            "Search error: Number of requested results 5 is greater than "
            "number of elements in index 0"
        )
        mock_vector_store.search.return_value = SearchResults.empty(error_msg)
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="anything")
        assert result == error_msg

    def test_execute_returns_no_content_message_when_empty(self, mock_vector_store, empty_search_results):
        """
        WHAT: When results are empty (no error, just no hits), execute() returns
              the 'No relevant content found' sentinel.
        ASSERT: return value starts with 'No relevant content found'.
        FAILURE MEANS: Empty DB causes tool to silently return empty string or crash.
        """
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="anything")
        assert result.startswith("No relevant content found")

    def test_execute_includes_course_filter_in_empty_message(self, mock_vector_store, empty_search_results):
        """
        WHAT: Empty result message mentions the requested course name.
        ASSERT: message contains the course_name that was requested.
        FAILURE MEANS: User can't tell which course had no content.
        """
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="anything", course_name="Python")
        assert "Python" in result

    def test_execute_does_not_update_sources_on_error(self, mock_vector_store):
        """
        WHAT: When store returns an error result, last_sources is NOT overwritten.
        ASSERT: Pre-seeded stale sources remain unchanged after an errored execute().
        FAILURE MEANS: Stale sources from a previous query could leak into this response.
        """
        mock_vector_store.search.return_value = SearchResults.empty("Search error: boom")
        tool = CourseSearchTool(mock_vector_store)
        tool.last_sources = [{"label": "stale", "url": None}]
        tool.execute(query="anything")
        # Error branch returns early — last_sources should NOT have been updated
        assert tool.last_sources == [{"label": "stale", "url": None}]


class TestFormatResults:

    def test_format_results_header_format(self, mock_vector_store, sample_search_results):
        """
        WHAT: _format_results includes [CourseName - Lesson N] headers.
        ASSERT: expected header appears in output.
        FAILURE MEANS: Claude receives raw content without course context headers.
        """
        tool = CourseSearchTool(mock_vector_store)
        result = tool._format_results(sample_search_results)
        assert "[Python Fundamentals - Lesson 1]" in result

    def test_format_results_no_lesson_number_omits_lesson_from_header(self, mock_vector_store):
        """
        WHAT: When lesson_number is None in metadata, header is just [CourseName].
        ASSERT: header does not contain 'Lesson'.
        FAILURE MEANS: Metadata extraction crashes on missing lesson_number.
        """
        results = SearchResults(
            documents=["Content without lesson number"],
            metadata=[{"course_title": "Advanced Python", "lesson_number": None}],
            distances=[0.1]
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool._format_results(results)
        assert "[Advanced Python]" in result
        assert "Lesson" not in result

    def test_format_results_separates_results_with_double_newline(self, mock_vector_store, sample_search_results):
        """
        WHAT: Multiple results are joined with double newlines.
        ASSERT: '\\n\\n' appears in the output.
        FAILURE MEANS: Output is garbled — all results run together.
        """
        tool = CourseSearchTool(mock_vector_store)
        result = tool._format_results(sample_search_results)
        assert "\n\n" in result


class TestToolManager:

    def test_tool_manager_get_last_sources_returns_first_nonempty(self, mock_vector_store):
        """
        WHAT: get_last_sources() returns the first non-empty last_sources from registered tools.
        ASSERT: returned list matches what was set on the tool.
        FAILURE MEANS: RAGSystem.query() always returns empty sources list.
        """
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        tool.last_sources = [{"label": "Python - Lesson 1", "url": "https://example.com"}]
        manager.register_tool(tool)
        assert manager.get_last_sources() == [{"label": "Python - Lesson 1", "url": "https://example.com"}]

    def test_tool_manager_reset_sources_clears_all_tools(self, mock_vector_store):
        """
        WHAT: reset_sources() clears last_sources on all registered tools.
        ASSERT: After reset, last_sources == [].
        FAILURE MEANS: Sources from query N bleed into query N+1.
        """
        manager = ToolManager()
        tool = CourseSearchTool(mock_vector_store)
        tool.last_sources = [{"label": "stale", "url": None}]
        manager.register_tool(tool)
        manager.reset_sources()
        assert tool.last_sources == []

    def test_tool_manager_execute_unknown_tool_returns_error_string(self, mock_vector_store):
        """
        WHAT: Calling execute_tool with an unregistered name returns an error string.
        ASSERT: Returns string containing 'not found'.
        FAILURE MEANS: Unknown tool name crashes instead of returning a recoverable error.
        """
        manager = ToolManager()
        result = manager.execute_tool("nonexistent_tool", query="test")
        assert "not found" in result
