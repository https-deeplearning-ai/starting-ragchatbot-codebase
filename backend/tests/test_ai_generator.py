"""
Tests for AIGenerator class.

Tests Anthropic API integration and tool handling.
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ai_generator import AIGenerator, ToolExecutionError


# Helper functions for creating mock responses
def create_tool_use_response(tool_name: str, tool_input: dict, tool_id: str = "tool_123"):
    """Helper function to create mock tool use responses"""
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"

    mock_tool_use = Mock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.id = tool_id
    mock_tool_use.name = tool_name
    mock_tool_use.input = tool_input

    mock_response.content = [mock_tool_use]
    return mock_response


def create_text_response(text: str):
    """Helper function to create mock text responses"""
    mock_response = Mock()
    mock_response.stop_reason = "end_turn"

    mock_content = Mock()
    mock_content.type = "text"
    mock_content.text = text

    mock_response.content = [mock_content]
    return mock_response


class TestAIGeneratorInitialization:
    """Test AIGenerator initialization"""

    def test_init_sets_model(self):
        """Verify model is set correctly during initialization"""
        with patch('ai_generator.anthropic.Anthropic'):
            generator = AIGenerator("test-key", "claude-sonnet-4-20250514")

            assert generator.model == "claude-sonnet-4-20250514"

    def test_init_creates_client(self):
        """Verify Anthropic client is created"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            generator = AIGenerator("test-key", "test-model")

            mock_anthropic.assert_called_once_with(api_key="test-key")

    def test_base_params_configured(self):
        """Verify base parameters are set"""
        with patch('ai_generator.anthropic.Anthropic'):
            generator = AIGenerator("test-key", "test-model")

            assert generator.base_params["temperature"] == 0
            assert generator.base_params["max_tokens"] == 800


class TestGenerateResponse:
    """Test generate_response method"""

    @pytest.fixture
    def mock_generator(self, mock_anthropic_client):
        """AIGenerator with mocked Anthropic client"""
        with patch('ai_generator.anthropic.Anthropic', return_value=mock_anthropic_client):
            generator = AIGenerator("test-key", "test-model")
            return generator

    def test_generate_response_simple_query(self, mock_generator, mock_anthropic_text_response):
        """Test simple query without tools returns text"""
        mock_generator.client.messages.create.return_value = mock_anthropic_text_response

        result = mock_generator.generate_response("What is Python?")

        assert result == "Here is your answer about the course content."

    def test_generate_response_includes_system_prompt(self, mock_generator, mock_anthropic_text_response):
        """Verify system prompt is included in API call"""
        mock_generator.client.messages.create.return_value = mock_anthropic_text_response

        mock_generator.generate_response("test query")

        call_kwargs = mock_generator.client.messages.create.call_args[1]
        assert "system" in call_kwargs
        assert "AI assistant" in call_kwargs["system"]

    def test_generate_response_with_conversation_history(self, mock_generator, mock_anthropic_text_response):
        """Test conversation history is included in system prompt"""
        mock_generator.client.messages.create.return_value = mock_anthropic_text_response

        history = "User: Previous question\nAssistant: Previous answer"
        mock_generator.generate_response("follow up", conversation_history=history)

        call_kwargs = mock_generator.client.messages.create.call_args[1]
        assert "Previous question" in call_kwargs["system"]
        assert "Previous answer" in call_kwargs["system"]

    def test_generate_response_with_tools(self, mock_generator, mock_anthropic_text_response):
        """Test tools are passed to API when provided"""
        mock_generator.client.messages.create.return_value = mock_anthropic_text_response

        tools = [{"name": "test_tool", "description": "Test", "input_schema": {}}]
        mock_generator.generate_response("query", tools=tools)

        call_kwargs = mock_generator.client.messages.create.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tool_choice"] == {"type": "auto"}


