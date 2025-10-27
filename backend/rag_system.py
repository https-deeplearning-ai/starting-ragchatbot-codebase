import os
from typing import Dict, List, Optional, Tuple

from ai_generator import AIGenerator
from document_processor import DocumentProcessor
from models import Course, CourseChunk, Lesson
from search_tools import CourseOutlineTool, CourseSearchTool, ToolManager
from session_manager import SessionManager
from vector_store import VectorStore


class RAGSystem:
    """Main orchestrator for the Retrieval-Augmented Generation system with lazy loading"""

    def __init__(self, config):
        self.config = config
        self._document_processor = None
        self._vector_store = None
        self._ai_generator = None
        self._session_manager = None
        self._tool_manager = None
        self._search_tool = None
        self._outline_tool = None
        self._initialized = False

    @property
    def document_processor(self):
        """Lazy load document processor"""
        if self._document_processor is None:
            self._document_processor = DocumentProcessor(
                self.config.CHUNK_SIZE, self.config.CHUNK_OVERLAP
            )
        return self._document_processor

    @property
    def vector_store(self):
        """Lazy load vector store (most expensive component)"""
        if self._vector_store is None:
            print("🔧 Initializing VectorStore (lazy loading)...")
            self._vector_store = VectorStore(
                self.config.CHROMA_PATH, self.config.EMBEDDING_MODEL, self.config.MAX_RESULTS
            )
            print("✅ VectorStore initialized")
        return self._vector_store

    @property
    def ai_generator(self):
        """Lazy load AI generator"""
        if self._ai_generator is None:
            self._ai_generator = AIGenerator(
                self.config.ANTHROPIC_API_KEY, self.config.ANTHROPIC_MODEL
            )
        return self._ai_generator

    @property
    def session_manager(self):
        """Lazy load session manager"""
        if self._session_manager is None:
            self._session_manager = SessionManager(self.config.MAX_HISTORY)
        return self._session_manager

    @property
    def tool_manager(self):
        """Lazy load tool manager"""
        if self._tool_manager is None:
            self._tool_manager = ToolManager()
            self._search_tool = CourseSearchTool(self.vector_store)
            self._outline_tool = CourseOutlineTool(self.vector_store)
            self._tool_manager.register_tool(self._search_tool)
            self._tool_manager.register_tool(self._outline_tool)
        return self._tool_manager

    def initialize_components(self):
        """Pre-initialize all components (optional for faster startup)"""
        if not self._initialized:
            print("🚀 Pre-initializing all components...")
            # Access all properties to trigger lazy loading
            _ = self.document_processor
            _ = self.vector_store
            _ = self.ai_generator
            _ = self.session_manager
            _ = self.tool_manager
            self._initialized = True
            print("✅ All components initialized")

    def add_course_document(self, file_path: str) -> Tuple[Course, int]:
        """
        Add a single course document to the knowledge base.

        Args:
            file_path: Path to the course document

        Returns:
            Tuple of (Course object, number of chunks created)
        """
        try:
            # Process the document
            course, course_chunks = self.document_processor.process_course_document(
                file_path
            )

            # Add course metadata to vector store for semantic search
            self.vector_store.add_course_metadata(course)

            # Add course content chunks to vector store
            self.vector_store.add_course_content(course_chunks)

            return course, len(course_chunks)
        except Exception as e:
            print(f"Error processing course document {file_path}: {e}")
            return None, 0

    def add_course_folder(
        self, folder_path: str, clear_existing: bool = False
    ) -> Tuple[int, int]:
        """
        Add all course documents from a folder.

        Args:
            folder_path: Path to folder containing course documents
            clear_existing: Whether to clear existing data first

        Returns:
            Tuple of (total courses added, total chunks created)
        """
        total_courses = 0
        total_chunks = 0

        # Clear existing data if requested
        if clear_existing:
            print("Clearing existing data for fresh rebuild...")
            self.vector_store.clear_all_data()

        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            return 0, 0

        # Get existing course titles to avoid re-processing
        existing_course_titles = set(self.vector_store.get_existing_course_titles())

        # Process each file in the folder
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path) and file_name.lower().endswith(
                (".pdf", ".docx", ".txt")
            ):
                try:
                    # Check if this course might already exist
                    # We'll process the document to get the course ID, but only add if new
                    course, course_chunks = (
                        self.document_processor.process_course_document(file_path)
                    )

                    if course and course.title not in existing_course_titles:
                        # This is a new course - add it to the vector store
                        self.vector_store.add_course_metadata(course)
                        self.vector_store.add_course_content(course_chunks)
                        total_courses += 1
                        total_chunks += len(course_chunks)
                        print(
                            f"Added new course: {course.title} ({len(course_chunks)} chunks)"
                        )
                        existing_course_titles.add(course.title)
                    elif course:
                        print(f"Course already exists: {course.title} - skipping")
                except Exception as e:
                    print(f"Error processing {file_name}: {e}")

        return total_courses, total_chunks

    def query(
        self, query: str, session_id: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """
        Process a user query using the RAG system with tool-based search.

        Args:
            query: User's question
            session_id: Optional session ID for conversation context

        Returns:
            Tuple of (response, sources list - empty for tool-based approach)
        """
        # Create prompt for the AI with clear instructions
        prompt = f"""Answer this question about course materials: {query}"""

        # Get conversation history if session exists
        history = None
        if session_id:
            history = self.session_manager.get_conversation_history(session_id)

        # Generate response using AI with tools
        response = self.ai_generator.generate_response(
            query=prompt,
            conversation_history=history,
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager,
        )

        # Get sources from the search tool
        sources = self.tool_manager.get_last_sources()

        # Reset sources after retrieving them
        self.tool_manager.reset_sources()

        # Update conversation history
        if session_id:
            self.session_manager.add_exchange(session_id, query, response)

        # Return response with sources from tool searches
        return response, sources

    def get_course_analytics(self) -> Dict:
        """Get analytics about the course catalog"""
        return {
            "total_courses": self.vector_store.get_course_count(),
            "course_titles": self.vector_store.get_existing_course_titles(),
        }
