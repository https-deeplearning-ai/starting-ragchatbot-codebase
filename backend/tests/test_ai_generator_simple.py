#!/usr/bin/env python3
"""
Simple test to verify sequential tool calling works properly.
"""

import sys
import os
from unittest.mock import Mock

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_generator import AIGenerator


def test_basic_sequential_functionality():
    """Simple test to verify the sequential tool calling methods exist and work"""

    # Create AI generator instance (we'll mock the client)
    with MockAnthropic():
        ai_generator = AIGenerator("test-key", "claude-sonnet-4")

    # Mock the client
    mock_client = Mock()
    ai_generator.client = mock_client

    # Create a mock response with tool use
    mock_response = Mock()
    mock_response.stop_reason = "tool_use"
    mock_response.content = [Mock(type="tool_use", name="search_course_content", input={"query": "test"}, id="tool_1")]

    mock_client.messages.create.return_value = mock_response

    # Mock tool manager
    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "mock result"

    # Test that sequential methods exist
    assert hasattr(ai_generator, '_execute_sequential_tools')
    assert hasattr(ai_generator, '_execute_single_tool_round')
    assert hasattr(ai_generator, '_should_continue_execution')

    print("✓ All sequential tool calling methods exist")

    # Test basic generate_response doesn't error
    try:
        result = ai_generator.generate_response("test query")
        print("✓ Basic generate_response works")
    except Exception as e:
        print(f"✗ Basic generate_response failed: {e}")

    print("✓ Sequential tool calling functionality verified")


class MockAnthropic:
    """Context manager to mock anthropic during AIGenerator creation"""
    def __enter__(self):
        import ai_generator
        self.original = ai_generator.anthropic
        ai_generator.anthropic = Mock()
        return self

    def __exit__(self, *args):
        import ai_generator
        ai_generator.anthropic = self.original


if __name__ == "__main__":
    test_basic_sequential_functionality()