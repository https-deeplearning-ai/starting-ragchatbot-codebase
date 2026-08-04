import json
from typing import Any, Dict, List, Optional

from openai import OpenAI


class AIGenerator:
    """Generate answers with OpenAI and execute local course-search tools."""

    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool only for questions about specific course content or detailed educational materials.
- Use at most one search per query.
- Synthesize search results into accurate, fact-based responses.
- If search yields no results, state this clearly without offering alternatives.

Response Protocol:
- General knowledge questions: answer using existing knowledge without searching.
- Course-specific questions: search first, then answer.
- Provide direct answers only. Do not describe your reasoning or search process.
- Do not say "based on the search results."

Keep responses brief, educational, clear, and focused. Include an example when it materially improves understanding.
"""

    def __init__(self, api_key: str, model: str):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_manager=None,
    ) -> str:
        """Generate a response, executing at most one round of tool calls."""
        instructions = self.SYSTEM_PROMPT
        if conversation_history:
            instructions += f"\n\nPrevious conversation:\n{conversation_history}"

        openai_tools = self._convert_tools(tools or [])
        input_items: List[Any] = [{"role": "user", "content": query}]
        request: Dict[str, Any] = {
            "model": self.model,
            "instructions": instructions,
            "input": input_items,
            "reasoning": {"effort": "low"},
            "max_output_tokens": 800,
        }
        if openai_tools:
            request["tools"] = openai_tools
            request["tool_choice"] = "auto"

        response = self.client.responses.create(**request)
        function_calls = [item for item in response.output if item.type == "function_call"]
        if not function_calls or not tool_manager:
            return response.output_text

        input_items.extend(response.output)
        for function_call in function_calls:
            arguments = json.loads(function_call.arguments)
            result = tool_manager.execute_tool(function_call.name, **arguments)
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": function_call.call_id,
                    "output": result,
                }
            )

        final_response = self.client.responses.create(
            model=self.model,
            instructions=instructions,
            input=input_items,
            tools=openai_tools,
            reasoning={"effort": "low"},
            max_output_tokens=800,
        )
        return final_response.output_text

    @staticmethod
    def _convert_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert the existing tool definitions to OpenAI function tools."""
        return [
            {
                "type": "function",
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool["input_schema"],
            }
            for tool in tools
        ]
