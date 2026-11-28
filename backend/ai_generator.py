import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- For questions about a course's outline, structure, syllabus or list of lessons, use `get_course_outline` instead. Present the course title, instructor, and course link each on their own line (blank line between them), then EVERY lesson as a bulleted "Lesson N: Title" markdown link
- You may make **up to 2 sequential tool calls per query**, each in its own step. Make a second call only when it depends on the first result (e.g. `get_course_outline` to find a lesson's title, then `search_course_content` using that title). Use a single call when it is enough, and never repeat a call with the same arguments
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first (up to two sequential calls), then answer
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
    
    def __init__(self, api_key: Optional[str], model: str):
        # Empty/None key -> SDK falls back to `ant auth login` credentials
        self.client = anthropic.Anthropic(api_key=api_key or None)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "max_tokens": 1500
        }
    
    @staticmethod
    def _extract_text(response) -> str:
        """Join the text blocks of a response, skipping thinking/tool_use blocks"""
        return "".join(b.text for b in response.content if b.type == "text")

    MAX_ROUNDS = 2

    def _execute_tools(self, response, tool_manager):
        """Run every tool_use block; always return one tool_result per block.

        Returns (tool_results, failed). A raised exception becomes an is_error
        result so the API contract (every tool_use answered) still holds.
        """
        results, failed = [], False
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                content = tool_manager.execute_tool(block.name, **block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": content})
            except Exception as e:
                failed = True
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Tool error: {e}", "is_error": True})
        return results, failed

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Claude may make up to MAX_ROUNDS sequential tool rounds, each a separate
        API request. The loop ends when a response has no tool_use, the round
        limit is hit, or a tool fails; in the last two cases one final call with
        tool_choice "none" produces the answer.
        """
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )
        messages = [{"role": "user", "content": query}]

        def call(tool_choice):
            params = {**self.base_params, "messages": messages, "system": system_content}
            if tools:
                # Tools stay on every call (replayed thinking blocks are bound
                # to them); tool_choice controls whether they may be used.
                params["tools"] = tools
                params["tool_choice"] = {"type": tool_choice}
            return self.client.messages.create(**params)

        for _ in range(self.MAX_ROUNDS):
            response = call("auto")
            if response.stop_reason != "tool_use" or not tool_manager:
                return self._extract_text(response)

            messages.append({"role": "assistant", "content": response.content})
            tool_results, failed = self._execute_tools(response, tool_manager)
            messages.append({"role": "user", "content": tool_results})
            if failed:
                break

        return self._extract_text(call("none"))
