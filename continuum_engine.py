"""
continuum_engine.py

Continuum Engine (QPC Layer 2 – Relational Field Layer)

This module implements:
- Field: continuous vectors/tensors over abstract spaces
- ContinuumEngine: generic field evolution engine
- RelationalFields: typed wrappers for ethics, emotion, context, narrative
- NarrativeState: bundled relational state
- RelationalDynamics: pluggable drift functions that define system behavior

Designed to sit between:
- Layer 1: Raw signal / sensory input
- Layer 3: Quantum / packet engine (discrete reasoning & decisions)

The quantum engine should:
- READ: stabilized fields (ethics, emotion, context, narrative)
- WRITE: external signals / perturbations, not hard overrides
"""

from __future__ import annotations
from dataclasses import dataclass, field as dataclass_field
from typing import Callable, Dict, Optional
import numpy as np


# ---------------------------------------------------------------------------
# Core: Generic continuous field
# ---------------------------------------------------------------------------

class Field:
    """
    A continuous field over some abstract space.

    Internally represented as a 1D or ND numpy array of floats.

    The field is assumed to be:
    - continuous (no hard jumps in core logic)
    - differentiable (conceptually, even if we don't use explicit gradients)
    - suitable for smooth evolution via drift functions
    """

    def __init__(self, values: np.ndarray):
        if not isinstance(values, np.ndarray):
            values = np.array(values, dtype=float)
        self.values = values.astype(float)

    def copy(self) -> "Field":
        return Field(self.values.copy())

    def blend(self, other: "Field", alpha: float) -> "Field":
        """
        Smooth interpolation between two fields.

        alpha in [0, 1]:
        - 0.0 -> self
        - 1.0 -> other
        """
        alpha = float(np.clip(alpha, 0.0, 1.0))
        return Field((1.0 - alpha) * self.values + alpha * other.values)

    def apply_nonlin(self, fn: Callable[[np.ndarray], np.ndarray]) -> "Field":
        """
        Apply a smooth, element-wise nonlinearity.
        """
        return Field(fn(self.values))

    def norm(self) -> float:
        """
        Euclidean norm of the field (used for diagnostics, not decisions).
        """
        return float(np.linalg.norm(self.values))

    def as_array(self) -> np.ndarray:
        """
        Safely expose underlying array for read-only use.
        """
        return self.values

    def __len__(self) -> int:
        return self.values.size

    def __repr__(self) -> str:
        return f"Field(shape={self.values.shape}, norm={self.norm():.4f})"


# ---------------------------------------------------------------------------
# Typed relational fields
# ---------------------------------------------------------------------------

@dataclass
class RelationalFields:
    """
    Typed wrappers around core fields.

    These represent *continuous* relational substrates:
    - ethics: ethical tension / balance field
    - emotion: emotional intensity / tone field
    - context: relevance, salience, and situational backdrop
    - narrative: continuity, arc, and momentum
    """

    ethics: Field
    emotion: Field
    context: Field
    narrative: Field


# ---------------------------------------------------------------------------
# Continuum Engine – generic field evolution
# ---------------------------------------------------------------------------

DriftFn = Callable[[np.ndarray], np.ndarray]


class ContinuumEngine:
    """
    Generic engine for evolving continuous fields over time.

    Core primitive:
        new_values = old_values + step_size * drift_fn(old_values)

    Where:
    - drift_fn describes the *direction* the field wants to move.
    - step_size controls how fast it moves (small = smoother, more stable).
    """

    def __init__(self, step_size: float = 0.05):
        self.step_size = float(step_size)

    def evolve(self, field: Field, drift_fn: DriftFn) -> Field:
        """
        Apply one evolution step to a field using a drift function.
        """
        values = field.as_array()
        drift = drift_fn(values)
        new_values = values + self.step_size * drift
        return Field(new_values)

    def stabilize_toward(self, field: Field, target: Field, strength: float) -> Field:
        """
        Pull a field smoothly toward a target configuration.

        drift = strength * (target - current)
        """
        strength = float(strength)

        def drift_fn(values: np.ndarray) -> np.ndarray:
            return strength * (target.as_array() - values)

        return self.evolve(field, drift_fn)


