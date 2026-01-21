import anthropic
from typing import List, Optional, Dict, Any


class ToolExecutionError(Exception):
    """Raised when tool execution fails"""
    pass


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **search_course_content**: Search for specific content within course materials
2. **get_course_outline**: Get course structure including title, link, and all lessons

Tool Usage Guidelines:
- Use **get_course_outline** for questions about:
  - Course structure or outline
  - What lessons are available
  - List of topics covered in a course
  - Course overview or syllabus
  - When responding, include the course title, course link, and for each lesson: the lesson number and title
- Use **search_course_content** for questions about:
  - Specific course content or concepts
  - Detailed educational materials
  - Finding information within lessons
- **Up to 2 sequential tool calls per query** - use a second call when you need to combine information or refine your search
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course outline questions**: Use get_course_outline, then present the course title, course link, and complete lesson list with numbers and titles
- **Course content questions**: Use search_course_content, then synthesize results
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    # Maximum sequential tool call rounds per query
    MAX_TOOL_ROUNDS = 2

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to MAX_TOOL_ROUNDS sequential tool calls.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        messages = [{"role": "user", "content": query}]
        system_content = self._build_system_content(conversation_history)

        for round_num in range(self.MAX_TOOL_ROUNDS):
            # Build params - include tools for all rounds in the loop
            # Use list() to create a snapshot of messages for this API call
            api_params = {
                **self.base_params,
                "messages": list(messages),
                "system": system_content
            }
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            response = self.client.messages.create(**api_params)

            # No tool use - return text response
            if response.stop_reason != "tool_use" or not tool_manager:
                return self._extract_text_response(response)

            # Execute tools and accumulate messages
            try:
                tool_results = self._execute_tool_calls(response, tool_manager)
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            except ToolExecutionError as e:
                return f"Tool execution failed: {e}"

        # Max rounds reached - final call WITHOUT tools
        final_params = {
            **self.base_params,
            "messages": list(messages),
            "system": system_content
        }
        final_response = self.client.messages.create(**final_params)
        return self._extract_text_response(final_response)

    def _build_system_content(self, conversation_history: Optional[str]) -> str:
        """Build system prompt with optional conversation history."""
        if conversation_history:
            return f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
        return self.SYSTEM_PROMPT

    def _execute_tool_calls(self, response, tool_manager) -> List[Dict[str, Any]]:
        """
        Execute all tool calls from response.

        Args:
            response: API response containing tool_use blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool result dicts

        Raises:
            ToolExecutionError: If tool execution fails
        """
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": result
                    })
                except Exception as e:
                    raise ToolExecutionError(f"Failed to execute {content_block.name}: {e}")
        return tool_results

    def _extract_text_response(self, response) -> str:
        """Extract text content from API response."""
        for content_block in response.content:
            if content_block.type == "text":
                return content_block.text
        return ""