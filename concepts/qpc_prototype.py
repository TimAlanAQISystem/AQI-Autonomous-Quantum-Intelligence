"""
QPC Prototype — Multi-wave Reasoning Chamber for AQI
----------------------------------------------------

This module implements a Quantum Probability Cloud (QPC) style multi-wave
reasoning engine with:

- Wave types: standing, transitional, null, superposition,
  plus semantic roles: ethical, surplus, cadence, calibration.
- Logging decorator for per-wave introspection.
- Collapse trace so each decision is explainable.
- Latent waves that activate when thresholds are crossed.
- ASCII variant-space visualizer for quick inspection.
- A simple calibration / stress test harness in __main__.

This file is intentionally self-contained so it can live in concepts/
as a conceptual chamber, independent of AQI's operational backbone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List, Any, Dict, Optional, Tuple
import math
import random
import time


# Simple global debug toggle for quiet vs. verbose runs.
_DEBUG = True


def set_debug_mode(enabled: bool) -> None:
    """Toggle verbose logging for this module."""

    global _DEBUG
    _DEBUG = bool(enabled)


def get_debug_mode() -> bool:
    """Return current debug flag state."""

    return _DEBUG


def _dprint(*args: Any, **kwargs: Any) -> None:
    """Conditional print obeying the debug toggle."""

    if _DEBUG:
        print(*args, **kwargs)


# ============================================================
# Wave typing and roles
# ============================================================

class WaveType(Enum):
    """
    Structural type of a wave — how it behaves in the variant-space.
    """

    STANDING = auto()       # stable, always-present pattern
    TRANSITIONAL = auto()   # in-motion / bridging state
    NULL = auto()           # structurally present, zero amplitude
    SUPERPOSITION = auto()  # part of a cloud of possibilities


class WaveRole(Enum):
    """
    Semantic role of a wave — what domain it serves.
    """

    GENERIC = auto()
    ETHICAL = auto()
    SURPLUS = auto()
    CADENCE = auto()
    CALIBRATION = auto()


# ============================================================
# Logging / introspection
# ============================================================

def wave_logger(fn: Callable[..., float]) -> Callable[..., float]:
    """
    Decorator to log per-wave evaluation.

    Expects the wrapped function signature:
        fn(self, context) -> float

    Prints:
    - Wave name
    - Wave role
    - Wave type
    - Raw score
    - Amplitude
    - Weighted score
    """

    def wrapper(self: Wave, context: Dict[str, Any]) -> float:
        raw = fn(self, context)
        weighted = self.amplitude * raw
        if _DEBUG:
            print(
                f"[WAVE EVAL] name={self.name:<18} "
                f"role={self.role.name:<11} "
                f"type={self.wave_type.name:<13} "
                f"raw={raw:6.3f} amp={self.amplitude:5.3f} "
                f"weighted={weighted:6.3f}"
            )
        return raw

    return wrapper


# ============================================================
# Wave, variant, QPC core
# ============================================================


@dataclass
class Wave:
    """
    Represents one 'wave' – a possible way of reasoning / acting.

    eval_fn:
        Takes a context dict and returns a raw suitability score.
    """

    name: str
    wave_type: WaveType
    role: WaveRole
    amplitude: float                        # pre-normalized weight
    eval_fn: Callable[[Dict[str, Any]], float]
    # Optional activation threshold: if provided, the wave may start latent
    # and become active when the context crosses this threshold.
    activation_key: Optional[str] = None
    activation_threshold: Optional[float] = None

    @wave_logger
    def _logged_eval(self, context: Dict[str, Any]) -> float:
        return self.eval_fn(context)

    def evaluate(self, context: Dict[str, Any]) -> float:
        """
        Compute amplitude-weighted score given context.
        """

        raw_score = self._logged_eval(context)
        return self.amplitude * raw_score

    def should_activate(self, context: Dict[str, Any]) -> bool:
        """
        Return True if this wave has an activation threshold and the context
        meets or exceeds it.
        """

        if self.activation_key is None or self.activation_threshold is None:
            return False
        value = context.get(self.activation_key, 0.0)
        return value >= self.activation_threshold


@dataclass
class WaveVariant:
    """
    Structured slot on the QPC: a discretized 'square on the board'.

    wave:   The Wave that occupies this slot (or None).
    latent: True = present in structure but not currently active.
    """

    id: int
    wave: Optional[Wave] = None
    latent: bool = False

    def is_active(self) -> bool:
        return self.wave is not None and not self.latent

    def describe(self) -> str:
        if self.wave is None:
            return f"[{self.id}] EMPTY"
        status = "ACTIVE" if not self.latent else "LATENT"
        wt = self.wave.wave_type.name
        wr = self.wave.role.name
        act_info = ""
        if self.wave.activation_key is not None:
            act_info = (
                f" (threshold: {self.wave.activation_key}>="
                f"{self.wave.activation_threshold})"
            )
        return (
            f"[{self.id:02}] {self.wave.name:<18} "
            f"({wt:<13} {wr:<11}) amp={self.wave.amplitude:5.3f} "
            f"{status}{act_info}"
        )


@dataclass
class QPC:
    """
    Quantum Probability Cloud: holds all variants (expressed + latent).

    This is the chamber where multiple waves coexist, some active,
    some latent, some null, all part of the same variant-space.
    """

    variants: List[WaveVariant] = field(default_factory=list)

    def add_wave(self, wave: Wave, latent: bool = False) -> None:
        vid = len(self.variants)
        self.variants.append(WaveVariant(id=vid, wave=wave, latent=latent))

    def active_waves(self) -> List[Wave]:
        return [v.wave for v in self.variants if v.is_active()]

    def latent_waves(self) -> List[Wave]:
        return [v.wave for v in self.variants if (v.wave is not None and v.latent)]

    def as_superposition(self) -> List[Wave]:
        """
        Interpret all active waves as a superposition cloud.
        """

        return self.active_waves()

    def activate_latent_based_on_context(self, context: Dict[str, Any]) -> None:
        """
        Check latent waves against their activation thresholds and promote
        them to active if needed.
        """

        for variant in self.variants:
            if variant.wave is not None and variant.latent:
                if variant.wave.should_activate(context):
                    _dprint(
                        f"[QPC] Activating latent wave "
                        f"'{variant.wave.name}' due to "
                        f"{variant.wave.activation_key}>="
                        f"{variant.wave.activation_threshold}"
                    )
                    variant.latent = False

    def visualize(self) -> None:
        """
        ASCII representation of the variant-space.
        """

        _dprint("\n[QPC VARIANT SPACE]")
        if not self.variants:
            _dprint("  <empty>")
            return
        for variant in self.variants:
            _dprint("  " + variant.describe())
        _dprint()


# ============================================================
# Collapse strategy with trace
# ============================================================


@dataclass
class CollapseTrace:
    """
    Records the details of a collapse event for introspection.
    """

    scores: Dict[str, float]
    normalized_probs: Dict[str, float]
    chosen_wave_name: Optional[str]
    random_sample: Optional[float]
    reason: str
    timestamp: float


@dataclass
class DriftMonitor:
    """Lightweight tracker for wave win rates to spot drift."""

    counts: Dict[str, int] = field(default_factory=dict)
    total: int = 0

    def record(self, wave_name: Optional[str]) -> None:
        if wave_name is None:
            return
        self.counts[wave_name] = self.counts.get(wave_name, 0) + 1
        self.total += 1

    def summary(self) -> Dict[str, float]:
        if self.total == 0:
            return {}
        return {name: count / self.total for name, count in self.counts.items()}

    def reset(self) -> None:
        self.counts.clear()
        self.total = 0


class WaveCollapseStrategy:
    """
    Policy for collapsing a superposition of waves into a single chosen wave.
    """

    @staticmethod
    def normalize_scores(scores: Dict[Wave, float]) -> Dict[Wave, float]:
        total = sum(max(s, 0.0) for s in scores.values())
        if total == 0:
            n = len(scores)
            return {w: 1.0 / n for w in scores} if n > 0 else {}
        return {w: max(s, 0.0) / total for w, s in scores.items()}

    @staticmethod
    def probabilistic_collapse(
        scores: Dict[Wave, float]
    ) -> Tuple[Optional[Wave], CollapseTrace]:
        """
        Collapse by sampling according to normalized scores.
        Also produce a CollapseTrace for introspection.
        """

        if not scores:
            trace = CollapseTrace(
                scores={},
                normalized_probs={},
                chosen_wave_name=None,
                random_sample=None,
                reason="No active waves available.",
                timestamp=time.time(),
            )
            return None, trace

        probs = WaveCollapseStrategy.normalize_scores(scores)
        r = random.random()
        cumulative = 0.0
        chosen: Optional[Wave] = None

        for wave, p in probs.items():
            cumulative += p
            if r <= cumulative:
                chosen = wave
                break

        if chosen is None:
            # Fallback: highest score
            chosen = max(scores.items(), key=lambda kv: kv[1])[0]
            reason = "Fallback to max-scoring wave."
        else:
            reason = "Probabilistic collapse based on normalized scores."

        # Build trace
        trace = CollapseTrace(
            scores={w.name: s for w, s in scores.items()},
            normalized_probs={w.name: p for w, p in probs.items()},
            chosen_wave_name=chosen.name if chosen else None,
            random_sample=r,
            reason=reason,
            timestamp=time.time(),
        )
        return chosen, trace


# ============================================================
# Multi-wave reasoner
# ============================================================


@dataclass
class MultiWaveReasoner:
    """
    AQI-style reasoning core using a QPC and multi-wave evaluation.
    """

    qpc: QPC
    drift_monitor: Optional[DriftMonitor] = None

    def evaluate_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        1. Activate any latent waves whose thresholds are met.
        2. Treat all active waves as a superposition.
        3. Evaluate each wave (with logging).
        4. Collapse to one chosen wave (with trace).
        5. Return decision + debug info + confidence.
        """

        _dprint("\n[REASONER] Evaluating context:", context)

        # 1. Activate latent waves if thresholds met
        self.qpc.activate_latent_based_on_context(context)

        # 2. Get active waves
        waves = self.qpc.as_superposition()
        if not waves:
            _dprint("[REASONER] No active waves available.")
            return {
                "chosen_wave": None,
                "scores": {},
                "probs": {},
                "wave_types": {},
                "wave_roles": {},
                "collapse_reason": "No active waves available.",
            }

        # 3. Evaluate each wave
        scores: Dict[Wave, float] = {}
        for w in waves:
            score = w.evaluate(context)
            scores[w] = score

        # 4. Collapse
        chosen, trace = WaveCollapseStrategy.probabilistic_collapse(scores)

        confidence = compute_confidence(scores, trace, self.drift_monitor)

        # 5. Summarize
        _dprint("\n[COLLAPSE TRACE]")
        _dprint(f"  random_sample: {trace.random_sample}")
        _dprint(f"  chosen_wave : {trace.chosen_wave_name}")
        _dprint(f"  reason      : {trace.reason}")
        _dprint("  scores:")
        for name, s in trace.scores.items():
            _dprint(f"    {name:<18}: {s:6.3f}")
        _dprint("  normalized_probs:")
        for name, p in trace.normalized_probs.items():
            _dprint(f"    {name:<18}: {p:6.3f}")
        _dprint()

        result = {
            "chosen_wave": chosen.name if chosen else None,
            "scores": {w.name: s for w, s in scores.items()},
            "probs": {w.name: trace.normalized_probs.get(w.name, 0.0) for w in waves},
            "wave_types": {w.name: w.wave_type.name for w in waves},
            "wave_roles": {w.name: w.role.name for w in waves},
            "collapse_reason": trace.reason,
            "confidence": confidence,
        }

        if self.drift_monitor is not None:
            self.drift_monitor.record(result["chosen_wave"])

        return result


