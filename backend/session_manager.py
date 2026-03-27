from typing import Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class Message:
    """Represents a single message in a conversation"""
    role: str     # "user" or "assistant"
    content: str  # The message content

@dataclass
class Session:
    """Represents a conversation session with language preference"""
    session_id: str
    messages: List[Message] = field(default_factory=list)
    language: Optional[str] = None  # 'en' or 'zh'

class SessionManager:
    """Manages conversation sessions and message history"""

    def __init__(self, max_history: int = 5):
        self.max_history = max_history
        self.sessions: Dict[str, Session] = {}
        self.session_counter = 0
    
    def create_session(self) -> str:
        """Create a new conversation session"""
        self.session_counter += 1
        session_id = f"session_{self.session_counter}"
        self.sessions[session_id] = Session(session_id=session_id)
        return session_id

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history"""
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(session_id=session_id)

        message = Message(role=role, content=content)
        self.sessions[session_id].messages.append(message)

        # Keep conversation history within limits
        if len(self.sessions[session_id].messages) > self.max_history * 2:
            self.sessions[session_id].messages = self.sessions[session_id].messages[-self.max_history * 2:]

    def add_exchange(self, session_id: str, user_message: str, assistant_message: str):
        """Add a complete question-answer exchange"""
        self.add_message(session_id, "user", user_message)
        self.add_message(session_id, "assistant", assistant_message)

    def get_conversation_history(self, session_id: Optional[str]) -> Optional[str]:
        """Get formatted conversation history for a session"""
        if not session_id or session_id not in self.sessions:
            return None

        messages = self.sessions[session_id].messages
        if not messages:
            return None

        # Format messages for context
        formatted_messages = []
        for msg in messages:
            formatted_messages.append(f"{msg.role.title()}: {msg.content}")

        return "\n".join(formatted_messages)

    def get_session_language(self, session_id: str) -> Optional[str]:
        """Get the language preference for a session"""
        if session_id not in self.sessions:
            return None
        return self.sessions[session_id].language

    def set_session_language(self, session_id: str, language: str):
        """Set the language preference for a session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = Session(session_id=session_id)
        self.sessions[session_id].language = language

    def clear_session(self, session_id: str):
        """Clear all messages from a session"""
        if session_id in self.sessions:
            self.sessions[session_id].messages = []