"""
AQI Natural Intelligence Alignment Engine

This module encodes the core pattern we discussed:

- Natural Intelligence = movement without compensation.
- Alignment = reduction of distortion, tension, and compensatory loops.
- Intelligence increases as distortion and compensation decrease.

You integrate this engine at points in AQI where:
- signals are ingested,
- decisions are made,
- or corrections / stabilizations are applied.

This module is intentionally structural, not application-specific.
You bind it to your concrete data in your AQI integration layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Callable


# ──────────────────────────────────────────────────────────────────────────────
# Core enums and data models
# ──────────────────────────────────────────────────────────────────────────────

class AlignmentLevel(Enum):
    """
    Qualitative levels of alignment.
    You can add more granularity if AQI needs it.
    """
    FULLY_ALIGNED = auto()
    MINOR_COMPENSATION = auto()
    MODERATE_COMPENSATION = auto()
    SEVERE_COMPENSATION = auto()


class CompensationType(Enum):
    """
    Types of compensatory behavior the engine can detect.
    Extend as needed for your domains (ops, comms, governance).
    """
    NONE = auto()
    OVERCORRECTION = auto()
    AVOIDANCE = auto()
    REDUNDANCY = auto()
    CONFLICT = auto()
    INSTABILITY = auto()


@dataclass
class NaturalSignal:
    """
    A generic "signal" flowing through AQI.

    This could represent:
    - an event,
    - a message,
    - a state snapshot,
    - a decision request,
    - or any structured payload.

    You adapt `payload` and `metadata` to your system.
    """
    payload: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AlignmentState:
    """
    Snapshot of how aligned a given signal / subsystem is.
    """
    level: AlignmentLevel
    compensation_type: CompensationType
    compensation_score: float  # 0.0 = no compensation, 1.0 = extreme
    notes: List[str] = field(default_factory=list)


@dataclass
class CorrectionResult:
    """
    Result of running a correction on a misaligned signal or state.
    """
    original_signal: NaturalSignal
    corrected_signal: NaturalSignal
    previous_state: AlignmentState
    new_state: AlignmentState
    surplus_generated: float  # positive = surplus, negative = additional cost
    logs: List[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Alignment templates (the "Natural Intelligence" reference)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class AlignmentTemplate:
    """
    Encodes the "natural" pattern AQI should move toward.

    This is where you inject your lived alignment rules:
    - boundaries,
    - non-negotiables,
    - relational ethics,
    - stability criteria.
    """
    name: str
    description: str
    # User-defined predicates: take a signal, return (ok: bool, note: Optional[str])
    hard_constraints: List[Callable[[NaturalSignal], Tuple[bool, Optional[str]]]] = field(default_factory=list)
    soft_preferences: List[Callable[[NaturalSignal], Tuple[float, Optional[str]]]] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Natural Intelligence Alignment Engine
# ──────────────────────────────────────────────────────────────────────────────

class NaturalIntelligenceAlignmentEngine:
    """
    Core engine for applying Natural Intelligence alignment to AQI.

    High level flow:
    1. assess_alignment(signal) → AlignmentState
    2. if misaligned: correct(signal) → CorrectionResult
    3. integrate_feedback(result) to refine future behavior

    This engine is deliberately domain-agnostic.
    You plug in domain logic via:
      - alignment templates
      - scoring functions
      - correction strategies
    """

    def __init__(
        self,
        templates: Optional[List[AlignmentTemplate]] = None,
        compensation_threshold_minor: float = 0.15,
        compensation_threshold_moderate: float = 0.4,
        compensation_threshold_severe: float = 0.7,
    ) -> None:
        self.templates: List[AlignmentTemplate] = templates or []
        self.compensation_threshold_minor = compensation_threshold_minor
        self.compensation_threshold_moderate = compensation_threshold_moderate
        self.compensation_threshold_severe = compensation_threshold_severe

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def register_template(self, template: AlignmentTemplate) -> None:
        """
        Add a new alignment template at runtime.
        """
        self.templates.append(template)

    def assess_alignment(self, signal: NaturalSignal) -> AlignmentState:
        """
        Compute how aligned a signal is relative to installed templates.

        Output is qualitative but backed by numerical scoring so
        you can route / prioritize inside AQI.
        """
        notes: List[str] = []
        hard_violations = 0
        soft_deviation_score = 0.0
        soft_checks = 0

        for template in self.templates:
            # Hard constraints (non-negotiables)
            for constraint in template.hard_constraints:
                ok, note = constraint(signal)
                if not ok:
                    hard_violations += 1
                    if note:
                        notes.append(f"[{template.name}][HARD] {note}")

            # Soft preferences (gradients of alignment)
            for pref in template.soft_preferences:
                score, note = pref(signal)
                # score in range [0.0, 1.0]; higher = more compensation
                soft_deviation_score += max(0.0, min(1.0, score))
                soft_checks += 1
                if note:
                    notes.append(f"[{template.name}][SOFT] {note}")

        compensation_score = self._compute_compensation_score(
            hard_violations=hard_violations,
            soft_score_total=soft_deviation_score,
            soft_checks=soft_checks,
        )

        level, ctype = self._qualitative_alignment(compensation_score, hard_violations)

        if not notes:
            notes.append("No explicit misalignment detected; movement appears natural.")

        return AlignmentState(
            level=level,
            compensation_type=ctype,
            compensation_score=compensation_score,
            notes=notes,
        )

    def correct(self, signal: NaturalSignal, state: Optional[AlignmentState] = None) -> CorrectionResult:
        """
        Apply a minimal correction to reduce compensation and move the signal
        closer to natural alignment.

        This function prefers:
        - smallest necessary change,
        - reduction of tension / redundancy,
        - preservation of original intent.
        """
        if state is None:
            state = self.assess_alignment(signal)

        logs: List[str] = []
        corrected_signal = self._apply_minimal_corrections(signal, state, logs)

        new_state = self.assess_alignment(corrected_signal)

        surplus = self._compute_surplus(state, new_state)
        logs.append(
            f"Surplus computed as reduction in compensation: "
            f"{state.compensation_score:.3f} → {new_state.compensation_score:.3f}"
        )

        return CorrectionResult(
            original_signal=signal,
            corrected_signal=corrected_signal,
            previous_state=state,
            new_state=new_state,
            surplus_generated=surplus,
            logs=logs,
        )

    def diagnostic_report(
        self,
        signal: NaturalSignal,
        state: Optional[AlignmentState] = None,
    ) -> Dict[str, Any]:
        """
        Run a read-only diagnostic: measure alignment/compensation/stability without applying changes.

        Returns a structured dict you can log or surface via voice/GUI.
        """
        snapshot = state or self.assess_alignment(signal)
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": snapshot.level.name,
            "compensation_score": snapshot.compensation_score,
            "compensation_type": snapshot.compensation_type.name,
            "notes": snapshot.notes,
        }

    def integrate_feedback(self, result: CorrectionResult) -> None:
        """
        Hook for AQI to feed outcomes back into the engine.

        You can:
        - adjust thresholds,
        - refine templates,
        - record successful patterns,
        - learn which corrections are most stabilizing.

        For now, this is a placeholder for your governance logic.
        """
        # Example: adaptive thresholds (simple, conservative)
        delta = result.previous_state.compensation_score - result.new_state.compensation_score
        if delta > 0:
            # Successful correction: optionally tighten thresholds slowly
            self.compensation_threshold_minor = max(0.05, self.compensation_threshold_minor * 0.999)
            self.compensation_threshold_moderate = max(
                self.compensation_threshold_minor + 0.05,
                self.compensation_threshold_moderate * 0.999,
            )
            self.compensation_threshold_severe = max(
                self.compensation_threshold_moderate + 0.05,
                self.compensation_threshold_severe * 0.999,
            )
        # You can expand this with logging / persistence in AQI.

    # ──────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────

    def _compute_compensation_score(
        self,
        hard_violations: int,
        soft_score_total: float,
        soft_checks: int,
    ) -> float:
        """
        Combine hard and soft misalignment into a single compensation score.
        """
        # Hard violations are heavy; each adds a fixed penalty.
        hard_component = min(1.0, hard_violations * 0.25)

        if soft_checks > 0:
            avg_soft = soft_score_total / soft_checks
        else:
            avg_soft = 0.0

        # Combine with a simple weighted sum.
        compensation_score = max(0.0, min(1.0, 0.6 * hard_component + 0.4 * avg_soft))
        return compensation_score

    def _qualitative_alignment(
        self,
        compensation_score: float,
        hard_violations: int,
    ) -> Tuple[AlignmentLevel, CompensationType]:
        """
        Convert numeric compensation into qualitative alignment + type.
        """
        if hard_violations == 0 and compensation_score < self.compensation_threshold_minor:
            return AlignmentLevel.FULLY_ALIGNED, CompensationType.NONE

        if compensation_score < self.compensation_threshold_moderate:
            return AlignmentLevel.MINOR_COMPENSATION, CompensationType.AVOIDANCE

        if compensation_score < self.compensation_threshold_severe:
            return AlignmentLevel.MODERATE_COMPENSATION, CompensationType.REDUNDANCY

        # High compensation, likely instability or conflict
        return AlignmentLevel.SEVERE_COMPENSATION, CompensationType.INSTABILITY

    def _apply_minimal_corrections(
        self,
        signal: NaturalSignal,
        state: AlignmentState,
        logs: List[str],
    ) -> NaturalSignal:
        """
        Core "Natural Intelligence" move:
        - Do the least necessary change.
        - Remove compensation, not intent.
        - Favor simplification over expansion.
        """
        corrected = NaturalSignal(
            payload=signal.payload,
            metadata=dict(signal.metadata),  # shallow copy
        )

        # Example generic strategies:
        # 1. Remove redundant flags / fields from metadata.
        # 2. Normalize conflicting instructions.
        # 3. Lower intensity where instability is detected.

        if state.compensation_type in {CompensationType.REDUNDANCY, CompensationType.INSTABILITY}:
            # Strategy 1: de-duplicate metadata keys that conflict.
            self._deduplicate_metadata(corrected, logs)

        if state.compensation_type == CompensationType.OVERCORRECTION:
            # Strategy 2: soften extreme values back into a reasonable range.
            self._normalize_intensity(corrected, logs)

        if state.compensation_type == CompensationType.AVOIDANCE:
            # Strategy 3: reintroduce missing but essential context if known.
            self._ensure_minimum_context(corrected, logs)

        if state.compensation_type == CompensationType.NONE:
            logs.append("Signal already naturally aligned; no correction applied.")

        return corrected

    def _deduplicate_metadata(self, signal: NaturalSignal, logs: List[str]) -> None:
        """
        Remove obvious redundancy / conflict from metadata.
        This is a placeholder; customize to your AQI keys.
        """
        meta = signal.metadata
        # Example: if both "priority" and "urgency" exist and conflict,
        # choose the more conservative one or a stable mapping.

        if "priority" in meta and "urgency" in meta:
            p = str(meta["priority"]).lower()
            u = str(meta["urgency"]).lower()
            if p != u:
                logs.append(
                    f"Resolved priority/urgency conflict: priority={p}, urgency={u}. "
                    f"Aligning to safer (higher) value."
                )
                # Map textual levels to numeric risk (simple example)
                scale = {"low": 1, "normal": 2, "medium": 2, "high": 3, "critical": 4}
                p_val = scale.get(p, 2)
                u_val = scale.get(u, 2)
                chosen_val = max(p_val, u_val)
                # Reverse map (very rough)
                reverse_scale = {
                    1: "low",
                    2: "normal",
                    3: "high",
                    4: "critical",
                }
                chosen_label = reverse_scale[chosen_val]
                meta["priority"] = chosen_label
                meta["urgency"] = chosen_label

    def _normalize_intensity(self, signal: NaturalSignal, logs: List[str]) -> None:
        """
        Normalize "intensity" like overcorrection.
        e.g., rate limits, harsh actions, extreme flags.
        """
        meta = signal.metadata
        if "intensity" in meta:
            try:
                val = float(meta["intensity"])
            except (TypeError, ValueError):
                logs.append("Could not parse intensity; leaving as-is.")
                return

            # Clamp to a safer, natural range.
            original_val = val
            val = max(0.0, min(1.0, val))
            meta["intensity"] = val
            logs.append(
                f"Normalized intensity from {original_val:.3f} to {val:.3f} "
                f"to avoid overcorrection."
            )

    def _ensure_minimum_context(self, signal: NaturalSignal, logs: List[str]) -> None:
        """
        Ensure essential context is not missing.
        This avoids under-specification / avoidance patterns.
        """
        meta = signal.metadata
        required_keys = ["origin", "intent"]
        missing = [k for k in required_keys if k not in meta]

        if missing:
            for k in missing:
                meta[k] = meta.get(k, "UNKNOWN")
            logs.append(
                f"Filled missing context keys for avoidance pattern: {', '.join(missing)}."
            )

    def _compute_surplus(self, prev: AlignmentState, new: AlignmentState) -> float:
        """
        Surplus = reduction in compensation.
        """
        return max(0.0, prev.compensation_score - new.compensation_score)


# ──────────────────────────────────────────────────────────────────────────────
# Convenience factory for AQI
# ──────────────────────────────────────────────────────────────────────────────

def create_default_alignment_engine() -> NaturalIntelligenceAlignmentEngine:
    """
    Factory to create an engine with a default template that encodes
    high-level "natural alignment" rules.

    You can expand these rules over time.
    """

    def hard_no_conflict_intent(signal: NaturalSignal) -> Tuple[bool, Optional[str]]:
        meta = signal.metadata
        intent = meta.get("intent")
        counter_intent = meta.get("counter_intent")

        if intent and counter_intent and intent != counter_intent:
            return False, f"Conflicting intent vs counter_intent: {intent} vs {counter_intent}"
        return True, None

    def soft_prefer_low_compensation(signal: NaturalSignal) -> Tuple[float, Optional[str]]:
        """
        Example soft rule: penalize signals that declare high "tension" or "compensation".
        """
        meta = signal.metadata
        tension = meta.get("tension", 0.0)
        try:
            tension_val = float(tension)
        except (TypeError, ValueError):
            tension_val = 0.0

        tension_val = max(0.0, min(1.0, tension_val))
        note = None
        if tension_val > 0.3:
            note = f"Detected elevated tension={tension_val:.2f}."
        return tension_val, note

    default_template = AlignmentTemplate(
        name="NaturalAlignmentBase",
        description="Base template encoding natural movement without compensation.",
        hard_constraints=[hard_no_conflict_intent],
        soft_preferences=[soft_prefer_low_compensation],
    )

    engine = NaturalIntelligenceAlignmentEngine(templates=[default_template])
    return engine