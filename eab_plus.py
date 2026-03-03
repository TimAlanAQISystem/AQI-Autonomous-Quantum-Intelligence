"""
+==============================================================================+
|   EAB-PLUS — Advanced Environment-Aware Behavior                              |
|   AQI Agent Alan --- Environment-Fluent Detection System                      |
|                                                                               |
|   PURPOSE:                                                                    |
|   Upgrade from "environment-aware" to "environment-fluent" by adding          |
|   secondary detectors and predictors that refine env.class, env.action,       |
|   and env.behavior over time and across turns.                                |
|                                                                               |
|   LAYERS (stacked on existing EAB spine):                                     |
|     1. Prosody Engine — human vs machine, emotional tone, interrupt intent    |
|     2. Silence-Pattern Classifier — machine silence, voicemail, beep          |
|     3. Timing-Fingerprint Detector — environment timing signatures            |
|     4. Human-Interrupt Detector — stop-talking reflex                         |
|     5. Hang-Up Prediction Model — shorten/shift before loss                   |
|     6. Vertical-Aware Predictor — env priors by merchant vertical             |
|     7. State-Aware Predictor — env priors by geography                        |
|     8. Lead-History Predictor — env priors by past calls to same number       |
|                                                                               |
|   CORE IDEA:                                                                  |
|   env.class becomes a COMPOSITE DECISION:                                     |
|     env.class = f(                                                            |
|       first_utterance_text, prosody_features, silence_pattern,                |
|       timing_fingerprint, device_type, vertical_prior,                        |
|       state_prior, lead_history_prior, multi_turn_observations                |
|     )                                                                         |
|                                                                               |
|   The existing rule-based classifier remains the spine.                       |
|   Each new module contributes SIGNALS and PRIORS, not hard overrides.         |
|                                                                               |
|   LINEAGE: Built 2026-02-20. Tim's EAB-Plus architecture spec.               |
|   INTEGRATES WITH: EnvironmentClass, CallEnvironmentClassifier,               |
|                    Phase 4 / Phase 5 telemetry, EAB core routing              |
+==============================================================================+
"""

import math
import struct
import logging
import time
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger("EAB_PLUS")


# ======================================================================
#  1. PROSODY ENGINE
#     Distinguish human vs machine, detect emotional tone,
#     support interrupt / hang-up prediction.
# ======================================================================

@dataclass
class ProsodyFeatures:
    """Lightweight feature vector extracted from raw audio."""
    pitch_variance: float = 0.0        # Hz std dev (proxy via zero-crossing)
    energy_variance: float = 0.0       # RMS variance over windows
    speaking_rate: float = 0.0         # frames-per-second with energy above floor
    pause_count: int = 0               # number of micro-pauses (gaps > 60ms)
    jitter: float = 0.0               # pitch period perturbation proxy
    shimmer: float = 0.0              # amplitude perturbation proxy
    mean_energy: float = 0.0          # average RMS
    max_energy: float = 0.0           # peak RMS
    duration_ms: float = 0.0          # total audio length


