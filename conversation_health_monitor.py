"""
conversation_health_monitor.py
Phase 3A: Organism Self-Awareness — Per-Turn Conversational Health

Maps real-time conversational signals (LLM latency, errors, repetition,
SoulCore vetoes) to the 4-level health model from organism_self_awareness_canon.py.

Levels:
    1 — OPTIMAL:  Normal latency, low errors, no loops.
    2 — STRAINED: Latency creeping up, occasional retries.
    3 — COMPROMISED: Repeated fallbacks, visible repetition, rising vetoes.
    4 — UNFIT:    Persistent failure patterns; call should end or escalate.

Behavioral hooks (consumed by build_llm_prompt via context keys):
    Level 2: Slow pacing slightly, simplify phrasing, reduce wit.
    Level 3: Explicitly acknowledge friction, tighten scope, no new branches.
    Level 4: Graceful sovereign exit via FSM end_call(reason='organism_unfit').

Created: Feb 19, 2026 — Phase 3A (Make Alan Whole)
"""

import time
import logging
from enum import IntEnum
from typing import Dict, Any, Optional, List
from collections import deque

logger = logging.getLogger("ConversationHealth")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEALTH LEVELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class HealthLevel(IntEnum):
    OPTIMAL = 1
    STRAINED = 2
    COMPROMISED = 3
    UNFIT = 4


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THRESHOLDS — Tunable per Tim's directive
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# LLM latency thresholds (ms) — end-to-end orchestrated response time
LATENCY_STRAINED_MS = 3000.0       # Above this → Level 2
LATENCY_COMPROMISED_MS = 5000.0    # Above this → Level 3
LATENCY_UNFIT_MS = 10000.0         # Above this → Level 4 (was 8000 — CW23 tuning)

# Error thresholds — count within sliding window
ERROR_STRAINED = 1           # 1 error in window → Level 2
ERROR_COMPROMISED = 2        # 2 errors in window → Level 3
ERROR_UNFIT = 4              # 4+ errors in window → Level 4 (was 3 — CW23 tuning)

# SoulCore veto thresholds — vetoes in sliding window
VETO_STRAINED = 1            # 1 veto in window → at least Level 2
VETO_COMPROMISED = 2         # 2 vetoes → at least Level 3

# Repetition thresholds — similar responses in sliding window
REPETITION_STRAINED = 2      # 2 near-identical responses → Level 2
REPETITION_COMPROMISED = 3   # 3 → Level 3
REPETITION_UNFIT = 5         # 5+ → Level 4 (was 4 — CW23 tuning)

# Sliding window size (turns)
WINDOW_SIZE = 6

