"""Test script to diagnose lesson 5 query issue"""
import sys
sys.path.insert(0, '.')

from config import config
from rag_system import RAGSystem

# Initialize RAG system
print("Initializing RAG system...")
rag_system = RAGSystem(config)

# Load documents
print("Loading documents...")
courses, chunks = rag_system.add_course_folder("../docs", clear_existing=False)
print(f"Loaded {courses} courses with {chunks} chunks\n")

# Test queries that might fail with lesson 5
test_queries = [
    "Lesson 5",
    "Tell me about lesson 5",
    "What is covered in lesson 5?",
    "Show me lesson 5 content",
    "lesson 5",
]

print("="*60)
print("Testing queries related to Lesson 5")
print("="*60)

for query in test_queries:
    print(f"\nQuery: '{query}'")
    print("-" * 60)
    try:
        # Try to execute the query (without API key, will fail at AI step)
        # But we can see if the search part works
        session_id = rag_system.session_manager.create_session()

        # Directly test the search tool
        result = rag_system.search_tool.execute(
            query=query,
            lesson_number=5
        )

        print(f"Search Result:")
        print(result[:200] if len(result) > 200 else result)
        print(f"\nSources: {rag_system.search_tool.last_sources}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    print()

# Also test searching with course name
print("\n" + "="*60)
print("Testing with course name filter")
print("="*60)

try:
    result = rag_system.search_tool.execute(
        query="content",
        course_name="Building Towards Computer Use with Anthropic",
        lesson_number=5
    )
    print(f"Result with full course name:")
    print(result[:300] if len(result) > 300 else result)
    print(f"\nSources: {rag_system.search_tool.last_sources}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Check what's actually in the database for lesson 5
print("\n" + "="*60)
print("Checking database for lesson 5 content")
print("="*60)

try:
    # Search for any content with lesson 5
    results = rag_system.vector_store.search(
        query="lesson content",
        lesson_number=5,
        limit=3
    )

    print(f"Found {len(results.documents)} results")
    if results.error:
        print(f"Error: {results.error}")
    else:
        for i, (doc, meta) in enumerate(zip(results.documents, results.metadata)):
            print(f"\n--- Result {i+1} ---")
            print(f"Metadata: {meta}")
            print(f"Content: {doc[:150]}...")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
