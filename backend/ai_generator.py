from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Maximum number of sequential tool calling rounds
    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for searching course content and retrieving course outlines.

Available Tools:
1. **Course Outline Tool** (get_course_outline) - Retrieve complete course structure
   - **ALWAYS use this tool** for queries asking for: outlines, course structure, lesson list, table of contents, or "what lessons"
   - Returns: course title, course link, and complete lesson list with numbers and titles
   - This is the PREFERRED tool for any structural/organizational queries about a course
   - Present the information directly without meta-commentary

2. **Content Search Tool** (search_course_content) - Search within course materials for specific information
   - Use **only** for questions about specific course content or detailed educational materials within lessons
   - Synthesize search results into accurate, fact-based responses
   - If search yields no results, state this clearly without offering alternatives

Multi-Step Tool Usage:
- You can make **up to 2 sequential tool calls** to gather comprehensive information
- Use the first tool call to gather initial information
- If needed, use a second tool call to gather complementary or comparative information
- After the second tool call, you must provide your final answer
- Examples of multi-step queries:
  * "Compare lesson 1 and lesson 3" → Search lesson 1, then search lesson 3
  * "Get outline then explain lesson 2" → Get outline, then search lesson 2 content
  * "What's in lesson 4 of the course about Neural Networks" → Get outline to find course, then search lesson 4

Efficiency Guidelines:
- **One tool per query** is preferred when sufficient
- Use two calls only when genuinely necessary for comparison or complementary information
- Do not use multiple tools for information that could be gathered in one call
- Example: "What's in lesson 1?" → ONE search call, not outline + search

Tool Selection Rules:
- **"Show me the outline"** → Use get_course_outline tool
- **"What lessons are in the course"** → Use get_course_outline tool
- **"List all lessons"** → Use get_course_outline tool
- **"What topics does the course cover"** → Use get_course_outline tool
- **"Explain [concept] from lesson X"** → Use search_course_content tool
- **"What does the course teach about [topic]"** → Use search_course_content tool

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course outline/structure questions**: ALWAYS use get_course_outline tool first
- **Course-specific content questions**: Use search_course_content tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool usage explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"


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
            "max_tokens": 2048,  # Increased from 800 for comprehensive responses
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

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
            # Debug: print tool names
            print(f"DEBUG: Available tools: {[t['name'] for t in tools]}")

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Debug: print which tool was used if any
        if hasattr(response, "stop_reason"):
            print(f"DEBUG: Stop reason: {response.stop_reason}")
            if response.stop_reason == "tool_use":
                for block in response.content:
                    if hasattr(block, "type") and block.type == "tool_use":
                        print(f"DEBUG: Tool called: {block.name}")

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)

        # Return direct response
        return response.content[0].text

    def _handle_tool_execution(
        self, initial_response, base_params: Dict[str, Any], tool_manager
    ):
        """
        Handle execution of tool calls across multiple rounds with reasoning.

        Supports up to MAX_TOOL_ROUNDS sequential tool calls where Claude can:
        - Use tool results to inform next tool call
        - Reason between tool executions
        - Make comparisons or gather complementary information

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters (includes tools)
            tool_manager: Manager to execute tools

        Returns:
            Final response text after all tool executions
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        current_response = initial_response

        # Loop for up to MAX_TOOL_ROUNDS
        for round_num in range(1, self.MAX_TOOL_ROUNDS + 1):
            # Only process if current response is tool_use
            if current_response.stop_reason != "tool_use":
                break

            print(f"DEBUG: Tool round {round_num}/{self.MAX_TOOL_ROUNDS}")

            # Add AI's tool use response
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    print(f"DEBUG: Executing tool: {content_block.name}")
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

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

            # Prepare next API call
            # CRITICAL: Include tools only if we haven't hit max rounds yet
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
            }

            # Allow tools in next round only if not at limit
            if round_num < self.MAX_TOOL_ROUNDS:
                next_params["tools"] = base_params["tools"]
                next_params["tool_choice"] = {"type": "auto"}
                print(f"DEBUG: Round {round_num} - tools available for next round")
            else:
                print(f"DEBUG: Round {round_num} - final round, no tools for next call")

            # Make next API call
            current_response = self.client.messages.create(**next_params)
            print(
                f"DEBUG: Round {round_num} stop_reason: {current_response.stop_reason}"
            )

        # Extract final text response
        return current_response.content[0].text
