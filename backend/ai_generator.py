import anthropic
from typing import List, Optional

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- You may search up to 2 times per query when a follow-up search would meaningfully refine the answer (e.g. searching for a lesson title first, then using that title to find related content across courses)
- Use multi-step search only when necessary — prefer a single targeted search
- Synthesize all search results into a single accurate, fact-based response
- If search yields no results, state this clearly without offering alternatives

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

    _FALLBACK = "I was unable to generate a response. Please try again."
    _MAX_TOOL_ROUNDS = 2

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800,
        }

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate an AI response, running up to _MAX_TOOL_ROUNDS sequential tool
        calls when Claude requests them.

        Each tool-use round is a separate API request so Claude can reason about
        prior search results before deciding whether another search is needed.

        Terminates when:
          (a) Claude returns a text response (stop_reason != "tool_use")
          (b) _MAX_TOOL_ROUNDS rounds have been completed
          (c) A tool call raises an exception
        """
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": query}]
        api_params = {**self.base_params, "messages": messages, "system": system_content}
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        response = self.client.messages.create(**api_params)

        for _ in range(self._MAX_TOOL_ROUNDS):
            if response.stop_reason != "tool_use" or not tool_manager:
                break

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            error_occurred = False
            for block in response.content:
                if block.type != "tool_use":
                    continue
                try:
                    result = tool_manager.execute_tool(block.name, **block.input)
                except Exception as e:
                    result = f"Tool error: {str(e)}"
                    error_occurred = True
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

            if error_occurred:
                break

            # tools must be included in follow-up calls — Anthropic returns HTTP 400
            # when messages contain tool_use blocks but no tools are defined.
            followup_params = {**self.base_params, "messages": messages, "system": system_content}
            if tools:
                followup_params["tools"] = tools
            response = self.client.messages.create(**followup_params)

        for block in response.content:
            if block.type == "text":
                return block.text

        return self._FALLBACK
