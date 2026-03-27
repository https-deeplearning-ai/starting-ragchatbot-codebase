import pytest
from unittest.mock import Mock, MagicMock
import sys
import os

# 添加项目根目录到Python路径，以便导入backend模块
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, project_root)

@pytest.fixture
def mock_vector_store():
    """Mock VectorStore fixture"""
    store = Mock()
    store.search = Mock()
    store.add_course_metadata = Mock()
    store.add_course_content = Mock()
    store.clear_all_data = Mock()
    store.get_existing_course_titles = Mock(return_value=[])
    store.get_course_count = Mock(return_value=0)
    return store

@pytest.fixture
def mock_search_results():
    """Mock SearchResults fixture"""
    results = Mock()
    results.documents = ["测试文档内容1", "测试文档内容2"]
    results.metadata = [
        {"course_title": "测试课程A", "lesson_number": 1},
        {"course_title": "测试课程A", "lesson_number": 2}
    ]
    results.distances = [0.1, 0.2]
    results.error = None
    results.is_empty = Mock(return_value=False)
    return results

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client fixture"""
    client = Mock()
    client.messages = Mock()
    return client

@pytest.fixture
def mock_tool_manager():
    """Mock ToolManager fixture"""
    manager = Mock()
    manager.execute_tool = Mock()
    manager.get_tool_definitions = Mock(return_value=[])
    manager.get_last_sources = Mock(return_value=[])
    manager.reset_sources = Mock()
    return manager

@pytest.fixture
def mock_config():
    """Mock Config fixture"""
    config = Mock()
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_RESULTS = 5
    config.MAX_HISTORY = 2
    config.CHROMA_PATH = "./test_chroma_db"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.ANTHROPIC_API_KEY = "test_key"
    config.ANTHROPIC_MODEL = "claude-test-model"
    return config