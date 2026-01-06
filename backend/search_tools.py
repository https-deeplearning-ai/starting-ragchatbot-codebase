from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from vector_store import SearchResults, VectorStore


class Tool(ABC):
    """Abstract base class for all tools"""

    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "search_course_content",
            "description": "Search course materials with smart course name matching and lesson filtering",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the course content",
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')",
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Specific lesson number to search within (e.g. 1, 2, 3)",
                    },
                },
                "required": ["query"],
            },
        }

    def execute(
        self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None
    ) -> str:
        """
        Execute the search tool with given parameters.

        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter

        Returns:
            Formatted search results or error message
        """

        # Use the vector store's unified search interface
        results = self.store.search(
            query=query, course_name=course_name, lesson_number=lesson_number
        )

        # Handle errors
        if results.error:
            return results.error

        # Handle empty results
        if results.is_empty():
            filter_info = ""
            if course_name:
                filter_info += f" in course '{course_name}'"
            if lesson_number:
                filter_info += f" in lesson {lesson_number}"
            return f"No relevant content found{filter_info}."

        # Format and return results
        return self._format_results(results)

    def _format_results(self, results: SearchResults) -> str:
        """Format search results with course and lesson context"""
        formatted = []
        sources = []  # Track sources for the UI

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get("course_title", "unknown")
            lesson_num = meta.get("lesson_number")

            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"

            # Track source for the UI - now with link
            source_text = course_title
            if lesson_num is not None:
                source_text += f" - Lesson {lesson_num}"

            # Get lesson or course link
            link = None
            source_type = "course"
            try:
                if lesson_num is not None:
                    link = self.store.get_lesson_link(course_title, lesson_num)
                    source_type = "lesson"

                # Fallback to course link if lesson link unavailable
                if not link:
                    link = self.store.get_course_link(course_title)
                    source_type = "course"
            except Exception as e:
                print(f"Error retrieving link for {course_title}: {e}")
                link = None  # Fallback to None

            # Create structured source object
            sources.append({"text": source_text, "link": link, "type": source_type})

            formatted.append(f"{header}\n{doc}")

        # Store sources for retrieval
        self.last_sources = sources

        return "\n\n".join(formatted)


class CourseOutlineTool(Tool):
    """Tool for retrieving complete course outlines and lesson structures"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources for UI display

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for course outline retrieval"""
        return {
            "name": "get_course_outline",
            "description": "Retrieve the complete structure and lesson list for a specific course. Use this for questions about course topics, lesson structure, what's covered in a course, or course overview questions. DO NOT use for searching lesson content.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "Course title or partial name (e.g., 'MCP', 'Introduction to Python'). Fuzzy matching is supported.",
                    }
                },
                "required": ["course_name"],
            },
        }

    def execute(self, course_name: str) -> str:
        """
        Execute the outline tool to retrieve course structure.

        Args:
            course_name: Course title or partial match

        Returns:
            Formatted course outline or error message
        """
        # Get course outline from vector store
        outline = self.store.get_course_outline(course_name)

        # Handle course not found
        if not outline:
            return f"No course found matching '{course_name}'. Please check the course name and try again."

        # Format and return results
        return self._format_outline(outline)

    def _format_outline(self, outline: Dict[str, Any]) -> str:
        """Format course outline for AI consumption"""
        # Build header with course metadata
        formatted_parts = [f"Course: {outline['title']}"]

        if outline.get("instructor"):
            formatted_parts.append(f"Instructor: {outline['instructor']}")

        formatted_parts.append(f"Total Lessons: {outline['lesson_count']}")
        formatted_parts.append("")  # Blank line
        formatted_parts.append("Lesson Structure:")

        # Add each lesson
        for lesson in outline.get("lessons", []):
            lesson_line = f"  Lesson {lesson['lesson_number']}: {lesson['lesson_title']}"
            formatted_parts.append(lesson_line)

        # Track source for UI display
        self.last_sources = [
            {"text": outline["title"], "link": outline.get("course_link"), "type": "course"}
        ]

        return "\n".join(formatted_parts)


class ToolManager:
    """Manages available tools for the AI"""

    def __init__(self):
        self.tools = {}

    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Anthropic tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"

        return self.tools[tool_name].execute(**kwargs)

    def get_last_sources(self) -> list:
        """Get sources from the last search operation"""
        # Check all tools for last_sources attribute
        for tool in self.tools.values():
            if hasattr(tool, "last_sources") and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, "last_sources"):
                tool.last_sources = []
