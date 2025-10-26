"""
Tests for RAG System integration and end-to-end functionality
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system import RAGSystem
from models import Course, Lesson, CourseChunk


class TestRAGSystem:
    """Test cases for RAGSystem class"""

    def test_initialization(self, test_config):
        """Test that RAGSystem initializes correctly"""
        with patch('rag_system.DocumentProcessor') as mock_processor, \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager:

            # Create RAG system
            rag = RAGSystem(test_config)

            # Verify all components were initialized
            mock_processor.assert_called_once_with(test_config.CHUNK_SIZE, test_config.CHUNK_OVERLAP)
            mock_store.assert_called_once_with(test_config.CHROMA_PATH, test_config.EMBEDDING_MODEL, test_config.MAX_RESULTS)
            mock_ai.assert_called_once_with(test_config.ANTHROPIC_API_KEY, test_config.ANTHROPIC_MODEL)
            mock_session.assert_called_once_with(test_config.MAX_HISTORY)
            mock_tool_manager.assert_called_once()

            # Verify attributes
            assert rag.config == test_config
            assert rag.document_processor is not None
            assert rag.vector_store is not None
            assert rag.ai_generator is not None
            assert rag.session_manager is not None
            assert rag.tool_manager is not None
            assert rag.search_tool is not None
            assert rag.outline_tool is not None

    def test_query_successful_response(self, test_config, sample_queries):
        """Test successful query processing"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager:

            # Setup mocks
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.return_value = "Machine learning is a subset of AI..."

            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get_conversation_history.return_value = None

            mock_tool_manager_instance = Mock()
            mock_tool_manager.return_value = mock_tool_manager_instance
            mock_tool_manager_instance.get_tool_definitions.return_value = []
            mock_tool_manager_instance.get_last_sources.return_value = ["Test Course - Lesson 1"]
            mock_tool_manager_instance.reset_sources.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test query
            response, sources = rag.query(sample_queries["valid_content_query"])

            # Verify AI was called with correct parameters
            mock_ai_instance.generate_response.assert_called_once()
            call_args = mock_ai_instance.generate_response.call_args

            assert call_args[1]["query"] == f"Answer this question about course materials: {sample_queries['valid_content_query']}"
            assert call_args[1]["conversation_history"] is None
            assert call_args[1]["tools"] == []
            assert call_args[1]["tool_manager"] == mock_tool_manager_instance

            # Verify response and sources
            assert response == "Machine learning is a subset of AI..."
            assert sources == ["Test Course - Lesson 1"]

            # Verify tool manager methods were called
            mock_tool_manager_instance.get_last_sources.assert_called_once()
            mock_tool_manager_instance.reset_sources.assert_called_once()

    def test_query_with_session_id(self, test_config, sample_queries):
        """Test query processing with session context"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager:

            # Setup mocks
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.return_value = "Response with context"

            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get_conversation_history.return_value = "Previous conversation context"
            mock_session_instance.add_exchange.return_value = None

            mock_tool_manager_instance = Mock()
            mock_tool_manager.return_value = mock_tool_manager_instance
            mock_tool_manager_instance.get_tool_definitions.return_value = []
            mock_tool_manager_instance.get_last_sources.return_value = []
            mock_tool_manager_instance.reset_sources.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            session_id = "test_session_123"
            response, sources = rag.query(sample_queries["valid_content_query"], session_id)

            # Verify conversation history was retrieved
            mock_session_instance.get_conversation_history.assert_called_once_with(session_id)

            # Verify AI was called with history
            call_args = mock_ai_instance.generate_response.call_args
            assert call_args[1]["conversation_history"] == "Previous conversation context"

            # Verify conversation was updated
            mock_session_instance.add_exchange.assert_called_once_with(
                session_id,
                sample_queries["valid_content_query"],
                "Response with context"
            )

    def test_query_without_session_id(self, test_config, sample_queries):
        """Test query processing without session ID"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager:

            # Setup mocks
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.return_value = "Response without session"

            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance

            mock_tool_manager_instance = Mock()
            mock_tool_manager.return_value = mock_tool_manager_instance
            mock_tool_manager_instance.get_tool_definitions.return_value = []
            mock_tool_manager_instance.get_last_sources.return_value = []
            mock_tool_manager_instance.reset_sources.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test query without session_id
            response, sources = rag.query(sample_queries["valid_content_query"])

            # Verify session manager was not called for history
            mock_session_instance.get_conversation_history.assert_not_called()

            # Verify conversation was not updated
            mock_session_instance.add_exchange.assert_not_called()

    def test_query_with_tools_integration(self, test_config, sample_queries, mock_search_tools):
        """Test query processing with tool integration"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager, \
             patch('rag_system.CourseSearchTool') as mock_search_tool_class, \
             patch('rag_system.CourseOutlineTool') as mock_outline_tool_class:

            # Setup AI mock
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.return_value = "Tool-based response"

            # Setup session mock
            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get_conversation_history.return_value = None

            # Setup tool mocks
            mock_search_tool_instance = mock_search_tools['search_tool']
            mock_outline_tool_instance = mock_search_tools['outline_tool']
            mock_search_tool_class.return_value = mock_search_tool_instance
            mock_outline_tool_class.return_value = mock_outline_tool_instance

            mock_tool_manager_instance = Mock()
            mock_tool_manager.return_value = mock_tool_manager_instance
            mock_tool_manager_instance.get_tool_definitions.return_value = [
                mock_search_tool_instance.get_tool_definition.return_value,
                mock_outline_tool_instance.get_tool_definition.return_value
            ]
            mock_tool_manager_instance.get_last_sources.return_value = ["Source from search"]
            mock_tool_manager_instance.reset_sources.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test query
            response, sources = rag.query(sample_queries["valid_content_query"])

            # Verify tools were registered
            mock_tool_manager_instance.register_tool.assert_has_calls([
                call(mock_search_tool_instance),
                call(mock_outline_tool_instance)
            ])

            # Verify AI was called with tools
            call_args = mock_ai_instance.generate_response.call_args
            assert call_args[1]["tools"] == [
                mock_search_tool_instance.get_tool_definition.return_value,
                mock_outline_tool_instance.get_tool_definition.return_value
            ]
            assert call_args[1]["tool_manager"] == mock_tool_manager_instance

    def test_query_ai_generation_failure(self, test_config, sample_queries):
        """Test query handling when AI generation fails"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager:

            # Setup AI to raise exception
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.side_effect = Exception("AI API Error")

            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get_conversation_history.return_value = None

            mock_tool_manager_instance = Mock()
            mock_tool_manager.return_value = mock_tool_manager_instance
            mock_tool_manager_instance.get_tool_definitions.return_value = []

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test query should raise exception
            with pytest.raises(Exception, match="AI API Error"):
                rag.query(sample_queries["valid_content_query"])

    def test_add_course_document_success(self, test_config, sample_course, sample_course_chunks):
        """Test successful course document addition"""
        with patch('rag_system.DocumentProcessor') as mock_processor, \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.ToolManager'):

            # Setup mocks
            mock_processor_instance = Mock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.process_course_document.return_value = (sample_course, sample_course_chunks)

            mock_store_instance = Mock()
            mock_store.return_value = mock_store_instance
            mock_store_instance.add_course_metadata.return_value = None
            mock_store_instance.add_course_content.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test document addition
            result_course, chunk_count = rag.add_course_document("/path/to/course.pdf")

            # Verify processor was called
            mock_processor_instance.process_course_document.assert_called_once_with("/path/to/course.pdf")

            # Verify vector store operations
            mock_store_instance.add_course_metadata.assert_called_once_with(sample_course)
            mock_store_instance.add_course_content.assert_called_once_with(sample_course_chunks)

            # Verify results
            assert result_course == sample_course
            assert chunk_count == len(sample_course_chunks)

    def test_add_course_document_processing_error(self, test_config):
        """Test handling of document processing errors"""
        with patch('rag_system.DocumentProcessor') as mock_processor, \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.ToolManager'):

            # Setup processor to raise exception
            mock_processor_instance = Mock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.process_course_document.side_effect = Exception("Document processing failed")

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test document addition should handle error gracefully
            result_course, chunk_count = rag.add_course_document("/path/to/invalid.pdf")

            # Verify error handling
            assert result_course is None
            assert chunk_count == 0

    def test_add_course_folder_empty_folder(self, test_config):
        """Test adding course folder when folder doesn't exist"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.ToolManager'), \
             patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir:

            # Setup folder doesn't exist
            mock_exists.return_value = False

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test folder addition
            total_courses, total_chunks = rag.add_course_folder("/nonexistent/folder")

            # Verify results
            assert total_courses == 0
            assert total_chunks == 0

    def test_add_course_folder_with_existing_courses(self, test_config, sample_course, sample_course_chunks):
        """Test adding course folder with existing course detection"""
        with patch('rag_system.DocumentProcessor') as mock_processor, \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.ToolManager'), \
             patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch('os.path.join') as mock_join:

            # Setup folder exists with files
            mock_exists.return_value = True
            mock_listdir.return_value = ["course1.pdf", "course2.txt"]
            mock_isfile.return_value = True
            mock_join.side_effect = lambda folder, filename: f"{folder}/{filename}"

            # Setup processor
            mock_processor_instance = Mock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.process_course_document.side_effect = [
                (sample_course, sample_course_chunks),  # First call - new course
                (sample_course, sample_course_chunks)   # Second call - existing course
            ]

            # Setup vector store
            mock_store_instance = Mock()
            mock_store.return_value = mock_store_instance
            mock_store_instance.get_existing_course_titles.return_value = [sample_course.title]
            mock_store_instance.add_course_metadata.return_value = None
            mock_store_instance.add_course_content.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test folder addition
            total_courses, total_chunks = rag.add_course_folder("/test/folder", clear_existing=False)

            # Verify existing courses were checked
            mock_store_instance.get_existing_course_titles.assert_called_once()

            # Verify only new course was added
            assert total_courses == 1  # Only one new course should be added
            assert total_chunks == len(sample_course_chunks)

            # Verify metadata and content were added only for new course
            mock_store_instance.add_course_metadata.assert_called_once_with(sample_course)
            mock_store_instance.add_course_content.assert_called_once_with(sample_course_chunks)

    def test_add_course_folder_clear_existing(self, test_config, sample_course, sample_course_chunks):
        """Test adding course folder with clear_existing=True"""
        with patch('rag_system.DocumentProcessor') as mock_processor, \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.ToolManager'), \
             patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch('os.path.join') as mock_join:

            # Setup folder exists with files
            mock_exists.return_value = True
            mock_listdir.return_value = ["course1.pdf"]
            mock_isfile.return_value = True
            mock_join.side_effect = lambda folder, filename: f"{folder}/{filename}"

            # Setup processor
            mock_processor_instance = Mock()
            mock_processor.return_value = mock_processor_instance
            mock_processor_instance.process_course_document.return_value = (sample_course, sample_course_chunks)

            # Setup vector store
            mock_store_instance = Mock()
            mock_store.return_value = mock_store_instance
            mock_store_instance.get_existing_course_titles.return_value = []  # No existing courses
            mock_store_instance.clear_all_data.return_value = None
            mock_store_instance.add_course_metadata.return_value = None
            mock_store_instance.add_course_content.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test folder addition with clear_existing=True
            total_courses, total_chunks = rag.add_course_folder("/test/folder", clear_existing=True)

            # Verify data was cleared first
            mock_store_instance.clear_all_data.assert_called_once()

            # Verify course was added
            assert total_courses == 1
            assert total_chunks == len(sample_course_chunks)

    def test_get_course_analytics(self, test_config):
        """Test getting course analytics"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_store, \
             patch('rag_system.AIGenerator'), \
             patch('rag_system.SessionManager'), \
             patch('rag_system.ToolManager'):

            # Setup vector store
            mock_store_instance = Mock()
            mock_store.return_value = mock_store_instance
            mock_store_instance.get_course_count.return_value = 5
            mock_store_instance.get_existing_course_titles.return_value = [
                "Course 1", "Course 2", "Course 3", "Course 4", "Course 5"
            ]

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test analytics
            analytics = rag.get_course_analytics()

            # Verify analytics structure
            assert "total_courses" in analytics
            assert "course_titles" in analytics
            assert analytics["total_courses"] == 5
            assert len(analytics["course_titles"]) == 5
            assert "Course 1" in analytics["course_titles"]

            # Verify vector store methods were called
            mock_store_instance.get_course_count.assert_called_once()
            mock_store_instance.get_existing_course_titles.assert_called_once()

    def test_query_prompt_formatting(self, test_config, sample_queries):
        """Test that query prompts are formatted correctly"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager:

            # Setup mocks
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.return_value = "Response"

            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get_conversation_history.return_value = None

            mock_tool_manager_instance = Mock()
            mock_tool_manager.return_value = mock_tool_manager_instance
            mock_tool_manager_instance.get_tool_definitions.return_value = []
            mock_tool_manager_instance.get_last_sources.return_value = []
            mock_tool_manager_instance.reset_sources.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test query
            query = sample_queries["valid_content_query"]
            rag.query(query)

            # Verify prompt formatting
            call_args = mock_ai_instance.generate_response.call_args
            expected_prompt = f"Answer this question about course materials: {query}"
            assert call_args[1]["query"] == expected_prompt

    def test_different_query_types(self, test_config, sample_queries):
        """Test handling of different query types"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager:

            # Setup mocks
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.return_value = "Response"

            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get_conversation_history.return_value = None

            mock_tool_manager_instance = Mock()
            mock_tool_manager.return_value = mock_tool_manager_instance
            mock_tool_manager_instance.get_tool_definitions.return_value = []
            mock_tool_manager_instance.get_last_sources.return_value = []
            mock_tool_manager_instance.reset_sources.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test different query types
            for query_type, query in sample_queries.items():
                if query:  # Skip empty queries
                    response, sources = rag.query(query)

                    # Verify each query was processed
                    call_args = mock_ai_instance.generate_response.call_args
                    assert query in call_args[1]["query"]

                    # Reset mock for next iteration
                    mock_ai_instance.reset_mock()

    def test_edge_case_queries(self, test_config):
        """Test edge case queries"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore'), \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager') as mock_session, \
             patch('rag_system.ToolManager') as mock_tool_manager:

            # Setup mocks
            mock_ai_instance = Mock()
            mock_ai.return_value = mock_ai_instance
            mock_ai_instance.generate_response.return_value = "Response"

            mock_session_instance = Mock()
            mock_session.return_value = mock_session_instance
            mock_session_instance.get_conversation_history.return_value = None

            mock_tool_manager_instance = Mock()
            mock_tool_manager.return_value = mock_tool_manager_instance
            mock_tool_manager_instance.get_tool_definitions.return_value = []
            mock_tool_manager_instance.get_last_sources.return_value = []
            mock_tool_manager_instance.reset_sources.return_value = None

            # Create RAG system
            rag = RAGSystem(test_config)

            # Test edge cases
            edge_cases = [
                "",  # Empty query
                " ",  # Whitespace only
                "a" * 1000,  # Very long query
                "特殊字符",  # Unicode characters
                "query with\nnewlines",  # Newlines in query
                "query with\t\ttabs",  # Tabs in query
            ]

            for query in edge_cases:
                response, sources = rag.query(query)

                # Verify query was processed (even empty/whitespace queries)
                mock_ai_instance.generate_response.assert_called()
                call_args = mock_ai_instance.generate_response.call_args
                assert query in call_args[1]["query"]

                # Reset mock for next iteration
                mock_ai_instance.reset_mock()