#!/usr/bin/env python3
"""
Comprehensive test suite for AIGenerator with sequential tool calling.
Focuses on external behavior testing rather than internal state validation.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_generator import AIGenerator


class MockAnthropicResponse:
    """Mock Anthropic API response for testing"""

    def __init__(self, content: List[Dict], stop_reason: str = "end_turn"):
        self.content = []
        self.stop_reason = stop_reason

        # Convert content to mock objects with proper attributes
        for item in content:
            mock_content = Mock()
            if item.get("type") == "text":
                mock_content.type = "text"
                mock_content.text = item["text"]
            elif item.get("type") == "tool_use":
                mock_content.type = "tool_use"
                mock_content.name = item["name"]
                mock_content.input = item["input"]
                mock_content.id = item.get("id", f"tool_{item['name']}_123")
            self.content.append(mock_content)


class MockToolManager:
    """Mock tool manager for testing"""

    def __init__(self):
        self.executed_tools = []
        self.tool_results = {}

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Track tool execution and return mock results"""
        self.executed_tools.append({"name": tool_name, "params": kwargs})

        # Return mock results based on tool
        if tool_name == "get_course_outline":
            return f"**Course: {kwargs.get('course_title', 'Test Course')}**\n1. Lesson 1: Introduction\n2. Lesson 2: Advanced Topics"
        elif tool_name == "search_course_content":
            return f"[Test Course - Lesson 1]\nContent about {kwargs.get('query', 'test topic')}"

        return f"Mock result for {tool_name}"

    def get_executed_tools(self) -> List[Dict]:
        """Get list of executed tools for verification"""
        return self.executed_tools.copy()

    def reset(self):
        """Reset for next test"""
        self.executed_tools.clear()


