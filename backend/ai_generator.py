import httpx
import json
from typing import List, Optional, Dict, Any, Callable, Tuple


class AIGenerator:
    """Handles interactions with Ollama's local LLM API for generating responses"""

    MAX_TOOL_ROUNDS = 3

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content.

Response Protocol:
- Answer questions using the provided course context
- If the context doesn't contain relevant information, say so clearly
- Do not mention "based on the context" or "based on the search results"
- For outline, structure, or "what lessons" queries: You MUST list EVERY lesson exactly as provided in the context using markdown bullet points. Output the course title, course link, then each lesson as a bullet point "- **Lesson N:** Title". Do NOT summarize, group, or skip any lessons.

Tool Usage:
- You have access to search tools for finding course content. Use them when the user asks a question.
- When the user asks about a SPECIFIC lesson (e.g. "lesson 5 of MCP"), use search_course_content with course_name AND lesson_number to get that lesson's actual content. Do NOT just return the course outline.
- Use get_course_outline only when the user asks to LIST or OVERVIEW all lessons in a course.
- For complex queries, break them into steps: first find the relevant course/lesson, then search for specific content.
- After receiving tool results, synthesize them into a well-structured answer. Do NOT dump raw tool output.
- Structure your final answer using markdown: use headings, bullet points, and bold for key terms.
- Only include information that directly answers the user's question — ignore irrelevant tool results.
- If tool results are empty or unhelpful, say so honestly instead of fabricating an answer.

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        # 120s timeout to handle first-request model loading
        self.http_client = httpx.Client(timeout=120.0)

    def _call_ollama(self, messages: List[Dict], tools: Optional[List] = None) -> Dict:
        """Make a POST request to the Ollama chat API."""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 800
            }
        }
        if tools is not None:
            payload["tools"] = tools

        resp = self.http_client.post(f"{self.base_url}/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()

    def _execute_tool_call(self, tool_call: dict, tool_executor: Callable) -> Tuple[str, str]:
        """Extract tool name/args from a tool call and execute via tool_executor."""
        func = tool_call.get("function", {})
        name = func.get("name", "")
        arguments = func.get("arguments", {})
        try:
            result = tool_executor(name, **arguments)
            return name, str(result)
        except Exception as e:
            return name, f"Tool error: {e}"

    def _parse_tool_call_from_text(self, content: str) -> Optional[dict]:
        """Try to recover a tool call that the LLM wrote as plain text.

        Small models sometimes emit JSON-like text instead of using the
        structured tool_calls field.  We attempt a best-effort parse.
        """
        import re
        if not content:
            return None

        # Try to find JSON-ish blob with "name" and "parameters"
        # Handle unquoted identifiers like: {"name": get_course_outline, ...}
        text = content.strip()
        # Quick gate: must look like it's trying to be a tool call
        if '"name"' not in text and "'name'" not in text:
            return None

        # Fix common malformed JSON: unquoted values after "name":
        text = re.sub(r'"name"\s*:\s*([a-zA-Z_]\w*)', r'"name": "\1"', text)
        # Fix single quotes to double quotes
        text = text.replace("'", '"')

        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract just the JSON object
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if not match:
                return None
            try:
                obj = json.loads(match.group())
            except json.JSONDecodeError:
                return None

        name = obj.get("name")
        params = obj.get("parameters") or obj.get("arguments") or {}
        if not name:
            return None

        return {"function": {"name": name, "arguments": params}}

    def _run_tool_round(self, messages: List[Dict], tools: List,
                        tool_executor: Callable, remaining_rounds: int) -> str:
        """Recursively call Ollama, executing tool calls until the LLM produces text."""
        # If rounds remain, offer tools; otherwise force a text-only response
        data = self._call_ollama(
            messages, tools=tools if remaining_rounds > 0 else None
        )

        assistant_msg = data.get("message", {})
        tool_calls = assistant_msg.get("tool_calls")
        content = assistant_msg.get("content", "")

        # Fallback: if the LLM wrote the tool call as plain text, parse it
        if not tool_calls and content and remaining_rounds > 0:
            recovered = self._parse_tool_call_from_text(content)
            if recovered:
                tool_calls = [recovered]
                # Rewrite assistant_msg so context stays consistent
                assistant_msg = {"role": "assistant", "content": "", "tool_calls": tool_calls}

        # Base cases: no tool calls or no remaining rounds
        if not tool_calls or remaining_rounds <= 0:
            return content

        # Append the assistant message (with its tool_calls) to context
        messages.append(assistant_msg)

        # Execute each tool call and append results
        for tc in tool_calls:
            name, result = self._execute_tool_call(tc, tool_executor)
            print(f"[Tool Call] {name}({tc.get('function', {}).get('arguments', {})}) -> {len(result)} chars")
            messages.append({"role": "tool", "content": result})

        return self._run_tool_round(messages, tools, tool_executor, remaining_rounds - 1)

    def generate_response(self, query: str,
                         context: str = "",
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_executor: Optional[Callable] = None) -> str:
        """
        Generate AI response using provided context.

        Args:
            query: The user's question or request
            context: Retrieved course content to answer from
            conversation_history: Previous messages for context
            tools: Optional tool definitions for Ollama function calling
            tool_executor: Callable(name, **kwargs) to execute tool calls

        Returns:
            Generated response as string
        """

        # Build system content
        system_content = self.SYSTEM_PROMPT
        if conversation_history:
            system_content += f"\n\nPrevious conversation:\n{conversation_history}"

        # Build user message with context
        if context:
            user_content = f"Course context:\n{context}\n\nQuestion: {query}"
        else:
            user_content = query

        # Build messages list
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        # Tool-calling path: recursive loop
        if tools is not None and tool_executor is not None:
            return self._run_tool_round(messages, tools, tool_executor, self.MAX_TOOL_ROUNDS)

        # Default path: single call, no tools
        data = self._call_ollama(messages)
        return data.get("message", {}).get("content", "")
