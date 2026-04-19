import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- You may make **up to 2 sequential tool calls** per query when needed (e.g. first retrieve a course outline, then search for related content across courses)
- Use a second tool call only if the first result is insufficient or a clearly necessary follow-up search is required
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives
- **Outline queries** (e.g. "what lessons are in X?", "give me the outline of X"):
  Use `get_course_outline`. Return the course title, course link (if present), and every lesson as "Lesson <number>: <title>".

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
        Supports up to MAX_TOOL_ROUNDS sequential tool-call rounds.

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

        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        round_count = 0

        while True:
            response = self.client.messages.create(**api_params)

            # No tool use requested or no manager to handle it — return text directly
            if response.stop_reason != "tool_use" or not tool_manager:
                return self._extract_text(response)

            round_count += 1

            # Append assistant turn and execute all tool calls
            new_messages = list(api_params["messages"])
            new_messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            error_occurred = False
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Error executing tool: {e}"
                        error_occurred = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            if tool_results:
                new_messages.append({"role": "user", "content": tool_results})

            # Cap reached or tool error — make one final call without tools and return
            if error_occurred or round_count >= self.MAX_TOOL_ROUNDS:
                final_params = {
                    **self.base_params,
                    "messages": new_messages,
                    "system": system_content
                }
                return self._extract_text(self.client.messages.create(**final_params))

            # Round not yet capped — keep tools available and continue
            api_params["messages"] = new_messages

    def _extract_text(self, response) -> str:
        """Safely extract text from any response, regardless of block ordering."""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""
