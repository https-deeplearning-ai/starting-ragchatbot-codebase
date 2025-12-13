"""Tests for AIGenerator tool calling integration"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_generator import AIGenerator
from tests.fixtures.sample_data import (
    SAMPLE_ANTHROPIC_TEXT_RESPONSE,
    SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE,
    SAMPLE_ANTHROPIC_FINAL_RESPONSE,
    MockTextBlock,
    MockToolUseBlock,
    MockAnthropicResponse
)


class TestAIGeneratorBasics:
    """Test basic AIGenerator functionality without tools"""

    def test_generate_response_without_tools(self, mock_anthropic_client):
        """Test that AIGenerator can generate responses without tool use"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        # Replace client with mock
        generator.client = mock_anthropic_client
        mock_anthropic_client.messages.create.return_value = SAMPLE_ANTHROPIC_TEXT_RESPONSE

        # Generate response without tools
        response = generator.generate_response(query="What is Python?")

        # Verify response is returned
        assert isinstance(response, str)
        assert "Model Context Protocol" in response

        # Verify API was called correctly
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args

        # Verify no tools were passed
        assert 'tools' not in call_args[1] or call_args[1].get('tools') is None

    def test_generate_response_with_conversation_history(self, mock_anthropic_client):
        """Test that conversation history is included in system prompt"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        mock_anthropic_client.messages.create.return_value = SAMPLE_ANTHROPIC_TEXT_RESPONSE

        # Generate with history
        history = "User: Hello\nAssistant: Hi there!"
        response = generator.generate_response(query="test", conversation_history=history)

        # Verify system prompt includes history
        call_args = mock_anthropic_client.messages.create.call_args
        system_content = call_args[1]['system']
        assert "Previous conversation:" in system_content
        assert history in system_content


class TestAIGeneratorToolCalling:
    """Test AIGenerator with tool use integration"""

    def test_generate_response_with_tool_use(self, mock_anthropic_client, mock_tool_manager):
        """
        CRITICAL TEST: Test that AIGenerator correctly calls tools

        This tests the complete tool calling flow:
        1. User query -> Claude decides to use tool
        2. Tool is executed by tool_manager
        3. Tool result sent back to Claude
        4. Claude synthesizes final response
        """
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool definitions
        tool_definitions = [{
            "name": "search_course_content",
            "description": "Search course content",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }]

        # Mock Claude's two responses:
        # 1. First response: tool_use
        # 2. Second response: final text after tool execution
        mock_anthropic_client.messages.create.side_effect = [
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE,  # First call: tool use
            SAMPLE_ANTHROPIC_FINAL_RESPONSE  # Second call: final response
        ]

        # Generate response with tools
        response = generator.generate_response(
            query="What is MCP?",
            tools=tool_definitions,
            tool_manager=mock_tool_manager
        )

        # Verify response is the final synthesized answer
        assert isinstance(response, str)
        assert "Model Context Protocol" in response

        # Verify API was called twice (once for tool_use, once for final response)
        assert mock_anthropic_client.messages.create.call_count == 2

        # Verify first call included tools
        first_call = mock_anthropic_client.messages.create.call_args_list[0]
        assert 'tools' in first_call[1]
        assert first_call[1]['tools'] == tool_definitions

    def test_tool_execution_flow(self, mock_anthropic_client):
        """Test the detailed flow of tool execution"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "[MCP - Lesson 1]\nMCP stands for Model Context Protocol."

        # Mock responses
        tool_use_response = MockAnthropicResponse(
            content=[
                MockToolUseBlock(
                    tool_id="tool123",
                    name="search_course_content",
                    input_data={"query": "What is MCP?"}
                )
            ],
            stop_reason="tool_use"
        )

        final_response = MockAnthropicResponse(
            content=[MockTextBlock("MCP stands for Model Context Protocol.")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [tool_use_response, final_response]

        # Execute
        response = generator.generate_response(
            query="What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="What is MCP?"
        )

        # Verify second API call included tool results
        second_call = mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call[1]['messages']

        # Should have 3 messages: user query, assistant tool use, user tool results
        assert len(messages) >= 2

        # Last message should be tool results
        tool_result_msg = messages[-1]
        assert tool_result_msg['role'] == 'user'
        assert isinstance(tool_result_msg['content'], list)
        assert tool_result_msg['content'][0]['type'] == 'tool_result'
        assert tool_result_msg['content'][0]['tool_use_id'] == 'tool123'

    def test_tool_execution_with_no_results_found(self, mock_anthropic_client):
        """Test flow when tool returns 'No relevant content found'"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager returning empty results
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "No relevant content found."

        # Mock responses
        tool_use_response = SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE

        # Claude's response after seeing empty results
        empty_result_response = MockAnthropicResponse(
            content=[MockTextBlock("I couldn't find any information about that in the course materials.")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [tool_use_response, empty_result_response]

        # Execute
        response = generator.generate_response(
            query="What is XYZ?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify Claude received the empty result and synthesized appropriate response
        assert "couldn't find" in response or "No" in response

    def test_multiple_tool_uses_in_single_response(self, mock_anthropic_client):
        """Test handling of multiple tool uses in one Claude response"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "[MCP - Lesson 1]\nMCP content",
            "[MCP - Lesson 2]\nMore MCP content"
        ]

        # Mock response with TWO tool uses
        multi_tool_response = MockAnthropicResponse(
            content=[
                MockToolUseBlock("tool1", "search_course_content", {"query": "MCP intro"}),
                MockToolUseBlock("tool2", "search_course_content", {"query": "MCP advanced"})
            ],
            stop_reason="tool_use"
        )

        final_response = MockAnthropicResponse(
            content=[MockTextBlock("Combined answer from both searches")],
            stop_reason="end_turn"
        )

        mock_anthropic_client.messages.create.side_effect = [multi_tool_response, final_response]

        # Execute
        response = generator.generate_response(
            query="Tell me about MCP",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify both tool results were sent back to Claude in single message
        second_call = mock_anthropic_client.messages.create.call_args_list[1]
        tool_result_msg = second_call[1]['messages'][-1]

        assert len(tool_result_msg['content']) == 2  # Two tool results
        assert all(r['type'] == 'tool_result' for r in tool_result_msg['content'])


class TestAIGeneratorErrorHandling:
    """Test error handling in AIGenerator"""

    def test_handles_missing_tool_manager(self, mock_anthropic_client):
        """Test that tool_use response without tool_manager is handled"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool_use response but no tool_manager provided
        mock_anthropic_client.messages.create.return_value = SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE

        # This should not crash, but won't execute tools
        # The exact behavior depends on implementation
        response = generator.generate_response(
            query="What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=None  # No tool manager!
        )

        # Should return some response (implementation may vary)
        assert isinstance(response, str)


class TestAIGeneratorSequentialToolCalling:
    """Test sequential tool calling with up to 2 rounds"""

    def test_two_sequential_tool_calls(self, mock_anthropic_client):
        """Test full 2-round flow with different tools each round"""
        from tests.fixtures.sample_data import (
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE_2,
            SAMPLE_ANTHROPIC_FINAL_RESPONSE_AFTER_TWO_ROUNDS
        )

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager (use Mock, not fixture)
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "[MCP Course] Lesson 4: Building Applications",  # First tool call
            "[MCP - Lesson 4] Content about building MCP applications..."  # Second tool call
        ]

        # Mock tool definitions
        tool_definitions = [
            {"name": "get_course_outline"},
            {"name": "search_course_content"}
        ]

        # Mock 3 API responses: tool_use, tool_use, end_turn
        mock_anthropic_client.messages.create.side_effect = [
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE,  # Round 1: search_course_content
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE_2,  # Round 2: get_course_outline
            SAMPLE_ANTHROPIC_FINAL_RESPONSE_AFTER_TWO_ROUNDS  # Final: end_turn
        ]

        # Execute
        response = generator.generate_response(
            query="What does lesson 4 of MCP teach?",
            tools=tool_definitions,
            tool_manager=mock_tool_manager
        )

        # Verify: 3 API calls made (2 tool rounds + 1 final)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify: Both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify: Final response contains synthesized answer
        assert isinstance(response, str)
        assert "lesson 4" in response.lower() or "building applications" in response.lower()

    def test_max_rounds_enforced(self, mock_anthropic_client):
        """Test that exactly 2 rounds allowed, then forced synthesis"""
        from tests.fixtures.sample_data import (
            create_mock_always_tool_use,
            SAMPLE_ANTHROPIC_FINAL_RESPONSE
        )

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Mock responses: always tool_use for first 2 calls, then end_turn for final
        mock_anthropic_client.messages.create.side_effect = [
            create_mock_always_tool_use(),  # Round 1: tool_use
            create_mock_always_tool_use(),  # Round 2: tool_use
            SAMPLE_ANTHROPIC_FINAL_RESPONSE  # Final synthesis: end_turn
        ]

        # Execute
        response = generator.generate_response(
            query="Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify: Exactly 3 API calls (2 with tools, 1 without)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify: Tools were executed exactly 2 times (once per round)
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify: Third API call had NO tools parameter
        third_call_kwargs = mock_anthropic_client.messages.create.call_args_list[2][1]
        assert 'tools' not in third_call_kwargs

        # Verify: Response returned
        assert isinstance(response, str)

    def test_early_termination_on_end_turn(self, mock_anthropic_client):
        """Test early exit when Claude provides direct answer in round 2"""
        from tests.fixtures.sample_data import SAMPLE_ANTHROPIC_FINAL_RESPONSE

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Mock responses: tool_use, then end_turn (early exit)
        mock_anthropic_client.messages.create.side_effect = [
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE,  # Round 1: tool_use
            SAMPLE_ANTHROPIC_FINAL_RESPONSE  # Round 2: end_turn (Claude decides it's done)
        ]

        # Execute
        response = generator.generate_response(
            query="Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify: Only 2 API calls (not 3)
        assert mock_anthropic_client.messages.create.call_count == 2

        # Verify: Tool executed once
        assert mock_tool_manager.execute_tool.call_count == 1

        # Verify: Response returned
        assert isinstance(response, str)
        assert "Model Context Protocol" in response

    def test_message_history_accumulates(self, mock_anthropic_client):
        """Verify messages list grows correctly across rounds"""
        from tests.fixtures.sample_data import (
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE_2,
            SAMPLE_ANTHROPIC_FINAL_RESPONSE_AFTER_TWO_ROUNDS
        )

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Mock responses
        mock_anthropic_client.messages.create.side_effect = [
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE,  # Round 1
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE_2,  # Round 2
            SAMPLE_ANTHROPIC_FINAL_RESPONSE_AFTER_TWO_ROUNDS  # Final
        ]

        # Execute
        response = generator.generate_response(
            query="Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify message structure at each API call
        call_args_list = mock_anthropic_client.messages.create.call_args_list

        # Call 1: messages = [user]
        first_call_messages = call_args_list[0][1]['messages']
        assert len(first_call_messages) == 1
        assert first_call_messages[0]['role'] == 'user'

        # Call 2: messages = [user, assistant, user]
        second_call_messages = call_args_list[1][1]['messages']
        assert len(second_call_messages) == 3
        assert second_call_messages[0]['role'] == 'user'
        assert second_call_messages[1]['role'] == 'assistant'
        assert second_call_messages[2]['role'] == 'user'

        # Call 3: messages = [user, assistant, user, assistant, user]
        third_call_messages = call_args_list[2][1]['messages']
        assert len(third_call_messages) == 5
        assert third_call_messages[0]['role'] == 'user'
        assert third_call_messages[1]['role'] == 'assistant'
        assert third_call_messages[2]['role'] == 'user'
        assert third_call_messages[3]['role'] == 'assistant'
        assert third_call_messages[4]['role'] == 'user'

    def test_tool_error_in_second_round(self, mock_anthropic_client):
        """Test graceful error handling in second round"""
        from tests.fixtures.sample_data import (
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE_2,
            SAMPLE_ANTHROPIC_FINAL_RESPONSE
        )

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager: first call succeeds, second call raises exception
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Tool result from round 1",  # Success
            Exception("Database connection error")  # Error in round 2
        ]

        # Mock responses
        mock_anthropic_client.messages.create.side_effect = [
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE,  # Round 1
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE_2,  # Round 2
            SAMPLE_ANTHROPIC_FINAL_RESPONSE  # Final
        ]

        # Execute
        response = generator.generate_response(
            query="Test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify: Error didn't crash, response was returned
        assert isinstance(response, str)

        # Verify: Tool called twice (once successfully, once with error)
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify: Error was passed to Claude as tool_result with is_error
        third_call_messages = mock_anthropic_client.messages.create.call_args_list[2][1]['messages']
        # Last user message should contain tool results
        tool_results = third_call_messages[-1]['content']
        # Should have tool_result with error
        assert any(
            tr.get('type') == 'tool_result' and tr.get('is_error') == True
            for tr in tool_results
        )

    def test_single_round_still_works(self, mock_anthropic_client):
        """Ensure existing single-round queries work unchanged (backwards compatibility)"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "MCP stands for Model Context Protocol"

        # Mock responses: tool_use, then immediate end_turn
        mock_anthropic_client.messages.create.side_effect = [
            SAMPLE_ANTHROPIC_TOOL_USE_RESPONSE,  # Round 1: tool_use
            SAMPLE_ANTHROPIC_FINAL_RESPONSE  # Round 1 response: end_turn (Claude done after 1 tool)
        ]

        # Execute
        response = generator.generate_response(
            query="What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager
        )

        # Verify: 2 API calls (same as old behavior)
        assert mock_anthropic_client.messages.create.call_count == 2

        # Verify: Tool executed once
        assert mock_tool_manager.execute_tool.call_count == 1

        # Verify: Response returned
        assert isinstance(response, str)
        assert "Model Context Protocol" in response
