"""
predictive_vad.py — Phase 5 Predictive VAD Organ
=================================================
AQI Classification: Experimental (governed)
Author: Tim (Founder) + Copilot (Instrument)
Created: February 19, 2026

PURPOSE:
    Shave ~150-250ms off turn-handoff by predicting turn endings
    BEFORE the hard silence threshold fires. Uses prosody signals
    (pitch contour, energy decay, syllable lengthening, micro-pause
    structure) to emit TURN_END_PREDICTED events early.

GUARDRAILS:
    - Predictive fire only allowed inside SANDBOX_WINDOW_MS before
      the current silence threshold (default: 150ms window).
    - If prediction is wrong and caller resumes within
      FALSE_CUT_TOLERANCE_MS, Alan yields immediately and logs
      a "false_early_cut" event.
    - If false-cut rate exceeds MAX_FALSE_CUT_RATE over a rolling
      window, predictive VAD auto-disables for the rest of the call.
    - All signals are logged to JSONL for post-hoc analysis.

INTEGRATION POINT:
    Called from the VAD GUARD block in aqi_conversation_relay_server.py.
    Sits between raw VAD state transitions and the STT pipeline trigger.

ARCHITECTURE:
    ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
    │ Audio Frames  │───▶│  ProsodyAnalyzer  │───▶│  PredictiveVAD   │
    │ (8kHz mulaw)  │    │  (pitch, energy,  │    │  (confidence →   │
    │               │    │   pause micro)    │    │   TURN_END event)│
    └──────────────┘    └──────────────────┘    └──────────────────┘
                                                        │
                                                        ▼
                                                ┌──────────────────┐
                                                │  FalseCutMonitor  │
                                                │  (rollback if     │
                                                │   rate too high)  │
                                                └──────────────────┘
"""

import time
import math
import json
import logging
import collections
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Deque
from pathlib import Path

logger = logging.getLogger("predictive_vad")

# =============================================================================
# CONFIGURATION — All tunable via aqi_modes.yaml or direct override
# =============================================================================
PREDICTIVE_VAD_ENABLED = False  # OFF by default — governed experiment
SANDBOX_WINDOW_MS = 150        # Only predict within this window before silence threshold
FALSE_CUT_TOLERANCE_MS = 300   # If caller resumes within this, it's a false cut
MAX_FALSE_CUT_RATE = 0.15      # Auto-disable if >15% false cuts in rolling window
ROLLING_WINDOW_SIZE = 20       # Number of predictions in the rolling window
CONFIDENCE_THRESHOLD = 0.70    # Minimum confidence to fire TURN_END_PREDICTED
SAMPLE_RATE = 8000             # mulaw 8kHz

# Prosody feature weights (sum to 1.0)
WEIGHT_PITCH_FALL = 0.35       # Falling pitch = statement ending
WEIGHT_ENERGY_DECAY = 0.25     # Trailing energy = winding down
WEIGHT_SYLLABLE_STRETCH = 0.15 # Final syllable lengthening
WEIGHT_MICRO_PAUSE = 0.25      # 20-80ms gaps between words = natural phrasing end

# Log paths
PVAD_LOG_DIR = Path("data/pvad_logs")


class PredictionOutcome(Enum):
    """Outcome of a predictive VAD firing."""
    CORRECT = "correct"           # Caller did stop — prediction was right
    FALSE_CUT = "false_early_cut" # Caller resumed — prediction was wrong
    SUPPRESSED = "suppressed"     # Confidence too low, did not fire
    DISABLED = "disabled"         # Auto-disabled due to high false-cut rate


@dataclass
class ProsodySnapshot:
    """A point-in-time snapshot of prosody features from audio frames."""
    timestamp: float
    pitch_slope: float = 0.0        # Negative = falling (statement)
    energy_level: float = 0.0       # 0.0-1.0 normalized
    energy_slope: float = 0.0       # Negative = decaying
    syllable_duration_ms: float = 0.0  # Last detected syllable length
    micro_pause_ms: float = 0.0     # Current pause duration in ms
    raw_confidence: float = 0.0     # Computed confidence before threshold


