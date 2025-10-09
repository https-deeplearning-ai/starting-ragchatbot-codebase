import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to search tools for course information.

Sequential Tool Usage Guidelines:
- **Multiple tool rounds supported**: You can use tools across up to 2 sequential rounds per query
- **Complex queries encouraged**: Break down multi-step queries into sequential tool calls
- **Context preservation**: Information from previous tool calls in the same query is preserved
- **Examples of multi-step queries**:
  - "Find course X, then search for topics related to lesson Y of that course"
  - "Get the outline for course A, then search for specific content mentioned in lesson 2"
  - "Search for content about topic Z, then find other courses that cover similar material"

Tool Usage Guidelines:
- **Course outline/structure questions**: Use `get_course_outline` tool for any questions about:
  - Course outlines, structure, or overviews
  - Lesson lists or what lessons are available
  - Course organization or curriculum
  - Questions containing words like "outline", "structure", "lessons", "overview"
- **Course content searches**: Use `search_course_content` tool for questions about specific content within lessons or courses
- **Sequential reasoning**: Use tool results to inform next tool calls
- **Context building**: Each tool call can build on previous results
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Termination Conditions:
- Maximum 2 tool execution rounds per query
- Stop when no more tools needed to answer the question
- Stop if tool execution fails

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course outline/structure questions**: Use `get_course_outline` tool first, then answer
- **Course-specific content questions**: Use `search_course_content` tool first, then answer
- **Multi-step questions**: Use sequential tool calls as needed
- **No meta-commentary**: Provide direct answers only — no reasoning process, tool explanations, or question-type analysis

When responding to outline requests:
- Return tool output EXACTLY as provided - do not reformat or modify
- Preserve all markdown formatting including links
- Do not summarize or change the structure

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Preserve formatting** - Return tool output exactly as provided
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
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
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._execute_sequential_tools(response, api_params, tool_manager)

        # Return direct response
        return response.content[0].text
    
    def _execute_sequential_tools(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Execute tools sequentially across multiple rounds (max 2 per query).

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after sequential tool execution
        """
        MAX_ROUNDS = 2
        current_round = 0
        current_response = initial_response
        messages = base_params["messages"].copy()

        while current_round < MAX_ROUNDS:
            current_round += 1

            try:
                # Execute current round of tools
                current_response, messages = self._execute_single_tool_round(
                    current_response, base_params, tool_manager, messages, current_round
                )

                # Check if we should continue to next round
                if not self._should_continue_execution(current_response, current_round, MAX_ROUNDS):
                    break

            except Exception as e:
                # Handle tool execution errors gracefully
                return self._handle_tool_error(e, current_round, messages, base_params)

        # Return final response
        return self._extract_final_response(current_response)

    def _execute_single_tool_round(self, response, base_params: Dict[str, Any], tool_manager, messages: list, round_number: int):
        """
        Execute one round of tool calling and get follow-up response.

        Args:
            response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            messages: Current conversation messages
            round_number: Current round number

        Returns:
            Tuple of (next_response, updated_messages)
        """
        # Add AI's tool use response to conversation
        messages.append({"role": "assistant", "content": response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })

                except Exception as e:
                    # Handle individual tool errors gracefully
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": f"Tool execution error: {str(e)}"
                    })

        # Add tool results to conversation
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Prepare API call for next round - keep tools available
        next_params = {
            **self.base_params,
            "messages": messages,
            "system": self._build_enhanced_system_prompt(base_params["system"], round_number)
        }

        # Keep tools available for potential next round
        if "tools" in base_params:
            next_params["tools"] = base_params["tools"]
            next_params["tool_choice"] = {"type": "auto"}

        # Get next response from Claude
        next_response = self.client.messages.create(**next_params)

        return next_response, messages

    def _should_continue_execution(self, response, current_round: int, max_rounds: int) -> bool:
        """
        Decide whether to continue with another tool execution round.

        Args:
            response: Current response to check
            current_round: Current round number
            max_rounds: Maximum allowed rounds

        Returns:
            True if should continue, False otherwise
        """
        # Stop if max rounds reached
        if current_round >= max_rounds:
            return False

        # Continue only if response contains tool_use blocks
        has_tool_use = any(
            content.type == "tool_use"
            for content in response.content
        )

        return has_tool_use and response.stop_reason == "tool_use"

    def _build_enhanced_system_prompt(self, base_system: str, round_number: int) -> str:
        """
        Build enhanced system prompt with round context.

        Args:
            base_system: Base system prompt
            round_number: Current round number

        Returns:
            Enhanced system prompt with context
        """
        if round_number <= 1:
            return base_system

        enhanced_prompt = base_system + f"\n\nCurrent execution context: Round {round_number}/2 - You can use tool results from previous rounds to inform your next tool calls."
        return enhanced_prompt

    def _handle_tool_error(self, error: Exception, round_number: int, messages: list, base_params: Dict[str, Any]) -> str:
        """
        Handle tool execution errors gracefully.

        Args:
            error: The exception that occurred
            round_number: Round where error occurred
            messages: Current conversation messages
            base_params: Base API parameters

        Returns:
            Error response or best available response
        """
        error_msg = f"I encountered an error while executing tools in round {round_number}: {str(error)}"

        # Try to provide a response based on available information
        try:
            # Prepare fallback API call without tools
            fallback_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }

            fallback_response = self.client.messages.create(**fallback_params)
            return fallback_response.content[0].text
        except Exception:
            # If even fallback fails, return error message
            return error_msg

    def _extract_final_response(self, response) -> str:
        """
        Extract final response text from API response.

        Args:
            response: API response object

        Returns:
            Response text
        """
        if hasattr(response, 'content') and response.content:
            return response.content[0].text

        return "I apologize, but I was unable to generate a proper response."