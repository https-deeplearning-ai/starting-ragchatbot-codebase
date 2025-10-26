#!/usr/bin/env python3
"""
Test RAG system initialization step by step to identify the bottleneck
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_component_initialization():
    """Test each component initialization separately"""

    print("🔍 Testing Component Initialization")
    print("=" * 50)

    # Test config
    print("1. Testing config...")
    try:
        from config import config
        print(f"   ✅ Config loaded")
        print(f"   ANTHROPIC_API_KEY exists: {bool(config.ANTHROPIC_API_KEY)}")
        print(f"   ANTHROPIC_MODEL: {config.ANTHROPIC_MODEL}")
        print(f"   EMBEDDING_MODEL: {config.EMBEDDING_MODEL}")
        print(f"   CHROMA_PATH: {config.CHROMA_PATH}")
    except Exception as e:
        print(f"   ❌ Config failed: {e}")
        return False

    # Test DocumentProcessor
    print("\n2. Testing DocumentProcessor...")
    try:
        from document_processor import DocumentProcessor
        processor = DocumentProcessor(config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        print(f"   ✅ DocumentProcessor initialized")
    except Exception as e:
        print(f"   ❌ DocumentProcessor failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test VectorStore
    print("\n3. Testing VectorStore...")
    try:
        from vector_store import VectorStore
        print(f"   Creating VectorStore with path: {config.CHROMA_PATH}")
        store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
        print(f"   ✅ VectorStore initialized")
    except Exception as e:
        print(f"   ❌ VectorStore failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test AIGenerator
    print("\n4. Testing AIGenerator...")
    try:
        from ai_generator import AIGenerator
        print(f"   Creating AIGenerator with model: {config.ANTHROPIC_MODEL}")
        generator = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)
        print(f"   ✅ AIGenerator initialized")
    except Exception as e:
        print(f"   ❌ AIGenerator failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test SessionManager
    print("\n5. Testing SessionManager...")
    try:
        from session_manager import SessionManager
        session = SessionManager(config.MAX_HISTORY)
        print(f"   ✅ SessionManager initialized")
    except Exception as e:
        print(f"   ❌ SessionManager failed: {e}")
        return False

    # Test ToolManager and tools
    print("\n6. Testing ToolManager and tools...")
    try:
        from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool

        tool_manager = ToolManager()
        print(f"   ✅ ToolManager initialized")

        # Create tools with the vector store
        search_tool = CourseSearchTool(store)
        outline_tool = CourseOutlineTool(store)
        print(f"   ✅ Search tools initialized")

        tool_manager.register_tool(search_tool)
        tool_manager.register_tool(outline_tool)
        print(f"   ✅ Tools registered")

    except Exception as e:
        print(f"   ❌ ToolManager failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test full RAG system
    print("\n7. Testing full RAGSystem...")
    try:
        from rag_system import RAGSystem
        rag = RAGSystem(config)
        print(f"   ✅ RAGSystem initialized")
    except Exception as e:
        print(f"   ❌ RAGSystem failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def test_vector_store_detailed():
    """Test vector store with more detail"""
    print("\n🔍 Detailed VectorStore Test")
    print("=" * 30)

    try:
        from vector_store import VectorStore
        from config import config

        print(f"Initializing VectorStore...")
        print(f"  Path: {config.CHROMA_PATH}")
        print(f"  Model: {config.EMBEDDING_MODEL}")
        print(f"  Max results: {config.MAX_RESULTS}")

        # This might hang, so we'll be careful
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("VectorStore initialization timed out")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)  # 10 second timeout

        try:
            store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
            signal.alarm(0)  # Cancel timeout
            print("  ✅ VectorStore created successfully")

            # Test basic methods
            course_count = store.get_course_count()
            print(f"  ✅ Course count: {course_count}")

            return store

        except TimeoutError:
            print("  ❌ VectorStore initialization timed out!")
            return None

    except Exception as e:
        print(f"  ❌ VectorStore error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run initialization tests"""

    # Test step by step
    success = test_component_initialization()

    if not success:
        print("\n❌ Component initialization failed")
        return False

    # Test vector store in detail
    store = test_vector_store_detailed()

    if store is None:
        print("\n❌ VectorStore seems to be the bottleneck")
        return False

    print("\n✅ All initialization tests passed!")
    print("The components initialize correctly individually.")
    print("The issue might be in the integration or during query processing.")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)