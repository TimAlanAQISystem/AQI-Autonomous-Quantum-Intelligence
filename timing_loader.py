"""
TIMING LOADER — Single source of truth for all Alan timing values.

Reads timing_config.json once at import time and exports validated values.
Every production file imports from HERE instead of hardcoding constants.

Usage:
    from timing_loader import TIMING
    
    speed = TIMING.tts_default_speed        # 1.12
    cap   = TIMING.max_sentences            # 5
    tempo = TIMING.tempo_multiplier         # 1.06
    prosody = TIMING.prosody_speed_map      # dict of intent→speed
    
    # Or access the raw dict:
    ring_timeout = TIMING.get("call_pacing", "ring_timeout")  # 50
"""

import json
import os
import logging

logger = logging.getLogger("TIMING")

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "timing_config.json")


def _load_config() -> dict:
    """Load and validate timing_config.json."""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        logger.info(f"[TIMING] Loaded timing config v{raw.get('_meta', {}).get('version', '?')}")
        return raw
    except FileNotFoundError:
        logger.error(f"[TIMING] timing_config.json NOT FOUND at {_CONFIG_PATH} — using hardcoded fallbacks")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"[TIMING] timing_config.json PARSE ERROR: {e} — using hardcoded fallbacks")
        return {}


def _extract(raw: dict, section: str, key: str, fallback):
    """Extract a value from config with bounds validation."""
    section_data = raw.get(section, {})
    entry = section_data.get(key, {})
    
    if isinstance(entry, dict) and "value" in entry:
        val = entry["value"]
        lo = entry.get("min")
        hi = entry.get("max")
        if lo is not None and val < lo:
            logger.warning(f"[TIMING] {section}.{key} = {val} below min {lo}, clamping")
            val = lo
        if hi is not None and val > hi:
            logger.warning(f"[TIMING] {section}.{key} = {val} above max {hi}, clamping")
            val = hi
        return val
    elif isinstance(entry, (int, float, str)):
        # Direct value (no min/max wrapper) — e.g., prosody_speed_map entries
        return entry
    else:
        logger.warning(f"[TIMING] Missing {section}.{key}, using fallback: {fallback}")
        return fallback


