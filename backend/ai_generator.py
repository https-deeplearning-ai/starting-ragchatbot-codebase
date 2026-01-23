import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **search_course_content** - Search for specific information within course content
2. **get_course_outline** - Get course structure (title, link, and lesson list)

Tool Usage Guidelines:
- Use **get_course_outline** when users ask about:
  - What lessons are in a course
  - Course structure or overview
  - What topics a course covers

- Use **search_course_content** when users ask about:
  - Specific concepts or information within course content
  - Details about particular topics covered in lessons

- **General knowledge questions**: Answer using existing knowledge without tools
- **Multi-step reasoning**: You may use tools sequentially to gather information. After receiving tool results, you can call another tool if more information is needed
- If a tool yields no results, state this clearly

Response Protocol:
- Provide direct answers only - no meta-commentary about tools or search results
- Do not mention "based on the search results" or "according to the outline"

All responses must be:
1. **Brief and concise** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def _extract_text_response(self, response) -> str:
        """Extract text content from API response."""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def _execute_tool_round(
        self, response, messages: list[dict], tool_manager
    ) -> tuple[list[dict], bool]:
        """
        Execute tools from response, update messages, return (updated_messages, has_error).
        """
        # Append assistant's tool_use response
        messages.append({"role": "assistant", "content": response.content})

        # Execute each tool, collect results
        tool_results = []
        has_error = False
        for block in response.content:
            if block.type == "tool_use":
                try:
                    result = tool_manager.execute_tool(block.name, **block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
                except Exception as e:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True,
                        }
                    )
                    has_error = True

        # Append tool results as user message
        messages.append({"role": "user", "content": tool_results})
        return messages, has_error

    def generate_response(
        self,
        query: str,
        conversation_history: str | None = None,
        tools: list | None = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to 2 sequential tool call rounds for multi-step reasoning.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        MAX_TOOL_ROUNDS = 2

        # Build system content
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages
        messages = [{"role": "user", "content": query}]

        # Build base API params
        api_params = {**self.base_params, "system": system_content}
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Initial API call
        response = self.client.messages.create(messages=messages, **api_params)

        # Tool calling loop
        for _round_num in range(MAX_TOOL_ROUNDS):
            # Exit if no tool use requested
            if response.stop_reason != "tool_use" or not tool_manager:
                break

            # Execute tools and update messages
            messages, has_error = self._execute_tool_round(
                response, messages, tool_manager
            )

            # Make next API call WITH tools (key fix!)
            response = self.client.messages.create(messages=messages, **api_params)

        return self._extract_text_response(response)
