"""Tests that AIGenerator correctly invokes tools via tool_manager."""

from unittest.mock import MagicMock, call, patch

import pytest

from ai_generator import AIGenerator
from tests.conftest import (
    make_api_response,
    make_text_block,
    make_tool_use_block,
)

OUTLINE_TOOL_DEF = {
    "name": "get_course_outline",
    "description": "Get course outline",
    "input_schema": {
        "type": "object",
        "properties": {
            "course_name": {"type": "string"},
        },
        "required": ["course_name"],
    },
}


@pytest.fixture
def ai_generator():
    with patch("ai_generator.anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        gen = AIGenerator(
            api_key="test-key",
            model="claude-test",
            base_url="https://api.example.com",
        )
        gen.client = mock_client
        yield gen


class TestAIGeneratorToolCalling:
    def test_tool_use_calls_search_course_content(
        self, ai_generator, search_course_content_tool_def
    ):
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = (
            "[Course - Lesson 1]\nRetrieved content about RAG."
        )

        initial = make_api_response(
            [
                make_tool_use_block(
                    name="search_course_content",
                    tool_input={"query": "What is RAG?", "course_name": "Chroma"},
                )
            ],
            stop_reason="tool_use",
        )
        final = make_api_response(
            [make_text_block("RAG retrieves relevant docs then generates an answer.")]
        )
        ai_generator.client.messages.create.side_effect = [initial, final]

        result = ai_generator.generate_response(
            query="What is RAG?",
            tools=[search_course_content_tool_def],
            tool_manager=tool_manager,
        )

        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="What is RAG?",
            course_name="Chroma",
        )
        assert "RAG retrieves" in result
        assert ai_generator.client.messages.create.call_count == 2

    def test_second_api_call_preserves_tool_results_and_keeps_tools_available(
        self, ai_generator, search_course_content_tool_def
    ):
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "tool output"

        tool_block = make_tool_use_block(
            tool_id="toolu_abc",
            tool_input={"query": "embeddings"},
        )
        initial = make_api_response([tool_block], stop_reason="tool_use")
        final = make_api_response([make_text_block("Final answer")])
        ai_generator.client.messages.create.side_effect = [initial, final]

        ai_generator.generate_response(
            query="Explain embeddings",
            tools=[search_course_content_tool_def],
            tool_manager=tool_manager,
        )

        assert ai_generator.client.messages.create.call_count == 2
        first_kwargs = ai_generator.client.messages.create.call_args_list[0].kwargs
        second_kwargs = ai_generator.client.messages.create.call_args_list[1].kwargs

        assert "tools" in first_kwargs
        assert first_kwargs["tools"][0]["name"] == "search_course_content"
        # Natural end-turn path: second call still includes tools
        assert "tools" in second_kwargs
        assert second_kwargs["tool_choice"] == {"type": "auto"}

        messages = second_kwargs["messages"]
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"
        tool_results = messages[2]["content"]
        assert tool_results[0]["type"] == "tool_result"
        assert tool_results[0]["tool_use_id"] == "toolu_abc"
        assert tool_results[0]["content"] == "tool output"

    def test_no_tool_use_skips_execute_tool(
        self, ai_generator, search_course_content_tool_def
    ):
        tool_manager = MagicMock()
        response = make_api_response(
            [make_text_block("Python is a programming language.")],
            stop_reason="end_turn",
        )
        ai_generator.client.messages.create.return_value = response

        result = ai_generator.generate_response(
            query="What is Python?",
            tools=[search_course_content_tool_def],
            tool_manager=tool_manager,
        )

        tool_manager.execute_tool.assert_not_called()
        assert result == "Python is a programming language."
        assert ai_generator.client.messages.create.call_count == 1

    def test_passes_tools_to_initial_api_call(
        self, ai_generator, search_course_content_tool_def
    ):
        response = make_api_response([make_text_block("ok")])
        ai_generator.client.messages.create.return_value = response

        ai_generator.generate_response(
            query="content question",
            tools=[search_course_content_tool_def],
            tool_manager=MagicMock(),
        )

        kwargs = ai_generator.client.messages.create.call_args.kwargs
        assert kwargs["tools"] == [search_course_content_tool_def]
        assert kwargs["tool_choice"] == {"type": "auto"}

    def test_tool_use_with_lesson_number_forwarded(
        self, ai_generator, search_course_content_tool_def
    ):
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "lesson content"

        initial = make_api_response(
            [
                make_tool_use_block(
                    tool_input={
                        "query": "MCP servers",
                        "course_name": "MCP",
                        "lesson_number": 5,
                    },
                )
            ],
            stop_reason="tool_use",
        )
        final = make_api_response([make_text_block("Answer about MCP")])
        ai_generator.client.messages.create.side_effect = [initial, final]

        ai_generator.generate_response(
            query="MCP lesson 5",
            tools=[search_course_content_tool_def],
            tool_manager=tool_manager,
        )

        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="MCP servers",
            course_name="MCP",
            lesson_number=5,
        )