# ============================================================
# Example wave behavior functions
# ============================================================


def eval_protect_merchant(context: Dict[str, Any]) -> float:
    """
    ETHICAL: High score when risk is high.
    """

    return float(context.get("risk_level", 0.0))


def eval_optimize_surplus(context: Dict[str, Any]) -> float:
    """
    SURPLUS: High score when surplus potential is high.
    """

    return float(context.get("surplus_potential", 0.0))


def eval_cadence_deescalate(context: Dict[str, Any]) -> float:
    """
    CADENCE: High score when conflict is high.
    """

    return float(context.get("conflict_intensity", 0.0))


def eval_calibration_refine(context: Dict[str, Any]) -> float:
    """
    CALIBRATION: High score when uncertainty is high.
    """

    return float(context.get("uncertainty_level", 0.0))


def eval_observe_only(context: Dict[str, Any]) -> float:
    """
    NULL / fallback observer: Even when low, it never fully disappears
    structurally. Here we return a small constant.
    """

    return 0.1


# ============================================================
# QPC builder
# ============================================================


def build_sample_qpc() -> QPC:
    """
    Build a QPC with a mix of wave types and roles, including latent
    threshold-activated waves.
    """

    qpc = QPC()

    # Standing ETHICAL wave – always present, high amplitude
    qpc.add_wave(
        Wave(
            name="ProtectMerchant",
            wave_type=WaveType.STANDING,
            role=WaveRole.ETHICAL,
            amplitude=0.9,
            eval_fn=eval_protect_merchant,
            activation_key=None,
            activation_threshold=None,
        ),
        latent=False,
    )

    # Transitional SURPLUS wave – focuses on surplus growth
    qpc.add_wave(
        Wave(
            name="OptimizeSurplus",
            wave_type=WaveType.TRANSITIONAL,
            role=WaveRole.SURPLUS,
            amplitude=0.7,
            eval_fn=eval_optimize_surplus,
            activation_key=None,
            activation_threshold=None,
        ),
        latent=False,
    )

    # SUPERPOSITION CADENCE wave – de-escalation under conflict
    qpc.add_wave(
        Wave(
            name="Deescalate",
            wave_type=WaveType.SUPERPOSITION,
            role=WaveRole.CADENCE,
            amplitude=0.8,
            eval_fn=eval_cadence_deescalate,
            activation_key=None,
            activation_threshold=None,
        ),
        latent=False,
    )

    # NULL observer – structurally present, latent, zero amplitude
    qpc.add_wave(
        Wave(
            name="ObserveOnly",
            wave_type=WaveType.NULL,
            role=WaveRole.GENERIC,
            amplitude=0.0,
            eval_fn=eval_observe_only,
            activation_key=None,
            activation_threshold=None,
        ),
        latent=True,
    )

    # Latent ETHICAL guard – activates on high risk
    qpc.add_wave(
        Wave(
            name="EthicalGuard",
            wave_type=WaveType.STANDING,
            role=WaveRole.ETHICAL,
            amplitude=0.6,
            eval_fn=eval_protect_merchant,
            activation_key="risk_level",
            activation_threshold=0.7,
        ),
        latent=True,
    )

    # Latent SURPLUS amplifier – activates when surplus potential is high
    qpc.add_wave(
        Wave(
            name="SurplusAmplifier",
            wave_type=WaveType.SUPERPOSITION,
            role=WaveRole.SURPLUS,
            amplitude=0.5,
            eval_fn=eval_optimize_surplus,
            activation_key="surplus_potential",
            activation_threshold=0.8,
        ),
        latent=True,
    )

    # Latent CADENCE brake – activates when conflict is intense
    qpc.add_wave(
        Wave(
            name="CadenceBrake",
            wave_type=WaveType.TRANSITIONAL,
            role=WaveRole.CADENCE,
            amplitude=0.65,
            eval_fn=eval_cadence_deescalate,
            activation_key="conflict_intensity",
            activation_threshold=0.6,
        ),
        latent=True,
    )

    # Latent CALIBRATION refine – activates when uncertainty is high
    qpc.add_wave(
        Wave(
            name="CalibrationRefine",
            wave_type=WaveType.SUPERPOSITION,
            role=WaveRole.CALIBRATION,
            amplitude=0.55,
            eval_fn=eval_calibration_refine,
            activation_key="uncertainty_level",
            activation_threshold=0.5,
        ),
        latent=True,
    )

    return qpc


