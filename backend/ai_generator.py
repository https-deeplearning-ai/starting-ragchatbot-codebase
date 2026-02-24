import boto3
import json
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Claude via AWS Bedrock using boto3"""

    # Static system prompt to avoid rebuilding on each call
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

    def __init__(self, model: str, aws_region: str = None, aws_profile: str = None):
        session = boto3.session.Session(profile_name=aws_profile or None)
        self.client = session.client("bedrock-runtime", region_name=aws_region)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "temperature": 0,
            "maxTokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [{"role": "user", "content": [{"text": query}]}]

        api_params = {
            "modelId": self.model,
            "messages": messages,
            "system": [{"text": system_content}],
            "inferenceConfig": self.base_params,
        }

        if tools:
            api_params["toolConfig"] = {
                "tools": tools,
                "toolChoice": {"auto": {}},
            }

        response = self.client.converse(**api_params)

        if response["stopReason"] == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)

        return response["output"]["message"]["content"][0]["text"]

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        messages = base_params["messages"].copy()

        # Add assistant's tool use turn
        assistant_content = initial_response["output"]["message"]["content"]
        messages.append({"role": "assistant", "content": assistant_content})

        # Execute tools and collect results
        tool_results = []
        for block in assistant_content:
            if "toolUse" in block:
                tool_use = block["toolUse"]
                result = tool_manager.execute_tool(tool_use["name"], **tool_use["input"])
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_use["toolUseId"],
                        "content": [{"text": result}],
                    }
                })

        messages.append({"role": "user", "content": tool_results})

        # Final call — toolConfig must be retained when history has tool blocks
        final_params = {
            **base_params,
            "messages": messages,
        }

        final_response = self.client.converse(**final_params)
        return final_response["output"]["message"]["content"][0]["text"]