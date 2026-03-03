"""
AQI recurring governance (effective starting 2025-12-17 and onward).
- Business start (default): 08:30 local time.
- Default end of business: 18:00 local time (full-day window by default).
- Duration derived from start->end unless a duration override is supplied.
- One active cycle at a time; one cycle per day (lock keyed by date).
- Use `evaluate_governance()` before starting; `mark_complete()` when done.
- Today (2025-12-16) remains governed by aqi_governance_today.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from pathlib import Path
import json
from typing import Any, Dict, Optional, Tuple

DEFAULT_START = time(8, 30)
DEFAULT_END = time(18, 0)
DEFAULT_DURATION = timedelta(hours=2)  # Used if end_time is not provided.
LOCK_DIR = Path("runtime")


@dataclass
class GovernanceDecision:
    allowed: bool
    action: str
    reason: str
    window_start: datetime
    window_end: datetime
    now: datetime


def _lock_path(day: date) -> Path:
    return LOCK_DIR / f"governance_{day.isoformat()}.lock"


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


def evaluate_governance(
    now: Optional[datetime] = None,
    start_time: time = DEFAULT_START,
    end_time: Optional[time] = DEFAULT_END,
    duration: Optional[timedelta] = None,
    prearranged_calls: bool = True,
) -> GovernanceDecision:
    """Evaluate whether a new cycle may start for the current day (>=2025-12-17)."""
    current = now or datetime.now()
    today = current.date()

    # Recurring governance begins 2025-12-17.
    if today <= date(2025, 12, 16):
        window_start = datetime.combine(today, start_time)
        use_duration = duration or DEFAULT_DURATION
        window_end = window_start + use_duration
        return GovernanceDecision(
            allowed=False,
            action="defer_to_one_day_rule",
            reason="Recurring governance starts 2025-12-17; use aqi_governance_today.py for 2025-12-16.",
            window_start=window_start,
            window_end=window_end,
            now=current,
        )

    window_start = datetime.combine(today, start_time)
    if end_time:
        window_end = datetime.combine(today, end_time)
        if window_end <= window_start:
            window_end = window_start + timedelta(hours=2)
    else:
        use_duration = duration or DEFAULT_DURATION
        window_end = window_start + use_duration
    lock_path = _lock_path(today)

    if not prearranged_calls:
        return GovernanceDecision(
            allowed=False,
            action="deny_calls",
            reason="Merchant Services calls require pre-arrangement before start.",
            window_start=window_start,
            window_end=window_end,
            now=current,
        )

    if current < window_start:
        return GovernanceDecision(
            allowed=False,
            action="queue",
            reason="Before business start; queue until window opens.",
            window_start=window_start,
            window_end=window_end,
            now=current,
        )

    active_lock = _read_lock(lock_path)
    if active_lock:
        lock_start, lock_end = active_lock
        if current < lock_end:
            return GovernanceDecision(
                allowed=False,
                action="deny_active",
                reason=f"Cycle already active until {lock_end.isoformat()} for this day.",
                window_start=lock_start,
                window_end=lock_end,
                now=current,
            )
        # Cycle expired; clear lock for a fresh run (still same day).
        _clear_lock(lock_path)

    # Grant new cycle.
    cycle_start = max(current, window_start)
    cycle_end = window_end
    _write_lock(lock_path, cycle_start, cycle_end)
    return GovernanceDecision(
        allowed=True,
        action="start_cycle",
        reason="Cycle granted: run A→Z now for configured duration, then report once.",
        window_start=cycle_start,
        window_end=cycle_end,
        now=current,
    )


def mark_complete(day: Optional[date] = None) -> None:
    """Mark the day’s governance cycle complete (clears the dated lock)."""
    target_day = day or date.today()
    path = _lock_path(target_day)
    _clear_lock(path)


__all__ = ["evaluate_governance", "mark_complete", "GovernanceDecision"]
