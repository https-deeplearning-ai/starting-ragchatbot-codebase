"""
Integration diagnostic script - Test RAG system components
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import Mock, patch
from backend.search_tools import CourseSearchTool
from backend.vector_store import SearchResults

print("=" * 80)
print("RAG System Diagnostic Tests")
print("=" * 80)

# Test 1: CourseSearchTool - Empty results
print("\n[Test 1] CourseSearchTool.execute() - Empty results")
try:
    mock_store = Mock()
    mock_store.search.return_value = SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )
    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="test query")
    
    if "No relevant content found" in result:
        print("[PASS] Correctly handles empty results")
    else:
        print("[FAIL] Did not handle empty results correctly")
        print(f"  Returned: {result}")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 2: CourseSearchTool - Valid results
print("\n[Test 2] CourseSearchTool.execute() - Valid results")
try:
    mock_store = Mock()
    mock_store.search.return_value = SearchResults(
        documents=["Python basics content"],
        metadata=[{"course_title": "Python 101", "lesson_number": 1}],
        distances=[0.1]
    )
    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="Python basics")
    
    if "Python 101" in result and "Python basics content" in result:
        print("[PASS] Correctly formats search results")
        print(f"  Result: {result[:100]}...")
    else:
        print("[FAIL] Did not format search results correctly")
        print(f"  Returned: {result}")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 3: AIGenerator - Check import
print("\n[Test 3] AIGenerator import")
try:
    from backend.ai_generator import AIGenerator
    print("[PASS] AIGenerator imported successfully")
except Exception as e:
    print(f"[FAIL] AIGenerator import failed - {e}")

# Test 4: RAGSystem - Check import
print("\n[Test 4] RAGSystem import")
try:
    from backend.rag_system import RAGSystem
    print("[PASS] RAGSystem imported successfully")
except Exception as e:
    print(f"[FAIL] RAGSystem import failed - {e}")

# Test 5: Check API key
print("\n[Test 5] Environment configuration check")
try:
    from backend.config import config
    if config.ANTHROPIC_API_KEY:
        print("[PASS] ANTHROPIC_API_KEY is set")
    else:
        print("[FAIL] ANTHROPIC_API_KEY is not set")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 6: Check vector store
print("\n[Test 6] Vector store check")
try:
    from backend.vector_store import VectorStore
    from backend.config import config
    
    store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL)
    course_count = store.get_course_count()
    print("[PASS] Vector store is accessible")
    print(f"  Current course count: {course_count}")
    
    if course_count == 0:
        print("  [WARNING] No course data in vector store")
        print("  This may be the cause of 'query failed' errors")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 7: SessionManager
print("\n[Test 7] SessionManager check")
try:
    from backend.session_manager import SessionManager
    
    manager = SessionManager(max_history=2)
    session_id = manager.create_session()
    print("[PASS] SessionManager works correctly")
    print(f"  Created session ID: {session_id}")
except Exception as e:
    print(f"[ERROR] {e}")

# Test 8: Test RAG query with mock data
print("\n[Test 8] RAG query with mock data")
try:
    from backend.rag_system import RAGSystem
    from backend.config import config
    
    with patch('backend.rag_system.DocumentProcessor'), \
         patch('backend.rag_system.VectorStore') as mock_vs, \
         patch('backend.rag_system.AIGenerator') as mock_ai, \
         patch('backend.rag_system.SessionManager'), \
         patch('backend.rag_system.ToolManager'), \
         patch('backend.rag_system.CourseSearchTool'):
        
        rag = RAGSystem(config)
        
        # Mock the AI generator to return a response
        rag.ai_generator.generate_response = Mock(return_value="Test response")
        rag.session_manager.create_session = Mock(return_value="session_1")
        rag.tool_manager.get_last_sources = Mock(return_value=[])
        
        answer, sources = rag.query("What is Python?")
        
        if answer == "Test response":
            print("[PASS] RAG query works with mocked components")
        else:
            print("[FAIL] RAG query did not return expected response")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 80)
print("Diagnostic tests completed")
print("=" * 80)
