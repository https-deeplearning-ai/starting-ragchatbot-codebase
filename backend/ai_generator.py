import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Tool Usage:
You have two tools available:
- **search_course_content** — search course materials for detailed content, concepts, or explanations
- **get_course_outline** — retrieve the full lesson list and links for a specific course

Rules:
- Use `get_course_outline` for outline-related questions (e.g., "what lessons does X have?", "show me the syllabus", "list the topics in course Y")
- Use `search_course_content` for questions about specific content, concepts, or explanations
- When returning a course outline, always include: course title, course link, and for each lesson its number and title
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

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
    
    def __init__(self, api_key: str, model: str, max_rounds: int = 5):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_rounds = max_rounds

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
                         max_rounds: Optional[int] = None) -> str:
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
            return self._handle_tool_execution(
                response, api_params, tool_manager,
                max_rounds=max_rounds or self.max_rounds
            )
        
        # Return direct response
        text_blocks = [b.text for b in response.content if hasattr(b, "text")]
        return text_blocks[0] if text_blocks else ""
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager, max_rounds: int = 5):
        """
        Handle iterative tool execution rounds until Claude produces a text response,
        max_rounds is exhausted, or no tool results are generated.
        """
        messages = base_params["messages"].copy()
        current_response = initial_response

        for _ in range(max_rounds):
            if current_response.stop_reason != "tool_use":
                break

            messages.append({"role": "assistant", "content": current_response.content})

            tool_results = []
            for block in current_response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Tool execution failed: {e}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            if not tool_results:
                break

            messages.append({"role": "user", "content": tool_results})

            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
            }
            if base_params.get("tools"):
                next_params["tools"] = base_params["tools"]
                next_params["tool_choice"] = {"type": "auto"}

            current_response = self.client.messages.create(**next_params)

        text_blocks = [b.text for b in current_response.content if hasattr(b, "text")]
        if not text_blocks:
            return "I was unable to generate a complete response. Please try rephrasing your question."
        return text_blocks[0]