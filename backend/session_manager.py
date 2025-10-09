from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import time
from logger import get_logger

# Initialize logger
logger = get_logger(__name__)

@dataclass
class Message:
    """Represents a single message in a conversation"""
    role: str     # "user" or "assistant"
    content: str  # The message content
    timestamp: datetime = None  # When the message was created

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class SessionInfo:
    """Information about a conversation session"""
    session_id: str
    messages: List[Message]
    created_at: datetime
    last_activity: datetime

    def is_expired(self, max_idle_time: timedelta) -> bool:
        """Check if session has exceeded max idle time"""
        return datetime.utcnow() - self.last_activity > max_idle_time

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

class SessionManager:
    """Manages conversation sessions and message history with automatic cleanup"""

    def __init__(self, max_history: int = 5, session_timeout_minutes: int = 60, cleanup_interval_minutes: int = 30):
        self.max_history = max_history
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.cleanup_interval = timedelta(minutes=cleanup_interval_minutes)

        self.sessions: Dict[str, SessionInfo] = {}
        self.session_counter = 0
        self._lock = threading.Lock()

        # Start cleanup thread
        self._cleanup_thread = None
        self._stop_cleanup = threading.Event()
        self._start_cleanup_thread()

        logger.info(f"SessionManager initialized: max_history={max_history}, "
                   f"session_timeout={session_timeout_minutes}min, "
                   f"cleanup_interval={cleanup_interval_minutes}min")
    
    def create_session(self) -> str:
        """Create a new conversation session"""
        with self._lock:
            self.session_counter += 1
            session_id = f"session_{self.session_counter}"
            now = datetime.utcnow()
            self.sessions[session_id] = SessionInfo(
                session_id=session_id,
                messages=[],
                created_at=now,
                last_activity=now
            )
            logger.info(f"Created new session: {session_id}")
            return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history"""
        with self._lock:
            if session_id not in self.sessions:
                # Create session if it doesn't exist
                now = datetime.utcnow()
                self.sessions[session_id] = SessionInfo(
                    session_id=session_id,
                    messages=[],
                    created_at=now,
                    last_activity=now
                )

            session = self.sessions[session_id]
            message = Message(role=role, content=content)
            session.messages.append(message)
            session.update_activity()

            # Keep conversation history within limits
            if len(session.messages) > self.max_history * 2:
                session.messages = session.messages[-self.max_history * 2:]
                logger.debug(f"Trimmed message history for session {session_id}")
    
    def add_exchange(self, session_id: str, user_message: str, assistant_message: str):
        """Add a complete question-answer exchange"""
        self.add_message(session_id, "user", user_message)
        self.add_message(session_id, "assistant", assistant_message)
    
    def get_conversation_history(self, session_id: Optional[str]) -> Optional[str]:
        """Get formatted conversation history for a session"""
        with self._lock:
            if not session_id or session_id not in self.sessions:
                return None

            session = self.sessions[session_id]
            if not session.messages:
                return None

            # Update activity timestamp
            session.update_activity()

            # Format messages for context
            formatted_messages = []
            for msg in session.messages:
                formatted_messages.append(f"{msg.role.title()}: {msg.content}")

            return "\n".join(formatted_messages)
    
    def clear_session(self, session_id: str):
        """Clear all messages from a session"""
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Cleared session: {session_id}")

    def _start_cleanup_thread(self):
        """Start the background cleanup thread"""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(target=self._cleanup_expired_sessions, daemon=True)
            self._cleanup_thread.start()
            logger.info("Started session cleanup thread")

    def _cleanup_expired_sessions(self):
        """Background task to clean up expired sessions"""
        while not self._stop_cleanup.wait(self.cleanup_interval.total_seconds()):
            try:
                expired_sessions = []
                with self._lock:
                    for session_id, session in self.sessions.items():
                        if session.is_expired(self.session_timeout):
                            expired_sessions.append(session_id)

                    for session_id in expired_sessions:
                        del self.sessions[session_id]

                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions: {expired_sessions}")

            except Exception as e:
                logger.error(f"Error during session cleanup: {e}", exc_info=True)

    def get_session_stats(self) -> Dict[str, int]:
        """Get statistics about active sessions"""
        with self._lock:
            total_sessions = len(self.sessions)
            total_messages = sum(len(session.messages) for session in self.sessions.values())
            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages
            }

    def shutdown(self):
        """Gracefully shutdown the session manager"""
        logger.info("Shutting down session manager...")
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5)
        logger.info("Session manager shut down")