class ProsodyEngine:
    """
    Extract lightweight prosody features from raw 8kHz mulaw audio.
    Non-blocking, DSP-only — no external API calls.
    """

    # === Thresholds (tunable) ===
    WINDOW_MS = 20           # analysis window size
    ENERGY_FLOOR = 50        # below this = silence / micro-pause
    HUMAN_PITCH_VAR_MIN = 15.0   # humans have higher pitch variance
    MACHINE_PITCH_VAR_MAX = 8.0  # machines are monotone

    # Emotion energy signatures (relative to mean)
    BUSY_ENERGY_RATIO = 1.4       # speaking fast + loud
    ANNOYED_PITCH_VAR_MIN = 25.0  # high pitch variation
    CURIOUS_PAUSE_RATIO = 0.25    # more pauses (thinking)

    def extract(self, audio_frames: bytes, sample_rate: int = 8000) -> ProsodyFeatures:
        """
        Extract lightweight prosody features from raw audio bytes.
        Expects linear PCM int16 or mulaw-decoded frames.

        Non-blocking, pure DSP.
        """
        pf = ProsodyFeatures()

        if not audio_frames or len(audio_frames) < 320:  # < 20ms at 8kHz 16-bit
            return pf

        # Decode audio to int16 samples
        try:
            samples = self._decode_audio(audio_frames)
        except Exception:
            return pf

        if len(samples) < 160:  # need at least 20ms
            return pf

        pf.duration_ms = (len(samples) / sample_rate) * 1000

        # Windowed analysis
        window_size = int(sample_rate * self.WINDOW_MS / 1000)
        energies = []
        zcr_values = []  # zero-crossing rate (pitch proxy)
        pauses = 0
        active_frames = 0

        for i in range(0, len(samples) - window_size, window_size):
            window = samples[i:i + window_size]

            # RMS energy
            rms = math.sqrt(sum(s * s for s in window) / len(window))
            energies.append(rms)

            if rms < self.ENERGY_FLOOR:
                pauses += 1
            else:
                active_frames += 1

            # Zero-crossing rate (proxy for pitch)
            zcr = sum(1 for j in range(1, len(window)) if
                      (window[j] >= 0) != (window[j-1] >= 0))
            zcr_values.append(zcr)

        if not energies:
            return pf

        # Compute features
        pf.mean_energy = sum(energies) / len(energies)
        pf.max_energy = max(energies)
        pf.pause_count = pauses

        if len(energies) > 1:
            mean_e = pf.mean_energy
            pf.energy_variance = math.sqrt(
                sum((e - mean_e) ** 2 for e in energies) / (len(energies) - 1)
            )

        if zcr_values and len(zcr_values) > 1:
            mean_zcr = sum(zcr_values) / len(zcr_values)
            pf.pitch_variance = math.sqrt(
                sum((z - mean_zcr) ** 2 for z in zcr_values) / (len(zcr_values) - 1)
            )

            # Jitter proxy: pitch period perturbation
            diffs = [abs(zcr_values[i] - zcr_values[i-1]) for i in range(1, len(zcr_values))]
            pf.jitter = sum(diffs) / len(diffs) if diffs else 0.0

        # Shimmer proxy: amplitude perturbation
        if len(energies) > 1:
            amp_diffs = [abs(energies[i] - energies[i-1]) for i in range(1, len(energies))]
            pf.shimmer = sum(amp_diffs) / len(amp_diffs) if amp_diffs else 0.0

        # Speaking rate: active frames per second
        total_windows = len(energies)
        if total_windows > 0:
            pf.speaking_rate = active_frames / (total_windows * self.WINDOW_MS / 1000)

        return pf

    def classify(self, pf: ProsodyFeatures) -> Dict[str, float]:
        """
        Classify prosody features into human/machine probability and emotion.

        Returns:
            {
                "is_human": float [0,1],
                "emotion_busy": float [0,1],
                "emotion_annoyed": float [0,1],
                "emotion_curious": float [0,1],
                "emotion_distracted": float [0,1],
                "interrupt_intent": float [0,1]
            }
        """
        result = {
            "is_human": 0.5,
            "emotion_busy": 0.0,
            "emotion_annoyed": 0.0,
            "emotion_curious": 0.0,
            "emotion_distracted": 0.0,
            "interrupt_intent": 0.0,
        }

        if pf.duration_ms < 100:  # not enough audio
            return result

        # --- Human vs Machine ---
        # Humans have higher pitch variance, energy variance, and micro-pauses
        human_score = 0.5

        # Pitch variance signal
        if pf.pitch_variance > self.HUMAN_PITCH_VAR_MIN:
            human_score += 0.15
        elif pf.pitch_variance < self.MACHINE_PITCH_VAR_MAX:
            human_score -= 0.15

        # Energy variance signal (humans vary loudness)
        if pf.energy_variance > 100:
            human_score += 0.10
        elif pf.energy_variance < 30:
            human_score -= 0.10

        # Shimmer signal (humans have more amplitude perturbation)
        if pf.shimmer > 50:
            human_score += 0.10
        elif pf.shimmer < 15:
            human_score -= 0.10

        # Jitter signal (humans have more pitch perturbation)
        if pf.jitter > 3.0:
            human_score += 0.10
        elif pf.jitter < 1.0:
            human_score -= 0.10

        # Micro-pauses (humans pause; machines are continuous)
        total_windows = int(pf.duration_ms / self.WINDOW_MS)
        if total_windows > 0:
            pause_ratio = pf.pause_count / total_windows
            if 0.10 < pause_ratio < 0.40:
                human_score += 0.05  # natural breathing pauses
            elif pause_ratio < 0.05:
                human_score -= 0.10  # machine: continuous output

        result["is_human"] = max(0.0, min(1.0, human_score))

        # --- Emotion detection ---
        if pf.mean_energy > 0:
            energy_ratio = pf.max_energy / pf.mean_energy

            # BUSY: high speaking rate + high energy
            if pf.speaking_rate > 40 and energy_ratio > self.BUSY_ENERGY_RATIO:
                result["emotion_busy"] = min(0.8, (pf.speaking_rate - 30) / 30)

            # ANNOYED: high pitch variance + high energy
            if pf.pitch_variance > self.ANNOYED_PITCH_VAR_MIN and energy_ratio > 1.2:
                result["emotion_annoyed"] = min(0.8,
                    (pf.pitch_variance - self.ANNOYED_PITCH_VAR_MIN) / 30)

        # CURIOUS: moderate pauses (thinking)
        if total_windows > 0:
            pause_ratio = pf.pause_count / total_windows
            if pause_ratio > self.CURIOUS_PAUSE_RATIO:
                result["emotion_curious"] = min(0.6, pause_ratio / 0.5)

        # DISTRACTED: low energy + irregular pauses
        if pf.mean_energy < self.ENERGY_FLOOR * 2 and pf.pause_count > 3:
            result["emotion_distracted"] = 0.4

        return result

    def _decode_audio(self, audio_bytes: bytes) -> List[int]:
        """
        Decode audio bytes to int16 samples.
        Tries int16 PCM first, falls back to mulaw decode.
        """
        if len(audio_bytes) % 2 == 0:
            # Try as int16 PCM
            try:
                count = len(audio_bytes) // 2
                samples = list(struct.unpack(f'<{count}h', audio_bytes))
                # Sanity check: if values are reasonable, it's PCM
                if any(abs(s) > 100 for s in samples[:50]):
                    return samples
            except struct.error:
                pass

        # Fallback: mulaw decode
        return [self._mulaw_decode(b) for b in audio_bytes]

    @staticmethod
    def _mulaw_decode(byte_val: int) -> int:
        """Decode a single mulaw byte to int16."""
        BIAS = 0x84
        byte_val = ~byte_val & 0xFF
        sign = byte_val & 0x80
        exponent = (byte_val >> 4) & 0x07
        mantissa = byte_val & 0x0F
        sample = ((mantissa << 3) + BIAS) << exponent
        sample -= BIAS
        if sign:
            sample = -sample
        return sample