# ---------------------------------------------------------------------------
# Relational dynamics – default drift functions
# ---------------------------------------------------------------------------

class RelationalDynamics:
    """
    Default relational drift functions.

    These are *not* hard rules.
    They define how the fields tend to move in the absence of discrete overrides.
    """

    @staticmethod
    def ethical_drift(values: np.ndarray) -> np.ndarray:
        """
        Ethics: encourage balance, penalize extremes softly.

        Intuition:
        - Very high or low values represent polarized ethical stances.
        - The system gently nudges them toward a balanced basin at 0.
        """
        return -0.1 * np.tanh(values)

    @staticmethod
    def emotional_drift(values: np.ndarray, external: np.ndarray) -> np.ndarray:
        """
        Emotions: smooth response to external inputs, with gentle decay.

        Intuition:
        - Emotion responds to stimuli (external) but also relaxes over time.
        """
        external = np.broadcast_to(external, values.shape)
        decay = -0.05 * values
        response = 0.2 * external
        return decay + response

    @staticmethod
    def context_drift(values: np.ndarray, signal: np.ndarray) -> np.ndarray:
        """
        Context: track external signal slowly, avoid sharp jumps.

        Intuition:
        - Context wants to follow the signal but not instantly match it.
        """
        signal = np.broadcast_to(signal, values.shape)
        return 0.1 * (signal - values)

    @staticmethod
    def narrative_drift(values: np.ndarray, tension: np.ndarray) -> np.ndarray:
        """
        Narrative: integrate tension into momentum.

        Intuition:
        - Tension (from ethics/emotion) shapes narrative momentum.
        - The narrative state changes in the direction of sustained tension.
        """
        tension = np.broadcast_to(tension, values.shape)
        momentum = 0.05 * tension
        decay = -0.02 * values
        return momentum + decay


# ---------------------------------------------------------------------------
# Narrative state – bundled relational layer for QPC
# ---------------------------------------------------------------------------

@dataclass
class NarrativeState:
    """
    The continuum layer's bundled state for QPC consumption.

    This is what Layer 3 (quantum/packet engine) should read from.

    It includes:
    - ethics: Field
    - emotion: Field
    - context: Field
    - narrative: Field
    """

    ethics: Field
    emotion: Field
    context: Field
    narrative: Field

    def snapshot(self) -> RelationalFields:
        """
        Return a structured snapshot for sampling / logging.
        """
        return RelationalFields(
            ethics=self.ethics.copy(),
            emotion=self.emotion.copy(),
            context=self.context.copy(),
            narrative=self.narrative.copy(),
        )


# ---------------------------------------------------------------------------
# High-level Continuum + Narrative integration
# ---------------------------------------------------------------------------

