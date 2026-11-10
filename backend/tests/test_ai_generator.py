"""2. Does AIGenerator call the search tool correctly?"""
from unittest.mock import MagicMock

import pytest
from conftest import response, text_block, thinking_block, tool_use_block

from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager

SEARCH_DEF = CourseSearchTool(MagicMock()).get_tool_definition()


@pytest.fixture
def generator():
    gen = AIGenerator(api_key="test-key", model="test-model")
    gen.client = MagicMock()
    return gen


def test_tools_are_offered_with_auto_choice(generator):
    generator.client.messages.create.return_value = response(text_block("Hi"))

    generator.generate_response("hello", tools=[SEARCH_DEF], tool_manager=MagicMock())

    kwargs = generator.client.messages.create.call_args.kwargs
    assert kwargs["tools"] == [SEARCH_DEF]
    assert kwargs["tool_choice"] == {"type": "auto"}
    assert "temperature" not in kwargs  # current models reject it


def test_direct_answer_makes_one_call_and_runs_no_tool(generator):
    generator.client.messages.create.return_value = response(
        thinking_block(), text_block("Paris")
    )
    tm = MagicMock()

    out = generator.generate_response("capital of France?", tools=[SEARCH_DEF], tool_manager=tm)

    assert out == "Paris"  # thinking block skipped
    assert generator.client.messages.create.call_count == 1
    tm.execute_tool.assert_not_called()


def test_tool_use_executes_search_with_claudes_arguments(generator):
    tool_input = {"query": "MCP architecture", "course_name": "MCP", "lesson_number": 2}
    generator.client.messages.create.side_effect = [
        response(thinking_block(), tool_use_block("search_course_content", tool_input),
                 stop_reason="tool_use"),
        response(text_block("Client-host-server.")),
    ]
    tm = MagicMock()
    tm.execute_tool.return_value = "[MCP - Lesson 2]\nchunk"

    out = generator.generate_response("q", tools=[SEARCH_DEF], tool_manager=tm)

    tm.execute_tool.assert_called_once_with(
        "search_course_content", query="MCP architecture", course_name="MCP", lesson_number=2
    )
    assert out == "Client-host-server."


def test_second_call_carries_tool_result_and_no_tools(generator):
    first = response(tool_use_block("search_course_content", {"query": "x"}, "toolu_42"),
                     stop_reason="tool_use")
    generator.client.messages.create.side_effect = [first, response(text_block("done"))]
    tm = MagicMock()
    tm.execute_tool.return_value = "RESULT"

    generator.generate_response("q", conversation_history="User: hi",
                                tools=[SEARCH_DEF], tool_manager=tm)

    second = generator.client.messages.create.call_args_list[1].kwargs
    assert "tools" not in second
    assert "User: hi" in second["system"]
    msgs = second["messages"]
    assert msgs[1] == {"role": "assistant", "content": first.content}
    assert msgs[2] == {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "toolu_42", "content": "RESULT"}
    ]}


def test_with_real_tool_manager_routes_to_search_tool(generator, mock_store):
    from conftest import MCP, make_results
    mock_store.search.return_value = make_results([("MCP is a protocol.", MCP, 1, 0)])
    tm = ToolManager()
    tm.register_tool(CourseSearchTool(mock_store))
    generator.client.messages.create.side_effect = [
        response(tool_use_block("search_course_content", {"query": "what is MCP"}),
                 stop_reason="tool_use"),
        response(text_block("A protocol.")),
    ]

    assert generator.generate_response("q", tools=tm.get_tool_definitions(),
                                       tool_manager=tm) == "A protocol."
    result = generator.client.messages.create.call_args_list[1].kwargs["messages"][2]["content"][0]
    assert "MCP is a protocol." in result["content"]


def test_tool_exception_is_reported_to_claude_not_raised(generator):
    """A failing tool should come back as an error tool_result, not crash the request (HTTP 500)."""
    generator.client.messages.create.side_effect = [
        response(tool_use_block("search_course_content", {"query": "x"}), stop_reason="tool_use"),
        response(text_block("Sorry, search failed.")),
    ]
    tm = MagicMock()
    tm.execute_tool.side_effect = RuntimeError("boom")

    out = generator.generate_response("q", tools=[SEARCH_DEF], tool_manager=tm)

    assert out == "Sorry, search failed."
    result = generator.client.messages.create.call_args_list[1].kwargs["messages"][2]["content"][0]
    assert result["is_error"] is True
