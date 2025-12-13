from dataclasses import dataclass


@dataclass
class Message:
    """Represents a single message in a conversation"""

    role: str  # "user" or "assistant"
    content: str  # The message content


class SessionManager:
    """Manages conversation sessions and message history"""

    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.sessions: dict[str, list[Message]] = {}
        self.session_counter = 0

    def create_session(self) -> str:
        """Create a new conversation session"""
        self.session_counter += 1
        session_id = f"session_{self.session_counter}"
        self.sessions[session_id] = []
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        message = Message(role=role, content=content)
        self.sessions[session_id].append(message)

        # Keep conversation history within limits
        if len(self.sessions[session_id]) > self.max_history * 2:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history * 2 :]

    def add_exchange(self, session_id: str, user_message: str, assistant_message: str):
        """Add a complete question-answer exchange"""
        self.add_message(session_id, "user", user_message)
        self.add_message(session_id, "assistant", assistant_message)

    def get_conversation_history(self, session_id: str | None) -> str | None:
        """Get formatted conversation history for a session"""
        if not session_id or session_id not in self.sessions:
            return None

        messages = self.sessions[session_id]
        if not messages:
            return None

        # Format messages for context
        formatted_messages = []
        for msg in messages:
            formatted_messages.append(f"{msg.role.title()}: {msg.content}")

        return "\n".join(formatted_messages)

    def clear_session(self, session_id: str):
        """Clear all messages from a session"""
        if session_id in self.sessions:
            self.sessions[session_id] = []
