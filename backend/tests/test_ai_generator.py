"""Tests for AIGenerator tool calling in ai_generator.py"""
import pytest
from unittest.mock import Mock, MagicMock, call
from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool
from vector_store import SearchResults


class MockTextBlock:
    """Mock text block from Anthropic response"""
    def __init__(self, text):
        self.type = "text"
        self.text = text


class MockToolUseBlock:
    """Mock tool use block from Anthropic response"""
    def __init__(self, id, name, input_params):
        self.type = "tool_use"
        self.id = id
        self.name = name
        self.input = input_params


class MockResponse:
    """Mock Anthropic API response"""
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


class TestAIGeneratorDirectResponse:
    """Test AIGenerator without tool use"""

    def test_generate_response_no_tools(self, ai_generator, mock_anthropic_client):
        """Test direct response without tool calling"""
        # Setup
        mock_response = MockResponse(
            content=[MockTextBlock("This is a direct answer.")],
            stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create.return_value = mock_response

        # Execute
        result = ai_generator.generate_response(
            query="What is Python?"
        )

        # Verify
        assert result == "This is a direct answer."
        mock_anthropic_client.messages.create.assert_called_once()

    def test_generate_response_with_conversation_history(self, ai_generator, mock_anthropic_client):
        """Test that conversation history is included in system prompt"""
        # Setup
        mock_response = MockResponse(
            content=[MockTextBlock("Follow-up answer.")],
            stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create.return_value = mock_response
        history = "User: Hello\nAssistant: Hi there!"

        # Execute
        result = ai_generator.generate_response(
            query="Tell me more",
            conversation_history=history
        )

        # Verify
        call_args = mock_anthropic_client.messages.create.call_args
        assert "Previous conversation" in call_args.kwargs["system"]
        assert history in call_args.kwargs["system"]


class TestAIGeneratorToolCalling:
    """Test AIGenerator with tool use"""

    def test_tool_definitions_passed_to_api(self, ai_generator, mock_anthropic_client):
        """Test that tool definitions are passed to Anthropic API"""
        # Setup
        mock_response = MockResponse(
            content=[MockTextBlock("Answer without tools.")],
            stop_reason="end_turn"
        )
        mock_anthropic_client.messages.create.return_value = mock_response

        tool_definitions = [{
            "name": "test_tool",
            "description": "A test tool",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }]

        # Execute
        ai_generator.generate_response(
            query="Test query",
            tools=tool_definitions
        )

        # Verify
        call_args = mock_anthropic_client.messages.create.call_args
        assert "tools" in call_args.kwargs
        assert call_args.kwargs["tools"] == tool_definitions
        assert "tool_choice" in call_args.kwargs
        assert call_args.kwargs["tool_choice"]["type"] == "auto"

    def test_tool_use_triggers_execution(self, ai_generator, mock_anthropic_client):
        """Test that tool_use stop_reason triggers tool execution"""
        # Setup - First response with tool use
        tool_use_response = MockResponse(
            content=[
                MockTextBlock("I'll search for that."),
                MockToolUseBlock(
                    id="tool_1",
                    name="search_course_content",
                    input_params={"query": "Python basics"}
                )
            ],
            stop_reason="tool_use"
        )

        # Second response after tool execution
        final_response = MockResponse(
            content=[MockTextBlock("Based on the search results, Python is...")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [tool_use_response, final_response]

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Python is a programming language."

        tool_definitions = [{
            "name": "search_course_content",
            "description": "Search courses",
            "input_schema": {"type": "object", "properties": {}, "required": []}
        }]

        # Execute
        result = ai_generator.generate_response(
            query="What is Python?",
            tools=tool_definitions,
            tool_manager=mock_tool_manager
        )

        # Verify
        assert result == "Based on the search results, Python is..."
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="Python basics"
        )
        # Should have called API twice: once for initial, once for follow-up
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_tool_result_formatting(self, ai_generator, mock_anthropic_client):
        """Test that tool results are properly formatted for Claude"""
        # Setup
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock(
                    id="tool_123",
                    name="search_course_content",
                    input_params={"query": "test"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content=[MockTextBlock("Final answer")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [tool_use_response, final_response]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result content"

        # Execute
        result = ai_generator.generate_response(
            query="Test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify the second API call includes tool results
        second_call_args = mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call_args.kwargs["messages"]

        # Should have 3 messages: user, assistant (with tool use), user (with tool results)
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # Tool result message should have correct format
        tool_result_content = messages[2]["content"]
        assert isinstance(tool_result_content, list)
        assert tool_result_content[0]["type"] == "tool_result"
        assert tool_result_content[0]["tool_use_id"] == "tool_123"
        assert tool_result_content[0]["content"] == "Tool result content"

    def test_multiple_tool_calls(self, ai_generator, mock_anthropic_client):
        """Test handling multiple tool calls in one response"""
        # Setup
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock("tool_1", "search_course_content", {"query": "Python"}),
                MockToolUseBlock("tool_2", "search_course_content", {"query": "Java"})
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content=[MockTextBlock("Compared both languages")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [tool_use_response, final_response]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Python result",
            "Java result"
        ]

        # Execute
        result = ai_generator.generate_response(
            query="Compare Python and Java",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2

    def test_tool_execution_error_handling(self, ai_generator, mock_anthropic_client):
        """Test that tool execution errors don't crash the system"""
        # Setup
        tool_use_response = MockResponse(
            content=[
                MockToolUseBlock("tool_1", "search_course_content", {"query": "test"})
            ],
            stop_reason="tool_use"
        )

        final_response = MockResponse(
            content=[MockTextBlock("Error handled gracefully")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [tool_use_response, final_response]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search error: Database connection failed"

        # Execute
        result = ai_generator.generate_response(
            query="Test",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify error is passed back to AI
        assert result == "Error handled gracefully"

    def test_no_tool_manager_with_tool_use(self, ai_generator, mock_anthropic_client):
        """Test that tool_use without tool_manager returns direct response"""
        # Setup
        tool_use_response = MockResponse(
            content=[
                MockTextBlock("I would search for that."),
                MockToolUseBlock("tool_1", "search_course_content", {"query": "test"})
            ],
            stop_reason="tool_use"
        )

        mock_anthropic_client.messages.create.return_value = tool_use_response

        # Execute (no tool_manager provided)
        result = ai_generator.generate_response(
            query="Test",
            tools=[{"name": "search_course_content"}]
        )

        # Verify returns text from first content block
        assert result == "I would search for that."


class TestAIGeneratorConfiguration:
    """Test AIGenerator configuration"""

    def test_base_params_configured(self, ai_generator):
        """Test that base parameters are properly configured"""
        assert ai_generator.base_params["model"] == "claude-sonnet-4-20250514"
        assert ai_generator.base_params["temperature"] == 0
        assert ai_generator.base_params["max_tokens"] == 800

    def test_system_prompt_exists(self, ai_generator):
        """Test that system prompt is defined"""
        assert hasattr(AIGenerator, "SYSTEM_PROMPT")
        assert len(AIGenerator.SYSTEM_PROMPT) > 0
        assert "tool" in AIGenerator.SYSTEM_PROMPT.lower()
