"""
telephony_health_monitor.py
Phase 3B: Telephony Perception — Per-Call Line Health

Maps real-time audio stream metrics (RMS, silence, talk-over, ASR quality)
to the telephony health model from telephony_perception_canon.py.

States (7, simplified to 5 actionable levels):
    EXCELLENT:  Clear audio, no issues.
    GOOD:       Minor noise but fully functional.
    DEGRADED:   Noticeable quality loss — one repair attempt.
    POOR:       Significant quality loss — short/clear mode.
    UNUSABLE:   Cannot sustain conversation — sovereign withdrawal.

Signals consumed per audio frame:
    - RMS energy levels (silence detection)
    - ASR confidence / "didn't catch that" detection
    - Talk-over / barge-in frequency
    - Sustained silence (one-sided audio)

Behavioral hooks (consumed by build_llm_prompt via context keys):
    DEGRADED:  One explicit repair: "I'm getting a little noise on my side..."
    POOR:      Switch to shorter sentences. Confirm key details.
    UNUSABLE:  Sovereign withdrawal phrase + FSM end_call(reason='telephony_unusable').

Created: Feb 19, 2026 — Phase 3B (Make Alan Whole)
"""

import time
import logging
from enum import IntEnum
from typing import Dict, Any, Optional
from collections import deque

logger = logging.getLogger("TelephonyHealth")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEALTH STATES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TelephonyHealthState(IntEnum):
    EXCELLENT = 1
    GOOD = 2
    DEGRADED = 3
    POOR = 4
    UNUSABLE = 5


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THRESHOLDS — Tunable
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Frame window for rolling metrics (1 frame = 20ms, 250 frames = 5s)
FRAME_WINDOW = 250

# Silence detection — % of frames below speech threshold in window
SILENCE_RATIO_DEGRADED = 0.85    # >85% silence in window → DEGRADED
SILENCE_RATIO_POOR = 0.92        # >92% silence → POOR
SILENCE_RATIO_UNUSABLE = 0.97    # >97% silence → UNUSABLE

# RMS thresholds
RMS_SPEECH_THRESHOLD = 400       # Below this = silence frame

# Talk-over / barge-in frequency (count in window)
TALKOVER_DEGRADED = 3            # 3+ barge-ins in window → at least DEGRADED
TALKOVER_POOR = 5                # 5+ → at least POOR

# ASR quality — "didn't catch that" / low-quality transcript detection
ASR_FAIL_DEGRADED = 2            # 2 ASR failures in window → at least DEGRADED
ASR_FAIL_POOR = 3                # 3+ → at least POOR
ASR_FAIL_UNUSABLE = 5            # 5+ → UNUSABLE

# ASR window size (turns, not frames)
ASR_WINDOW_SIZE = 8

# Sustained poor state before escalation (seconds)
SUSTAINED_POOR_THRESHOLD_S = 15.0
SUSTAINED_UNUSABLE_THRESHOLD_S = 8.0

# Minimum call duration before telephony health can trigger exit (seconds)
# Prevents false kills during initial silence before greeting plays
MIN_CALL_AGE_FOR_EXIT_S = 20.0

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CANONICAL PHRASES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REPAIR_PHRASE = (
    "I'm getting a little bit of noise on my side — "
    "let me repeat that more clearly."
)

POOR_DIRECTIVE = (
    "[TELEPHONY HEALTH: POOR] The line quality is degraded. "
    "Use very short, clear sentences. Confirm key details explicitly. "
    "Avoid complex phrasing. If the merchant can't hear you, wrap up."
)