class TestAIGeneratorSequentialToolRounds:
    def test_two_tool_rounds_executes_outline_then_search(
        self, ai_generator, search_course_content_tool_def
    ):
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = [
            "Course X outline\nLesson 4: Embeddings",
            "[Course Y]\nContent about embeddings",
        ]

        round1 = make_api_response(
            [
                make_tool_use_block(
                    name="get_course_outline",
                    tool_id="toolu_1",
                    tool_input={"course_name": "Course X"},
                )
            ],
            stop_reason="tool_use",
        )
        round2 = make_api_response(
            [
                make_tool_use_block(
                    name="search_course_content",
                    tool_id="toolu_2",
                    tool_input={"query": "Embeddings"},
                )
            ],
            stop_reason="tool_use",
        )
        final = make_api_response(
            [make_text_block("Course Y also discusses embeddings.")]
        )
        ai_generator.client.messages.create.side_effect = [round1, round2, final]

        tools = [OUTLINE_TOOL_DEF, search_course_content_tool_def]
        result = ai_generator.generate_response(
            query="Find a course on the same topic as lesson 4 of Course X",
            tools=tools,
            tool_manager=tool_manager,
        )

        assert ai_generator.client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2
        tool_manager.execute_tool.assert_has_calls(
            [
                call("get_course_outline", course_name="Course X"),
                call("search_course_content", query="Embeddings"),
            ]
        )

        third_kwargs = ai_generator.client.messages.create.call_args_list[2].kwargs
        assert len(third_kwargs["messages"]) == 5
        assert "tools" in third_kwargs
        assert "Course Y also discusses embeddings" in result

    def test_max_tool_rounds_forces_final_call_without_tools(
        self, ai_generator, search_course_content_tool_def
    ):
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["result1", "result2"]

        r1 = make_api_response(
            [make_tool_use_block(tool_id="toolu_1", tool_input={"query": "a"})],
            stop_reason="tool_use",
        )
        r2 = make_api_response(
            [make_tool_use_block(tool_id="toolu_2", tool_input={"query": "b"})],
            stop_reason="tool_use",
        )
        r3 = make_api_response(
            [make_tool_use_block(tool_id="toolu_3", tool_input={"query": "c"})],
            stop_reason="tool_use",
        )
        r4 = make_api_response([make_text_block("Synthesized answer")])
        ai_generator.client.messages.create.side_effect = [r1, r2, r3, r4]

        result = ai_generator.generate_response(
            query="complex query",
            tools=[search_course_content_tool_def],
            tool_manager=tool_manager,
        )

        assert tool_manager.execute_tool.call_count == 2
        assert ai_generator.client.messages.create.call_count == 4

        # Third tool_use was not executed
        assert tool_manager.execute_tool.call_args_list[0] == call(
            "search_course_content", query="a"
        )
        assert tool_manager.execute_tool.call_args_list[1] == call(
            "search_course_content", query="b"
        )

        fourth_kwargs = ai_generator.client.messages.create.call_args_list[3].kwargs
        assert "tools" not in fourth_kwargs
        assert result == "Synthesized answer"

    def test_tool_execution_exception_returns_graceful_message(
        self, ai_generator, search_course_content_tool_def
    ):
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = RuntimeError("db down")

        initial = make_api_response(
            [make_tool_use_block()],
            stop_reason="tool_use",
        )
        ai_generator.client.messages.create.return_value = initial

        result = ai_generator.generate_response(
            query="What is RAG?",
            tools=[search_course_content_tool_def],
            tool_manager=tool_manager,
        )

        assert ai_generator.client.messages.create.call_count == 1
        assert result == AIGenerator.TOOL_ERROR_MESSAGE
        tool_manager.execute_tool.assert_called_once()

    def test_tool_soft_failure_result_passed_to_model_and_continues(
        self, ai_generator, search_course_content_tool_def
    ):
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = (
            "No relevant content found in course materials."
        )

        initial = make_api_response(
            [make_tool_use_block(tool_id="toolu_soft")],
            stop_reason="tool_use",
        )
        final = make_api_response(
            [make_text_block("No matching course content was found.")]
        )
        ai_generator.client.messages.create.side_effect = [initial, final]

        result = ai_generator.generate_response(
            query="obscure topic",
            tools=[search_course_content_tool_def],
            tool_manager=tool_manager,
        )

        assert ai_generator.client.messages.create.call_count == 2
        second_kwargs = ai_generator.client.messages.create.call_args_list[1].kwargs
        tool_results = second_kwargs["messages"][2]["content"]
        assert tool_results[0]["content"] == (
            "No relevant content found in course materials."
        )
        assert "No matching course content" in result
