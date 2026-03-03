"""Smoke test for AQI Governance Engine."""

import sys
import os

# Add the package to path
sys.path.insert(0, os.path.dirname(__file__))

from aqi_governance import GovernanceEngine, DecisionType
from talk.schema import TalkPacket, StateChange, Intent, Constraints
from talk.utils import generate_id, get_timestamp


def test_governance_engine():
    """Test basic governance engine functionality."""

    # Create governance engine
    governance = GovernanceEngine()

    # Create a test packet
    packet = TalkPacket(
        id=generate_id(),
        timestamp=get_timestamp(),
        lineage=["test_authority"],
        state_changes=[
            StateChange(
                entity="test_entity",
                operation="create",
                old_value=None,
                new_value={"name": "test"},
                metadata={"source": "test"}
            )
        ],
        intent=Intent(
            action="process",
            target="test_entity",
            parameters={}
        ),
        constraints=Constraints(
            required_authority=1,
            immutable_fields=[],
            validation_rules=[]
        ),
        metadata={"test": True}
    )

    # Evaluate the packet
    decision = governance.evaluate_packet(packet)

    # Check that we got a decision
    assert decision is not None
    assert hasattr(decision, 'decision')
    assert decision.decision in [DecisionType.APPROVE, DecisionType.REJECT, DecisionType.ESCALATE]

    print("✓ Governance engine smoke test passed")
    print(f"Decision: {decision.decision}")
    print(f"Reason: {decision.reason}")


if __name__ == "__main__":
    test_governance_engine()