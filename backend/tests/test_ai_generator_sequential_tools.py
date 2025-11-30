"""
Tests for AIGenerator sequential tool calling functionality
Tests the ability to make up to 2 sequential tool calls with reasoning between calls
"""

from unittest.mock import Mock, patch

import pytest
from ai_generator import AIGenerator
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestAIGeneratorSequentialTools:
    """Test suite for sequential tool calling (up to 2 rounds)"""

    @pytest.fixture
    def ai_generator(self):
        """Create AIGenerator instance with test configuration"""
        return AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

    @pytest.fixture
    def tool_manager(self, mock_vector_store):
        """Create ToolManager with CourseSearchTool"""
        manager = ToolManager()
        search_tool = CourseSearchTool(mock_vector_store)
        manager.register_tool(search_tool)
        return manager

    def test_zero_rounds_general_knowledge(self, ai_generator, tool_manager):
        """Test: No tools needed (0 rounds) - general knowledge question"""
        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # Direct response without tool use
            response = Mock()
            response.stop_reason = "end_turn"
            response.content = [Mock(text="2 + 2 = 4")]
            mock_create.return_value = response

            result = ai_generator.generate_response(
                query="What is 2 + 2?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            assert result == "2 + 2 = 4"
            assert mock_create.call_count == 1  # Only initial call

            # Verify tools were offered but not used
            first_call = mock_create.call_args_list[0]
            assert "tools" in first_call.kwargs

    def test_one_round_single_search(
        self, ai_generator, tool_manager, mock_vector_store
    ):
        """Test: Single tool call (1 round) - standard search"""
        # Setup mock search result
        mock_vector_store.search.return_value = SearchResults(
            documents=["Python basics content"],
            metadata=[{"course_title": "Python 101", "lesson_number": 1}],
            distances=[0.1],
            links=["http://example.com"],
            error=None,
        )

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # First call: tool use
            tool_response = Mock()
            tool_response.stop_reason = "tool_use"
            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "tool_1"
            tool_block.input = {"query": "Python basics", "lesson_number": 1}
            tool_response.content = [tool_block]

            # Second call: final answer (no more tools needed)
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Python is a programming language")]

            mock_create.side_effect = [tool_response, final_response]

            result = ai_generator.generate_response(
                query="What are Python basics in lesson 1?",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            assert result == "Python is a programming language"
            assert mock_create.call_count == 2
            assert mock_vector_store.search.call_count == 1

            # Verify second call has tools (we're only on round 1 < MAX_TOOL_ROUNDS)
            second_call = mock_create.call_args_list[1]
            assert "tools" in second_call.kwargs

    def test_two_rounds_sequential_searches(
        self, ai_generator, tool_manager, mock_vector_store
    ):
        """Test: Two sequential tool calls (2 rounds) - compare lessons"""
        # Setup mock search results for two different calls
        mock_vector_store.search.side_effect = [
            SearchResults(
                documents=["Lesson 1 covers Python introduction"],
                metadata=[{"course_title": "Python 101", "lesson_number": 1}],
                distances=[0.1],
                links=["http://example.com/lesson1"],
                error=None,
            ),
            SearchResults(
                documents=["Lesson 5 covers advanced decorators"],
                metadata=[{"course_title": "Python 101", "lesson_number": 5}],
                distances=[0.1],
                links=["http://example.com/lesson5"],
                error=None,
            ),
        ]

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # First call: tool use for lesson 1
            tool_response_1 = Mock()
            tool_response_1.stop_reason = "tool_use"
            tool_block_1 = Mock()
            tool_block_1.type = "tool_use"
            tool_block_1.name = "search_course_content"
            tool_block_1.id = "tool_1"
            tool_block_1.input = {"query": "lesson 1", "lesson_number": 1}
            tool_response_1.content = [tool_block_1]

            # Second call: tool use for lesson 5
            tool_response_2 = Mock()
            tool_response_2.stop_reason = "tool_use"
            tool_block_2 = Mock()
            tool_block_2.type = "tool_use"
            tool_block_2.name = "search_course_content"
            tool_block_2.id = "tool_2"
            tool_block_2.input = {"query": "lesson 5", "lesson_number": 5}
            tool_response_2.content = [tool_block_2]

            # Third call: final comparison
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [
                Mock(text="Lesson 1 covers basics, lesson 5 covers advanced topics")
            ]

            mock_create.side_effect = [tool_response_1, tool_response_2, final_response]

            result = ai_generator.generate_response(
                query="Compare lesson 1 and lesson 5",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            assert result == "Lesson 1 covers basics, lesson 5 covers advanced topics"
            assert mock_create.call_count == 3  # Initial + 2 tool rounds
            assert mock_vector_store.search.call_count == 2

            # Verify API call progression
            # Call 1: Should have tools
            assert "tools" in mock_create.call_args_list[0].kwargs

            # Call 2: Should have tools (round 1 < max 2)
            assert "tools" in mock_create.call_args_list[1].kwargs

            # Call 3: Should NOT have tools (round 2 == max 2)
            assert "tools" not in mock_create.call_args_list[2].kwargs

            # Verify message structure in final call
            final_call_messages = mock_create.call_args_list[2].kwargs["messages"]
            assert len(final_call_messages) == 5  # user, asst, user, asst, user

    def test_tool_limit_enforced(self, ai_generator, tool_manager, mock_vector_store):
        """Test: Claude wants 3rd tool but hits limit - must answer with 2"""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test", "lesson_number": 1}],
            distances=[0.1],
            links=["http://test.com"],
            error=None,
        )

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # Simulate Claude wanting to keep using tools
            tool_response_1 = Mock()
            tool_response_1.stop_reason = "tool_use"
            tool_block_1 = Mock()
            tool_block_1.type = "tool_use"
            tool_block_1.name = "search_course_content"
            tool_block_1.id = "tool_1"
            tool_block_1.input = {"query": "search 1"}
            tool_response_1.content = [tool_block_1]

            tool_response_2 = Mock()
            tool_response_2.stop_reason = "tool_use"
            tool_block_2 = Mock()
            tool_block_2.type = "tool_use"
            tool_block_2.name = "search_course_content"
            tool_block_2.id = "tool_2"
            tool_block_2.input = {"query": "search 2"}
            tool_response_2.content = [tool_block_2]

            # Final response (no choice, tools removed)
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Final answer with 2 tools")]

            mock_create.side_effect = [tool_response_1, tool_response_2, final_response]

            result = ai_generator.generate_response(
                query="Complex query",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            # Should stop at 2 tools
            assert mock_create.call_count == 3
            assert mock_vector_store.search.call_count == 2

            # Third call should NOT have tools
            third_call = mock_create.call_args_list[2]
            assert "tools" not in third_call.kwargs

    def test_tool_error_in_round_1(self, ai_generator, tool_manager, mock_vector_store):
        """Test: Tool error in round 1 - error passed to Claude, can continue"""
        # First search returns error
        mock_vector_store.search.side_effect = [
            SearchResults(
                documents=[],
                metadata=[],
                distances=[],
                links=[],
                error="No course found matching 'Nonexistent'",
            ),
            SearchResults(
                documents=["Fallback content"],
                metadata=[{"course_title": "Test", "lesson_number": 1}],
                distances=[0.1],
                links=["http://test.com"],
                error=None,
            ),
        ]

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # First tool use
            tool_response_1 = Mock()
            tool_response_1.stop_reason = "tool_use"
            tool_block_1 = Mock()
            tool_block_1.type = "tool_use"
            tool_block_1.name = "search_course_content"
            tool_block_1.id = "tool_1"
            tool_block_1.input = {"query": "query 1", "course_name": "Nonexistent"}
            tool_response_1.content = [tool_block_1]

            # Claude tries alternative approach
            tool_response_2 = Mock()
            tool_response_2.stop_reason = "tool_use"
            tool_block_2 = Mock()
            tool_block_2.type = "tool_use"
            tool_block_2.name = "search_course_content"
            tool_block_2.id = "tool_2"
            tool_block_2.input = {"query": "fallback query"}
            tool_response_2.content = [tool_block_2]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Answer using fallback")]

            mock_create.side_effect = [tool_response_1, tool_response_2, final_response]

            result = ai_generator.generate_response(
                query="test",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            # Should complete successfully with fallback
            assert result == "Answer using fallback"
            assert mock_create.call_count == 3

            # Verify error was passed to Claude in round 1
            second_call_messages = mock_create.call_args_list[1].kwargs["messages"]
            tool_result_1 = second_call_messages[2]["content"][0]
            assert "No course found matching 'Nonexistent'" in tool_result_1["content"]

    def test_tool_error_in_round_2(self, ai_generator, tool_manager, mock_vector_store):
        """Test: Tool error in round 2 - Claude must answer with partial info"""
        mock_vector_store.search.side_effect = [
            SearchResults(
                documents=["Good content from lesson 1"],
                metadata=[{"course_title": "Test", "lesson_number": 1}],
                distances=[0.1],
                links=["http://test.com"],
                error=None,
            ),
            SearchResults(
                documents=[],
                metadata=[],
                distances=[],
                links=[],
                error="No course found matching 'lesson 5'",
            ),
        ]

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            tool_response_1 = Mock()
            tool_response_1.stop_reason = "tool_use"
            tool_block_1 = Mock()
            tool_block_1.type = "tool_use"
            tool_block_1.name = "search_course_content"
            tool_block_1.id = "tool_1"
            tool_block_1.input = {"query": "lesson 1"}
            tool_response_1.content = [tool_block_1]

            tool_response_2 = Mock()
            tool_response_2.stop_reason = "tool_use"
            tool_block_2 = Mock()
            tool_block_2.type = "tool_use"
            tool_block_2.name = "search_course_content"
            tool_block_2.id = "tool_2"
            tool_block_2.input = {"query": "lesson 5"}
            tool_response_2.content = [tool_block_2]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [
                Mock(text="Lesson 1 info available, lesson 5 search failed")
            ]

            mock_create.side_effect = [tool_response_1, tool_response_2, final_response]

            result = ai_generator.generate_response(
                query="Compare lessons",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            assert "Lesson 1 info available" in result
            assert mock_create.call_count == 3

    def test_message_history_preservation(
        self, ai_generator, tool_manager, mock_vector_store
    ):
        """Test: Message history preserved across all rounds"""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test", "lesson_number": 1}],
            distances=[0.1],
            links=["http://test.com"],
            error=None,
        )

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            tool_response_1 = Mock()
            tool_response_1.stop_reason = "tool_use"
            tool_block_1 = Mock()
            tool_block_1.type = "tool_use"
            tool_block_1.name = "search_course_content"
            tool_block_1.id = "tool_1"
            tool_block_1.input = {"query": "q1"}
            tool_response_1.content = [tool_block_1]

            tool_response_2 = Mock()
            tool_response_2.stop_reason = "tool_use"
            tool_block_2 = Mock()
            tool_block_2.type = "tool_use"
            tool_block_2.name = "search_course_content"
            tool_block_2.id = "tool_2"
            tool_block_2.input = {"query": "q2"}
            tool_response_2.content = [tool_block_2]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Final")]

            mock_create.side_effect = [tool_response_1, tool_response_2, final_response]

            # Include conversation history
            history = "User: Previous question\nAssistant: Previous answer"
            result = ai_generator.generate_response(
                query="New question",
                conversation_history=history,
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            # Verify system prompt includes history in ALL calls
            for call in mock_create.call_args_list:
                system = call.kwargs["system"]
                assert "Previous conversation:" in system
                assert "Previous question" in system
                assert "Previous answer" in system

    def test_early_termination_natural(
        self, ai_generator, tool_manager, mock_vector_store
    ):
        """Test: Claude naturally terminates after first tool (doesn't use all rounds)"""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Complete answer content"],
            metadata=[{"course_title": "Test", "lesson_number": 1}],
            distances=[0.1],
            links=["http://test.com"],
            error=None,
        )

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # First tool use
            tool_response = Mock()
            tool_response.stop_reason = "tool_use"
            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "tool_1"
            tool_block.input = {"query": "complete query"}
            tool_response.content = [tool_block]

            # Claude decides one tool is enough
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Complete answer after one tool")]

            mock_create.side_effect = [tool_response, final_response]

            result = ai_generator.generate_response(
                query="Simple question",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            assert result == "Complete answer after one tool"
            # Should only make 2 API calls (not 3)
            assert mock_create.call_count == 2
            assert mock_vector_store.search.call_count == 1

    def test_mixed_content_blocks(self, ai_generator, tool_manager, mock_vector_store):
        """Test: Claude returns both text AND tool_use in same response (edge case)"""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test", "lesson_number": 1}],
            distances=[0.1],
            links=["http://test.com"],
            error=None,
        )

        with patch.object(ai_generator.client.messages, "create") as mock_create:
            # Response with both text and tool use blocks
            mixed_response = Mock()
            mixed_response.stop_reason = "tool_use"

            text_block = Mock()
            text_block.type = "text"
            text_block.text = "Let me search for that..."

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "tool_1"
            tool_block.input = {"query": "search"}

            mixed_response.content = [text_block, tool_block]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Final answer")]

            mock_create.side_effect = [mixed_response, final_response]

            result = ai_generator.generate_response(
                query="test",
                tools=tool_manager.get_tool_definitions(),
                tool_manager=tool_manager,
            )

            # Should handle mixed content and execute tool
            assert result == "Final answer"
            assert mock_vector_store.search.call_count == 1

            # Verify assistant message includes BOTH blocks
            second_call_messages = mock_create.call_args_list[1].kwargs["messages"]
            assistant_content = second_call_messages[1]["content"]
            assert len(assistant_content) == 2  # text + tool_use
