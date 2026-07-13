"""Tests that AIGenerator correctly invokes CourseSearchTool via tool_manager."""

from unittest.mock import MagicMock, patch

import pytest

from ai_generator import AIGenerator
from tests.conftest import (
    make_api_response,
    make_text_block,
    make_tool_use_block,
)


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
            [make_tool_use_block(
                name="search_course_content",
                tool_input={"query": "What is RAG?", "course_name": "Chroma"},
            )],
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

    def test_second_api_call_includes_tool_results_without_tools(
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
        assert "tools" not in second_kwargs

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
            [make_tool_use_block(
                tool_input={
                    "query": "MCP servers",
                    "course_name": "MCP",
                    "lesson_number": 5,
                },
            )],
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
