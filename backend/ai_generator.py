import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Maximum tool calling rounds per query
    MAX_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Tool Usage:

Tool Selection:
- **Course outline/structure queries** (e.g., "What lessons are in X?", "Show me the outline of Y"):
  Use get_course_outline tool - returns course title, course link, and complete lesson list with numbers and titles
- **Course content queries** (e.g., "What does X teach about Y?"):
  Use search_course_content tool - returns relevant content chunks from lessons

Tool Execution:
- You can make **up to 2 sequential tool calls** to gather information
- After each tool call, you receive results and can decide if another call is needed
- Use this for multi-step queries requiring information from multiple sources
- Examples:
  * Get course outline → Find lesson title → Search that lesson's content
  * Search one course → Search another course for comparison
  * Search general topic → Get specific course outline if relevant

When to use multiple rounds:
- Comparisons requiring information from different courses/lessons
- Multi-part questions where one answer informs the next search
- When initial results suggest a refined search would help

General Rules:
- Use tools **only** for questions about course materials
- Synthesize tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool usage explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"


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
        Supports up to MAX_ROUNDS sequential tool calls per query.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content (once, before loop)
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages list (accumulates across rounds)
        messages = [{"role": "user", "content": query}]

        # Track last response for post-loop check
        last_response = None

        # Loop through up to MAX_ROUNDS
        for round_num in range(self.MAX_ROUNDS):
            # Build API parameters (copy messages to preserve state for testing)
            api_params = {**self.base_params, "messages": messages.copy(), "system": system_content}

            # Add tools if available (CRITICAL: include in all rounds)
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Make API call
            response = self.client.messages.create(**api_params)
            last_response = response

            # TERMINATION CONDITION 1: Natural completion
            if response.stop_reason != "tool_use":
                return response.content[0].text

            # Handle tool execution
            if not tool_manager:
                # Can't execute tools without manager
                return "I need to use tools but no tool manager is available"

            # Append assistant's tool_use to messages
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tools
            tool_results = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(
                            content_block.name, **content_block.input
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": result,
                            }
                        )
                    except Exception as e:
                        # TERMINATION CONDITION 3: Tool error (graceful)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": f"Error executing tool: {e!s}",
                                "is_error": True,
                            }
                        )

            # Append tool results to messages
            messages.append({"role": "user", "content": tool_results})

            # Continue to next round...

        # TERMINATION CONDITION 2: Max rounds reached
        # Make final synthesis call WITHOUT tools
        if last_response and last_response.stop_reason == "tool_use":
            final_params = {
                **self.base_params,
                "messages": messages.copy(),
                "system": system_content,
                # NO tools parameter
            }
            final_response = self.client.messages.create(**final_params)
            return final_response.content[0].text
        else:
            # Last round was already end_turn
            return last_response.content[0].text
