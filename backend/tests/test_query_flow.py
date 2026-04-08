"""
Detailed test of the complete query flow to identify where 'query failed' occurs
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from unittest.mock import Mock, patch, MagicMock
from backend.search_tools import CourseSearchTool
from backend.vector_store import SearchResults

print("=" * 80)
print("DETAILED QUERY FLOW ANALYSIS")
print("=" * 80)

# Scenario 1: Empty vector store (current state)
print("\n[Scenario 1] Query with EMPTY vector store (current state)")
print("-" * 80)
try:
    from backend.rag_system import RAGSystem
    from backend.config import config
    
    # Create RAG system with real components
    rag = RAGSystem(config)
    
    # Check vector store state
    course_count = rag.vector_store.get_course_count()
    print(f"Vector store course count: {course_count}")
    
    if course_count == 0:
        print("[ISSUE] Vector store is EMPTY - this is the problem!")
        print("When CourseSearchTool searches, it will find no results")
        print("This causes the AI to have no context to answer questions")
    
except Exception as e:
    print(f"[ERROR] {e}")

# Scenario 2: Simulate what happens when AI tries to use search tool with empty store
print("\n[Scenario 2] Simulating tool execution with empty store")
print("-" * 80)
try:
    from backend.rag_system import RAGSystem
    from backend.config import config
    
    rag = RAGSystem(config)
    
    # Simulate a search with empty store
    search_results = rag.vector_store.search(
        query="What is Python?",
        course_name=None,
        lesson_number=None
    )
    
    print(f"Search results empty: {search_results.is_empty()}")
    print(f"Search error: {search_results.error}")
    
    # Now see what CourseSearchTool returns
    tool_result = rag.search_tool.execute(query="What is Python?")
    print(f"Tool result: {tool_result}")
    
    if "No relevant content found" in tool_result:
        print("[ISSUE] Tool returns 'No relevant content found'")
        print("This is passed to the AI, which may cause it to fail")
    
except Exception as e:
    print(f"[ERROR] {e}")

# Scenario 3: Test with mock data to see if system works when data exists
print("\n[Scenario 3] Testing with MOCK course data")
print("-" * 80)
try:
    from backend.rag_system import RAGSystem
    from backend.config import config
    from backend.vector_store import SearchResults
    
    with patch('backend.rag_system.VectorStore') as mock_vs_class:
        # Create mock vector store that returns results
        mock_vs = Mock()
        mock_vs_class.return_value = mock_vs
        
        # Mock search to return results
        mock_vs.search.return_value = SearchResults(
            documents=["Python is a programming language used for web development, data science, and automation."],
            metadata=[{"course_title": "Python 101", "lesson_number": 1}],
            distances=[0.1]
        )
        mock_vs.get_course_count.return_value = 1
        mock_vs.get_existing_course_titles.return_value = ["Python 101"]
        
        rag = RAGSystem(config)
        
        # Now test the search tool
        tool_result = rag.search_tool.execute(query="What is Python?")
        print(f"Tool result with mock data: {tool_result[:100]}...")
        
        if "Python 101" in tool_result:
            print("[SUCCESS] Tool returns relevant content when data exists")
        
except Exception as e:
    print(f"[ERROR] {e}")

# Scenario 4: Identify the exact failure point in the API
print("\n[Scenario 4] Tracing API request failure")
print("-" * 80)
print("When user sends POST /api/query:")
print("1. app.py calls rag_system.query()")
print("2. rag_system.query() calls ai_generator.generate_response()")
print("3. ai_generator calls Claude API with tools")
print("4. Claude may call search_course_content tool")
print("5. search_course_content calls vector_store.search()")
print("6. vector_store.search() returns EMPTY results (no courses)")
print("7. CourseSearchTool formats empty results as 'No relevant content found'")
print("8. Claude receives 'No relevant content found' as tool result")
print("9. Claude may fail to generate a meaningful response")
print("10. API returns 500 error or 'query failed'")
print("\n[ROOT CAUSE] No course data in vector store!")

# Scenario 5: Check if there's a way to add sample data
print("\n[Scenario 5] Checking document loading mechanism")
print("-" * 80)
try:
    docs_path = "docs"
    if os.path.exists(docs_path):
        files = os.listdir(docs_path)
        print(f"Found docs directory with {len(files)} files:")
        for f in files[:5]:
            print(f"  - {f}")
        print("\n[SOLUTION] Add course documents to the docs/ directory")
        print("Then call rag_system.add_course_folder('docs')")
    else:
        print(f"[WARNING] docs directory not found at {docs_path}")
        print("Create docs/ directory and add course documents there")
except Exception as e:
    print(f"[ERROR] {e}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
