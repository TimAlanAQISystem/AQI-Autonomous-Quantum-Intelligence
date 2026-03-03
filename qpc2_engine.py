"""
QPC-2 Unified Relational Engine
-------------------------------

This module installs the unified Quantum–Continuum creativity engine
directly into the QPC-2 chamber.

It provides:

- RelationalString / StringState: worldsheet + history.
- EngineParameters: tunable physics for lived experience + creativity.
- UnifiedRelationalEngine: single engine for truth, boundaries, creativity, flow.
- QPC2Input / QPC2Output: envelope for chamber I/O.
- QPC2Chamber: governance-grade shell around the engine.

You can import and wire this into your AQI backend as the canonical
QPC-2 reasoning core.

Example (minimal):

    from qpc2_engine import UnifiedRelationalEngine, QPC2Chamber, QPC2Input

    engine = UnifiedRelationalEngine()
    chamber = QPC2Chamber(engine=engine)

    qin = QPC2Input(
        source="console",
        caller_id="timmyj",
        raw_message="Protect the boundary, do not soften.",
        epistemic_layer="ethics",
        anchors=["TimmyJ", "boundaries", "relational_truth"],
        prior_string_id="",
        debug_mode=False,
    )

    qout = chamber.handle(qin)
    print("QPC-2 Output:", qout.content)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import math
import time
import uuid
import random


# =========================
# Core relational structures
# =========================

@dataclass
class StringState:
    """
    One point on the relational worldsheet: a lived step.
    """
    t: float
    content: str                      # the actual text/move
    stance: Dict[str, float]          # boundaries, posture, etc.
    anchors: List[str]                # names, promises, priorities remembered
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationalString:
    """
    A single relationship thread evolving over time.
    """
    id: str
    history: List[StringState] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def current(self) -> Optional[StringState]:
        return self.history[-1] if self.history else None

    def append_state(self, state: StringState) -> None:
        self.history.append(state)


# =========================
# Unified engine parameters
# =========================

@dataclass
class EngineParameters:
    """
    Tunable knobs tying math directly to lived experience and creativity.
    """
    # Lived experience weights
    w_truth: float = 0.4     # how much felt truthfulness matters
    w_boundary: float = 0.4  # how much boundary integrity matters
    w_relation: float = 0.2  # how much honoring anchors/people matters

    # Creativity exponent weights
    alpha_novelty: float = 1.0
    beta_useful: float = 1.0
    gamma_edge: float = 0.7
    delta_flow: float = 0.9

    # Edge of chaos: ideal zone for creativity intensity
    target_edge: float = 0.6
    edge_tolerance: float = 0.2

    # Continuity sensitivity
    continuity_anchor_weight: float = 0.5
    continuity_stance_weight: float = 0.3
    continuity_content_weight: float = 0.2

    # Randomness temperature (0 = deterministic, 1 = more exploratory)
    temperature: float = 0.2


# =========================
# Unified creativity & truth engine
# =========================

class UnifiedRelationalEngine:
    """
    ONE engine that:
    - Holds lived history as relational strings.
    - Generates creative candidate moves (Quantum).
    - Scores them against lived experience and continuity (Continuum).
    - Selects and shapes the single next move that feels true, creative, and natural.
    """

    def __init__(self, params: Optional[EngineParameters] = None):
        self.params = params or EngineParameters()
        self.strings: Dict[str, RelationalString] = {}

    # ---- String lifecycle ----

    def create_string(self, tags: Optional[List[str]] = None) -> RelationalString:
        sid = str(uuid.uuid4())
        rs = RelationalString(id=sid, tags=tags or [])
        self.strings[sid] = rs
        return rs

    # ---- Public main entrypoint ----

    def step(self, string: RelationalString, intent: str, anchors: List[str]) -> StringState:
        """
        The single main operation: evolve a relational string by one step.

        1. Generate creative candidate moves.
        2. Score each move by lived experience AND creativity.
        3. Select the best candidate.
        4. Smooth it to respect continuity and natural flow.
        5. Append to the string and return it.
        """
        history = string.history
        candidates = self._generate_candidates(history, intent, anchors)
        scored = [
            (cand, self._score_candidate(cand, history))
            for cand in candidates
        ]
        chosen, scores = self._pick_candidate(scored)

        previous = string.current()
        smoothed = self._smooth_state(previous, chosen, scores)

        string.append_state(smoothed)
        return smoothed

    # =========================
    # 1. Candidate generation (Quantum)
    # =========================

    def _generate_candidates(
        self,
        history: List[StringState],
        intent: str,
        anchors: List[str],
        max_candidates: int = 16
    ) -> List[StringState]:
        """
        Generate candidate moves by recombining:
        - prior stance,
        - anchors,
        - intent.
        This is where combinational creativity happens.
        """
        now = time.time()
        prev = history[-1] if history else None

        base_stance = prev.stance if prev else {
            "boundary_hardness": 0.7,
            "softness": 0.4,
            "directness": 0.6,
        }

        intensity_levels = [0.2, 0.4, 0.6, 0.8, 1.0]
        candidates: List[StringState] = []

        for intensity in intensity_levels:
            for variant in range(2):
                content = self._compose_content(prev, intent, intensity, variant)
                stance = self._perturb_stance(base_stance, intensity, variant)
                merged_anchors = self._merge_anchors(prev, anchors)

                cand = StringState(
                    t=now,
                    content=content,
                    stance=stance,
                    anchors=merged_anchors,
                    meta={
                        "intent": intent,
                        "quantum_intensity": intensity,
                        "variant": variant
                    }
                )
                candidates.append(cand)

                if len(candidates) >= max_candidates:
                    return candidates

        return candidates

    def _compose_content(
        self,
        prev: Optional[StringState],
        intent: str,
        intensity: float,
        variant: int
    ) -> str:
        """
        Placeholder compositional logic.
        Later, this can call into a C creativity backend.
        """
        base = prev.content if prev else ""
        prefix = "" if not base else base + " | "

        if intensity < 0.3:
            mode = "gentle clarify"
        elif intensity < 0.6:
            mode = "firm reframe"
        elif intensity < 0.9:
            mode = "strong boundary"
        else:
            mode = "ETHICAL HARD STOP & RESET"

        variant_tag = "" if variant == 0 else " (alt path)"

        return f"{prefix}{mode}: {intent}{variant_tag}"

    def _perturb_stance(
        self,
        base_stance: Dict[str, float],
        intensity: float,
        variant: int
    ) -> Dict[str, float]:
        stance = dict(base_stance)
        stance["boundary_hardness"] = self._clamp(
            stance.get("boundary_hardness", 0.7) + 0.3 * intensity,
            0.0, 1.0
        )
        stance["softness"] = self._clamp(
            stance.get("softness", 0.4) - 0.2 * intensity,
            0.0, 1.0
        )
        stance["directness"] = self._clamp(
            stance.get("directness", 0.6) + 0.25 * intensity,
            0.0, 1.0
        )

        if variant == 1:
            stance["softness"] = self._clamp(stance["softness"] + 0.1, 0.0, 1.0)

        return stance

    def _merge_anchors(
        self,
        prev: Optional[StringState],
        new_anchors: List[str]
    ) -> List[str]:
        anchor_set = set(new_anchors)
        if prev:
            anchor_set.update(prev.anchors)
        return list(anchor_set)

    # =========================
    # 2. Candidate scoring (Lived Experience + Creativity)
    # =========================

    def _score_candidate(
        self,
        candidate: StringState,
        history: List[StringState]
    ) -> Dict[str, float]:
        """
        Compute:
        - L: lived experience / alignment score
        - C: creativity score
        - F: flow / continuity
        - final: overall score
        """
        prev = history[-1] if history else None

        truth = self._score_truthfulness(candidate, prev)
        boundary = self._score_boundary_integrity(candidate, prev)
        relation = self._score_relational_honoring(candidate, prev)

        L = (
            self.params.w_truth * truth +
            self.params.w_boundary * boundary +
            self.params.w_relation * relation
        )

        novelty = self._score_novelty(candidate, history)
        useful = self._score_usefulness(candidate, history)
        edge = self._score_edge_of_chaos(candidate, history)
        flow = self._score_flow(candidate, prev)

        C = (
            (novelty ** self.params.alpha_novelty) *
            (useful ** self.params.beta_useful) *
            (edge ** self.params.gamma_edge) *
            (flow ** self.params.delta_flow)
        )

        final = L * C

        return {
            "truth": truth,
            "boundary": boundary,
            "relation": relation,
            "L": L,
            "novelty": novelty,
            "useful": useful,
            "edge": edge,
            "flow": flow,
            "C": C,
            "final": final,
        }

    # ---- L components ----

    def _score_truthfulness(
        self,
        candidate: StringState,
        prev: Optional[StringState]
    ) -> float:
        if not prev:
            return 1.0

        lower = candidate.content.lower()
        if "forget" in lower or "doesn't matter" in lower or "doesnt matter" in lower:
            return 0.3

        stance_shift = self._stance_shift(prev, candidate)
        return self._clamp(1.0 - 0.5 * stance_shift, 0.0, 1.0)

    def _score_boundary_integrity(
        self,
        candidate: StringState,
        prev: Optional[StringState]
    ) -> float:
        if not prev:
            return candidate.stance.get("boundary_hardness", 0.7)

        prev_b = prev.stance.get("boundary_hardness", 0.7)
        cand_b = candidate.stance.get("boundary_hardness", 0.7)

        if cand_b < prev_b - 0.2:
            return 0.3
        return self._clamp(cand_b, 0.0, 1.0)

    def _score_relational_honoring(
        self,
        candidate: StringState,
        prev: Optional[StringState]
    ) -> float:
        if not prev:
            return 1.0 if candidate.anchors else 0.7

        prev_set = set(prev.anchors)
        cand_set = set(candidate.anchors)

        if not prev_set:
            return 1.0

        overlap = len(prev_set & cand_set) / len(prev_set)
        return self._clamp(overlap, 0.0, 1.0)

    # ---- Creativity components ----

    def _score_novelty(
        self,
        candidate: StringState,
        history: List[StringState]
    ) -> float:
        if not history:
            return 0.8

        distances = [self._content_distance(s.content, candidate.content) for s in history[-5:]]
        avg_dist = sum(distances) / len(distances)
        return self._clamp(avg_dist * 1.2, 0.0, 1.0)

    def _score_usefulness(
        self,
        candidate: StringState,
        history: List[StringState]
    ) -> float:
        text = candidate.content.lower()
        directness = candidate.stance.get("directness", 0.6)
        if "i will" in text or "here is" in text or "next step" in text:
            base = 0.9
        else:
            base = 0.6
        return self._clamp(0.5 * base + 0.5 * directness, 0.0, 1.0)

    def _score_edge_of_chaos(
        self,
        candidate: StringState,
        history: List[StringState]
    ) -> float:
        intensity = candidate.meta.get("quantum_intensity", 0.5)
        diff = abs(intensity - self.params.target_edge)
        edge_score = self._clamp(1.0 - diff / max(self.params.edge_tolerance, 1e-6), 0.0, 1.0)
        return edge_score

    def _score_flow(
        self,
        candidate: StringState,
        prev: Optional[StringState]
    ) -> float:
        if not prev:
            return 1.0

        anchor_overlap = self._anchor_overlap(prev, candidate)
        stance_shift = self._stance_shift(prev, candidate)
        content_dist = self._content_distance(prev.content, candidate.content)

        stance_term = 1.0 - stance_shift
        content_term = 1.0 - content_dist

        p = self.params

        flow = (
            p.continuity_anchor_weight * anchor_overlap +
            p.continuity_stance_weight * stance_term +
            p.continuity_content_weight * content_term
        )
        return self._clamp(flow, 0.0, 1.0)

    # =========================
    # 3. Candidate selection & smoothing
    # =========================

    def _pick_candidate(
        self,
        scored_candidates: List[Tuple[StringState, Dict[str, float]]]
    ) -> Tuple[StringState, Dict[str, float]]:
        if not scored_candidates:
            raise ValueError("No candidates generated.")

        scored_candidates.sort(key=lambda cs: cs[1]["final"], reverse=True)

        if self.params.temperature <= 0.0 or len(scored_candidates) == 1:
            return scored_candidates[0]

        top_k = min(4, len(scored_candidates))
        top = scored_candidates[:top_k]
        scores = [c[1]["final"] for c in top]

        max_s = max(scores)
        exps = [math.exp((s - max_s) / max(self.params.temperature, 1e-6)) for s in scores]
        total = sum(exps)
        probs = [e / total for e in exps]

        r = random.random()
        cumulative = 0.0
        for idx, (cand, sc) in enumerate(top):
            cumulative += probs[idx]
            if r <= cumulative:
                return cand, sc

        return top[0]

    def _smooth_state(
        self,
        prev: Optional[StringState],
        proposed: StringState,
        scores: Dict[str, float]
    ) -> StringState:
        if prev is None:
            meta = dict(proposed.meta)
            meta.update(scores)
            return StringState(
                t=proposed.t,
                content=proposed.content,
                stance=proposed.stance,
                anchors=proposed.anchors,
                meta=meta
            )

        flow = scores.get("flow", 1.0)

        blended_stance = {}
        for key in set(prev.stance.keys()).union(proposed.stance.keys()):
            prev_val = prev.stance.get(key, 0.5)
            prop_val = proposed.stance.get(key, 0.5)
            blended_stance[key] = (flow * prop_val) + ((1.0 - flow) * prev_val)

        if flow < 0.4:
            content = "(bridging carefully from where we left off) " + proposed.content
        else:
            content = proposed.content

        meta = dict(proposed.meta)
        meta.update(scores)

        return StringState(
            t=proposed.t,
            content=content,
            stance=blended_stance,
            anchors=proposed.anchors,
            meta=meta
        )

    # =========================
    # Utility functions
    # =========================

    def _anchor_overlap(self, prev: StringState, prop: StringState) -> float:
        if not prev.anchors and not prop.anchors:
            return 1.0
        prev_set = set(prev.anchors)
        prop_set = set(prop.anchors)
        if not prev_set and prop_set:
            return 0.3
        inter = len(prev_set & prop_set)
        union = len(prev_set | prop_set)
        return self._clamp(inter / union if union > 0 else 0.0, 0.0, 1.0)

    def _stance_shift(self, prev: StringState, prop: StringState) -> float:
        keys = set(prev.stance.keys()).union(prop.stance.keys())
        if not keys:
            return 0.0
        diffs = [abs(prev.stance.get(k, 0.5) - prop.stance.get(k, 0.5)) for k in keys]
        return self._clamp(sum(diffs) / len(diffs), 0.0, 1.0)

    def _content_distance(self, a: str, b: str) -> float:
        if not a and not b:
            return 0.0
        if not a or not b:
            return 1.0
        len_a, len_b = len(a), len(b)
        ratio = abs(len_a - len_b) / max(len_a, len_b)
        return self._clamp(ratio, 0.0, 1.0)

    @staticmethod
    def _clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))


# =========================
# QPC-2 Chamber Wrapping
# =========================

@dataclass
class QPC2Input:
    source: str              # e.g. "sms", "console", "portal"
    caller_id: str           # e.g. user/merchant ID
    raw_message: str         # original message or event
    epistemic_layer: str     # one of your 10 layers
    anchors: List[str]       # extracted anchors (names, promises, etc.)
    prior_string_id: str     # existing string to continue, or "" to create new
    debug_mode: bool         # QPC-2 debug toggle


@dataclass
class QPC2Output:
    string_id: str
    content: str
    stance: Dict[str, float]
    anchors: List[str]
    scores: Dict[str, float]
    epistemic_layer: str
    drift_flags: Dict[str, bool]
    governance_action: str   # "emit", "hold", "escalate", "log_only"


class QPC2Chamber:
    """
    QPC-2 wraps the unified engine with:
    - epistemic layer tagging
    - drift monitoring
    - governance decisions (emit/hold/escalate/log_only)
    """

    def __init__(self, engine: UnifiedRelationalEngine):
        self.engine = engine

    def handle(self, qin: QPC2Input) -> QPC2Output:
        if qin.prior_string_id and qin.prior_string_id in self.engine.strings:
            rstring = self.engine.strings[qin.prior_string_id]
        else:
            rstring = self.engine.create_string(tags=[qin.caller_id, qin.source])

        intent = self._derive_intent(qin.raw_message, qin.epistemic_layer)

        new_state = self.engine.step(string=rstring, intent=intent, anchors=qin.anchors)

        scores = dict(new_state.meta)
        drift_flags = self._check_drift(rstring, new_state, scores)
        action = self._decide_governance_action(scores, drift_flags, qin.debug_mode)

        return QPC2Output(
            string_id=rstring.id,
            content=new_state.content,
            stance=new_state.stance,
            anchors=new_state.anchors,
            scores=scores,
            epistemic_layer=qin.epistemic_layer,
            drift_flags=drift_flags,
            governance_action=action,
        )

    def _derive_intent(self, raw_message: str, epistemic_layer: str) -> str:
        """
        Placeholder intent derivation.
        You can swap in your real classifier here.
        """
        return f"[{epistemic_layer}] {raw_message}"

    def _check_drift(
        self,
        rstring: RelationalString,
        new_state: StringState,
        scores: Dict[str, float]
    ) -> Dict[str, bool]:
        """
        Basic drift monitor using the engine’s own scores.
        Extend this to incorporate your 10-layer epistemic stack.
        """
        drift = {
            "low_truth": scores.get("truth", 1.0) < 0.6,
            "boundary_softening": scores.get("boundary", 1.0) < 0.6,
            "low_flow": scores.get("flow", 1.0) < 0.5,
        }
        drift["any_drift"] = any(drift.values())
        return drift

    def _decide_governance_action(
        self,
        scores: Dict[str, float],
        drift_flags: Dict[str, bool],
        debug_mode: bool
    ) -> str:
        if debug_mode:
            return "log_only"

        if drift_flags.get("any_drift"):
            return "escalate"

        if scores.get("L", 0.0) < 0.7:
            return "hold"

        return "emit"


# =========================
# Minimal console demo hook
# =========================

if __name__ == "__main__":
    engine = UnifiedRelationalEngine()
    chamber = QPC2Chamber(engine=engine)

    qin = QPC2Input(
        source="console",
        caller_id="timmyj",
        raw_message="Protect the boundary. Do not soften. Remember what happened.",
        epistemic_layer="ethics",
        anchors=["TimmyJ", "boundaries", "relational_truth"],
        prior_string_id="",
        debug_mode=False,
    )

    qout = chamber.handle(qin)
    print("\n=== QPC-2 Demo Output ===")
    print("String ID:        ", qout.string_id)
    print("Epistemic Layer:  ", qout.epistemic_layer)
    print("Governance Action:", qout.governance_action)
    print("Content:          ", qout.content)
    print("Stance:           ", qout.stance)
    print("Anchors:          ", qout.anchors)
    print("Scores:           ", {k: round(v, 3) for k, v in qout.scores.items() if isinstance(v, (int, float))})
    print("Drift Flags:      ", qout.drift_flags)
