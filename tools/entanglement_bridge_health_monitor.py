"""
Entanglement Bridge Health Monitor
=====================================
Monitors cross-instance personality synchronization health for Phase 6.
In Phase 5, this runs in simulation mode (single instance, synthetic data).

Tracks:
  - Drift between primary and secondary state vectors
  - Sync frequency and hash match rate
  - Correlation coefficient
  - Reconvergence events

Usage:
    .venv\\Scripts\\python.exe tools/entanglement_bridge_health_monitor.py [--simulate]
"""

import sys
import os
import json
import time
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from personality_engine import PersonalityEngine

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── THRESHOLDS ───────────────────────────────────────────────────────────
DRIFT_NORMAL = 0.05
DRIFT_ELEVATED = 0.10
DRIFT_CRITICAL = 0.15
SYNC_PULL_STRENGTH = 0.05       # 5% pull toward primary
DAMPENING_LAMBDA_MIN = 0.1
DAMPENING_LAMBDA_MAX = 0.3
RECONVERGENCE_ALPHA = 0.7       # Blend weight for reconvergence
CORRELATION_FLOOR = 0.02


def compute_drift(v_primary, v_secondary):
    """Compute L2 drift between two state vectors."""
    return float(np.linalg.norm(v_primary - v_secondary))


def compute_correlation(v_primary, v_secondary):
    """Compute correlation coefficient between two state vectors."""
    if np.std(v_primary) < 1e-10 or np.std(v_secondary) < 1e-10:
        return 0.0
    return float(np.corrcoef(v_primary, v_secondary)[0, 1])


def hash_state(state_vector):
    """SHA-3 hash of state vector for sync detection."""
    data = state_vector.tobytes()
    return hashlib.sha3_256(data).hexdigest()[:16]


def sync_pull(v_primary, v_secondary, strength=SYNC_PULL_STRENGTH):
    """Apply sync pull: move secondary toward primary."""
    v_new = v_secondary + strength * (v_primary - v_secondary)
    # Re-normalize
    norm = np.linalg.norm(v_new)
    if norm > 1e-10:
        v_new = v_new / norm
    return v_new


def drift_dampening(v_primary, v_secondary, drift):
    """Apply drift dampening with adaptive lambda."""
    if drift < DRIFT_ELEVATED:
        return v_secondary  # No dampening needed

    # Scale lambda by drift magnitude
    lam = DAMPENING_LAMBDA_MIN + (DAMPENING_LAMBDA_MAX - DAMPENING_LAMBDA_MIN) * (
        min(drift - DRIFT_ELEVATED, DRIFT_CRITICAL - DRIFT_ELEVATED)
        / (DRIFT_CRITICAL - DRIFT_ELEVATED)
    )
    v_new = v_secondary - lam * (v_secondary - v_primary)
    norm = np.linalg.norm(v_new)
    if norm > 1e-10:
        v_new = v_new / norm
    return v_new


def reconverge(v_primary, v_secondary, alpha=RECONVERGENCE_ALPHA):
    """Full reconvergence protocol."""
    v_target = alpha * v_primary + (1 - alpha) * v_secondary
    norm = np.linalg.norm(v_target)
    if norm > 1e-10:
        v_target = v_target / norm
    return v_target


