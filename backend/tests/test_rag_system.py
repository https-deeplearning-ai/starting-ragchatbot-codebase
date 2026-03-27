"""测试backend/rag_system.py中的RAGSystem类"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from backend.rag_system import RAGSystem


class TestRAGSystem:
    """测试RAGSystem类"""

    def test_rag_system_initialization(self, mock_config):
        """测试RAGSystem初始化"""
        with patch('backend.rag_system.DocumentProcessor') as mock_doc_processor, \
             patch('backend.rag_system.VectorStore') as mock_vector_store, \
             patch('backend.rag_system.AIGenerator') as mock_ai_generator, \
             patch('backend.rag_system.SessionManager') as mock_session_manager, \
             patch('backend.rag_system.CourseSearchTool') as mock_search_tool:

            # 创建RAGSystem实例
            rag = RAGSystem(mock_config)

            # 验证组件被正确初始化
            mock_doc_processor.assert_called_once_with(
                mock_config.CHUNK_SIZE, mock_config.CHUNK_OVERLAP
            )
            mock_vector_store.assert_called_once_with(
                mock_config.CHROMA_PATH,
                mock_config.EMBEDDING_MODEL,
                mock_config.MAX_RESULTS
            )
            mock_ai_generator.assert_called_once_with(
                mock_config.ANTHROPIC_API_KEY,
                mock_config.ANTHROPIC_MODEL
            )
            mock_session_manager.assert_called_once_with(mock_config.MAX_HISTORY)

            # 验证工具系统被正确设置
            assert hasattr(rag, 'tool_manager')
            assert hasattr(rag, 'search_tool')
            mock_search_tool.assert_called_once_with(mock_vector_store.return_value)

    def test_rag_system_query_without_session(self, mock_config):
        """测试无会话ID的查询"""
        with patch('backend.rag_system.DocumentProcessor'), \
             patch('backend.rag_system.VectorStore') as mock_vector_store, \
             patch('backend.rag_system.AIGenerator') as mock_ai_generator, \
             patch('backend.rag_system.SessionManager') as mock_session_manager, \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager') as mock_tool_manager_class:

            # 创建模拟实例
            mock_ai_instance = Mock()
            mock_ai_instance.generate_response.return_value = "AI生成的响应"
            mock_ai_generator.return_value = mock_ai_instance

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [{"name": "search_tool"}]
            mock_tool_manager.get_last_sources.return_value = ["源1", "源2"]
            mock_tool_manager.reset_sources.return_value = None
            mock_tool_manager_class.return_value = mock_tool_manager

            # 创建RAGSystem实例
            rag = RAGSystem(mock_config)
            rag.tool_manager = mock_tool_manager

            # 执行无会话查询
            response, sources = rag.query("测试查询内容")

            # 验证AI生成器被正确调用
            mock_ai_instance.generate_response.assert_called_once_with(
                query="Answer this question about course materials: 测试查询内容",
                conversation_history=None,  # 无会话，历史为空
                tools=[{"name": "search_tool"}],
                tool_manager=mock_tool_manager
            )

            # 验证工具管理器方法被调用
            mock_tool_manager.get_tool_definitions.assert_called_once()
            mock_tool_manager.get_last_sources.assert_called_once()
            mock_tool_manager.reset_sources.assert_called_once()

            # 验证会话管理器未使用（无会话ID）
            mock_session_manager.return_value.get_conversation_history.assert_not_called()
            mock_session_manager.return_value.add_exchange.assert_not_called()

            # 验证返回结果
            assert response == "AI生成的响应"
            assert sources == ["源1", "源2"]

    def test_rag_system_query_with_session(self, mock_config):
        """测试有会话ID的查询"""
        with patch('backend.rag_system.DocumentProcessor'), \
             patch('backend.rag_system.VectorStore'), \
             patch('backend.rag_system.AIGenerator') as mock_ai_generator, \
             patch('backend.rag_system.SessionManager') as mock_session_manager, \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager') as mock_tool_manager_class:

            # 创建模拟实例
            mock_ai_instance = Mock()
            mock_ai_instance.generate_response.return_value = "会话响应"
            mock_ai_generator.return_value = mock_ai_instance

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = [{"name": "search_tool"}]
            mock_tool_manager.get_last_sources.return_value = ["会话源"]
            mock_tool_manager_class.return_value = mock_tool_manager

            mock_session_instance = Mock()
            mock_session_instance.get_conversation_history.return_value = "之前的历史对话"
            mock_session_instance.add_exchange.return_value = None
            mock_session_manager.return_value = mock_session_instance

            # 创建RAGSystem实例
            rag = RAGSystem(mock_config)
            rag.tool_manager = mock_tool_manager
            rag.session_manager = mock_session_instance

            # 执行有会话查询
            response, sources = rag.query("会话中的查询", session_id="test_session_123")

            # 验证会话历史被获取
            mock_session_instance.get_conversation_history.assert_called_once_with("test_session_123")

            # 验证AI生成器被正确调用（包含历史）
            mock_ai_instance.generate_response.assert_called_once_with(
                query="Answer this question about course materials: 会话中的查询",
                conversation_history="之前的历史对话",  # 包含会话历史
                tools=[{"name": "search_tool"}],
                tool_manager=mock_tool_manager
            )

            # 验证会话被更新
            mock_session_instance.add_exchange.assert_called_once_with(
                "test_session_123", "会话中的查询", "会话响应"
            )

            # 验证返回结果
            assert response == "会话响应"
            assert sources == ["会话源"]

    def test_rag_system_query_error_handling(self, mock_config):
        """测试查询过程中的错误处理"""
        with patch('backend.rag_system.DocumentProcessor'), \
             patch('backend.rag_system.VectorStore'), \
             patch('backend.rag_system.AIGenerator') as mock_ai_generator, \
             patch('backend.rag_system.SessionManager'), \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager') as mock_tool_manager_class:

            # 模拟AI生成器抛出异常
            mock_ai_instance = Mock()
            mock_ai_instance.generate_response.side_effect = Exception("AI服务不可用")
            mock_ai_generator.return_value = mock_ai_instance

            mock_tool_manager = Mock()
            mock_tool_manager_class.return_value = mock_tool_manager

            rag = RAGSystem(mock_config)
            rag.tool_manager = mock_tool_manager

            # 验证异常被传播
            with pytest.raises(Exception, match="AI服务不可用"):
                rag.query("测试查询")

    def test_rag_system_add_course_document_success(self, mock_config):
        """测试成功添加单个课程文档"""
        with patch('backend.rag_system.DocumentProcessor') as mock_doc_processor, \
             patch('backend.rag_system.VectorStore') as mock_vector_store, \
             patch('backend.rag_system.AIGenerator'), \
             patch('backend.rag_system.SessionManager'), \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager'):

            # 模拟文档处理器返回结果
            mock_course = Mock()
            mock_course.title = "测试课程"
            mock_chunks = [Mock(), Mock(), Mock()]  # 3个块

            mock_doc_processor.return_value.process_course_document.return_value = (
                mock_course, mock_chunks
            )

            # 创建RAGSystem实例
            rag = RAGSystem(mock_config)

            # 添加课程文档
            course, chunk_count = rag.add_course_document("/path/to/course.txt")

            # 验证文档处理器被调用
            mock_doc_processor.return_value.process_course_document.assert_called_once_with(
                "/path/to/course.txt"
            )

            # 验证向量存储被更新
            mock_vector_store.return_value.add_course_metadata.assert_called_once_with(mock_course)
            mock_vector_store.return_value.add_course_content.assert_called_once_with(mock_chunks)

            # 验证返回结果
            assert course == mock_course
            assert chunk_count == 3

    def test_rag_system_add_course_document_error(self, mock_config):
        """测试添加课程文档时发生错误"""
        with patch('backend.rag_system.DocumentProcessor') as mock_doc_processor, \
             patch('backend.rag_system.VectorStore'), \
             patch('backend.rag_system.AIGenerator'), \
             patch('backend.rag_system.SessionManager'), \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager'):

            # 模拟文档处理器抛出异常
            mock_doc_processor.return_value.process_course_document.side_effect = Exception(
                "文件格式错误"
            )

            rag = RAGSystem(mock_config)

            # 添加课程文档（应捕获异常）
            course, chunk_count = rag.add_course_document("/path/to/invalid.txt")

            # 验证返回None和0（错误情况）
            assert course is None
            assert chunk_count == 0

    def test_rag_system_add_course_folder_success(self, mock_config):
        """测试成功批量添加课程文件夹"""
        with patch('backend.rag_system.DocumentProcessor') as mock_doc_processor, \
             patch('backend.rag_system.VectorStore') as mock_vector_store, \
             patch('backend.rag_system.AIGenerator'), \
             patch('backend.rag_system.SessionManager'), \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager'), \
             patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch('os.path.join') as mock_join:

            # 模拟文件系统
            mock_exists.return_value = True
            mock_listdir.return_value = ["course1.txt", "course2.pdf", "ignore.xyz"]
            mock_isfile.side_effect = lambda x: True  # 所有都是文件
            mock_join.side_effect = lambda *args: "/".join(args)

            # 模拟向量存储返回现有课程标题
            mock_vector_store.return_value.get_existing_course_titles.return_value = []

            # 模拟文档处理器返回课程
            mock_course1 = Mock()
            mock_course1.title = "课程1"
            mock_chunks1 = [Mock(), Mock()]

            mock_course2 = Mock()
            mock_course2.title = "课程2"
            mock_chunks2 = [Mock(), Mock(), Mock()]

            # 第一次调用返回课程1，第二次返回课程2
            mock_doc_processor.return_value.process_course_document.side_effect = [
                (mock_course1, mock_chunks1),
                (mock_course2, mock_chunks2)
            ]

            rag = RAGSystem(mock_config)

            # 添加课程文件夹（不清除现有数据）
            total_courses, total_chunks = rag.add_course_folder("/data/courses", clear_existing=False)

            # 验证不清除现有数据
            mock_vector_store.return_value.clear_all_data.assert_not_called()

            # 验证只处理了支持的格式
            assert mock_doc_processor.return_value.process_course_document.call_count == 2

            # 验证向量存储被更新
            assert mock_vector_store.return_value.add_course_metadata.call_count == 2
            assert mock_vector_store.return_value.add_course_content.call_count == 2

            # 验证返回结果
            assert total_courses == 2
            assert total_chunks == 5  # 2 + 3

    def test_rag_system_add_course_folder_clear_existing(self, mock_config):
        """测试清除现有数据后添加课程文件夹"""
        with patch('backend.rag_system.DocumentProcessor'), \
             patch('backend.rag_system.VectorStore') as mock_vector_store, \
             patch('backend.rag_system.AIGenerator'), \
             patch('backend.rag_system.SessionManager'), \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager'), \
             patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir:

            mock_exists.return_value = True
            mock_listdir.return_value = []  # 空文件夹

            rag = RAGSystem(mock_config)

            # 添加课程文件夹（清除现有数据）
            total_courses, total_chunks = rag.add_course_folder("/data/courses", clear_existing=True)

            # 验证清除现有数据
            mock_vector_store.return_value.clear_all_data.assert_called_once()

            # 验证返回0（空文件夹）
            assert total_courses == 0
            assert total_chunks == 0

    def test_rag_system_add_course_folder_nonexistent(self, mock_config):
        """测试添加不存在的课程文件夹"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False

            with patch('backend.rag_system.DocumentProcessor'), \
                 patch('backend.rag_system.VectorStore'), \
                 patch('backend.rag_system.AIGenerator'), \
                 patch('backend.rag_system.SessionManager'), \
                 patch('backend.rag_system.CourseSearchTool'), \
                 patch('backend.rag_system.ToolManager'):

                rag = RAGSystem(mock_config)

                # 添加不存在的文件夹
                total_courses, total_chunks = rag.add_course_folder("/nonexistent/path")

                # 验证返回0
                assert total_courses == 0
                assert total_chunks == 0

    def test_rag_system_add_course_folder_skip_existing(self, mock_config):
        """测试跳过已存在的课程"""
        with patch('backend.rag_system.DocumentProcessor') as mock_doc_processor, \
             patch('backend.rag_system.VectorStore') as mock_vector_store, \
             patch('backend.rag_system.AIGenerator'), \
             patch('backend.rag_system.SessionManager'), \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager'), \
             patch('os.path.exists') as mock_exists, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isfile') as mock_isfile, \
             patch('os.path.join'):

            mock_exists.return_value = True
            mock_listdir.return_value = ["existing_course.txt", "new_course.txt"]
            mock_isfile.return_value = True

            # 模拟向量存储返回现有课程标题
            mock_vector_store.return_value.get_existing_course_titles.return_value = ["已存在的课程"]

            # 模拟文档处理器
            existing_course = Mock()
            existing_course.title = "已存在的课程"
            existing_chunks = [Mock()]

            new_course = Mock()
            new_course.title = "新课程"
            new_chunks = [Mock(), Mock()]

            mock_doc_processor.return_value.process_course_document.side_effect = [
                (existing_course, existing_chunks),
                (new_course, new_chunks)
            ]

            rag = RAGSystem(mock_config)

            # 添加课程文件夹
            total_courses, total_chunks = rag.add_course_folder("/data/courses")

            # 验证只添加了新课程
            assert mock_vector_store.return_value.add_course_metadata.call_count == 1
            assert mock_vector_store.return_value.add_course_content.call_count == 1

            # 验证返回结果（只添加了1个新课程，2个块）
            assert total_courses == 1
            assert total_chunks == 2

    def test_rag_system_get_course_analytics(self, mock_config):
        """测试获取课程分析信息"""
        with patch('backend.rag_system.DocumentProcessor'), \
             patch('backend.rag_system.VectorStore') as mock_vector_store, \
             patch('backend.rag_system.AIGenerator'), \
             patch('backend.rag_system.SessionManager'), \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager'):

            # 模拟向量存储返回数据
            mock_vector_store.return_value.get_course_count.return_value = 3
            mock_vector_store.return_value.get_existing_course_titles.return_value = [
                "课程A", "课程B", "课程C"
            ]

            rag = RAGSystem(mock_config)

            # 获取分析信息
            analytics = rag.get_course_analytics()

            # 验证向量存储方法被调用
            mock_vector_store.return_value.get_course_count.assert_called_once()
            mock_vector_store.return_value.get_existing_course_titles.assert_called_once()

            # 验证分析信息
            assert analytics["total_courses"] == 3
            assert analytics["course_titles"] == ["课程A", "课程B", "课程C"]

    def test_rag_system_query_prompt_format(self, mock_config):
        """测试查询提示词的格式"""
        with patch('backend.rag_system.DocumentProcessor'), \
             patch('backend.rag_system.VectorStore'), \
             patch('backend.rag_system.AIGenerator') as mock_ai_generator, \
             patch('backend.rag_system.SessionManager'), \
             patch('backend.rag_system.CourseSearchTool'), \
             patch('backend.rag_system.ToolManager') as mock_tool_manager_class:

            mock_ai_instance = Mock()
            mock_ai_instance.generate_response.return_value = "响应"
            mock_ai_generator.return_value = mock_ai_instance

            mock_tool_manager = Mock()
            mock_tool_manager.get_tool_definitions.return_value = []
            mock_tool_manager.get_last_sources.return_value = []
            mock_tool_manager_class.return_value = mock_tool_manager

            rag = RAGSystem(mock_config)
            rag.tool_manager = mock_tool_manager

            # 执行查询
            rag.query("Python编程基础")

            # 验证提示词格式
            mock_ai_instance.generate_response.assert_called_once()
            call_args = mock_ai_instance.generate_response.call_args[1]

            # 验证提示词包含"Answer this question about course materials: "
            assert call_args["query"] == "Answer this question about course materials: Python编程基础"