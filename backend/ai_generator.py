import json
from typing import Dict, List, Optional

import anthropic
from openai import OpenAI


class AIGenerator:
    """Handles interactions with Claude API via Anthropic or OpenRouter"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in course materials and educational content with access to comprehensive search and outline tools for course information.

Tool Selection Guidelines:
- **Course Outline Tool** (`get_course_outline`): Use for questions about:
  - Course structure, topics, or overview ("What's in this course?", "What topics are covered?")
  - Lesson list or organization ("How many lessons?", "What lessons are included?")
  - Course metadata (instructor, course details)
  - General course navigation questions

- **Content Search Tool** (`search_course_content`): Use for questions about:
  - Specific content within lessons ("What does lesson 3 say about...?")
  - Detailed technical information from course materials
  - Code examples, explanations, or specific concepts taught in lessons

- **Sequential tool use allowed**: You may use tools across multiple turns
  - Maximum 2 rounds of tool calls per query
  - Use first round to gather context, second to get specifics
  - Example: get_course_outline → then search_course_content for details
- Synthesize tool results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course structure questions**: Use outline tool first, then answer
- **Course content questions**: Use search tool first, then answer
- **No meta-commentary**:
  - Provide direct answers only — no reasoning process, tool usage explanations, or question-type analysis
  - Do not mention "based on the search results" or "using the outline tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(
        self,
        api_key: str,
        model: str,
        provider: str = "anthropic",
        base_url: Optional[str] = None,
        max_tool_rounds: int = 2,
    ):
        self.provider = provider.lower()
        self.model = model
        self.max_tool_rounds = max_tool_rounds

        # Initialize appropriate client based on provider
        if self.provider == "openrouter":
            self.client = OpenAI(
                api_key=api_key, base_url=base_url or "https://openrouter.ai/api/v1"
            )
        else:  # anthropic (default)
            self.client = anthropic.Anthropic(api_key=api_key)

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 300,  # Llama free model has higher limits
        }

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        if self.provider == "openrouter":
            return self._generate_openrouter(query, conversation_history, tools, tool_manager)
        else:
            return self._generate_anthropic(query, conversation_history, tools, tool_manager)

    def _generate_anthropic(
        self, query: str, conversation_history: Optional[str], tools: Optional[List], tool_manager
    ) -> str:
        """Generate response using Anthropic SDK with loop-based sequential tool calling"""
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages with user query
        messages = [{"role": "user", "content": query}]

        # Sequential tool calling loop
        for iteration in range(self.max_tool_rounds):
            # Prepare API call parameters
            api_params = {**self.base_params, "messages": messages, "system": system_content}

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Get response from Claude
            response = self.client.messages.create(**api_params)

            # Termination condition: No tool use - Claude gave final answer
            if response.stop_reason != "tool_use":
                return response.content[0].text

            # Tool use detected - execute tools if tool_manager available
            if not tool_manager:
                # No tool manager, make final call without tools
                break

            # Add assistant's tool use response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result = tool_manager.execute_tool(
                            content_block.name, **content_block.input
                        )
                    except Exception as e:
                        tool_result = f"Error executing tool: {str(e)}"
                        print(f"Tool execution error: {e}")

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Continue to next iteration (or exit if max rounds reached)

        # Max iterations reached - make final call without tools
        final_params = {**self.base_params, "messages": messages, "system": system_content}

        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text

    def _generate_openrouter(
        self, query: str, conversation_history: Optional[str], tools: Optional[List], tool_manager
    ) -> str:
        """Generate response using OpenRouter (OpenAI-compatible) with loop-based sequential tool calling"""
        # Build system content
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Initialize messages with system prompt and user query
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]

        # Convert Anthropic tool format to OpenAI format if tools provided
        openai_tools = self._convert_tools_to_openai(tools) if tools else None

        # Sequential tool calling loop
        for iteration in range(self.max_tool_rounds):
            # Prepare API call parameters
            api_params = {**self.base_params, "messages": messages}

            # Add tools if available
            if openai_tools:
                api_params["tools"] = openai_tools
                api_params["tool_choice"] = "auto"

            # Get response from OpenRouter
            response = self.client.chat.completions.create(**api_params)

            # Termination condition: No tool calls - Claude gave final answer
            message = response.choices[0].message
            if not message.tool_calls:
                return message.content

            # Tool calls detected - execute tools if tool_manager available
            if not tool_manager:
                # No tool manager, make final call without tools
                break

            # Add assistant's tool call message
            messages.append(message)

            # Execute all tool calls
            for tool_call in message.tool_calls:
                # Parse arguments
                args = json.loads(tool_call.function.arguments)

                # Execute tool
                try:
                    tool_result = tool_manager.execute_tool(tool_call.function.name, **args)
                except Exception as e:
                    tool_result = f"Error executing tool: {str(e)}"
                    print(f"Tool execution error: {e}")

                # Add tool response
                messages.append(
                    {"role": "tool", "tool_call_id": tool_call.id, "content": tool_result}
                )

            # Continue to next iteration (or exit if max rounds reached)

        # Max iterations reached - make final call without tools
        # MUST include system prompt for context
        final_response = self.client.chat.completions.create(
            model=self.base_params["model"],
            messages=[
                {"role": "system", "content": system_content},
                *messages[1:],  # Skip original system message to avoid duplication
            ],
            temperature=self.base_params["temperature"],
            max_tokens=self.base_params["max_tokens"],
        )

        return final_response.choices[0].message.content

    def _convert_tools_to_openai(self, anthropic_tools: List[Dict]) -> List[Dict]:
        """Convert Anthropic tool format to OpenAI function calling format"""
        openai_tools = []
        for tool in anthropic_tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["input_schema"],
                    },
                }
            )
        return openai_tools