def simulate_divergence():
    """
    Simulate two PE instances diverging under different inputs.
    Demonstrates drift detection, dampening, and reconvergence.
    """
    print("\n  SIMULATION MODE — Two PE instances diverging")
    print("  " + "-" * 50)

    pe_primary = PersonalityEngine()
    pe_secondary = PersonalityEngine()

    # Shared sequence (turns 1-3)
    shared_turns = [
        ("positive", "Hello, I'm interested in your service."),
        ("neutral", "Tell me more about pricing."),
        ("positive", "That sounds reasonable."),
    ]

    # Divergent sequences
    primary_turns = [
        ("positive", "Great, let's set up a demo."),
        ("positive", "I'm excited about this."),
        ("positive", "My team will love this."),
    ]

    secondary_turns = [
        ("negative", "Actually, I have concerns."),
        ("negative", "The competitor offers more."),
        ("neutral", "I need to think about it."),
    ]

    log_entries = []

    # Shared phase
    print("\n  Phase 1: Shared inputs (turns 1-3)")
    for sentiment, text in shared_turns:
        pe_primary.process_turn(sentiment, text)
        pe_secondary.process_turn(sentiment, text)

    drift = compute_drift(pe_primary.quantum_state.state,
                          pe_secondary.quantum_state.state)
    print(f"    Post-shared drift: {drift:.6f} (should be ~0)")

    # Divergent phase
    print("\n  Phase 2: Divergent inputs (turns 4-6)")
    for i, ((p_sent, p_text), (s_sent, s_text)) in enumerate(
        zip(primary_turns, secondary_turns)
    ):
        pe_primary.process_turn(p_sent, p_text)
        pe_secondary.process_turn(s_sent, s_text)

        v_p = pe_primary.quantum_state.state
        v_s = pe_secondary.quantum_state.state
        drift = compute_drift(v_p, v_s)
        corr = compute_correlation(v_p, v_s)
        h_p = hash_state(v_p)
        h_s = hash_state(v_s)

        level = "NORMAL"
        if drift >= DRIFT_CRITICAL:
            level = "CRITICAL"
        elif drift >= DRIFT_ELEVATED:
            level = "ELEVATED"

        entry = {
            "turn": i + 4,
            "drift": round(drift, 6),
            "correlation": round(corr, 4),
            "hash_primary": h_p,
            "hash_secondary": h_s,
            "hash_match": h_p == h_s,
            "level": level,
        }
        log_entries.append(entry)

        print(f"    Turn {i+4}: drift={drift:.4f}  corr={corr:.4f}  level={level}")

    # Sync pull demo
    print("\n  Phase 3: Applying sync pull (5%)")
    v_s_before = pe_secondary.quantum_state.state.copy()
    v_s_after = sync_pull(pe_primary.quantum_state.state, v_s_before)
    drift_before = compute_drift(pe_primary.quantum_state.state, v_s_before)
    drift_after = compute_drift(pe_primary.quantum_state.state, v_s_after)
    print(f"    Drift before sync: {drift_before:.4f}")
    print(f"    Drift after sync:  {drift_after:.4f}")
    print(f"    Drift reduced by:  {drift_before - drift_after:.4f}")

    # Dampening demo
    if drift_before >= DRIFT_ELEVATED:
        print("\n  Phase 4: Applying drift dampening")
        v_s_dampened = drift_dampening(
            pe_primary.quantum_state.state, v_s_before, drift_before
        )
        drift_dampened = compute_drift(pe_primary.quantum_state.state, v_s_dampened)
        print(f"    Drift after dampening: {drift_dampened:.4f}")

    # Reconvergence demo
    if drift_before >= DRIFT_CRITICAL:
        print("\n  Phase 5: Reconvergence protocol (alpha=0.7)")
        v_s_reconverged = reconverge(pe_primary.quantum_state.state, v_s_before)
        drift_reconverged = compute_drift(
            pe_primary.quantum_state.state, v_s_reconverged
        )
        print(f"    Drift after reconvergence: {drift_reconverged:.4f}")
        print(f"    Below critical threshold: {drift_reconverged < DRIFT_CRITICAL}")

    # Write log
    log_path = os.path.join(PROJECT_ROOT, "phase6_bridge_simulation.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "simulation": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "entries": log_entries,
            "thresholds": {
                "normal": DRIFT_NORMAL,
                "elevated": DRIFT_ELEVATED,
                "critical": DRIFT_CRITICAL,
            },
        }, f, indent=2)
    print(f"\n  Simulation log saved to: {log_path}")

    return log_entries


def main():
    print("=" * 60)
    print("  ENTANGLEMENT BRIDGE HEALTH MONITOR")
    print("=" * 60)

    simulate = "--simulate" in sys.argv or len(sys.argv) < 2

    if simulate:
        entries = simulate_divergence()
        max_drift = max(e["drift"] for e in entries) if entries else 0
        print(f"\n  Max drift observed: {max_drift:.4f}")
        if max_drift >= DRIFT_CRITICAL:
            print("  STATUS: Reconvergence would be triggered in production")
        elif max_drift >= DRIFT_ELEVATED:
            print("  STATUS: Drift dampening would be applied in production")
        else:
            print("  STATUS: All within normal bounds")
    else:
        print("  Live monitoring not yet implemented.")
        print("  Use --simulate for simulation mode.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