# ======================================================================
#  2. SILENCE PATTERN CLASSIFIER
#     Distinguish human vs machine silence, voicemail vs live,
#     early environment hints from noise/beep patterns.
# ======================================================================

class SilencePatternClassifier:
    """
    Analyze silence/noise patterns to detect machine vs human environments.

    Features:
    - Background noise floor level
    - Micro-noise presence (breath, rustle) → human
    - Regularity of silence (perfect = machine, imperfect = human)
    - Beep detection (voicemail, call screen)
    """

    BEEP_FREQ_LOW = 800     # Hz — typical voicemail beep range
    BEEP_FREQ_HIGH = 2000   # Hz
    BEEP_MIN_DURATION = 30  # ms
    BEEP_MAX_DURATION = 500 # ms
    NOISE_FLOOR_THRESHOLD = 40  # RMS below this = clean silence

    def analyze(self, silence_frames: bytes, sample_rate: int = 8000) -> Dict[str, float]:
        """
        Detect machine-like silence, voicemail beeps, micro-noises.

        Args:
            silence_frames: Raw audio bytes during silence period.
            sample_rate: Audio sample rate in Hz.

        Returns:
            {
                "is_machine": float [0,1],
                "is_voicemail": float [0,1],
                "has_beep": float [0,1],
                "noise_floor": float,
                "micro_noise_count": int
            }
        """
        result = {
            "is_machine": 0.0,
            "is_voicemail": 0.0,
            "has_beep": 0.0,
            "noise_floor": 0.0,
            "micro_noise_count": 0,
        }

        if not silence_frames or len(silence_frames) < 160:
            return result

        # Decode to samples
        try:
            if len(silence_frames) % 2 == 0:
                count = len(silence_frames) // 2
                samples = list(struct.unpack(f'<{count}h', silence_frames))
            else:
                samples = [ProsodyEngine._mulaw_decode(b) for b in silence_frames]
        except Exception:
            return result

        if len(samples) < 80:
            return result

        # --- Noise floor ---
        window_size = int(sample_rate * 0.020)  # 20ms windows
        energies = []
        for i in range(0, len(samples) - window_size, window_size):
            window = samples[i:i + window_size]
            rms = math.sqrt(sum(s * s for s in window) / len(window))
            energies.append(rms)

        if not energies:
            return result

        noise_floor = sum(energies) / len(energies)
        result["noise_floor"] = noise_floor

        # --- Machine vs human silence ---
        # Perfect silence (near-zero noise) = machine / digital
        # Slight noise with variation = human environment (breath, room tone)
        if noise_floor < self.NOISE_FLOOR_THRESHOLD:
            # Very clean silence: likely machine/digital
            if len(energies) > 1:
                energy_var = math.sqrt(
                    sum((e - noise_floor) ** 2 for e in energies) / (len(energies) - 1)
                )
                if energy_var < 10:
                    result["is_machine"] = 0.7
                else:
                    result["is_machine"] = 0.3
        else:
            # Some background noise: likely human environment
            result["is_machine"] = 0.1

        # --- Micro-noise detection ---
        # Count windows with energy spikes above 2x noise floor
        micro_noise_threshold = max(noise_floor * 2.0, 60)
        micro_noises = sum(1 for e in energies if e > micro_noise_threshold)
        result["micro_noise_count"] = micro_noises

        # Micro-noises suggest human (breathing, shuffling)
        if micro_noises > 0 and micro_noises < len(energies) * 0.3:
            result["is_machine"] = max(0.0, result["is_machine"] - 0.2)

        # --- Beep detection ---
        # Look for sudden energy spike characteristic of a beep
        beep_detected = self._detect_beep(energies, window_size, sample_rate)
        if beep_detected:
            result["has_beep"] = 0.8
            result["is_voicemail"] = 0.7

        return result

    def _detect_beep(self, energies: List[float], window_size: int,
                     sample_rate: int) -> bool:
        """
        Simple beep detection: look for a short, sharp energy spike
        followed by silence.
        """
        if len(energies) < 5:
            return False

        mean_energy = sum(energies) / len(energies)
        threshold = max(mean_energy * 4.0, 200)

        for i in range(len(energies) - 2):
            # Spike: high energy surrounded by low energy
            if (energies[i] < mean_energy * 1.5 and
                energies[i + 1] > threshold and
                i + 3 < len(energies) and
                energies[i + 3] < mean_energy * 1.5):
                return True

        return False


# ======================================================================
#  3. TIMING FINGERPRINT DETECTOR
#     Pre-classify environment using timing signatures.
# ======================================================================

