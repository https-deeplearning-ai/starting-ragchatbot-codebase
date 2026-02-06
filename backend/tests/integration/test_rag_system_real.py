"""End-to-end tests for the RAG system with real API calls"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import config
from rag_system import RAGSystem


class TestRAGSystemReal:
    """Tests for RAG system with real components"""

    @pytest.fixture
    def rag_system(self):
        """Create a real RAG system instance"""
        return RAGSystem(config)

    def test_rag_system_initializes(self, rag_system):
        """Test that RAG system initializes without errors"""
        assert rag_system is not None
        assert rag_system.tool_manager is not None
        assert rag_system.ai_generator is not None
        assert rag_system.vector_store is not None

    def test_tools_are_registered(self, rag_system):
        """Test that both tools are registered"""
        tool_names = list(rag_system.tool_manager.tools.keys())

        assert "search_course_content" in tool_names, \
            f"search_course_content not registered. Available: {tool_names}"
        assert "get_course_outline" in tool_names, \
            f"get_course_outline not registered. Available: {tool_names}"

    def test_tool_definitions_are_valid(self, rag_system):
        """Test that tool definitions are properly formatted"""
        definitions = rag_system.tool_manager.get_tool_definitions()

        assert len(definitions) == 2, f"Expected 2 tools, got {len(definitions)}"

        for tool_def in definitions:
            assert "name" in tool_def, "Tool missing 'name'"
            assert "description" in tool_def, "Tool missing 'description'"
            assert "input_schema" in tool_def, "Tool missing 'input_schema'"

    @pytest.mark.skipif(
        not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "test-key",
        reason="Requires valid API key"
    )
    def test_query_returns_response(self, rag_system):
        """Test that query returns a response (real API call)"""
        try:
            response, sources = rag_system.query("What courses are available?")

            print(f"\nQuery: 'What courses are available?'")
            print(f"Response length: {len(response)} chars")
            print(f"Response preview: {response[:200]}...")
            print(f"Sources: {sources}")

            assert response is not None, "Response should not be None"
            assert len(response) > 0, "Response should not be empty"

        except Exception as e:
            pytest.fail(f"RAG query failed with error: {type(e).__name__}: {e}")

    @pytest.mark.skipif(
        not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "test-key",
        reason="Requires valid API key"
    )
    def test_query_content_question(self, rag_system):
        """Test a content-related question (this is what's reportedly failing)"""
        try:
            response, sources = rag_system.query(
                "What is computer use and how does it work?"
            )

            print(f"\nQuery: 'What is computer use and how does it work?'")
            print(f"Response length: {len(response)} chars")
            print(f"Response: {response}")
            print(f"Sources: {sources}")

            # Check for common error indicators
            error_indicators = [
                "not detail content",
                "no relevant content",
                "I don't have",
                "I cannot find",
                "error",
                "failed"
            ]

            response_lower = response.lower()
            for indicator in error_indicators:
                if indicator in response_lower:
                    print(f"\n*** POTENTIAL ISSUE DETECTED: '{indicator}' found in response ***")

            assert response is not None, "Response should not be None"
            assert len(response) > 50, f"Response seems too short: {response}"

        except Exception as e:
            pytest.fail(f"Content query failed with error: {type(e).__name__}: {e}")

    @pytest.mark.skipif(
        not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "test-key",
        reason="Requires valid API key"
    )
    def test_query_specific_course(self, rag_system):
        """Test a question about a specific course"""
        try:
            response, sources = rag_system.query(
                "Tell me about the MCP course"
            )

            print(f"\nQuery: 'Tell me about the MCP course'")
            print(f"Response length: {len(response)} chars")
            print(f"Response: {response}")
            print(f"Sources: {sources}")

            assert response is not None
            assert len(response) > 20

        except Exception as e:
            pytest.fail(f"Specific course query failed: {type(e).__name__}: {e}")


class TestAIGeneratorReal:
    """Test AI Generator with real API calls"""

    @pytest.fixture
    def ai_generator(self):
        """Create real AI generator"""
        from ai_generator import AIGenerator
        return AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)

    @pytest.mark.skipif(
        not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "test-key",
        reason="Requires valid API key"
    )
    def test_simple_response(self, ai_generator):
        """Test simple response without tools"""
        try:
            response = ai_generator.generate_response("Say hello")

            print(f"\nSimple response: {response}")

            assert response is not None
            assert len(response) > 0

        except Exception as e:
            pytest.fail(
                f"AI Generator failed: {type(e).__name__}: {e}\n"
                f"This may indicate an issue with the API key or model name '{config.ANTHROPIC_MODEL}'"
            )

    @pytest.mark.skipif(
        not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "test-key",
        reason="Requires valid API key"
    )
    def test_response_with_tools(self, ai_generator):
        """Test response with tools provided"""
        from search_tools import CourseSearchTool, ToolManager
        from vector_store import VectorStore

        # Create real vector store and tools
        chroma_path = config.CHROMA_PATH
        if not os.path.isabs(chroma_path):
            backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            chroma_path = os.path.normpath(os.path.join(backend_dir, chroma_path))

        store = VectorStore(
            chroma_path=chroma_path,
            embedding_model=config.EMBEDDING_MODEL,
            max_results=config.MAX_RESULTS
        )

        tool_manager = ToolManager()
        search_tool = CourseSearchTool(store)
        tool_manager.register_tool(search_tool)

        tools = tool_manager.get_tool_definitions()

        try:
            response = ai_generator.generate_response(
                "Search for information about computer use in the courses",
                tools=tools,
                tool_manager=tool_manager
            )

            print(f"\nTool-enabled response: {response}")
            print(f"Last sources: {tool_manager.get_last_sources()}")

            assert response is not None

        except Exception as e:
            pytest.fail(f"Tool-enabled response failed: {type(e).__name__}: {e}")


