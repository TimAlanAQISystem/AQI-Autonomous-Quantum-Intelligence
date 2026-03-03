"""Integration test for the governed AQI pipeline."""

import sys
import os
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from talk.pipeline_hooks.inventory import talk_from_inventory_result
from talk.interpreter.interpreter import TalkInterpreter
from aqi_delta import DeltaEngine
from aqi_governance import GovernanceEngine, DecisionType


def test_integration():
    """Test the TALK -> Delta -> Governance integration."""

    # Mock inventory records
    mock_records = [
        type('MockRecord', (), {
            'file_path': '/test/file1.py',
            'size': 100,
            'hash': 'abc123'
        })(),
        type('MockRecord', (), {
            'file_path': '/test/file2.py',
            'size': 200,
            'hash': 'def456'
        })()
    ]

    # Create TalkPacket from inventory result
    packet = talk_from_inventory_result(mock_records)
    print(f"✓ Created TalkPacket: {packet.id}")

    # Initialize engines
    interpreter = TalkInterpreter()
    delta_engine = DeltaEngine()
    governance_engine = GovernanceEngine(interpreter)

    # Process through engines
    from aqi_indexer.orchestrator.run_all import process_through_engines

    final_packet, delta, decision = process_through_engines(
        packet,
        interpreter=interpreter,
        delta_engine=delta_engine,
        governance_engine=governance_engine,
    )

    print(f"✓ Processed through engines:")
    print(f"  - Final packet: {final_packet is not None}")
    print(f"  - Delta: {delta}")
    print(f"  - Decision: {decision.decision}")

    # Verify decision is valid
    assert decision.decision in [DecisionType.APPROVE, DecisionType.REJECT, DecisionType.ESCALATE, DecisionType.MODIFY]
    assert final_packet is not None or decision.decision == DecisionType.REJECT

    print("✓ Integration test passed!")


if __name__ == "__main__":
    test_integration()