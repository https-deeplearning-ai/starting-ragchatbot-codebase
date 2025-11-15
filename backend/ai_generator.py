import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Up to two sequential searches per query** - use this capability when:
  • The first search provides information needed to formulate a more specific second search
  • You need to compare or correlate information from different courses or lessons
  • Example: Search for a course outline to find a specific lesson topic, then search for that topic across all courses
  • Example: Search for content in one lesson, then search for related content in another course
- **Do NOT use multiple searches to**:
  • Retry the same search with different wording
  • Verify or double-check results from the first search
  • Search for the same information in different ways
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
                         tool_manager=None,
                         max_rounds: int = 2) -> str:
        """
        Generate AI response with optional sequential tool usage and conversation context.

        Supports up to `max_rounds` sequential tool calls, allowing Claude to:
        - Make an initial search to gather information
        - Use results from the first search to inform a second search
        - Synthesize a final answer from all gathered information

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum sequential tool calls allowed (default: 2)

        Returns:
            Generated response as string

        Raises:
            Exception: With descriptive message if API call or tool execution fails
        """
        try:
            # Build system content efficiently
            system_content = (
                f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
                if conversation_history
                else self.SYSTEM_PROMPT
            )

            # Initialize message history for this query
            messages = [{"role": "user", "content": query}]

            # Initialize round counter
            round_count = 0
            last_response = None

            # Iterative tool execution loop
            while round_count < max_rounds:
                # Make API call with tools available
                response = self._make_api_call(
                    messages=messages,
                    system=system_content,
                    tools=tools if tools and tool_manager else None
                )

                last_response = response

                # Check stop reason - if not tool_use, we have final answer
                if response.stop_reason != "tool_use":
                    # Claude provided direct answer - return it
                    return response.content[0].text

                # Tool use detected - execute tools
                print(f"[AI_GENERATOR] Round {round_count + 1}/{max_rounds}: Executing tools")

                # Add assistant's tool_use response to messages
                messages.append({"role": "assistant", "content": response.content})

                # Execute tools and get results
                tool_results = self._execute_tools_and_build_results(
                    response.content,
                    tool_manager
                )

                # Add tool results to messages
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

                # Increment round counter
                round_count += 1

            # Exited loop - max rounds reached
            # Make final synthesis call WITHOUT tools
            print(f"[AI_GENERATOR] Max rounds ({max_rounds}) reached, performing final synthesis")
            final_response = self._make_api_call(
                messages=messages,
                system=system_content,
                tools=None  # No tools for final synthesis
            )

            return final_response.content[0].text

        except Exception as e:
            # Log the error (in production, use proper logging)
            print(f"[AI_GENERATOR ERROR] generate_response failed: {str(e)}")
            raise

    def _make_api_call(self, messages: List[Dict[str, Any]], system: str,
                       tools: Optional[List] = None):
        """
        Make a single API call to Claude with error handling.

        Args:
            messages: Message history for the API call
            system: System prompt content
            tools: Optional tool definitions to include

        Returns:
            API response object

        Raises:
            Exception: With descriptive message if API call fails
        """
        # Build API parameters
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system
        }

        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Make API call with comprehensive error handling
        try:
            return self.client.messages.create(**api_params)
        except anthropic.APIConnectionError as e:
            raise Exception(f"Failed to connect to Anthropic API. Please check your internet connection. Details: {str(e)}")
        except anthropic.APITimeoutError as e:
            raise Exception(f"Anthropic API request timed out. Please try again. Details: {str(e)}")
        except anthropic.RateLimitError as e:
            raise Exception(f"Anthropic API rate limit exceeded. Please wait a moment before trying again. Details: {str(e)}")
        except anthropic.APIStatusError as e:
            raise Exception(f"Anthropic API error (status {e.status_code}). Details: {str(e)}")
        except anthropic.AuthenticationError as e:
            raise Exception(f"Anthropic API authentication failed. Please check your API key. Details: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error calling Anthropic API: {str(e)}")

    def _execute_tools_and_build_results(self, content_blocks, tool_manager) -> List[Dict[str, Any]]:
        """
        Execute all tool calls from a response and build tool result messages.

        Args:
            content_blocks: Content blocks from API response (may contain tool_use)
            tool_manager: Manager to execute tools

        Returns:
            List of tool result dictionaries in API format
        """
        tool_results = []

        for content_block in content_blocks:
            if content_block.type == "tool_use":
                try:
                    # Execute the tool
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )

                    # Format successful result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })

                except Exception as e:
                    # Log error and return as tool result (graceful degradation)
                    print(f"[AI_GENERATOR ERROR] Tool '{content_block.name}' execution failed: {str(e)}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": f"Tool execution failed: {str(e)}",
                        "is_error": True
                    })

        return tool_results