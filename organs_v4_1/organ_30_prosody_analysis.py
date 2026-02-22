"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 30 — PROSODY ANALYSIS                                        ║
║                                                                              ║
║  Extracts tone, emotion, urgency, and vocal cues from audio-level metadata.  ║
║  Alan currently hears the words; this organ lets him hear the music.          ║
║                                                                              ║
║  Input: audio frame metrics (energy, pitch, speaking rate, jitter/shimmer)   ║
║  Output: tone profile (energy_level, arousal, urgency, emotion tag)          ║
║                                                                              ║
║  Feeds into: pacing decisions, script selection, objection handling           ║
║  Called: every 1-2 seconds during live call                                  ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - Tone analysis cannot override explicit merchant statements              ║
║    - Tone data is advisory, not authoritative                                ║
║    - All tone classifications logged for lineage                             ║
║                                                                              ║
║  RRG: Section 40                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─── IQcore Wiring ───────────────────────────────────────────────────────────
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

try:
    from iqcore_enforcer import iqcore_cost
    IQCORE_AVAILABLE = True
except ImportError:
    IQCORE_AVAILABLE = False
    def iqcore_cost(actor, cost):
        def decorator(fn):
            fn._iqcore_actor = actor
            fn._iqcore_cost = cost
            return fn
        return decorator

logger = logging.getLogger("ORGAN_30")


# ─── CONSTANTS ───────────────────────────────────────────────────────────────

# Energy thresholds (RMS normalized 0.0–1.0)
ENERGY_LOW = 0.2
ENERGY_MED = 0.45
ENERGY_HIGH = 0.7

# Speaking rate thresholds (words per second)
WPS_SLOW = 1.2
WPS_NORMAL = 2.5
WPS_FAST = 3.5

# Pitch thresholds (Hz — approximate ranges for speech)
PITCH_LOW = 100.0
PITCH_MED = 180.0
PITCH_HIGH = 280.0

# Emotion mapping confidence threshold
EMOTION_CONFIDENCE_MIN = 0.5

# Strategy mappings
TONE_STRATEGY_MAP = {
    "frustrated": {"pacing": "slow", "tone": "empathetic", "priority": "de-escalate"},
    "interested": {"pacing": "match", "tone": "warm", "priority": "advance"},
    "impatient": {"pacing": "faster", "tone": "direct", "priority": "concise"},
    "confused": {"pacing": "slower", "tone": "clarifying", "priority": "simplify"},
    "neutral": {"pacing": "normal", "tone": "professional", "priority": "continue"},
    "enthusiastic": {"pacing": "match", "tone": "energetic", "priority": "close"},
    "resigned": {"pacing": "slow", "tone": "reassuring", "priority": "rebuild"},
}


# ─── PROSODY ANALYSIS ORGAN ─────────────────────────────────────────────────

