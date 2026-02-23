from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2
    DIRECT_RETURN_TOOLS = frozenset({"get_course_outline"})

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Available Tools:
- **search_course_content**: Search within course materials for specific content
- **get_course_outline**: Get complete course outline with all lessons

Tool Usage Guidelines:
- Use search_course_content for detailed questions about specific topics or lessons
- Use get_course_outline for questions about course structure, lesson lists, or "what's in this course"
- **You can make up to 2 rounds of tool calls to gather comprehensive information**
  - Round 1: Initial search to gather relevant information
  - Round 2: Refine or search additional context (different course, narrower lesson, related term)
  - Most queries need only 1 tool call. Use a second only when the first result is insufficient.
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Course Outline Responses:
When using get_course_outline:
- Return the tool output EXACTLY as formatted - do not add summaries, context, or additional information
- Present the complete structured list without modification

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course outline questions**: Use get_course_outline first
- **Course-specific content questions**: Use search_course_content first, then synthesize
- **No meta-commentary**:
  - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
  - Do not mention "based on the tool results"

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

    def _call_api(self, **params):
        """Make an Anthropic API call with standardized error handling."""
        try:
            return self.client.messages.create(**params)
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"Anthropic API authentication failed: {e}") from e
        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to MAX_TOOL_ROUNDS sequential rounds of tool calling.

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

        # Start with initial messages
        messages = [{"role": "user", "content": query}]

        # Execute up to MAX_TOOL_ROUNDS rounds of tool calling
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

            response = self._call_api(**api_params)

            # Handle tool execution if needed
            if response.stop_reason == "tool_use" and tool_manager:
                messages, should_continue, direct_result = self._handle_tool_execution(
                    response, messages, tool_manager
                )
                if direct_result is not None:
                    return direct_result
                if not should_continue:
                    break
            else:
                # No tool use, return direct response
                return self._extract_text(response)

        # After max rounds, make final call without tools to get response
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        final_response = self._call_api(**final_params)
        return self._extract_text(final_response)

    @staticmethod
    def _extract_text(response) -> str:
        """Safely extract text from an API response, handling empty content."""
        if not response.content:
            return "I'm sorry, I wasn't able to generate a response. Please try again."
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "I'm sorry, I wasn't able to generate a response. Please try again."

    def _handle_tool_execution(self, initial_response, messages: List, tool_manager):
        """
        Handle execution of tool calls and update message history.

        Executes ALL tool calls before deciding flow control. This ensures the
        Anthropic API receives tool_result blocks for every tool_use block, even
        if some tools fail.

        Args:
            initial_response: The response containing tool use requests
            messages: Current message history
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (updated_messages, should_continue, direct_result)
            direct_result is non-None when the tool output should be returned as-is
        """
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute ALL tool calls and collect results
        tool_results = []
        direct_return_result = None
        has_error = False

        for content_block in initial_response.content:
            if content_block.type != "tool_use":
                continue

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

                # Mark outline results for direct return (but keep executing remaining tools)
                if content_block.name in self.DIRECT_RETURN_TOOLS:
                    direct_return_result = tool_result

            except Exception as e:
                has_error = True
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": f"Error: Tool execution failed - {str(e)}",
                        "is_error": True,
                    }
                )

        # Add all tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Direct return takes priority (e.g. course outline)
        if direct_return_result is not None:
            return messages, False, direct_return_result

        # Stop rounds if any tool failed
        if has_error:
            return messages, False, None

        # Continue with next round
        return messages, True, None
