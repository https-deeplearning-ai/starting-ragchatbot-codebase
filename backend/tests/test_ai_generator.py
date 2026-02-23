"""Tests for AIGenerator tool calling and response handling."""

import pytest
import anthropic
from unittest.mock import MagicMock, patch, call
from helpers import make_anthropic_response
from ai_generator import AIGenerator


@pytest.fixture
def generator():
    with patch("ai_generator.anthropic.Anthropic"):
        gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
    return gen


@pytest.fixture
def tool_manager():
    tm = MagicMock()
    tm.execute_tool.return_value = "Tool result: content about topic"
    return tm


@pytest.fixture
def sample_tools():
    return [
        {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ]


class TestNoToolUsage:
    def test_direct_text_response(self, generator, sample_tools):
        """When Claude returns text (no tools), returns text directly."""
        response = make_anthropic_response(
            [{"type": "text", "text": "Hello, I can help!"}],
            stop_reason="end_turn",
        )
        generator.client.messages.create.return_value = response

        result = generator.generate_response(query="hi", tools=sample_tools)

        assert result == "Hello, I can help!"

    def test_empty_content_returns_fallback(self, generator, sample_tools):
        """When response.content is empty, returns a fallback message instead of crashing."""
        response = make_anthropic_response([], stop_reason="end_turn")
        response.content = []  # explicitly empty
        generator.client.messages.create.return_value = response

        result = generator.generate_response(query="test", tools=sample_tools)

        assert "able to generate a response" in result.lower()


class TestSingleToolRound:
    def test_tool_use_calls_tool_manager(self, generator, tool_manager, sample_tools):
        """When Claude returns tool_use, calls tool_manager.execute_tool()."""
        tool_response = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "search_course_content",
                    "input": {"query": "neural networks"},
                }
            ],
            stop_reason="tool_use",
        )
        text_response = make_anthropic_response(
            [{"type": "text", "text": "Neural networks are..."}],
            stop_reason="end_turn",
        )
        generator.client.messages.create.side_effect = [
            tool_response,
            text_response,
        ]

        generator.generate_response(
            query="what are neural networks",
            tools=sample_tools,
            tool_manager=tool_manager,
        )

        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="neural networks"
        )

    def test_tool_use_then_synthesis(self, generator, tool_manager, sample_tools):
        """Round 1: tool_use -> execute -> Round 2: Claude synthesizes answer."""
        tool_response = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "search_course_content",
                    "input": {"query": "transformers"},
                }
            ],
            stop_reason="tool_use",
        )
        synthesis_response = make_anthropic_response(
            [{"type": "text", "text": "Transformers use attention mechanisms."}],
            stop_reason="end_turn",
        )
        generator.client.messages.create.side_effect = [
            tool_response,
            synthesis_response,
        ]

        result = generator.generate_response(
            query="explain transformers",
            tools=sample_tools,
            tool_manager=tool_manager,
        )

        assert result == "Transformers use attention mechanisms."
        assert generator.client.messages.create.call_count == 2

    def test_course_outline_returns_directly(
        self, generator, tool_manager, sample_tools
    ):
        """get_course_outline tool result is returned directly without synthesis."""
        outline_result = "**Course Title:** MCP\n- Lesson 1: Intro"
        tool_manager.execute_tool.return_value = outline_result

        tool_response = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "get_course_outline",
                    "input": {"course_name": "MCP"},
                }
            ],
            stop_reason="tool_use",
        )
        generator.client.messages.create.return_value = tool_response

        result = generator.generate_response(
            query="outline of MCP",
            tools=sample_tools,
            tool_manager=tool_manager,
        )

        assert result == outline_result
        # Should NOT make a second API call for synthesis
        assert generator.client.messages.create.call_count == 1