@dataclass
class PredictionEvent:
    """A single prediction event for logging and analysis."""
    call_sid: str
    timestamp: float
    confidence: float
    outcome: PredictionOutcome
    prosody: ProsodySnapshot
    latency_saved_ms: float = 0.0   # Estimated ms saved vs reactive VAD
    caller_resumed_after_ms: float = 0.0  # If false cut, how soon caller resumed


class ProsodyAnalyzer:
    """Extracts prosody features from raw audio frames.
    
    Operates on a sliding window of audio frames to compute:
    - Pitch contour slope (via zero-crossing rate as pitch proxy)
    - Energy envelope and decay rate
    - Syllable boundary detection (energy dips)
    - Micro-pause detection (sub-100ms silence gaps)
    
    NOTE: This is a lightweight approximation. Full pitch tracking
    (autocorrelation, CREPE, etc.) would be more accurate but adds
    latency and compute. ZCR-based proxy is sufficient for turn-end
    prediction where we need speed over precision.
    """

    def __init__(self, window_frames: int = 10):
        """
        Args:
            window_frames: Number of recent frames to analyze.
                          At 20ms/frame, 10 frames = 200ms window.
        """
        self._window_frames = window_frames
        self._frame_buffer: Deque[bytes] = collections.deque(maxlen=window_frames)
        self._energy_history: Deque[float] = collections.deque(maxlen=window_frames)
        self._zcr_history: Deque[float] = collections.deque(maxlen=window_frames)
        self._silence_start: Optional[float] = None
        self._last_voiced_time: float = 0.0

    def feed_frame(self, frame: bytes, timestamp: float) -> ProsodySnapshot:
        """Process one audio frame and return current prosody snapshot.
        
        Args:
            frame: Raw audio bytes (PCM 16-bit or mulaw 8-bit, 8kHz).
            timestamp: Current time (time.time()).
        
        Returns:
            ProsodySnapshot with current prosody features.
        """
        self._frame_buffer.append(frame)

        # Compute energy (RMS approximation)
        energy = self._compute_energy(frame)
        self._energy_history.append(energy)

        # Compute zero-crossing rate (pitch proxy)
        zcr = self._compute_zcr(frame)
        self._zcr_history.append(zcr)

        # Track silence/voiced transitions
        silence_threshold = 0.02
        is_silence = energy < silence_threshold
        micro_pause_ms = 0.0

        if is_silence:
            if self._silence_start is None:
                self._silence_start = timestamp
            micro_pause_ms = (timestamp - self._silence_start) * 1000
        else:
            self._silence_start = None
            self._last_voiced_time = timestamp

        # Compute slopes over window
        pitch_slope = self._compute_slope(list(self._zcr_history))
        energy_slope = self._compute_slope(list(self._energy_history))

        # Estimate syllable duration from energy dip patterns
        syllable_duration_ms = self._estimate_last_syllable_duration()

        # Normalize energy to 0-1
        max_energy = max(self._energy_history) if self._energy_history else 1.0
        norm_energy = energy / max_energy if max_energy > 0 else 0.0

        # Compute raw confidence
        confidence = self._compute_confidence(
            pitch_slope, energy_slope, norm_energy,
            syllable_duration_ms, micro_pause_ms
        )

        return ProsodySnapshot(
            timestamp=timestamp,
            pitch_slope=pitch_slope,
            energy_level=norm_energy,
            energy_slope=energy_slope,
            syllable_duration_ms=syllable_duration_ms,
            micro_pause_ms=micro_pause_ms,
            raw_confidence=confidence,
        )

    def _compute_energy(self, frame: bytes) -> float:
        """RMS energy of frame. Works with raw bytes."""
        if not frame:
            return 0.0
        # Treat bytes as unsigned 8-bit, center at 128
        total = sum((b - 128) ** 2 for b in frame)
        return math.sqrt(total / len(frame)) / 128.0

    def _compute_zcr(self, frame: bytes) -> float:
        """Zero-crossing rate as pitch proxy. Higher ZCR ≈ higher pitch."""
        if len(frame) < 2:
            return 0.0
        crossings = sum(
            1 for i in range(1, len(frame))
            if (frame[i] > 128) != (frame[i-1] > 128)
        )
        return crossings / len(frame)

    def _compute_slope(self, values: list) -> float:
        """Simple linear regression slope over a sequence."""
        n = len(values)
        if n < 3:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        return num / den if den != 0 else 0.0

    def _estimate_last_syllable_duration(self) -> float:
        """Estimate last syllable duration from energy dip patterns.
        Returns duration in ms. Rough heuristic: time since last energy dip."""
        if len(self._energy_history) < 3:
            return 0.0
        # Find last energy dip (local minimum)
        vals = list(self._energy_history)
        for i in range(len(vals) - 2, 0, -1):
            if vals[i] < vals[i-1] and vals[i] < vals[i+1]:
                frames_since = len(vals) - i
                return frames_since * 20.0  # 20ms per frame
        return len(vals) * 20.0

    def _compute_confidence(self, pitch_slope, energy_slope, energy_level,
                           syllable_duration_ms, micro_pause_ms) -> float:
        """Weighted confidence that a turn ending is imminent.
        
        Features indicating turn-end:
        - Falling pitch (negative slope) → statement completion
        - Decaying energy (negative slope) → trailing off
        - Stretched syllable (>150ms) → final syllable lengthening
        - Micro-pause (20-80ms) → natural phrase boundary
        """
        scores = []

        # Pitch fall: negative slope is a strong turn-end signal
        pitch_score = min(1.0, max(0.0, -pitch_slope * 50))  # Scale and clamp
        scores.append(WEIGHT_PITCH_FALL * pitch_score)

        # Energy decay: negative slope means winding down
        energy_score = min(1.0, max(0.0, -energy_slope * 30))
        scores.append(WEIGHT_ENERGY_DECAY * energy_score)

        # Syllable stretch: final syllable > 150ms suggests completion
        stretch_score = min(1.0, max(0.0, (syllable_duration_ms - 100) / 150))
        scores.append(WEIGHT_SYLLABLE_STRETCH * stretch_score)

        # Micro-pause: 20-80ms gap is a natural phrase boundary
        if 20 <= micro_pause_ms <= 80:
            pause_score = 1.0
        elif micro_pause_ms < 20:
            pause_score = micro_pause_ms / 20.0
        else:
            pause_score = max(0.0, 1.0 - (micro_pause_ms - 80) / 100)
        scores.append(WEIGHT_MICRO_PAUSE * pause_score)

        return sum(scores)

    def reset(self):
        """Reset analyzer state for new call/turn."""
        self._frame_buffer.clear()
        self._energy_history.clear()
        self._zcr_history.clear()
        self._silence_start = None
        self._last_voiced_time = 0.0


