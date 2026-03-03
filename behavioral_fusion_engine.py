from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any
import time


class BehavioralHealth(Enum):
    OPTIMAL = "optimal"
    STABLE = "stable"
    FRAGILE = "fragile"
    FAILED = "failed"


class BehavioralMode(Enum):
    NORMAL = "normal"
    HIGH_FRICTION = "high_friction"
    STALLED = "stalled"
    RECOVERING = "recovering"
    COLLAPSED = "collapsed"


@dataclass
class BehavioralSnapshot:
    timestamp_ms: int
    fluidic_state: str
    mode: BehavioralMode
    health: BehavioralHealth
    trajectory_velocity: float
    trajectory_drift: float
    emotional_viscosity: float
    objection_count: int
    objections_resolved: int
    turn_count: int
    perception_mode: str
    perception_health: str
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        d["health"] = self.health.value
        return d


class BehavioralFusionEngine:
    """
    Fuses Fluidic Kernel state, Continuum Engine metrics, objection physics,
    and Perception Fusion state into a single behavioral state vector.
    """

    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        self._last_snapshot: Optional[BehavioralSnapshot] = None

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def fuse(
        self,
        *,
        fluidic_state: str,
        trajectory_velocity: float,
        trajectory_drift: float,
        emotional_viscosity: float,
        objection_count: int,
        objections_resolved: int,
        turn_count: int,
        perception_mode: str,
        perception_health: str,
    ) -> BehavioralSnapshot:
        mode = self._infer_mode(
            fluidic_state=fluidic_state,
            trajectory_velocity=trajectory_velocity,
            trajectory_drift=trajectory_drift,
            emotional_viscosity=emotional_viscosity,
            objection_count=objection_count,
            turn_count=turn_count,
        )
        health = self._infer_health(
            mode=mode,
            trajectory_velocity=trajectory_velocity,
            trajectory_drift=trajectory_drift,
            emotional_viscosity=emotional_viscosity,
            perception_health=perception_health,
        )

        snapshot = BehavioralSnapshot(
            timestamp_ms=self._now_ms(),
            fluidic_state=fluidic_state,
            mode=mode,
            health=health,
            trajectory_velocity=trajectory_velocity,
            trajectory_drift=trajectory_drift,
            emotional_viscosity=emotional_viscosity,
            objection_count=objection_count,
            objections_resolved=objections_resolved,
            turn_count=turn_count,
            perception_mode=perception_mode,
            perception_health=perception_health,
            notes=None,
        )
        self._last_snapshot = snapshot
        return snapshot

    def _infer_mode(
        self,
        *,
        fluidic_state: str,
        trajectory_velocity: float,
        trajectory_drift: float,
        emotional_viscosity: float,
        objection_count: int,
        turn_count: int,
    ) -> BehavioralMode:
        # Stalled: low velocity, high turns
        if (
            trajectory_velocity <= self.cfg.get("stall_velocity_threshold", 0.05)
            and turn_count >= self.cfg.get("stall_turn_threshold", 8)
        ):
            return BehavioralMode.STALLED

        # High friction: high viscosity or many objections
        if (
            emotional_viscosity >= self.cfg.get("high_viscosity_threshold", 1.4)
            or objection_count >= self.cfg.get("high_objection_threshold", 3)
        ):
            return BehavioralMode.HIGH_FRICTION

        # Collapsed: NEGOTIATION or CLOSING with negative drift
        if fluidic_state in ("NEGOTIATION", "CLOSING") and trajectory_drift <= self.cfg.get("collapse_drift_threshold", -0.6):
            return BehavioralMode.COLLAPSED

        # Recovering: positive velocity after stall/friction conditions
        # NOTE: Without state history, we treat high velocity as 'NORMAL' unless we were previously flagged.
        # However, for this stateless implementation, let's reserve RECOVERING for cases 
        # where we might want to flag a surge. 
        # But per the spec "positive velocity after stall", we can't know "after stall" here easily without history.
        # Implementation decision: If just high velocity, it's NORMAL (and Health will be OPTIMAL).
        # We only return RECOVERING if we explicitly track previous state (which we do in self._last_snapshot).
        
        if (
            self._last_snapshot 
            and self._last_snapshot.mode in (BehavioralMode.STALLED, BehavioralMode.HIGH_FRICTION)
            and trajectory_velocity >= self.cfg.get("recovery_velocity_threshold", 0.25)
        ):
            return BehavioralMode.RECOVERING

        return BehavioralMode.NORMAL

    def _infer_health(
        self,
        *,
        mode: BehavioralMode,
        trajectory_velocity: float,
        trajectory_drift: float,
        emotional_viscosity: float,
        perception_health: str,
    ) -> BehavioralHealth:
        # Hard failure
        if mode == BehavioralMode.COLLAPSED:
            return BehavioralHealth.FAILED

        # Fragile if perception is degraded/critical or drift is high
        if perception_health in ("degraded", "critical"):
            return BehavioralHealth.FRAGILE

        if abs(trajectory_drift) >= self.cfg.get("high_drift_threshold", 0.7):
            return BehavioralHealth.FRAGILE

        if emotional_viscosity >= self.cfg.get("high_viscosity_threshold", 1.4):
            return BehavioralHealth.FRAGILE

        # Optimal if velocity is strong and drift is low
        if (
            trajectory_velocity >= self.cfg.get("optimal_velocity_threshold", 0.4)
            and abs(trajectory_drift) <= self.cfg.get("low_drift_threshold", 0.2)
        ):
            return BehavioralHealth.OPTIMAL

        return BehavioralHealth.STABLE

    def last_snapshot(self) -> Optional[BehavioralSnapshot]:
        return self._last_snapshot
