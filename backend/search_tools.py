from typing import Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from vector_store import VectorStore, SearchResults


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
        self,
        query: str,
        course_name: Optional[str] = None,
        lesson_number: Optional[int] = None,
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
        self.last_sources = []  # always reset before searching (prevents stale sources)

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
            if (
                lesson_number is not None
            ):  # explicit None check: 0 is a valid lesson number
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

            # Track source with lesson link for the UI
            source_text = course_title
            if lesson_num is not None:
                source_text += f" - Lesson {lesson_num}"
            lesson_url = (
                self.store.get_lesson_link(course_title, lesson_num)
                if lesson_num is not None
                else None
            )
            sources.append({"text": source_text, "url": lesson_url})

            formatted.append(f"{header}\n{doc}")

        # Store sources for retrieval
        self.last_sources = sources

        return "\n\n".join(formatted)


class CourseOutlineTool(Tool):
    """Tool for retrieving course outline and lesson list from the catalog"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "name": "get_course_outline",
            "description": "Get the full outline (lesson titles and links) for a specific course",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "Course title (partial matches work)",
                    }
                },
                "required": ["course_name"],
            },
        }

    def execute(self, course_name: str) -> str:
        self.last_sources = []
        course_title = self.store._resolve_course_name(course_name)
        if not course_title:
            return f"No course found matching '{course_name}'"

        all_metadata = self.store.get_all_courses_metadata()
        for meta in all_metadata:
            if meta.get("title") == course_title:
                lines = [f"Course: {meta['title']}"]
                if meta.get("course_link"):
                    lines.append(f"Course Link: {meta['course_link']}")
                if meta.get("instructor"):
                    lines.append(f"Instructor: {meta['instructor']}")
                lines.append("")

                # Course link goes to sources, not answer body
                self.last_sources.append(
                    {"text": course_title, "url": meta.get("course_link")}
                )

                for lesson in meta.get("lessons", []):
                    lines.append(
                        f"Lesson {lesson['lesson_number']}: {lesson['lesson_title']}"
                    )
                    lesson_link = lesson.get("lesson_link")
                    if lesson_link:
                        self.last_sources.append(
                            {
                                "text": f"{course_title} - Lesson {lesson['lesson_number']}",
                                "url": lesson_link,
                            }
                        )

                return "\n".join(lines)

        return f"Outline not found for '{course_name}'"


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
