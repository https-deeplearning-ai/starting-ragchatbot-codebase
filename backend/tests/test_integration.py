#!/usr/bin/env python3
"""
Integration test for sequential tool calling with the RAG system.
"""

import sys
import os
from unittest.mock import Mock, patch

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ai_generator import AIGenerator
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool


def test_ai_generator_integration():
    """Test that AIGenerator integrates properly with existing components"""

    print("Testing AI Generator integration with existing RAG system...")

    # Test 1: Verify system prompt updates
    ai_gen = AIGenerator("test-key", "test-model")

    # Check that system prompt includes sequential capabilities
    assert "Multiple tool rounds supported" in ai_gen.SYSTEM_PROMPT
    assert "up to 2 sequential rounds" in ai_gen.SYSTEM_PROMPT
    assert "Sequential reasoning" in ai_gen.SYSTEM_PROMPT
    print("✓ System prompt properly updated for sequential tool calling")

    # Test 2: Verify new methods exist
    assert hasattr(ai_gen, '_execute_sequential_tools')
    assert hasattr(ai_gen, '_execute_single_tool_round')
    assert hasattr(ai_gen, '_should_continue_execution')
    assert hasattr(ai_gen, '_build_enhanced_system_prompt')
    assert hasattr(ai_gen, '_handle_tool_error')
    assert hasattr(ai_gen, '_extract_final_response')
    print("✓ All new sequential tool methods exist")

    # Test 3: Verify tool manager compatibility
    tool_manager = ToolManager()

    # Mock vector store for tools
    mock_vector_store = Mock()
    mock_vector_store.search.return_value = Mock(error=None, is_empty=lambda: False,
                                               documents=["test doc"], metadata=[{"course_title": "Test"}])
    mock_vector_store.get_all_courses_metadata.return_value = [{"title": "Test Course"}]

    search_tool = CourseSearchTool(mock_vector_store)
    outline_tool = CourseOutlineTool(mock_vector_store)

    tool_manager.register_tool(search_tool)
    tool_manager.register_tool(outline_tool)

    # Verify tools work with manager
    tool_defs = tool_manager.get_tool_definitions()
    assert len(tool_defs) == 2
    assert any(tool['name'] == 'search_course_content' for tool in tool_defs)
    assert any(tool['name'] == 'get_course_outline' for tool in tool_defs)
    print("✓ Tool manager integration works")

    # Test 4: Verify sequential termination logic
    mock_response_no_tools = Mock()
    mock_response_no_tools.content = [Mock(type="text")]
    mock_response_no_tools.stop_reason = "end_turn"

    mock_response_with_tools = Mock()
    mock_response_with_tools.content = [Mock(type="tool_use")]
    mock_response_with_tools.stop_reason = "tool_use"

    # Test continuation logic
    assert not ai_gen._should_continue_execution(mock_response_no_tools, 1, 2)  # No tools = stop
    assert ai_gen._should_continue_execution(mock_response_with_tools, 1, 2)   # Has tools = continue
    assert not ai_gen._should_continue_execution(mock_response_with_tools, 2, 2)  # Max rounds = stop
    print("✓ Sequential termination logic works correctly")

    # Test 5: Verify backward compatibility
    # The generate_response method should still work for single-round scenarios
    with patch.object(ai_gen, 'client') as mock_client:
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Direct response")]
        mock_client.messages.create.return_value = mock_response

        result = ai_gen.generate_response("Simple query")
        assert result == "Direct response"
        assert mock_client.messages.create.call_count == 1
    print("✓ Backward compatibility maintained for simple queries")

    print("\n✅ All integration tests passed! Sequential tool calling is ready.")
    return True


def test_system_prompt_enhancements():
    """Test that system prompt enhancements work correctly"""

    ai_gen = AIGenerator("test-key", "test-model")
    base_prompt = "Base prompt content"

    # Test round 1 - should return base prompt
    enhanced_1 = ai_gen._build_enhanced_system_prompt(base_prompt, 1)
    assert enhanced_1 == base_prompt

    # Test round 2 - should add context
    enhanced_2 = ai_gen._build_enhanced_system_prompt(base_prompt, 2)
    assert "Round 2/2" in enhanced_2
    assert base_prompt in enhanced_2

    print("✓ System prompt enhancement logic works correctly")
    return True


if __name__ == "__main__":
    try:
        test_ai_generator_integration()
        test_system_prompt_enhancements()
        print("\n🎉 All integration tests completed successfully!")
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)