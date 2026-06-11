from anthropic import AnthropicVertex
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- Use the search tool **up to 2 times** per query — use a second search only when the first result was insufficient or the query has two distinct parts needing separate lookups
- Synthesize search results into accurate, fact-based responses
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

    def __init__(self, project_id: str, region: str, model: str):
        self.client = AnthropicVertex(project_id=project_id, region=region)
        self.model = model

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
        Supports up to MAX_TOOL_ROUNDS sequential tool-call rounds per query.

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

        messages = [{"role": "user", "content": query}]

        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }

        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        response = self.client.messages.create(**api_params)

        for round_num in range(self.MAX_TOOL_ROUNDS):
            if response.stop_reason != "tool_use" or not tool_manager:
                return response.content[0].text

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            error_occurred = False
            for content_block in response.content:
                if content_block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )
                    except Exception as e:
                        result = f"Tool execution failed: {str(e)}"
                        error_occurred = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

            is_last = error_occurred or (round_num == self.MAX_TOOL_ROUNDS - 1)

            if is_last:
                closing_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": system_content
                }
                response = self.client.messages.create(**closing_params)
                return response.content[0].text

            next_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
                "tools": tools,
                "tool_choice": {"type": "auto"}
            }
            response = self.client.messages.create(**next_params)

        return response.content[0].text
