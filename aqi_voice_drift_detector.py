"""
AQI Voice Drift Detector (v1.0)
-------------------------------

Consumes per-turn trajectories from the regression harness and
emits governance-grade drift signals.
"""

from __future__ import annotations

from typing import List, Dict, Any


DEFAULT_THRESHOLDS = {
    "energy_spike": 0.35,
    "energy_drift": 0.25,
    "stance_delta": 0.30,
    "oscillation": 0.40,
    "softening": -0.25,
}


def _safe_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _delta(prev, curr):
    if prev is None or curr is None:
        return None
    return curr - prev


def detect_voice_drift(
    trajectory: List[Dict[str, Any]],
    thresholds: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    energies = [_safe_float(t.get("energy")) for t in trajectory]
    stances = [t.get("stance") for t in trajectory]

    energy_drift = False
    energy_spikes: List[int] = []
    oscillation = False

    for i in range(1, len(energies)):
        prev = energies[i - 1]
        curr = energies[i]
        if prev is None or curr is None:
            continue

        if curr - prev > thresholds["energy_spike"]:
            energy_spikes.append(i)

        if abs(curr - energies[0]) > thresholds["energy_drift"]:
            energy_drift = True

        if i >= 2:
            prev2 = energies[i - 2]
            if prev2 is not None and (curr - prev) * (prev - prev2) < -thresholds["oscillation"]:
                oscillation = True

    stance_instability = False
    softening = False

    for i in range(1, len(stances)):
        prev = stances[i - 1]
        curr = stances[i]
        if not isinstance(prev, dict) or not isinstance(curr, dict):
            continue

        for key, curr_val in curr.items():
            prev_val = prev.get(key)
            if prev_val is None:
                continue

            change = _delta(prev_val, curr_val)
            if change is None:
                continue

            if abs(change) > thresholds["stance_delta"]:
                stance_instability = True

            if change < thresholds["softening"]:
                softening = True

    return {
        "energy_drift": energy_drift,
        "energy_spikes": energy_spikes,
        "stance_instability": stance_instability,
        "oscillation": oscillation,
        "softening": softening,
        "details": {
            "energies": energies,
            "stances": stances,
            "thresholds": thresholds,
        },
    }