class TestMultiRoundToolCalling:
    def test_two_rounds_of_tool_calls(self, generator, tool_manager, sample_tools):
        """Loop executes up to 2 tool rounds before final synthesis call."""
        tool_response_1 = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "search_course_content",
                    "input": {"query": "round 1"},
                }
            ],
            stop_reason="tool_use",
        )
        tool_response_2 = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t2",
                    "name": "search_course_content",
                    "input": {"query": "round 2"},
                }
            ],
            stop_reason="tool_use",
        )
        final_response = make_anthropic_response(
            [{"type": "text", "text": "Final answer after 2 rounds."}],
            stop_reason="end_turn",
        )
        generator.client.messages.create.side_effect = [
            tool_response_1,
            tool_response_2,
            final_response,
        ]

        result = generator.generate_response(
            query="complex question",
            tools=sample_tools,
            tool_manager=tool_manager,
        )

        assert result == "Final answer after 2 rounds."
        # 2 tool rounds + 1 final synthesis = 3 API calls
        assert generator.client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2

    def test_messages_accumulate_across_rounds(
        self, generator, tool_manager, sample_tools
    ):
        """2nd API call's messages kwarg contains tool results from round 1."""
        tool_manager.execute_tool.return_value = "Result from round 1"

        tool_response_1 = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "search_course_content",
                    "input": {"query": "round 1"},
                }
            ],
            stop_reason="tool_use",
        )
        text_response = make_anthropic_response(
            [{"type": "text", "text": "Synthesized answer."}],
            stop_reason="end_turn",
        )
        generator.client.messages.create.side_effect = [
            tool_response_1,
            text_response,
        ]

        generator.generate_response(
            query="test query",
            tools=sample_tools,
            tool_manager=tool_manager,
        )

        # The 2nd API call should have accumulated messages
        second_call_kwargs = generator.client.messages.create.call_args_list[1][1]
        msgs = second_call_kwargs["messages"]

        # Should be: user query, assistant tool_use, user tool_result
        assert len(msgs) == 3
        assert msgs[0] == {"role": "user", "content": "test query"}
        assert msgs[1]["role"] == "assistant"
        assert msgs[2]["role"] == "user"
        # The tool_result content should contain our result
        tool_result_content = msgs[2]["content"]
        assert len(tool_result_content) == 1
        assert tool_result_content[0]["type"] == "tool_result"
        assert tool_result_content[0]["content"] == "Result from round 1"

    def test_parallel_tool_calls_all_executed(
        self, generator, tool_manager, sample_tools
    ):
        """When Claude calls 2 tools in one response, both execute."""
        tool_manager.execute_tool.side_effect = ["Result A", "Result B"]

        parallel_response = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "search_course_content",
                    "input": {"query": "topic A"},
                },
                {
                    "type": "tool_use",
                    "id": "t2",
                    "name": "search_course_content",
                    "input": {"query": "topic B"},
                },
            ],
            stop_reason="tool_use",
        )
        synthesis_response = make_anthropic_response(
            [{"type": "text", "text": "Combined answer."}],
            stop_reason="end_turn",
        )
        generator.client.messages.create.side_effect = [
            parallel_response,
            synthesis_response,
        ]

        result = generator.generate_response(
            query="compare topics",
            tools=sample_tools,
            tool_manager=tool_manager,
        )

        assert result == "Combined answer."
        assert tool_manager.execute_tool.call_count == 2
        tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="topic A"
        )
        tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="topic B"
        )

        # Verify both results sent back to API
        second_call_msgs = generator.client.messages.create.call_args_list[1][1][
            "messages"
        ]
        tool_results_msg = second_call_msgs[-1]["content"]
        assert len(tool_results_msg) == 2
        assert tool_results_msg[0]["content"] == "Result A"
        assert tool_results_msg[1]["content"] == "Result B"

    def test_parallel_tools_one_fails_still_returns_all_results(
        self, generator, tool_manager, sample_tools
    ):
        """One tool fails -> error sent for that tool, successful result still included."""
        tool_manager.execute_tool.side_effect = [
            "Success result",
            RuntimeError("Tool B crashed"),
        ]

        parallel_response = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "search_course_content",
                    "input": {"query": "good query"},
                },
                {
                    "type": "tool_use",
                    "id": "t2",
                    "name": "search_course_content",
                    "input": {"query": "bad query"},
                },
            ],
            stop_reason="tool_use",
        )
        final_response = make_anthropic_response(
            [{"type": "text", "text": "Partial answer with error context."}],
            stop_reason="end_turn",
        )
        generator.client.messages.create.side_effect = [
            parallel_response,
            final_response,
        ]

        result = generator.generate_response(
            query="multi tool query",
            tools=sample_tools,
            tool_manager=tool_manager,
        )

        assert isinstance(result, str)
        # Both tools were attempted
        assert tool_manager.execute_tool.call_count == 2

        # Verify both results (success + error) sent back to API
        second_call_msgs = generator.client.messages.create.call_args_list[1][1][
            "messages"
        ]
        tool_results_msg = second_call_msgs[-1]["content"]
        assert len(tool_results_msg) == 2
        # First tool succeeded
        assert tool_results_msg[0]["content"] == "Success result"
        assert "is_error" not in tool_results_msg[0]
        # Second tool has error
        assert "Error" in tool_results_msg[1]["content"]
        assert tool_results_msg[1]["is_error"] is True


class TestErrorHandling:
    def test_tool_execution_exception_handled(
        self, generator, tool_manager, sample_tools
    ):
        """When tool_manager raises, error is caught and loop breaks."""
        tool_manager.execute_tool.side_effect = RuntimeError("Tool crashed")

        tool_response = make_anthropic_response(
            [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "search_course_content",
                    "input": {"query": "test"},
                }
            ],
            stop_reason="tool_use",
        )
        # After exception, a final synthesis call is made (no tools)
        final_response = make_anthropic_response(
            [{"type": "text", "text": "I encountered an error."}],
            stop_reason="end_turn",
        )
        generator.client.messages.create.side_effect = [
            tool_response,
            final_response,
        ]

        result = generator.generate_response(
            query="test", tools=sample_tools, tool_manager=tool_manager
        )

        # The function should still return (error is handled in _handle_tool_execution)
        assert isinstance(result, str)

    def test_api_exception_wrapped_as_runtime_error(self, generator, sample_tools):
        """When client.messages.create() raises APIError, it's wrapped as RuntimeError with context."""
        generator.client.messages.create.side_effect = anthropic.APIError(
            message="rate limit exceeded",
            request=MagicMock(),
            body=None,
        )

        with pytest.raises(RuntimeError, match="Anthropic API error"):
            generator.generate_response(query="test", tools=sample_tools)

    def test_auth_exception_wrapped_with_context(self, generator, sample_tools):
        """When client.messages.create() raises AuthenticationError, it's wrapped with auth context."""
        generator.client.messages.create.side_effect = anthropic.AuthenticationError(
            message="invalid api key",
            response=MagicMock(status_code=401, headers={}),
            body=None,
        )

        with pytest.raises(RuntimeError, match="authentication failed"):
            generator.generate_response(query="test", tools=sample_tools)
