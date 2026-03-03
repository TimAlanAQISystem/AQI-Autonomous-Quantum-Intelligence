# voice_sensitizer.py
"""
Voice Sensitizer -- Real-Time Voice Identity Integrity Monitor
==============================================================
Monitors Alan's voice output to ensure:
  - Voice identity integrity (spectral similarity to baseline)
  - Prosody within expected persona ranges
  - Automatic correction on severe drift
  - Kill switch on catastrophic voice failure

Architecture:
  1. Per-window analysis: each TTS audio chunk is analyzed for drift
  2. Drift classification: none -> mild -> moderate -> severe -> catastrophic
  3. Action dispatch: log_only -> log_and_warn -> adjust_tts_params -> abort_call_and_alert
  4. Post-call summary: aggregate drift stats written to CDC

Integration:
  - Real-time: called per TTS audio window in the streaming path
  - Post-call: summary written to CDC at call finalization

Author: Claude Opus 4.6 - AQI System Expert
Date: February 18, 2026
"""

import json
import os
import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("VoiceSensitizer")

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class VoiceWindowMetrics:
    """Metrics extracted from a single TTS audio window."""
    spectral_similarity: float   # 0-1 (1 = identical to baseline)
    pitch_variance: float        # normalized variance of pitch
    energy_variance: float       # normalized variance of energy
    speaking_rate_wpm: float     # estimated words per minute


@dataclass
class VoiceDriftEvent:
    """A single drift event detected in a window."""
    window_index: int
    drift_score: float
    severity: str
    action_taken: str


# =============================================================================
# DEFAULT CONFIG (fallback if YAML not loaded)
# =============================================================================

DEFAULT_VOICE_SENSITIZER_CONFIG = {
    "thresholds": {
        "mild_drift": 0.15,
        "moderate_drift": 0.25,
        "severe_drift": 0.35,
        "catastrophic_drift": 0.45,
        "min_pitch_variance": 0.05,
        "max_pitch_variance": 0.40,
        "min_energy_variance": 0.05,
        "max_energy_variance": 0.50,
        "min_speaking_rate_wpm": 110,
        "max_speaking_rate_wpm": 190,
    },
    "actions": {
        "on_mild_drift": "log_only",
        "on_moderate_drift": "log_and_warn",
        "on_severe_drift": "adjust_tts_params",
        "on_catastrophic_drift": "abort_call_and_alert",
    },
    "tts_adjustments": {
        "stability_delta": -0.1,
        "similarity_boost_delta": 0.1,
        "speaking_rate_delta": -0.05,
    },
    "baseline": {
        "voiceprint_path": "baselines/alan_voiceprint.json",
        "prosody_profile_path": "baselines/alan_prosody_profile.json",
    },
    "logging": {
        "enable_per_window_logging": False,
        "enable_per_call_summary": True,
    },
}


# =============================================================================
# VOICE SENSITIZER CONFIG
# =============================================================================