# Consecutive turns at a level before escalation is "sticky"
STICKY_TURNS = 2


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BEHAVIORAL DIRECTIVES (injected into prompt)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HEALTH_DIRECTIVES = {
    HealthLevel.OPTIMAL: None,  # No injection needed
    HealthLevel.STRAINED: (
        "[ORGANISM HEALTH: STRAINED] Keep responses shorter and simpler. "
        "Reduce wit. Avoid complex branching questions. Stay focused."
    ),
    HealthLevel.COMPROMISED: (
        "[ORGANISM HEALTH: COMPROMISED] Something feels off on my end. "
        "Use very short, clear sentences. No new conversation branches. "
        "Confirm what you heard. If this continues, wrap up gracefully."
    ),
    HealthLevel.UNFIT: (
        "[ORGANISM HEALTH: UNFIT — SOVEREIGN EXIT REQUIRED] "
        "End this conversation gracefully and immediately. "
        "Say something like: 'I appreciate your time today — let me follow up "
        "with you another time when I can give you my full attention. Take care!'"
    ),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MONITOR CLASS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ConversationHealthMonitor:
    """
    Per-call organism health tracker.

    Usage:
        monitor = ConversationHealthMonitor()
        context['_health_monitor'] = monitor

        # After each turn:
        monitor.record_turn(
            llm_latency_ms=...,
            had_error=...,
            had_fallback=...,
            had_veto=...,
            response_text=...
        )
        health = monitor.current_level
        directive = monitor.get_directive()
    """

    def __init__(self):
        self._latencies: deque = deque(maxlen=WINDOW_SIZE)
        self._errors: deque = deque(maxlen=WINDOW_SIZE)
        self._vetoes: deque = deque(maxlen=WINDOW_SIZE)
        self._responses: deque = deque(maxlen=WINDOW_SIZE)
        self._level_history: deque = deque(maxlen=WINDOW_SIZE)
        self._current_level: HealthLevel = HealthLevel.OPTIMAL
        self._turn_count: int = 0
        self._total_errors: int = 0
        self._total_vetoes: int = 0
        self._created_at: float = time.time()

    # ── Record Turn ───────────────────────────────────────────────────

    def record_turn(
        self,
        llm_latency_ms: float = 0.0,
        had_error: bool = False,
        had_fallback: bool = False,
        had_veto: bool = False,
        response_text: str = "",
    ):
        """Record signals from one completed turn and recompute health level."""
        self._turn_count += 1
        self._latencies.append(llm_latency_ms)
        self._errors.append(1 if (had_error or had_fallback) else 0)
        self._vetoes.append(1 if had_veto else 0)
        self._responses.append(self._normalize(response_text))

        if had_error or had_fallback:
            self._total_errors += 1
        if had_veto:
            self._total_vetoes += 1

        # Compute new level
        new_level = self._compute_level()
        self._level_history.append(new_level)
        old_level = self._current_level

        # Level can escalate immediately but only de-escalates after STICKY_TURNS
        if new_level > self._current_level:
            self._current_level = new_level
        elif new_level < self._current_level:
            # Only de-escalate if the last STICKY_TURNS were all at or below new_level
            recent = list(self._level_history)[-STICKY_TURNS:]
            if len(recent) >= STICKY_TURNS and all(lv <= new_level for lv in recent):
                self._current_level = new_level

        if self._current_level != old_level:
            logger.info(
                f"[ORGANISM HEALTH] Level changed: {old_level.name} → {self._current_level.name} "
                f"(turn={self._turn_count}, latency={llm_latency_ms:.0f}ms, "
                f"errors={sum(self._errors)}, vetoes={sum(self._vetoes)}, "
                f"reps={self._repetition_count()})"
            )
        else:
            logger.debug(
                f"[ORGANISM HEALTH] Level={self._current_level.name} "
                f"(turn={self._turn_count}, latency={llm_latency_ms:.0f}ms)"
            )

    # ── Compute ───────────────────────────────────────────────────────

    def _compute_level(self) -> HealthLevel:
        """Evaluate all signals and return worst-case health level."""
        signals = []

        # Signal 1: LLM latency
        if self._latencies:
            avg_lat = sum(self._latencies) / len(self._latencies)
            last_lat = self._latencies[-1]
            # Use max of average and last — catches both sustained and spike
            effective_lat = max(avg_lat, last_lat)
            if effective_lat >= LATENCY_UNFIT_MS:
                signals.append(HealthLevel.UNFIT)
            elif effective_lat >= LATENCY_COMPROMISED_MS:
                signals.append(HealthLevel.COMPROMISED)
            elif effective_lat >= LATENCY_STRAINED_MS:
                signals.append(HealthLevel.STRAINED)
            else:
                signals.append(HealthLevel.OPTIMAL)

        # Signal 2: Error rate
        error_count = sum(self._errors)
        if error_count >= ERROR_UNFIT:
            signals.append(HealthLevel.UNFIT)
        elif error_count >= ERROR_COMPROMISED:
            signals.append(HealthLevel.COMPROMISED)
        elif error_count >= ERROR_STRAINED:
            signals.append(HealthLevel.STRAINED)
        else:
            signals.append(HealthLevel.OPTIMAL)

        # Signal 3: SoulCore vetoes
        veto_count = sum(self._vetoes)
        if veto_count >= VETO_COMPROMISED:
            signals.append(HealthLevel.COMPROMISED)
        elif veto_count >= VETO_STRAINED:
            signals.append(HealthLevel.STRAINED)
        else:
            signals.append(HealthLevel.OPTIMAL)

        # Signal 4: Repetition
        rep_count = self._repetition_count()
        if rep_count >= REPETITION_UNFIT:
            signals.append(HealthLevel.UNFIT)
        elif rep_count >= REPETITION_COMPROMISED:
            signals.append(HealthLevel.COMPROMISED)
        elif rep_count >= REPETITION_STRAINED:
            signals.append(HealthLevel.STRAINED)
        else:
            signals.append(HealthLevel.OPTIMAL)

        # Worst-case wins
        return max(signals) if signals else HealthLevel.OPTIMAL

    def _repetition_count(self) -> int:
        """Count near-identical responses in the sliding window."""
        if len(self._responses) < 2:
            return 0
        responses = list(self._responses)
        last = responses[-1]
        if not last:
            return 0
        count = 0
        for r in responses[:-1]:
            if r and self._is_similar(last, r):
                count += 1
        return count

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize response text for comparison."""
        return ' '.join(text.lower().split())[:200]

    @staticmethod
    def _is_similar(a: str, b: str) -> bool:
        """Quick similarity check — same first 50 chars or >80% word overlap."""
        if not a or not b:
            return False
        # Prefix match
        if a[:50] == b[:50]:
            return True
        # Word overlap
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return False
        intersection = words_a & words_b
        union = words_a | words_b
        if len(intersection) / len(union) > 0.8:
            return True
        return False

    # ── Public API ────────────────────────────────────────────────────

    @property
    def current_level(self) -> HealthLevel:
        return self._current_level

    @property
    def current_level_name(self) -> str:
        return self._current_level.name

    @property
    def current_level_int(self) -> int:
        return int(self._current_level)

    @property
    def is_unfit(self) -> bool:
        return self._current_level == HealthLevel.UNFIT

    @property
    def is_compromised_or_worse(self) -> bool:
        return self._current_level >= HealthLevel.COMPROMISED

    # ── CW23 Engagement Override ─────────────────────────────────────

    def should_suppress_unfit(self, turn_count: int = 0, merchant_engaged: bool = False) -> bool:
        """CW23 organism_unfit tuning: suppress UNFIT exit when merchant is engaged.

        If the merchant is actively in conversation (3+ turns, asking questions
        or giving substantive responses), we grant 2 extra turns of patience
        before allowing the UNFIT exit. This prevents premature exits during
        real conversations where system health dips are transient.

        Returns True if UNFIT should be suppressed (don't exit yet).
        """
        if not self.is_unfit:
            return False
        # Engagement override: if merchant is actively engaged, suppress
        if merchant_engaged and turn_count >= 3:
            # Only suppress if we haven't been unfit for too many consecutive turns
            recent_unfit = sum(1 for lv in list(self._level_history)[-3:] if lv == HealthLevel.UNFIT)
            if recent_unfit < 3:  # Allow up to 2 UNFIT turns before forcing exit
                logger.info(
                    f"[ORGANISM HEALTH] UNFIT suppressed — merchant engaged "
                    f"(turns={turn_count}, consecutive_unfit={recent_unfit})"
                )
                return True
        return False

    def get_directive(self) -> Optional[str]:
        """Return prompt directive for current health level, or None for OPTIMAL."""
        return HEALTH_DIRECTIVES.get(self._current_level)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable state for logging / CDC."""
        return {
            'level': self._current_level.name,
            'level_int': int(self._current_level),
            'turn_count': self._turn_count,
            'avg_latency_ms': round(sum(self._latencies) / max(1, len(self._latencies)), 1),
            'error_count_window': sum(self._errors),
            'veto_count_window': sum(self._vetoes),
            'repetition_count': self._repetition_count(),
            'total_errors': self._total_errors,
            'total_vetoes': self._total_vetoes,
            'uptime_s': round(time.time() - self._created_at, 1),
        }