class TestDiagnoseNotDetailContent:
    """Specific tests to diagnose 'not detail content' issue"""

    @pytest.mark.skipif(
        not config.ANTHROPIC_API_KEY or config.ANTHROPIC_API_KEY == "test-key",
        reason="Requires valid API key"
    )
    def test_step_by_step_query_flow(self):
        """Step through the query flow to identify where it breaks"""
        from ai_generator import AIGenerator
        from vector_store import VectorStore
        from search_tools import CourseSearchTool, ToolManager

        print("\n" + "="*60)
        print("STEP-BY-STEP DIAGNOSTIC")
        print("="*60)

        # Step 1: Initialize components
        print("\n1. Initializing components...")
        chroma_path = config.CHROMA_PATH
        if not os.path.isabs(chroma_path):
            backend_dir = os.path.join(os.path.dirname(__file__), '..', '..')
            chroma_path = os.path.normpath(os.path.join(backend_dir, chroma_path))

        store = VectorStore(
            chroma_path=chroma_path,
            embedding_model=config.EMBEDDING_MODEL,
            max_results=config.MAX_RESULTS
        )
        print(f"   VectorStore initialized with {store.get_course_count()} courses")

        # Step 2: Test direct search
        print("\n2. Testing direct search...")
        results = store.search("computer use")
        print(f"   Search returned {len(results.documents)} documents")
        if results.documents:
            print(f"   First result preview: {results.documents[0][:100]}...")
        else:
            print("   *** WARNING: No documents returned from search ***")

        # Step 3: Test search tool
        print("\n3. Testing CourseSearchTool...")
        search_tool = CourseSearchTool(store)
        tool_result = search_tool.execute(query="computer use")
        print(f"   Tool result length: {len(tool_result)} chars")
        print(f"   Tool result preview: {tool_result[:200]}...")

        # Step 4: Initialize AI generator
        print("\n4. Initializing AI generator...")
        print(f"   Model: {config.ANTHROPIC_MODEL}")
        ai_gen = AIGenerator(config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL)

        # Step 5: Test AI response without tools
        print("\n5. Testing AI response without tools...")
        try:
            simple_response = ai_gen.generate_response("Say 'test successful'")
            print(f"   Response: {simple_response[:100]}...")
        except Exception as e:
            print(f"   *** FAILURE: {type(e).__name__}: {e} ***")
            pytest.fail(f"AI generator failed without tools: {e}")

        # Step 6: Test AI response with tools
        print("\n6. Testing AI response with tools...")
        tool_manager = ToolManager()
        tool_manager.register_tool(search_tool)
        tools = tool_manager.get_tool_definitions()

        try:
            tool_response = ai_gen.generate_response(
                "What is computer use? Search for it in the course materials.",
                tools=tools,
                tool_manager=tool_manager
            )
            print(f"   Response: {tool_response[:300]}...")
            print(f"   Sources captured: {len(tool_manager.get_last_sources())}")

            # Check for error indicators
            if "not detail content" in tool_response.lower():
                print("\n   *** 'not detail content' FOUND IN RESPONSE ***")
                print("   This indicates the AI is generating this text, not the search tool")

        except Exception as e:
            print(f"   *** FAILURE: {type(e).__name__}: {e} ***")
            pytest.fail(f"AI generator failed with tools: {e}")

        print("\n" + "="*60)
        print("DIAGNOSTIC COMPLETE")
        print("="*60)

        assert True  # Always pass - this is for diagnostics