UNUSABLE_EXIT_PHRASE = (
    "I'm having trouble hearing you — the line might be acting up. "
    "I respect your time, so I'll try you back on a better connection. Take care!"
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BEHAVIORAL DIRECTIVES (injected into prompt)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TELEPHONY_DIRECTIVES = {
    TelephonyHealthState.EXCELLENT: None,
    TelephonyHealthState.GOOD: None,
    TelephonyHealthState.DEGRADED: (
        "[TELEPHONY HEALTH: DEGRADED] Some line noise detected. "
        "Keep sentences short and clear. Speak slightly more deliberately."
    ),
    TelephonyHealthState.POOR: POOR_DIRECTIVE,
    TelephonyHealthState.UNUSABLE: (
        "[TELEPHONY HEALTH: UNUSABLE — SOVEREIGN EXIT REQUIRED] "
        "The line is too degraded to continue. End gracefully: "
        f'"{UNUSABLE_EXIT_PHRASE}"'
    ),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MONITOR CLASS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TelephonyHealthMonitor:
    """
    Per-call telephony health tracker.

    Usage:
        monitor = TelephonyHealthMonitor()
        context['_telephony_monitor'] = monitor

        # On every inbound audio frame:
        monitor.process_frame(rms_value)

        # On barge-in events:
        monitor.record_talkover()

        # On ASR transcript events:
        monitor.record_asr_result(text, is_low_quality=...)

        # Query:
        state = monitor.current_state
        directive = monitor.get_directive()
        should_exit = monitor.should_exit()
    """

    def __init__(self):
        # Rolling frame metrics
        self._frame_energies: deque = deque(maxlen=FRAME_WINDOW)
        self._talkover_timestamps: deque = deque(maxlen=50)
        self._asr_failures: deque = deque(maxlen=ASR_WINDOW_SIZE)

        # State tracking
        self._current_state: TelephonyHealthState = TelephonyHealthState.EXCELLENT
        self._state_entered_at: float = time.time()
        self._created_at: float = time.time()
        self._total_frames: int = 0
        self._total_silence_frames: int = 0
        self._total_talkovers: int = 0
        self._total_asr_failures: int = 0

        # Repair tracking — only send repair phrase once
        self._repair_sent: bool = False

        # State transition log
        self._transitions: list = []

    # ── Frame Processing ──────────────────────────────────────────────

    def process_frame(self, rms: int):
        """Process one inbound audio frame (called every ~20ms)."""
        self._total_frames += 1
        is_silence = rms < RMS_SPEECH_THRESHOLD
        self._frame_energies.append(rms)
        if is_silence:
            self._total_silence_frames += 1

        # Recompute state every 50 frames (~1 second) to avoid excessive logging
        if self._total_frames % 50 == 0:
            self._recompute_state()

    def record_talkover(self):
        """Record a barge-in / talk-over event."""
        self._total_talkovers += 1
        self._talkover_timestamps.append(time.time())

    def record_asr_result(self, text: str, is_low_quality: bool = False):
        """
        Record an ASR transcript result.
        is_low_quality: True if transcript was garbled, too short, or
        contains "didn't catch that" / "sorry" patterns.
        """
        if is_low_quality:
            self._total_asr_failures += 1
            self._asr_failures.append(True)
        else:
            self._asr_failures.append(False)

    # ── State Computation ─────────────────────────────────────────────

    def _recompute_state(self):
        """Evaluate all telephony signals and update state."""
        signals = []

        # Signal 1: Silence ratio in frame window
        if len(self._frame_energies) >= 50:  # Need at least 1s of data
            silence_count = sum(1 for rms in self._frame_energies if rms < RMS_SPEECH_THRESHOLD)
            silence_ratio = silence_count / len(self._frame_energies)

            if silence_ratio >= SILENCE_RATIO_UNUSABLE:
                signals.append(TelephonyHealthState.UNUSABLE)
            elif silence_ratio >= SILENCE_RATIO_POOR:
                signals.append(TelephonyHealthState.POOR)
            elif silence_ratio >= SILENCE_RATIO_DEGRADED:
                signals.append(TelephonyHealthState.DEGRADED)
            else:
                signals.append(TelephonyHealthState.EXCELLENT)

        # Signal 2: Talk-over frequency (last 30 seconds)
        now = time.time()
        recent_talkovers = sum(1 for t in self._talkover_timestamps if now - t < 30.0)
        if recent_talkovers >= TALKOVER_POOR:
            signals.append(TelephonyHealthState.POOR)
        elif recent_talkovers >= TALKOVER_DEGRADED:
            signals.append(TelephonyHealthState.DEGRADED)
        else:
            signals.append(TelephonyHealthState.GOOD)

        # Signal 3: ASR quality
        asr_fail_count = sum(1 for f in self._asr_failures if f)
        if asr_fail_count >= ASR_FAIL_UNUSABLE:
            signals.append(TelephonyHealthState.UNUSABLE)
        elif asr_fail_count >= ASR_FAIL_POOR:
            signals.append(TelephonyHealthState.POOR)
        elif asr_fail_count >= ASR_FAIL_DEGRADED:
            signals.append(TelephonyHealthState.DEGRADED)
        else:
            signals.append(TelephonyHealthState.EXCELLENT)

        # Worst-case wins
        new_state = max(signals) if signals else TelephonyHealthState.EXCELLENT

        # State transition logic — can escalate freely, de-escalates conservatively
        old_state = self._current_state
        if new_state > self._current_state:
            self._current_state = new_state
            self._state_entered_at = now
            self._transitions.append({
                'from': old_state.name,
                'to': new_state.name,
                'at': now,
                'elapsed_s': round(now - self._created_at, 1),
            })
            logger.info(
                f"[TELEPHONY HEALTH] State changed: {old_state.name} → {new_state.name} "
                f"(frames={self._total_frames}, talkovers={self._total_talkovers}, "
                f"asr_fails={self._total_asr_failures})"
            )
        elif new_state < self._current_state:
            # De-escalate only if we've been at the lower state for >5 seconds worth of checks
            time_at_current = now - self._state_entered_at
            if time_at_current > 10.0:
                self._current_state = new_state
                self._state_entered_at = now
                self._transitions.append({
                    'from': old_state.name,
                    'to': new_state.name,
                    'at': now,
                    'elapsed_s': round(now - self._created_at, 1),
                })
                logger.info(
                    f"[TELEPHONY HEALTH] State improved: {old_state.name} → {new_state.name}"
                )

    # ── Public API ────────────────────────────────────────────────────

    @property
    def current_state(self) -> TelephonyHealthState:
        return self._current_state

    @property
    def current_state_name(self) -> str:
        return self._current_state.name

    @property
    def current_state_int(self) -> int:
        return int(self._current_state)

    @property
    def is_unusable(self) -> bool:
        return self._current_state == TelephonyHealthState.UNUSABLE

    @property
    def is_poor_or_worse(self) -> bool:
        return self._current_state >= TelephonyHealthState.POOR

    @property
    def needs_repair(self) -> bool:
        """Returns True once when state first reaches DEGRADED (one-shot)."""
        if self._current_state >= TelephonyHealthState.DEGRADED and not self._repair_sent:
            return True
        return False

    def mark_repair_sent(self):
        """Call after sending the repair phrase so it's not repeated."""
        self._repair_sent = True

    def get_repair_phrase(self) -> str:
        """Returns the canonical repair phrase."""
        return REPAIR_PHRASE

    def should_exit(self) -> bool:
        """
        Returns True if telephony health warrants sovereign withdrawal.
        Requires:
          - State is UNUSABLE
          - State has been UNUSABLE for >= SUSTAINED_UNUSABLE_THRESHOLD_S
          - Call has been active for >= MIN_CALL_AGE_FOR_EXIT_S
        """
        if self._current_state != TelephonyHealthState.UNUSABLE:
            return False
        now = time.time()
        call_age = now - self._created_at
        if call_age < MIN_CALL_AGE_FOR_EXIT_S:
            return False
        time_at_unusable = now - self._state_entered_at
        return time_at_unusable >= SUSTAINED_UNUSABLE_THRESHOLD_S

    def get_directive(self) -> Optional[str]:
        """Return prompt directive for current telephony state, or None for EXCELLENT/GOOD."""
        return TELEPHONY_DIRECTIVES.get(self._current_state)

    def get_exit_phrase(self) -> str:
        """Returns the canonical sovereign withdrawal phrase."""
        return UNUSABLE_EXIT_PHRASE

    def to_dict(self) -> Dict[str, Any]:
        """Serializable state for logging / CDC."""
        silence_ratio = 0.0
        if self._frame_energies:
            silence_count = sum(1 for rms in self._frame_energies if rms < RMS_SPEECH_THRESHOLD)
            silence_ratio = round(silence_count / len(self._frame_energies), 3)

        return {
            'state': self._current_state.name,
            'state_int': int(self._current_state),
            'total_frames': self._total_frames,
            'silence_ratio': silence_ratio,
            'total_talkovers': self._total_talkovers,
            'total_asr_failures': self._total_asr_failures,
            'repair_sent': self._repair_sent,
            'uptime_s': round(time.time() - self._created_at, 1),
            'transitions': len(self._transitions),
        }