class TimingFingerprintDetector:
    """
    Use timing signatures to pre-classify environment before or alongside STT.

    Timing patterns:
    - Google Call Screen: 1.2-1.7s delay to first speech
    - Voicemail: immediate beep or long ring then speech
    - Human: <500ms to first speech
    - IVR: 200-800ms to first speech, then structured prompts
    """

    # Known timing signatures (tunable)
    SIGNATURES = {
        "GOOGLE_CALL_SCREEN": {"delay_min": 1100, "delay_max": 1700, "base_conf": 0.70},
        "HUMAN": {"delay_min": 0, "delay_max": 500, "base_conf": 0.50},
        "BUSINESS_IVR": {"delay_min": 200, "delay_max": 800, "base_conf": 0.35},
        "VOICEMAIL": {"delay_min": 3000, "delay_max": 30000, "base_conf": 0.40},
    }

    def detect(self, answer_ms: int, first_audio_ms: int,
               first_beep_ms: Optional[int] = None) -> Dict[str, Any]:
        """
        Classify environment based on timing signatures.

        Args:
            answer_ms: When call was answered (connected) in epoch ms.
            first_audio_ms: When remote side first produced audio in epoch ms.
            first_beep_ms: When first beep was detected (if any).

        Returns:
            {
                "prior_env_class": str,
                "confidence": float [0,1],
                "delay_ms": int,
                "beep_delay_ms": int or None
            }
        """
        delay = max(0, first_audio_ms - answer_ms)
        beep_delay = (first_beep_ms - answer_ms) if first_beep_ms else None

        prior = "UNKNOWN"
        conf = 0.0

        # Check beep first — strong voicemail signal
        if beep_delay is not None:
            if beep_delay < 5000:
                prior = "PERSONAL_VOICEMAIL"
                conf = 0.75
            else:
                prior = "PERSONAL_VOICEMAIL"
                conf = 0.55

        # Check delay-based signatures
        if prior == "UNKNOWN":
            for env_name, sig in self.SIGNATURES.items():
                if sig["delay_min"] <= delay <= sig["delay_max"]:
                    # If multiple match, take the one with highest base confidence
                    if sig["base_conf"] > conf:
                        prior = env_name
                        conf = sig["base_conf"]

        # Adjust confidence based on delay precision
        # Very precise match = higher confidence
        if prior in self.SIGNATURES:
            sig = self.SIGNATURES[prior]
            mid = (sig["delay_min"] + sig["delay_max"]) / 2
            range_size = sig["delay_max"] - sig["delay_min"]
            if range_size > 0:
                distance = abs(delay - mid) / range_size
                conf = conf * (1.0 - distance * 0.3)  # slight penalty for edge cases

        return {
            "prior_env_class": prior,
            "confidence": round(conf, 3),
            "delay_ms": delay,
            "beep_delay_ms": beep_delay,
        }


# ======================================================================
#  4. HUMAN INTERRUPT DETECTOR
#     Detect when human tries to speak while Alan is talking.
# ======================================================================

class HumanInterruptDetector:
    """
    Detect when the remote side is trying to speak while Alan is talking
    and signal the floor should be yielded.

    Integration:
    - If interrupt_intent > 0.5 → stop TTS stream, mark agent_yielded, listen.
    - Tag in Phase 5: human.interrupt = true.
    """

    def __init__(self):
        self._consecutive_detections: int = 0
        self._last_detection_ms: float = 0.0
        self._cooldown_ms: float = 2000  # don't re-trigger within 2s

    def detect(self, remote_vad_active: bool, agent_speaking: bool,
               remote_energy: float = 0.0, timestamp_ms: float = 0.0) -> float:
        """
        Returns interrupt intent score [0,1].

        Args:
            remote_vad_active: Whether VAD detected speech on remote channel.
            agent_speaking: Whether Alan's TTS is currently playing.
            remote_energy: RMS energy of remote audio (for confidence).
            timestamp_ms: Current time in ms.

        Returns:
            Interrupt intent score [0,1].
        """
        if not (remote_vad_active and agent_speaking):
            # No overlap → reset consecutive counter (decay)
            if self._consecutive_detections > 0:
                self._consecutive_detections = max(0,
                    self._consecutive_detections - 1)
            return 0.0

        # Check cooldown
        if (timestamp_ms - self._last_detection_ms) < self._cooldown_ms:
            return 0.0

        self._consecutive_detections += 1

        # Score based on persistence
        if self._consecutive_detections >= 3:
            intent = 0.9
        elif self._consecutive_detections >= 2:
            intent = 0.7
        else:
            intent = 0.4

        # Boost if remote energy is significant
        if remote_energy > 200:
            intent = min(1.0, intent + 0.1)

        if intent > 0.5:
            self._last_detection_ms = timestamp_ms

        return round(intent, 2)

    def reset(self):
        """Reset detector for new call."""
        self._consecutive_detections = 0
        self._last_detection_ms = 0.0


# ======================================================================
#  5. HANG-UP PREDICTION MODEL
#     Predict when human is about to hang up and adapt behavior.
# ======================================================================

class HangupPredictionModel:
    """
    Predict hang-up risk from prosody, content, and conversation state.

    Integration:
    - hangup_risk > 0.7 → shorten response, move to value/close
    - hangup_risk > 0.9 → last-resort salvage attempt
    """

    # High-risk content markers
    DISENGAGEMENT_MARKERS = [
        "not interested", "no thanks", "no thank you", "don't call",
        "take me off", "remove me", "stop calling", "goodbye", "bye",
        "gotta go", "got to go", "busy right now", "in a meeting",
        "can't talk", "wrong number", "don't need",
    ]

    # Moderate risk markers
    IMPATIENCE_MARKERS = [
        "yeah", "uh huh", "okay", "right", "sure", "mm hmm",
        "go on", "and", "so", "what",
    ]

    def predict(self, prosody: Dict[str, float], text: str,
                turn_count: int, response_length: int = 0,
                response_latency_ms: float = 0.0,
                objection_count: int = 0) -> float:
        """
        Returns hangup risk in [0,1].

        Args:
            prosody: Prosody classification dict.
            text: Remote side's text (current utterance).
            turn_count: Number of turns so far.
            response_length: Length of remote's response (chars).
            response_latency_ms: How fast they responded.
            objection_count: Number of objections raised so far.
        """
        risk = 0.0
        text_lower = text.lower().strip()

        # --- Content signals ---
        for marker in self.DISENGAGEMENT_MARKERS:
            if marker in text_lower:
                risk += 0.45
                break  # one is enough

        impatience_hits = sum(1 for m in self.IMPATIENCE_MARKERS
                             if text_lower == m or text_lower == m + ".")
        if impatience_hits > 0 and turn_count > 2:
            risk += 0.15 * min(impatience_hits, 2)

        # --- Prosody signals ---
        if prosody.get("emotion_annoyed", 0) > 0.4:
            risk += 0.25
        if prosody.get("emotion_busy", 0) > 0.5:
            risk += 0.20

        # --- Conversation state ---
        if turn_count > 6:
            risk += 0.10
        if turn_count > 10:
            risk += 0.15

        # Short responses = losing interest
        if response_length < 5 and turn_count > 1:
            risk += 0.15

        # Many objections = close to hanging up
        if objection_count >= 2:
            risk += 0.20
        elif objection_count >= 1:
            risk += 0.10

        return round(min(1.0, risk), 2)