class FalseCutMonitor:
    """Tracks false-cut rate and auto-disables predictive VAD if too high.
    
    Uses a rolling window of the last N predictions. If the false-cut
    rate exceeds MAX_FALSE_CUT_RATE, predictive VAD is disabled for
    the remainder of the call.
    """

    def __init__(self, window_size: int = ROLLING_WINDOW_SIZE,
                 max_rate: float = MAX_FALSE_CUT_RATE):
        self._window: Deque[PredictionOutcome] = collections.deque(maxlen=window_size)
        self._max_rate = max_rate
        self._disabled = False
        self._disable_reason: Optional[str] = None

    @property
    def is_disabled(self) -> bool:
        return self._disabled

    @property
    def false_cut_rate(self) -> float:
        if not self._window:
            return 0.0
        fired = [o for o in self._window
                 if o in (PredictionOutcome.CORRECT, PredictionOutcome.FALSE_CUT)]
        if not fired:
            return 0.0
        false_cuts = sum(1 for o in fired if o == PredictionOutcome.FALSE_CUT)
        return false_cuts / len(fired)

    def record(self, outcome: PredictionOutcome) -> bool:
        """Record a prediction outcome. Returns True if still enabled."""
        self._window.append(outcome)
        rate = self.false_cut_rate
        if rate > self._max_rate and len(self._window) >= 5:
            self._disabled = True
            self._disable_reason = (
                f"False-cut rate {rate:.1%} exceeds threshold {self._max_rate:.1%} "
                f"over last {len(self._window)} predictions"
            )
            logger.warning(f"[PVAD] Auto-disabled: {self._disable_reason}")
            return False
        return True

    def reset(self):
        """Reset for new call."""
        self._window.clear()
        self._disabled = False
        self._disable_reason = None


