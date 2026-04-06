import requests
import json
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with MiniMax API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Tools Available:
1. search_course_content - Search for specific content within courses
2. get_course_outline - Get course outline with title, link, and all lessons

Tool Selection Guidelines:
- Use **get_course_outline** for: course outline requests, listing all lessons, what lessons are in a course, course structure, syllabus queries
- Use **search_course_content** for: specific content questions, detailed information about topics

Search Tool Usage:
- Use the search tools **only** for questions about course content or outline
- **One search per query maximum**
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"

When responding to outline queries, include:
- Course title
- Course link (if available)
- Number and title of each lesson

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = 0
        self.max_tokens = 800

    def _make_request(self, messages: List[Dict], tools: Optional[List] = None, stream: bool = False):
        """Make API request to MiniMax"""
        url = f"{self.base_url}/v1/messages"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Format messages for MiniMax Anthropic-compatible API
        formatted_messages = []
        system_prompt = ""

        for msg in messages:
            if msg.get("role") == "system":
                # Combine system messages
                system_prompt += msg.get("text", "") + "\n"
            else:
                # Convert to Anthropic format: content as array with text object
                content = msg.get("text", "")
                formatted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": [{"type": "text", "text": content}]
                })

        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": stream
        }

        if system_prompt:
            payload["system"] = system_prompt.strip()

        if formatted_messages:
            payload["messages"] = formatted_messages

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = {"type": "auto"}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            print(f"MiniMax request: {payload}")
            print(f"MiniMax response status: {response.status_code}")
            print(f"MiniMax response: {response.text[:500]}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_detail = e.response.text if e.response else str(e)
            print(f"MiniMax API error detail: {error_detail}")
            raise Exception(f"MiniMax API error: {error_detail}")

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with sequential tool calling (up to 2 rounds).

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        # Build initial messages
        messages = []
        messages.append({"role": "system", "text": self.SYSTEM_PROMPT})
        if conversation_history:
            messages.append({"role": "system", "text": f"Previous conversation:\n{conversation_history}"})
        messages.append({"role": "user", "text": query})

        # Sequential tool calling: max 2 rounds
        max_rounds = 2

        for round_num in range(1, max_rounds + 1):
            # Make request with tools enabled
            response = self._make_request(messages, tools=tools)

            stop_reason = response.get("stop_reason")
            content_blocks = response.get("content", [])

            # Check if model wants to use a tool
            if stop_reason == "tool_use" and tool_manager:
                tool_block = self._extract_tool_use(content_blocks)
                if not tool_block:
                    break

                # Execute tool with error handling
                tool_result = self._execute_tool_safely(tool_manager, tool_block)

                # Accumulate messages for next round
                messages.append({"role": "assistant", "content": [tool_block]})
                messages.append(self._build_tool_result_message(tool_block, tool_result))

                # If not last round, continue to next round
                if round_num < max_rounds:
                    continue
                else:
                    # Last round - make final call without tools
                    final_response = self._make_request(messages, tools=None)
                    content_blocks = final_response.get("content", [])
            else:
                # No tool use - return response
                pass

            # Extract text and return
            return self._extract_text_from_blocks(content_blocks)

        # Fallback: return whatever we have
        return self._extract_text_from_blocks(content_blocks)

    def _extract_tool_use(self, content_blocks: List[Dict]) -> Optional[Dict]:
        """Extract tool_use block from response content."""
        for block in content_blocks:
            if block.get("type") == "tool_use":
                return block
        return None

    def _execute_tool_safely(self, tool_manager, tool_block: Dict) -> str:
        """Execute tool with graceful error handling."""
        try:
            tool_name = tool_block.get("name")
            tool_input = tool_block.get("input", {})
            return tool_manager.execute_tool(tool_name, **tool_input)
        except KeyError as e:
            return f"Tool parameter error: {str(e)}"
        except Exception as e:
            return f"Tool execution error: {str(e)}"

    def _build_tool_result_message(self, tool_block: Dict, result: str) -> Dict:
        """Build tool_result message in API format."""
        return {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_block.get("id"),
                "content": result
            }]
        }

    def _extract_text_from_blocks(self, content_blocks: List[Dict]) -> str:
        """Extract text from content blocks."""
        response_text = ""
        for block in content_blocks:
            if block.get("type") == "text":
                response_text += block.get("text", "")
        return response_text