"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                 IQcore ALERTS — Burn-Rate Early Warning System                ║
║                                                                              ║
║  Monitors IQcore burn rates and produces alerts when actors approach          ║
║  cognitive budget exhaustion.                                                ║
║                                                                              ║
║  Thresholds:                                                                 ║
║    HIGH     — > 70% of allocated IQcores consumed                            ║
║    CRITICAL — > 90% consumed                                                 ║
║    EXHAUST  — >= 100% (enforcer blocks before this)                          ║
║                                                                              ║
║  Alerts are written to iqcore_alert_log.json and surfaced to Agent X.       ║
║                                                                              ║
║  Author: Agent X / CW23                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import time
import logging
from pathlib import Path

logger = logging.getLogger("IQCORE_ALERT")

ALERT_LOG_PATH = Path(__file__).parent / "logs" / "iqcore_alert_log.json"

# Ensure logs directory exists
ALERT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── THRESHOLDS ──────────────────────────────────────────────────────────────

THRESHOLD_HIGH = 70       # > 70% → informational alert
THRESHOLD_CRITICAL = 90   # > 90% → intervention alert


# ─── ALERT WRITER ────────────────────────────────────────────────────────────

def _write_alert(alert: dict) -> None:
    """Append an alert to the alert log. Never throws."""
    try:
        data = []
        if ALERT_LOG_PATH.exists():
            data = json.loads(ALERT_LOG_PATH.read_text(encoding="utf-8"))

        data.append(alert)

        # Cap to last 500 alerts
        if len(data) > 500:
            data = data[-500:]

        ALERT_LOG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning(f"[IQCORE_ALERT] Failed to write alert: {e}")


# ─── BURN RATE CHECKER ──────────────────────────────────────────────────────

def check_burn_rates() -> list:
    """
    Check all actors' burn rates against thresholds.
    Returns a list of alerts generated (empty if all clear).

    Should be called:
    - once per campaign cycle
    - once per Regime Engine cycle
    - once per Agent X governance cycle
    """
    try:
        from iqcore_dashboard import get_dashboard
    except ImportError:
        return []

    dashboard = get_dashboard()
    actors = dashboard.get("actors", {})
    alerts = []

    for actor, state in actors.items():
        limit = state.get("limit", 0)
        current = state.get("current", 0)

        if limit <= 0:
            continue  # Skip actors with no budget (e.g., RegimeEngine observes only)

        pct = (current / limit) * 100

        alert = None
        if pct >= THRESHOLD_CRITICAL:
            alert = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "actor": actor,
                "level": "CRITICAL",
                "burn_pct": round(pct, 1),
                "current": current,
                "limit": limit,
                "message": f"{actor} at {pct:.1f}% IQcore burn — INTERVENTION REQUIRED",
            }
        elif pct >= THRESHOLD_HIGH:
            alert = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "actor": actor,
                "level": "HIGH",
                "burn_pct": round(pct, 1),
                "current": current,
                "limit": limit,
                "message": f"{actor} at {pct:.1f}% IQcore burn — approaching limit",
            }

        if alert:
            _write_alert(alert)
            alerts.append(alert)
            logger.warning(f"[IQCORE_ALERT] {alert['level']}: {alert['message']}")

    return alerts


def get_alert_history(limit: int = 50) -> list:
    """Get the most recent alerts from the log."""
    if not ALERT_LOG_PATH.exists():
        return []
    try:
        data = json.loads(ALERT_LOG_PATH.read_text(encoding="utf-8"))
        return data[-limit:]
    except Exception:
        return []


def clear_alerts() -> None:
    """Clear the alert log."""
    try:
        ALERT_LOG_PATH.write_text("[]", encoding="utf-8")
    except Exception:
        pass


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  IQcore ALERTS — Burn-Rate Check")
    print("=" * 60)

    alerts = check_burn_rates()
    if alerts:
        for a in alerts:
            print(f"  [{a['level']:8s}] {a['actor']:10s} — {a['message']}")
    else:
        print("  All actors within safe IQcore limits.")

    history = get_alert_history(10)
    if history:
        print(f"\n  Recent Alert History ({len(history)} entries):")
        for h in history[-5:]:
            print(f"    {h['timestamp']} [{h['level']}] {h['actor']}: {h['message']}")

    print("=" * 60)
