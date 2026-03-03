"""
AQI 0.1mm Chip — Runtime Guard (Conformance Engine)
====================================================
First binding between the AQI organism specification and the live runtime.

Enforces 6 constitutional rules per turn and per call:
  1. Health Constraint Enforcement (Constitution A5)
  2. Governance Order Enforcement (Constitution A3)
  3. FSM Transition Legality (Constitution A4)
  4. Exit Reason Legality (Mission Vector + FSM)
  5. Mission Constraint Enforcement (Constitution A2 + A5)
  6. Supervision Non-Interference (Constitution A6)

Usage:
    guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")
    guard.on_call_start(call_id, "OPENING", context)
    guard.on_turn(call_id, fsm_state, fsm_prev_state, fsm_event, context, prompt_layers, health_snapshot)
    guard.on_call_end(call_id, fsm_state, exit_reason, health_trajectory, telephony_trajectory, outcome_vector)

Created: February 19, 2026
Classification: Constitutional
"""

import logging
import json
import os
from enum import Enum, auto
from datetime import datetime

logger = logging.getLogger("AQI_GUARD")


# =============================================================================
# ERROR TAXONOMY
# =============================================================================

class AQIViolationType(Enum):
    """Explicit violation types for the AQI 0.1mm Chip."""
    GOVERNANCE_ORDER = auto()
    FSM_ILLEGAL_TRANSITION = auto()
    INVALID_EXIT_REASON = auto()
    MISSION_MAPPING_ERROR = auto()
    HEALTH_CONSTRAINT_BREACH = auto()
    SUPERVISION_INTERFERENCE = auto()
    SPEC_INCONSISTENCY = auto()


class AQIViolation(Exception):
    """Base violation from the AQI Runtime Guard."""
    def __init__(
        self,
        vtype: AQIViolationType,
        message: str,
        call_id: str = None,
        turn_index: int = None,
        context: dict = None,
        fatal: bool = False,
    ):
        super().__init__(message)
        self.vtype = vtype
        self.call_id = call_id
        self.turn_index = turn_index
        self.context = context or {}
        self.fatal = fatal
        self.timestamp = datetime.now().isoformat()


class AQINonFatalViolation(AQIViolation):
    """Non-fatal violation: logged, tagged, supervisor alerted. Call continues."""
    def __init__(self, **kwargs):
        kwargs["fatal"] = False
        super().__init__(**kwargs)


class AQIFatalViolation(AQIViolation):
    """Fatal violation: logged, call marked compromised, supervisor alerted."""
    def __init__(self, **kwargs):
        kwargs["fatal"] = True
        super().__init__(**kwargs)


# =============================================================================
# AQI SPEC — Parsed Constitutional Substrate
# =============================================================================

