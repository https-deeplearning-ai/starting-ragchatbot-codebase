"""
Tests for AIGenerator - Focus on tool calling and OpenRouter system prompt bug
"""

from unittest.mock import Mock

from ai_generator import AIGenerator


class TestAnthropicToolCalling:
    """Test Anthropic provider tool calling"""

    def test_anthropic_without_tools(self, mock_anthropic_client, mock_tool_manager):
        """Test basic response without tool use"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4", provider="anthropic")
        generator.client = mock_anthropic_client

        response = generator.generate_response(
            query="What is Python?", conversation_history=None, tools=None, tool_manager=None
        )

        assert response == "Test response"
        mock_anthropic_client.messages.create.assert_called_once()

    def test_anthropic_with_tool_use(self, mock_tool_manager):
        """Test Anthropic tool calling flow"""
        # Create mock client with tool use response
        mock_client = Mock()

        # First response: tool use
        tool_use_response = Mock()
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "test"}
        tool_use_response.content = [tool_use_block]
        tool_use_response.stop_reason = "tool_use"

        # Second response: final answer
        final_response = Mock()
        final_text = Mock()
        final_text.type = "text"
        final_text.text = "Final answer with tool results"
        final_response.content = [final_text]
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4", provider="anthropic")
        generator.client = mock_client

        response = generator.generate_response(
            query="What's in the MCP course?",
            conversation_history=None,
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Should call API twice (tool use + final response)
        assert mock_client.messages.create.call_count == 2
        # Should execute tool
        mock_tool_manager.execute_tool.assert_called_once()
        assert response == "Final answer with tool results"


class TestOpenRouterToolCalling:
    """Test OpenRouter provider tool calling - CRITICAL BUG #1"""

    def test_openrouter_system_prompt_in_final_call(self, mock_tool_manager):
        """
        CRITICAL TEST: Tests Bug #1 - Missing system prompt in OpenRouter final call

        This test will FAIL with current code because:
        - Line 213-216 in ai_generator.py doesn't include system prompt in final API call
        - The final call uses **self.base_params which doesn't include system message
        - OpenRouter models need system prompt to maintain context

        Expected: System prompt should be included in the final API call after tool execution
        """
        # Create mock OpenRouter client
        mock_client = Mock()

        # First response: tool use
        tool_call_response = Mock()
        tool_call_message = Mock()
        tool_call = Mock()
        tool_call.function.name = "search_course_content"
        tool_call.function.arguments = '{"query": "test"}'
        tool_call.id = "call_123"
        tool_call_message.tool_calls = [tool_call]
        tool_call_response.choices = [Mock(message=tool_call_message)]

        # Second response: final answer
        final_response = Mock()
        final_message = Mock()
        final_message.content = "Final answer"
        final_message.tool_calls = None
        final_response.choices = [Mock(message=final_message)]

        mock_client.chat.completions.create.side_effect = [tool_call_response, final_response]

        generator = AIGenerator(
            api_key="test-key",
            model="anthropic/claude-3.5-sonnet",
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
        )
        generator.client = mock_client

        _response = generator.generate_response(  # noqa: F841
            query="What's in the MCP course?",
            conversation_history=None,
            tools=[
                {
                    "name": "search_course_content",
                    "description": "Search course content",
                    "input_schema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                }
            ],
            tool_manager=mock_tool_manager,
        )

        # Verify final API call includes system prompt
        assert mock_client.chat.completions.create.call_count == 2

        # Get the second (final) API call
        final_call_kwargs = mock_client.chat.completions.create.call_args_list[1][1]

        # CRITICAL CHECK: System prompt must be in messages for final call
        messages = final_call_kwargs.get("messages", [])

        # Should have system message at the start
        system_messages = [msg for msg in messages if msg.get("role") == "system"]

        # THIS WILL FAIL - current code doesn't include system prompt in final call
        assert len(system_messages) > 0, "System prompt missing in OpenRouter final call!"
        assert generator.SYSTEM_PROMPT in system_messages[0]["content"]

    def test_openrouter_basic_response(self, mock_openai_client):
        """Test basic OpenRouter response without tools"""
        generator = AIGenerator(
            api_key="test-key",
            model="anthropic/claude-3.5-sonnet",
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
        )
        generator.client = mock_openai_client

        response = generator.generate_response(
            query="What is Python?", conversation_history=None, tools=None, tool_manager=None
        )

        assert response == "Test response"


class TestToolExecutionErrorHandling:
    """Test error handling in tool execution - Bug #5"""

    def test_tool_execution_exception_anthropic(self):
        """
        Tests Bug #5 - No error handling for tool execution

        Current code doesn't wrap tool_manager.execute_tool() in try-except
        If tool execution fails, the entire query crashes

        Expected: Should catch exceptions and return error message to model
        """
        mock_client = Mock()

        # Tool use response
        tool_use_response = Mock()
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "test"}
        tool_use_response.content = [tool_use_block]
        tool_use_response.stop_reason = "tool_use"

        # Final response
        final_response = Mock()
        final_text = Mock()
        final_text.type = "text"
        final_text.text = "Error handled response"
        final_response.content = [final_text]
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        # Tool manager that raises exception
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed!")

        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4", provider="anthropic")
        generator.client = mock_client

        # THIS WILL FAIL - current code doesn't handle tool execution exceptions
        # Should not raise exception, should handle gracefully
        response = generator.generate_response(
            query="test",
            conversation_history=None,
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Should complete despite tool error
        assert response is not None

    def test_tool_execution_exception_openrouter(self):
        """Test OpenRouter tool execution error handling"""
        mock_client = Mock()

        # Tool call response
        tool_call_response = Mock()
        tool_call_message = Mock()
        tool_call = Mock()
        tool_call.function.name = "search_course_content"
        tool_call.function.arguments = '{"query": "test"}'
        tool_call.id = "call_123"
        tool_call_message.tool_calls = [tool_call]
        tool_call_response.choices = [Mock(message=tool_call_message)]

        # Final response
        final_response = Mock()
        final_message = Mock()
        final_message.content = "Error handled"
        final_message.tool_calls = None
        final_response.choices = [Mock(message=final_message)]

        mock_client.chat.completions.create.side_effect = [tool_call_response, final_response]

        # Tool manager that raises exception
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed!")

        generator = AIGenerator(
            api_key="test-key",
            model="anthropic/claude-3.5-sonnet",
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
        )
        generator.client = mock_client

        # Should not raise exception
        response = generator.generate_response(
            query="test",
            conversation_history=None,
            tools=[
                {
                    "name": "search_course_content",
                    "description": "Search course content",
                    "input_schema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                }
            ],
            tool_manager=mock_tool_manager,
        )

        assert response is not None


class TestConversationHistory:
    """Test conversation history handling"""

    def test_with_conversation_history(self, mock_anthropic_client):
        """Test that conversation history is included in system prompt"""
        generator = AIGenerator(api_key="test-key", model="claude-sonnet-4", provider="anthropic")
        generator.client = mock_anthropic_client

        # Format history as string (same format as SessionManager.get_conversation_history)
        history = "User: What is MCP?\nAssistant: MCP is Model Context Protocol\nUser: Tell me more\nAssistant: It's a way to..."

        generator.generate_response(
            query="What's the latest?", conversation_history=history, tools=None, tool_manager=None
        )

        # Verify history was included in system prompt
        call_kwargs = mock_anthropic_client.messages.create.call_args.kwargs
        system_content = call_kwargs["system"]

        # History should be in system prompt
        assert "What is MCP?" in system_content
        assert "MCP is Model Context Protocol" in system_content


class TestSequentialToolCalling:
    """Test sequential tool calling with loop-based implementation"""

    def test_single_round_backward_compatibility(self, mock_tool_manager):
        """Test that single-round tool calling still works (backward compatibility)"""
        mock_client = Mock()

        # Single tool use response, then final answer
        tool_use_response = Mock()
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "test"}
        tool_use_response.content = [tool_use_block]
        tool_use_response.stop_reason = "tool_use"

        # Second call returns final answer (no more tool use)
        final_response = Mock()
        final_text = Mock()
        final_text.type = "text"
        final_text.text = "Final answer"
        final_response.content = [final_text]
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_use_response, final_response]

        generator = AIGenerator(
            api_key="test-key", model="claude-sonnet-4", provider="anthropic", max_tool_rounds=2
        )
        generator.client = mock_client

        response = generator.generate_response(
            query="What's in the course?",
            conversation_history=None,
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Should call API twice (tool use + final)
        assert mock_client.messages.create.call_count == 2
        # Should execute tool once
        assert mock_tool_manager.execute_tool.call_count == 1
        assert response == "Final answer"

    def test_two_sequential_rounds_anthropic(self, mock_tool_manager):
        """Test Anthropic provider with 2 sequential tool calls"""
        mock_client = Mock()

        # First response: tool use
        tool_use_1 = Mock()
        tool_use_block_1 = Mock()
        tool_use_block_1.type = "tool_use"
        tool_use_block_1.name = "get_course_outline"
        tool_use_block_1.id = "tool_1"
        tool_use_block_1.input = {"course_name": "MCP"}
        tool_use_1.content = [tool_use_block_1]
        tool_use_1.stop_reason = "tool_use"

        # Second response: another tool use
        tool_use_2 = Mock()
        tool_use_block_2 = Mock()
        tool_use_block_2.type = "tool_use"
        tool_use_block_2.name = "search_course_content"
        tool_use_block_2.id = "tool_2"
        tool_use_block_2.input = {"query": "lesson 3", "course_name": "MCP"}
        tool_use_2.content = [tool_use_block_2]
        tool_use_2.stop_reason = "tool_use"

        # Third response: final answer
        final_response = Mock()
        final_text = Mock()
        final_text.type = "text"
        final_text.text = "Lesson 3 covers..."
        final_response.content = [final_text]
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_use_1, tool_use_2, final_response]

        generator = AIGenerator(
            api_key="test-key", model="claude-sonnet-4", provider="anthropic", max_tool_rounds=2
        )
        generator.client = mock_client

        response = generator.generate_response(
            query="What does lesson 3 of MCP course cover?",
            conversation_history=None,
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Should call API 3 times (tool1 + tool2 + final)
        assert mock_client.messages.create.call_count == 3
        # Should execute tools twice
        assert mock_tool_manager.execute_tool.call_count == 2
        assert response == "Lesson 3 covers..."

    def test_max_depth_enforcement_anthropic(self, mock_tool_manager):
        """Test that Anthropic stops at max_tool_rounds=2"""
        mock_client = Mock()

        # All responses are tool uses (Claude keeps requesting tools)
        tool_use_response = Mock()
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "tool_123"
        tool_use_block.input = {"query": "test"}
        tool_use_response.content = [tool_use_block]
        tool_use_response.stop_reason = "tool_use"

        # Final response after max rounds
        final_response = Mock()
        final_text = Mock()
        final_text.type = "text"
        final_text.text = "Final answer after max rounds"
        final_response.content = [final_text]

        # Claude tries to use tools 3 times, but we stop at 2
        mock_client.messages.create.side_effect = [
            tool_use_response,  # Round 1
            tool_use_response,  # Round 2
            final_response,  # Final call without tools
        ]

        generator = AIGenerator(
            api_key="test-key", model="claude-sonnet-4", provider="anthropic", max_tool_rounds=2
        )
        generator.client = mock_client

        response = generator.generate_response(
            query="Test query",
            conversation_history=None,
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Should call API exactly 3 times (2 tool rounds + 1 final)
        assert mock_client.messages.create.call_count == 3
        # Should execute tools exactly twice (max_tool_rounds=2)
        assert mock_tool_manager.execute_tool.call_count == 2
        assert response == "Final answer after max rounds"

    def test_two_sequential_rounds_openrouter(self, mock_tool_manager):
        """Test OpenRouter provider with 2 sequential tool calls"""
        mock_client = Mock()

        # First response: tool call
        tool_call_1 = Mock()
        tool_call_1.function.name = "get_course_outline"
        tool_call_1.function.arguments = '{"course_name": "MCP"}'
        tool_call_1.id = "call_1"

        message_1 = Mock()
        message_1.tool_calls = [tool_call_1]
        message_1.content = None
        response_1 = Mock()
        response_1.choices = [Mock(message=message_1)]

        # Second response: another tool call
        tool_call_2 = Mock()
        tool_call_2.function.name = "search_course_content"
        tool_call_2.function.arguments = '{"query": "lesson 3", "course_name": "MCP"}'
        tool_call_2.id = "call_2"

        message_2 = Mock()
        message_2.tool_calls = [tool_call_2]
        message_2.content = None
        response_2 = Mock()
        response_2.choices = [Mock(message=message_2)]

        # Third response: final answer
        final_message = Mock()
        final_message.tool_calls = None
        final_message.content = "Lesson 3 covers..."
        final_response = Mock()
        final_response.choices = [Mock(message=final_message)]

        mock_client.chat.completions.create.side_effect = [response_1, response_2, final_response]

        generator = AIGenerator(
            api_key="test-key",
            model="anthropic/claude-3.5-sonnet",
            provider="openrouter",
            base_url="https://openrouter.ai/api/v1",
            max_tool_rounds=2,
        )
        generator.client = mock_client

        # Complete tool definitions with required fields
        tools = [
            {"name": "get_course_outline", "description": "Get course outline", "input_schema": {}},
            {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {},
            },
        ]

        response = generator.generate_response(
            query="What does lesson 3 of MCP course cover?",
            conversation_history=None,
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        # Should call API 3 times
        assert mock_client.chat.completions.create.call_count == 3
        # Should execute tools twice
        assert mock_tool_manager.execute_tool.call_count == 2
        assert response == "Lesson 3 covers..."

    def test_max_depth_enforcement_openrouter(self, mock_tool_manager):
        """Test that OpenRouter stops at max_tool_rounds=2"""
        mock_client = Mock()

        # All responses have tool calls (Claude keeps requesting tools)
        tool_call = Mock()
        tool_call.function.name = "search_course_content"
        tool_call.function.arguments = '{"query": "test"}'
        tool_call.id = "call_123"

        message_with_tools = Mock()
        message_with_tools.tool_calls = [tool_call]
        message_with_tools.content = None
        response_with_tools = Mock()
        response_with_tools.choices = [Mock(message=message_with_tools)]

        # Final response
        final_message = Mock()
        final_message.content = "Final answer after max rounds"
        final_response = Mock()
        final_response.choices = [Mock(message=final_message)]

        mock_client.chat.completions.create.side_effect = [
            response_with_tools,  # Round 1
            response_with_tools,  # Round 2
            final_response,  # Final call
        ]

        generator = AIGenerator(
            api_key="test-key",
            model="anthropic/claude-3.5-sonnet",
            provider="openrouter",
            max_tool_rounds=2,
        )
        generator.client = mock_client

        # Complete tool definition with required fields
        tools = [
            {"name": "search_course_content", "description": "Search content", "input_schema": {}}
        ]

        response = generator.generate_response(
            query="Test query",
            conversation_history=None,
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        # Should call API exactly 3 times
        assert mock_client.chat.completions.create.call_count == 3
        # Should execute tools exactly twice
        assert mock_tool_manager.execute_tool.call_count == 2
        assert response == "Final answer after max rounds"

    def test_message_history_preserved_sequential(self, mock_tool_manager):
        """Test that message history is preserved across sequential tool rounds"""
        mock_client = Mock()

        # Two tool use rounds
        tool_use_1 = Mock()
        tool_use_block_1 = Mock()
        tool_use_block_1.type = "tool_use"
        tool_use_block_1.name = "get_course_outline"
        tool_use_block_1.id = "tool_1"
        tool_use_block_1.input = {"course_name": "MCP"}
        tool_use_1.content = [tool_use_block_1]
        tool_use_1.stop_reason = "tool_use"

        tool_use_2 = Mock()
        tool_use_block_2 = Mock()
        tool_use_block_2.type = "tool_use"
        tool_use_block_2.name = "search_course_content"
        tool_use_block_2.id = "tool_2"
        tool_use_block_2.input = {"query": "lesson 3"}
        tool_use_2.content = [tool_use_block_2]
        tool_use_2.stop_reason = "tool_use"

        final_response = Mock()
        final_text = Mock()
        final_text.type = "text"
        final_text.text = "Final answer"
        final_response.content = [final_text]
        final_response.stop_reason = "end_turn"

        mock_client.messages.create.side_effect = [tool_use_1, tool_use_2, final_response]

        generator = AIGenerator(
            api_key="test-key", model="claude-sonnet-4", provider="anthropic", max_tool_rounds=2
        )
        generator.client = mock_client

        response = generator.generate_response(
            query="What does lesson 3 cover?",
            conversation_history=None,
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify sequential tool calling occurred correctly
        # Should make 3 API calls total (2 tool rounds + 1 final)
        assert mock_client.messages.create.call_count == 3

        # Should execute both tools
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify final response
        assert response == "Final answer"

        # Verify that system prompt was included in all calls
        for api_call in mock_client.messages.create.call_args_list:
            call_kwargs = api_call[1]
            assert "system" in call_kwargs, "System prompt should be in all API calls"
