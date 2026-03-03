"""
qpc_kernel.py

Quantum Python Chip (QPC)
- Quantum: branches, superposition, collapse, measurement, lineage
- Fluidic: flow, pressure, viscosity, turbulence, damping
- Constitutional: invariants, permissions, identity, surfaces

This is a core kernel skeleton: no business logic, no app glue.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable, Tuple
import uuid
import time


# =========================
# Enums & basic definitions
# =========================

class BranchState(Enum):
    OPEN = auto()
    COLLAPSED = auto()
    MERGED = auto()


class EventType(Enum):
    BRANCH_SPAWNED = auto()
    BRANCH_COLLAPSED = auto()
    SUPERPOSITION_CREATED = auto()
    MEASUREMENT_COMMITTED = auto()
    SURFACE_REGISTERED = auto()
    SURFACE_ACTION_REQUESTED = auto()
    INVARIANT_VIOLATION = auto()


class RiskMode(Enum):
    STRICT = auto()
    NORMAL = auto()
    EXPLORATORY = auto()


# =========================
# Core quantum primitives
# =========================

@dataclass
class Branch:
    branch_id: str
    parent_branch_id: Optional[str]
    hypothesis: str
    assumptions: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    state: BranchState = BranchState.OPEN
    invariants: List[str] = field(default_factory=list)
    # Fluidic properties
    flow_rate: float = 1.0      # how much attention/compute it gets
    pressure: float = 1.0       # urgency/demand
    viscosity: float = 1.0      # resistance to change/fork
    turbulence: float = 0.0     # allowed chaos/exploration

    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Superposition:
    superposition_id: str
    question: str
    branches: List[Branch] = field(default_factory=list)
    # Fluidic aggregate properties
    total_flow: float = 0.0
    turbulence_level: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeasurementEvent:
    measurement_id: str
    superposition_id: str
    winning_branch_id: str
    losing_branch_ids: List[str]
    strategy: str
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


# =========================
# Constitutional layer
# =========================

@dataclass
class AgentProfile:
    agent_id: str
    name: str
    constitution_rules: List[str] = field(default_factory=list)
    permissions: Dict[str, Any] = field(default_factory=dict)
    risk_mode: RiskMode = RiskMode.NORMAL
    invariants: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SurfaceDescriptor:
    surface_id: str
    surface_type: str  # e.g. "telephony", "browser", "cli", "ui", "api"
    capabilities: List[str]
    latency_profile: str = "normal"
    reliability_profile: str = "normal"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KernelEvent:
    event_type: EventType
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


# =========================
# QPC Kernel
# =========================

class QPCKernel:
    """
    Quantum + Fluidic + Constitutional kernel.
    Everything (agents, tools, surfaces) must go through this.
    """

    def __init__(self):
        self._branches: Dict[str, Branch] = {}
        self._superpositions: Dict[str, Superposition] = {}
        self._measurements: Dict[str, MeasurementEvent] = {}
        self._agents: Dict[str, AgentProfile] = {}
        self._surfaces: Dict[str, SurfaceDescriptor] = {}
        self._event_log: List[KernelEvent] = []

        # Policy hooks (can be replaced/extended)
        self.measurement_strategy: Callable[[Superposition], Branch] = (
            self._default_measurement_strategy
        )
        self.flow_regulator: Callable[[Branch], None] = self._default_flow_regulator

    # -------------
    # Event handling
    # -------------

    def _emit_event(self, event_type: EventType, payload: Dict[str, Any]) -> None:
        event = KernelEvent(event_type=event_type, payload=payload)
        self._event_log.append(event)

    @property
    def events(self) -> List[KernelEvent]:
        return list(self._event_log)

    # -------------
    # Agent & surface registration
    # -------------

    def register_agent(self, profile: AgentProfile) -> None:
        self._agents[profile.agent_id] = profile

    def register_surface(self, descriptor: SurfaceDescriptor) -> None:
        self._surfaces[descriptor.surface_id] = descriptor
        self._emit_event(
            EventType.SURFACE_REGISTERED,
            {"surface_id": descriptor.surface_id, "type": descriptor.surface_type},
        )

    # -------------
    # Quantum syscalls
    # -------------

    def spawn_branch(
        self,
        hypothesis: str,
        assumptions: Optional[Dict[str, Any]] = None,
        parent_branch_id: Optional[str] = None,
        invariants: Optional[List[str]] = None,
        score: float = 0.0,
        flow_rate: float = 1.0,
        pressure: float = 1.0,
        viscosity: float = 1.0,
        turbulence: float = 0.0,
    ) -> Branch:
        branch_id = str(uuid.uuid4())
        branch = Branch(
            branch_id=branch_id,
            parent_branch_id=parent_branch_id,
            hypothesis=hypothesis,
            assumptions=assumptions or {},
            invariants=invariants or [],
            score=score,
            flow_rate=flow_rate,
            pressure=pressure,
            viscosity=viscosity,
            turbulence=turbulence,
        )
        self._branches[branch_id] = branch
        self._emit_event(
            EventType.BRANCH_SPAWNED,
            {"branch_id": branch_id, "parent_branch_id": parent_branch_id},
        )
        return branch

    def create_superposition(
        self,
        question: str,
        branches: Optional[List[Branch]] = None,
        turbulence_level: float = 0.0,
    ) -> Superposition:
        superposition_id = str(uuid.uuid4())
        sp = Superposition(
            superposition_id=superposition_id,
            question=question,
            branches=branches or [],
            turbulence_level=turbulence_level,
        )
        sp.total_flow = sum(b.flow_rate for b in sp.branches)
        self._superpositions[superposition_id] = sp
        self._emit_event(
            EventType.SUPERPOSITION_CREATED,
            {"superposition_id": superposition_id, "question": question},
        )
        return sp

    def collapse_branch(self, branch_id: str, reason: str) -> None:
        branch = self._branches.get(branch_id)
        if not branch or branch.state != BranchState.OPEN:
            return
        branch.state = BranchState.COLLAPSED
        self._emit_event(
            EventType.BRANCH_COLLAPSED,
            {"branch_id": branch_id, "reason": reason},
        )

    def measure_superposition(
        self,
        superposition_id: str,
        strategy_name: str = "default",
    ) -> Optional[MeasurementEvent]:
        sp = self._superpositions.get(superposition_id)
        if not sp or not sp.branches:
            return None

        winning_branch = self.measurement_strategy(sp)
        losing = [b for b in sp.branches if b.branch_id != winning_branch.branch_id]

        for lb in losing:
            self.collapse_branch(lb.branch_id, reason="measurement_loss")

        measurement_id = str(uuid.uuid4())
        event = MeasurementEvent(
            measurement_id=measurement_id,
            superposition_id=superposition_id,
            winning_branch_id=winning_branch.branch_id,
            losing_branch_ids=[b.branch_id for b in losing],
            strategy=strategy_name,
        )
        self._measurements[measurement_id] = event
        self._emit_event(
            EventType.MEASUREMENT_COMMITTED,
            {
                "measurement_id": measurement_id,
                "superposition_id": superposition_id,
                "winning_branch_id": winning_branch.branch_id,
            },
        )
        return event

    # -------------
    # Invariants & constitutional checks
    # -------------

    def assert_invariant(self, branch_id: str, invariant: str) -> bool:
        branch = self._branches.get(branch_id)
        if not branch:
            return False
        # Placeholder: real logic would evaluate invariant expression
        ok = True
        if not ok:
            self._emit_event(
                EventType.INVARIANT_VIOLATION,
                {"branch_id": branch_id, "invariant": invariant},
            )
            self.collapse_branch(branch_id, reason="invariant_violation")
        return ok

    # -------------
    # Fluidic regulation
    # -------------

    def _default_flow_regulator(self, branch: Branch) -> None:
        """
        Simple placeholder:
        - If pressure is high, increase flow_rate.
        - If turbulence is high, cap flow_rate to avoid chaos.
        """
        base = branch.flow_rate
        base *= branch.pressure
        if branch.turbulence > 1.0:
            base *= 0.5
        branch.flow_rate = max(0.1, min(base, 10.0))

    def regulate_flows(self) -> None:
        for branch in self._branches.values():
            if branch.state == BranchState.OPEN:
                self.flow_regulator(branch)

    # -------------
    # Measurement strategy
    # -------------

    def _default_measurement_strategy(self, sp: Superposition) -> Branch:
        """
        Default: pick the highest score; tie-breaker = earliest created.
        """
        return sorted(
            sp.branches,
            key=lambda b: (-b.score, b.created_at),
        )[0]

    # -------------
    # Introspection
    # -------------

    def get_branch(self, branch_id: str) -> Optional[Branch]:
        return self._branches.get(branch_id)

    def get_superposition(self, superposition_id: str) -> Optional[Superposition]:
        return self._superpositions.get(superposition_id)

    def get_measurement(self, measurement_id: str) -> Optional[MeasurementEvent]:
        return self._measurements.get(measurement_id)

    def snapshot_state(self) -> Dict[str, Any]:
        return {
            "branches": list(self._branches.keys()),
            "superpositions": list(self._superpositions.keys()),
            "measurements": list(self._measurements.keys()),
            "agents": list(self._agents.keys()),
            "surfaces": list(self._surfaces.keys()),
            "events_count": len(self._event_log),
        }


# =========================
# Minimal “ready to install” usage example
# =========================

if __name__ == "__main__":
    kernel = QPCKernel()

    # Example agent & surface registration
    agent = AgentProfile(agent_id="alan", name="Alan")
    kernel.register_agent(agent)

    surface = SurfaceDescriptor(
        surface_id="twilio_voice",
        surface_type="telephony",
        capabilities=["send_audio", "receive_audio", "dtmf"],
    )
    kernel.register_surface(surface)

    # Quantum + fluidic demo
    b1 = kernel.spawn_branch(
        hypothesis="Option A",
        score=0.7,
        flow_rate=1.0,
        pressure=1.5,
        turbulence=0.3,
    )
    b2 = kernel.spawn_branch(
        hypothesis="Option B",
        score=0.9,
        flow_rate=1.0,
        pressure=1.0,
        turbulence=0.2,
    )

    sp = kernel.create_superposition(
        question="Choose best option",
        branches=[b1, b2],
        turbulence_level=0.3,
    )

    kernel.regulate_flows()
    measurement = kernel.measure_superposition(sp.superposition_id)

    print("Snapshot:", kernel.snapshot_state())
    print("Measurement:", measurement)