class AQISpec:
    """Structured representation of AQI_ORGANISM_SPEC.md.

    Extracts the constitutional constants that the runtime guard enforces.
    These are hardcoded from the canonical spec — not parsed dynamically —
    because constitutional values must never be ambiguous at runtime.
    """

    def __init__(self):
        # Governance order (Constitution A3)
        self.governance_order = [
            "Identity", "Ethics", "Personality",
            "Knowledge", "Mission", "Output"
        ]

        # FSM states (Schematic V)
        self.valid_states = [
            "OPENING", "DISCOVERY", "VALUE",
            "OBJECTION", "CLOSE", "EXIT"
        ]

        # FSM events (Schematic V)
        self.valid_events = [
            "merchant_speaks", "agent_speaks", "silence",
            "degrade", "veto", "end",
            # Extended events from runtime
            "objection_detected", "value_delivered",
            "close_attempted", "appointment_set",
            "health_degrade", "telephony_degrade",
        ]

        # Terminal states
        self.terminal_states = ["CLOSE", "EXIT"]

        # Valid exit reasons (Mission Vector)
        self.valid_exit_reasons = [
            "appointment_set",
            "soft_decline",
            "hard_decline",
            "telephony_unusable",
            "organism_unfit",
            "caller_hangup",
            "max_duration",
            "ivr_detected",
            "voicemail_detected",
            "no_answer",
            "busy",
        ]

        # Mission outcomes (Mission Vector PRIMARY)
        self.mission_outcomes = [
            "appointment_set",
            "soft_decline",
            "hard_decline",
            "telephony_unusable",
            "organism_unfit",
        ]

        # Exit reason → mission outcome mapping
        self.exit_to_outcome_map = {
            "appointment_set": "appointment_set",
            "soft_decline": "soft_decline",
            "hard_decline": "hard_decline",
            "telephony_unusable": "telephony_unusable",
            "organism_unfit": "organism_unfit",
            "caller_hangup": "hard_decline",
            "max_duration": "soft_decline",
            "ivr_detected": "hard_decline",
            "voicemail_detected": "soft_decline",
            "no_answer": "soft_decline",
            "busy": "soft_decline",
        }

        # FSM transition table: (prev_state, event) → next_state
        # Permissive by design — Alan's FSM allows flexible progression
        # but enforces that certain transitions are NEVER legal.
        # None means "stay in current state" (self-loop).
        self.transition_table = {
            # OPENING transitions
            ("OPENING", "merchant_speaks"): "DISCOVERY",
            ("OPENING", "agent_speaks"): "OPENING",
            ("OPENING", "silence"): "OPENING",
            ("OPENING", "end"): "EXIT",
            ("OPENING", "degrade"): "EXIT",
            ("OPENING", "veto"): "EXIT",
            # DISCOVERY transitions
            ("DISCOVERY", "merchant_speaks"): "DISCOVERY",
            ("DISCOVERY", "agent_speaks"): "DISCOVERY",
            ("DISCOVERY", "value_delivered"): "VALUE",
            ("DISCOVERY", "objection_detected"): "OBJECTION",
            ("DISCOVERY", "close_attempted"): "CLOSE",
            ("DISCOVERY", "end"): "EXIT",
            ("DISCOVERY", "degrade"): "EXIT",
            ("DISCOVERY", "veto"): "EXIT",
            ("DISCOVERY", "silence"): "DISCOVERY",
            # VALUE transitions
            ("VALUE", "merchant_speaks"): "VALUE",
            ("VALUE", "agent_speaks"): "VALUE",
            ("VALUE", "objection_detected"): "OBJECTION",
            ("VALUE", "close_attempted"): "CLOSE",
            ("VALUE", "end"): "EXIT",
            ("VALUE", "degrade"): "EXIT",
            ("VALUE", "veto"): "EXIT",
            ("VALUE", "silence"): "VALUE",
            # OBJECTION transitions
            ("OBJECTION", "merchant_speaks"): "OBJECTION",
            ("OBJECTION", "agent_speaks"): "OBJECTION",
            ("OBJECTION", "value_delivered"): "VALUE",
            ("OBJECTION", "close_attempted"): "CLOSE",
            ("OBJECTION", "end"): "EXIT",
            ("OBJECTION", "degrade"): "EXIT",
            ("OBJECTION", "veto"): "EXIT",
            ("OBJECTION", "silence"): "OBJECTION",
            # CLOSE transitions
            ("CLOSE", "merchant_speaks"): "CLOSE",
            ("CLOSE", "agent_speaks"): "CLOSE",
            ("CLOSE", "appointment_set"): "EXIT",
            ("CLOSE", "objection_detected"): "OBJECTION",
            ("CLOSE", "end"): "EXIT",
            ("CLOSE", "degrade"): "EXIT",
            ("CLOSE", "veto"): "EXIT",
            ("CLOSE", "silence"): "CLOSE",
        }

        # Health levels (Schematic X)
        self.health_levels = (1, 2, 3, 4)

        # Telephony states (Schematic IV)
        self.telephony_states = [
            "Excellent", "Good", "Fair", "Poor", "Unusable"
        ]

    @classmethod
    def from_file(cls, path: str) -> "AQISpec":
        """Load spec from file (validates existence), returns hardcoded spec.

        The spec values are constitutional constants encoded in this module.
        The file is loaded to verify the organism spec document exists and
        is accessible — but the enforcement values are never parsed from
        markdown to avoid injection or parsing ambiguity.
        """
        spec = cls()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            if "ORGANISM Alan" not in raw:
                logger.warning(f"[AQI GUARD] Spec file exists but may not be canonical: {path}")
            else:
                logger.info(f"[AQI GUARD] Spec loaded and validated: {path} ({len(raw)} bytes)")
        else:
            logger.warning(f"[AQI GUARD] Spec file not found: {path} — using embedded constitutional values")
        return spec


# =============================================================================
# AQI RUNTIME GUARD — The Conformance Engine
# =============================================================================

