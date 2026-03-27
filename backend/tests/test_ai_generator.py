"""Tests for AIGenerator in ai_generator.py"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from backend.ai_generator import AIGenerator


class TestAIGenerator:
    """Test suite for AIGenerator.generate_response() method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_client = Mock()
        with patch('backend.ai_generator.anthropic.Anthropic', return_value=self.mock_client):
            self.generator = AIGenerator(api_key="test_key", model="claude-3-sonnet")

    def test_generate_response_without_tools(self):
        """Test generate_response() without tools"""
        # Arrange
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="This is a response")]
        self.mock_client.messages.create.return_value = mock_response

        # Act
        result = self.generator.generate_response(query="What is Python?")

        # Assert
        assert result == "This is a response"
        self.mock_client.messages.create.assert_called_once()
        call_args = self.mock_client.messages.create.call_args
        assert call_args[1]["messages"][0]["content"] == "What is Python?"

    def test_generate_response_with_conversation_history(self):
        """Test generate_response() with conversation history"""
        # Arrange
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Follow-up response")]
        self.mock_client.messages.create.return_value = mock_response

        history = "User: Previous question\nAssistant: Previous answer"

        # Act
        result = self.generator.generate_response(
            query="Follow-up question",
            conversation_history=history
        )

        # Assert
        assert result == "Follow-up response"
        call_args = self.mock_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous conversation" in system_content
        assert history in system_content

    def test_generate_response_with_tools(self):
        """Test generate_response() with tools available"""
        # Arrange
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response with tools")]
        self.mock_client.messages.create.return_value = mock_response

        tools = [{"name": "search", "description": "Search tool"}]

        # Act
        result = self.generator.generate_response(
            query="Search for something",
            tools=tools
        )

        # Assert
        assert result == "Response with tools"
        call_args = self.mock_client.messages.create.call_args
        assert "tools" in call_args[1]
        assert call_args[1]["tools"] == tools
        assert call_args[1]["tool_choice"]["type"] == "auto"

    def test_generate_response_with_tool_use(self):
        """Test generate_response() when AI uses a tool"""
        # Arrange
        # First response: AI wants to use a tool
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "Python basics"}

        first_response = Mock()
        first_response.stop_reason = "tool_use"
        first_response.content = [tool_use_block]

        # Second response: Final answer after tool execution
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="Here is the answer")]

        self.mock_client.messages.create.side_effect = [first_response, final_response]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search results"

        tools = [{"name": "search_course_content"}]

        # Act
        result = self.generator.generate_response(
            query="What is Python?",
            tools=tools,
            tool_manager=mock_tool_manager
        )

        # Assert
        assert result == "Here is the answer"
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="Python basics"
        )
        # Should have made two API calls
        assert self.mock_client.messages.create.call_count == 2

    def test_generate_response_tool_execution_flow(self):
        """Test the complete tool execution flow"""
        # Arrange
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_456"
        tool_use_block.input = {"query": "test", "course_name": "Python"}

        first_response = Mock()
        first_response.stop_reason = "tool_use"
        first_response.content = [tool_use_block]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_response.content = [Mock(text="Final answer")]

        self.mock_client.messages.create.side_effect = [first_response, final_response]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool output"

        # Act
        result = self.generator.generate_response(
            query="Query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Assert
        assert result == "Final answer"
        # Verify tool was called with correct parameters
        mock_tool_manager.execute_tool.assert_called_once()
        call_args = mock_tool_manager.execute_tool.call_args
        assert call_args[0][0] == "search_course_content"
        assert call_args[1]["query"] == "test"
        assert call_args[1]["course_name"] == "Python"

    def test_generate_response_without_tool_manager(self):
        """Test generate_response() when tool_use occurs but no tool_manager provided"""
        # Arrange
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"

        response = Mock()
        response.stop_reason = "tool_use"
        response.content = [tool_use_block]
        self.mock_client.messages.create.return_value = response

        # Act & Assert - should handle gracefully
        # This tests the edge case where tool_use is returned but no tool_manager
        with pytest.raises(AttributeError):
            self.generator.generate_response(
                query="Query",
                tools=[{"name": "search"}],
                tool_manager=None
            )

    def test_system_prompt_included(self):
        """Test that system prompt is included in API call"""
        # Arrange
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response")]
        self.mock_client.messages.create.return_value = mock_response

        # Act
        self.generator.generate_response(query="Test")

        # Assert
        call_args = self.mock_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "AI assistant specialized in course materials" in system_content
        assert "search tool" in system_content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
