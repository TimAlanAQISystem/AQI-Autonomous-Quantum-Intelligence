# fluid.py

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List
import math
import time
import uuid

from config import DMA_MAX_LIFETIME_SEC, MAX_ACTIVE_DMAS_BASE
from mengine import Context, Hardness
from containers import Container

from metrics import Metrics


@dataclass
class DMAConfig:
    name: str
    role: str
    allowed_fields: List[str]
    allowed_boundaries: List[str]
    max_lifetime_sec: float = DMA_MAX_LIFETIME_SEC


class DMAState(Enum):
    SPAWNED = auto()
    RUNNING = auto()
    COMPLETED = auto()
    TERMINATED = auto()
    ERROR = auto()


@dataclass
class SignalVector:
    dx: float
    dy: float

    def magnitude(self) -> float:
        return math.sqrt(self.dx ** 2 + self.dy ** 2)


@dataclass
class SignalField:
    """
    Discrete vector field: entity_id -> SignalVector.
    """
    vectors: Dict[str, SignalVector]

    def divergence(self) -> Dict[str, float]:
        return {eid: vec.dx + vec.dy for eid, vec in self.vectors.items()}

    def curl(self) -> Dict[str, float]:
        return {eid: vec.dx - vec.dy for eid, vec in self.vectors.items()}


@dataclass
class FluidSubstrate:
    """
    Represents the space DMAs operate in.
    Includes a real connector: local log file.
    """
    container: Container
    signal_field: SignalField
    state_space: Dict[str, Any] = field(default_factory=dict)

    def read_logs(self) -> List[str]:
        """
        Real connector: reads from a local log file path defined in container.resources.connectors["logs"].
        Boundary enforcement is handled by DMA.request_resource.
        """
        path = self.container.spec.resources.connectors.get("logs")
        if not path:
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().splitlines()
        except FileNotFoundError:
            print(f"[SUBSTRATE] Log file not found at {path}")
            return []


@dataclass
class DMA:
    dma_id: str
    config: DMAConfig
    context: Context
    created_at: float = field(default_factory=time.time)
    state: DMAState = DMAState.SPAWNED
    local_data: Dict[str, Any] = field(default_factory=dict)

    def expired(self) -> bool:
        return (time.time() - self.created_at) > self.config.max_lifetime_sec

    # ---------- Boundary-enforced resource access ----------
    def validate_access(self, substrate: FluidSubstrate, boundary_name: str) -> bool:
        """
        Ensure DMA has permission to access a boundary and the container allows it.
        """
        if boundary_name not in self.config.allowed_boundaries:
            print(f"[DMA:{self.config.name}] Boundary '{boundary_name}' not allowed for this DMA.")
            return False
        if boundary_name not in substrate.container.spec.boundaries:
            print(f"[DMA:{self.config.name}] Boundary '{boundary_name}' not provided by container.")
            return False
        mode = substrate.container.spec.boundaries[boundary_name]
        if mode not in ("read_only", "read_write"):
            print(f"[DMA:{self.config.name}] Boundary '{boundary_name}' has unsupported mode: {mode}")
            return False
        return True

    def request_logs(self, substrate: FluidSubstrate) -> List[str]:
        """
        Example of a real, boundary-enforced connector call.
        """
        if not self.validate_access(substrate, "logs"):
            self.state = DMAState.ERROR
            Metrics.record_error(substrate.container.spec.container_id, f"DMA {self.config.name} boundary access denied for logs")
            Metrics.record_dma_error()
            return []
        return substrate.read_logs()

    # -------------------------------------------------------

    def step(self, substrate: FluidSubstrate) -> None:
        """
        Minimal but real: inspect mass + divergence + curl and log a decision.
        Optionally read logs if allowed.
        """
        if self.state in {DMAState.COMPLETED, DMAState.TERMINATED, DMAState.ERROR}:
            return

        if self.expired():
            self.state = DMAState.TERMINATED
            print(f"[DMA:{self.config.name}] Expired.")
            Metrics.record_dma_terminate()
            return

        self.state = DMAState.RUNNING

        mass_map = self.context.mass_map
        div_map = substrate.signal_field.divergence()
        curl_map = substrate.signal_field.curl()

        target_id = None
        best_score = -1e9

        for eid, mass in mass_map.items():
            div = div_map.get(eid, 0.0)
            curl = curl_map.get(eid, 0.0)
            score = mass * 1.0 + div * 0.5 - abs(curl) * 0.2
            if score > best_score:
                best_score = score
                target_id = eid

        if target_id is not None:
            print(
                f"[DMA:{self.config.name}] "
                f"Target={target_id}, mass={mass_map[target_id]:.3f}, "
                f"div={div_map.get(target_id, 0):.3f}, "
                f"curl={curl_map.get(target_id, 0):.3f}, "
                f"score={best_score:.3f}"
            )
            self.local_data["target"] = target_id

            # Example: if this is a diagnostics DMA, try reading logs
            if "diagnostics" in self.config.role:
                logs = self.request_logs(substrate)
                if logs:
                    print(f"[DMA:{self.config.name}] Read {len(logs)} log lines.")
                    self.local_data["log_sample"] = logs[:3]
        else:
            print(f"[DMA:{self.config.name}] No meaningful target found.")

        self.state = DMAState.COMPLETED
        execution_time = time.time() - self.created_at
        Metrics.record_dma_complete(execution_time)


class MCI:
    """
    Micro Capability Interface: spawns, routes, dissolves DMAs.
    Uses a hardness-based budget to limit active DMAs.
    """

    def __init__(self, base_max_active_dmas: int = MAX_ACTIVE_DMAS_BASE) -> None:
        self.base_max_active_dmas = base_max_active_dmas
        self.active_dmas: Dict[str, DMA] = {}

    def _hardness_multiplier(self, hardness: Hardness) -> float:
        if hardness == Hardness.VAPOR:
            return 1.0
        if hardness == Hardness.TABLET:
            return 0.75
        if hardness == Hardness.TOOL:
            return 0.5
        if hardness == Hardness.STEEL:
            return 0.25
        return 1.0

    def max_active_for_hardness(self, hardness: Hardness) -> int:
        return max(1, int(self.base_max_active_dmas * self._hardness_multiplier(hardness)))

    def spawn_dma(self, config: DMAConfig, ctx: Context, hardness: Hardness) -> DMA:
        if len(self.active_dmas) >= self.max_active_for_hardness(hardness):
            print("[MCI] DMA limit reached for current hardness, cannot spawn.")
            raise RuntimeError("DMA limit reached")
        dma_id = str(uuid.uuid4())
        dma = DMA(dma_id=dma_id, config=config, context=ctx)
        self.active_dmas[dma_id] = dma
        print(f"[MCI] Spawned DMA: {config.name} ({dma_id})")
        Metrics.record_dma_spawn()
        return dma

    def step_all(self, substrate: FluidSubstrate) -> None:
        for dma_id, dma in list(self.active_dmas.items()):
            dma.step(substrate)
            if dma.state in {DMAState.COMPLETED, DMAState.TERMINATED, DMAState.ERROR} or dma.expired():
                print(f"[MCI] Retiring DMA: {dma.config.name} ({dma_id})")
                del self.active_dmas[dma_id]