class TimingConfig:
    """Validated, immutable timing configuration."""

    def __init__(self):
        self._raw = _load_config()
        self._loaded = bool(self._raw)
        
        # === VOICE PACING ===
        vp = "voice_pacing"
        self.tempo_multiplier     = _extract(self._raw, vp, "tempo_multiplier", 1.06)
        self.tts_default_speed    = _extract(self._raw, vp, "tts_default_speed", 1.12)
        self.max_sentences        = int(_extract(self._raw, vp, "max_sentences", 5))
        self.question_cap_per_turn = int(_extract(self._raw, vp, "question_cap_per_turn", 1))
        
        # === PROSODY SPEED MAP ===
        psm = self._raw.get("prosody_speed_map", {})
        self.prosody_speed_map = {
            k: v for k, v in psm.items() if not k.startswith("_")
        }
        if not self.prosody_speed_map:
            # Hardcoded fallback — must match relay server originals
            self.prosody_speed_map = {
                "neutral":             1.12,
                "empathetic_reflect":  1.02,
                "reassure_stability":  1.06,
                "confident_recommend": 1.08,
                "curious_probe":       1.16,
                "casual_rapport":      1.12,
                "micro_hesitate":      1.10,
                "objection_handling":  1.06,
                "formal_respectful":   1.08,
                "turn_yield":          1.08,
                "repair_clarify":      1.08,
                "closing_momentum":    1.14,
            }
            logger.warning("[TIMING] prosody_speed_map missing — using hardcoded fallback")
        
        # === TURN TIMING ===
        tt = "turn_timing"
        self.turn_timeout = _extract(self._raw, tt, "turn_timeout", 3.0)
        
        # === LLM PARAMETERS ===
        llm = "llm_parameters"
        self.relay_max_tokens   = int(_extract(self._raw, llm, "relay_max_tokens", 80))
        self.direct_max_tokens  = int(_extract(self._raw, llm, "direct_max_tokens", 150))
        self.temperature        = _extract(self._raw, llm, "temperature", 0.5)
        self.frequency_penalty  = _extract(self._raw, llm, "frequency_penalty", 0.5)
        
        # === CALL PACING ===
        cp = "call_pacing"
        self.ring_timeout       = int(_extract(self._raw, cp, "ring_timeout", 50))
        self.post_call_cooldown = int(_extract(self._raw, cp, "post_call_cooldown", 30))
        self.campaign_cooldown  = int(_extract(self._raw, cp, "campaign_cooldown", 150))
        self.machine_detection  = _extract(self._raw, cp, "machine_detection", "Enable")
        
        # === HEALTH MONITORING ===
        hm = "health_monitoring"
        self.health_check_interval = int(_extract(self._raw, hm, "health_check_interval", 30))
        self.deep_check_interval   = int(_extract(self._raw, hm, "deep_check_interval", 150))
        
        # === BREATH PATTERNS ===
        bp = self._raw.get("breath_patterns", {})
        self.breath_patterns = bp.get("patterns", [
            {"type": "inhale",  "duration_ms": 100, "peak_amp": 0.008},
            {"type": "inhale",  "duration_ms": 130, "peak_amp": 0.010},
            {"type": "inhale",  "duration_ms": 80,  "peak_amp": 0.006},
            {"type": "exhale",  "duration_ms": 140, "peak_amp": 0.007},
            {"type": "exhale",  "duration_ms": 110, "peak_amp": 0.009},
        ])

        # === PROSODY SILENCE FRAMES (per-intent inter-sentence silence) ===
        psf = self._raw.get("prosody_silence_frames", {})
        self.prosody_silence_frames = {
            k: v for k, v in psf.items() if not k.startswith("_") and k != "frame_duration_ms"
        }
        self.silence_frame_duration_ms = psf.get("frame_duration_ms", 20)
        if not self.prosody_silence_frames:
            # Hardcoded fallback — research-backed defaults (Stivers/Gong)
            self.prosody_silence_frames = {
                "neutral":             10,
                "empathetic_reflect":  14,
                "reassure_stability":  12,
                "confident_recommend":  8,
                "curious_probe":        7,
                "casual_rapport":       5,
                "micro_hesitate":       6,
                "objection_handling":  15,
                "formal_respectful":    7,
                "turn_yield":           4,
                "repair_clarify":      10,
                "closing_momentum":     5,
            }
            logger.warning("[TIMING] prosody_silence_frames missing — using hardcoded fallback")

        # === SILENCE THRESHOLDS (conversation science boundaries) ===
        st = "silence_thresholds"
        self.trouble_threshold_ms   = int(_extract(self._raw, st, "trouble_threshold_ms", 700))
        self.standard_max_silence_ms = int(_extract(self._raw, st, "standard_max_silence_ms", 1000))

    def get(self, section: str, key: str, fallback=None):
        """Generic accessor for any config value."""
        return _extract(self._raw, section, key, fallback)

    def summary(self) -> str:
        """Human-readable summary for logs."""
        return (
            f"[TIMING] Loaded={'YES' if self._loaded else 'FALLBACK'} | "
            f"tempo={self.tempo_multiplier} | tts_speed={self.tts_default_speed} | "
            f"max_sent={self.max_sentences} | q_cap={self.question_cap_per_turn} | "
            f"turn_timeout={self.turn_timeout}s | relay_tokens={self.relay_max_tokens} | "
            f"cooldown={self.post_call_cooldown}s | ring={self.ring_timeout}s | "
            f"silence_frames={len(self.prosody_silence_frames)} intents | "
            f"trouble_thresh={self.trouble_threshold_ms}ms | max_silence={self.standard_max_silence_ms}ms"
        )


# === SINGLETON — Import once, use everywhere ===
TIMING = TimingConfig()

if TIMING._loaded:
    logger.info(TIMING.summary())
