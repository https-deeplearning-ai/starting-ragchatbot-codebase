"""Integration tests for the RAG system"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system import RAGSystem
from vector_store import SearchResults
from models import Course, Lesson, CourseChunk


class TestRAGSystemQuery:
    """Tests for RAGSystem.query() with content-related questions"""

    @pytest.fixture
    def mock_rag_system(self, config_mock, sample_search_results):
        """Create a RAG system with mocked components"""
        with patch('rag_system.DocumentProcessor'):
            with patch('rag_system.VectorStore') as mock_vs:
                with patch('rag_system.AIGenerator') as mock_ai:
                    with patch('rag_system.SessionManager') as mock_sm:
                        # Configure mocks
                        mock_vs_instance = Mock()
                        mock_vs_instance.search = Mock(return_value=sample_search_results)
                        mock_vs.return_value = mock_vs_instance

                        mock_ai_instance = Mock()
                        mock_ai_instance.generate_response = Mock(
                            return_value="Here's the answer based on search results"
                        )
                        mock_ai.return_value = mock_ai_instance

                        mock_sm_instance = Mock()
                        mock_sm_instance.create_session = Mock(return_value="session_1")
                        mock_sm_instance.get_conversation_history = Mock(return_value=None)
                        mock_sm_instance.add_exchange = Mock()
                        mock_sm.return_value = mock_sm_instance

                        # Create RAG system
                        rag = RAGSystem(config_mock)
                        rag.vector_store = mock_vs_instance
                        rag.ai_generator = mock_ai_instance
                        rag.session_manager = mock_sm_instance

                        yield rag

    def test_query_returns_response_and_sources(self, mock_rag_system):
        """Test that query returns both response and sources"""
        response, sources = mock_rag_system.query("What is Python?")

        assert isinstance(response, str)
        assert isinstance(sources, list)

    def test_query_calls_ai_generator_with_tools(self, mock_rag_system):
        """Test that query passes tools to AI generator"""
        response, sources = mock_rag_system.query("Python basics")

        # Verify AI generator was called with tools
        mock_rag_system.ai_generator.generate_response.assert_called_once()
        call_args = mock_rag_system.ai_generator.generate_response.call_args

        # Check that tools were passed
        assert "tools" in call_args.kwargs
        tools = call_args.kwargs["tools"]
        assert len(tools) > 0

        # Check tool names
        tool_names = [t["name"] for t in tools]
        assert "search_course_content" in tool_names

    def test_query_uses_provided_session_or_none(self, mock_rag_system):
        """Test that query works with or without session_id"""
        # Note: Session creation is handled by the API layer (app.py), not RAGSystem
        response, sources = mock_rag_system.query("Question?", session_id=None)

        # When session_id is None, RAGSystem doesn't call get_conversation_history
        mock_rag_system.session_manager.get_conversation_history.assert_not_called()

        # But it does work without errors
        assert isinstance(response, str)
        assert isinstance(sources, list)

    def test_query_uses_existing_session(self, mock_rag_system):
        """Test that query uses existing session if provided"""
        response, sources = mock_rag_system.query("Question?", session_id="session_123")

        # Should not create a new session
        mock_rag_system.session_manager.create_session.assert_not_called()

        # Should retrieve history
        mock_rag_system.session_manager.get_conversation_history.assert_called_once_with("session_123")

    def test_query_adds_to_conversation_history(self, mock_rag_system):
        """Test that query adds exchange to conversation history"""
        response, sources = mock_rag_system.query("Question?", session_id="session_1")

        mock_rag_system.session_manager.add_exchange.assert_called_once()
        call_args = mock_rag_system.session_manager.add_exchange.call_args
        assert call_args[0][0] == "session_1"  # session_id

    def test_query_retrieves_and_returns_sources(self, mock_rag_system):
        """Test that sources are retrieved from tool_manager"""
        # Mock get_last_sources to return test sources
        mock_rag_system.tool_manager.get_last_sources = Mock(
            return_value=[{"title": "Test", "url": "http://example.com"}]
        )

        response, sources = mock_rag_system.query("Question?")

        # Verify sources were retrieved
        mock_rag_system.tool_manager.get_last_sources.assert_called()
        assert isinstance(sources, list)

    def test_query_passes_session_id_in_request(self, mock_rag_system):
        """Test that session_id is included in tool_manager"""
        response, sources = mock_rag_system.query("Question?", session_id="session_123")

        # Verify tool_manager was passed to AI generator
        call_args = mock_rag_system.ai_generator.generate_response.call_args
        assert "tool_manager" in call_args.kwargs
        assert call_args.kwargs["tool_manager"] == mock_rag_system.tool_manager

    def test_query_with_search_results_includes_sources(self, mock_rag_system, sample_search_results):
        """Test that search results are converted to sources"""
        # Mock the tool_manager to return sources
        mock_rag_system.tool_manager.get_last_sources = Mock(
            return_value=[
                {"title": "Course 1 - Lesson 1", "url": "https://example.com/1"},
                {"title": "Course 1 - Lesson 2", "url": "https://example.com/2"}
            ]
        )

        response, sources = mock_rag_system.query("Python question")

        assert len(sources) == 2
        assert sources[0]["title"] == "Course 1 - Lesson 1"

    def test_query_empty_sources_for_non_search_questions(self, mock_rag_system):
        """Test that sources are empty if AI doesn't use search"""
        # Mock tool_manager to return no sources (no search was performed)
        mock_rag_system.tool_manager.get_last_sources = Mock(return_value=[])

        response, sources = mock_rag_system.query("What is 2+2?")

        assert sources == []

    def test_query_formats_prompt_correctly(self, mock_rag_system):
        """Test that query formats the prompt for AI"""
        mock_rag_system.query("Find information about loops")

        # Verify AI was called
        call_args = mock_rag_system.ai_generator.generate_response.call_args
        prompt = call_args.kwargs["query"]

        # Should have the formatted prompt
        assert "Find information about loops" in prompt or "course materials" in prompt.lower()


