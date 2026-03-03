"""Integration test for TALK -> Delta -> Governance flow."""

import sys
import os

# Add packages to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'aqi_delta'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'talk'))

from talk.schema import TalkPacket, StateChange, Intent, Constraints
from talk.utils import generate_id, get_timestamp
from aqi_delta import DeltaEngine
from aqi_governance import GovernanceEngine, DecisionType


def test_full_flow():
    """Test the complete TALK -> Delta -> Governance flow."""

    # Initialize engines
    delta_engine = DeltaEngine()
    governance_engine = GovernanceEngine()

    # Create initial packet
    packet1 = TalkPacket(
        id=generate_id(),
        timestamp=get_timestamp(),
        lineage=["system"],
        state_changes=[
            StateChange(
                entity="inventory",
                operation="create",
                old_value=None,
                new_value={"items": ["item1", "item2"]},
                metadata={"source": "extraction"}
            )
        ],
        intent=Intent(
            action="initialize",
            target="inventory",
            parameters={}
        ),
        constraints=Constraints(
            required_authority=1,
            immutable_fields=[],
            validation_rules=[]
        ),
        metadata={"phase": "inventory"}
    )

    # Process through delta engine
    delta_result = delta_engine.process_packet(packet1)
    print(f"✓ Delta computed: {len(delta_result.deltas)} deltas")

    # Create second packet (modification)
    packet2 = TalkPacket(
        id=generate_id(),
        timestamp=get_timestamp(),
        lineage=["system", "user"],
        state_changes=[
            StateChange(
                entity="inventory",
                operation="modify",
                old_value={"items": ["item1", "item2"]},
                new_value={"items": ["item1", "item2", "item3"]},
                metadata={"source": "user_input"}
            )
        ],
        intent=Intent(
            action="update",
            target="inventory",
            parameters={"add_item": "item3"}
        ),
        constraints=Constraints(
            required_authority=2,
            immutable_fields=[],
            validation_rules=[]
        ),
        metadata={"phase": "modification"}
    )

    # Process second packet through delta engine
    delta_result2 = delta_engine.process_packet(packet2)
    print(f"✓ Second delta computed: {len(delta_result2.deltas)} deltas")

    # Evaluate through governance engine
    decision = governance_engine.evaluate_packet(packet2)
    print(f"✓ Governance decision: {decision.decision}")
    print(f"Reason: {decision.reason}")

    # Verify decision is valid
    assert decision.decision in [DecisionType.APPROVE, DecisionType.REJECT, DecisionType.ESCALATE, DecisionType.MODIFY]
    assert decision.original_packet == packet2

    print("✓ Full TALK -> Delta -> Governance flow test passed")


if __name__ == "__main__":
    test_full_flow()