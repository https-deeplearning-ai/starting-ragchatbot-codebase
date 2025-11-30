"""
Tests for AIGenerator tool calling functionality
Tests the integration between AIGenerator and the tool system
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager


class TestAIGeneratorToolCalling:
    """Test suite for AIGenerator tool calling capabilities"""

    @pytest.fixture
    def ai_generator(self):
        """Create an AIGenerator instance with fake API key"""
        return AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

    @pytest.fixture
    def tool_manager(self, mock_vector_store):
        """Create a ToolManager with CourseSearchTool"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)
        return manager

    def test_tools_passed_to_api(self, ai_generator, tool_manager):
        """Test that tools are correctly passed to the Anthropic API"""
        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # Setup mock response
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = [Mock(text="Response without tools")]
            mock_create.return_value = mock_response

            # Call with tools
            tools = tool_manager.get_tool_definitions()
            ai_generator.generate_response(
                query="Test query", tools=tools, tool_manager=tool_manager
            )

            # Verify tools were passed in API call
            call_args = mock_create.call_args
            assert "tools" in call_args.kwargs
            assert call_args.kwargs["tools"] == tools
            assert "tool_choice" in call_args.kwargs
            assert call_args.kwargs["tool_choice"] == {"type": "auto"}

    def test_direct_response_without_tools(self, ai_generator):
        """Test response when Claude doesn't use tools"""
        with patch.object(ai_generator.client.messages, "create") as mock_create:
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = [Mock(text="Direct response without using tools")]
            mock_create.return_value = mock_response

            response = ai_generator.generate_response(query="What is 2+2?", tools=None)

            assert response == "Direct response without using tools"
            # Should only call API once (no tool execution)
            assert mock_create.call_count == 1

    def test_tool_execution_flow(self, ai_generator, tool_manager, mock_vector_store):
        """Test full tool execution flow: request -> execute -> final response"""
        from vector_store import SearchResults

        # Setup mock vector store response
        mock_search_results = SearchResults(
            documents=["Python is a programming language"],
            metadata=[{"course_title": "Python 101", "lesson_number": 1}],
            distances=[0.1],
            links=["http://example.com/lesson1"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_search_results

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # First call: Claude wants to use tool
            tool_use_response = Mock()
            tool_use_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "tool_abc123"
            tool_block.input = {"query": "What is Python?"}

            tool_use_response.content = [tool_block]

            # Second call: Final response after tool execution
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [
                Mock(text="Python is a high-level programming language.")
            ]

            # Configure mock to return different responses
            mock_create.side_effect = [tool_use_response, final_response]

            # Execute
            tools = tool_manager.get_tool_definitions()
            response = ai_generator.generate_response(
                query="What is Python?", tools=tools, tool_manager=tool_manager
            )

            # Verify tool was executed
            mock_vector_store.search.assert_called_once_with(
                query="What is Python?", course_name=None, lesson_number=None
            )

            # Verify final response
            assert response == "Python is a high-level programming language."

            # Verify API was called twice (initial + after tool execution)
            assert mock_create.call_count == 2

    def test_tool_result_integration(
        self, ai_generator, tool_manager, mock_vector_store
    ):
        """Test that tool results are properly integrated into the message flow"""
        from vector_store import SearchResults

        mock_search_results = SearchResults(
            documents=["Tool result content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
            links=["http://test.com"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_search_results

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # Tool use response
            tool_use_response = Mock()
            tool_use_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "tool_xyz"
            tool_block.input = {"query": "test"}

            tool_use_response.content = [tool_block]

            # Final response
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Final answer")]

            mock_create.side_effect = [tool_use_response, final_response]

            tools = tool_manager.get_tool_definitions()
            ai_generator.generate_response(
                query="test query", tools=tools, tool_manager=tool_manager
            )

            # Check second API call includes tool results
            second_call = mock_create.call_args_list[1]
            messages = second_call.kwargs["messages"]

            # Should have 3 messages: user, assistant (tool use), user (tool result)
            assert len(messages) == 3
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"
            assert messages[2]["role"] == "user"

            # Verify tool result message structure
            tool_result_message = messages[2]["content"][0]
            assert tool_result_message["type"] == "tool_result"
            assert tool_result_message["tool_use_id"] == "tool_xyz"
            assert "content" in tool_result_message

    def test_max_tokens_configuration(self, ai_generator):
        """Test that max_tokens is configured correctly"""
        with patch.object(ai_generator.client.messages, "create") as mock_create:
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = [Mock(text="Response")]
            mock_create.return_value = mock_response

            ai_generator.generate_response(query="test")

            # Check max_tokens in API call
            call_args = mock_create.call_args
            assert (
                call_args.kwargs["max_tokens"] == 2048
            )  # Increased from 800 for comprehensive responses

    def test_temperature_configuration(self, ai_generator):
        """Test that temperature is set to 0 for deterministic responses"""
        with patch.object(ai_generator.client.messages, "create") as mock_create:
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = [Mock(text="Response")]
            mock_create.return_value = mock_response

            ai_generator.generate_response(query="test")

            call_args = mock_create.call_args
            assert call_args.kwargs["temperature"] == 0

    def test_system_prompt_included(self, ai_generator):
        """Test that system prompt is included in API calls"""
        with patch.object(ai_generator.client.messages, "create") as mock_create:
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = [Mock(text="Response")]
            mock_create.return_value = mock_response

            ai_generator.generate_response(query="test")

            call_args = mock_create.call_args
            assert "system" in call_args.kwargs
            system_content = call_args.kwargs["system"]
            # Should include the static system prompt
            assert "AI assistant specialized in course materials" in system_content

    def test_conversation_history_integration(self, ai_generator):
        """Test that conversation history is added to system prompt"""
        with patch.object(ai_generator.client.messages, "create") as mock_create:
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = [Mock(text="Response")]
            mock_create.return_value = mock_response

            history = "User: Previous question\nAssistant: Previous answer"
            ai_generator.generate_response(
                query="Follow-up question", conversation_history=history
            )

            call_args = mock_create.call_args
            system_content = call_args.kwargs["system"]
            assert "Previous conversation:" in system_content
            assert "Previous question" in system_content
            assert "Previous answer" in system_content

    def test_multiple_tool_calls_in_sequence(
        self, ai_generator, tool_manager, mock_vector_store
    ):
        """Test handling of multiple tool blocks in one response"""
        from vector_store import SearchResults

        mock_search_results = SearchResults(
            documents=["Result"],
            metadata=[{"course_title": "Course", "lesson_number": 1}],
            distances=[0.1],
            links=["http://example.com"],
            error=None,
        )
        mock_vector_store.search.return_value = mock_search_results

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # Response with multiple tool uses
            tool_use_response = Mock()
            tool_use_response.stop_reason = "tool_use"

            tool_block1 = Mock()
            tool_block1.type = "tool_use"
            tool_block1.name = "search_course_content"
            tool_block1.id = "tool_1"
            tool_block1.input = {"query": "query 1"}

            tool_block2 = Mock()
            tool_block2.type = "tool_use"
            tool_block2.name = "search_course_content"
            tool_block2.id = "tool_2"
            tool_block2.input = {"query": "query 2"}

            tool_use_response.content = [tool_block1, tool_block2]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Final")]

            mock_create.side_effect = [tool_use_response, final_response]

            tools = tool_manager.get_tool_definitions()
            response = ai_generator.generate_response(
                query="test", tools=tools, tool_manager=tool_manager
            )

            # Both tools should be executed
            assert mock_vector_store.search.call_count == 2

            # Second API call should have results for both tools
            second_call = mock_create.call_args_list[1]
            tool_results = second_call.kwargs["messages"][2]["content"]
            assert len(tool_results) == 2  # Two tool results

    def test_tool_not_found_error_handling(self, ai_generator, tool_manager):
        """Test handling when Claude requests a tool that doesn't exist"""
        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # Claude tries to use non-existent tool
            tool_use_response = Mock()
            tool_use_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "nonexistent_tool"
            tool_block.id = "tool_fail"
            tool_block.input = {}

            tool_use_response.content = [tool_block]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Error handled")]

            mock_create.side_effect = [tool_use_response, final_response]

            tools = tool_manager.get_tool_definitions()
            response = ai_generator.generate_response(
                query="test", tools=tools, tool_manager=tool_manager
            )

            # Should still return a response (error is passed back to Claude)
            assert response == "Error handled"

            # Check that error message was sent to Claude
            second_call = mock_create.call_args_list[1]
            tool_result = second_call.kwargs["messages"][2]["content"][0]
            assert "Tool 'nonexistent_tool' not found" in tool_result["content"]