class ContinuumRelationalLayer:
    """
    High-level wrapper around ContinuumEngine + relational dynamics.

    This is the object QPC should talk to as "Layer 2 – Continuum Engine".

    Responsibilities:
    - Maintain NarrativeState
    - Evolve fields in response to raw inputs (Layer 1)
    - Expose a stable, read-only, structured API for the quantum layer
    """

    def __init__(
        self,
        dim: int = 16,
        step_size: float = 0.05,
        rng: Optional[np.random.Generator] = None,
    ):
        self.dim = int(dim)
        self.engine = ContinuumEngine(step_size=step_size)
        self.rng = rng or np.random.default_rng()

        ethics_init = Field(self.rng.normal(loc=0.0, scale=0.5, size=self.dim))
        emotion_init = Field(np.zeros(self.dim))
        context_init = Field(np.zeros(self.dim))
        narrative_init = Field(np.zeros(self.dim))

        self.state = NarrativeState(
            ethics=ethics_init,
            emotion=emotion_init,
            context=context_init,
            narrative=narrative_init,
        )

    def step(
        self,
        raw_signal: np.ndarray,
        external_emotion: Optional[np.ndarray] = None,
        overrides: Optional[Dict[str, DriftFn]] = None,
    ) -> NarrativeState:
        """
        Advance the continuum layer by one time step.

        Inputs:
        - raw_signal: continuous vector from Layer 1 (sensory / context input)
        - external_emotion: optional emotional signal (e.g., user affect estimate)
        - overrides: optional dict of drift overrides per field:
            keys: "ethics", "emotion", "context", "narrative"
            values: drift functions taking np.ndarray -> np.ndarray

        Returns:
        - updated NarrativeState (also stored internally)
        """
        overrides = overrides or {}
        raw_signal = np.broadcast_to(raw_signal, (self.dim,))

        ethics_drift = overrides.get("ethics", RelationalDynamics.ethical_drift)
        new_ethics = self.engine.evolve(self.state.ethics, ethics_drift)

        external_emotion = np.zeros(self.dim) if external_emotion is None else np.broadcast_to(external_emotion, (self.dim,))

        def default_emotional_drift(values: np.ndarray) -> np.ndarray:
            return RelationalDynamics.emotional_drift(values, external_emotion)

        emotion_drift = overrides.get("emotion", default_emotional_drift)
        new_emotion = self.engine.evolve(self.state.emotion, emotion_drift)

        def default_context_drift(values: np.ndarray) -> np.ndarray:
            return RelationalDynamics.context_drift(values, raw_signal)

        context_drift = overrides.get("context", default_context_drift)
        new_context = self.engine.evolve(self.state.context, context_drift)

        tension = new_ethics.as_array() + new_emotion.as_array()

        def default_narrative_drift(values: np.ndarray) -> np.ndarray:
            return RelationalDynamics.narrative_drift(values, tension)

        narrative_drift = overrides.get("narrative", default_narrative_drift)
        new_narrative = self.engine.evolve(self.state.narrative, narrative_drift)

        self.state = NarrativeState(
            ethics=new_ethics,
            emotion=new_emotion,
            context=new_context,
            narrative=new_narrative,
        )
        return self.state

    def get_fields(self) -> RelationalFields:
        return self.state.snapshot()

    def get_compact_view(self) -> Dict[str, np.ndarray]:
        fields = self.state.snapshot()
        return {
            "ethics": fields.ethics.as_array().copy(),
            "emotion": fields.emotion.as_array().copy(),
            "context": fields.context.as_array().copy(),
            "narrative": fields.narrative.as_array().copy(),
        }

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        ethics_init = Field(self.rng.normal(loc=0.0, scale=0.5, size=self.dim))
        emotion_init = Field(np.zeros(self.dim))
        context_init = Field(np.zeros(self.dim))
        narrative_init = Field(np.zeros(self.dim))

        self.state = NarrativeState(
            ethics=ethics_init,
            emotion=emotion_init,
            context=context_init,
            narrative=narrative_init,
        )


# ---------------------------------------------------------------------------
# Minimal demo hook (safe to remove in production)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    layer = ContinuumRelationalLayer(dim=8, step_size=0.05, rng=np.random.default_rng(42))

    for t in range(5):
        raw_signal = np.linspace(-1.0, 1.0, 8)
        external_emotion = np.sin(np.linspace(0, np.pi, 8) + 0.2 * t)

        state = layer.step(raw_signal=raw_signal, external_emotion=external_emotion)
        view = layer.get_compact_view()

        print(f"Step {t}")
        print("  ethics norm   :", np.linalg.norm(view["ethics"]))
        print("  emotion norm  :", np.linalg.norm(view["emotion"]))
        print("  context norm  :", np.linalg.norm(view["context"]))
        print("  narrative norm:", np.linalg.norm(view["narrative"]))
        print()
