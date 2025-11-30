"""
Integration tests for RAG System
Tests the complete query flow including source tracking and tool integration
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from config import Config
from models import Course, CourseChunk, Lesson
from rag_system import RAGSystem
from vector_store import SearchResults


class TestRAGSystemIntegration:
    """Test suite for RAG System end-to-end integration"""

    @pytest.fixture
    def temp_chroma_path(self):
        """Create temporary directory for ChromaDB"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def test_config(self, temp_chroma_path):
        """Create test configuration"""
        config = Config()
        config.CHROMA_PATH = temp_chroma_path
        config.ANTHROPIC_API_KEY = "test-key"
        return config

    @pytest.fixture
    def rag_system(self, test_config):
        """Create RAG system with test configuration"""
        return RAGSystem(test_config)

    def test_rag_system_initialization(self, rag_system):
        """Test that RAG system initializes all components correctly"""
        assert rag_system.document_processor is not None
        assert rag_system.vector_store is not None
        assert rag_system.ai_generator is not None
        assert rag_system.session_manager is not None
        assert rag_system.tool_manager is not None
        assert rag_system.search_tool is not None
        assert rag_system.outline_tool is not None

    def test_tool_registration(self, rag_system):
        """Test that tools are registered in the tool manager"""
        tool_definitions = rag_system.tool_manager.get_tool_definitions()

        # Should have both search and outline tools
        assert len(tool_definitions) == 2

        tool_names = [tool["name"] for tool in tool_definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_basic_query_flow_with_mocked_ai(
        self, rag_system, sample_course, sample_course_chunks
    ):
        """Test complete query flow with mocked AI generator"""
        # Add test data to vector store
        rag_system.vector_store.add_course_metadata(sample_course)
        rag_system.vector_store.add_course_content(sample_course_chunks)

        # Mock the AI generator to simulate tool use
        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            # First response: Claude wants to search
            tool_use_response = Mock()
            tool_use_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "tool_123"
            tool_block.input = {"query": "Python"}

            tool_use_response.content = [tool_block]

            # Second response: Final answer
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [
                Mock(text="Python is a high-level programming language.")
            ]

            mock_create.side_effect = [tool_use_response, final_response]

            # Execute query
            response, sources = rag_system.query("What is Python?")

            # Verify response
            assert response == "Python is a high-level programming language."

            # Verify sources were tracked
            assert len(sources) > 0
            assert isinstance(sources[0], dict)
            assert "text" in sources[0]
            assert "link" in sources[0]

    def test_source_tracking_through_pipeline(
        self, rag_system, sample_course, sample_course_chunks
    ):
        """Test that sources are properly tracked from vector store to final response"""
        # Add test data
        rag_system.vector_store.add_course_metadata(sample_course)
        rag_system.vector_store.add_course_content(sample_course_chunks)

        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            tool_use_response = Mock()
            tool_use_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "tool_src"
            tool_block.input = {"query": "Variables", "course_name": "Python Basics"}

            tool_use_response.content = [tool_block]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Variables store data.")]

            mock_create.side_effect = [tool_use_response, final_response]

            response, sources = rag_system.query("Explain variables")

            # Verify sources include course and lesson information
            assert len(sources) > 0
            first_source = sources[0]
            assert "Python Basics" in first_source["text"]
            assert "link" in first_source

    def test_conversation_history_handling(self, rag_system):
        """Test that conversation history is maintained across queries"""
        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            # Mock responses for two queries
            response1 = Mock()
            response1.stop_reason = "end_turn"
            response1.content = [Mock(text="First answer")]

            response2 = Mock()
            response2.stop_reason = "end_turn"
            response2.content = [Mock(text="Second answer with context")]

            mock_create.side_effect = [response1, response2]

            # First query - creates session
            resp1, _ = rag_system.query("First question")
            session_id = rag_system.session_manager.create_session()
            rag_system.session_manager.add_exchange(session_id, "First question", resp1)

            # Second query with session
            resp2, _ = rag_system.query("Follow-up question", session_id=session_id)

            # Verify second call includes history in system prompt
            second_call = mock_create.call_args_list[1]
            system_content = second_call.kwargs["system"]
            assert (
                "Previous conversation:" in system_content
                or "First question" in system_content
            )

    def test_source_reset_after_query(
        self, rag_system, sample_course, sample_course_chunks
    ):
        """Test that sources are reset after each query to avoid stale data"""
        rag_system.vector_store.add_course_metadata(sample_course)
        rag_system.vector_store.add_course_content(sample_course_chunks)

        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            # First query with tool use
            tool_response = Mock()
            tool_response.stop_reason = "tool_use"
            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "tool_1"
            tool_block.input = {"query": "test"}
            tool_response.content = [tool_block]

            final1 = Mock()
            final1.stop_reason = "end_turn"
            final1.content = [Mock(text="Answer 1")]

            # Second query without tool use
            direct_response = Mock()
            direct_response.stop_reason = "end_turn"
            direct_response.content = [Mock(text="Answer 2")]

            mock_create.side_effect = [tool_response, final1, direct_response]

            # First query - should have sources
            _, sources1 = rag_system.query("Query 1")
            assert len(sources1) > 0

            # Second query - should have no sources (no tool use)
            _, sources2 = rag_system.query("What is 2+2?")
            assert len(sources2) == 0  # Sources were reset

    def test_outline_tool_integration(self, rag_system, sample_course):
        """Test that outline tool can be called and returns proper structure"""
        rag_system.vector_store.add_course_metadata(sample_course)

        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            # Claude decides to use outline tool
            tool_response = Mock()
            tool_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "get_course_outline"
            tool_block.id = "outline_tool"
            tool_block.input = {"course_title": "Python Basics"}

            tool_response.content = [tool_block]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [
                Mock(text="The course has 3 lessons covering Python fundamentals.")
            ]

            mock_create.side_effect = [tool_response, final_response]

            response, sources = rag_system.query("Show me the Python Basics outline")

            # Verify outline tool was executed (check via sources)
            assert len(sources) > 0
            # Outline tool should track the course as a source
            assert sources[0]["text"] == "Python Basics"

    def test_query_without_session(self, rag_system):
        """Test that queries work without providing a session_id"""
        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = [Mock(text="Answer")]
            mock_create.return_value = mock_response

            # Query without session
            response, sources = rag_system.query("Test query")

            # Should still work
            assert response == "Answer"
            assert isinstance(sources, list)

    def test_empty_query_handling(self, rag_system):
        """Test system behavior with empty or whitespace queries"""
        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            mock_response = Mock()
            mock_response.stop_reason = "end_turn"
            mock_response.content = [Mock(text="I need more information.")]
            mock_create.return_value = mock_response

            # Empty query
            response, sources = rag_system.query("")
            assert isinstance(response, str)

    def test_get_course_analytics(self, rag_system, sample_course):
        """Test course analytics retrieval"""
        rag_system.vector_store.add_course_metadata(sample_course)

        analytics = rag_system.get_course_analytics()

        assert "total_courses" in analytics
        assert "course_titles" in analytics
        assert analytics["total_courses"] == 1
        assert "Python Basics" in analytics["course_titles"]

    def test_multiple_courses_search(self, rag_system, sample_course):
        """Test searching across multiple courses"""
        # Add multiple courses
        course1 = sample_course
        course2 = Course(
            title="Advanced Python",
            course_link="https://example.com/advanced",
            instructor="John Doe",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Decorators",
                    lesson_link="http://example.com/adv/l1",
                )
            ],
        )

        rag_system.vector_store.add_course_metadata(course1)
        rag_system.vector_store.add_course_metadata(course2)

        # Add chunks for both
        from models import CourseChunk

        chunks = [
            CourseChunk(
                content="Basic Python content",
                course_title="Python Basics",
                lesson_number=1,
                chunk_index=0,
            ),
            CourseChunk(
                content="Advanced decorators",
                course_title="Advanced Python",
                lesson_number=1,
                chunk_index=0,
            ),
        ]
        rag_system.vector_store.add_course_content(chunks)

        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            tool_response = Mock()
            tool_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "multi_search"
            tool_block.input = {"query": "Python"}  # No course filter - search all

            tool_response.content = [tool_block]

            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="Found content in multiple courses")]

            mock_create.side_effect = [tool_response, final_response]

            response, sources = rag_system.query("Tell me about Python")

            # Should potentially find results from both courses
            assert len(sources) >= 1

    def test_tool_error_propagation(self, rag_system):
        """Test that errors from tools are handled gracefully"""
        with patch.object(
            rag_system.ai_generator.client.messages, "create"
        ) as mock_create:
            # Mock tool use for non-existent course
            tool_response = Mock()
            tool_response.stop_reason = "tool_use"

            tool_block = Mock()
            tool_block.type = "tool_use"
            tool_block.name = "search_course_content"
            tool_block.id = "error_tool"
            tool_block.input = {"query": "test", "course_name": "NonExistentCourse"}

            tool_response.content = [tool_block]

            # AI handles the error
            final_response = Mock()
            final_response.stop_reason = "end_turn"
            final_response.content = [Mock(text="I couldn't find that course.")]

            mock_create.side_effect = [tool_response, final_response]

            response, sources = rag_system.query("Search in fake course")

            # Should return error message as response
            assert "find" in response.lower() or "course" in response.lower()
            # No sources on error
            assert len(sources) == 0
