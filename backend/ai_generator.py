import anthropic
from typing import List, Optional, Dict, Any, Tuple


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2
    TOOL_ERROR_MESSAGE = (
        "I encountered an error retrieving course information. Please try again."
    )
    EMPTY_RESPONSE_FALLBACK = (
        "I encountered an error retrieving course information. Please try again."
    )

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Tool Usage:
- You may use tools across up to 2 sequential rounds when needed
- Prefer a single tool call when sufficient; use a second round only when the answer requires additional course data
- Typical two-step flow: get_course_outline first for structure/lesson titles, then search_course_content for specific lesson content
- Use **search_course_content** only for questions about specific course content or detailed educational materials
- Use **get_course_outline** for questions about a course outline, syllabus, structure, or lesson list
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course content questions**: Use search_course_content first, then answer
- **Course outline questions**: Use get_course_outline first, then answer with the course title, course link, and each lesson's number and title
- **Multi-part or comparison questions**: Use a second tool round when needed to gather complementary information
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str, base_url: str):
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.model = model
        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def _build_api_params(
        self,
        system: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List] = None,
    ) -> Dict[str, Any]:
        """Build Anthropic messages.create parameters."""
        params: Dict[str, Any] = {
            **self.base_params,
            "messages": messages,
            "system": system,
            "thinking": {"type": "disabled"},
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = {"type": "auto"}
        return params

    def _execute_tool_round(
        self, content, tool_manager
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Execute all tool_use blocks in a response content list.

        Returns:
            (tool_results, failed) — failed is True if any execute_tool raised.
        """
        tool_results: List[Dict[str, Any]] = []
        for content_block in content:
            if getattr(content_block, "type", None) != "tool_use":
                continue
            try:
                result = tool_manager.execute_tool(
                    content_block.name,
                    **content_block.input,
                )
            except Exception as e:
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": str(e),
                        "is_error": True,
                    }
                )
                return tool_results, True

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": result,
                }
            )
        return tool_results, False

    def _finalize_response(self, response) -> str:
        """Extract text from a model response, with a safe fallback."""
        texts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        if not texts:
            return self.EMPTY_RESPONSE_FALLBACK
        return "\n".join(texts)

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional sequential tool usage (max 2 rounds).

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

        messages: List[Dict[str, Any]] = [{"role": "user", "content": query}]
        tool_rounds_completed = 0
        can_use_tools = bool(tools) and tool_manager is not None

        while True:
            # Keep tools available until we force a synthesis call
            api_params = self._build_api_params(
                system_content,
                messages,
                tools if can_use_tools else None,
            )
            response = self.client.messages.create(**api_params)

            if response.stop_reason != "tool_use" or not tool_manager:
                return self._finalize_response(response)

            # Max rounds already completed: do not execute; force synthesis without tools
            if tool_rounds_completed >= self.MAX_TOOL_ROUNDS:
                messages.append({"role": "assistant", "content": response.content})
                # Provide tool_result stubs so the messages API remains valid
                stub_results = [
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": (
                            "Tool round limit reached. "
                            "Please answer using the information already gathered."
                        ),
                    }
                    for block in response.content
                    if getattr(block, "type", None) == "tool_use"
                ]
                if stub_results:
                    messages.append({"role": "user", "content": stub_results})
                final_params = self._build_api_params(
                    system_content, messages, tools=None
                )
                final_response = self.client.messages.create(**final_params)
                return self._finalize_response(final_response)

            tool_results, failed = self._execute_tool_round(
                response.content, tool_manager
            )

            if failed:
                return self.TOOL_ERROR_MESSAGE

            messages.append({"role": "assistant", "content": response.content})
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            tool_rounds_completed += 1
