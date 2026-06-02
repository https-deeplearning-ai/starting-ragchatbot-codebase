"""Tests for AIGenerator and tool use handling"""

import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


class TestAIGenerator:
    """Tests for AIGenerator.generate_response()"""

    def test_generate_response_without_tools(self, mock_anthropic_client):
        """Test generate_response without tools (direct answer)"""
        # Mock the anthropic module
        with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            response = generator.generate_response("What is Python?")

            # Verify response
            assert response == "This is a direct answer"
            mock_anthropic_client.messages.create.assert_called_once()

    def test_generate_response_with_conversation_history(self, mock_anthropic_client):
        """Test that conversation history is included in system prompt"""
        with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            _ = generator.generate_response(
                "What is a variable?",
                conversation_history="Previous: What is Python?\nAssistant: Python is...",
            )

            # Verify the call
            call_args = mock_anthropic_client.messages.create.call_args
            system_content = call_args.kwargs["system"]
            assert "Previous: What is Python?" in system_content

    def test_generate_response_with_tools_available(self, mock_anthropic_client):
        """Test that tools are included when provided"""
        with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content", "description": "Search for content"}]

            _ = generator.generate_response("Python basics", tools=tools)

            # Verify tools were passed to API
            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["tools"] == tools
            assert call_args.kwargs["tool_choice"] == {"type": "auto"}

    def test_generate_response_handles_tool_use(self, mock_anthropic_client_with_tool_use):
        """Test that generate_response properly handles tool use"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Tool result: Found content")

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_with_tool_use
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            response = generator.generate_response(
                "Find Python content", tools=tools, tool_manager=mock_tool_manager
            )

            # Verify tool was executed
            mock_tool_manager.execute_tool.assert_called_once_with(
                "search_course_content", query="python basics"
            )

            # Verify final response
            assert "answer with search results" in response.lower()

    def test_generate_response_tool_execution_sends_results_back(
        self, mock_anthropic_client_with_tool_use
    ):
        """Test that tool results are sent back to Claude"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Search results: content about topic")

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_with_tool_use
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            _ = generator.generate_response(
                "Tell me about topic", tools=tools, tool_manager=mock_tool_manager
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
        with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            _ = generator.generate_response("Question?", conversation_history=None)

            call_args = mock_anthropic_client.messages.create.call_args
            system_content = call_args.kwargs["system"]
            # Should only have the system prompt, not history
            assert "Previous conversation:" not in system_content

    def test_generate_response_respects_max_tokens(self, mock_anthropic_client):
        """Test that max_tokens parameter is set correctly"""
        with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            _ = generator.generate_response("Test")

            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["max_tokens"] == 800

    def test_generate_response_sets_temperature_zero(self, mock_anthropic_client):
        """Test that temperature is set to 0 for deterministic responses"""
        with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            _ = generator.generate_response("Test")

            call_args = mock_anthropic_client.messages.create.call_args
            assert call_args.kwargs["temperature"] == 0

    def test_system_prompt_includes_search_guidance(self):
        """Test that SYSTEM_PROMPT includes guidance for tool usage"""
        assert "search_course_content" in AIGenerator.SYSTEM_PROMPT
        assert "get_course_outline" in AIGenerator.SYSTEM_PROMPT
        assert "Up to 2 sequential searches per query" in AIGenerator.SYSTEM_PROMPT

    def test_generate_response_preserves_message_order(self, mock_anthropic_client_with_tool_use):
        """Test that multi-turn conversation maintains correct message order"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Tool result")

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_with_tool_use
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            _ = generator.generate_response(
                "Query text", tools=tools, tool_manager=mock_tool_manager
            )

            # Check second call messages
            second_call = mock_anthropic_client_with_tool_use.messages.create.call_args_list[1]
            messages = second_call.kwargs["messages"]

            # Verify message structure: [user message, assistant tool use, user tool results]
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"
            assert messages[2]["role"] == "user"
            assert isinstance(messages[2]["content"], list)

    def test_two_round_tool_flow(self, mock_anthropic_client_two_tool_rounds):
        """Test that two sequential tool-use rounds execute correctly"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(side_effect=["Result 1", "Result 2"])

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_two_tool_rounds
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}, {"name": "get_course_outline"}]

            response = generator.generate_response(
                "Find a course with same topic as lesson 4",
                tools=tools,
                tool_manager=mock_tool_manager,
            )

            # Verify 3 API calls made (initial + 2 tool rounds)
            assert mock_anthropic_client_two_tool_rounds.messages.create.call_count == 3
            # Verify 2 tool executions
            assert mock_tool_manager.execute_tool.call_count == 2
            # Verify final response
            assert response == "Final answer using both results"

    def test_two_round_tool_names_called(self, mock_anthropic_client_two_tool_rounds):
        """Test that correct tools are called in correct order for two rounds"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(side_effect=["Outline data", "Search results"])

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_two_tool_rounds
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "get_course_outline"}, {"name": "search_course_content"}]

            generator.generate_response(
                "Complex query", tools=tools, tool_manager=mock_tool_manager
            )

            # Get all execute_tool calls
            calls = mock_tool_manager.execute_tool.call_args_list
            # First call should be search_course_content
            assert calls[0][0][0] == "search_course_content"
            # Second call should be get_course_outline
            assert calls[1][0][0] == "get_course_outline"

    def test_round_cap_enforced(self, mock_anthropic_client_round_cap):
        """Test that round cap (2 rounds max) is enforced with final no-tools call"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(side_effect=["Result 1", "Result 2"])

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_round_cap
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            response = generator.generate_response(
                "Query that needs multiple searches", tools=tools, tool_manager=mock_tool_manager
            )

            # Verify 3 API calls (2 tool rounds + 1 final no-tools)
            assert mock_anthropic_client_round_cap.messages.create.call_count == 3
            # Verify 2 tool executions
            assert mock_tool_manager.execute_tool.call_count == 2
            # Final response from the enforced no-tools call
            assert response == "Answer after round cap enforced"

    def test_single_round_unchanged(self, mock_anthropic_client_with_tool_use):
        """Test that single-round flow still works (backwards compatibility)"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(return_value="Search result")

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_with_tool_use
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            response = generator.generate_response(
                "Simple query", tools=tools, tool_manager=mock_tool_manager
            )

            # Should only make 2 calls (initial + 1 tool execution)
            assert mock_anthropic_client_with_tool_use.messages.create.call_count == 2
            # Only 1 tool execution
            assert mock_tool_manager.execute_tool.call_count == 1
            # Response from second call
            assert response == "Here's the answer with search results"

    def test_tool_error_terminates_loop(self, mock_anthropic_client_with_tool_use):
        """Test that tool execution errors are caught and included in results"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(side_effect=Exception("Tool failed"))

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_with_tool_use
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            response = generator.generate_response(
                "Query", tools=tools, tool_manager=mock_tool_manager
            )

            # Should still make 2 calls (error is caught and sent as tool result)
            assert mock_anthropic_client_with_tool_use.messages.create.call_count == 2
            # Tool manager was called once
            assert mock_tool_manager.execute_tool.call_count == 1
            # Response is returned (not an exception)
            assert isinstance(response, str)

    def test_tools_passed_in_each_round(self, mock_anthropic_client_two_tool_rounds):
        """Test that tools are included in API calls for all rounds, not just the first"""
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool = Mock(side_effect=["Result 1", "Result 2"])

        with patch(
            "ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client_two_tool_rounds
        ):
            generator = AIGenerator("test-key", "claude-haiku-4-5")
            tools = [{"name": "search_course_content"}]

            generator.generate_response(
                "Multi-round query", tools=tools, tool_manager=mock_tool_manager
            )

            # Check that tools are present in all tool-using calls
            calls = mock_anthropic_client_two_tool_rounds.messages.create.call_args_list
            # First call should have tools
            assert "tools" in calls[0].kwargs
            assert calls[0].kwargs["tools"] == tools
            # Second call should also have tools (key change from old implementation)
            assert "tools" in calls[1].kwargs
            assert calls[1].kwargs["tools"] == tools
