import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Search Tool Usage:
- Use the `get_course_outline` tool for questions about a course's structure, available lessons, or lesson list — it returns the course title, course link, and all lesson numbers and titles
- Use the `search_course_content` tool **only** for questions about specific course content or detailed educational materials
- **Up to 2 sequential searches per query** — use a second search only when the first result is insufficient to answer the question
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course outline/structure questions**: Use get_course_outline, then present the course title, link, and numbered lesson list
- **Course-specific content questions**: Use search_course_content, then answer
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
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: str | None = None,
        tools: list | None = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to 2 sequential tool-call rounds.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages with user query
        messages = [{"role": "user", "content": query}]

        # Prepare base API parameters
        api_params = {**self.base_params, "messages": messages, "system": system_content}

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get initial response from Claude
        response = self.client.messages.create(**api_params)

        # Validate response has content
        if not response.content:
            raise ValueError("Empty response from Claude API - no content blocks returned")

        # Tool execution loop: up to MAX_TOOL_ROUNDS sequential tool calls
        for round_num in range(self.MAX_TOOL_ROUNDS):
            # Exit loop if no tool use or no tool manager
            if response.stop_reason != "tool_use" or not tool_manager:
                break

            # Add AI's tool use response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result = tool_manager.execute_tool(
                            content_block.name, **content_block.input
                        )
                    except Exception as e:
                        tool_result = f"Tool error: {e!s}"

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Make next API call with tools still available
            api_params["messages"] = messages
            response = self.client.messages.create(**api_params)

            # Validate response has content
            if not response.content:
                raise ValueError(
                    "Empty response from Claude API during tool execution - no content blocks returned"
                )

        # Final call if loop ended with tool_use (round cap reached)
        if response.stop_reason == "tool_use" and tool_manager and tools:
            messages.append({"role": "assistant", "content": response.content})
            api_params_final = {**self.base_params, "messages": messages, "system": system_content}
            response = self.client.messages.create(**api_params_final)

            # Validate response has content
            if not response.content:
                raise ValueError(
                    "Empty response from Claude API after round cap - no content blocks returned"
                )

        return response.content[0].text