class PredictiveVAD:
    """Phase 5 Predictive VAD Organ.
    
    Sits between raw audio frames and the VAD guard to predict
    turn endings ~150-250ms before the hard silence threshold.
    
    Usage in relay server:
        pvad = PredictiveVAD(call_sid)
        # In audio frame handler:
        event = pvad.on_audio_frame(frame, timestamp, current_silence_ms)
        if event == "TURN_END_PREDICTED":
            # Fire pipeline early
        # When caller resumes after prediction:
        pvad.on_caller_resumed(resumed_after_ms)
        # At call end:
        pvad.finalize()
    """

    def __init__(self, call_sid: str, enabled: bool = PREDICTIVE_VAD_ENABLED):
        self._call_sid = call_sid
        self._enabled = enabled
        self._analyzer = ProsodyAnalyzer()
        self._monitor = FalseCutMonitor()
        self._events: List[PredictionEvent] = []
        self._last_prediction_time: float = 0.0
        self._pending_prediction: Optional[PredictionEvent] = None
        self._silence_threshold_ms: float = 420  # Match relay server's 0.42s

    @property
    def enabled(self) -> bool:
        return self._enabled and not self._monitor.is_disabled

    def on_audio_frame(self, frame: bytes, timestamp: float,
                       current_silence_ms: float) -> Optional[str]:
        """Process an audio frame and potentially predict turn end.
        
        Args:
            frame: Raw audio frame bytes.
            timestamp: Current time.
            current_silence_ms: How long the caller has been silent (ms).
        
        Returns:
            "TURN_END_PREDICTED" if prediction fires, None otherwise.
        """
        if not self.enabled:
            return None

        # Only predict within the sandbox window
        sandbox_start = self._silence_threshold_ms - SANDBOX_WINDOW_MS
        if current_silence_ms < sandbox_start:
            return None  # Too early — not in sandbox window yet
        if current_silence_ms >= self._silence_threshold_ms:
            return None  # Reactive VAD will handle this

        # Analyze prosody
        snapshot = self._analyzer.feed_frame(frame, timestamp)

        if snapshot.raw_confidence >= CONFIDENCE_THRESHOLD:
            # Fire prediction!
            latency_saved = self._silence_threshold_ms - current_silence_ms
            event = PredictionEvent(
                call_sid=self._call_sid,
                timestamp=timestamp,
                confidence=snapshot.raw_confidence,
                outcome=PredictionOutcome.CORRECT,  # Assume correct until proven wrong
                prosody=snapshot,
                latency_saved_ms=latency_saved,
            )
            self._pending_prediction = event
            self._last_prediction_time = timestamp
            self._events.append(event)
            logger.info(
                f"[PVAD] TURN_END_PREDICTED — confidence={snapshot.raw_confidence:.2f}, "
                f"saved={latency_saved:.0f}ms, pitch_slope={snapshot.pitch_slope:.3f}, "
                f"energy_slope={snapshot.energy_slope:.3f}"
            )
            return "TURN_END_PREDICTED"

        # Below threshold — record as suppressed
        return None

    def on_caller_resumed(self, resumed_after_ms: float):
        """Called when caller resumes speaking after a prediction fired.
        
        If the caller resumes within FALSE_CUT_TOLERANCE_MS, this was
        a false prediction. Log it and update the false-cut monitor.
        """
        if not self._pending_prediction:
            return

        if resumed_after_ms <= FALSE_CUT_TOLERANCE_MS:
            self._pending_prediction.outcome = PredictionOutcome.FALSE_CUT
            self._pending_prediction.caller_resumed_after_ms = resumed_after_ms
            logger.warning(
                f"[PVAD] FALSE CUT — caller resumed after {resumed_after_ms:.0f}ms. "
                f"Confidence was {self._pending_prediction.confidence:.2f}"
            )
        else:
            self._pending_prediction.outcome = PredictionOutcome.CORRECT
            logger.info(
                f"[PVAD] Prediction CORRECT — caller did not resume until "
                f"{resumed_after_ms:.0f}ms (threshold: {FALSE_CUT_TOLERANCE_MS}ms)"
            )

        self._monitor.record(self._pending_prediction.outcome)
        self._pending_prediction = None

    def confirm_turn_end(self):
        """Called when silence threshold fires normally — confirm any pending prediction."""
        if self._pending_prediction:
            self._pending_prediction.outcome = PredictionOutcome.CORRECT
            self._monitor.record(PredictionOutcome.CORRECT)
            self._pending_prediction = None

    def finalize(self) -> dict:
        """Finalize at call end. Write logs, return summary."""
        # Resolve any pending prediction
        if self._pending_prediction:
            self._pending_prediction.outcome = PredictionOutcome.CORRECT
            self._monitor.record(PredictionOutcome.CORRECT)
            self._pending_prediction = None

        summary = {
            "call_sid": self._call_sid,
            "total_predictions": len(self._events),
            "correct": sum(1 for e in self._events if e.outcome == PredictionOutcome.CORRECT),
            "false_cuts": sum(1 for e in self._events if e.outcome == PredictionOutcome.FALSE_CUT),
            "suppressed": sum(1 for e in self._events if e.outcome == PredictionOutcome.SUPPRESSED),
            "false_cut_rate": self._monitor.false_cut_rate,
            "auto_disabled": self._monitor.is_disabled,
            "avg_latency_saved_ms": (
                sum(e.latency_saved_ms for e in self._events if e.outcome == PredictionOutcome.CORRECT)
                / max(1, sum(1 for e in self._events if e.outcome == PredictionOutcome.CORRECT))
            ),
        }

        # Write JSONL log
        self._write_log(summary)

        logger.info(f"[PVAD] Call finalized: {json.dumps(summary)}")
        return summary

    def _write_log(self, summary: dict):
        """Write prediction events and summary to JSONL log."""
        try:
            PVAD_LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_file = PVAD_LOG_DIR / f"pvad_{self._call_sid}.jsonl"
            with open(log_file, "w") as f:
                # Write each event
                for event in self._events:
                    record = {
                        "type": "prediction",
                        "call_sid": event.call_sid,
                        "timestamp": event.timestamp,
                        "confidence": event.confidence,
                        "outcome": event.outcome.value,
                        "latency_saved_ms": event.latency_saved_ms,
                        "caller_resumed_after_ms": event.caller_resumed_after_ms,
                        "pitch_slope": event.prosody.pitch_slope,
                        "energy_slope": event.prosody.energy_slope,
                        "energy_level": event.prosody.energy_level,
                        "micro_pause_ms": event.prosody.micro_pause_ms,
                    }
                    f.write(json.dumps(record) + "\n")
                # Write summary
                summary["type"] = "summary"
                f.write(json.dumps(summary) + "\n")
        except Exception as e:
            logger.error(f"[PVAD] Failed to write log: {e}")

    def reset(self):
        """Reset for new call."""
        self._analyzer.reset()
        self._monitor.reset()
        self._events.clear()
        self._pending_prediction = None
        self._last_prediction_time = 0.0


