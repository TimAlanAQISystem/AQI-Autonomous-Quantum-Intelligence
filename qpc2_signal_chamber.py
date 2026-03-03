"""
QPC-2 Signal Chamber (Upgraded)
Carbon-14-style temporal signal traces + QPC-2 epistemic stack alignment.

Core components:
- SignalTrace: temporal, decaying, lineage-aware, governed signal.
- EventTrace: promoted, persistent historical event.
- QPC2SignalChamber: sandboxed signal organ with governance and drift hooks.
- QPC2SignalInterface: IQcore-ready facade for ingestion/query/stabilization/audit.

Design goals:
- Time-embedded memory with Carbon-14 decay.
- Epistemic tagging (EC1–EC10) + confidence bands + source signatures.
- Drift surfacing (not overfitted, just enough for governance hooks).
- Participation roles to gate what influences reasoning.
- Temporal pressure at chamber level to keep the organ "alive."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import log2
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# EventTrace (persistent historical record)
# ---------------------------------------------------------------------------

@dataclass
class EventTrace:
    """
    A promoted, persistent historical event.

    Typically created from a stabilized, high-strength SignalTrace
    that the system wants to preserve beyond normal decay.
    """

    event_payload: Any
    lineage_token: str
    epistemic_class: str
    confidence_band: Optional[str]
    source_signature: Optional[str]
    event_birth: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lineage_token": self.lineage_token,
            "epistemic_class": self.epistemic_class,
            "confidence_band": self.confidence_band,
            "source_signature": self.source_signature,
            "event_birth": self.event_birth.isoformat(),
            "event_payload": self.event_payload,
        }


# ---------------------------------------------------------------------------
# SignalTrace (Carbon-14-style temporal signal)
# ---------------------------------------------------------------------------

@dataclass
class SignalTrace:
    """
    QPC-2 signal trace with Carbon-14-style temporal decay and epistemic tagging.

    Core fields:
    - signal_payload: content of the signal.
    - signal_birth: when the signal entered the chamber.
    - decay_constant: half-life controlling signal weakening.
    - lineage_token: relational identity for governance.
    - epistemic_class: EC1–EC10 / your epistemic layer label.
    - confidence_band: coarse band ("low", "medium", "high", etc.).
    - source_signature: origin marker ("user", "system", "external", etc.).
    - participation_role: "active", "observer", or "quarantined".

    Governance fields:
    - drift_score: simple scalar for drift surfacing (not overfitted).
    """

    signal_payload: Any
    decay_constant: timedelta
    signal_birth: datetime = field(default_factory=utc_now)
    lineage_token: Optional[str] = None

    epistemic_class: str = "EC-UNSPECIFIED"
    confidence_band: Optional[str] = None
    source_signature: Optional[str] = None
    participation_role: str = "active"  # "active" | "observer" | "quarantined"

    drift_score: float = 0.0

    _sealed_birth: datetime = field(init=False, repr=False)
    _initial_hash: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._sealed_birth = self.signal_birth
        self._initial_hash = self._compute_structural_hash()

    # ----- Core temporal logic ------------------------------------------------

    def _compute_structural_hash(self) -> int:
        return hash(
            (
                repr(self.signal_payload),
                self.signal_birth.isoformat(),
                self.lineage_token,
                self.epistemic_class,
                self.confidence_band,
                self.source_signature,
                self.participation_role,
            )
        )

    def age(self, now: Optional[datetime] = None) -> timedelta:
        now = now or utc_now()
        return now - self.signal_birth

    def age_in_half_lives(self, now: Optional[datetime] = None) -> float:
        hl_seconds = self.decay_constant.total_seconds()
        if hl_seconds <= 0:
            raise ValueError("decay_constant must be positive")
        return self.age(now).total_seconds() / hl_seconds

    def signal_strength(self, now: Optional[datetime] = None) -> float:
        """
        Canonical Carbon-14 decay:
            strength = 0.5 ** (age / decay_constant)
        """
        return 0.5 ** self.age_in_half_lives(now)

    # ----- Stabilization (reinforcement) -------------------------------------

    def stabilize(self, factor: float = 1.0, now: Optional[datetime] = None) -> None:
        """
        Adjust the decay_constant so the signal persists longer or shorter,
        while preserving its current strength at the time of stabilization.

        - factor > 1.0: slows decay (stronger persistence).
        - factor < 1.0: accelerates decay (weaker persistence).
        """
        if factor <= 0:
            raise ValueError("stabilization factor must be positive")

        now = now or utc_now()
        current_strength = self.signal_strength(now)

        if current_strength == 0:
            self.signal_birth = now
            self._sealed_birth = now
            self._initial_hash = self._compute_structural_hash()
            return

        age = self.age(now)
        age_seconds = age.total_seconds()

        if age_seconds <= 0:
            self.decay_constant = timedelta(seconds=self.decay_constant.total_seconds() * factor)
            return

        hl_seconds = -age_seconds / log2(current_strength)
        hl_seconds *= factor
        self.decay_constant = timedelta(seconds=hl_seconds)

    # ----- Integrity & drift --------------------------------------------------

    def is_temporally_consistent(self, tolerance: timedelta = timedelta(seconds=1)) -> bool:
        return abs(self.signal_birth - self._sealed_birth) <= tolerance

    def is_structurally_consistent(self) -> bool:
        return self._compute_structural_hash() == self._initial_hash

    def mark_drift(self, delta: float) -> None:
        self.drift_score += delta

    def epistemic_integrity(self) -> Dict[str, Any]:
        now = utc_now()
        return {
            "lineage_token": self.lineage_token,
            "signal_birth": self.signal_birth.isoformat(),
            "age_seconds": self.age(now).total_seconds(),
            "signal_strength": self.signal_strength(now),
            "epistemic_class": self.epistemic_class,
            "confidence_band": self.confidence_band,
            "source_signature": self.source_signature,
            "participation_role": self.participation_role,
            "drift_score": self.drift_score,
            "temporal_consistency": self.is_temporally_consistent(),
            "structural_consistency": self.is_structurally_consistent(),
        }

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (
            f"{cls}(payload={self.signal_payload!r}, "
            f"decay_constant={self.decay_constant}, "
            f"signal_birth={self.signal_birth.isoformat()}, "
            f"lineage_token={self.lineage_token!r}, "
            f"epistemic_class={self.epistemic_class!r}, "
            f"participation_role={self.participation_role!r})"
        )


# ---------------------------------------------------------------------------
# QPC-2 Signal Chamber
# ---------------------------------------------------------------------------

class QPC2SignalChamber:
    """
    QPC-2 sandbox chamber for temporal signal traces.

    Responsibilities:
    - Ingest signals as SignalTrace objects.
    - Rank by signal_strength with epistemic and participation filters.
    - Stabilize signals by lineage or top-N.
    - Shed exhausted signals.
    - Promote signals into EventTrace.
    - Track chamber-level temporal pressure.
    - Provide governance-grade integrity and audit reports.
    """

    def __init__(
        self,
        default_decay_constant: timedelta,
        max_signals: int = 1024,
        min_strength_threshold: float = 1e-3,
        chamber_id: Optional[str] = None,
        base_temporal_pressure: float = 1.0,
    ) -> None:

        if default_decay_constant.total_seconds() <= 0:
            raise ValueError("default_decay_constant must be positive")

        self.default_decay_constant = default_decay_constant
        self.max_signals = max_signals
        self.min_strength_threshold = min_strength_threshold
        self.chamber_id = chamber_id or "QPC2-SANDBOX"
        self.base_temporal_pressure = base_temporal_pressure

        self._signals: List[SignalTrace] = []
        self._events: List[EventTrace] = []
        self._next_lineage_seq: int = 1

    def _next_lineage_token(self) -> str:
        token = f"{self.chamber_id}::S{self._next_lineage_seq}"
        self._next_lineage_seq += 1
        return token

    def ingest_signal(
        self,
        payload: Any,
        *,
        decay_constant: Optional[timedelta] = None,
        lineage_token: Optional[str] = None,
        signal_birth: Optional[datetime] = None,
        epistemic_class: str = "EC-UNSPECIFIED",
        confidence_band: Optional[str] = None,
        source_signature: Optional[str] = None,
        participation_role: str = "active",
    ) -> SignalTrace:

        dc = decay_constant or self.default_decay_constant
        token = lineage_token or self._next_lineage_token()

        trace = SignalTrace(
            signal_payload=payload,
            decay_constant=dc,
            signal_birth=signal_birth or utc_now(),
            lineage_token=token,
            epistemic_class=epistemic_class,
            confidence_band=confidence_band,
            source_signature=source_signature,
            participation_role=participation_role,
        )

        self._signals.append(trace)
        self._enforce_capacity()
        return trace

    def _effective_strength(self, trace: SignalTrace, now: Optional[datetime] = None) -> float:
        now = now or utc_now()
        base = trace.signal_strength(now)
        pressure = self.base_temporal_pressure
        if base <= 0.0:
            return 0.0
        return base ** pressure

    def set_temporal_pressure(self, value: float) -> None:
        if value <= 0:
            raise ValueError("temporal pressure must be positive")
        self.base_temporal_pressure = value

    def _enforce_capacity(self) -> None:
        if len(self._signals) <= self.max_signals:
            return

        now = utc_now()
        self._signals.sort(key=lambda s: self._effective_strength(s, now), reverse=True)
        self._signals = self._signals[: self.max_signals]

    def shed_exhausted_signals(self) -> int:
        now = utc_now()
        before = len(self._signals)
        self._signals = [
            s for s in self._signals if self._effective_strength(s, now) >= self.min_strength_threshold
        ]
        return before - len(self._signals)

    def all_signals(self) -> List[SignalTrace]:
        return list(self._signals)

    def all_events(self) -> List[EventTrace]:
        return list(self._events)

    def rank_signals(
        self,
        *,
        limit: Optional[int] = None,
        predicate: Optional[Callable[[SignalTrace], bool]] = None,
        include_roles: Optional[List[str]] = None,
        epistemic_filter: Optional[List[str]] = None,
    ) -> List[SignalTrace]:

        now = utc_now()
        candidate: Iterable[SignalTrace] = self._signals

        if predicate is not None:
            candidate = filter(predicate, candidate)

        if include_roles is not None:
            roles = set(include_roles)
            candidate = filter(lambda s: s.participation_role in roles, candidate)

        if epistemic_filter is not None:
            ecs = set(epistemic_filter)
            candidate = filter(lambda s: s.epistemic_class in ecs, candidate)

        ranked = sorted(candidate, key=lambda s: self._effective_strength(s, now), reverse=True)
        if limit is not None:
            ranked = ranked[:limit]
        return ranked

    def find_by_lineage(self, lineage_token: str) -> Optional[SignalTrace]:
        for s in self._signals:
            if s.lineage_token == lineage_token:
                return s
        return None

    def stabilize_lineage(self, lineage_token: str, *, factor: float = 1.0) -> bool:
        trace = self.find_by_lineage(lineage_token)
        if trace is None:
            return False
        trace.stabilize(factor=factor)
        return True

    def stabilize_top_signals(
        self,
        *,
        count: int = 1,
        factor: float = 1.0,
        include_roles: Optional[List[str]] = None,
        epistemic_filter: Optional[List[str]] = None,
    ) -> List[SignalTrace]:

        top = self.rank_signals(
            limit=count,
            include_roles=include_roles,
            epistemic_filter=epistemic_filter,
        )
        for s in top:
            s.stabilize(factor=factor)
        return top

    def promote_to_event(self, trace: SignalTrace) -> EventTrace:
        event = EventTrace(
            event_payload=trace.signal_payload,
            lineage_token=trace.lineage_token or "<UNLINED>",
            epistemic_class=trace.epistemic_class,
            confidence_band=trace.confidence_band,
            source_signature=trace.source_signature,
            event_birth=utc_now(),
        )
        self._events.append(event)
        return event

    def promote_top_to_events(
        self,
        *,
        count: int = 1,
        include_roles: Optional[List[str]] = None,
        epistemic_filter: Optional[List[str]] = None,
    ) -> List[EventTrace]:

        top = self.rank_signals(
            limit=count,
            include_roles=include_roles,
            epistemic_filter=epistemic_filter,
        )
        promoted: List[EventTrace] = []
        for s in top:
            promoted.append(self.promote_to_event(s))
        return promoted

    def chamber_integrity(self) -> Dict[str, Any]:
        now = utc_now()
        strengths = [self._effective_strength(s, now) for s in self._signals]
        ages = [s.age(now).total_seconds() for s in self._signals]
        drifts = [s.drift_score for s in self._signals]

        def _avg(xs: List[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        return {
            "chamber_id": self.chamber_id,
            "total_signals": len(self._signals),
            "total_events": len(self._events),
            "avg_strength": _avg(strengths),
            "avg_age_seconds": _avg(ages),
            "avg_drift_score": _avg(drifts),
            "min_strength": min(strengths) if strengths else 0.0,
            "max_strength": max(strengths) if strengths else 0.0,
            "temporal_pressure": self.base_temporal_pressure,
        }

    def audit_signals(self) -> List[Dict[str, Any]]:
        return [s.epistemic_integrity() for s in self._signals]

    def reset_chamber(
        self,
        *,
        preserve_events: bool = True,
        preserve_high_value_signals: bool = True,
        strength_threshold: float = 0.5,
    ) -> None:
        now = utc_now()
        preserved: List[SignalTrace] = []

        if preserve_high_value_signals:
            for s in self._signals:
                if self._effective_strength(s, now) >= strength_threshold:
                    preserved.append(s)

        self._signals = preserved

        if not preserve_events:
            self._events.clear()

    def __repr__(self) -> str:
        return (
            f"QPC2SignalChamber(chamber_id={self.chamber_id!r}, "
            f"default_decay_constant={self.default_decay_constant}, "
            f"max_signals={self.max_signals}, "
            f"min_strength_threshold={self.min_strength_threshold}, "
            f"current_signals={len(self._signals)}, "
            f"current_events={len(self._events)}, "
            f"temporal_pressure={self.base_temporal_pressure})"
        )


# ---------------------------------------------------------------------------
# IQcore-ready facade
# ---------------------------------------------------------------------------

class QPC2SignalInterface:
    """
    Thin facade around QPC2SignalChamber for IQcore integration.

    Shape for adapters:
    - ingest()
    - query()
    - stabilize()
    - promote()
    - audit()
    """

    def __init__(self, chamber: QPC2SignalChamber) -> None:
        self.chamber = chamber

    def ingest(
        self,
        payload: Any,
        *,
        epistemic_class: str = "EC-UNSPECIFIED",
        confidence_band: Optional[str] = None,
        source_signature: Optional[str] = None,
        participation_role: str = "active",
    ) -> SignalTrace:
        return self.chamber.ingest_signal(
            payload,
            epistemic_class=epistemic_class,
            confidence_band=confidence_band,
            source_signature=source_signature,
            participation_role=participation_role,
        )

    def query_top(
        self,
        *,
        limit: int = 5,
        roles: Optional[List[str]] = None,
        epistemic_filter: Optional[List[str]] = None,
    ) -> List[SignalTrace]:
        return self.chamber.rank_signals(
            limit=limit,
            include_roles=roles,
            epistemic_filter=epistemic_filter,
        )

    def stabilize_lineage(self, lineage_token: str, *, factor: float = 1.0) -> bool:
        return self.chamber.stabilize_lineage(lineage_token, factor=factor)

    def stabilize_top(
        self,
        *,
        count: int = 1,
        factor: float = 1.0,
        roles: Optional[List[str]] = None,
        epistemic_filter: Optional[List[str]] = None,
    ) -> List[SignalTrace]:
        return self.chamber.stabilize_top_signals(
            count=count,
            factor=factor,
            include_roles=roles,
            epistemic_filter=epistemic_filter,
        )

    def promote_top_to_events(
        self,
        *,
        count: int = 1,
        roles: Optional[List[str]] = None,
        epistemic_filter: Optional[List[str]] = None,
    ) -> List[EventTrace]:
        return self.chamber.promote_top_to_events(
            count=count,
            include_roles=roles,
            epistemic_filter=epistemic_filter,
        )

    def audit(self) -> Dict[str, Any]:
        return {
            "chamber_integrity": self.chamber.chamber_integrity(),
            "signals": self.chamber.audit_signals(),
            "events": [e.to_dict() for e in self.chamber.all_events()],
        }


# ---------------------------------------------------------------------------
# Optional smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    chamber = QPC2SignalChamber(
        default_decay_constant=timedelta(hours=1),
        max_signals=10,
        min_strength_threshold=1e-4,
        chamber_id="QPC2-DEMO",
        base_temporal_pressure=1.0,
    )
    iface = QPC2SignalInterface(chamber)

    iface.ingest({"event": "system_boot"}, epistemic_class="EC1", source_signature="system")
    iface.ingest({"event": "user_login", "user": "alice"}, epistemic_class="EC3", source_signature="user")
    iface.ingest(
        {"event": "external_ping"},
        epistemic_class="EC5",
        source_signature="external",
        participation_role="observer",
    )

    print("Chamber:", chamber)
    print("Audit:", iface.audit())
    top = iface.query_top(limit=2)
    print("Top signals:", top)