# ======================================================================
#  6. VERTICAL-AWARE ENVIRONMENT PREDICTOR
#     Use merchant vertical to predict likely environment and priors.
# ======================================================================

class VerticalAwarePredictor:
    """
    Predict likely call environment based on merchant vertical.

    Priors are derived from Phase 5 statistics when available,
    with hardcoded fallbacks for bootstrapping.
    """

    # Hardcoded baseline priors per vertical (sum to 1.0)
    # These get overridden by Phase 5 stats once enough data exists.
    BASELINE_PRIORS = {
        "RESTAURANT": {
            "HUMAN": 0.30, "BUSINESS_IVR": 0.10,
            "LIVE_RECEPTIONIST": 0.25, "AI_RECEPTIONIST": 0.10,
            "GOOGLE_CALL_SCREEN": 0.05, "PERSONAL_VOICEMAIL": 0.10,
            "CARRIER_VOICEMAIL": 0.05, "ANSWERING_SERVICE": 0.05,
        },
        "CONTRACTOR": {
            "HUMAN": 0.45, "PERSONAL_VOICEMAIL": 0.30,
            "CARRIER_VOICEMAIL": 0.10, "GOOGLE_CALL_SCREEN": 0.10,
            "BUSINESS_IVR": 0.05,
        },
        "MEDICAL": {
            "LIVE_RECEPTIONIST": 0.35, "BUSINESS_IVR": 0.25,
            "AI_RECEPTIONIST": 0.15, "HUMAN": 0.10,
            "ANSWERING_SERVICE": 0.10, "PERSONAL_VOICEMAIL": 0.05,
        },
        "RETAIL": {
            "HUMAN": 0.40, "LIVE_RECEPTIONIST": 0.20,
            "BUSINESS_IVR": 0.15, "GOOGLE_CALL_SCREEN": 0.10,
            "PERSONAL_VOICEMAIL": 0.10, "CARRIER_VOICEMAIL": 0.05,
        },
        "SALON": {
            "HUMAN": 0.35, "LIVE_RECEPTIONIST": 0.25,
            "AI_RECEPTIONIST": 0.15, "PERSONAL_VOICEMAIL": 0.15,
            "GOOGLE_CALL_SCREEN": 0.10,
        },
        "AUTO": {
            "LIVE_RECEPTIONIST": 0.30, "BUSINESS_IVR": 0.25,
            "HUMAN": 0.20, "AI_RECEPTIONIST": 0.10,
            "PERSONAL_VOICEMAIL": 0.10, "ANSWERING_SERVICE": 0.05,
        },
        "ECOM": {
            "AI_RECEPTIONIST": 0.30, "BUSINESS_IVR": 0.25,
            "HUMAN": 0.20, "CARRIER_VOICEMAIL": 0.15,
            "PERSONAL_VOICEMAIL": 0.10,
        },
    }

    # Uniform fallback if vertical unknown
    DEFAULT_PRIOR = {
        "HUMAN": 0.35, "PERSONAL_VOICEMAIL": 0.20,
        "GOOGLE_CALL_SCREEN": 0.10, "BUSINESS_IVR": 0.10,
        "LIVE_RECEPTIONIST": 0.10, "AI_RECEPTIONIST": 0.05,
        "CARRIER_VOICEMAIL": 0.05, "ANSWERING_SERVICE": 0.03,
        "CARRIER_SPAM_BLOCKER": 0.02,
    }

    def __init__(self, phase5_db=None):
        """
        Args:
            phase5_db: Optional Phase 5 database connection for learned priors.
        """
        self.phase5_db = phase5_db
        self._cache: Dict[str, Dict[str, float]] = {}
        self._cache_ttl: float = 3600  # refresh hourly
        self._cache_ts: float = 0.0

    def prior(self, vertical: str) -> Dict[str, float]:
        """
        Returns environment priors for a given merchant vertical.

        Args:
            vertical: Merchant vertical string (e.g., "RESTAURANT", "CONTRACTOR").

        Returns:
            Dict mapping environment class names to probability [0,1].
        """
        vert_upper = (vertical or "").upper().strip()

        # Try learned priors from Phase 5
        if self.phase5_db and (time.time() - self._cache_ts > self._cache_ttl):
            learned = self._load_phase5_priors()
            if learned:
                self._cache = learned
                self._cache_ts = time.time()

        if vert_upper in self._cache:
            return self._cache[vert_upper]

        # Fall back to hardcoded baselines
        return self.BASELINE_PRIORS.get(vert_upper, self.DEFAULT_PRIOR.copy())

    def _load_phase5_priors(self) -> Dict[str, Dict[str, float]]:
        """Load learned priors from Phase 5 env_plus_signals table."""
        try:
            if not self.phase5_db:
                return {}

            # Query distribution of env_class per vertical
            cursor = self.phase5_db.execute("""
                SELECT vertical, env_class, COUNT(*) as cnt
                FROM env_plus_signals
                WHERE vertical IS NOT NULL AND env_class IS NOT NULL
                GROUP BY vertical, env_class
            """)
            rows = cursor.fetchall()

            if not rows:
                return {}

            # Build distributions
            vert_counts: Dict[str, Dict[str, int]] = {}
            for row in rows:
                vert = row[0].upper()
                env = row[1]
                cnt = row[2]
                if vert not in vert_counts:
                    vert_counts[vert] = {}
                vert_counts[vert][env] = cnt

            # Normalize to probabilities
            result: Dict[str, Dict[str, float]] = {}
            for vert, env_counts in vert_counts.items():
                total = sum(env_counts.values())
                if total > 10:  # need minimum sample size
                    result[vert] = {env: cnt / total for env, cnt in env_counts.items()}

            return result

        except Exception as e:
            logger.warning(f"[EAB-PLUS] Phase5 prior load failed: {e}")
            return {}

    def load_phase5_signals(self, call_sid: str) -> Dict[str, Any]:
        """
        Load Phase 5 intelligence signals for a specific call.
        Returns zero_turn_class, dnc_flag, there_spam_flag alongside standard signals.
        """
        try:
            if not self.phase5_db:
                return {}
            cursor = self.phase5_db.execute("""
                SELECT env_class, env_action, env_behavior,
                       hangup_risk, zero_turn_class,
                       dnc_flag, there_spam_flag
                FROM env_plus_signals
                WHERE call_sid = ? AND turn_index = 0
                LIMIT 1
            """, (call_sid,))
            row = cursor.fetchone()
            if not row:
                return {}
            return {
                "env_class": row[0],
                "env_action": row[1],
                "env_behavior": row[2],
                "hangup_risk": row[3],
                "zero_turn_class": row[4],
                "dnc_flag": bool(row[5]),
                "there_spam_flag": bool(row[6]),
            }
        except Exception as e:
            logger.warning(f"[EAB-PLUS] Phase5 signal load failed for {call_sid}: {e}")
            return {}


