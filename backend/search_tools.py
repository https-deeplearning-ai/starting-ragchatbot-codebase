from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from vector_store import VectorStore, SearchResults


class Tool(ABC):
    """Abstract base class for all tools"""

    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return tool definition for this tool"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters"""
        pass


class CourseOutlineTool(Tool):
    """Tool for retrieving course outline - title, link, and complete lesson list"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []

    def get_tool_definition(self) -> Dict[str, Any]:
        """Return tool definition for course outline"""
        return {
            "type": "function",
            "function": {
                "name": "get_course_outline",
                "description": "Get the complete outline of a course including course title, course link, and all lessons with their numbers and titles",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "course_title": {
                            "type": "string",
                            "description": "The title of the course to get outline for"
                        }
                    },
                    "required": ["course_title"]
                }
            }
        }

    def execute(self, course_title: str) -> str:
        """
        Execute the course outline tool.

        Args:
            course_title: The course title to get outline for

        Returns:
            Formatted course outline with title, link, and lessons
        """
        import json

        try:
            # Get all courses metadata to find the matching course
            all_courses = self.store.get_all_courses_metadata()

            # Find the course by title (partial match support)
            matched_course = None
            for course in all_courses:
                if course_title.lower() in course.get('title', '').lower() or \
                   course.get('title', '').lower() in course_title.lower():
                    matched_course = course
                    break

            if not matched_course:
                return f"No course found matching '{course_title}'"

            # Extract course info
            title = matched_course.get('title', 'Unknown')
            link = matched_course.get('course_link', '')
            lessons = matched_course.get('lessons', [])

            # Build the formatted output
            output = f"Course: {title}"
            if link:
                output += f"\nLink: {link}"
            output += "\n\nLessons:"

            for lesson in lessons:
                lesson_num = lesson.get('lesson_number', '?')
                lesson_title = lesson.get('lesson_title', 'Untitled')
                output += f"\n- Lesson {lesson_num}: {lesson_title}"

            # Track source for the UI
            source = title
            if link:
                source_with_link = f"{source}|{link}"
                self.last_sources = [source_with_link]
            else:
                self.last_sources = [source]

            return output

        except Exception as e:
            return f"Error getting course outline: {str(e)}"


class CourseSearchTool(Tool):
    """Tool for searching course content with semantic course name matching"""
    
    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []  # Track sources from last search
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return MiniMax/OpenAI tool definition for this tool"""
        return {
            "type": "function",
            "function": {
                "name": "search_course_content",
                "description": "Search course materials with smart course name matching and lesson filtering",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in the course content"
                        },
                        "course_name": {
                            "type": "string",
                            "description": "Course title (partial matches work, e.g. 'MCP', 'Introduction')"
                        },
                        "lesson_number": {
                            "type": "integer",
                            "description": "Specific lesson number to search within (e.g. 1, 2, 3)"
                        }
                    },
                    "required": ["query"]
                }
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
        sources = []  # Track sources for the UI

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')

            # Get course and lesson links
            course_link = self.store.get_course_link(course_title)
            lesson_link = None
            if lesson_num is not None:
                lesson_link = self.store.get_lesson_link(course_title, lesson_num)

            # Prefer lesson link, fall back to course link
            link = lesson_link or course_link

            # Build context header with embedded link
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"

            # Track source for the UI as object with link
            source = course_title
            if lesson_num is not None:
                source += f" - Lesson {lesson_num}"

            # Store source with embedded link (as JSON for frontend to parse)
            source_with_link = f"{source}|{link}" if link else source
            sources.append(source_with_link)

            formatted.append(f"{header}\n{doc}")

        # Store sources for retrieval
        self.last_sources = sources

        return "\n\n".join(formatted)

class ToolManager:
    """Manages available tools for the AI"""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        # Handle both Anthropic format (direct name) and OpenAI/MiniMax format (nested in function)
        tool_name = tool_def.get("name") or tool_def.get("function", {}).get("name")
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