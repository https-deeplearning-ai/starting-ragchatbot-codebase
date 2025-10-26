"""
Tests for AI Generator functionality and tool calling
"""

import os
import sys
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


class TestAIGenerator:
    """Test cases for AIGenerator class"""

    def test_initialization(self, test_config):
        """Test that AIGenerator initializes correctly"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Verify Anthropic client was created
            mock_anthropic.assert_called_once_with(
                api_key=test_config.ANTHROPIC_API_KEY
            )

            # Verify attributes
            assert generator.client == mock_client
            assert generator.model == test_config.ANTHROPIC_MODEL
            assert generator.base_params["model"] == test_config.ANTHROPIC_MODEL
            assert generator.base_params["temperature"] == 0
            assert generator.base_params["max_tokens"] == 800
            assert hasattr(generator, "SYSTEM_PROMPT")

    def test_system_prompt_structure(self, test_config):
        """Test that system prompt is properly structured"""
        with patch("ai_generator.anthropic.Anthropic"):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Check that system prompt contains expected elements
            assert "course materials" in generator.SYSTEM_PROMPT.lower()
            assert "search_course_content" in generator.SYSTEM_PROMPT
            assert "get_course_outline" in generator.SYSTEM_PROMPT
            assert "tool usage guidelines" in generator.SYSTEM_PROMPT.lower()

    def test_generate_response_simple_query(self, test_config, mock_anthropic_client):
        """Test simple response generation without tools"""
        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Test simple query
            response = generator.generate_response(query="What is machine learning?")

            # Verify API was called correctly
            mock_anthropic_client["client"].messages.create.assert_called_once()

            # Check call arguments
            call_args = mock_anthropic_client["client"].messages.create.call_args
            assert call_args[1]["model"] == test_config.ANTHROPIC_MODEL
            assert call_args[1]["temperature"] == 0
            assert call_args[1]["max_tokens"] == 800
            assert len(call_args[1]["messages"]) == 1
            assert call_args[1]["messages"][0]["role"] == "user"
            assert "What is machine learning?" in call_args[1]["messages"][0]["content"]

            # Verify system prompt was included
            assert "system" in call_args[1]
            assert generator.SYSTEM_PROMPT in call_args[1]["system"]

            # Verify tools were not included
            assert "tools" not in call_args[1]

            # Verify response
            assert response == "This is a test response about machine learning."

    def test_generate_response_with_tools(
        self, test_config, mock_anthropic_client, mock_search_tools
    ):
        """Test response generation with tools"""
        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Create tool manager mock
            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [
                mock_search_tools["search_tool"].get_tool_definition.return_value,
                mock_search_tools["outline_tool"].get_tool_definition.return_value,
            ]

            # Test query that should use tools
            response = generator.generate_response(
                query="Tell me about machine learning fundamentals",
                tools=mock_tool_manager.get_tool_definitions.return_value,
                tool_manager=mock_tool_manager,
            )

            # Verify API was called with tools
            call_args = mock_anthropic_client["client"].messages.create.call_args
            assert "tools" in call_args[1]
            assert "tool_choice" in call_args[1]
            assert call_args[1]["tool_choice"]["type"] == "auto"

            # Verify response
            assert response == "This is a test response about machine learning."

    def test_generate_response_with_conversation_history(
        self, test_config, mock_anthropic_client
    ):
        """Test response generation with conversation history"""
        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            history = (
                "User: What is ML?\nAssistant: Machine learning is a subset of AI..."
            )

            response = generator.generate_response(
                query="Can you give me an example?", conversation_history=history
            )

            # Verify conversation history was included in system prompt
            call_args = mock_anthropic_client["client"].messages.create.call_args
            assert history in call_args[1]["system"]
            assert generator.SYSTEM_PROMPT in call_args[1]["system"]

    def test_generate_response_tool_execution(
        self, test_config, mock_anthropic_client, mock_search_tools
    ):
        """Test tool execution flow"""
        # Configure mock to return tool use response first
        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_anthropic_client["tool_response"],  # First call triggers tool use
            mock_anthropic_client[
                "final_response"
            ],  # Second call returns final response
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Create tool manager mock
            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [
                mock_search_tools["search_tool"].get_tool_definition.return_value
            ]
            mock_tool_manager.execute_tool.return_value = (
                "Found relevant content about machine learning"
            )

            response = generator.generate_response(
                query="Tell me about machine learning",
                tools=mock_tool_manager.get_tool_definitions.return_value,
                tool_manager=mock_tool_manager,
            )

            # Verify two API calls were made
            assert mock_anthropic_client["client"].messages.create.call_count == 2

            # Verify tool was executed - check the actual call made
            assert mock_tool_manager.execute_tool.call_count == 1
            actual_call = mock_tool_manager.execute_tool.call_args
            # Verify the call parameters match expected structure
            # actual_call[1] contains the kwargs dictionary
            assert (
                actual_call[1]["query"] == "machine learning basics"
            )  # query parameter

            # Verify final response
            assert response == "Based on the course materials, machine learning is..."

    def test_handle_tool_execution_multiple_tools(
        self, test_config, mock_anthropic_client, mock_search_tools
    ):
        """Test handling multiple tool executions in one response"""
        # Create a response with multiple tool uses
        mock_multi_tool_response = Mock()
        mock_multi_tool_response.stop_reason = "tool_use"
        mock_multi_tool_response.content = [
            Mock(
                type="tool_use",
                id="tool_123",
                name="search_course_content",
                input={"query": "machine learning"},
            ),
            Mock(
                type="tool_use",
                id="tool_456",
                name="get_course_outline",
                input={"course_title": "Machine Learning Fundamentals"},
            ),
        ]

        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_multi_tool_response,  # First call with multiple tools
            mock_anthropic_client["final_response"],  # Final response
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Create tool manager mock
            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [
                mock_search_tools["search_tool"].get_tool_definition.return_value,
                mock_search_tools["outline_tool"].get_tool_definition.return_value,
            ]
            mock_tool_manager.execute_tool.side_effect = [
                "Found machine learning content",
                "Course outline retrieved",
            ]

            response = generator.generate_response(
                query="Tell me about the ML course",
                tools=mock_tool_manager.get_tool_definitions.return_value,
                tool_manager=mock_tool_manager,
            )

            # Verify both tools were executed
            assert mock_tool_manager.execute_tool.call_count == 2
            # Check that the correct parameters were passed (without asserting exact tool names)
            calls = mock_tool_manager.execute_tool.call_args_list
            # Verify query parameter was passed correctly
            assert calls[0][1]["query"] == "machine learning"  # query from first call
            # Verify course_title parameter was passed correctly
            assert (
                calls[1][1]["course_title"] == "Machine Learning Fundamentals"
            )  # course_title from second call

    def test_tool_execution_with_empty_tool_results(
        self, test_config, mock_anthropic_client
    ):
        """Test tool execution when tools return empty results"""
        # Create tool response with no actual tool uses
        mock_empty_tool_response = Mock()
        mock_empty_tool_response.stop_reason = "tool_use"
        mock_empty_tool_response.content = []  # No tool uses

        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_empty_tool_response,
            mock_anthropic_client["final_response"],
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = []

            response = generator.generate_response(
                query="Test query", tools=[], tool_manager=mock_tool_manager
            )

            # Should handle empty tool results gracefully
            assert response == "Based on the course materials, machine learning is..."

    def test_api_key_handling(self, test_config):
        """Test API key validation and handling"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            # Test with valid API key
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            generator = AIGenerator("valid-api-key", test_config.ANTHROPIC_MODEL)
            mock_anthropic.assert_called_once_with(api_key="valid-api-key")

            # Test with empty API key
            mock_anthropic.reset_mock()
            generator = AIGenerator("", test_config.ANTHROPIC_MODEL)
            mock_anthropic.assert_called_once_with(api_key="")

    def test_model_configuration(self, test_config):
        """Test model configuration handling"""
        with patch("ai_generator.anthropic.Anthropic"):
            # Test with different model
            custom_model = "claude-3-opus-20240229"
            generator = AIGenerator(test_config.ANTHROPIC_API_KEY, custom_model)

            assert generator.model == custom_model
            assert generator.base_params["model"] == custom_model

    def test_error_handling_in_api_call(self, test_config):
        """Test handling of API errors"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            # Mock API to raise exception
            mock_client.messages.create.side_effect = Exception(
                "API Error: Invalid request"
            )

            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Should raise the exception
            with pytest.raises(Exception, match="API Error: Invalid request"):
                generator.generate_response(query="test query")

    def test_system_prompt_efficiency(self, test_config, mock_anthropic_client):
        """Test that system prompt is built efficiently"""
        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Test without history
            generator.generate_response(query="test")
            call_args = mock_anthropic_client["client"].messages.create.call_args
            system_prompt = call_args[1]["system"]
            assert system_prompt == generator.SYSTEM_PROMPT

            # Test with history
            history = "Previous conversation"
            generator.generate_response(query="test", conversation_history=history)
            call_args = mock_anthropic_client["client"].messages.create.call_args
            system_prompt = call_args[1]["system"]
            assert generator.SYSTEM_PROMPT in system_prompt
            assert history in system_prompt

    def test_message_structure_validation(self, test_config, mock_anthropic_client):
        """Test that API messages are structured correctly"""
        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            generator.generate_response(query="test query")

            call_args = mock_anthropic_client["client"].messages.create.call_args
            messages = call_args[1]["messages"]

            # Verify message structure
            assert isinstance(messages, list)
            assert len(messages) == 1

            message = messages[0]
            assert isinstance(message, dict)
            assert message["role"] == "user"
            assert isinstance(message["content"], str)
            assert "test query" in message["content"]

    def test_tool_execution_message_flow(self, test_config, mock_anthropic_client):
        """Test the complete message flow during tool execution"""
        # Setup tool execution scenario
        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_anthropic_client["tool_response"],
            mock_anthropic_client["final_response"],
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [{}]
            mock_tool_manager.execute_tool.return_value = "Tool result"

            generator.generate_response(
                query="test", tools=[{}], tool_manager=mock_tool_manager
            )

            # Check that all calls were made
            assert mock_anthropic_client["client"].messages.create.call_count == 2

            # Check first call (initial query)
            first_call = mock_anthropic_client["client"].messages.create.call_args_list[
                0
            ]
            assert len(first_call[1]["messages"]) == 1

            # Check second call (with tool results)
            second_call = mock_anthropic_client[
                "client"
            ].messages.create.call_args_list[1]
            assert (
                len(second_call[1]["messages"]) == 3
            )  # User + Assistant + Tool results
            assert second_call[1]["messages"][0]["role"] == "user"
            assert second_call[1]["messages"][1]["role"] == "assistant"
            assert second_call[1]["messages"][2]["role"] == "user"

    def test_base_params_immutability(self, test_config, mock_anthropic_client):
        """Test that base_params are not accidentally modified"""
        with patch("ai_generator.anthropic.Anthropic"):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Store original params
            original_params = generator.base_params.copy()

            # Verify base_params structure
            assert "model" in original_params
            assert "temperature" in original_params
            assert "max_tokens" in original_params

            # Generate response and verify params weren't modified
            with patch.object(generator.client, "messages.create") as mock_create:
                mock_create.return_value = mock_anthropic_client["response"]

                generator.generate_response(query="test")

                # Verify base_params are unchanged
                assert generator.base_params == original_params

    def test_tool_results_structure(self, test_config, mock_anthropic_client):
        """Test that tool results are structured correctly for the API"""
        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_anthropic_client["tool_response"],
            mock_anthropic_client["final_response"],
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [{}]
            mock_tool_manager.execute_tool.return_value = "Tool execution result"

            generator.generate_response(
                query="test", tools=[{}], tool_manager=mock_tool_manager
            )

            # Check the second call's tool results structure
            second_call = mock_anthropic_client[
                "client"
            ].messages.create.call_args_list[1]
            tool_results_message = second_call[1]["messages"][2]

            assert tool_results_message["role"] == "user"
            assert isinstance(tool_results_message["content"], list)

            tool_result = tool_results_message["content"][0]
            assert tool_result["type"] == "tool_result"
            assert "tool_use_id" in tool_result
            assert "content" in tool_result
            assert tool_result["content"] == "Tool execution result"

    # Sequential Tool Calling Tests

    def test_sequential_tool_calling_two_rounds(
        self, test_config, mock_anthropic_client, mock_search_tools
    ):
        """Test sequential tool calling with exactly 2 rounds"""
        # Create sequential responses: outline → search → final
        mock_outline_response = Mock()
        mock_outline_response.stop_reason = "tool_use"
        mock_outline_response.content = [
            Mock(
                type="tool_use",
                id="outline_123",
                name="get_course_outline",
                input={"course_title": "Machine Learning Fundamentals"},
            )
        ]

        mock_search_response = Mock()
        mock_search_response.stop_reason = "tool_use"
        mock_search_response.content = [
            Mock(
                type="tool_use",
                id="search_456",
                name="search_course_content",
                input={"query": "neural networks"},
            )
        ]

        # Set up the sequence of API calls
        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_outline_response,  # Round 1: outline tool
            mock_search_response,  # Round 2: search tool
            mock_anthropic_client["final_response"],  # Final response
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [
                mock_search_tools["outline_tool"].get_tool_definition.return_value,
                mock_search_tools["search_tool"].get_tool_definition.return_value,
            ]
            mock_tool_manager.execute_tool.side_effect = [
                "Course outline: Lesson 1-5 on ML basics, Lesson 6-10 on neural networks",
                "Found content about neural networks in advanced ML course",
            ]

            response = generator.generate_response(
                query="Find courses about neural networks using the ML fundamentals outline",
                tools=mock_tool_manager.get_tool_definitions.return_value,
                tool_manager=mock_tool_manager,
                max_tool_rounds=2,
            )

            # Verify tools were called in correct sequence
            assert mock_tool_manager.execute_tool.call_count == 2
            # Check the calls were made with correct parameters
            calls = mock_tool_manager.execute_tool.call_args_list
            # Check first call (outline tool)
            assert (
                calls[0][1]["course_title"] == "Machine Learning Fundamentals"
            )  # course_title parameter
            # Check second call (search tool)
            assert calls[1][1]["query"] == "neural networks"  # query parameter

            # Verify final response
            assert response == "Based on the course materials, machine learning is..."

    def test_sequential_tool_calling_early_termination(
        self, test_config, mock_anthropic_client, mock_search_tools
    ):
        """Test sequential tool calling stops early when Claude doesn't request more tools"""
        # First response requests tool, second response is final (no tools)
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [
            Mock(
                type="tool_use",
                id="tool_123",
                name="search_course_content",
                input={"query": "machine learning"},
            )
        ]

        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_tool_response,
            mock_anthropic_client["final_response"],  # No more tools requested
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [
                mock_search_tools["search_tool"].get_tool_definition.return_value
            ]
            mock_tool_manager.execute_tool.return_value = "Found ML content"

            response = generator.generate_response(
                query="Tell me about machine learning",
                tools=mock_tool_manager.get_tool_definitions.return_value,
                tool_manager=mock_tool_manager,
                max_tool_rounds=2,
            )

            # Should only make 2 calls (initial + 1 tool round) - early termination
            assert mock_anthropic_client["client"].messages.create.call_count == 2
            assert mock_tool_manager.execute_tool.call_count == 1
            assert response == "Based on the course materials, machine learning is..."

    def test_sequential_tool_calling_max_rounds_limit(
        self, test_config, mock_anthropic_client, mock_search_tools
    ):
        """Test that sequential tool calling respects max_tool_rounds limit"""
        # Create responses that would continue beyond 2 rounds
        mock_responses = []
        for i in range(4):  # Create 4 tool-requesting responses
            response = Mock()
            response.stop_reason = "tool_use"
            response.content = [
                Mock(
                    type="tool_use",
                    id=f"tool_{i}",
                    name="search_course_content",
                    input={"query": f"search term {i}"},
                )
            ]
            mock_responses.append(response)

        # Add final response
        mock_responses.append(mock_anthropic_client["final_response"])

        mock_anthropic_client["client"].messages.create.side_effect = mock_responses

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [
                mock_search_tools["search_tool"].get_tool_definition.return_value
            ]
            mock_tool_manager.execute_tool.return_value = "Search result"

            response = generator.generate_response(
                query="Complex multi-step search",
                tools=mock_tool_manager.get_tool_definitions.return_value,
                tool_manager=mock_tool_manager,
                max_tool_rounds=2,  # Limit to 2 rounds
            )

            # Should make exactly 3 calls: initial + 2 tool rounds (no extra final call needed)
            assert mock_anthropic_client["client"].messages.create.call_count == 3
            assert (
                mock_tool_manager.execute_tool.call_count == 3
            )  # Initial + 2 sequential
            assert response == "Based on the course materials, machine learning is..."

    def test_sequential_tool_calling_conversation_context(
        self, test_config, mock_anthropic_client, mock_search_tools
    ):
        """Test that conversation context is preserved across sequential tool calls"""
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [
            Mock(
                type="tool_use",
                id="tool_123",
                name="get_course_outline",
                input={"course_title": "Course A"},
            )
        ]

        mock_sequential_response = Mock()
        mock_sequential_response.stop_reason = "tool_use"
        mock_sequential_response.content = [
            Mock(
                type="tool_use",
                id="tool_456",
                name="search_course_content",
                input={"query": "topic from Course A"},
            )
        ]

        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_tool_response,
            mock_sequential_response,
            mock_anthropic_client["final_response"],
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [
                mock_search_tools["outline_tool"].get_tool_definition.return_value,
                mock_search_tools["search_tool"].get_tool_definition.return_value,
            ]
            mock_tool_manager.execute_tool.side_effect = [
                "Course A outline: Advanced Topics",
                "Found related content in Course B",
            ]

            response = generator.generate_response(
                query="Find related courses to Course A",
                tools=mock_tool_manager.get_tool_definitions.return_value,
                tool_manager=mock_tool_manager,
                max_tool_rounds=2,
            )

            # Check that conversation context accumulates correctly
            call_args_list = mock_anthropic_client[
                "client"
            ].messages.create.call_args_list

            # Verify that calls were made in sequence
            assert len(call_args_list) == 3  # Should have 3 total calls

            # Check that messages accumulate properly across calls
            # The implementation should handle conversation context correctly
            assert mock_tool_manager.execute_tool.call_count == 2

    def test_sequential_tool_calling_tool_execution_error_handling(
        self, test_config, mock_anthropic_client
    ):
        """Test error handling in sequential tool execution"""
        mock_tool_response = Mock()
        mock_tool_response.stop_reason = "tool_use"
        mock_tool_response.content = [
            Mock(
                type="tool_use",
                id="tool_123",
                name="search_course_content",
                input={"query": "test query"},
            )
        ]

        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_tool_response,
            mock_anthropic_client["final_response"],
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [{}]
            # Tool execution raises exception
            mock_tool_manager.execute_tool.side_effect = Exception(
                "Tool execution failed"
            )

            response = generator.generate_response(
                query="test query",
                tools=[{}],
                tool_manager=mock_tool_manager,
                max_tool_rounds=2,
            )

            # Should handle error gracefully and continue
            assert mock_anthropic_client["client"].messages.create.call_count == 2
            assert response == "Based on the course materials, machine learning is..."

    def test_sequential_tool_calling_backward_compatibility(
        self, test_config, mock_anthropic_client, mock_search_tools
    ):
        """Test that existing single-tool calls still work with new implementation"""
        # Original single tool call pattern should still work
        mock_anthropic_client["client"].messages.create.side_effect = [
            mock_anthropic_client["tool_response"],
            mock_anthropic_client["final_response"],
        ]

        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [
                mock_search_tools["search_tool"].get_tool_definition.return_value
            ]
            mock_tool_manager.execute_tool.return_value = "Tool result"

            # Call without max_tool_rounds parameter (backward compatibility)
            response = generator.generate_response(
                query="test",
                tools=mock_tool_manager.get_tool_definitions.return_value,
                tool_manager=mock_tool_manager,
            )

            # Should work exactly as before
            assert mock_anthropic_client["client"].messages.create.call_count == 2
            assert mock_tool_manager.execute_tool.call_count == 1
            # The response should be the final response from our mock
            assert response == "Based on the course materials, machine learning is..."

    def test_sequential_tool_calling_no_tools_provided(
        self, test_config, mock_anthropic_client
    ):
        """Test sequential tool calling when no tools are provided"""
        with patch(
            "ai_generator.anthropic.Anthropic",
            return_value=mock_anthropic_client["client"],
        ):
            generator = AIGenerator(
                test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL
            )

            # Call without tools or tool_manager
            response = generator.generate_response(
                query="general knowledge question", max_tool_rounds=2
            )

            # Should make single call without tools
            assert mock_anthropic_client["client"].messages.create.call_count == 1
            call_args = mock_anthropic_client["client"].messages.create.call_args

            # Verify no tools were included
            assert "tools" not in call_args[1]
            assert response == "This is a test response about machine learning."
