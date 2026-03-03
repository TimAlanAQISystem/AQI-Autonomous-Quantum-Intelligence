"""Core delta computation engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from talk.schema import TalkPacket
from .delta_packet import DeltaPacket, DeltaType
from .delta_storage import DeltaStorage
from talk.utils import generate_id, get_timestamp


class DeltaEngine:
    """
    Computes semantic deltas between TALK packets.

    This is the engine that makes AQI aware of change.
    """

    def __init__(self, storage: Optional[DeltaStorage] = None):
        self.storage = storage or DeltaStorage()
        self.previous_states: Dict[str, TalkPacket] = {}

    def process_packet(self, packet: TalkPacket) -> Optional[DeltaPacket]:
        """
        Process a new TalkPacket and compute delta if applicable.

        Returns the delta packet if a change was detected, None otherwise.
        """
        resource_key = f"{packet.state_change.resource_type}:{packet.state_change.resource_id}"
        previous_packet = self.previous_states.get(resource_key)

        if previous_packet is None:
            # First time seeing this resource
            delta = self._create_initial_delta(packet)
        else:
            # Compare with previous state
            delta = self._compute_delta(previous_packet, packet)

        if delta:
            self.storage.store_delta(delta)
            # Update previous state
            self.previous_states[resource_key] = packet

        return delta

    def _create_initial_delta(self, packet: TalkPacket) -> DeltaPacket:
        """Create delta for newly observed resource."""
        return DeltaPacket(
            id=generate_id(),
            delta_type=DeltaType.ADD,
            new_state=packet,
            affected_entities=[packet.state_change.resource_id],
            semantic_changes={
                "action": "resource_discovered",
                "resource_type": packet.state_change.resource_type,
                "initial_state": packet.state_change.operation
            },
            lineage=packet.lineage,
            timestamp=get_timestamp(),
        )

    def _compute_delta(self, previous: TalkPacket, current: TalkPacket) -> Optional[DeltaPacket]:
        """Compute delta between two packets."""
        if self._packets_equivalent(previous, current):
            return None  # No change

        delta_type = self._determine_delta_type(previous, current)
        semantic_changes = self._compute_semantic_changes(previous, current)

        return DeltaPacket(
            id=generate_id(),
            delta_type=delta_type,
            previous_state=previous,
            new_state=current,
            affected_entities=self._find_affected_entities(previous, current),
            semantic_changes=semantic_changes,
            lineage=current.lineage,
            timestamp=get_timestamp(),
        )

    def _packets_equivalent(self, p1: TalkPacket, p2: TalkPacket) -> bool:
        """Check if two packets represent equivalent states."""
        return (
            p1.state_change.resource_type == p2.state_change.resource_type and
            p1.state_change.resource_id == p2.state_change.resource_id and
            p1.state_change.operation == p2.state_change.operation and
            p1.state_change.payload == p2.state_change.payload and
            p1.intent == p2.intent
        )

    def _determine_delta_type(self, previous: TalkPacket, current: TalkPacket) -> DeltaType:
        """Determine the type of delta."""
        prev_op = previous.state_change.operation
        curr_op = current.state_change.operation

        if prev_op == "create" and curr_op == "delete":
            return DeltaType.REMOVE
        elif prev_op == "delete" and curr_op == "create":
            return DeltaType.ADD
        elif current.intent.value == "correct":
            return DeltaType.CORRECTION
        elif self._is_drift(previous, current):
            return DeltaType.DRIFT
        else:
            return DeltaType.MODIFY

    def _is_drift(self, previous: TalkPacket, current: TalkPacket) -> bool:
        """Detect if this represents unexpected drift."""
        # Simple heuristic: same resource, different intent unexpectedly
        return (
            previous.state_change.resource_type == current.state_change.resource_type and
            previous.intent != current.intent and
            current.intent.value not in ["correct", "sync"]
        )

    def _compute_semantic_changes(self, previous: TalkPacket, current: TalkPacket) -> Dict[str, Any]:
        """Compute semantic description of changes."""
        changes = {}

        # Operation change
        if previous.state_change.operation != current.state_change.operation:
            changes["operation_changed"] = {
                "from": previous.state_change.operation,
                "to": current.state_change.operation
            }

        # Payload changes
        payload_changes = self._diff_payloads(previous.state_change.payload, current.state_change.payload)
        if payload_changes:
            changes["payload_changes"] = payload_changes

        # Intent change
        if previous.intent != current.intent:
            changes["intent_changed"] = {
                "from": previous.intent.value,
                "to": current.intent.value
            }

        return changes

    def _diff_payloads(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """Compute differences between payloads."""
        changes = {}
        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            old_val = old.get(key)
            new_val = new.get(key)

            if old_val != new_val:
                changes[key] = {
                    "old": old_val,
                    "new": new_val
                }

        return changes

    def _find_affected_entities(self, previous: TalkPacket, current: TalkPacket) -> List[str]:
        """Find entities affected by this delta."""
        entities = [current.state_change.resource_id]

        # Add referenced entities from payload
        payload = current.state_change.payload
        if isinstance(payload, dict):
            for key, value in payload.items():
                if key in ["referenced_files", "affected_nodes", "related_entities"]:
                    if isinstance(value, list):
                        entities.extend(value)

        return list(set(entities))

    def get_deltas_for_resource(self, resource_type: str, resource_id: str) -> List[DeltaPacket]:
        """Get all deltas for a specific resource."""
        return self.storage.get_deltas_for_resource(resource_type, resource_id)

    def replay_to_timestamp(self, timestamp: str) -> Dict[str, TalkPacket]:
        """Replay deltas to reconstruct state at a specific timestamp."""
        return self.storage.replay_to_timestamp(timestamp)