# =============================================================================
# MODULE SELF-TEST
# =============================================================================
if __name__ == "__main__":
    import struct

    logging.basicConfig(level=logging.DEBUG)
    print("=== Predictive VAD Self-Test ===\n")

    # Create a test instance with predictive VAD enabled
    pvad = PredictiveVAD("test_call_001", enabled=True)

    # Simulate frames with falling energy (turn ending)
    print("1. Simulating turn-end prosody (falling energy + silence)...")
    for i in range(15):
        # Generate fake frame with decreasing energy
        energy = max(0, 200 - i * 15)
        frame = bytes([128 + (energy if i % 2 == 0 else -energy) % 128] * 160)
        silence_ms = max(0, i * 30 - 100)  # Starts accumulating silence
        result = pvad.on_audio_frame(frame, time.time() + i * 0.02, silence_ms)
        if result:
            print(f"   Frame {i}: {result}")

    # Confirm turn ended
    pvad.confirm_turn_end()

    # Finalize and show summary
    summary = pvad.finalize()
    print(f"\n2. Summary: {json.dumps(summary, indent=2)}")

    # Test false-cut monitor
    print("\n3. Testing false-cut auto-disable...")
    monitor = FalseCutMonitor(window_size=10, max_rate=0.15)
    for i in range(10):
        outcome = PredictionOutcome.FALSE_CUT if i % 3 == 0 else PredictionOutcome.CORRECT
        still_enabled = monitor.record(outcome)
        print(f"   Prediction {i}: {outcome.value} → rate={monitor.false_cut_rate:.1%}, enabled={still_enabled}")

    print("\n=== Self-Test Complete ===")
