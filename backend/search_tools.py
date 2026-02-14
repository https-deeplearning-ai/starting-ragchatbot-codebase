from typing import Dict, Any, Optional, List, Protocol
from abc import ABC, abstractmethod
from vector_store import VectorStore, SearchResults


class Tool(ABC):
    """Abstract base class for all tools"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Return OpenAI-compatible tool definition for Ollama"""
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
        """Return OpenAI-compatible tool definition for Ollama"""
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
    
    def execute(self, query: str = "", course_name: Optional[str] = None, lesson_number: Optional[int] = None) -> str:
        """
        Execute the search tool with given parameters.

        Args:
            query: What to search for
            course_name: Optional course filter
            lesson_number: Optional lesson filter

        Returns:
            Formatted search results or error message
        """
        # Coerce lesson_number to int (LLMs sometimes send it as a string)
        if lesson_number is not None:
            try:
                lesson_number = int(lesson_number)
            except (ValueError, TypeError):
                lesson_number = None

        # If query is empty but we have filters, use a generic query
        if not query and (course_name or lesson_number is not None):
            query = f"{course_name or ''} lesson {lesson_number or ''}".strip()

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
        sources: List[Dict[str, Any]] = []
        seen = set()  # Deduplicate by (course_title, lesson_num)

        for doc, meta in zip(results.documents, results.metadata):
            course_title = meta.get('course_title', 'unknown')
            lesson_num = meta.get('lesson_number')

            # Build context header
            header = f"[{course_title}"
            if lesson_num is not None:
                header += f" - Lesson {lesson_num}"
            header += "]"

            # Track source for the UI (deduplicated)
            key = (course_title, lesson_num)
            if key not in seen:
                seen.add(key)
                title = course_title
                if lesson_num is not None:
                    title += f" - Lesson {lesson_num}"
                link = None
                if lesson_num is not None:
                    link = self.store.get_lesson_link(course_title, lesson_num)
                if not link:
                    link = self.store.get_course_link(course_title)
                sources.append({"title": title, "link": link})

            formatted.append(f"{header}\n{doc}")

        # Accumulate sources (may be called multiple times per query)
        self.last_sources.extend(sources)

        return "\n\n".join(formatted)

class CourseOutlineTool(Tool):
    """Tool for retrieving course outlines from the course catalog"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_course_outline",
                "description": "Get the full outline of a course including title, link, and all lessons",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "course_name": {
                            "type": "string",
                            "description": "Course title or partial name (e.g. 'MCP', 'RAG chatbot')"
                        }
                    },
                    "required": ["course_name"]
                }
            }
        }

    def execute(self, course_name: str) -> str:
        outline = self.store.get_course_outline(course_name)
        if not outline:
            return f"No course found matching '{course_name}'."

        title = outline["title"]
        link = outline.get("course_link") or "N/A"
        lessons = outline.get("lessons", [])

        # Accumulate sources (may be called multiple times per query)
        self.last_sources.extend([{"title": title, "link": outline.get("course_link")}])

        lines = [
            f"COURSE OUTLINE (list every lesson as a markdown bullet point):",
            f"**Course:** {title}",
            f"**Course Link:** {link}",
            f"**Total Lessons:** {len(lessons)}",
            "",
        ]
        for lesson in lessons:
            num = lesson.get("lesson_number", "?")
            ltitle = lesson.get("lesson_title", "Untitled")
            lines.append(f"- **Lesson {num}:** {ltitle}")

        return "\n".join(lines)


class ToolManager:
    """Manages available tools for the AI"""
    
    def __init__(self):
        self.tools = {}
    
    def register_tool(self, tool: Tool):
        """Register any tool that implements the Tool interface"""
        tool_def = tool.get_tool_definition()
        # OpenAI-compatible format nests name under "function"
        func_def = tool_def.get("function", {})
        tool_name = func_def.get("name") or tool_def.get("name")
        if not tool_name:
            raise ValueError("Tool must have a 'name' in its definition")
        self.tools[tool_name] = tool

    
    def get_tool_definitions(self) -> list:
        """Get all tool definitions for Ollama tool calling"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Execute a tool by name with given parameters"""
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"
        
        return self.tools[tool_name].execute(**kwargs)
    
    def get_last_sources(self) -> list:
        """Get sources from all tools, deduplicated by (title, link)."""
        seen = set()
        sources = []
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                for s in tool.last_sources:
                    key = (s.get("title"), s.get("link"))
                    if key not in seen:
                        seen.add(key)
                        sources.append(s)
        return sources

    def reset_sources(self):
        """Reset sources from all tools that track sources"""
        for tool in self.tools.values():
            if hasattr(tool, 'last_sources'):
                tool.last_sources = []