"""
AQI governance guard for one-day enforcement (2025-12-16 only).
- Earliest start: 09:25 local time on 2025-12-16.
- Duration: 2 hours from the moment the cycle is granted.
- Single active cycle at a time; additional triggers are denied/queued.
- Use `evaluate_governance()` before starting a cycle; call `mark_complete()` when done.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from pathlib import Path
import json
from typing import Any, Dict, Optional, Tuple

WINDOW_DATE = date(2025, 12, 16)
EARLIEST_START = time(9, 25)
CYCLE_DURATION = timedelta(hours=2)
LOCK_PATH = Path("runtime/governance_2025-12-16.lock")


@dataclass
class GovernanceDecision:
    allowed: bool
    action: str
    reason: str
    window_start: datetime
    window_end: datetime
    now: datetime


def _ensure_runtime_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_lock(path: Path) -> Optional[Tuple[datetime, datetime]]:
    if not path.exists():
        return None
    try:
        data: Dict[str, Any] = json.loads(path.read_text())
        start = datetime.fromisoformat(data.get("start"))
        end = datetime.fromisoformat(data.get("end"))
        return start, end
    except Exception:
        return None


def _write_lock(path: Path, start: datetime, end: datetime) -> None:
    _ensure_runtime_dir(path)
    payload = {"start": start.isoformat(), "end": end.isoformat()}
    path.write_text(json.dumps(payload))


def _clear_lock(path: Path) -> None:
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass


def evaluate_governance(now: Optional[datetime] = None) -> GovernanceDecision:
    """Evaluate whether a new cycle may start under today's governance rules."""
    current = now or datetime.now()

    window_start = datetime.combine(WINDOW_DATE, EARLIEST_START)

    # Expiry: governance applies only on WINDOW_DATE.
    if current.date() != WINDOW_DATE:
        window_end = window_start + CYCLE_DURATION
        return GovernanceDecision(
            allowed=False,
            action="expired",
            reason="Governance applies only on 2025-12-16 (local).",
            window_start=window_start,
            window_end=window_end,
            now=current,
        )

    # Not yet time: queue until earliest start.
    if current < window_start:
        window_end = window_start + CYCLE_DURATION
        return GovernanceDecision(
            allowed=False,
            action="queue",
            reason="Before earliest start (09:25). Queue until window opens.",
            window_start=window_start,
            window_end=window_end,
            now=current,
        )

    # Handle lock state.
    active_lock = _read_lock(LOCK_PATH)
    if active_lock:
        lock_start, lock_end = active_lock
        if current < lock_end:
            return GovernanceDecision(
                allowed=False,
                action="deny_active",
                reason=f"Cycle already active until {lock_end.isoformat()}",
                window_start=lock_start,
                window_end=lock_end,
                now=current,
            )
        # Expired lock: clear it and allow a fresh start (still same day).
        _clear_lock(LOCK_PATH)

    # Grant new cycle: 2 hours from now.
    cycle_start = current
    cycle_end = current + CYCLE_DURATION
    _write_lock(LOCK_PATH, cycle_start, cycle_end)
    return GovernanceDecision(
        allowed=True,
        action="start_cycle",
        reason="Cycle granted: run A→Z now for 2 hours, then report once.",
        window_start=cycle_start,
        window_end=cycle_end,
        now=current,
    )


def mark_complete() -> None:
    """Mark the governance cycle complete (clears the lock)."""
    _clear_lock(LOCK_PATH)


__all__ = ["evaluate_governance", "mark_complete", "GovernanceDecision"]