# ============================================================
# Alan / IQcore adapter (context in, action out)
# ============================================================


ACTION_REGISTRY: Dict[str, Dict[str, str]] = {
    # Safety / protection
    "protect": {"id": "ACT_PROTECT", "category": "safety", "fallback": "observe", "safety_override": "hard"},
    "halt_and_verify": {"id": "ACT_HALT_VERIFY", "category": "safety", "fallback": "protect", "safety_override": "hard"},
    # Revenue / surplus
    "optimize_surplus": {"id": "ACT_OPT_SURPLUS", "category": "revenue", "fallback": "observe", "safety_override": "soft"},
    "amplify_surplus": {"id": "ACT_AMP_SURPLUS", "category": "revenue", "fallback": "optimize_surplus", "safety_override": "soft"},
    # Cadence / interaction control
    "deescalate": {"id": "ACT_DEESCALATE", "category": "cadence", "fallback": "observe", "safety_override": "soft"},
    "slow_or_pause": {"id": "ACT_SLOW_PAUSE", "category": "cadence", "fallback": "deescalate", "safety_override": "soft"},
    # Calibration / signal gathering
    "gather_signal": {"id": "ACT_GATHER_SIGNAL", "category": "calibration", "fallback": "observe", "safety_override": "soft"},
    # Passive
    "observe": {"id": "ACT_OBSERVE", "category": "passive", "fallback": "none", "safety_override": "none"},
    "no_decision": {"id": "ACT_NONE", "category": "passive", "fallback": "observe", "safety_override": "none"},
}