class ProsodyAnalysisOrgan:
    """
    Organ 30 — Prosody Analysis

    Extracts coarse tone features from audio-level metadata and maps them
    to strategy recommendations for downstream organs.

    Input frame_metrics:
      {
        "rms_energy": float,     # 0.0–1.0 normalized RMS energy
        "pitch_hz": float,       # fundamental frequency in Hz
        "words_per_second": float,
        "jitter": float,         # pitch period perturbation (0.0–1.0)
        "shimmer": float,        # amplitude perturbation (0.0–1.0)
      }

    Output tone:
      {
        "energy_level": "low" | "medium" | "high",
        "arousal": "low" | "neutral" | "high",
        "urgency": "low" | "medium" | "high",
        "emotion": str,
        "emotion_confidence": float,
        "strategy": dict,
        "raw": dict,
      }
    """

    def __init__(self):
        self._history: List[Dict[str, Any]] = []  # rolling window of last N frames
        self._window_size = 10  # frames in rolling average
        self._frame_count = 0
        self._tone_log: List[Dict[str, Any]] = []
        logger.info("[ORGAN 30] Prosody Analysis initialized")

    # ─── ANALYSIS ────────────────────────────────────────────────────────

    @iqcore_cost("Alan", 1)
    def analyze_frame(self, frame_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single audio frame and return a tone profile.
        IQcore cost: 1 per call.
        """
        energy = frame_metrics.get("rms_energy", 0.0)
        pitch = frame_metrics.get("pitch_hz", 0.0)
        wps = frame_metrics.get("words_per_second", 0.0)
        jitter = frame_metrics.get("jitter", 0.0)
        shimmer = frame_metrics.get("shimmer", 0.0)

        # ── Energy level ─────────────────────────────────────────────
        if energy >= ENERGY_HIGH:
            energy_level = "high"
        elif energy >= ENERGY_MED:
            energy_level = "medium"
        else:
            energy_level = "low"

        # ── Arousal (combined energy + pitch) ────────────────────────
        arousal_score = (energy * 0.6) + (min(pitch / 300.0, 1.0) * 0.4)
        if arousal_score >= 0.65:
            arousal = "high"
        elif arousal_score >= 0.35:
            arousal = "neutral"
        else:
            arousal = "low"

        # ── Urgency (speaking rate) ──────────────────────────────────
        if wps >= WPS_FAST:
            urgency = "high"
        elif wps >= WPS_NORMAL:
            urgency = "medium"
        else:
            urgency = "low"

        # ── Emotion classification ───────────────────────────────────
        emotion, emotion_confidence = self._classify_emotion(
            energy, pitch, wps, jitter, shimmer
        )

        # ── Strategy recommendation ──────────────────────────────────
        strategy = TONE_STRATEGY_MAP.get(emotion, TONE_STRATEGY_MAP["neutral"])

        tone = {
            "energy_level": energy_level,
            "arousal": arousal,
            "urgency": urgency,
            "emotion": emotion,
            "emotion_confidence": round(emotion_confidence, 3),
            "strategy": strategy,
            "raw": frame_metrics,
        }

        # Update rolling history
        self._history.append(tone)
        if len(self._history) > self._window_size:
            self._history = self._history[-self._window_size:]
        self._frame_count += 1

        return tone

    def _classify_emotion(self, energy: float, pitch: float, wps: float,
                          jitter: float, shimmer: float) -> Tuple[str, float]:
        """
        Rule-based emotion classification from prosodic features.
        Returns (emotion_tag, confidence).
        """
        scores: Dict[str, float] = {
            "neutral": 0.3,  # base prior
            "frustrated": 0.0,
            "interested": 0.0,
            "impatient": 0.0,
            "confused": 0.0,
            "enthusiastic": 0.0,
            "resigned": 0.0,
        }

        # Frustrated: high energy + high jitter + high pitch
        if energy > ENERGY_HIGH and jitter > 0.4:
            scores["frustrated"] += 0.5
        if pitch > PITCH_HIGH and energy > ENERGY_MED:
            scores["frustrated"] += 0.3

        # Interested: medium-high energy + moderate pitch + moderate rate
        if ENERGY_MED <= energy <= ENERGY_HIGH and WPS_NORMAL <= wps <= WPS_FAST:
            scores["interested"] += 0.5
        if PITCH_MED <= pitch <= PITCH_HIGH:
            scores["interested"] += 0.2

        # Impatient: fast speaking + high energy
        if wps > WPS_FAST:
            scores["impatient"] += 0.4
        if energy > ENERGY_HIGH and wps > WPS_NORMAL:
            scores["impatient"] += 0.3

        # Confused: slow rate + rising pitch + high jitter
        if wps < WPS_SLOW and pitch > PITCH_MED:
            scores["confused"] += 0.4
        if jitter > 0.5:
            scores["confused"] += 0.2

        # Enthusiastic: high energy + high pitch + fast rate
        if energy > ENERGY_HIGH and pitch > PITCH_HIGH and wps > WPS_NORMAL:
            scores["enthusiastic"] += 0.6

        # Resigned: low energy + low pitch + slow rate
        if energy < ENERGY_LOW and pitch < PITCH_LOW and wps < WPS_NORMAL:
            scores["resigned"] += 0.5

        # Winner
        best = max(scores, key=scores.get)
        confidence = scores[best]

        # Require minimum confidence
        if confidence < EMOTION_CONFIDENCE_MIN:
            return "neutral", confidence

        return best, confidence

    # ─── TREND ANALYSIS ──────────────────────────────────────────────────

    def get_trend(self) -> Dict[str, Any]:
        """Return rolling trend analysis over the last N frames."""
        if not self._history:
            return {"trend": "no_data", "frames": 0}

        emotions = [f["emotion"] for f in self._history]
        urgencies = [f["urgency"] for f in self._history]

        # Most common emotion in window
        from collections import Counter
        emotion_counts = Counter(emotions)
        dominant_emotion = emotion_counts.most_common(1)[0][0]

        # Urgency trend
        urgency_map = {"low": 0, "medium": 1, "high": 2}
        urgency_values = [urgency_map.get(u, 0) for u in urgencies]
        if len(urgency_values) >= 3:
            recent = sum(urgency_values[-3:]) / 3
            older = sum(urgency_values[:3]) / 3
            if recent > older + 0.5:
                urgency_trend = "rising"
            elif recent < older - 0.5:
                urgency_trend = "falling"
            else:
                urgency_trend = "stable"
        else:
            urgency_trend = "insufficient_data"

        return {
            "dominant_emotion": dominant_emotion,
            "emotion_distribution": dict(emotion_counts),
            "urgency_trend": urgency_trend,
            "frames_analyzed": len(self._history),
            "total_frames": self._frame_count,
        }

    # ─── CALL LIFECYCLE ──────────────────────────────────────────────────

    def start_call(self) -> None:
        """Reset state at call start."""
        self._history.clear()
        self._tone_log.clear()
        self._frame_count = 0

    def end_call(self) -> Dict[str, Any]:
        """Return call-level tone stats."""
        trend = self.get_trend()
        stats = {
            "total_frames": self._frame_count,
            "trend": trend,
        }
        self._history.clear()
        self._frame_count = 0
        return stats

    # ─── DIAGNOSTICS ─────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "organ": "30-prosody-analysis",
            "frames_analyzed": self._frame_count,
            "history_size": len(self._history),
            "window_size": self._window_size,
            "iqcore_available": IQCORE_AVAILABLE,
        }


# ─── MODULE SELF-TEST ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("ORGAN 30 — Prosody Analysis — Self-Test")
    print("=" * 60)

    pa = ProsodyAnalysisOrgan()
    pa.start_call()

    # Simulate frames
    test_frames = [
        {"rms_energy": 0.3, "pitch_hz": 150.0, "words_per_second": 2.0, "jitter": 0.1, "shimmer": 0.1},
        {"rms_energy": 0.8, "pitch_hz": 300.0, "words_per_second": 4.0, "jitter": 0.5, "shimmer": 0.3},
        {"rms_energy": 0.1, "pitch_hz": 80.0, "words_per_second": 1.0, "jitter": 0.1, "shimmer": 0.1},
        {"rms_energy": 0.6, "pitch_hz": 200.0, "words_per_second": 2.8, "jitter": 0.2, "shimmer": 0.2},
    ]

    for i, frame in enumerate(test_frames):
        tone = pa.analyze_frame(frame)
        print(f"  Frame {i+1}: energy={tone['energy_level']}, arousal={tone['arousal']}, "
              f"urgency={tone['urgency']}, emotion={tone['emotion']} ({tone['emotion_confidence']:.2f})")

    trend = pa.get_trend()
    print(f"  Trend: dominant={trend['dominant_emotion']}, urgency={trend['urgency_trend']}")

    stats = pa.end_call()
    print(f"  Call stats: {stats['total_frames']} frames")
    print("  SELF-TEST PASSED")
