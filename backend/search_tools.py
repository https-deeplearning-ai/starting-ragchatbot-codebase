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
            "description": "Search course materials with smart course name matching and lesson filtering. IMPORTANT: When the user asks about a specific lesson (e.g. 'lesson 5', 'lesson 3'), you MUST use the lesson_number parameter to filter results. When a course is mentioned (e.g. 'MCP course', 'Computer Use'), use the course_name parameter.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in the course content (use general terms like 'content', 'topics covered', 'main concepts')"
                    },
                    "course_name": {
                        "type": "string",
                        "description": "Course title to filter by (partial matches work, e.g. 'MCP', 'Computer Use', 'Chroma'). Extract from user query."
                    },
                    "lesson_number": {
                        "type": "integer",
                        "description": "Lesson number to filter by. MUST be used when user mentions a specific lesson (e.g. 'lesson 5' -> 5, 'lesson 3' -> 3)"
                    }
                },
                "required": ["query"]
            }
        }
    
    def execute(self, query: str, course_name: Optional[str] = None, lesson_number: Optional[int] = None) -> str:
        """
        Execute the search tool with given parameters.

        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter

        Returns:
            Formatted search results or error message
        """
        # Handle string 'None' from AI tool calls (AI sometimes passes "None" as string)
        if course_name == 'None' or course_name == 'null':
            course_name = None
        if lesson_number == 'None' or lesson_number == 'null':
            lesson_number = None

        # Use the vector store's unified search interface
        results = self.store.search(
            query=query,
            course_name=course_name,
            lesson_number=lesson_number
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
        sources_dict = {}  # Deduplicate by source text

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')

            # Build context header for Claude
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"

            # Build source text
            source_text = course_title
            if lesson_num is not None:
                source_text += f" - Lesson {lesson_num}"

            # Get link (deduplicated)
            if source_text not in sources_dict:
                link = None
                if lesson_num is not None:
                    link = self.store.get_lesson_link(course_title, lesson_num)
                if link is None:
                    link = self.store.get_course_link(course_title)

                sources_dict[source_text] = {"text": source_text, "link": link}

            formatted.append(f"{header}\n{doc}")

        # Store sources for retrieval (deduplicated list)
        self.last_sources = list(sources_dict.values())

        return "\n\n".join(formatted)


class CourseOutlineTool(Tool):
    """Tool for retrieving course outlines with lesson lists"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources for citation

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return Anthropic tool definition for this tool"""
        return {
            "name": "get_course_outline",
            "description": "Get the complete outline of a course including all lessons. Use this when users ask about course structure, lesson lists, what topics a course covers, or want an overview of a course.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "course_name": {
                        "type": "string",
                        "description": "Course title to get outline for (partial matches work, e.g. 'MCP', 'Introduction')"
                    }
                },
                "required": ["course_name"]
            }
        }

    def execute(self, course_name: str) -> str:
        """
        Execute the outline tool to retrieve course structure.

        Args:
            course_name: Course name (partial/fuzzy matching supported)

        Returns:
            Formatted course outline or error message
        """
        # Step 1: Resolve fuzzy course name to exact title
        resolved_title = self.store._resolve_course_name(course_name)

        if not resolved_title:
            return f"No course found matching '{course_name}'"

        # Step 2: Get course outline
        outline = self.store.get_course_outline(resolved_title)

        if not outline:
            return f"Could not retrieve outline for course '{resolved_title}'"

        # Step 3: Track source for citation
        self.last_sources = [{
            "text": outline['title'],
            "link": outline.get('course_link')
        }]

        # Step 4: Format and return outline
        return self._format_outline(outline)

    def _format_outline(self, outline: Dict[str, Any]) -> str:
        """Format course outline for Claude to present to users"""
        parts = [f"Course: {outline['title']}"]

        if outline.get('instructor'):
            parts.append(f"Instructor: {outline['instructor']}")

        if outline.get('course_link'):
            parts.append(f"Course Link: {outline['course_link']}")

        parts.append(f"Total Lessons: {outline.get('lesson_count', 0)}")
        parts.append("")  # Empty line before lessons
        parts.append("Lessons:")

        # Format each lesson
        lessons = outline.get('lessons', [])
        if lessons:
            for lesson in lessons:
                lesson_num = lesson.get('lesson_number', '?')
                lesson_title = lesson.get('lesson_title', 'Untitled')
                parts.append(f"{lesson_num}. {lesson_title}")
        else:
            parts.append("No lessons found.")

        return "\n".join(parts)


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
            if hasattr(tool, 'last_sources') and tool.last_sources:
                return tool.last_sources
        return []

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []