from typing import List, Tuple, Optional, Dict
import os
from document_processor import DocumentProcessor
from vector_store import VectorStore
from ai_generator import AIGenerator
from session_manager import SessionManager
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool
from models import Course, Lesson, CourseChunk

class RAGSystem:
    """Main orchestrator for the Retrieval-Augmented Generation system"""
    
    def __init__(self, config):
        self.config = config
        
        # Initialize core components
        self.document_processor = DocumentProcessor(config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        self.vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
        self.ai_generator = AIGenerator(config.MINMAX_API_KEY, config.MINMAX_BASE_URL, config.MINMAX_MODEL)
        self.session_manager = SessionManager(config.MAX_HISTORY)
        
        # Initialize search tools
        self.tool_manager = ToolManager()
        self.search_tool = CourseSearchTool(self.vector_store)
        self.outline_tool = CourseOutlineTool(self.vector_store)
        self.tool_manager.register_tool(self.search_tool)
        self.tool_manager.register_tool(self.outline_tool)
    
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
            course, course_chunks = self.document_processor.process_course_document(file_path)
            
            # Add course metadata to vector store for semantic search
            self.vector_store.add_course_metadata(course)
            
            # Add course content chunks to vector store
            self.vector_store.add_course_content(course_chunks)
            
            return course, len(course_chunks)
        except Exception as e:
            print(f"Error processing course document {file_path}: {e}")
            return None, 0
    
    def add_course_folder(self, folder_path: str, clear_existing: bool = False) -> Tuple[int, int]:
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
            if os.path.isfile(file_path) and file_name.lower().endswith(('.pdf', '.docx', '.txt')):
                try:
                    # Check if this course might already exist
                    # We'll process the document to get the course ID, but only add if new
                    course, course_chunks = self.document_processor.process_course_document(file_path)
                    
                    if course and course.title not in existing_course_titles:
                        # This is a new course - add it to the vector store
                        self.vector_store.add_course_metadata(course)
                        self.vector_store.add_course_content(course_chunks)
                        total_courses += 1
                        total_chunks += len(course_chunks)
                        print(f"Added new course: {course.title} ({len(course_chunks)} chunks)")
                        existing_course_titles.add(course.title)
                    elif course:
                        print(f"Course already exists: {course.title} - skipping")
                except Exception as e:
                    print(f"Error processing {file_name}: {e}")
        
        return total_courses, total_chunks
    
    def query(self, query: str, session_id: Optional[str] = None) -> Tuple[str, List[str]]:
        """
        Process a user query using the RAG system with pre-search approach.

        Args:
            query: User's question
            session_id: Optional session ID for conversation context

        Returns:
            Tuple of (response, sources list)
        """
        # Step 1: Search for relevant content first (instead of using tool calling)
        search_results = self.vector_store.search(query=query, limit=5)

        # Step 2: Build context from search results
        context = ""
        sources = []

        if not search_results.is_empty() and search_results.documents:
            context_parts = []
            for doc, meta in zip(search_results.documents, search_results.metadata):
                course_title = meta.get('course_title', 'unknown')
                lesson_num = meta.get('lesson_number')

                # Build header
                header = f"[{course_title}"
                if lesson_num is not None:
                    header += f" - Lesson {lesson_num}"
                header += "]"

                context_parts.append(f"{header}\n{doc}")

                # Track source with link
                source_name = course_title
                if lesson_num is not None:
                    source_name += f" - Lesson {lesson_num}"

                # Get link
                course_link = self.vector_store.get_course_link(course_title)
                lesson_link = None
                if lesson_num is not None:
                    lesson_link = self.vector_store.get_lesson_link(course_title, lesson_num)
                link = lesson_link or course_link

                source_with_link = f"{source_name}|{link}" if link else source_name
                sources.append(source_with_link)

            context = "\n\n".join(context_parts)
            context = f"Here are relevant course materials:\n\n{context}\n\n"
        else:
            context = "No relevant course materials found.\n\n"

        # Step 3: Create prompt with context injected
        if context:
            prompt = f"""{context}Answer this question about course materials: {query}"""
        else:
            prompt = f"""Answer this question about course materials: {query}"""

        # Get conversation history if session exists
        history = None
        if session_id:
            history = self.session_manager.get_conversation_history(session_id)

        # Generate response using AI (without tools - we did search manually)
        response = self.ai_generator.generate_response(
            query=prompt,
            conversation_history=history,
            tools=None,  # No tools - we pre-searched
            tool_manager=None
        )

        # Update conversation history
        if session_id:
            self.session_manager.add_exchange(session_id, query, response)

        # Return response with sources
        return response, sources
    
    def get_course_analytics(self) -> Dict:
        """Get analytics about the course catalog"""
        return {
            "total_courses": self.vector_store.get_course_count(),
            "course_titles": self.vector_store.get_existing_course_titles()
        }