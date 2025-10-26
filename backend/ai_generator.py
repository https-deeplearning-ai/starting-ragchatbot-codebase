from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **search_course_content**: Search within course materials for specific topics, concepts, or detailed content
2. **get_course_outline**: Get complete course structure including title, link, and full lesson list

Tool Usage Guidelines:
- Use **search_course_content** for questions about specific course content, topics, or detailed educational materials
- Use **get_course_outline** for questions about course structure, curriculum, lesson lists, or "what does this course cover?"
- **Use tools sequentially when needed** - You can make multiple tool calls to gather comprehensive information
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course content questions**: Use search_course_content tool first, then answer
- **Course structure questions**: Use get_course_outline tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "according to the outline"

For outline queries, ensure you return:
- Complete course title
- Course link (if available)
- All lesson numbers and titles
- Lesson links (if available)

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
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_tool_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of sequential tool calling rounds (default: 2)

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
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(
                response, api_params, tool_manager, max_tool_rounds
            )

        # Return direct response
        return response.content[0].text

    def _handle_tool_execution(
        self,
        initial_response,
        base_params: Dict[str, Any],
        tool_manager,
        max_tool_rounds: int,
    ):
        """
        Handle sequential execution of tool calls and get follow-up response.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of sequential tool calling rounds

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute tools from initial response
        tool_results = self._execute_tools_from_response(initial_response, tool_manager)

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Continue sequential tool calling for remaining rounds
        for round_num in range(1, max_tool_rounds):
            # Prepare API call with tools (for potential follow-up tool calls)
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": base_params.get("tools", []),
                "tool_choice": {"type": "auto"},
            }

            # Get response from Claude
            response = self.client.messages.create(**api_params)

            # If no more tools needed, this is our final response
            if response.stop_reason != "tool_use":
                return response.content[0].text

            # Add AI's tool use response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Execute tools from this response
            tool_results = self._execute_tools_from_response(response, tool_manager)

            # Add tool results to conversation
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        # Max rounds reached - make final call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"],
        }

        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text

    def _execute_tools_from_response(self, response, tool_manager):
        """
        Execute all tools from a response and return formatted results.

        Args:
            response: The response containing tool use requests
            tool_manager: Manager to execute tools

        Returns:
            List of tool result objects formatted for the API
        """
        tool_results = []

        try:
            for content_block in response.content:
                if content_block.type == "tool_use":
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
            # If tool execution fails, add error result
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": getattr(content_block, "id", "unknown"),
                    "content": f"Error executing tool: {str(e)}",
                }
            )

        return tool_results
