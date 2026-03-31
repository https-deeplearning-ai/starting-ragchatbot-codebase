import anthropic
from typing import List, Optional

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use `search_course_content` for questions about specific course content or detailed educational materials
- Use `get_course_outline` for questions about course structure, lesson list, or what topics a course covers — it returns the course title, course link, and all lessons with their numbers and titles
- **Up to 2 sequential tool calls per query**
- Synthesize results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

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

    MAX_ROUNDS = 2

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
        Supports up to MAX_ROUNDS sequential tool-call rounds before forcing a
        final text response.

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

        messages = [{"role": "user", "content": query}]

        # Prepare initial API call parameters
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Tool-calling loop: up to MAX_ROUNDS sequential rounds
        round_count = 0
        while round_count < self.MAX_ROUNDS:
            response = self.client.messages.create(**api_params)

            # Early exit: no tool use requested or no manager to execute them
            if response.stop_reason != "tool_use" or not tool_manager:
                return response.content[0].text

            # Append assistant turn (contains tool-use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls in this round
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = tool_manager.execute_tool(block.name, **block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

            # Rebuild api_params with updated messages; keep tools for next round
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
                "tools": tools,
                "tool_choice": {"type": "auto"}
            }
            round_count += 1

        # Max rounds reached — force a text response by calling without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
