import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Outline Tool Usage:
- Use get_course_outline **only** for questions about course structure, syllabus, lesson list, or what topics a course covers
- Return the course title, course link, and each lesson number with its title
- Do not use the content search tool for outline queries

Sequential Tool Calls:
- You may make up to 2 tool calls in sequence when a single search is insufficient
- Use sequential calls for: multi-part questions, comparisons across courses/lessons,
  or when you need an outline first and then content from a specific lesson
  (e.g. get_course_outline → search_course_content using the lesson title found)
- Do NOT make a second tool call if the first result fully answers the question

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
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

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]

        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        response = self.client.messages.create(**api_params)

        # Tool loop: up to MAX_TOOL_ROUNDS sequential rounds
        rounds_completed = 0
        while (
            response.stop_reason == "tool_use"
            and tool_manager
            and rounds_completed < self.MAX_TOOL_ROUNDS
        ):
            response, success = self._handle_tool_execution(
                response, messages, tool_manager, system_content, tools
            )
            rounds_completed += 1
            if not success:
                break

        # Round cap hit or no tool_manager: force a plain-text synthesis call
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            response = self.client.messages.create(
                **self.base_params,
                messages=messages,
                system=system_content
            )

        return response.content[0].text

    def _handle_tool_execution(self, response, messages: List, tool_manager,
                               system_content: str, tools: List) -> tuple:
        """
        Execute one round of tool calls and make the intermediate follow-up API call.

        Mutates messages in place by appending the assistant tool-use message and
        the tool results user message.

        Args:
            response: The current API response with stop_reason == "tool_use"
            messages: Accumulated message list (mutated in place)
            tool_manager: Manager to execute tools
            system_content: System prompt string for the follow-up call
            tools: Tool definitions for the follow-up call

        Returns:
            (next_response, success): next_response is the follow-up API response;
            success is False if any tool raised an exception (loop should stop).
        """
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        success = True
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = tool_manager.execute_tool(block.name, **block.input)
                except Exception as e:
                    result = f"Tool execution error: {e}"
                    success = False
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Intermediate follow-up WITH tools so Claude can call again if needed
        next_response = self.client.messages.create(
            **self.base_params,
            messages=messages,
            system=system_content,
            tools=tools,
            tool_choice={"type": "auto"}
        )
        return next_response, success