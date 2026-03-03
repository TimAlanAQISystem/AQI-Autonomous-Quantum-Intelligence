"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   IQcore ENFORCER — Cognitive Budget Enforcement              ║
║                                                                              ║
║  Provides a deterministic IQcore accounting system for the Agent X organism. ║
║  Every decorated function has an explicit cognitive cost.                     ║
║  Budget is enforced at runtime — exceeding the limit raises                  ║
║  IQcoreExceededError.                                                        ║
║                                                                              ║
║  Actors:                                                                     ║
║    Alan    — 60 IQcores — operator (real-time decisioning)                   ║
║    AgentX  — 40 IQcores — governor (constitutional enforcement)              ║
║                                                                              ║
║  Usage:                                                                      ║
║    @iqcore_cost("Alan", 3)                                                   ║
║    def choose_script(self, segment): ...                                     ║
║                                                                              ║
║  Author: Agent X / CW23                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import logging
import threading
from functools import wraps
from pathlib import Path

logger = logging.getLogger("IQCORE")

# ─── CHARTER LOADER ─────────────────────────────────────────────────────────

CHARTER_PATH = Path(__file__).parent / "IQCORE_CHARTER.json"


def _load_charter() -> dict:
    """Load the IQcore charter. Falls back to defaults if missing."""
    if CHARTER_PATH.exists():
        try:
            with open(CHARTER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[IQCORE] Failed to load charter: {e}")
    return {
        "actors": {
            "Alan": {"allocated_iqcores": 60},
            "AgentX": {"allocated_iqcores": 40},
        },
        "rules": {"min_alan_iqcores": 50, "max_agentx_iqcores": 50},
    }


_charter = _load_charter()


# ─── EXCEPTIONS ──────────────────────────────────────────────────────────────

class IQcoreExceededError(Exception):
    """Raised when an actor attempts to exceed IQcore budget."""

    def __init__(self, actor: str, cost: int, current: int, limit: int):
        self.actor = actor
        self.cost = cost
        self.current = current
        self.limit = limit
        super().__init__(
            f"{actor} exceeded IQcore budget: attempted cost {cost}, "
            f"current {current}/{limit}"
        )


# ─── LEDGER ──────────────────────────────────────────────────────────────────

class IQcoreLedger:
    """Thread-safe IQcore accounting ledger."""

    def __init__(self):
        self._lock = threading.Lock()
        self._current = {"alan": 0, "agentx": 0}
        self._limits = {
            "alan": _charter["actors"]["Alan"]["allocated_iqcores"],
            "agentx": _charter["actors"]["AgentX"]["allocated_iqcores"],
        }
        self._calls = {"alan": 0, "agentx": 0}  # total decorated calls

    @property
    def alan(self) -> int:
        return self._current["alan"]

    @alan.setter
    def alan(self, v: int):
        self._current["alan"] = v

    @property
    def agentx(self) -> int:
        return self._current["agentx"]

    @agentx.setter
    def agentx(self, v: int):
        self._current["agentx"] = v

    def limits(self, actor: str) -> int:
        return self._limits.get(actor.lower(), 0)

    def acquire(self, actor: str, cost: int) -> None:
        """Acquire IQcores for an actor. Raises if over budget."""
        key = actor.lower()
        with self._lock:
            current = self._current.get(key, 0)
            limit = self._limits.get(key, 0)
            if current + cost > limit:
                raise IQcoreExceededError(actor, cost, current, limit)
            self._current[key] = current + cost
            self._calls[key] = self._calls.get(key, 0) + 1

    def release(self, actor: str, cost: int) -> None:
        """Release IQcores after function completes."""
        key = actor.lower()
        with self._lock:
            self._current[key] = max(0, self._current.get(key, 0) - cost)

    def snapshot(self) -> dict:
        """Return a point-in-time snapshot of the ledger."""
        with self._lock:
            return {
                "Alan": {
                    "current": self._current["alan"],
                    "limit": self._limits["alan"],
                    "remaining": self._limits["alan"] - self._current["alan"],
                    "total_calls": self._calls.get("alan", 0),
                },
                "AgentX": {
                    "current": self._current["agentx"],
                    "limit": self._limits["agentx"],
                    "remaining": self._limits["agentx"] - self._current["agentx"],
                    "total_calls": self._calls.get("agentx", 0),
                },
            }

    def reset(self, actor: str = None) -> None:
        """Reset IQcore counters. If actor is None, reset all."""
        with self._lock:
            if actor:
                key = actor.lower()
                self._current[key] = 0
                self._calls[key] = 0
            else:
                for k in self._current:
                    self._current[k] = 0
                    self._calls[k] = 0


# Global singleton
IQCORES = IQcoreLedger()


# ─── DASHBOARD INTEGRATION ──────────────────────────────────────────────────

def _try_log_burn(actor: str, cost: int, func_name: str):
    """Best-effort dashboard logging. Never throws."""
    try:
        from iqcore_dashboard import log_burn
        log_burn(actor, cost, func_name)
    except Exception:
        pass  # Dashboard is optional


# ─── DECORATOR ───────────────────────────────────────────────────────────────

def iqcore_cost(actor: str, cost: int):
    """
    Decorator that enforces IQcore budget for a function.

    Usage:
        @iqcore_cost("Alan", 3)
        def choose_script(self, segment): ...

    The decorated function:
    1. Checks if the actor has enough remaining IQcores
    2. Acquires `cost` IQcores (raises IQcoreExceededError if over budget)
    3. Runs the function
    4. Releases `cost` IQcores (even if the function throws)
    5. Logs burn to dashboard (best-effort)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            IQCORES.acquire(actor, cost)
            _try_log_burn(actor, cost, func.__name__)
            try:
                return func(*args, **kwargs)
            finally:
                IQCORES.release(actor, cost)

        # Preserve metadata for introspection
        wrapper._iqcore_actor = actor
        wrapper._iqcore_cost = cost
        return wrapper

    return decorator


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  IQcore ENFORCER — Status")
    print("=" * 60)

    charter = _load_charter()
    alan_iq = charter["actors"]["Alan"]["allocated_iqcores"]
    agentx_iq = charter["actors"]["AgentX"]["allocated_iqcores"]
    total = alan_iq + agentx_iq

    print(f"  Charter:   {CHARTER_PATH}")
    print(f"  Total:     {total} IQcores")
    print(f"  Alan:      {alan_iq} IQcores (operator)")
    print(f"  Agent X:   {agentx_iq} IQcores (governor)")
    print(f"  Min Alan:  {charter['rules']['min_alan_iqcores']}")
    print(f"  Max X:     {charter['rules']['max_agentx_iqcores']}")

    snap = IQCORES.snapshot()
    print()
    print(f"  Ledger (live):")
    for actor, data in snap.items():
        print(f"    {actor}: {data['current']}/{data['limit']} ({data['remaining']} remaining)")
    print("=" * 60)
