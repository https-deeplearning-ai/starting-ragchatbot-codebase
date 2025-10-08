"""Tests for AIGenerator tool calling functionality"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from ai_generator import AIGenerator
import anthropic


class TestAIGeneratorToolCalling:
    """Test AIGenerator's ability to correctly call tools"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Create a mock Anthropic client"""
        with patch('anthropic.Anthropic') as mock_client:
            yield mock_client

    @pytest.fixture
    def ai_generator_with_mock(self, mock_api_key, mock_anthropic_client):
        """Create AIGenerator with mocked client"""
        generator = AIGenerator(api_key=mock_api_key, model="claude-sonnet-4-20250514")
        generator.client = mock_anthropic_client.return_value
        return generator

    def test_generate_response_without_tools(self, ai_generator_with_mock):
        """Test basic response generation without tool calling"""
        # Mock response
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="This is a test response")]

        ai_generator_with_mock.client.messages.create.return_value = mock_response

        result = ai_generator_with_mock.generate_response(
            query="What is 2+2?",
            conversation_history=None,
            tools=None,
            tool_manager=None
        )

        assert result == "This is a test response"
        assert ai_generator_with_mock.client.messages.create.called

    def test_tool_call_triggered_for_content_question(self, ai_generator_with_mock, tool_manager):
        """Test that content-related questions trigger tool use"""
        # Mock initial response with tool use
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_123"
        mock_tool_block.input = {"query": "machine learning"}

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_block]

        # Mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Machine learning is a subset of AI...")]

        ai_generator_with_mock.client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        result = ai_generator_with_mock.generate_response(
            query="What is machine learning?",
            conversation_history=None,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Should have called API twice (initial + final)
        assert ai_generator_with_mock.client.messages.create.call_count == 2
        assert result == "Machine learning is a subset of AI..."

    def test_tool_parameters_extracted_correctly(self, ai_generator_with_mock, tool_manager):
        """Test that tool parameters are correctly extracted from queries"""
        # Mock tool use with course_name parameter
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_456"
        mock_tool_block.input = {
            "query": "neural networks",
            "course_name": "Introduction to Machine Learning",
            "lesson_number": 2
        }

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_block]

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Neural networks are...")]

        ai_generator_with_mock.client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        # Mock the tool manager's execute to verify parameters
        original_execute = tool_manager.execute_tool
        executed_params = {}

        def capture_execute(tool_name, **kwargs):
            executed_params['tool_name'] = tool_name
            executed_params['params'] = kwargs
            return original_execute(tool_name, **kwargs)

        tool_manager.execute_tool = capture_execute

        result = ai_generator_with_mock.generate_response(
            query="Tell me about neural networks in lesson 2 of the ML course",
            conversation_history=None,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Verify parameters were passed
        assert executed_params['tool_name'] == "search_course_content"
        assert 'query' in executed_params['params']
        assert executed_params['params']['query'] == "neural networks"

    def test_tool_result_synthesis(self, ai_generator_with_mock, tool_manager):
        """Test that tool results are properly synthesized into response"""
        # Mock tool use
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_789"
        mock_tool_block.input = {"query": "API basics"}

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_block]

        # Mock final response should synthesize tool results
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Based on the course content, the API basics cover...")]

        ai_generator_with_mock.client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        result = ai_generator_with_mock.generate_response(
            query="What are the API basics?",
            conversation_history=None,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Final response should be synthesized answer
        assert isinstance(result, str)
        assert len(result) > 0

    def test_conversation_history_included(self, ai_generator_with_mock):
        """Test that conversation history is included in API calls"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Response with context")]

        ai_generator_with_mock.client.messages.create.return_value = mock_response

        history = "User: What is ML?\nAssistant: Machine learning is..."

        result = ai_generator_with_mock.generate_response(
            query="Can you explain more?",
            conversation_history=history,
            tools=None,
            tool_manager=None
        )

        # Check that history was included in the system prompt
        call_args = ai_generator_with_mock.client.messages.create.call_args
        system_content = call_args[1]['system']

        assert history in system_content

    def test_multiple_tool_calls_in_sequence(self, ai_generator_with_mock, tool_manager):
        """Test handling of multiple tool calls (though system limits to 1)"""
        # First tool call
        mock_tool_block1 = Mock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "search_course_content"
        mock_tool_block1.id = "tool_001"
        mock_tool_block1.input = {"query": "supervised learning"}

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_block1]

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Supervised learning uses labeled data...")]

        ai_generator_with_mock.client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        result = ai_generator_with_mock.generate_response(
            query="Explain supervised learning",
            conversation_history=None,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        assert isinstance(result, str)

    def test_tool_execution_error_handling(self, ai_generator_with_mock, tool_manager):
        """Test handling when tool execution fails"""
        # Mock tool use
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_error"
        mock_tool_block.input = {"query": "test"}

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_block]

        # Mock final response after error
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="I couldn't find information on that topic.")]

        ai_generator_with_mock.client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        # Mock tool manager to return error
        original_execute = tool_manager.execute_tool

        def error_execute(tool_name, **kwargs):
            return "No course found matching 'InvalidCourse'"

        tool_manager.execute_tool = error_execute

        result = ai_generator_with_mock.generate_response(
            query="Tell me about InvalidCourse",
            conversation_history=None,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        # Should still return a response
        assert isinstance(result, str)
        # Restore original
        tool_manager.execute_tool = original_execute

    def test_outline_tool_called_correctly(self, ai_generator_with_mock, tool_manager):
        """Test that get_course_outline tool is called for outline queries"""
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "get_course_outline"
        mock_tool_block.id = "tool_outline"
        mock_tool_block.input = {"course_name": "Machine Learning"}

        mock_initial_response = Mock()
        mock_initial_response.stop_reason = "tool_use"
        mock_initial_response.content = [mock_tool_block]

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="The course outline includes...")]

        ai_generator_with_mock.client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response
        ]

        result = ai_generator_with_mock.generate_response(
            query="Show me the outline for Machine Learning course",
            conversation_history=None,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        assert isinstance(result, str)

    def test_system_prompt_includes_tool_instructions(self, ai_generator_with_mock, tool_manager):
        """Test that system prompt includes proper tool usage instructions"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Test")]

        ai_generator_with_mock.client.messages.create.return_value = mock_response

        ai_generator_with_mock.generate_response(
            query="Test query",
            conversation_history=None,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager
        )

        call_args = ai_generator_with_mock.client.messages.create.call_args
        system_content = call_args[1]['system']

        # Should include tool usage instructions
        assert "search_course_content" in system_content or "tool" in system_content.lower()

    def test_temperature_zero_for_deterministic_responses(self, ai_generator_with_mock):
        """Test that temperature is set to 0 for consistency"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Test")]

        ai_generator_with_mock.client.messages.create.return_value = mock_response

        ai_generator_with_mock.generate_response(
            query="Test",
            conversation_history=None,
            tools=None,
            tool_manager=None
        )

        call_args = ai_generator_with_mock.client.messages.create.call_args

        # Temperature should be 0
        assert call_args[1]['temperature'] == 0

    def test_max_tokens_configuration(self, ai_generator_with_mock):
        """Test that max_tokens is configured correctly"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Test")]

        ai_generator_with_mock.client.messages.create.return_value = mock_response

        ai_generator_with_mock.generate_response(
            query="Test",
            conversation_history=None,
            tools=None,
            tool_manager=None
        )

        call_args = ai_generator_with_mock.client.messages.create.call_args

        # Max tokens should be set
        assert 'max_tokens' in call_args[1]
        assert call_args[1]['max_tokens'] > 0


class TestAIGeneratorSystemPrompt:
    """Test system prompt configuration and behavior"""

    def test_system_prompt_exists(self):
        """Test that SYSTEM_PROMPT is defined"""
        assert hasattr(AIGenerator, 'SYSTEM_PROMPT')
        assert len(AIGenerator.SYSTEM_PROMPT) > 0

    def test_system_prompt_mentions_tools(self):
        """Test that system prompt mentions available tools"""
        prompt = AIGenerator.SYSTEM_PROMPT

        assert "search_course_content" in prompt or "tool" in prompt.lower()
        assert "get_course_outline" in prompt or "outline" in prompt.lower()

    def test_system_prompt_response_protocol(self):
        """Test that system prompt includes response guidelines"""
        prompt = AIGenerator.SYSTEM_PROMPT

        # Should have guidelines about when to use tools
        assert "course" in prompt.lower()

    def test_system_prompt_one_tool_call_limitation(self):
        """Test that system prompt includes the one tool call limitation"""
        prompt = AIGenerator.SYSTEM_PROMPT

        # This is a potential issue - system limits to one tool call
        assert "one tool call" in prompt.lower() or "One tool call" in prompt