class TestRAGSystemDataLoading:
    """Tests for RAGSystem.add_course_document() and add_course_folder()"""

    @pytest.fixture
    def mock_rag_system_for_loading(self, config_mock, sample_course, sample_course_chunks):
        """Create a RAG system for testing data loading"""
        with patch('rag_system.DocumentProcessor') as mock_dp:
            with patch('rag_system.VectorStore') as mock_vs:
                with patch('rag_system.AIGenerator'):
                    with patch('rag_system.SessionManager'):
                        mock_dp_instance = Mock()
                        mock_dp_instance.process_course_document = Mock(
                            return_value=(sample_course, sample_course_chunks)
                        )
                        mock_dp.return_value = mock_dp_instance

                        mock_vs_instance = Mock()
                        mock_vs_instance.add_course_metadata = Mock()
                        mock_vs_instance.add_course_content = Mock()
                        mock_vs_instance.get_existing_course_titles = Mock(return_value=[])
                        mock_vs.return_value = mock_vs_instance

                        rag = RAGSystem(config_mock)
                        rag.document_processor = mock_dp_instance
                        rag.vector_store = mock_vs_instance

                        yield rag

    def test_add_course_document_processes_file(self, mock_rag_system_for_loading):
        """Test that add_course_document processes a file correctly"""
        course, chunks = mock_rag_system_for_loading.add_course_document("/path/to/course.pdf")

        # Verify document was processed
        mock_rag_system_for_loading.document_processor.process_course_document.assert_called_once_with(
            "/path/to/course.pdf"
        )

        # Verify course was added to vector store
        mock_rag_system_for_loading.vector_store.add_course_metadata.assert_called_once()
        mock_rag_system_for_loading.vector_store.add_course_content.assert_called_once()

    def test_add_course_document_returns_course_and_chunk_count(self, mock_rag_system_for_loading, sample_course):
        """Test that add_course_document returns proper values"""
        course, chunk_count = mock_rag_system_for_loading.add_course_document("/path/to/course.pdf")

        assert course is not None
        assert chunk_count > 0

    def test_add_course_folder_requires_existing_path(self, mock_rag_system_for_loading):
        """Test that add_course_folder handles missing paths"""
        courses, chunks = mock_rag_system_for_loading.add_course_folder("/nonexistent/path")

        assert courses == 0
        assert chunks == 0


class TestRAGSystemGetCourseAnalytics:
    """Tests for RAGSystem.get_course_analytics()"""

    @pytest.fixture
    def mock_rag_system_analytics(self, config_mock):
        """Create a RAG system for analytics tests"""
        with patch('rag_system.DocumentProcessor'):
            with patch('rag_system.VectorStore') as mock_vs:
                with patch('rag_system.AIGenerator'):
                    with patch('rag_system.SessionManager'):
                        mock_vs_instance = Mock()
                        mock_vs_instance.get_course_count = Mock(return_value=3)
                        mock_vs_instance.get_existing_course_titles = Mock(
                            return_value=["Python", "JavaScript", "Go"]
                        )
                        mock_vs.return_value = mock_vs_instance

                        rag = RAGSystem(config_mock)
                        rag.vector_store = mock_vs_instance

                        yield rag

    def test_get_course_analytics_returns_dict(self, mock_rag_system_analytics):
        """Test that get_course_analytics returns proper structure"""
        analytics = mock_rag_system_analytics.get_course_analytics()

        assert isinstance(analytics, dict)
        assert "total_courses" in analytics
        assert "course_titles" in analytics

    def test_get_course_analytics_returns_course_count(self, mock_rag_system_analytics):
        """Test that analytics includes course count"""
        analytics = mock_rag_system_analytics.get_course_analytics()

        assert analytics["total_courses"] == 3

    def test_get_course_analytics_returns_course_titles(self, mock_rag_system_analytics):
        """Test that analytics includes course titles"""
        analytics = mock_rag_system_analytics.get_course_analytics()

        assert len(analytics["course_titles"]) == 3
        assert "Python" in analytics["course_titles"]
