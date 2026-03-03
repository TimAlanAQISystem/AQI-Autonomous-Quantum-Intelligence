"""Delta storage and retrieval."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any
from .delta_packet import DeltaPacket


class DeltaStorage:
    """
    Stores and retrieves delta packets.

    Provides persistence and query capabilities for deltas.
    """

    def __init__(self, storage_dir: str = "aqi_deltas"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def store_delta(self, delta: DeltaPacket) -> None:
        """Store a delta packet."""
        filename = f"delta_{delta.id}.json"
        filepath = self.storage_dir / filename

        with filepath.open("w", encoding="utf-8") as f:
            json.dump(delta.to_dict(), f, indent=2, sort_keys=True)

    def get_delta(self, delta_id: str) -> Optional[DeltaPacket]:
        """Retrieve a specific delta."""
        filename = f"delta_{delta_id}.json"
        filepath = self.storage_dir / filename

        if not filepath.exists():
            return None

        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return DeltaPacket.from_dict(data)

    def get_deltas_for_resource(self, resource_type: str, resource_id: str) -> List[DeltaPacket]:
        """Get all deltas for a specific resource."""
        deltas = []
        resource_key = f"{resource_type}:{resource_id}"

        for filepath in self.storage_dir.glob("delta_*.json"):
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)
                delta = DeltaPacket.from_dict(data)

                # Check if this delta affects the resource
                if resource_key in [f"{delta.new_state.state_change.resource_type}:{delta.new_state.state_change.resource_id}"]:
                    deltas.append(delta)
                elif resource_id in delta.affected_entities:
                    deltas.append(delta)

        # Sort by timestamp
        deltas.sort(key=lambda d: d.timestamp)
        return deltas

    def get_all_deltas(self) -> List[DeltaPacket]:
        """Get all stored deltas."""
        deltas = []

        for filepath in self.storage_dir.glob("delta_*.json"):
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)
                deltas.append(DeltaPacket.from_dict(data))

        deltas.sort(key=lambda d: d.timestamp)
        return deltas

    def replay_to_timestamp(self, timestamp: str) -> Dict[str, TalkPacket]:
        """
        Replay deltas to reconstruct the state at a specific timestamp.

        Returns a dictionary of resource_key -> latest TalkPacket at that timestamp.
        """
        from talk.schema import TalkPacket

        state = {}
        deltas = self.get_all_deltas()

        for delta in deltas:
            if delta.timestamp > timestamp:
                break

            resource_key = f"{delta.new_state.state_change.resource_type}:{delta.new_state.state_change.resource_id}"
            state[resource_key] = delta.new_state

        return state

    def get_deltas_in_range(self, start_time: str, end_time: str) -> List[DeltaPacket]:
        """Get deltas within a time range."""
        deltas = self.get_all_deltas()
        return [
            d for d in deltas
            if start_time <= d.timestamp <= end_time
        ]