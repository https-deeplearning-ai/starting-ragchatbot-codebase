"""Tests for AIGenerator and tool use handling"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


class TestAIGenerator:
    """Tests for AIGenerator.generate_response()"""

    def test_generate_response_without_tools(self, mock_anthropic_client):
        """Test generate_response without tools (direct answer)"""
        # Mock the anthropic module
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            response = generator.generate_response("What is Python?")

            # Verify response
            assert response == "This is a direct answer"
            mock_anthropic_client.messages.create.assert_called_once()

    def test_generate_response_with_conversation_history(self, mock_anthropic_client):
        """Test that conversation history is included in system prompt"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            response = generator.generate_response(
                "What is a variable?",
                conversation_history="Previous: What is Python?\nAssistant: Python is..."
            )

            # Verify the call
            call_args = mock_anthropic_client.messages.create.call_args
            system_content = call_args.kwargs["system"]
            assert "Previous: What is Python?" in system_content

    def test_generate_response_with_tools_available(self, mock_anthropic_client):
        """Test that tools are included when provided"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [
                {"name": "search_course_content", "description": "Search for content"}
            ]

            response = generator.generate_response("Python basics", tools=tools)

            # Verify tools were passed to API
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["tools"] == tools
            assert call_args.kwargs["tool_choice"] == {"type": "auto"}

    def test_generate_response_handles_tool_use(self, mock_anthropic_client_with_tool_use):
        """Test that generate_response properly handles tool use"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Tool result: Found content")

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_with_tool_use):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            response = generator.generate_response(
                "Find Python content",
                tools=tools,
                tool_manager=mock_tool_manager
            )

            # Verify tool was executed
            mock_tool_manager.execute_tool.assert_called_once_with(
                "search_course_content",
                query="python basics"
            )

            # Verify final response
            assert "answer with search results" in response.lower()

    def test_generate_response_tool_execution_sends_results_back(self, mock_anthropic_client_with_tool_use):
        """Test that tool results are sent back to Claude"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Search results: content about topic")

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_with_tool_use):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            response = generator.generate_response(
                "Tell me about topic",
                tools=tools,
                tool_manager=mock_tool_manager
            )

            # Verify that second API call was made
            assert mock_anthropic_client_with_tool_use.messages.create.call_count == 2

            # Check second call includes tool results
            second_call = mock_anthropic_client_with_tool_use.messages.create.call_args_list[1]
            messages = second_call.kwargs["messages"]

            # Last message should contain tool results
            assert messages[-1]["role"] == "user"
            assert isinstance(messages[-1]["content"], list)
            assert messages[-1]["content"][0]["type"] == "tool_result"

    def test_generate_response_with_empty_conversation_history(self, mock_anthropic_client):
        """Test that None conversation history doesn't cause issues"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            response = generator.generate_response("Question?", conversation_history=None)

            call_args = mock_anthropic_client.messages.create.call_args
            system_content = call_args.kwargs["system"]
            # Should only have the system prompt, not history
            assert "Previous conversation:" not in system_content

    def test_generate_response_respects_max_tokens(self, mock_anthropic_client):
        """Test that max_tokens parameter is set correctly"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            response = generator.generate_response("Test")

            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["max_tokens"] == 800

    def test_generate_response_sets_temperature_zero(self, mock_anthropic_client):
        """Test that temperature is set to 0 for deterministic responses"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            response = generator.generate_response("Test")

            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["temperature"] == 0

    def test_system_prompt_includes_search_guidance(self):
        """Test that SYSTEM_PROMPT includes guidance for tool usage"""
        assert "search_course_content" in AIGenerator.SYSTEM_PROMPT
        assert "get_course_outline" in AIGenerator.SYSTEM_PROMPT
        assert "One search per query maximum" in AIGenerator.SYSTEM_PROMPT

    def test_generate_response_preserves_message_order(self, mock_anthropic_client_with_tool_use):
        """Test that multi-turn conversation maintains correct message order"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Tool result")

        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client_with_tool_use):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            response = generator.generate_response(
                "Query text",
                tools=tools,
                tool_manager=mock_tool_manager
            )

            # Check second call messages
            second_call = mock_anthropic_client_with_tool_use.messages.create.call_args_list[1]
            messages = second_call.kwargs["messages"]

            # Verify message structure: [user message, assistant tool use, user tool results]
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"
            assert messages[2]["role"] == "user"
            assert isinstance(messages[2]["content"], list)
