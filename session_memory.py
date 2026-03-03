"""
Session Memory Management for Agent X Call Center
Provides conversation context persistence across utterances
"""

import json
import os
import threading
from datetime import datetime
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class CallSession:
    """Represents a single call session with full context"""
    call_sid: str
    direction: str  # 'inbound' or 'outbound'
    merchant_number: str
    merchant_name: Optional[str] = None
    call_stage: str = "greeting"  # greeting, qualification, closing, etc.
    last_utterance: Optional[str] = None
    alan_response: Optional[str] = None
    conversation_history: list = None  # List of (speaker, message) tuples
    merchant_state: Dict[str, Any] = None  # interested, qualified, declined, etc.
    compliance_acknowledged: bool = False
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.conversation_history is None:
            self.conversation_history = []
        if self.merchant_state is None:
            self.merchant_state = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class SessionManager:
    """Manages call sessions with thread-safe operations"""

    def __init__(self, storage_file: str = "call_sessions.json"):
        self.storage_file = storage_file
        self._sessions: Dict[str, CallSession] = {}
        self._lock = threading.Lock()
        self._load_sessions()

    def _load_sessions(self):
        """Load sessions from persistent storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    for sid, session_data in data.items():
                        # Convert datetime strings back to datetime objects
                        if 'created_at' in session_data:
                            session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
                        if 'updated_at' in session_data:
                            session_data['updated_at'] = datetime.fromisoformat(session_data['updated_at'])
                        self._sessions[sid] = CallSession(**session_data)
        except Exception as e:
            print(f"Error loading sessions: {e}")
            self._sessions = {}

    def _save_sessions(self):
        """Save sessions to persistent storage"""
        try:
            data = {}
            for sid, session in self._sessions.items():
                session_dict = asdict(session)
                # Convert datetime objects to ISO strings
                session_dict['created_at'] = session.created_at.isoformat()
                session_dict['updated_at'] = session.updated_at.isoformat()
                data[sid] = session_dict

            with open(self.storage_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving sessions: {e}")

    def get_session(self, call_sid: str, direction: str = None, merchant_number: str = None) -> CallSession:
        """Get or create a session for the given call"""
        with self._lock:
            if call_sid not in self._sessions:
                self._sessions[call_sid] = CallSession(
                    call_sid=call_sid,
                    direction=direction or "unknown",
                    merchant_number=merchant_number or "unknown"
                )
                self._save_sessions()
            return self._sessions[call_sid]

    def update_session(self, call_sid: str, **updates):
        """Update session with new information"""
        with self._lock:
            if call_sid in self._sessions:
                session = self._sessions[call_sid]
                for key, value in updates.items():
                    if hasattr(session, key):
                        setattr(session, key, value)
                session.updated_at = datetime.now()

                # Handle special cases
                if 'utterance' in updates:
                    session.last_utterance = updates['utterance']
                if 'alan_response' in updates:
                    session.alan_response = updates['alan_response']
                    # Add to conversation history
                    session.conversation_history.append(("alan", updates['alan_response']))

                self._save_sessions()

    def add_conversation_turn(self, call_sid: str, speaker: str, message: str):
        """Add a turn to the conversation history"""
        with self._lock:
            if call_sid in self._sessions:
                session = self._sessions[call_sid]
                session.conversation_history.append((speaker, message))
                session.updated_at = datetime.now()
                self._save_sessions()

    def get_conversation_context(self, call_sid: str) -> str:
        """Get formatted conversation context for Alan"""
        with self._lock:
            if call_sid not in self._sessions:
                return ""

            session = self._sessions[call_sid]
            context_parts = []

            # Add session info
            context_parts.append(f"Direction: {session.direction}")
            context_parts.append(f"Stage: {session.call_stage}")
            context_parts.append(f"Merchant: {session.merchant_number}")
            if session.merchant_name:
                context_parts.append(f"Merchant Name: {session.merchant_name}")

            # Add merchant state
            if session.merchant_state:
                state_info = ", ".join(f"{k}: {v}" for k, v in session.merchant_state.items())
                context_parts.append(f"Merchant State: {state_info}")

            # Add recent conversation history (last 5 turns)
            if session.conversation_history:
                recent_history = session.conversation_history[-5:]
                history_text = "\n".join(f"{speaker}: {msg}" for speaker, msg in recent_history)
                context_parts.append(f"Recent Conversation:\n{history_text}")

            return "\n".join(context_parts)

    def end_session(self, call_sid: str):
        """Mark session as ended (keep for history but stop active tracking)"""
        with self._lock:
            if call_sid in self._sessions:
                session = self._sessions[call_sid]
                session.call_stage = "ended"
                session.updated_at = datetime.now()
                self._save_sessions()

    def cleanup_old_sessions(self, days_old: int = 7):
        """Remove sessions older than specified days"""
        cutoff = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        with self._lock:
            to_remove = []
            for sid, session in self._sessions.items():
                if session.updated_at.timestamp() < cutoff:
                    to_remove.append(sid)

            for sid in to_remove:
                del self._sessions[sid]

            if to_remove:
                self._save_sessions()
                print(f"Cleaned up {len(to_remove)} old sessions")

# Global session manager instance
session_manager = SessionManager()