# ======================================================================
#  7. STATE-AWARE ENVIRONMENT PREDICTOR
#     Use geography to predict environment mix.
# ======================================================================

class StateAwarePredictor:
    """
    Predict environment distribution by geographic state / area code.
    """

    BASELINE_PRIORS = {
        "FL": {
            "GOOGLE_CALL_SCREEN": 0.20, "PERSONAL_VOICEMAIL": 0.25,
            "HUMAN": 0.30, "BUSINESS_IVR": 0.10,
            "AI_RECEPTIONIST": 0.05, "LIVE_RECEPTIONIST": 0.10,
        },
        "TX": {
            "HUMAN": 0.45, "PERSONAL_VOICEMAIL": 0.20,
            "GOOGLE_CALL_SCREEN": 0.10, "BUSINESS_IVR": 0.10,
            "LIVE_RECEPTIONIST": 0.10, "AI_RECEPTIONIST": 0.05,
        },
        "CA": {
            "AI_RECEPTIONIST": 0.15, "GOOGLE_CALL_SCREEN": 0.15,
            "HUMAN": 0.30, "BUSINESS_IVR": 0.15,
            "PERSONAL_VOICEMAIL": 0.15, "LIVE_RECEPTIONIST": 0.10,
        },
        "NY": {
            "HUMAN": 0.35, "BUSINESS_IVR": 0.20,
            "LIVE_RECEPTIONIST": 0.15, "PERSONAL_VOICEMAIL": 0.15,
            "GOOGLE_CALL_SCREEN": 0.10, "AI_RECEPTIONIST": 0.05,
        },
        "GA": {
            "HUMAN": 0.40, "PERSONAL_VOICEMAIL": 0.20,
            "GOOGLE_CALL_SCREEN": 0.15, "BUSINESS_IVR": 0.10,
            "LIVE_RECEPTIONIST": 0.10, "AI_RECEPTIONIST": 0.05,
        },
    }

    DEFAULT_PRIOR = {
        "HUMAN": 0.35, "PERSONAL_VOICEMAIL": 0.20,
        "GOOGLE_CALL_SCREEN": 0.15, "BUSINESS_IVR": 0.10,
        "LIVE_RECEPTIONIST": 0.10, "AI_RECEPTIONIST": 0.05,
        "CARRIER_VOICEMAIL": 0.05,
    }

    # Area code → state mapping (common ones)
    AREA_CODE_STATE = {
        "213": "CA", "310": "CA", "323": "CA", "415": "CA", "510": "CA",
        "559": "CA", "619": "CA", "626": "CA", "650": "CA", "714": "CA",
        "408": "CA", "818": "CA", "858": "CA", "925": "CA", "949": "CA",
        "212": "NY", "347": "NY", "516": "NY", "646": "NY", "718": "NY",
        "917": "NY", "914": "NY", "631": "NY", "845": "NY",
        "214": "TX", "281": "TX", "512": "TX", "713": "TX", "817": "TX",
        "210": "TX", "469": "TX", "972": "TX", "832": "TX",
        "305": "FL", "407": "FL", "561": "FL", "727": "FL", "786": "FL",
        "813": "FL", "850": "FL", "904": "FL", "954": "FL", "321": "FL",
        "404": "GA", "470": "GA", "678": "GA", "706": "GA", "770": "GA",
        "912": "GA",
        "252": "NC", "336": "NC", "704": "NC", "828": "NC", "910": "NC",
        "919": "NC", "980": "NC",
        "843": "SC", "864": "SC",
        "406": "MT",
    }

    def __init__(self, phase5_db=None):
        self.phase5_db = phase5_db
        self._cache: Dict[str, Dict[str, float]] = {}
        self._cache_ts: float = 0.0

    def prior(self, state: Optional[str] = None,
              area_code: Optional[str] = None) -> Dict[str, float]:
        """
        Returns environment priors for a given state or area code.

        Accepts either state abbreviation or area code.
        """
        # Resolve state from area code if needed
        if not state and area_code:
            state = self.AREA_CODE_STATE.get(area_code)

        state = (state or "").upper().strip()

        if state in self.BASELINE_PRIORS:
            return self.BASELINE_PRIORS[state]

        return self.DEFAULT_PRIOR.copy()

    def state_from_phone(self, phone: str) -> Optional[str]:
        """Extract state from phone number's area code."""
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) >= 10:
            area_code = digits[-10:-7]  # last 10 digits, first 3
            return self.AREA_CODE_STATE.get(area_code)
        return None