class VoiceSensitizerConfig:
    """Loads and holds voice sensitizer configuration."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, path: Optional[str] = None):
        """
        Initialize from a dict (preferred) or YAML file path.
        Falls back to DEFAULT_VOICE_SENSITIZER_CONFIG if neither provided.
        """
        if config:
            cfg = config
        elif path and os.path.exists(path):
            try:
                import yaml
                with open(path, "r") as f:
                    cfg = yaml.safe_load(f)
            except ImportError:
                logger.warning("[VOICE-SENS] PyYAML not installed, using default config")
                cfg = DEFAULT_VOICE_SENSITIZER_CONFIG
            except Exception as e:
                logger.warning(f"[VOICE-SENS] Failed to load {path}: {e}, using default")
                cfg = DEFAULT_VOICE_SENSITIZER_CONFIG
        else:
            cfg = DEFAULT_VOICE_SENSITIZER_CONFIG

        self.thresholds = cfg.get("thresholds", DEFAULT_VOICE_SENSITIZER_CONFIG["thresholds"])
        self.actions = cfg.get("actions", DEFAULT_VOICE_SENSITIZER_CONFIG["actions"])
        self.tts_adjustments = cfg.get("tts_adjustments", DEFAULT_VOICE_SENSITIZER_CONFIG["tts_adjustments"])
        self.baseline_paths = cfg.get("baseline", DEFAULT_VOICE_SENSITIZER_CONFIG["baseline"])
        self.logging = cfg.get("logging", DEFAULT_VOICE_SENSITIZER_CONFIG["logging"])


# =============================================================================
# VOICE SENSITIZER ENGINE
# =============================================================================

class VoiceSensitizer:
    """
    Monitors Alan's voice in real time to ensure:
      - Voice identity integrity (spectral similarity to baseline)
      - Prosody within expected persona ranges
      - Automatic correction / abort on severe drift

    Usage:
      config = VoiceSensitizerConfig()
      vs = VoiceSensitizer(config)

      # Per-window (real-time):
      result = vs.analyze_window_and_maybe_correct(window_metrics)

      # Post-call (summary):
      summary = vs.analyze_call(call_id, all_windows)
    """

    def __init__(self, config: VoiceSensitizerConfig):
        self.cfg = config
        self.baseline_voiceprint = self._load_json(self.cfg.baseline_paths.get("voiceprint_path", ""))
        self.baseline_prosody = self._load_json(self.cfg.baseline_paths.get("prosody_profile_path", ""))
        # Per-call window accumulator (reset per call)
        self._call_windows: List[VoiceWindowMetrics] = []
        self._drift_events: List[VoiceDriftEvent] = []

    def _load_json(self, path: str) -> Dict[str, Any]:
        """Load a JSON baseline file. Returns empty dict if not found."""
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"[VOICE-SENS] Could not load baseline {path}: {e}")
            return {}

    def reload_config(self, config: Dict[str, Any]):
        """Hot-reload config from dict (e.g., from ClassifierConfigLoader)."""
        self.cfg = VoiceSensitizerConfig(config=config)

    def reset_call(self):
        """Reset per-call accumulators. Call at start of each new call."""
        self._call_windows = []
        self._drift_events = []

    # -----------------------------------------------------------------
    # PUBLIC: Per-window analysis (real-time path)
    # -----------------------------------------------------------------

    def analyze_window_and_maybe_correct(self, window: VoiceWindowMetrics) -> Dict[str, Any]:
        """
        Real-time path: called per TTS audio window during a call.

        Returns:
          - severity: none/mild/moderate/severe/catastrophic
          - drift_score: 0-1
          - action: what was done
          - tts_adjustments: dict of TTS param deltas (if severe)
          - prosody_flags: list of prosody issues in this window
        """
        drift_score = self._compute_drift_score(window)
        severity = self._classify_severity(drift_score)
        action = self._action_for_severity(severity)

        tts_adjustments = {}
        if action == "adjust_tts_params":
            tts_adjustments = dict(self.cfg.tts_adjustments)

        prosody_ok, prosody_reasons = self._check_prosody(window)

        # Accumulate for post-call summary
        self._call_windows.append(window)
        if severity != "none":
            event = VoiceDriftEvent(
                window_index=len(self._call_windows) - 1,
                drift_score=drift_score,
                severity=severity,
                action_taken=action,
            )
            self._drift_events.append(event)

        if self.cfg.logging.get("enable_per_window_logging", False):
            logger.info(
                f"[VOICE-SENS] Window {len(self._call_windows)}: "
                f"drift={drift_score:.3f} severity={severity} action={action}"
            )

        return {
            "drift_score": drift_score,
            "severity": severity,
            "action": action,
            "tts_adjustments": tts_adjustments,
            "prosody_flags": prosody_reasons,
        }

    # -----------------------------------------------------------------
    # PUBLIC: Post-call analysis
    # -----------------------------------------------------------------

    def analyze_call(self, call_id: str, windows: Optional[List[VoiceWindowMetrics]] = None) -> Dict[str, Any]:
        """
        Post-call analysis. If windows is None, uses accumulated windows from
        analyze_window_and_maybe_correct calls.

        Returns a summary dict suitable for CDC storage.
        """
        if windows is not None:
            # Full batch mode -- re-analyze all windows
            return self._batch_analyze(call_id, windows)

        # Use accumulated data
        drift_scores = [self._compute_drift_score(w) for w in self._call_windows]
        avg_drift = sum(drift_scores) / len(drift_scores) if drift_scores else 0.0
        max_drift = max(drift_scores) if drift_scores else 0.0

        # Collect prosody flags
        prosody_flags = []
        for idx, w in enumerate(self._call_windows):
            ok, reasons = self._check_prosody(w)
            if not ok:
                prosody_flags.append({"window_index": idx, "reason": reasons})

        summary = {
            "call_id": call_id,
            "total_windows": len(self._call_windows),
            "avg_drift": round(avg_drift, 4),
            "max_drift": round(max_drift, 4),
            "drift_events": [asdict(e) for e in self._drift_events],
            "drift_event_count": len(self._drift_events),
            "prosody_flags": prosody_flags,
            "prosody_flag_count": len(prosody_flags),
        }

        if self.cfg.logging.get("enable_per_call_summary", True):
            logger.info(
                f"[VOICE-SENS] Call {call_id[:16]}: "
                f"windows={len(self._call_windows)} "
                f"avg_drift={avg_drift:.4f} max_drift={max_drift:.4f} "
                f"events={len(self._drift_events)} prosody_flags={len(prosody_flags)}"
            )

        return summary

    def _batch_analyze(self, call_id: str, windows: List[VoiceWindowMetrics]) -> Dict[str, Any]:
        """Batch-analyze a list of windows (post-hoc mode)."""
        drift_events = []
        drift_scores = []
        prosody_flags = []

        for idx, w in enumerate(windows):
            drift_score = self._compute_drift_score(w)
            drift_scores.append(drift_score)

            severity = self._classify_severity(drift_score)
            action = self._action_for_severity(severity)

            if severity != "none":
                drift_events.append(
                    VoiceDriftEvent(
                        window_index=idx,
                        drift_score=drift_score,
                        severity=severity,
                        action_taken=action,
                    )
                )

            prosody_ok, prosody_reasons = self._check_prosody(w)
            if not prosody_ok:
                prosody_flags.append({"window_index": idx, "reason": prosody_reasons})

        avg_drift = sum(drift_scores) / len(drift_scores) if drift_scores else 0.0
        max_drift = max(drift_scores) if drift_scores else 0.0

        return {
            "call_id": call_id,
            "total_windows": len(windows),
            "avg_drift": round(avg_drift, 4),
            "max_drift": round(max_drift, 4),
            "drift_events": [asdict(e) for e in drift_events],
            "drift_event_count": len(drift_events),
            "prosody_flags": prosody_flags,
            "prosody_flag_count": len(prosody_flags),
        }

    # -----------------------------------------------------------------
    # INTERNALS
    # -----------------------------------------------------------------

    def _compute_drift_score(self, w: VoiceWindowMetrics) -> float:
        """
        Core drift computation.
        Base drift = 1 - spectral_similarity (how far from baseline identity).
        Prosody penalty = additional penalty for out-of-range prosody.
        Total capped at 1.0.
        """
        base_drift = 1.0 - max(0.0, min(1.0, w.spectral_similarity))
        prosody_penalty = self._prosody_deviation_penalty(w)
        return min(1.0, base_drift + prosody_penalty)

    def _prosody_deviation_penalty(self, w: VoiceWindowMetrics) -> float:
        """Compute prosody penalty (0.05 per out-of-range dimension)."""
        t = self.cfg.thresholds
        penalty = 0.0

        if w.pitch_variance < t.get("min_pitch_variance", 0.05) or \
           w.pitch_variance > t.get("max_pitch_variance", 0.40):
            penalty += 0.05

        if w.energy_variance < t.get("min_energy_variance", 0.05) or \
           w.energy_variance > t.get("max_energy_variance", 0.50):
            penalty += 0.05

        if w.speaking_rate_wpm < t.get("min_speaking_rate_wpm", 110) or \
           w.speaking_rate_wpm > t.get("max_speaking_rate_wpm", 190):
            penalty += 0.05

        return penalty

    def _classify_severity(self, drift_score: float) -> str:
        """Classify drift score into severity level."""
        t = self.cfg.thresholds
        if drift_score >= t.get("catastrophic_drift", 0.45):
            return "catastrophic"
        if drift_score >= t.get("severe_drift", 0.35):
            return "severe"
        if drift_score >= t.get("moderate_drift", 0.25):
            return "moderate"
        if drift_score >= t.get("mild_drift", 0.15):
            return "mild"
        return "none"

    def _action_for_severity(self, severity: str) -> str:
        """Map severity to action."""
        a = self.cfg.actions
        action_map = {
            "mild": a.get("on_mild_drift", "log_only"),
            "moderate": a.get("on_moderate_drift", "log_and_warn"),
            "severe": a.get("on_severe_drift", "adjust_tts_params"),
            "catastrophic": a.get("on_catastrophic_drift", "abort_call_and_alert"),
        }
        return action_map.get(severity, "none")

    def _check_prosody(self, w: VoiceWindowMetrics) -> Tuple[bool, List[str]]:
        """Check prosody dimensions against expected ranges."""
        t = self.cfg.thresholds
        reasons = []

        if w.pitch_variance < t.get("min_pitch_variance", 0.05):
            reasons.append("pitch_too_flat")
        elif w.pitch_variance > t.get("max_pitch_variance", 0.40):
            reasons.append("pitch_too_erratic")

        if w.energy_variance < t.get("min_energy_variance", 0.05):
            reasons.append("energy_too_flat")
        elif w.energy_variance > t.get("max_energy_variance", 0.50):
            reasons.append("energy_too_erratic")

        if w.speaking_rate_wpm < t.get("min_speaking_rate_wpm", 110):
            reasons.append("too_slow")
        elif w.speaking_rate_wpm > t.get("max_speaking_rate_wpm", 190):
            reasons.append("too_fast")

        return (len(reasons) == 0, reasons)
