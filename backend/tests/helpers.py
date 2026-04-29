from unittest.mock import MagicMock
from vector_store import SearchResults


def make_search_results(documents=None, metadata=None, distances=None, error=None):
    return SearchResults(
        documents=documents or [],
        metadata=metadata or [],
        distances=distances or [],
        error=error,
    )


def make_text_block(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def make_tool_use_block(tool_name: str, tool_input: dict, block_id: str = "tu_001"):
    # spec limits accessible attributes — hasattr(block, "text") returns False
    block = MagicMock(spec=["type", "name", "input", "id"])
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = block_id
    return block


def make_message(content_blocks, stop_reason: str = "end_turn"):
    msg = MagicMock()
    msg.stop_reason = stop_reason
    msg.content = content_blocks
    return msg
