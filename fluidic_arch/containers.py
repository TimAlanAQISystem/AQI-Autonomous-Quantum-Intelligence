# containers.py

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional
from config import MAX_PATTERNS_PER_CONTAINER

from metrics import Metrics


@dataclass
class ResourceOrgans:
    execution_substrate: Dict[str, Any]
    storage: Dict[str, Any]
    connectors: Dict[str, Any]
    security: Dict[str, Any]
    context_providers: Dict[str, Any]


@dataclass
class ContainerSpec:
    container_id: str
    purpose: str
    boundaries: Dict[str, Any]  # e.g., {"logs": "read_only"}
    resources: ResourceOrgans
    self_store: Dict[str, Any] = field(default_factory=dict)


class ContainerLifecycleState(Enum):
    CREATED = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    ARCHIVED = auto()
    DESTROYED = auto()


@dataclass
class Container:
    spec: ContainerSpec
    state: ContainerLifecycleState = ContainerLifecycleState.CREATED

    def activate(self) -> None:
        if self.state in {ContainerLifecycleState.CREATED,
                          ContainerLifecycleState.SUSPENDED}:
            self.state = ContainerLifecycleState.ACTIVE
            print(f"[CONTAINER] Activated: {self.spec.container_id}")
            Metrics.set_container_health(self.spec.container_id, "active")

    def suspend(self) -> None:
        if self.state == ContainerLifecycleState.ACTIVE:
            self.state = ContainerLifecycleState.SUSPENDED
            print(f"[CONTAINER] Suspended: {self.spec.container_id}")

    def archive(self) -> None:
        self.state = ContainerLifecycleState.ARCHIVED
        print(f"[CONTAINER] Archived: {self.spec.container_id}")

    def destroy(self) -> None:
        self.state = ContainerLifecycleState.DESTROYED
        print(f"[CONTAINER] Destroyed: {self.spec.container_id}")

    def _trim_patterns_if_needed(self) -> None:
        if len(self.spec.self_store) > MAX_PATTERNS_PER_CONTAINER:
            # Very simple LRU: drop first inserted key
            oldest_key = next(iter(self.spec.self_store.keys()))
            del self.spec.self_store[oldest_key]
            print(f"[CONTAINER] Evicted old pattern key: {oldest_key}")

    def store_form_pattern(self, intent: str, pattern: Dict[str, Any]) -> None:
        self.spec.self_store[intent] = pattern
        self._trim_patterns_if_needed()
        print(f"[CONTAINER] Stored form pattern for intent: {intent}")

    def load_form_pattern_for_intent(self, intent: str) -> Optional[Dict[str, Any]]:
        return self.spec.self_store.get(intent)