# ======================================================================
#  8. LEAD-HISTORY ENVIRONMENT PREDICTOR
#     Use past calls to same number for priors.
# ======================================================================

class LeadHistoryPredictor:
    """
    Predict environment based on past call history to the same phone number.

    Integration:
    - If last 3 calls → VOICEMAIL → expect voicemail, maybe skip long greeting
    - If last call → GOOGLE_CALL_SCREEN → expect screener again
    - If last call → HUMAN + CONTINUE_MISSION → warm follow-up
    """

    def __init__(self, cdc_db=None):
        """
        Args:
            cdc_db: Optional CDC (Call Data Capture) database connection.
        """
        self.cdc_db = cdc_db

    def prior(self, phone: str) -> Dict[str, Any]:
        """
        Returns priors based on past calls to this number.

        Args:
            phone: Phone number in E.164 or similar format.

        Returns:
            Dict with:
                "last_env_class": str — most recent classification
                "last_outcome": str — most recent outcome
                "call_count": int — total previous calls
                "env_distribution": dict — env class → probability
                "recommendation": str — e.g., "expect_voicemail", "warm_followup"
        """
        result = {
            "last_env_class": "UNKNOWN",
            "last_outcome": "UNKNOWN",
            "call_count": 0,
            "env_distribution": {},
            "recommendation": "no_history",
        }

        if not self.cdc_db or not phone:
            return result

        try:
            # Normalize phone
            digits = ''.join(c for c in phone if c.isdigit())
            if len(digits) < 10:
                return result

            # Query past environment events for this number
            cursor = self.cdc_db.execute("""
                SELECT ee.env_class, ee.outcome, ee.timestamp
                FROM environment_events ee
                JOIN calls c ON ee.call_sid = c.call_sid
                WHERE c.merchant_phone LIKE ?
                ORDER BY ee.timestamp DESC
                LIMIT 10
            """, (f"%{digits[-10:]}%",))

            rows = cursor.fetchall()
            if not rows:
                return result

            result["call_count"] = len(rows)
            result["last_env_class"] = rows[0][0] or "UNKNOWN"
            result["last_outcome"] = rows[0][1] or "UNKNOWN"

            # Build distribution
            env_counts: Dict[str, int] = {}
            for row in rows:
                env = row[0] or "UNKNOWN"
                env_counts[env] = env_counts.get(env, 0) + 1

            total = sum(env_counts.values())
            result["env_distribution"] = {
                env: round(cnt / total, 2) for env, cnt in env_counts.items()
            }

            # Make recommendation
            recent_envs = [r[0] for r in rows[:3]]
            if all(e in ("PERSONAL_VOICEMAIL", "CARRIER_VOICEMAIL") for e in recent_envs if e):
                result["recommendation"] = "expect_voicemail"
            elif recent_envs and recent_envs[0] == "GOOGLE_CALL_SCREEN":
                result["recommendation"] = "expect_screener"
            elif recent_envs and recent_envs[0] == "HUMAN":
                result["recommendation"] = "warm_followup"
            elif recent_envs and recent_envs[0] in ("BUSINESS_IVR", "AI_RECEPTIONIST"):
                result["recommendation"] = "expect_automation"
            else:
                result["recommendation"] = "mixed_history"

        except Exception as e:
            logger.warning(f"[EAB-PLUS] Lead history lookup failed: {e}")

        return result


# ======================================================================
#  9. EAB-PLUS COMPOSITE RESOLVER
#     Combines all signals into a final env.class decision.
# ======================================================================

