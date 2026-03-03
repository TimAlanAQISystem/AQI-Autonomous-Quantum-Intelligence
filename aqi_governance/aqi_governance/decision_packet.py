"""Decision packet schema."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from talk.schema import TalkPacket, Lineage, ConstraintType


class DecisionType(str, Enum):
    """Types of governance decisions."""

    APPROVE = "approve"      # Allow the action
    REJECT = "reject"        # Block the action
    ESCALATE = "escalate"    # Require higher authority
    MODIFY = "modify"        # Allow with modifications
    DEFER = "defer"          # Delay decision


class DecisionPacket(BaseModel):
    """
    Represents a governance decision on a TalkPacket.

    This captures the governance engine's response to a state change request.
    """

    id: str = Field(..., description="Unique decision identifier")
    decision: DecisionType
    original_packet: TalkPacket
    reason: str = Field(..., description="Explanation for the decision")
    violated_constraints: List[ConstraintType] = Field(default_factory=list)
    required_authority_level: Optional[int] = None
    suggested_modifications: Dict[str, Any] = Field(default_factory=dict)
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
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionPacket":
        """Create from dictionary."""
        return cls(**data)