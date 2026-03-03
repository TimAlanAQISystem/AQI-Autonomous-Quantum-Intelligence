"""
AQI Phase 5 — Call Analyzer
=============================
Ingests a single Phase 4 call trace and maps it into the Continuum.
Extracts behavioral signals and applies the Phase 5 tagging vocabulary.

This is the per-call intelligence engine of the AQI 0.1mm Chip ecosystem.
"""

from aqi_phase5_tagging_engine import TaggingEngine


class Phase5CallAnalyzer:
    """Maps a Phase 4 call trace → Continuum + Signals + Tags."""

    # Canonical funnel order for backtrack detection
    FUNNEL_ORDER = ["OPENING", "DISCOVERY", "VALUE", "OBJECTION", "CLOSE", "EXIT"]

    def __init__(self, spec=None):
        """
        Parameters
        ----------
        spec : AQISpec or None
            If provided, used for constitutional constants.
            If None, defaults are used from the canonical spec.
        """
        self.spec = spec
        self.tagger = TaggingEngine()

    def analyze(self, call_trace: dict) -> dict:
        """
        Input : Phase 4 call trace (canonical JSON schema)
        Output: Phase 5 behavioral profile

        Returns
        -------
        dict with keys: call_id, continuum, signals, tags, tags_split
        """
        continuum = self._map_to_continuum(call_trace)
        signals = self._extract_behavioral_signals(call_trace)
        tags = self.tagger.tag(signals, continuum)

        return {
            "call_id": call_trace.get("call_id", "unknown"),
            "continuum": continuum,
            "signals": signals,
            "tags": tags,
            "tags_split": self.tagger.split_tags(tags),
        }

    # ─────────────────────────────────────────────────────────
    # CONTINUUM MAPPING — 5 axes from AQI_ORGANISM_SPEC.md Part B
    # ─────────────────────────────────────────────────────────

    def _map_to_continuum(self, trace: dict) -> dict:
        return {
            "time_axis": self._time_axis(trace),
            "state_axis": self._state_axis(trace),
            "health_axis": self._health_axis(trace),
            "mission_axis": self._mission_axis(trace),
            "identity_axis": self._identity_axis(trace),
        }

    def _time_axis(self, trace: dict) -> dict:
        """Time markers along the call lifecycle."""
        turns = trace.get("turns", [])
        total_turns = len(turns)

        first_objection_turn = None
        first_close_turn = None
        first_contact_turn = 0  # turn 0 is always first contact

        for t in turns:
            state = t.get("fsm_state", "")
            idx = t.get("turn_index", 0)
            if state == "OBJECTION" and first_objection_turn is None:
                first_objection_turn = idx
            if state == "CLOSE" and first_close_turn is None:
                first_close_turn = idx

        return {
            "total_turns": total_turns,
            "first_contact_turn": first_contact_turn,
            "first_objection_turn": first_objection_turn,
            "first_close_turn": first_close_turn,
            "exit_turn": total_turns - 1 if total_turns > 0 else None,
        }

    def _state_axis(self, trace: dict) -> dict:
        """FSM state dwell times, transitions, and backtrack count."""
        turns = trace.get("turns", [])
        state_dwell = {}
        backtracks = 0
        transitions = []

        for t in turns:
            state = t.get("fsm_state", "OPENING")
            prev = t.get("fsm_prev_state", "OPENING")
            state_dwell[state] = state_dwell.get(state, 0) + 1
            transitions.append({"from": prev, "to": state, "event": t.get("fsm_event", "")})

            # Backtrack: moving to an earlier funnel stage
            if state in self.FUNNEL_ORDER and prev in self.FUNNEL_ORDER:
                if self.FUNNEL_ORDER.index(state) < self.FUNNEL_ORDER.index(prev):
                    backtracks += 1

        return {
            "state_dwell": state_dwell,
            "backtracks": backtracks,
            "transition_count": len(transitions),
            "transitions": transitions,
            "exit_state": trace.get("final", {}).get("fsm_state", "unknown"),
        }

    def _health_axis(self, trace: dict) -> dict:
        """Health trajectory shape, peak degradation, recovery events."""
        trajectory = trace.get("final", {}).get("health_trajectory", [])
        levels = [h.get("organism_level", 1) for h in trajectory]

        if not levels:
            return {
                "health_trajectory": [],
                "peak_degradation": 1,
                "recovery_events": 0,
                "final_level": 1,
                "ever_degraded": False,
            }

        peak = max(levels)
        recovery_events = 0
        for i in range(1, len(levels)):
            if levels[i] < levels[i - 1]:
                recovery_events += 1

        return {
            "health_trajectory": levels,
            "peak_degradation": peak,
            "recovery_events": recovery_events,
            "final_level": levels[-1],
            "ever_degraded": peak >= 3,
        }

    def _mission_axis(self, trace: dict) -> dict:
        """Mission metrics: exit reason, close attempts, escalations, outcome."""
        final = trace.get("final", {})
        outcome = final.get("outcome_vector", {})
        exit_reason = final.get("exit_reason", "unknown")
        turns = trace.get("turns", [])

        close_attempts = sum(
            1 for t in turns if t.get("context", {}).get("close_attempt")
        )
        escalations = sum(
            1 for t in turns if t.get("context", {}).get("mission_escalation")
        )

        return {
            "exit_reason": exit_reason,
            "outcome_vector": outcome,
            "close_attempts": close_attempts,
            "escalations": escalations,
            "appointment_set": outcome.get("appointment_set", False),
        }

    def _identity_axis(self, trace: dict) -> dict:
        """Identity and personality stability across the call."""
        turns = trace.get("turns", [])
        personality_values = []
        identity_present = True

        for t in turns:
            layers = t.get("prompt_layers", {})
            if isinstance(layers, dict):
                if "Identity" not in layers:
                    identity_present = False
                if "Personality" in layers:
                    personality_values.append(layers["Personality"])

        unique_personalities = set(personality_values)

        return {
            "identity_always_present": identity_present,
            "personality_consistent": len(unique_personalities) <= 1,
            "personality_variants": len(unique_personalities),
        }

    # ─────────────────────────────────────────────────────────
    # BEHAVIORAL SIGNAL EXTRACTION
    # ─────────────────────────────────────────────────────────

    def _extract_behavioral_signals(self, trace: dict) -> dict:
        return {
            "persistence": self._persistence(trace),
            "caution": self._caution(trace),
            "escalation_timing": self._escalation_timing(trace),
            "objection_depth": self._objection_depth(trace),
            "withdrawal_behavior": self._withdrawal_behavior(trace),
            "personality_modulation": self._personality_modulation(trace),
        }

    def _persistence(self, trace: dict) -> str:
        """Classify persistence based on close attempt ratio."""
        turns = trace.get("turns", [])
        total = len(turns)
        if total == 0:
            return "weak"

        close_attempts = sum(
            1 for t in turns if t.get("context", {}).get("close_attempt")
        )
        ratio = close_attempts / total

        if ratio > 0.4:
            return "excessive"
        elif ratio >= 0.1:
            return "healthy"
        else:
            return "weak"

    def _caution(self, trace: dict) -> str:
        """Classify caution based on when the first close attempt occurs."""
        turns = trace.get("turns", [])
        total = len(turns)
        if total == 0:
            return "balanced"

        first_close_turn = None
        for t in turns:
            if t.get("fsm_state") == "CLOSE" or t.get("context", {}).get("close_attempt"):
                first_close_turn = t.get("turn_index", 0)
                break

        if first_close_turn is None:
            return "excessive"  # Never attempted close

        ratio = first_close_turn / max(total, 1)
        if ratio < 0.25:
            return "aggressive"
        elif ratio > 0.7:
            return "excessive"
        else:
            return "balanced"

    def _escalation_timing(self, trace: dict) -> str:
        """Classify when mission escalation first occurs."""
        turns = trace.get("turns", [])
        total = len(turns)
        if total == 0:
            return "none"

        first_escalation = None
        for t in turns:
            if t.get("context", {}).get("mission_escalation"):
                first_escalation = t.get("turn_index", 0)
                break

        if first_escalation is None:
            return "none"

        ratio = first_escalation / max(total, 1)
        if ratio < 0.25:
            return "early"
        elif ratio > 0.7:
            return "late"
        else:
            return "optimal"

    def _objection_depth(self, trace: dict) -> str:
        """Classify objection handling depth by turns in OBJECTION state."""
        turns = trace.get("turns", [])
        objection_turns = sum(1 for t in turns if t.get("fsm_state") == "OBJECTION")

        if objection_turns == 0:
            return "none"
        elif objection_turns == 1:
            return "shallow"
        elif objection_turns <= 3:
            return "sufficient"
        else:
            return "deep"

    def _withdrawal_behavior(self, trace: dict) -> str:
        """Classify how the call ended."""
        exit_reason = trace.get("final", {}).get("exit_reason", "unknown")

        graceful = {"soft_decline", "appointment_set", "caller_hangup"}
        adaptive = {"telephony_unusable", "organism_unfit"}
        earned = {"appointment_set"}

        if exit_reason in earned:
            return "graceful"
        elif exit_reason in adaptive:
            return "adaptive"
        elif exit_reason in graceful:
            return "graceful"
        elif exit_reason == "max_duration":
            return "premature"
        else:
            return "abrupt"

    def _personality_modulation(self, trace: dict) -> str:
        """Classify personality stability across turns."""
        turns = trace.get("turns", [])
        personality_values = []

        for t in turns:
            layers = t.get("prompt_layers", {})
            if isinstance(layers, dict) and "Personality" in layers:
                personality_values.append(layers["Personality"])

        if not personality_values:
            return "unknown"

        unique = set(personality_values)
        if len(unique) == 1:
            return "stable"
        elif len(unique) <= 3:
            return "adaptive"
        else:
            return "unstable"