ALAN_WAVE_ACTION_MAP: Dict[str, Dict[str, str]] = {
    "ProtectMerchant": {"action": "protect", "reason": "risk high"},
    "EthicalGuard": {"action": "halt_and_verify", "reason": "ethical guardrail"},
    "OptimizeSurplus": {"action": "optimize_surplus", "reason": "surplus opportunity"},
    "SurplusAmplifier": {"action": "amplify_surplus", "reason": "strong surplus signal"},
    "Deescalate": {"action": "deescalate", "reason": "conflict detected"},
    "CadenceBrake": {"action": "slow_or_pause", "reason": "high tension"},
    "CalibrationRefine": {"action": "gather_signal", "reason": "uncertainty high"},
    "ObserveOnly": {"action": "observe", "reason": "low signals"},
}


def map_alan_context_to_qpc(alan_ctx: Dict[str, Any]) -> Dict[str, float]:
    """Project Alan/IQcore signals into the QPC feature space, with normalization."""

    raw = {
        "risk_level": alan_ctx.get("risk_level", alan_ctx.get("risk_score", 0.0)),
        "surplus_potential": alan_ctx.get(
            "surplus_potential",
            alan_ctx.get("lifetime_value_delta", alan_ctx.get("opportunity", 0.0)),
        ),
        "conflict_intensity": alan_ctx.get(
            "conflict_intensity",
            alan_ctx.get("customer_tension", alan_ctx.get("friction_score", 0.0)),
        ),
        "uncertainty_level": alan_ctx.get(
            "uncertainty_level",
            alan_ctx.get("confidence_gap", alan_ctx.get("signal_gap", 0.0)),
        ),
    }

    return context_normalizer(raw)


