from google import genai
from google.genai import types
from typing import List, Optional, Dict, Any

TYPE_MAP = {
    "object":  types.Type.OBJECT,
    "string":  types.Type.STRING,
    "integer": types.Type.INTEGER,
    "number":  types.Type.NUMBER,
    "boolean": types.Type.BOOLEAN,
    "array":   types.Type.ARRAY,
}


class GeminiGenerator:
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **One search per query maximum**
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

    def __init__(self, api_key: str, model: str):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        system = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )
        contents = [{"role": "user", "parts": [{"text": query}]}]
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0,
            max_output_tokens=800,
            tools=self._convert_tools(tools) if tools else None,
        )
        response = self.client.models.generate_content(
            model=self.model, contents=contents, config=config
        )
        if self._has_function_call(response) and tool_manager:
            return self._handle_tool_execution(response, contents, system, tool_manager)
        return response.text

    def _handle_tool_execution(self, initial_response, contents, system, tool_manager) -> str:
        contents = contents + [
            {"role": "model", "parts": initial_response.candidates[0].content.parts}
        ]
        result_parts = []
        for part in initial_response.candidates[0].content.parts:
            if part.function_call:
                result = tool_manager.execute_tool(
                    part.function_call.name, **dict(part.function_call.args)
                )
                result_parts.append(
                    types.Part.from_function_response(
                        name=part.function_call.name,
                        response={"result": result},
                    )
                )
        contents = contents + [{"role": "user", "parts": result_parts}]
        final = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=0, max_output_tokens=800
            ),
        )
        return final.text

    def _has_function_call(self, response) -> bool:
        try:
            return any(
                p.function_call for p in response.candidates[0].content.parts
            )
        except (AttributeError, IndexError):
            return False

    def _convert_tools(self, anthropic_tools: List[Dict]) -> List:
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=t["name"],
                        description=t["description"],
                        parameters=self._convert_schema(t["input_schema"]),
                    )
                    for t in anthropic_tools
                ]
            )
        ]

    def _convert_schema(self, schema: Dict) -> types.Schema:
        kwargs: Dict[str, Any] = {
            "type": TYPE_MAP.get(schema.get("type", "").lower(), types.Type.STRING)
        }
        if "description" in schema:
            kwargs["description"] = schema["description"]
        if "properties" in schema:
            kwargs["properties"] = {
                k: self._convert_schema(v) for k, v in schema["properties"].items()
            }
        if "required" in schema:
            kwargs["required"] = schema["required"]
        if "items" in schema:
            kwargs["items"] = self._convert_schema(schema["items"])
        return types.Schema(**kwargs)