class TestToolExecution:
    """Test tool execution flow in AIGenerator"""

    @pytest.fixture
    def generator_with_mocked_client(self):
        """AIGenerator with fully mocked client for tool tests"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator("test-key", "test-model")
            return generator, mock_client

    def test_tool_use_triggers_handle_tool_execution(
        self, generator_with_mocked_client,
        mock_anthropic_tool_use_response,
        mock_anthropic_final_response
    ):
        """Test that tool_use stop_reason triggers tool execution"""
        generator, mock_client = generator_with_mocked_client

        # First call returns tool use, second returns final response
        mock_client.messages.create.side_effect = [
            mock_anthropic_tool_use_response,
            mock_anthropic_final_response
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result: MCP information"

        result = generator.generate_response(
            "What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once()

    def test_tool_execution_passes_correct_arguments(
        self, generator_with_mocked_client,
        mock_anthropic_tool_use_response,
        mock_anthropic_final_response
    ):
        """Test correct arguments are passed to tool execution"""
        generator, mock_client = generator_with_mocked_client

        mock_client.messages.create.side_effect = [
            mock_anthropic_tool_use_response,
            mock_anthropic_final_response
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Result"

        generator.generate_response(
            "query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify tool was called with correct name and arguments
        call_args = mock_tool_manager.execute_tool.call_args
        assert call_args[0][0] == "search_course_content"  # Tool name
        assert "query" in call_args[1]  # Keyword args include query

    def test_tool_result_sent_back_to_claude(
        self, generator_with_mocked_client,
        mock_anthropic_tool_use_response,
        mock_anthropic_final_response
    ):
        """Test tool results are sent back to Claude for final response"""
        generator, mock_client = generator_with_mocked_client

        mock_client.messages.create.side_effect = [
            mock_anthropic_tool_use_response,
            mock_anthropic_final_response
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search found: MCP details"

        generator.generate_response(
            "query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Second API call should include tool result
        second_call = mock_client.messages.create.call_args_list[1]
        messages = second_call[1]["messages"]

        # Find tool result message
        tool_result_msg = None
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg.get("content"), list):
                for content in msg["content"]:
                    if content.get("type") == "tool_result":
                        tool_result_msg = content
                        break

        assert tool_result_msg is not None
        assert "Search found: MCP details" in tool_result_msg["content"]

    def test_final_response_returned_after_tool_execution(
        self, generator_with_mocked_client,
        mock_anthropic_tool_use_response,
        mock_anthropic_final_response
    ):
        """Test final response is returned after tool execution"""
        generator, mock_client = generator_with_mocked_client

        mock_client.messages.create.side_effect = [
            mock_anthropic_tool_use_response,
            mock_anthropic_final_response
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        result = generator.generate_response(
            "query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        assert result == "Based on the course materials, MCP is a protocol for AI integration."


class TestToolExecutionWithEmptyResults:
    """
    Tests specifically for the MAX_RESULTS=0 bug scenario.
    These tests verify behavior when tools return empty/no results.
    """

    @pytest.fixture
    def generator_with_empty_tool_results(self):
        """Generator configured for testing empty tool results"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator("test-key", "test-model")
            return generator, mock_client

    def test_empty_tool_result_propagates_to_final_response(
        self, generator_with_empty_tool_results
    ):
        """
        BUG SCENARIO TEST

        When MAX_RESULTS=0, tool returns "No relevant content found".
        This should be sent to Claude, which then generates a "query failed" response.
        """
        generator, mock_client = generator_with_empty_tool_results

        # Tool use response
        tool_use_response = Mock()
        tool_use_response.stop_reason = "tool_use"
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.id = "tool_123"
        tool_use.name = "search_course_content"
        tool_use.input = {"query": "What is MCP?"}
        tool_use_response.content = [tool_use]

        # Final response after empty tool result
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_content = Mock()
        final_content.type = "text"
        final_content.text = "I couldn't find relevant information about that topic."
        final_response.content = [final_content]

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        # Tool manager returns empty result (simulating MAX_RESULTS=0)
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "No relevant content found."

        result = generator.generate_response(
            "What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify empty result was sent to Claude
        second_call = mock_client.messages.create.call_args_list[1]
        messages = second_call[1]["messages"]

        tool_result_content = None
        for msg in messages:
            if msg["role"] == "user" and isinstance(msg.get("content"), list):
                for content in msg["content"]:
                    if content.get("type") == "tool_result":
                        tool_result_content = content["content"]
                        break

        assert tool_result_content == "No relevant content found."


class TestErrorHandling:
    """Test error handling in AIGenerator"""

    def test_api_error_propagates(self):
        """Test that API errors are not silently swallowed"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("API Error")
            mock_anthropic_class.return_value = mock_client

            generator = AIGenerator("test-key", "test-model")

            with pytest.raises(Exception, match="API Error"):
                generator.generate_response("test query")


class TestSequentialToolCalling:
    """Tests for sequential tool calling (up to 2 rounds)"""

    @pytest.fixture
    def generator_for_sequential_tests(self):
        """Generator with mocked client for sequential tests"""
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            generator = AIGenerator("test-key", "test-model")
            return generator, mock_client

    def test_no_tool_call_direct_response(self, generator_for_sequential_tests):
        """Test direct text response without tool calls makes 1 API call"""
        generator, mock_client = generator_for_sequential_tests

        mock_client.messages.create.return_value = create_text_response("Direct answer")

        result = generator.generate_response(
            "What is Python?",
            tools=[{"name": "search_course_content"}],
            tool_manager=Mock()
        )

        assert mock_client.messages.create.call_count == 1
        assert result == "Direct answer"

    def test_single_tool_call_then_text(self, generator_for_sequential_tests):
        """Test single tool call followed by text response makes 2 API calls"""
        generator, mock_client = generator_for_sequential_tests

        mock_client.messages.create.side_effect = [
            create_tool_use_response("search_course_content", {"query": "MCP"}, "tool_1"),
            create_text_response("MCP is a protocol for AI integration.")
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search results about MCP"

        result = generator.generate_response(
            "What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        assert mock_client.messages.create.call_count == 2
        assert mock_tool_manager.execute_tool.call_count == 1
        assert "MCP is a protocol" in result

    def test_two_sequential_tool_calls(self, generator_for_sequential_tests):
        """Test Claude can make two sequential tool calls (3 API calls total)"""
        generator, mock_client = generator_for_sequential_tests

        mock_client.messages.create.side_effect = [
            create_tool_use_response("get_course_outline", {"course_name": "MCP"}, "tool_1"),
            create_tool_use_response("search_course_content", {"query": "tools"}, "tool_2"),
            create_text_response("Here is the combined information about MCP tools.")
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Course outline: Lesson 1, Lesson 2, Lesson 3",
            "Search results: MCP tools enable..."
        ]

        result = generator.generate_response(
            "Tell me about MCP tools",
            tools=[{"name": "search_course_content"}, {"name": "get_course_outline"}],
            tool_manager=mock_tool_manager
        )

        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2
        assert "combined information" in result

    def test_max_rounds_enforced(self, generator_for_sequential_tests):
        """Test that after 2 rounds, final call has no tools"""
        generator, mock_client = generator_for_sequential_tests

        mock_client.messages.create.side_effect = [
            create_tool_use_response("search_course_content", {"query": "A"}, "tool_1"),
            create_tool_use_response("search_course_content", {"query": "B"}, "tool_2"),
            create_text_response("Final answer after max rounds")
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["Result A", "Result B"]

        result = generator.generate_response(
            "query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Third call (index 2) should NOT have tools
        third_call_kwargs = mock_client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs
        assert result == "Final answer after max rounds"

    def test_tool_execution_error_terminates(self, generator_for_sequential_tests):
        """Test tool execution error terminates gracefully"""
        generator, mock_client = generator_for_sequential_tests

        mock_client.messages.create.return_value = create_tool_use_response(
            "search_course_content", {"query": "test"}, "tool_1"
        )

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Database connection failed")

        result = generator.generate_response(
            "query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        assert "Tool execution failed" in result
        assert mock_client.messages.create.call_count == 1

    def test_messages_preserved_between_rounds(self, generator_for_sequential_tests):
        """Test that tool results from round 1 are visible in round 2"""
        generator, mock_client = generator_for_sequential_tests

        mock_client.messages.create.side_effect = [
            create_tool_use_response("get_course_outline", {"course_name": "X"}, "tool_1"),
            create_tool_use_response("search_course_content", {"query": "Y"}, "tool_2"),
            create_text_response("Final answer")
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Outline: Lesson 1 - Intro, Lesson 2 - Advanced",
            "Content about Y topic"
        ]

        generator.generate_response(
            "original query",
            tools=[{"name": "search_course_content"}, {"name": "get_course_outline"}],
            tool_manager=mock_tool_manager
        )

        # Check second API call (index 1) includes first tool result
        second_call_messages = mock_client.messages.create.call_args_list[1][1]["messages"]

        # Should have: user query, assistant tool_use, user tool_result
        assert len(second_call_messages) == 3
        assert second_call_messages[0]["role"] == "user"
        assert second_call_messages[1]["role"] == "assistant"
        assert second_call_messages[2]["role"] == "user"

        # Verify tool result content
        tool_result_msg = second_call_messages[2]["content"]
        assert isinstance(tool_result_msg, list)
        assert tool_result_msg[0]["type"] == "tool_result"
        assert "Outline: Lesson 1" in tool_result_msg[0]["content"]

        # Check third API call includes BOTH tool results
        third_call_messages = mock_client.messages.create.call_args_list[2][1]["messages"]
        assert len(third_call_messages) == 5  # user, assistant, user, assistant, user

    def test_api_called_correct_number_of_times(self, generator_for_sequential_tests):
        """Verify exact API call counts for different scenarios"""
        generator, mock_client = generator_for_sequential_tests

        # Scenario: 2 tool calls then text
        mock_client.messages.create.side_effect = [
            create_tool_use_response("tool1", {}, "t1"),
            create_tool_use_response("tool2", {}, "t2"),
            create_text_response("done")
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "result"

        generator.generate_response("q", tools=[{"name": "tool1"}], tool_manager=mock_tool_manager)

        assert mock_client.messages.create.call_count == 3
