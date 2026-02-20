"""
QPC State - Immutable snapshot of cognitive process
"""
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

class QPCState:
    def __init__(
        self,
        context_data: Dict[str, Any],
        parent_state_id: Optional[str] = None,
        identity_context: Optional[Dict[str, Any]] = None,
        coherence_window_id: Optional[str] = None
    ):
        self.state_id = str(uuid.uuid4())
        self.parent_state_id = parent_state_id
        self.timestamp = datetime.now().isoformat()
        self.identity_context = identity_context or {}
        self.coherence_window_id = coherence_window_id
        self.data = context_data  # The actual state payload (variables, memory, etc.)
        self._immutable = True

    @classmethod
    def from_context(cls, context_dict: Dict[str, Any], **kwargs) -> 'QPCState':
        """Create a state snapshot from a running context dictionary"""
        # Deep copy might be needed in production v1
        return cls(context_data=context_dict.copy(), **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for logging/replay"""
        return {
            "state_id": self.state_id,
            "parent_state_id": self.parent_state_id,
            "timestamp": self.timestamp,
            "identity_context": self.identity_context,
            "coherence_window_id": self.coherence_window_id,
            "data": self.data
        }
