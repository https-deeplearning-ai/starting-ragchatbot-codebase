"""Tests for CourseSearchTool in search_tools.py"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.search_tools import CourseSearchTool, ToolManager
from backend.vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool.execute() method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.tool = CourseSearchTool(self.mock_vector_store)

    def test_execute_with_empty_results(self):
        """Test execute() when search returns no results"""
        self.mock_vector_store.search.return_value = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        result = self.tool.execute(query="test query")
        assert "No relevant content found" in result
        self.mock_vector_store.search.assert_called_once()

    def test_execute_with_valid_results(self):
        """Test execute() with valid search results"""
        self.mock_vector_store.search.return_value = SearchResults(
            documents=["Content about Python basics"],
            metadata=[{"course_title": "Python 101", "lesson_number": 1}],
            distances=[0.1]
        )
        result = self.tool.execute(query="Python basics")
        assert "Python 101" in result
        assert "Content about Python basics" in result
        assert len(self.tool.last_sources) == 1

    def test_execute_with_course_filter(self):
        """Test execute() with course name filter"""
        self.mock_vector_store.search.return_value = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        result = self.tool.execute(query="test", course_name="Python 101")
        assert "in course 'Python 101'" in result

    def test_execute_with_search_error(self):
        """Test execute() when search returns an error"""
        self.mock_vector_store.search.return_value = SearchResults.empty(
            "Database connection failed"
        )
        result = self.tool.execute(query="test")
        assert "Database connection failed" in result

    def test_get_tool_definition(self):
        """Test get_tool_definition() returns correct schema"""
        definition = self.tool.get_tool_definition()
        assert definition["name"] == "search_course_content"
        assert "input_schema" in definition


class TestToolManager:
    """Test suite for ToolManager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = ToolManager()
        self.mock_tool = Mock()
        self.mock_tool.get_tool_definition.return_value = {
            "name": "test_tool",
            "description": "Test tool"
        }

    def test_register_tool(self):
        """Test registering a tool"""
        self.manager.register_tool(self.mock_tool)
        assert "test_tool" in self.manager.tools

    def test_execute_tool(self):
        """Test executing a tool"""
        self.mock_tool.execute.return_value = "Tool result"
        self.manager.register_tool(self.mock_tool)
        result = self.manager.execute_tool("test_tool", param1="value1")
        assert result == "Tool result"

    def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist"""
        result = self.manager.execute_tool("nonexistent_tool")
        assert "not found" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
