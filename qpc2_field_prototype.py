"""
QPC-2 Field Prototype
---------------------

Prototype module for Quantum + Continuum + Integration as a single field.

This DOES NOT modify qpc2_engine.py.
It runs alongside it, so you can compare behavior safely.

Core ideas:

    s_{t+1} = s_t + λ_t * k_t * ΔQ_t

Where:
    s_t   = FieldState (stance + energy)
    ΔQ_t  = FieldDelta from Quantum (proposed change)
    k_t   = Continuum weight in [0, 1] (how much change can flow now)
    λ_t   = Integration rate in [0, 1] (how much becomes identity)

You can later weave these abstractions into UnifiedRelationalEngine.step(...)
once you're satisfied with the prototype behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# =========================
# Field core structures
# =========================


@dataclass
class FieldState:
    """
    Minimal state vector for the field:
    - stance: boundaries, softness, directness, etc.
    - energy: how 'charged' the system is (for edge-of-chaos).
    """

    stance: Dict[str, float]
    energy: float  # 0 = flat, 1 = max intensity

    def copy(self) -> "FieldState":
        return FieldState(stance=dict(self.stance), energy=self.energy)


@dataclass
class FieldDelta:
    """Proposed change from the Quantum module."""

    d_stance: Dict[str, float]
    d_energy: float


# =========================
# Field equation components
# =========================


def quantum_proposal(state: FieldState, intensity: float) -> FieldDelta:
    """Quantum: propose a change direction based on intensity."""

    d_stance = {
        "boundary_hardness": +0.4 * intensity,
        "softness": -0.3 * intensity,
        "directness": +0.3 * intensity,
    }
    d_energy = 0.5 * intensity
    return FieldDelta(d_stance=d_stance, d_energy=d_energy)


def continuum_weight(state: FieldState, delta: FieldDelta) -> float:
    """Continuum: compute k_t in [0, 1] based on how disruptive the proposed change is."""

    total_shift = 0.0
    for dv in delta.d_stance.values():
        total_shift += abs(dv)

    normalized_shift = min(1.0, total_shift)
    k = 1.0 - 0.5 * normalized_shift
    k *= 1.0 - 0.3 * state.energy

    return clamp(k, 0.0, 1.0)


def integration_rate(state: FieldState, trust: float) -> float:
    """Integration: compute λ_t in [0, 1]."""

    base = 0.5 + 0.5 * trust
    fatigue = 0.3 * state.energy
    lam = base * (1.0 - fatigue)
    return clamp(lam, 0.0, 1.0)


def apply_field_update(state: FieldState, delta: FieldDelta, k: float, lam: float) -> FieldState:
    """Field equation: s_{t+1} = s_t + λ_t * k_t * ΔQ_t"""

    factor = lam * k
    new_stance = dict(state.stance)

    for key, dv in delta.d_stance.items():
        prev = new_stance.get(key, 0.5)
        new_stance[key] = clamp(prev + factor * dv, 0.0, 1.0)

    new_energy = clamp(state.energy + factor * delta.d_energy, 0.0, 1.0)

    return FieldState(stance=new_stance, energy=new_energy)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# =========================
# Higher-level helpers
# =========================


def step_field(state: FieldState, intensity: float, trust: float) -> FieldState:
    """Run a single quantum + continuum + integration update."""

    delta = quantum_proposal(state, intensity=intensity)
    k = continuum_weight(state, delta)
    lam = integration_rate(state, trust=trust)
    next_state = apply_field_update(state, delta, k, lam)
    return next_state


def run_scenario(initial: FieldState, intensities: List[float], trusts: List[float]) -> List[FieldState]:
    """Run a sequence of steps over the field, returning all states."""

    if len(intensities) != len(trusts):
        raise ValueError("intensities and trusts must align in length")

    states = [initial]
    current = initial
    for intensity, trust in zip(intensities, trusts):
        current = step_field(current, intensity=intensity, trust=trust)
        states.append(current)
    return states


# =========================
# Minimal console demo
# =========================


if __name__ == "__main__":
    s0 = FieldState(
        stance={
            "boundary_hardness": 0.7,
            "softness": 0.4,
            "directness": 0.6,
        },
        energy=0.3,
    )

    intensities = [0.3, 0.6, 0.9, 0.4, 0.7]
    trusts = [0.8, 0.9, 0.95, 0.7, 0.9]

    states = run_scenario(s0, intensities, trusts)

    print("\n=== QPC-2 Field Prototype Demo ===")
    for i, st in enumerate(states):
        print(f"\nStep {i}:")
        print("  boundary_hardness:", round(st.stance.get("boundary_hardness", 0.0), 3))
        print("  softness:         ", round(st.stance.get("softness", 0.0), 3))
        print("  directness:       ", round(st.stance.get("directness", 0.0), 3))
        print("  energy:           ", round(st.energy, 3))
