"""
QPC-2 sandbox module.
Carbon-14-style temporal memory plus a QPC-2 chamber wrapper.
Self-contained; standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import log2
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Carbon-14-style memory
# ---------------------------------------------------------------------------

@dataclass
class CarbonMemory:
    """Temporal memory with decay, reinforcement, and tamper checks."""

    content: Any
    half_life: timedelta
    created_at: datetime = field(default_factory=utc_now)
    lineage_id: Optional[str] = None

    _sealed_at: datetime = field(init=False, repr=False)
    _initial_hash: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._sealed_at = self.created_at
        self._initial_hash = self._compute_structural_hash()

    # ---- temporal logic -----------------------------------------------------
    def _compute_structural_hash(self) -> int:
        return hash((repr(self.content), self.created_at.isoformat(), self.lineage_id))

    def age(self, now: Optional[datetime] = None) -> timedelta:
        now = now or utc_now()
        return now - self.created_at

    def age_in_half_lives(self, now: Optional[datetime] = None) -> float:
        hl_seconds = self.half_life.total_seconds()
        if hl_seconds <= 0:
            raise ValueError("half_life must be positive")
        return self.age(now).total_seconds() / hl_seconds

    def decay_factor(self, now: Optional[datetime] = None) -> float:
        return 0.5 ** self.age_in_half_lives(now)

    def weight(self, now: Optional[datetime] = None) -> float:
        return self.decay_factor(now)

    # ---- reinforcement ------------------------------------------------------
    def reinforce(self, factor: float = 1.0, now: Optional[datetime] = None) -> None:
        if factor <= 0:
            raise ValueError("reinforcement factor must be positive")

        now = now or utc_now()
        current_weight = self.weight(now)

        if current_weight == 0:
            self.created_at = now
            self._sealed_at = self.created_at
            self._initial_hash = self._compute_structural_hash()
            return

        age_seconds = self.age(now).total_seconds()
        if age_seconds <= 0:
            self.half_life = timedelta(seconds=self.half_life.total_seconds() * factor)
            return

        hl_seconds = -age_seconds / log2(current_weight)
        hl_seconds *= factor
        self.half_life = timedelta(seconds=hl_seconds)

    # ---- integrity ----------------------------------------------------------
    def is_temporally_consistent(self, tolerance: timedelta = timedelta(seconds=1)) -> bool:
        delta = abs(self.created_at - self._sealed_at)
        return delta <= tolerance

    def is_structurally_consistent(self) -> bool:
        return self._compute_structural_hash() == self._initial_hash

    def integrity_status(self) -> Dict[str, Any]:
        now = utc_now()
        return {
            "lineage_id": self.lineage_id,
            "created_at": self.created_at.isoformat(),
            "age_seconds": self.age(now).total_seconds(),
            "weight": self.weight(now),
            "temporally_consistent": self.is_temporally_consistent(),
            "structurally_consistent": self.is_structurally_consistent(),
        }

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (
            f"{cls}(content={self.content!r}, "
            f"half_life={self.half_life}, "
            f"created_at={self.created_at.isoformat()}, "
            f"lineage_id={self.lineage_id!r})"
        )


# ---------------------------------------------------------------------------
# QPC-2 chamber
# ---------------------------------------------------------------------------

class QPC2Chamber:
    """Sandbox chamber that hosts CarbonMemory instances."""

    def __init__(
        self,
        default_half_life: timedelta,
        max_memories: int = 1024,
        min_weight_threshold: float = 1e-3,
        chamber_id: Optional[str] = None,
    ) -> None:
        if default_half_life.total_seconds() <= 0:
            raise ValueError("default_half_life must be positive")

        self.default_half_life = default_half_life
        self.max_memories = max_memories
        self.min_weight_threshold = min_weight_threshold
        self.chamber_id = chamber_id or "QPC2-SANDBOX"

        self._memories: List[CarbonMemory] = []
        self._next_lineage_seq: int = 1

    # ---- memory creation ----------------------------------------------------
    def _next_lineage_id(self) -> str:
        lid = f"{self.chamber_id}::M{self._next_lineage_seq}"
        self._next_lineage_seq += 1
        return lid

    def record(
        self,
        content: Any,
        *,
        half_life: Optional[timedelta] = None,
        lineage_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> CarbonMemory:
        hl = half_life or self.default_half_life
        lid = lineage_id or self._next_lineage_id()
        mem = CarbonMemory(
            content=content,
            half_life=hl,
            created_at=created_at or utc_now(),
            lineage_id=lid,
        )
        self._memories.append(mem)
        self._enforce_capacity()
        return mem

    # ---- capacity / pruning -------------------------------------------------
    def _enforce_capacity(self) -> None:
        if len(self._memories) <= self.max_memories:
            return
        now = utc_now()
        self._memories.sort(key=lambda m: m.weight(now), reverse=True)
        self._memories = self._memories[: self.max_memories]

    def prune_decayed(self) -> int:
        now = utc_now()
        before = len(self._memories)
        self._memories = [
            m for m in self._memories if m.weight(now) >= self.min_weight_threshold
        ]
        return before - len(self._memories)

    # ---- query / retrieval --------------------------------------------------
    def all_memories(self) -> Tuple[CarbonMemory, ...]:
        return tuple(self._memories)

    def ranked_memories(
        self,
        *,
        limit: Optional[int] = None,
        predicate: Optional[Callable[[CarbonMemory], bool]] = None,
    ) -> List[CarbonMemory]:
        now = utc_now()
        candidate: Iterable[CarbonMemory] = self._memories
        if predicate is not None:
            candidate = filter(predicate, candidate)

        ranked = sorted(candidate, key=lambda m: m.weight(now), reverse=True)
        if limit is not None:
            ranked = ranked[:limit]
        return ranked

    def find_by_lineage(self, lineage_id: str) -> Optional[CarbonMemory]:
        for m in self._memories:
            if m.lineage_id == lineage_id:
                return m
        return None

    # ---- reinforcement ------------------------------------------------------
    def reinforce_lineage(
        self,
        lineage_id: str,
        *,
        factor: float = 1.0,
    ) -> bool:
        mem = self.find_by_lineage(lineage_id)
        if mem is None:
            return False
        mem.reinforce(factor=factor)
        return True

    def reinforce_top(
        self,
        *,
        count: int = 1,
        factor: float = 1.0,
    ) -> List[CarbonMemory]:
        top = self.ranked_memories(limit=count)
        for m in top:
            m.reinforce(factor=factor)
        return top

    # ---- governance ---------------------------------------------------------
    def integrity_report(self) -> Dict[str, Any]:
        now = utc_now()
        weights = [m.weight(now) for m in self._memories]
        ages = [m.age(now).total_seconds() for m in self._memories]

        def _avg(xs: List[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        return {
            "chamber_id": self.chamber_id,
            "total_memories": len(self._memories),
            "avg_weight": _avg(weights),
            "avg_age_seconds": _avg(ages),
            "min_weight": min(weights) if weights else 0.0,
            "max_weight": max(weights) if weights else 0.0,
        }

    def audit_memories(self) -> List[Dict[str, Any]]:
        return [m.integrity_status() for m in self._memories]

    def __repr__(self) -> str:
        return (
            f"QPC2Chamber(chamber_id={self.chamber_id!r}, "
            f"default_half_life={self.default_half_life}, "
            f"max_memories={self.max_memories}, "
            f"min_weight_threshold={self.min_weight_threshold}, "
            f"current_memories={len(self._memories)})"
        )


# ---------------------------------------------------------------------------
# Example usage (for quick sandbox runs)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    chamber = QPC2Chamber(
        default_half_life=timedelta(hours=1),
        max_memories=5,
        min_weight_threshold=1e-4,
        chamber_id="QPC2-SANDBOX-DEMO",
    )

    chamber.record({"event": "system_started"})
    chamber.record({"event": "user_login", "user": "alice"})
    chamber.record({"event": "user_login", "user": "bob"})

    print("Chamber:", chamber)
    print("Integrity report:", chamber.integrity_report())
    print("Ranked memories:", chamber.ranked_memories())
    for status in chamber.audit_memories():
        print("Memory integrity:", status)
