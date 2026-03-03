"""Delta packet schema."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from talk.schema import TalkPacket, Lineage


class DeltaType(str, Enum):
    """Types of deltas that can occur."""

    ADD = "add"              # New entity added
    REMOVE = "remove"        # Entity removed
    MODIFY = "modify"        # Entity modified
    DRIFT = "drift"          # Unexpected change detected
    CORRECTION = "correction"  # Corrective action applied
    CONSTRAINT = "constraint"  # Constraint violation/resolution


class DeltaPacket(BaseModel):
    """
    Represents a semantic delta between two states.

    This captures what changed, why, and the impact.
    """

    id: str = Field(..., description="Unique delta identifier")
    delta_type: DeltaType
    previous_state: Optional[TalkPacket] = None
    new_state: TalkPacket
    affected_entities: List[str] = Field(default_factory=list, description="Entities impacted by this delta")
    semantic_changes: Dict[str, Any] = Field(default_factory=dict, description="Semantic description of changes")
    lineage: Lineage
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        validate_assignment = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeltaPacket":
        """Create from dictionary."""
        return cls(**data)