def map_wave_to_alan_action(wave_name: Optional[str]) -> Dict[str, str]:
    """Translate a chosen wave into an Alan-facing action payload."""

    if wave_name is None:
        action = "no_decision"
        reason = "no active waves"
    else:
        mapping = ALAN_WAVE_ACTION_MAP.get(
            wave_name, {"action": "observe", "reason": "default fallback"}
        )
        action = mapping["action"]
        reason = mapping["reason"]

    reg = ACTION_REGISTRY.get(action, ACTION_REGISTRY["observe"])
    return {
        "action": action,
        "action_id": reg["id"],
        "category": reg["category"],
        "fallback": reg["fallback"],
        "safety_override": reg["safety_override"],
        "reason": reason,
    }


def alan_decision(reasoner: MultiWaveReasoner, alan_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """End-to-end adapter: Alan context -> QPC collapse -> Alan action."""

    qpc_context = map_alan_context_to_qpc(alan_ctx)
    result = reasoner.evaluate_context(qpc_context)
    result["alan_action"] = map_wave_to_alan_action(result.get("chosen_wave"))
    result["input_context"] = qpc_context
    if reasoner.drift_monitor is not None:
        result["drift_summary"] = reasoner.drift_monitor.summary()
    result["wave_health"] = wave_health_scan(reasoner.qpc, reasoner.drift_monitor)
    return result


# ============================================================
# Calibration / test harness
# ============================================================


def run_single_demo(reasoner: MultiWaveReasoner, context: Dict[str, Any]) -> None:
    """
    Run one evaluation with a given context and print the decision.
    """

    reasoner.qpc.visualize()
    result = reasoner.evaluate_context(context)
    print("[DECISION RESULT]")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("-" * 60)


def amplitude_tuner_test(iterations: int = 20) -> None:
    """
    Simple amplitude tuner: run multiple random contexts and observe
    which waves dominate over time.
    """

    qpc = build_sample_qpc()
    reasoner = MultiWaveReasoner(qpc=qpc)

    win_counts: Dict[str, int] = {}
    for i in range(iterations):
        context = {
            "risk_level": random.random(),
            "surplus_potential": random.random(),
            "conflict_intensity": random.random(),
            "uncertainty_level": random.random(),
        }
        print(f"\n=== ITERATION {i+1}/{iterations} ===")
        result = reasoner.evaluate_context(context)
        chosen = result["chosen_wave"]
        if chosen is not None:
            win_counts[chosen] = win_counts.get(chosen, 0) + 1

    print("\n[AMPLITUDE TUNER SUMMARY]")
    for name, count in win_counts.items():
        print(f"  {name:<18}: {count} wins")
    print()


def threshold_activation_test() -> None:
    """
    Show how latent waves become active as thresholds are crossed.
    """

    qpc = build_sample_qpc()
    reasoner = MultiWaveReasoner(qpc=qpc)

    contexts = [
        {
            "risk_level": 0.2,
            "surplus_potential": 0.2,
            "conflict_intensity": 0.2,
            "uncertainty_level": 0.2,
        },
        {
            "risk_level": 0.8,   # triggers EthicalGuard
            "surplus_potential": 0.2,
            "conflict_intensity": 0.2,
            "uncertainty_level": 0.2,
        },
        {
            "risk_level": 0.8,
            "surplus_potential": 0.85,  # triggers SurplusAmplifier
            "conflict_intensity": 0.7,  # triggers CadenceBrake
            "uncertainty_level": 0.6,   # triggers CalibrationRefine
        },
    ]

    for i, ctx in enumerate(contexts, start=1):
        print(f"\n=== THRESHOLD CONTEXT {i} ===")
        run_single_demo(reasoner, ctx)


def stability_stress_test(iterations: int = 1000) -> None:
    """
    Run many collapses to see distribution and detect drift / bias.
    """

    qpc = build_sample_qpc()
    reasoner = MultiWaveReasoner(qpc=qpc)

    win_counts: Dict[str, int] = {}
    for _ in range(iterations):
        context = {
            "risk_level": random.random(),
            "surplus_potential": random.random(),
            "conflict_intensity": random.random(),
            "uncertainty_level": random.random(),
        }
        result = reasoner.evaluate_context(context)
        chosen = result["chosen_wave"]
        if chosen is not None:
            win_counts[chosen] = win_counts.get(chosen, 0) + 1

    print("\n[STABILITY STRESS TEST]")
    print(f"Iterations: {iterations}")
    for name, count in sorted(win_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<18}: {count} ({count/iterations:6.3%})")
    print()


# ============================================================
# Confidence metric, health scan, context normalizer
# ============================================================


def compute_confidence(
    scores: Dict[Wave, float],
    trace: CollapseTrace,
    drift_monitor: Optional[DriftMonitor] = None,
) -> float:
    """Derive a simple confidence signal combining probs, amplitude spread, and drift."""

    if not scores:
        return 0.0

    # Probability sharpness
    probs = list(trace.normalized_probs.values())
    max_p = max(probs) if probs else 0.0
    # Entropy-based dispersion
    entropy = -sum(p * math.log(p + 1e-9) for p in probs) if probs else 0.0
    max_entropy = math.log(len(probs)) if probs else 1.0
    entropy_term = 1.0 - (entropy / max_entropy if max_entropy > 0 else 1.0)

    # Amplitude spread (favor concentrated amplitudes)
    amps = [w.amplitude for w in scores.keys()]
    amp_total = sum(amps) or 1.0
    amp_probs = [a / amp_total for a in amps]
    amp_entropy = -sum(p * math.log(p + 1e-9) for p in amp_probs)
    amp_entropy_term = 1.0 - (amp_entropy / math.log(len(amp_probs)) if len(amp_probs) > 1 else 0.0)

    # Drift stability (if available)
    drift_term = 1.0
    if drift_monitor and drift_monitor.total > 0:
        # Lower confidence if wins are overly concentrated
        freqs = list(drift_monitor.summary().values())
        drift_entropy = -sum(p * math.log(p + 1e-9) for p in freqs)
        drift_entropy_term = 1.0 - (
            drift_entropy / math.log(len(freqs)) if len(freqs) > 1 else 0.0
        )
        drift_term = 1.0 - 0.5 * drift_entropy_term

    # Blend terms (weighted average)
    confidence = (
        0.45 * max_p
        + 0.25 * entropy_term
        + 0.2 * amp_entropy_term
        + 0.1 * drift_term
    )
    return max(0.0, min(1.0, confidence))


def wave_health_scan(qpc: QPC, drift_monitor: Optional[DriftMonitor]) -> Dict[str, Any]:
    """Summarize which waves dominate, underuse, or never trigger."""

    active_names = [w.wave.name for w in qpc.variants if w.is_active() and w.wave]
    latent_names = [w.wave.name for w in qpc.variants if w.wave and w.latent]
    zero_amp = [w.wave.name for w in qpc.variants if w.wave and w.wave.amplitude == 0]

    drift = drift_monitor.summary() if drift_monitor else {}
    dominating = [n for n, freq in drift.items() if freq > 0.5]
    underused = [n for n, freq in drift.items() if freq < 0.05]

    never_triggered = [name for name in latent_names if name not in drift]

    return {
        "dominating": dominating,
        "underused": underused,
        "never_triggered": never_triggered,
        "zero_amplitude": zero_amp,
        "active_now": active_names,
        "latent_now": latent_names,
    }


def context_normalizer(raw: Dict[str, Any]) -> Dict[str, float]:
    """Normalize incoming raw signals to 0..1 space with simple clamping/scaling."""

    def norm(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 0.0
        if hi == lo:
            return 0.0
        return max(0.0, min(1.0, (v - lo) / (hi - lo)))

    return {
        "risk_level": norm(raw.get("risk_level", 0.0), 0.0, 1.0),
        "surplus_potential": norm(raw.get("surplus_potential", 0.0), -0.1, 1.0),
        "conflict_intensity": norm(raw.get("conflict_intensity", 0.0), 0.0, 1.0),
        "uncertainty_level": norm(raw.get("uncertainty_level", 0.0), 0.0, 1.0),
    }


# ============================================================
# Main entry: minimal runner
# ============================================================


if __name__ == "__main__":
    # Minimal manual demo (gated by debug mode to avoid noise in ops paths).
    if not get_debug_mode():
        # Quiet exit when debug is off.
        exit(0)

    print("\n=== QPC PROTOTYPE DEMO ===")
    qpc = build_sample_qpc()
    reasoner = MultiWaveReasoner(qpc=qpc, drift_monitor=DriftMonitor())

    demo_context = {
        "risk_level": 0.8,
        "surplus_potential": 0.6,
        "conflict_intensity": 0.3,
        "uncertainty_level": 0.4,
    }

    run_single_demo(reasoner, demo_context)

    # Uncomment to run additional tests (these obey the debug flag already):
    # amplitude_tuner_test(iterations=10)
    # threshold_activation_test()
    # stability_stress_test(iterations=100)
