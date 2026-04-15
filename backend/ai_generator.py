import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_ROUNDS = 2  # Maximum sequential tool-calling rounds per query

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use **get_course_outline** for questions about a course's structure, outline, or lesson list — it returns the course title, link, and all lesson numbers and titles
- Use **search_course_content** only for questions about specific course content or detailed educational materials
- You may make up to 2 sequential tool calls when a query requires chaining
- Use a second tool call only when the result of the first is needed to form the next query
  (e.g., use get_course_outline to find a lesson title, then search_course_content with that title)
- After receiving tool results, respond in text as soon as you have enough information
- Do not chain tool calls speculatively — only when the second depends on the first
- Synthesize results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course outline questions**: Call get_course_outline and return the course title, course link, and the complete numbered lesson list
- **Course-specific questions**: Call search_course_content first, then answer
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

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use":
            if tool_manager:
                return self._handle_tool_execution(response, api_params, tool_manager)
            return "I tried to look up information but tool execution is not available."

        # Return direct response
        return response.content[0].text

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle sequential tool calls up to MAX_ROUNDS, then force a final text response.

        Each round:
          1. Execute all tool_use blocks in the current response
          2. Append assistant turn + tool results to the message thread
          3. If rounds remain and no error, make an intermediate call WITH tools
          4. If Claude answers without a tool call, return immediately (early exit)

        After the loop, make one final call WITHOUT tools so Claude is forced to answer.

        Args:
            initial_response: The first response containing tool use requests
            base_params: API parameters from generate_response (includes tools/tool_choice)
            tool_manager: Manager to execute tools

        Returns:
            Final response text
        """
        messages = base_params["messages"].copy()
        current_response = initial_response

        for round_num in range(self.MAX_ROUNDS):
            # --- Execute all tool calls in this round ---
            tool_results = []
            had_error = False
            for block in current_response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Tool execution failed: {e}"
                        had_error = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # --- Append this round to the message thread ---
            messages.append({"role": "assistant", "content": current_response.content})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            is_last_round = (round_num == self.MAX_ROUNDS - 1)

            # Stop conditions (b) exception or (c) rounds exhausted
            if had_error or is_last_round:
                break

            # --- Intermediate call: tools still available for chaining ---
            intermediate_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": base_params["tools"],
                "tool_choice": base_params["tool_choice"],
            }
            current_response = self.client.messages.create(**intermediate_params)

            # Stop condition (a): Claude answered without requesting another tool
            if current_response.stop_reason != "tool_use":
                return current_response.content[0].text

        # --- Forced final call: always strip tools ---
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"],
        }
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
