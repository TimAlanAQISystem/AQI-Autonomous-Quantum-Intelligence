"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  IQcore DASHBOARD — Cognitive Ledger                         ║
║                                                                              ║
║  Unified view of cognitive burn-rate, remaining budget, and per-function     ║
║  cost across Alan, Agent X, and the Regime Engine.                           ║
║                                                                              ║
║  Reads/writes iqcore_dashboard_state.json.                                   ║
║  Does NOT interfere with the enforcers — it only observes and logs.         ║
║                                                                              ║
║  Author: Agent X / CW23                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import time
import os
import threading
import logging
from pathlib import Path

logger = logging.getLogger("IQCORE_DASH")

DASHBOARD_PATH = Path(__file__).parent / "iqcore_dashboard_state.json"

_dash_lock = threading.Lock()


def _load() -> dict:
    """Load the dashboard state from disk."""
    if not DASHBOARD_PATH.exists():
        return _default_state()
    try:
        with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"[IQCORE_DASH] Failed to load state: {e}")
        return _default_state()


def _default_state() -> dict:
    return {
        "version": "1.0.0",
        "updated_at": "",
        "actors": {
            "Alan": {"limit": 60, "current": 0, "burn_log": []},
            "AgentX": {"limit": 40, "current": 0, "burn_log": []},
            "RegimeEngine": {"limit": 0, "current": 0, "burn_log": []},
        },
    }


def _save(state: dict) -> None:
    """Save the dashboard state to disk."""
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"[IQCORE_DASH] Failed to save state: {e}")


def log_burn(actor: str, cost: int, function_name: str) -> None:
    """
    Log a cognitive burn event for an actor.
    Called by the IQcore enforcer decorator after each decorated function runs.

    Keeps at most the last 200 burn log entries per actor to prevent unbounded growth.
    """
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "function": function_name,
        "cost": cost,
    }

    with _dash_lock:
        state = _load()
        if actor not in state["actors"]:
            state["actors"][actor] = {"limit": 0, "current": 0, "burn_log": []}

        state["actors"][actor]["current"] += cost
        state["actors"][actor]["burn_log"].append(entry)

        # Cap burn log size
        if len(state["actors"][actor]["burn_log"]) > 200:
            state["actors"][actor]["burn_log"] = state["actors"][actor]["burn_log"][-200:]

        _save(state)


def reset_actor(actor: str) -> None:
    """Reset an actor's burn state to zero."""
    with _dash_lock:
        state = _load()
        if actor in state["actors"]:
            state["actors"][actor]["current"] = 0
            state["actors"][actor]["burn_log"] = []
            _save(state)


def reset_all() -> None:
    """Reset all actors' burn state to zero."""
    with _dash_lock:
        state = _load()
        for actor in state["actors"]:
            state["actors"][actor]["current"] = 0
            state["actors"][actor]["burn_log"] = []
        _save(state)


def get_dashboard() -> dict:
    """Get the full dashboard state."""
    return _load()


def get_actor_summary(actor: str) -> dict:
    """Get a summary for a specific actor."""
    state = _load()
    if actor not in state["actors"]:
        return {"error": f"Unknown actor: {actor}"}
    a = state["actors"][actor]
    pct = (a["current"] / a["limit"] * 100) if a["limit"] > 0 else 0
    return {
        "actor": actor,
        "current": a["current"],
        "limit": a["limit"],
        "remaining": a["limit"] - a["current"],
        "burn_pct": round(pct, 1),
        "recent_burns": a["burn_log"][-5:] if a["burn_log"] else [],
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pprint

    print("=" * 60)
    print("  IQcore DASHBOARD — Live Snapshot")
    print("=" * 60)

    state = get_dashboard()
    print(f"  Version:    {state.get('version', '?')}")
    print(f"  Updated:    {state.get('updated_at', 'never')}")
    print()

    for actor, data in state.get("actors", {}).items():
        limit = data.get("limit", 0)
        current = data.get("current", 0)
        pct = (current / limit * 100) if limit > 0 else 0
        burns = len(data.get("burn_log", []))
        print(f"  {actor:15s}  {current:3d}/{limit:3d}  ({pct:5.1f}%)  [{burns} burns logged]")

    print("=" * 60)