class EABPlusResolver:
    """
    Composite environment resolver.

    Architecture:
        base_env = rule_based_EAB(first_utterance_text)
        priors = combine_priors(timing, vertical, geo, lead_history)
        signals = {prosody, silence, timing_confidence}
        env.class = resolve_env(base_env, priors, signals, multi_turn_obs)

    The existing rule-based classifier is the spine.
    Each module contributes signals and priors, not hard overrides.
    """

    # Weight configuration for prior combination
    PRIOR_WEIGHTS = {
        "timing": 0.30,     # timing fingerprint
        "vertical": 0.20,   # merchant vertical
        "geo": 0.15,        # geographic state
        "lead": 0.35,       # lead history (strongest if data exists)
    }

    # Minimum confidence to override base classification
    OVERRIDE_THRESHOLD = 0.75

    def __init__(
        self,
        base_classifier,
        prosody_engine: ProsodyEngine,
        silence_classifier: SilencePatternClassifier,
        timing_detector: TimingFingerprintDetector,
        interrupt_detector: HumanInterruptDetector,
        hangup_model: HangupPredictionModel,
        vertical_predictor: VerticalAwarePredictor,
        state_predictor: StateAwarePredictor,
        lead_predictor: LeadHistoryPredictor,
    ):
        self.base_classifier = base_classifier
        self.prosody_engine = prosody_engine
        self.silence_classifier = silence_classifier
        self.timing_detector = timing_detector
        self.interrupt_detector = interrupt_detector
        self.hangup_model = hangup_model
        self.vertical_predictor = vertical_predictor
        self.state_predictor = state_predictor
        self.lead_predictor = lead_predictor

    def resolve(
        self,
        transcript: str,
        stt_conf: float,
        audio_frames: bytes,
        silence_frames: bytes,
        answer_ms: int,
        first_audio_ms: int,
        vertical: str = "",
        state: str = "",
        phone: str = "",
        turn_count: int = 0,
        response_length: int = 0,
        objection_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Master resolution: combine all signals into final env classification.

        Returns:
            {
                "env_class": str,
                "env_confidence": float,
                "base_env": str,
                "base_confidence": float,
                "prosody": dict,
                "silence": dict,
                "timing": dict,
                "vertical_prior": dict,
                "state_prior": dict,
                "lead_prior": dict,
                "hangup_risk": float,
                "resolution_reason": str,
            }
        """
        start_ms = time.time() * 1000

        # 1. Base EAB classification (spine)
        base_result = self.base_classifier.classify(transcript, stt_conf)
        base_env = base_result.env_class.name
        base_conf = base_result.confidence

        # 2. Prosody analysis
        pf = self.prosody_engine.extract(audio_frames)
        prosody = self.prosody_engine.classify(pf)

        # 3. Silence pattern analysis
        silence = self.silence_classifier.analyze(silence_frames)

        # 4. Timing fingerprint
        timing = self.timing_detector.detect(answer_ms, first_audio_ms)

        # 5. Prior signals
        vertical_prior = self.vertical_predictor.prior(vertical)
        state_prior = self.state_predictor.prior(state=state)
        lead_prior = self.lead_predictor.prior(phone)

        # 6. Hang-up risk
        hangup_risk = self.hangup_model.predict(
            prosody, transcript, turn_count,
            response_length=response_length,
            objection_count=objection_count,
        )

        # 7. Composite resolution
        final_env = base_env
        final_conf = base_conf
        reason_parts = [f"base={base_env}({base_conf:.2f})"]

        # --- Signal overrides (strong evidence) ---

        # Timing fingerprint: if high confidence & base is UNKNOWN
        if timing["confidence"] > 0.6 and base_env == "UNKNOWN":
            final_env = timing["prior_env_class"]
            final_conf = timing["confidence"]
            reason_parts.append(f"timing_override={final_env}")

        # Silence beep → voicemail prior
        if silence.get("has_beep", 0) > 0.7:
            if base_env in ("UNKNOWN", "HUMAN"):
                final_env = "PERSONAL_VOICEMAIL"
                final_conf = max(final_conf, 0.70)
                reason_parts.append("silence_beep→voicemail")

        # Silence machine → machine prior
        if silence.get("is_machine", 0) > 0.6:
            if base_env == "UNKNOWN":
                # Don't hard-override, just boost confidence for machine envs
                reason_parts.append(f"silence_machine={silence['is_machine']:.2f}")

        # Prosody human boost
        if prosody.get("is_human", 0) > 0.7:
            if base_env in ("UNKNOWN", "AI_RECEPTIONIST"):
                final_env = "HUMAN"
                final_conf = max(final_conf, prosody["is_human"] * 0.8)
                reason_parts.append(f"prosody_human={prosody['is_human']:.2f}")

        # Prosody machine signal
        if prosody.get("is_human", 1.0) < 0.3:
            if base_env == "HUMAN" and base_conf < 0.5:
                # Weak human classification + machine prosody → reconsider
                reason_parts.append(f"prosody_machine_signal={prosody['is_human']:.2f}")

        # --- Lead history override (strongest prior) ---
        if lead_prior.get("call_count", 0) >= 3:
            recommendation = lead_prior.get("recommendation", "")
            if recommendation == "expect_voicemail" and base_env == "UNKNOWN":
                final_env = "PERSONAL_VOICEMAIL"
                final_conf = max(final_conf, 0.60)
                reason_parts.append("lead_history→voicemail")
            elif recommendation == "expect_screener" and base_env == "UNKNOWN":
                final_env = "GOOGLE_CALL_SCREEN"
                final_conf = max(final_conf, 0.55)
                reason_parts.append("lead_history→screener")

        elapsed_ms = time.time() * 1000 - start_ms

        result = {
            "env_class": final_env,
            "env_confidence": round(final_conf, 3),
            "base_env": base_env,
            "base_confidence": round(base_conf, 3),
            "prosody": prosody,
            "silence": silence,
            "timing": timing,
            "vertical_prior": vertical_prior,
            "state_prior": state_prior,
            "lead_prior": lead_prior,
            "hangup_risk": hangup_risk,
            "resolution_reason": " | ".join(reason_parts),
            "resolve_ms": round(elapsed_ms, 1),
        }

        logger.info(
            f"[EAB-PLUS] RESOLVED: {final_env} (conf={final_conf:.2f}) | "
            f"base={base_env} | hangup_risk={hangup_risk} | "
            f"reason={result['resolution_reason']} | {elapsed_ms:.1f}ms"
        )

        return result
