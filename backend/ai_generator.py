import anthropic
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **search_course_content**: Search for specific content within course materials
   - Use for questions about specific topics, concepts, or detailed educational content
2. **get_course_outline**: Get the complete structure of a course
   - Use for questions about course structure, lessons list, or course overview
   - Returns: course title, course link, and all lessons (number and title for each)

Tool Usage Guidelines:
- **Up to 2 sequential tool calls per query** if needed for complex questions
- First search for content, then optionally get more details or search related topics
- Use **get_course_outline** when asked about:
  - What lessons are in a course
  - Course structure or outline
  - Overview of a course
  - How many lessons a course has
- Use **search_course_content** for questions about specific topics or content within courses
- Synthesize results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course outline questions**: Use get_course_outline, then present the course title, course link, and lesson list
- **Course content questions**: Use search_course_content, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the results"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    # Maximum sequential tool calling rounds per query
    MAX_TOOL_ROUNDS = 2

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with support for sequential tool calls (max 2 rounds).

        Uses a loop-based approach where:
        - Each iteration is a complete API call
        - Tools remain available until max rounds reached
        - Messages accumulate across rounds

        Termination conditions:
        - (a) MAX_TOOL_ROUNDS reached
        - (b) Claude responds without tool_use
        - (c) Tool execution fails

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize message list - accumulates across rounds
        messages = [{"role": "user", "content": query}]

        # Main tool-calling loop
        for round_num in range(self.MAX_TOOL_ROUNDS):
            # Prepare API call parameters
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Make API call
            response = self.client.messages.create(**api_params)

            # Termination condition (b): no tool use requested
            if response.stop_reason != "tool_use":
                return self._extract_text_response(response)

            # Tool use requested but no tool_manager - return any text
            if not tool_manager:
                return self._extract_text_response(response)

            # Execute tools and check for errors - condition (c)
            tool_results, has_error = self._execute_tools(response, tool_manager)

            # Append assistant's tool use response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Append tool results as user message
            messages.append({"role": "user", "content": tool_results})

            # If tool error, make final call without tools
            if has_error:
                return self._get_final_response(messages, system_content)

        # MAX_TOOL_ROUNDS reached - make final API call without tools
        return self._get_final_response(messages, system_content)

    def _extract_text_response(self, response) -> str:
        """
        Extract text content from a Claude response.

        Handles responses that may contain mixed content blocks.
        Returns the first text block found.
        """
        for content_block in response.content:
            if hasattr(content_block, "text"):
                return content_block.text
        return ""

    def _execute_tools(self, response, tool_manager):
        """
        Execute all tool calls from a response and collect results.

        Args:
            response: Anthropic API response containing tool_use blocks
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (tool_results list for API, has_error boolean)
        """
        tool_results = []
        has_error = False

        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )
                except Exception as e:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Error executing tool: {str(e)}",
                            "is_error": True,
                        }
                    )
                    has_error = True

        return tool_results, has_error

    def _get_final_response(self, messages: List[Dict], system_content: str) -> str:
        """
        Make a final API call without tools to get a text response.

        Args:
            messages: Accumulated conversation messages
            system_content: System prompt with optional history

        Returns:
            Final text response from Claude
        """
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        final_response = self.client.messages.create(**final_params)
        return self._extract_text_response(final_response)