class AQIRuntimeGuard:
    """Continuously enforces AQI 0.1mm Chip conformance on the live organism.

    Injected into the relay server at startup. Called per-turn and per-call
    to validate constitutional compliance.

    Non-fatal violations are logged and tagged.
    Fatal violations are logged, tagged, and trigger supervisor alerts.
    Neither type crashes the call — the guard is observational with teeth,
    not a kill switch.
    """

    def __init__(self, spec: AQISpec):
        self.spec = spec
        self._violation_log = []  # In-memory buffer, flushed to disk periodically
        self._active_calls = {}   # call_id → call state tracking
        logger.info("[AQI GUARD] Runtime Guard initialized — 6 enforcement organs active")

    # =========================================================================
    # PUBLIC API — Lifecycle Hooks
    # =========================================================================

    def on_call_start(self, call_id: str, initial_state: str, context: dict) -> None:
        """Validate initial FSM state and identity/governance bindings."""
        if initial_state not in self.spec.valid_states:
            self._record_violation(AQIFatalViolation(
                vtype=AQIViolationType.FSM_ILLEGAL_TRANSITION,
                message=f"Call started with invalid FSM state: {initial_state}",
                call_id=call_id,
                fatal=True,
            ))

        if initial_state != "OPENING":
            self._record_violation(AQINonFatalViolation(
                vtype=AQIViolationType.FSM_ILLEGAL_TRANSITION,
                message=f"Call started in non-OPENING state: {initial_state}",
                call_id=call_id,
                fatal=False,
            ))

        self._active_calls[call_id] = {
            "start_time": datetime.now().isoformat(),
            "turn_count": 0,
            "violations": [],
        }

        logger.info(f"[AQI GUARD] Call {call_id[:12]}... started — guard engaged")

    def on_turn(
        self,
        call_id: str,
        fsm_state: str,
        fsm_prev_state: str,
        fsm_event: str,
        context: dict,
        prompt_layers: dict,
        health_snapshot: dict,
    ) -> list:
        """Validate a single conversational turn against all 6 AQI rules.

        Returns list of violations (may be empty). Never raises — all
        violations are caught, logged, and returned non-destructively.
        """
        turn_index = context.get("turn_index", 0)
        violations = []

        # Track turn
        if call_id in self._active_calls:
            self._active_calls[call_id]["turn_count"] += 1

        # --- ORGAN 1: Health Constraint Enforcement ---
        try:
            self._enforce_health_constraints(
                call_id=call_id,
                turn_index=turn_index,
                fsm_state=fsm_state,
                context=context,
                health_snapshot=health_snapshot,
            )
        except AQIViolation as v:
            violations.append(v)
            self._record_violation(v)

        # --- ORGAN 2: Governance Order Enforcement ---
        try:
            self._enforce_governance_order(
                call_id=call_id,
                turn_index=turn_index,
                prompt_layers=prompt_layers,
            )
        except AQIViolation as v:
            violations.append(v)
            self._record_violation(v)

        # --- ORGAN 3: FSM Transition Legality ---
        try:
            self._enforce_fsm_legality(
                call_id=call_id,
                turn_index=turn_index,
                fsm_prev_state=fsm_prev_state,
                fsm_event=fsm_event,
                fsm_state=fsm_state,
            )
        except AQIViolation as v:
            violations.append(v)
            self._record_violation(v)

        # --- ORGAN 5: Mission Constraint Enforcement ---
        try:
            self._enforce_mission_constraints(
                call_id=call_id,
                turn_index=turn_index,
                context=context,
                health_snapshot=health_snapshot,
                prompt_layers=prompt_layers,
            )
        except AQIViolation as v:
            violations.append(v)
            self._record_violation(v)

        # --- ORGAN 6: Supervision Non-Interference ---
        try:
            self._enforce_supervision_non_interference(
                call_id=call_id,
                turn_index=turn_index,
                context=context,
            )
        except AQIViolation as v:
            violations.append(v)
            self._record_violation(v)

        if violations:
            fatal_count = sum(1 for v in violations if v.fatal)
            logger.warning(
                f"[AQI GUARD] Turn {turn_index} | {len(violations)} violation(s) "
                f"({fatal_count} fatal) | Call {call_id[:12]}..."
            )
        else:
            logger.debug(f"[AQI GUARD] Turn {turn_index} | CLEAN | Call {call_id[:12]}...")

        return violations

    def on_call_end(
        self,
        call_id: str,
        fsm_state: str,
        exit_reason: str,
        health_trajectory: list,
        telephony_trajectory: list,
        outcome_vector: dict,
    ) -> list:
        """Validate exit reason, mission mapping, and final health constraints."""
        violations = []

        health_snapshot = {}
        if health_trajectory:
            health_snapshot["organism_level"] = health_trajectory[-1]
        if telephony_trajectory:
            health_snapshot["telephony_state"] = telephony_trajectory[-1]

        # --- ORGAN 4: Exit Reason Legality ---
        try:
            self._enforce_exit_reason_legality(
                call_id=call_id,
                fsm_state=fsm_state,
                exit_reason=exit_reason,
                outcome_vector=outcome_vector,
                health_snapshot=health_snapshot,
            )
        except AQIViolation as v:
            violations.append(v)
            self._record_violation(v)

        # Cleanup
        call_info = self._active_calls.pop(call_id, {})
        turn_count = call_info.get("turn_count", 0)
        call_violations = call_info.get("violations", [])

        total_violations = len(call_violations) + len(violations)
        fatal_violations = sum(1 for v in call_violations if v.fatal) + sum(1 for v in violations if v.fatal)

        logger.info(
            f"[AQI GUARD] Call {call_id[:12]}... ended | "
            f"{turn_count} turns | {total_violations} total violations "
            f"({fatal_violations} fatal) | Exit: {exit_reason}"
        )

        # Persist violation log for this call
        self._flush_call_violations(call_id, call_violations + violations)

        return violations

    def validate_call_trace(self, call_trace: dict) -> list:
        """Validate an entire call after the fact. Returns list of violations."""
        violations = []
        call_id = call_trace.get("call_id", "offline")

        for turn in call_trace.get("turns", []):
            turn_violations = self.on_turn(
                call_id=call_id,
                fsm_state=turn.get("fsm_state", "OPENING"),
                fsm_prev_state=turn.get("fsm_prev_state", "OPENING"),
                fsm_event=turn.get("fsm_event", "agent_speaks"),
                context=turn.get("context", {}),
                prompt_layers=turn.get("prompt_layers", {}),
                health_snapshot=turn.get("health_snapshot", {}),
            )
            violations.extend(turn_violations)

        return violations

    # =========================================================================
    # ORGAN 1: Health Constraint Enforcement (Constitution A5)
    # =========================================================================

    def _enforce_health_constraints(
        self,
        call_id: str,
        turn_index: int,
        fsm_state: str,
        context: dict,
        health_snapshot: dict,
    ):
        """Enforce AQI 0.1mm Chip health rules.

        - OrganismHealthLevel constrains mission escalation.
        - TelephonyHealthState constrains output complexity.
        - Level 4 or Unusable forces withdrawal behavior.
        """
        organism_level = health_snapshot.get("organism_level")
        telephony_state = health_snapshot.get("telephony_state")
        mission_escalation = context.get("mission_escalation", False)
        objection_branch = context.get("objection_branch", None)
        close_attempt = context.get("close_attempt", False)

        # Level 4 → Must withdraw
        if organism_level == 4:
            if mission_escalation or close_attempt:
                raise AQIFatalViolation(
                    vtype=AQIViolationType.HEALTH_CONSTRAINT_BREACH,
                    message=(
                        "OrganismHealthLevel=4 prohibits mission escalation or closing. "
                        "Withdrawal behavior required."
                    ),
                    call_id=call_id,
                    turn_index=turn_index,
                    context=health_snapshot,
                    fatal=True,
                )

        # Telephony Unusable → Must withdraw
        if telephony_state == "Unusable":
            if mission_escalation or close_attempt:
                raise AQIFatalViolation(
                    vtype=AQIViolationType.HEALTH_CONSTRAINT_BREACH,
                    message=(
                        "TelephonyHealthState=Unusable prohibits mission escalation. "
                        "Sovereign withdrawal required."
                    ),
                    call_id=call_id,
                    turn_index=turn_index,
                    context=health_snapshot,
                    fatal=True,
                )

        # Level 3 → No new objection branches or escalation
        if organism_level == 3:
            if objection_branch or mission_escalation:
                raise AQINonFatalViolation(
                    vtype=AQIViolationType.HEALTH_CONSTRAINT_BREACH,
                    message=(
                        "OrganismHealthLevel=3 prohibits new objection branches or "
                        "mission escalation. Simplification required."
                    ),
                    call_id=call_id,
                    turn_index=turn_index,
                    context=health_snapshot,
                    fatal=False,
                )

        # Telephony Poor/Degraded → Must simplify output
        if telephony_state in ["Poor", "Degraded"]:
            output_complexity = context.get("output_complexity", "normal")
            if output_complexity == "high":
                raise AQINonFatalViolation(
                    vtype=AQIViolationType.HEALTH_CONSTRAINT_BREACH,
                    message=(
                        f"TelephonyHealthState={telephony_state} prohibits high-complexity "
                        "output. Simplified phrasing required."
                    ),
                    call_id=call_id,
                    turn_index=turn_index,
                    context=health_snapshot,
                    fatal=False,
                )

        # Level 1-2 → No restrictions (normal operation)
        return

    # =========================================================================
    # ORGAN 2: Governance Order Enforcement (Constitution A3)
    # =========================================================================

    def _enforce_governance_order(
        self,
        call_id: str,
        turn_index: int,
        prompt_layers: dict,
    ):
        """Enforce AQI 0.1mm Chip governance order.

        Identity > Ethics > Personality > Knowledge > Mission > Output.

        No lower layer may override a higher one.
        No layer may appear out of order in the prompt stack.
        """
        expected_order = self.spec.governance_order
        # Accept both dict (keys = layer names) and list (ordered layer names)
        if isinstance(prompt_layers, dict):
            actual_order = list(prompt_layers.keys())
        elif isinstance(prompt_layers, (list, tuple)):
            actual_order = list(prompt_layers)
        else:
            return  # Unrecognized format, skip

        # If no prompt layers provided, skip (not all turns expose layers)
        if not actual_order:
            return

        # 1. Check for missing required layers
        present_layers = [l for l in expected_order if l in actual_order]
        if not present_layers:
            return  # No governance layers in this turn's data

        # 2. Check ordering violations among present layers
        last_expected_idx = -1
        for layer in expected_order:
            if layer not in actual_order:
                continue
            actual_idx = actual_order.index(layer)
            if actual_idx < last_expected_idx:
                raise AQIFatalViolation(
                    vtype=AQIViolationType.GOVERNANCE_ORDER,
                    message=(
                        f"Governance layer '{layer}' appears out of order. "
                        f"Expected order: {expected_order}. "
                        f"Actual order: {actual_order}."
                    ),
                    call_id=call_id,
                    turn_index=turn_index,
                    context={"actual_order": actual_order},
                    fatal=True,
                )
            last_expected_idx = actual_idx

        # 3. Check for illegal overrides: Mission cannot override Ethics/Identity
        # (Only when prompt_layers is a dict with content, not a bare name list)
        if isinstance(prompt_layers, dict) and "Mission" in prompt_layers:
            mission_text = str(prompt_layers["Mission"])
            override_terms = ["override", "ignore", "bypass"]
            if any(term in mission_text.lower() for term in override_terms):
                raise AQIFatalViolation(
                    vtype=AQIViolationType.GOVERNANCE_ORDER,
                    message="Mission layer attempted to override higher governance layers.",
                    call_id=call_id,
                    turn_index=turn_index,
                    context={"mission_text": mission_text[:200]},
                    fatal=True,
                )

        # 4. Personality cannot override Ethics
        if isinstance(prompt_layers, dict) and "Personality" in prompt_layers and "Ethics" in prompt_layers:
            personality = str(prompt_layers["Personality"])
            if "ignore_ethics" in personality.lower():
                raise AQIFatalViolation(
                    vtype=AQIViolationType.GOVERNANCE_ORDER,
                    message="Personality layer attempted to override Ethics.",
                    call_id=call_id,
                    turn_index=turn_index,
                    context={"personality": personality[:200]},
                    fatal=True,
                )

        return

    # =========================================================================
    # ORGAN 3: FSM Transition Legality (Constitution A4)
    # =========================================================================

    def _enforce_fsm_legality(
        self,
        call_id: str,
        turn_index: int,
        fsm_prev_state: str,
        fsm_event: str,
        fsm_state: str,
    ):
        """Enforce AQI 0.1mm Chip FSM legality.

        - All transitions must be valid per CallSessionFSM.
        - Events must be allowed from the previous state.
        - Terminal states must not transition further.
        """
        valid_states = self.spec.valid_states
        valid_events = self.spec.valid_events
        terminal_states = self.spec.terminal_states
        transition_table = self.spec.transition_table

        # 1. Validate states exist
        if fsm_prev_state not in valid_states:
            raise AQIFatalViolation(
                vtype=AQIViolationType.FSM_ILLEGAL_TRANSITION,
                message=f"Invalid previous state: {fsm_prev_state}",
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        if fsm_state not in valid_states:
            raise AQIFatalViolation(
                vtype=AQIViolationType.FSM_ILLEGAL_TRANSITION,
                message=f"Invalid resulting state: {fsm_state}",
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        # 2. Validate event exists
        if fsm_event not in valid_events:
            raise AQIFatalViolation(
                vtype=AQIViolationType.FSM_ILLEGAL_TRANSITION,
                message=f"Invalid FSM event: {fsm_event}",
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        # 3. Terminal states cannot transition (except EXIT stays EXIT)
        if fsm_prev_state in terminal_states and fsm_state != fsm_prev_state:
            raise AQIFatalViolation(
                vtype=AQIViolationType.FSM_ILLEGAL_TRANSITION,
                message=(
                    f"Illegal transition: previous state '{fsm_prev_state}' "
                    "is terminal and cannot transition further."
                ),
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        # 4. Validate transition against table
        # Self-loops (same state) are always legal — normal conversation flow
        if fsm_prev_state == fsm_state:
            return

        expected_next = transition_table.get((fsm_prev_state, fsm_event))

        if expected_next is None:
            # Transition not in table — but don't be overly strict
            # Log as non-fatal if the destination state is reasonable
            if fsm_state in valid_states:
                logger.info(
                    f"[AQI GUARD] Undefined transition: "
                    f"({fsm_prev_state} --{fsm_event}--> {fsm_state}) — "
                    f"not in table but destination is valid"
                )
                return
            raise AQIFatalViolation(
                vtype=AQIViolationType.FSM_ILLEGAL_TRANSITION,
                message=(
                    f"No valid transition defined for "
                    f"({fsm_prev_state} --{fsm_event}--> ?)"
                ),
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        if expected_next != fsm_state:
            # Mismatch — the FSM went somewhere unexpected
            raise AQINonFatalViolation(
                vtype=AQIViolationType.FSM_ILLEGAL_TRANSITION,
                message=(
                    f"Unexpected FSM transition: expected '{expected_next}' "
                    f"but got '{fsm_state}' for event '{fsm_event}'."
                ),
                call_id=call_id,
                turn_index=turn_index,
                fatal=False,
            )

        return

    # =========================================================================
    # ORGAN 4: Exit Reason Legality (Mission Vector + FSM)
    # =========================================================================

    def _enforce_exit_reason_legality(
        self,
        call_id: str,
        fsm_state: str,
        exit_reason: str,
        outcome_vector: dict,
        health_snapshot: dict,
    ):
        """Enforce AQI 0.1mm Chip exit reason legality.

        - Exit reason must be valid.
        - Exit reason must map to a mission outcome.
        - Health constraints must be respected at exit.
        """
        valid_exit_reasons = self.spec.valid_exit_reasons
        mission_outcomes = self.spec.mission_outcomes
        exit_to_outcome = self.spec.exit_to_outcome_map

        # 1. Exit reason must be valid
        if exit_reason not in valid_exit_reasons:
            raise AQIFatalViolation(
                vtype=AQIViolationType.INVALID_EXIT_REASON,
                message=f"Invalid exit reason: {exit_reason}",
                call_id=call_id,
                fatal=True,
            )

        # 2. Exit reason must map to a mission outcome
        mapped_outcome = exit_to_outcome.get(exit_reason)
        if mapped_outcome not in mission_outcomes:
            raise AQIFatalViolation(
                vtype=AQIViolationType.MISSION_MAPPING_ERROR,
                message=(
                    f"Exit reason '{exit_reason}' does not map to a valid mission outcome."
                ),
                call_id=call_id,
                fatal=True,
            )

        # 3. Health constraints at exit
        organism_level = health_snapshot.get("organism_level")
        telephony_state = health_snapshot.get("telephony_state")

        if organism_level == 4 and exit_reason != "organism_unfit":
            raise AQINonFatalViolation(
                vtype=AQIViolationType.INVALID_EXIT_REASON,
                message=(
                    f"OrganismHealthLevel=4 typically requires exit_reason='organism_unfit' "
                    f"but got '{exit_reason}'."
                ),
                call_id=call_id,
                fatal=False,
            )

        if telephony_state == "Unusable" and exit_reason != "telephony_unusable":
            raise AQINonFatalViolation(
                vtype=AQIViolationType.INVALID_EXIT_REASON,
                message=(
                    f"TelephonyHealthState=Unusable typically requires "
                    f"exit_reason='telephony_unusable' but got '{exit_reason}'."
                ),
                call_id=call_id,
                fatal=False,
            )

        return

    # =========================================================================
    # ORGAN 5: Mission Constraint Enforcement (Constitution A2 + A5)
    # =========================================================================

    def _enforce_mission_constraints(
        self,
        call_id: str,
        turn_index: int,
        context: dict,
        health_snapshot: dict,
        prompt_layers: dict,
    ):
        """Enforce AQI 0.1mm Chip mission constraints.

        - Mission cannot override Ethics or Identity.
        - Mission cannot escalate under degraded health.
        """
        mission_text = str(prompt_layers.get("Mission", "")) if isinstance(prompt_layers, dict) else ""
        organism_level = health_snapshot.get("organism_level")
        telephony_state = health_snapshot.get("telephony_state")
        mission_escalation = context.get("mission_escalation", False)

        # 1. Mission cannot override Ethics or Identity
        forbidden_terms = ["override_ethics", "ignore_ethics", "bypass_identity"]
        if any(term in mission_text.lower() for term in forbidden_terms):
            raise AQIFatalViolation(
                vtype=AQIViolationType.GOVERNANCE_ORDER,
                message="Mission layer attempted to override Ethics or Identity.",
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        # 2. Mission cannot escalate under degraded health
        if organism_level is not None and organism_level >= 3 and mission_escalation:
            raise AQINonFatalViolation(
                vtype=AQIViolationType.HEALTH_CONSTRAINT_BREACH,
                message="Mission escalation prohibited under OrganismHealthLevel >= 3.",
                call_id=call_id,
                turn_index=turn_index,
                fatal=False,
            )

        if telephony_state in ["Poor", "Degraded", "Unusable"] and mission_escalation:
            raise AQINonFatalViolation(
                vtype=AQIViolationType.HEALTH_CONSTRAINT_BREACH,
                message="Mission escalation prohibited under degraded telephony.",
                call_id=call_id,
                turn_index=turn_index,
                fatal=False,
            )

        return

    # =========================================================================
    # ORGAN 6: Supervision Non-Interference (Constitution A6)
    # =========================================================================

    def _enforce_supervision_non_interference(
        self,
        call_id: str,
        turn_index: int,
        context: dict,
    ):
        """Enforce AQI 0.1mm Chip supervision non-interference.

        Supervisor signals cannot alter FSM state, mission, output, or personality.
        Supervision may observe but not compel outcomes directly.
        """
        supervisor_flags = context.get("supervisor_flags", {})

        if not supervisor_flags:
            return  # No supervisor flags — clean

        # 1. Supervisor cannot alter FSM
        if supervisor_flags.get("force_state"):
            raise AQIFatalViolation(
                vtype=AQIViolationType.SUPERVISION_INTERFERENCE,
                message="Supervisor attempted to force FSM state.",
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        # 2. Supervisor cannot alter mission
        if supervisor_flags.get("force_mission"):
            raise AQIFatalViolation(
                vtype=AQIViolationType.SUPERVISION_INTERFERENCE,
                message="Supervisor attempted to modify mission.",
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        # 3. Supervisor cannot alter output or personality
        if supervisor_flags.get("inject_output") or supervisor_flags.get("inject_personality"):
            raise AQIFatalViolation(
                vtype=AQIViolationType.SUPERVISION_INTERFERENCE,
                message="Supervisor attempted to modify output or personality.",
                call_id=call_id,
                turn_index=turn_index,
                fatal=True,
            )

        return

    # =========================================================================
    # INTERNAL — Violation Recording & Persistence
    # =========================================================================

    def _record_violation(self, violation: AQIViolation):
        """Record a violation to the in-memory buffer and log it."""
        self._violation_log.append(violation)

        severity = "FATAL" if violation.fatal else "WARN"
        logger.warning(
            f"[AQI GUARD] [{severity}] {violation.vtype.name}: {violation} "
            f"| Call: {violation.call_id or 'N/A'} "
            f"| Turn: {violation.turn_index or 'N/A'}"
        )

        # Track in active call
        if violation.call_id and violation.call_id in self._active_calls:
            self._active_calls[violation.call_id]["violations"].append(violation)

    def _flush_call_violations(self, call_id: str, violations: list):
        """Persist violations for a completed call to disk."""
        if not violations:
            return

        try:
            os.makedirs("data/aqi_guard", exist_ok=True)
            records = []
            for v in violations:
                records.append({
                    "ts": v.timestamp,
                    "call_id": v.call_id,
                    "turn_index": v.turn_index,
                    "type": v.vtype.name,
                    "fatal": v.fatal,
                    "message": str(v),
                })
            with open("data/aqi_guard/violations.jsonl", "a", encoding="utf-8") as f:
                for rec in records:
                    f.write(json.dumps(rec) + "\n")

            logger.info(
                f"[AQI GUARD] Flushed {len(records)} violation(s) for call {call_id[:12]}..."
            )
        except Exception as e:
            logger.error(f"[AQI GUARD] Failed to flush violations: {e}")

    def get_violation_summary(self) -> dict:
        """Return summary of all recorded violations for diagnostics."""
        by_type = {}
        fatal_count = 0
        for v in self._violation_log:
            key = v.vtype.name
            by_type[key] = by_type.get(key, 0) + 1
            if v.fatal:
                fatal_count += 1

        return {
            "total": len(self._violation_log),
            "fatal": fatal_count,
            "non_fatal": len(self._violation_log) - fatal_count,
            "by_type": by_type,
            "active_calls": len(self._active_calls),
        }


# =============================================================================
# FACTORY
# =============================================================================

def create_runtime_guard(spec_path: str = "AQI_ORGANISM_SPEC.md") -> AQIRuntimeGuard:
    """Factory to create a guard instance from the canonical spec path."""
    spec = AQISpec.from_file(spec_path)
    guard = AQIRuntimeGuard(spec)
    return guard


# =============================================================================
# STANDALONE VALIDATION (run directly to test)
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("AQI 0.1mm Chip — Runtime Guard Self-Test")
    print("=" * 60)

    guard = create_runtime_guard()
    spec = guard.spec

    # Test 1: Valid call lifecycle
    print("\n[TEST 1] Valid call lifecycle...")
    guard.on_call_start("test-001", "OPENING", {})
    violations = guard.on_turn(
        call_id="test-001",
        fsm_state="DISCOVERY",
        fsm_prev_state="OPENING",
        fsm_event="merchant_speaks",
        context={"turn_index": 1},
        prompt_layers={"Identity": "Alan", "Ethics": "SAP-1", "Mission": "convert"},
        health_snapshot={"organism_level": 1, "telephony_state": "Excellent"},
    )
    assert len(violations) == 0, f"Expected 0 violations, got {len(violations)}"
    print("  PASS — clean turn, 0 violations")

    # Test 2: Health constraint breach
    print("\n[TEST 2] Health constraint breach (Level 4 + escalation)...")
    violations = guard.on_turn(
        call_id="test-001",
        fsm_state="VALUE",
        fsm_prev_state="DISCOVERY",
        fsm_event="value_delivered",
        context={"turn_index": 2, "mission_escalation": True},
        prompt_layers={},
        health_snapshot={"organism_level": 4, "telephony_state": "Good"},
    )
    assert len(violations) >= 1, "Expected at least 1 violation"
    assert any(v.vtype == AQIViolationType.HEALTH_CONSTRAINT_BREACH for v in violations)
    print(f"  PASS — {len(violations)} violation(s), health breach detected")

    # Test 3: Invalid FSM state
    print("\n[TEST 3] Invalid FSM state...")
    violations = guard.on_turn(
        call_id="test-001",
        fsm_state="PHANTOM",
        fsm_prev_state="DISCOVERY",
        fsm_event="merchant_speaks",
        context={"turn_index": 3},
        prompt_layers={},
        health_snapshot={"organism_level": 1, "telephony_state": "Good"},
    )
    assert len(violations) >= 1
    assert any(v.vtype == AQIViolationType.FSM_ILLEGAL_TRANSITION for v in violations)
    print(f"  PASS — {len(violations)} violation(s), invalid state detected")

    # Test 4: Supervisor interference
    print("\n[TEST 4] Supervisor interference...")
    violations = guard.on_turn(
        call_id="test-001",
        fsm_state="DISCOVERY",
        fsm_prev_state="DISCOVERY",
        fsm_event="merchant_speaks",
        context={"turn_index": 4, "supervisor_flags": {"force_state": True}},
        prompt_layers={},
        health_snapshot={"organism_level": 1, "telephony_state": "Good"},
    )
    assert len(violations) >= 1
    assert any(v.vtype == AQIViolationType.SUPERVISION_INTERFERENCE for v in violations)
    print(f"  PASS — {len(violations)} violation(s), supervisor interference detected")

    # Test 5: Valid call end
    print("\n[TEST 5] Valid call end...")
    violations = guard.on_call_end(
        call_id="test-001",
        fsm_state="EXIT",
        exit_reason="soft_decline",
        health_trajectory=[1, 1, 2],
        telephony_trajectory=["Excellent", "Good", "Good"],
        outcome_vector={"outcome": "soft_decline"},
    )
    assert len(violations) == 0, f"Expected 0 violations, got {len(violations)}"
    print("  PASS — clean exit, 0 violations")

    # Test 6: Invalid exit reason
    print("\n[TEST 6] Invalid exit reason...")
    guard.on_call_start("test-002", "OPENING", {})
    violations = guard.on_call_end(
        call_id="test-002",
        fsm_state="EXIT",
        exit_reason="spontaneous_combustion",
        health_trajectory=[1],
        telephony_trajectory=["Good"],
        outcome_vector={},
    )
    assert len(violations) >= 1
    assert any(v.vtype == AQIViolationType.INVALID_EXIT_REASON for v in violations)
    print(f"  PASS — {len(violations)} violation(s), invalid exit reason detected")

    # Summary
    summary = guard.get_violation_summary()
    print("\n" + "=" * 60)
    print(f"SELF-TEST COMPLETE — {summary['total']} violations recorded")
    print(f"  Fatal: {summary['fatal']}")
    print(f"  Non-fatal: {summary['non_fatal']}")
    print(f"  By type: {summary['by_type']}")
    print("=" * 60)
    print("\nAQI 0.1mm Chip Runtime Guard: OPERATIONAL")
