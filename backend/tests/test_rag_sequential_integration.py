"""
Integration test for sequential tool calling through the RAG system
Tests the complete flow from user query to AI response with multiple tool rounds
"""

from unittest.mock import Mock, patch

from config import Config
from rag_system import RAGSystem


class TestRAGSequentialIntegration:
    """Integration tests for sequential tool calling through RAG system"""

    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    def test_sequential_tool_calling_integration(self, mock_doc_processor, mock_vector_store_class):
        """
        E2E integration test: User query triggers sequential tool calls

        Simulates: "What does lesson 3 of the MCP course cover?"
        Expected flow:
        1. Claude uses get_course_outline to get course structure
        2. Claude sees lesson 3 exists, uses search_course_content to get details
        3. Claude synthesizes final answer
        """
        # Mock configuration
        config = Config()
        config.API_PROVIDER = "anthropic"
        config.ANTHROPIC_API_KEY = "test-key"
        config.MAX_TOOL_ROUNDS = 2

        # Mock vector store instance
        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        # Mock course outline response
        mock_vector_store.get_course_outline.return_value = {
            "title": "Introduction to MCP",
            "instructor": "Test Instructor",
            "course_link": "https://example.com/mcp",
            "lesson_count": 5,
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Getting Started",
                    "lesson_link": "https://example.com/lesson1",
                },
                {
                    "lesson_number": 2,
                    "lesson_title": "Basic Concepts",
                    "lesson_link": "https://example.com/lesson2",
                },
                {
                    "lesson_number": 3,
                    "lesson_title": "Building Your First Server",
                    "lesson_link": "https://example.com/lesson3",
                },
            ],
        }

        # Mock search results for lesson 3
        from vector_store import SearchResults

        mock_search_results = SearchResults(
            documents=["Lesson 3 covers building your first MCP server with Python..."],
            metadata=[
                {"course_title": "Introduction to MCP", "lesson_number": 3, "chunk_index": 0}
            ],
            distances=[0.15],
        )
        mock_vector_store.search.return_value = mock_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson3"
        mock_vector_store.get_course_link.return_value = "https://example.com/mcp"

        # Initialize RAG system
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            # Mock Anthropic client responses
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            # First API call: Claude requests course outline
            outline_tool_use = Mock()
            outline_tool_use.type = "tool_use"
            outline_tool_use.name = "get_course_outline"
            outline_tool_use.id = "tool_1"
            outline_tool_use.input = {"course_name": "MCP"}

            outline_response = Mock()
            outline_response.content = [outline_tool_use]
            outline_response.stop_reason = "tool_use"

            # Second API call: Claude requests lesson content search
            search_tool_use = Mock()
            search_tool_use.type = "tool_use"
            search_tool_use.name = "search_course_content"
            search_tool_use.id = "tool_2"
            search_tool_use.input = {
                "query": "Building Your First Server",
                "course_name": "MCP",
                "lesson_number": 3,
            }

            search_response = Mock()
            search_response.content = [search_tool_use]
            search_response.stop_reason = "tool_use"

            # Third API call: Claude returns final answer
            final_text = Mock()
            final_text.type = "text"
            final_text.text = "Lesson 3 of the MCP course covers building your first server with Python. It provides step-by-step instructions and examples."

            final_response = Mock()
            final_response.content = [final_text]
            final_response.stop_reason = "end_turn"

            # Set up API call sequence
            mock_client.messages.create.side_effect = [
                outline_response,  # Round 1: get outline
                search_response,  # Round 2: search content
                final_response,  # Final response
            ]

            # Create RAG system and execute query
            rag = RAGSystem(config)
            response, sources = rag.query("What does lesson 3 of the MCP course cover?")

            # Verify sequential tool calling occurred
            assert (
                mock_client.messages.create.call_count == 3
            ), "Should make 3 API calls (2 tools + final)"

            # Verify tools were called in correct order
            assert (
                mock_vector_store.get_course_outline.call_count == 1
            ), "Should call get_course_outline once"
            assert mock_vector_store.search.call_count == 1, "Should call search once"

            # Verify final response is returned
            assert "Lesson 3" in response
            assert "building your first server" in response.lower()

            # Verify sources are provided
            assert len(sources) > 0, "Should have sources from the search"
            assert sources[0]["text"] == "Introduction to MCP - Lesson 3"
            assert sources[0]["link"] == "https://example.com/lesson3"

    @patch("rag_system.VectorStore")
    @patch("rag_system.DocumentProcessor")
    def test_max_rounds_enforcement_integration(self, mock_doc_processor, mock_vector_store_class):
        """
        Integration test: Verify system stops at MAX_TOOL_ROUNDS

        Simulates a scenario where Claude keeps requesting tools,
        but system enforces the 2-round limit
        """
        config = Config()
        config.API_PROVIDER = "anthropic"
        config.ANTHROPIC_API_KEY = "test-key"
        config.MAX_TOOL_ROUNDS = 2

        mock_vector_store = Mock()
        mock_vector_store_class.return_value = mock_vector_store

        # Mock returns for tools
        from vector_store import SearchResults

        mock_vector_store.search.return_value = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"

        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            # Claude keeps requesting tools (simulating greedy behavior)
            tool_use = Mock()
            tool_use.type = "tool_use"
            tool_use.name = "search_course_content"
            tool_use.id = "tool_123"
            tool_use.input = {"query": "test"}

            tool_response = Mock()
            tool_response.content = [tool_use]
            tool_response.stop_reason = "tool_use"

            # Final response
            final_text = Mock()
            final_text.type = "text"
            final_text.text = "Final answer after max rounds"

            final_response = Mock()
            final_response.content = [final_text]

            # Claude tries to use tools repeatedly, but we limit to 2 rounds
            mock_client.messages.create.side_effect = [
                tool_response,  # Round 1
                tool_response,  # Round 2
                final_response,  # Final call (forced)
            ]

            rag = RAGSystem(config)
            response, sources = rag.query("Test query")

            # Verify max rounds enforced
            assert (
                mock_client.messages.create.call_count == 3
            ), "Should stop at 2 tool rounds + 1 final call"
            assert mock_vector_store.search.call_count == 2, "Should execute tools exactly twice"
            assert response == "Final answer after max rounds"