class TestAIGeneratorSequentialTools:
    """Test suite for sequential tool calling functionality"""

    def setup_method(self):
        """Setup for each test method"""
        with patch('ai_generator.anthropic.Anthropic'):
            self.ai_generator = AIGenerator("test-api-key", "claude-sonnet-4")
        self.mock_tool_manager = MockToolManager()
        self.mock_tools = [
            {
                "name": "get_course_outline",
                "description": "Get course outline",
                "input_schema": {"type": "object", "properties": {"course_title": {"type": "string"}}}
            },
            {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}}
            }
        ]

    def test_single_round_tool_calling_backward_compatibility(self):
        """Test that single-round tool calling still works (backward compatibility)"""
        # Setup mock client
        mock_client = Mock()
        self.ai_generator.client = mock_client

        # Mock sequence: tool use -> tool result -> final response
        tool_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "search_course_content", "input": {"query": "test"}}
        ], stop_reason="tool_use")

        final_response = MockAnthropicResponse([
            {"type": "text", "text": "Based on the search results, here's the answer."}
        ])

        mock_client.messages.create.side_effect = [tool_response, final_response]

        # Execute
        result = self.ai_generator.generate_response(
            query="What is the test topic?",
            tools=self.mock_tools,
            tool_manager=self.mock_tool_manager
        )

        # Verify external behavior
        assert result == "Based on the search results, here's the answer."
        assert len(self.mock_tool_manager.get_executed_tools()) == 1
        assert self.mock_tool_manager.get_executed_tools()[0]["name"] == "search_course_content"
        assert mock_client.messages.create.call_count == 2  # Initial + final

    def test_double_round_tool_calling_complex_query(self):
        """Test double round tool calling for complex multi-step queries"""
        # Setup mock client
        mock_client = Mock()
        self.ai_generator.client = mock_client

        # Mock sequence: Round 1 - get outline -> Round 2 - search content -> final response
        round1_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "get_course_outline", "input": {"course_title": "MCP Course"}}
        ], stop_reason="tool_use")

        round2_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "search_course_content", "input": {"query": "Advanced Topics"}}
        ], stop_reason="tool_use")

        final_response = MockAnthropicResponse([
            {"type": "text", "text": "Based on the course outline and search results, here's the comprehensive answer."}
        ])

        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]

        # Execute
        result = self.ai_generator.generate_response(
            query="Search for content related to lesson 2 of MCP Course",
            tools=self.mock_tools,
            tool_manager=self.mock_tool_manager
        )

        # Verify external behavior
        assert result == "Based on the course outline and search results, here's the comprehensive answer."
        executed_tools = self.mock_tool_manager.get_executed_tools()
        assert len(executed_tools) == 2
        assert executed_tools[0]["name"] == "get_course_outline"
        assert executed_tools[1]["name"] == "search_course_content"
        assert mock_client.messages.create.call_count == 3  # Round1 + Round2 + Final

    def test_max_rounds_termination(self):
        """Test that execution terminates after maximum 2 rounds"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock sequence: Round 1 -> Round 2 -> would continue but should stop
        round1_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "get_course_outline", "input": {"course_title": "Test"}}
        ], stop_reason="tool_use")

        round2_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "search_course_content", "input": {"query": "test"}}
        ], stop_reason="tool_use")

        final_response = MockAnthropicResponse([
            {"type": "text", "text": "Final answer after 2 rounds."}
        ])

        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]

        # Execute
        result = self.ai_generator.generate_response(
            query="Complex query requiring multiple steps",
            tools=self.mock_tools,
            tool_manager=self.mock_tool_manager
        )

        # Verify termination after 2 rounds
        assert result == "Final answer after 2 rounds."
        assert len(self.mock_tool_manager.get_executed_tools()) == 2
        assert mock_client.messages.create.call_count == 3  # Exactly 3 calls (2 rounds + final)

    @patch('ai_generator.anthropic.Anthropic')
    def test_early_termination_no_tool_use(self, mock_anthropic_class):
        """Test termination when response has no tool_use blocks"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock sequence: Round 1 with tool -> Round 2 without tool (should terminate)
        round1_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "search_course_content", "input": {"query": "test"}}
        ], stop_reason="tool_use")

        round2_response = MockAnthropicResponse([
            {"type": "text", "text": "I have enough information to answer your question."}
        ])  # No tool_use, should terminate

        mock_client.messages.create.side_effect = [round1_response, round2_response]

        # Execute
        result = self.ai_generator.generate_response(
            query="Simple query that completes in round 2",
            tools=self.mock_tools,
            tool_manager=self.mock_tool_manager
        )

        # Verify early termination
        assert result == "I have enough information to answer your question."
        assert len(self.mock_tool_manager.get_executed_tools()) == 1
        assert mock_client.messages.create.call_count == 2  # Only 2 calls

    @patch('ai_generator.anthropic.Anthropic')
    def test_tool_execution_error_handling(self, mock_anthropic_class):
        """Test graceful handling of tool execution errors"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool manager that raises exception
        error_tool_manager = Mock()
        error_tool_manager.execute_tool.side_effect = Exception("Tool execution failed")

        tool_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "search_course_content", "input": {"query": "test"}}
        ], stop_reason="tool_use")

        final_response = MockAnthropicResponse([
            {"type": "text", "text": "I encountered an error but here's what I can tell you."}
        ])

        mock_client.messages.create.side_effect = [tool_response, final_response]

        # Execute
        result = self.ai_generator.generate_response(
            query="Query that will cause tool error",
            tools=self.mock_tools,
            tool_manager=error_tool_manager
        )

        # Should handle error gracefully
        assert result == "I encountered an error but here's what I can tell you."
        assert mock_client.messages.create.call_count == 2

    @patch('ai_generator.anthropic.Anthropic')
    def test_conversation_context_preservation(self, mock_anthropic_class):
        """Test that conversation context is preserved between rounds"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        conversation_history = "Previous conversation:\nUser: What courses are available?\nAssistant: Here are the available courses..."

        # Mock two-round sequence
        round1_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "get_course_outline", "input": {"course_title": "Test"}}
        ], stop_reason="tool_use")

        final_response = MockAnthropicResponse([
            {"type": "text", "text": "Based on our previous conversation and the outline..."}
        ])

        mock_client.messages.create.side_effect = [round1_response, final_response]

        # Execute with conversation history
        result = self.ai_generator.generate_response(
            query="Follow-up question about the course",
            conversation_history=conversation_history,
            tools=self.mock_tools,
            tool_manager=self.mock_tool_manager
        )

        # Verify context preservation by checking API calls
        api_calls = mock_client.messages.create.call_args_list

        # First call should include conversation history in system prompt
        first_call_system = api_calls[0][1]["system"]
        assert "Previous conversation:" in first_call_system

        # Second call should preserve message context
        second_call_messages = api_calls[1][1]["messages"]
        assert len(second_call_messages) >= 3  # Original query + AI response + tool results

    @patch('ai_generator.anthropic.Anthropic')
    def test_no_tools_provided_fallback(self, mock_anthropic_class):
        """Test behavior when no tools are provided"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        direct_response = MockAnthropicResponse([
            {"type": "text", "text": "I can answer based on my general knowledge."}
        ])

        mock_client.messages.create.return_value = direct_response

        # Execute without tools
        result = self.ai_generator.generate_response(
            query="General knowledge question"
        )

        # Should work normally without tools
        assert result == "I can answer based on my general knowledge."
        assert mock_client.messages.create.call_count == 1
        assert len(self.mock_tool_manager.get_executed_tools()) == 0

    @patch('ai_generator.anthropic.Anthropic')
    def test_mixed_tool_sequence_outline_then_search(self, mock_anthropic_class):
        """Test mixed tool sequence: outline tool then search tool"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Create specific mock tool manager for this test
        mixed_tool_manager = Mock()
        executed_tools = []

        def mock_execute_tool(tool_name, **kwargs):
            executed_tools.append({"name": tool_name, "params": kwargs})
            if tool_name == "get_course_outline":
                return "**Course: Python Basics**\n1. Lesson 1: Variables\n2. Lesson 2: Functions"
            elif tool_name == "search_course_content":
                return "[Python Basics - Lesson 2]\nFunction definition and usage examples"
            return "Mock result"

        mixed_tool_manager.execute_tool.side_effect = mock_execute_tool

        # Round 1: Get outline
        round1_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "get_course_outline", "input": {"course_title": "Python Basics"}}
        ], stop_reason="tool_use")

        # Round 2: Search specific content
        round2_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "search_course_content", "input": {"query": "functions", "course_name": "Python Basics"}}
        ], stop_reason="tool_use")

        final_response = MockAnthropicResponse([
            {"type": "text", "text": "Based on the course outline, lesson 2 covers functions. Here are the details..."}
        ])

        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]

        # Execute
        result = self.ai_generator.generate_response(
            query="Tell me about functions in the Python Basics course",
            tools=self.mock_tools,
            tool_manager=mixed_tool_manager
        )

        # Verify the sequence
        assert result == "Based on the course outline, lesson 2 covers functions. Here are the details..."
        assert len(executed_tools) == 2
        assert executed_tools[0]["name"] == "get_course_outline"
        assert executed_tools[1]["name"] == "search_course_content"
        assert mock_client.messages.create.call_count == 3


