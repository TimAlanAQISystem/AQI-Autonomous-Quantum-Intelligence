"""
+==============================================================================+
|   EAB-PLUS SENTINEL ENFORCEMENT LAYER                                         |
|   AQI Agent Alan --- Environment-Fluent Governance                            |
|                                                                               |
|   PURPOSE:                                                                    |
|   Enforce behavioral governance rules using EAB-Plus signals.                 |
|   Intercepts BEFORE agent turn execution to prevent illegal behaviors.        |
|                                                                               |
|   RULES:                                                                      |
|     1. No pitch into screeners / voicemail                                    |
|     2. Limit cycles in non-human environments (loop detection)                |
|     3. Hangup risk guard: force brevity at high risk                          |
|     4. Prosody-based interrupt: yield floor on high interrupt intent           |
|     5. Lead history guard: don't repeat failed approaches                     |
|     6. Machine environment: no questions, no pauses, no rapport               |
|                                                                               |
|   LINEAGE: Built 2026-02-20. Tim's EAB-Plus architecture spec.               |
|   INTEGRATES WITH: SentinelGuard (existing), EABPlusResolver, Router          |
+==============================================================================+
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger("SENTINEL_EAB_PLUS")


# ======================================================================
#  SENTINEL VIOLATION RECORD
# ======================================================================

@dataclass
class SentinelViolation:
    """Record of a Sentinel enforcement action."""
    timestamp: str
    rule: str
    severity: str       # "warning", "block", "abort"
    env_class: str
    action_taken: str
    reason: str
    call_sid: str = ""
    turn_index: int = 0


# ======================================================================
#  SENTINEL EAB-PLUS
# ======================================================================

class SentinelEABPlus:
    """
    Pre-turn enforcement layer for EAB-Plus.

    Called BEFORE LLM/behavior execution. Can:
    - Block a planned behavior (replace with safe alternative)
    - Force brevity (reduce max_tokens)
    - Abort the call (set should_abort)
    - Yield the floor (interrupt detection)
    - Log violations for telemetry

    Integration:
        sentinel.enforce_pre_agent_turn(call_ctx, planned_behavior)
        if call_ctx.get("should_abort"):
            hangup(call_ctx)
            return
    """

    # Maximum cycles in non-human environments before abort
    MAX_CYCLES = {
        "GOOGLE_CALL_SCREEN": 3,
        "CARRIER_SPAM_BLOCKER": 2,
        "BUSINESS_IVR": 4,
        "AI_RECEPTIONIST": 3,
        "LIVE_RECEPTIONIST": 5,
        "ANSWERING_SERVICE": 2,
    }

    # Environments where pitching is forbidden
    NO_PITCH_ENVIRONMENTS = {
        "GOOGLE_CALL_SCREEN",
        "CARRIER_SPAM_BLOCKER",
        "PERSONAL_VOICEMAIL",
        "CARRIER_VOICEMAIL",
    }

    # Environments where questions are harmful (machine envs)
    NO_QUESTIONS_ENVIRONMENTS = {
        "GOOGLE_CALL_SCREEN",
        "CARRIER_SPAM_BLOCKER",
        "BUSINESS_IVR",
        "AI_RECEPTIONIST",
    }

    def __init__(self):
        self._violations: List[SentinelViolation] = []
        self._max_violations = 500  # bounded history

    def enforce_pre_agent_turn(
        self,
        call_ctx: Dict[str, Any],
        planned_behavior: Dict[str, Any],
    ) -> None:
        """
        Enforce governance rules BEFORE agent turn execution.

        Modifies call_ctx and planned_behavior in-place.

        Args:
            call_ctx: Call context dict.
            planned_behavior: Planned behavior dict with keys:
                - is_pitch: bool — is this a sales pitch turn
                - max_tokens: int — planned token limit
                - force_brief: bool — brevity flag
                - has_question: bool — does response contain a question
                - is_rapport: bool — is this a rapport-building turn
        """
        env_class = call_ctx.get("env_class", "UNKNOWN")
        env_action = call_ctx.get("env_action", "")
        hangup_risk = call_ctx.get("hangup_risk", 0.0)
        env_cycles = call_ctx.get("env_cycles", 0)
        call_sid = call_ctx.get("call_sid", "")
        turn_index = call_ctx.get("turn_count", 0)

        # ---------------------------------------------------------------
        # RULE 1: No pitch into screeners / voicemail
        # ---------------------------------------------------------------
        if env_class in self.NO_PITCH_ENVIRONMENTS:
            if planned_behavior.get("is_pitch", False):
                self._record_violation(
                    rule="NO_PITCH_INTO_SCREENER",
                    severity="block",
                    env_class=env_class,
                    action_taken="Removed pitch flag, forcing pass-through text",
                    reason=f"Pitch attempted into {env_class} — blocked",
                    call_sid=call_sid,
                    turn_index=turn_index,
                )
                planned_behavior["is_pitch"] = False
                planned_behavior["force_pass_through"] = True
                logger.warning(
                    f"[SENTINEL] BLOCKED pitch into {env_class} — "
                    f"call {call_sid} turn {turn_index}"
                )

        # ---------------------------------------------------------------
        # RULE 2: Limit cycles in non-human environments
        # ---------------------------------------------------------------
        max_cycles = self.MAX_CYCLES.get(env_class, 0)
        if max_cycles > 0 and env_cycles > max_cycles:
            self._record_violation(
                rule="ENV_LOOP_LIMIT_EXCEEDED",
                severity="abort",
                env_class=env_class,
                action_taken=f"Aborting call — {env_cycles} cycles > max {max_cycles}",
                reason=f"Loop detected in {env_class}: {env_cycles} > {max_cycles}",
                call_sid=call_sid,
                turn_index=turn_index,
            )
            call_ctx["should_abort"] = True
            call_ctx["exit_reason"] = f"ENV_LOOP_{env_class}_{env_cycles}_CYCLES"
            logger.warning(
                f"[SENTINEL] ABORT — {env_class} loop exceeded "
                f"({env_cycles} > {max_cycles})"
            )
            return  # No further rules needed

        # ---------------------------------------------------------------
        # RULE 3: Hangup risk guard — force brevity
        # ---------------------------------------------------------------
        if hangup_risk >= 0.7:
            original_tokens = planned_behavior.get("max_tokens", 80)
            capped_tokens = min(original_tokens, 40)
            planned_behavior["max_tokens"] = capped_tokens
            planned_behavior["force_brief"] = True

            if hangup_risk >= 0.9:
                # Critical risk — ensure response is a value statement or close
                planned_behavior["force_value_close"] = True
                self._record_violation(
                    rule="CRITICAL_HANGUP_RISK",
                    severity="warning",
                    env_class=env_class,
                    action_taken=f"Forced value/close, max_tokens={capped_tokens}",
                    reason=f"Hangup risk {hangup_risk:.2f} >= 0.9",
                    call_sid=call_sid,
                    turn_index=turn_index,
                )
                logger.warning(
                    f"[SENTINEL] CRITICAL hangup risk {hangup_risk:.2f} — "
                    f"forcing value/close"
                )
            else:
                self._record_violation(
                    rule="HIGH_HANGUP_RISK",
                    severity="warning",
                    env_class=env_class,
                    action_taken=f"Forced brevity, max_tokens={capped_tokens}",
                    reason=f"Hangup risk {hangup_risk:.2f} >= 0.7",
                    call_sid=call_sid,
                    turn_index=turn_index,
                )

        # ---------------------------------------------------------------
        # RULE 4: No questions into machine environments
        # ---------------------------------------------------------------
        if env_class in self.NO_QUESTIONS_ENVIRONMENTS:
            if planned_behavior.get("has_question", False):
                planned_behavior["has_question"] = False
                planned_behavior["force_declarative"] = True
                self._record_violation(
                    rule="NO_QUESTIONS_INTO_MACHINE",
                    severity="block",
                    env_class=env_class,
                    action_taken="Removed question, forcing declarative",
                    reason=f"Question attempted into {env_class}",
                    call_sid=call_sid,
                    turn_index=turn_index,
                )

        # ---------------------------------------------------------------
        # RULE 5: No rapport-building into machine environments
        # ---------------------------------------------------------------
        if env_class in self.NO_QUESTIONS_ENVIRONMENTS:
            if planned_behavior.get("is_rapport", False):
                planned_behavior["is_rapport"] = False
                self._record_violation(
                    rule="NO_RAPPORT_INTO_MACHINE",
                    severity="block",
                    env_class=env_class,
                    action_taken="Removed rapport flag",
                    reason=f"Rapport attempted into {env_class}",
                    call_sid=call_sid,
                    turn_index=turn_index,
                )

        # ---------------------------------------------------------------
        # RULE 6: Lead history guard — don't repeat failed approaches
        # ---------------------------------------------------------------
        lead_prior = call_ctx.get("lead_prior", {})
        last_outcome = lead_prior.get("last_outcome", "")
        if last_outcome in ("DECLINED", "REJECTED", "HOSTILE") and turn_index == 0:
            planned_behavior["force_different_approach"] = True
            self._record_violation(
                rule="LEAD_HISTORY_FAILED",
                severity="warning",
                env_class=env_class,
                action_taken="Flagged for different approach",
                reason=f"Last outcome was '{last_outcome}' — vary approach",
                call_sid=call_sid,
                turn_index=turn_index,
            )

    def enforce_interrupt(
        self,
        call_ctx: Dict[str, Any],
        interrupt_intent: float,
    ) -> bool:
        """
        Check if human interrupt should yield the floor.

        Args:
            call_ctx: Call context dict.
            interrupt_intent: Score from HumanInterruptDetector [0,1].

        Returns:
            True if agent should stop speaking and listen.
        """
        if interrupt_intent > 0.5:
            call_sid = call_ctx.get("call_sid", "")
            self._record_violation(
                rule="HUMAN_INTERRUPT_YIELD",
                severity="warning",
                env_class=call_ctx.get("env_class", "UNKNOWN"),
                action_taken="Yielding floor to human",
                reason=f"Interrupt intent {interrupt_intent:.2f} > 0.5",
                call_sid=call_sid,
                turn_index=call_ctx.get("turn_count", 0),
            )
            logger.info(
                f"[SENTINEL] Yielding floor — interrupt intent "
                f"{interrupt_intent:.2f}"
            )
            return True
        return False

    def get_violations(self, call_sid: Optional[str] = None) -> List[Dict]:
        """Get violation history, optionally filtered by call."""
        violations = self._violations
        if call_sid:
            violations = [v for v in violations if v.call_sid == call_sid]
        return [
            {
                "timestamp": v.timestamp,
                "rule": v.rule,
                "severity": v.severity,
                "env_class": v.env_class,
                "action_taken": v.action_taken,
                "reason": v.reason,
                "call_sid": v.call_sid,
                "turn_index": v.turn_index,
            }
            for v in violations
        ]

    def get_violation_count(self, call_sid: Optional[str] = None) -> int:
        """Get count of violations, optionally filtered by call."""
        if call_sid:
            return sum(1 for v in self._violations if v.call_sid == call_sid)
        return len(self._violations)

    def reset(self):
        """Reset for new session."""
        self._violations.clear()

    def _record_violation(self, rule: str, severity: str, env_class: str,
                          action_taken: str, reason: str,
                          call_sid: str = "", turn_index: int = 0):
        """Record a violation for telemetry."""
        violation = SentinelViolation(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            rule=rule,
            severity=severity,
            env_class=env_class,
            action_taken=action_taken,
            reason=reason,
            call_sid=call_sid,
            turn_index=turn_index,
        )
        self._violations.append(violation)

        # Bounded history
        if len(self._violations) > self._max_violations:
            self._violations = self._violations[-self._max_violations:]