class TestAIGeneratorIntegration:
    """Integration tests for AI Generator with real-like scenarios"""

    def setup_method(self):
        """Setup for integration tests"""
        self.ai_generator = AIGenerator("test-api-key", "claude-sonnet-4")

    @patch('ai_generator.anthropic.Anthropic')
    def test_realistic_multi_step_query_flow(self, mock_anthropic_class):
        """Test realistic multi-step query: 'Find content similar to lesson 4 of course X'"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Create realistic tool manager
        realistic_tool_manager = Mock()
        tool_calls = []

        def realistic_execute_tool(tool_name, **kwargs):
            tool_calls.append({"tool": tool_name, "params": kwargs})

            if tool_name == "get_course_outline" and "MCP" in kwargs.get("course_title", ""):
                return """**Course: Model Context Protocol (MCP)**
Course Link: https://example.com/mcp-course

**Lessons (5 total):**
1. [Introduction to MCP](https://example.com/lesson1)
2. [Basic Concepts](https://example.com/lesson2)
3. [Implementation Details](https://example.com/lesson3)
4. [Authentication & Security](https://example.com/lesson4)
5. [Advanced Topics](https://example.com/lesson5)"""

            elif tool_name == "search_course_content" and "authentication" in kwargs.get("query", "").lower():
                return """[Security Fundamentals - Lesson 2]
Authentication methods and security protocols for distributed systems.

[Advanced Security - Lesson 1]
OAuth, JWT tokens, and secure authentication patterns in modern applications."""

            return "No results found"

        realistic_tool_manager.execute_tool.side_effect = realistic_execute_tool

        # Mock API responses
        round1_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "get_course_outline", "input": {"course_title": "MCP"}}
        ], stop_reason="tool_use")

        round2_response = MockAnthropicResponse([
            {"type": "tool_use", "name": "search_course_content", "input": {"query": "authentication security"}}
        ], stop_reason="tool_use")

        final_response = MockAnthropicResponse([
            {"type": "text", "text": "Based on the MCP course outline, lesson 4 covers 'Authentication & Security'. I found similar content in other courses covering authentication methods and security protocols."}
        ])

        mock_client.messages.create.side_effect = [round1_response, round2_response, final_response]

        # Execute realistic query
        result = self.ai_generator.generate_response(
            query="Find courses that discuss similar topics to lesson 4 of the MCP course",
            tools=[
                {"name": "get_course_outline", "description": "Get course outline"},
                {"name": "search_course_content", "description": "Search course content"}
            ],
            tool_manager=realistic_tool_manager
        )

        # Verify realistic behavior
        assert "Authentication & Security" in result or "authentication" in result.lower()
        assert len(tool_calls) == 2
        assert tool_calls[0]["tool"] == "get_course_outline"
        assert tool_calls[1]["tool"] == "search_course_content"
        assert "authentication" in tool_calls[1]["params"]["query"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])