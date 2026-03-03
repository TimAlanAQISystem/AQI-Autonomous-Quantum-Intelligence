"""
LIVE CALL MONITOR + HUMAN VOICE FREQUENCY DETECTOR
====================================================
Tim's Directive: "There must always be an active way to confirm that 
Alan is on the Phone with an Actual Human... I want to know what is 
actually happening, LIVE, not guessing."

This module provides:
1. Human Voice Frequency Detection — analyzes audio spectrum to distinguish
   human speech (85-300Hz fundamental, formants up to 3.4kHz) from IVR tones,
   silence, and machine-generated audio.
2. Live Call State Tracking — real-time snapshot of what's happening on any
   active call: who's speaking, voice confidence, transcript, timing.

Audio Science:
- Twilio sends mulaw 8kHz mono audio (narrowband telephony: 300-3400Hz)
- Human voice fundamental frequency: male 85-180Hz, female 165-255Hz
- In 8kHz sampling, Nyquist = 4kHz, so we capture the full telephony band
- IVR/DTMF tones are pure sinusoids at specific frequencies (697-1633Hz)
- Human speech has broad spectral energy with formant peaks (irregular)
- Machine/recording audio has unnaturally flat spectral distribution

Detection Method:
- FFT on 160-sample frames (20ms at 8kHz)
- Spectral flatness: human speech is "spiky" (formants), machines are "flat"
- Energy distribution: human voice concentrates energy in 300-1000Hz band
- Pitch detection: human speech has detectable fundamental frequency
"""

import struct
import math
import time
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("LIVE_MONITOR")

# ── Voice Frequency Constants for 8kHz Telephony ──
SAMPLE_RATE = 8000
FRAME_SIZE = 160        # 20ms at 8kHz (standard telephony frame)
FFT_SIZE = 256          # Next power of 2 above FRAME_SIZE
NYQUIST = SAMPLE_RATE / 2  # 4000 Hz

# Human voice frequency bands (Hz) mapped to FFT bins
# At 8kHz sample rate with 256-point FFT: bin_freq = bin_index * (8000/256) = bin_index * 31.25 Hz
BIN_RESOLUTION = SAMPLE_RATE / FFT_SIZE  # 31.25 Hz per bin

# Key bands for human voice detection
VOICE_LOW = 200    # Low end of voice fundamental (bin ~6)
VOICE_HIGH = 1000  # Voice formant region (bin ~32)
FULL_BAND_HIGH = 3400  # Telephony upper limit (bin ~109)

# Detection thresholds
SPECTRAL_FLATNESS_HUMAN_THRESHOLD = 0.35   # Below this = "spiky" spectrum = human
VOICE_BAND_ENERGY_THRESHOLD = 0.55          # Fraction of energy in voice band
MIN_RMS_FOR_ANALYSIS = 300                  # Below this = silence, skip analysis
HUMAN_CONFIDENCE_SMOOTHING = 0.7            # Exponential smoothing factor

# Live state labels
STATE_SILENCE = "SILENCE"
STATE_HUMAN_SPEAKING = "HUMAN_SPEAKING" 
STATE_MACHINE_AUDIO = "MACHINE_AUDIO"
STATE_ALAN_SPEAKING = "ALAN_SPEAKING"
STATE_UNKNOWN = "UNKNOWN"


@dataclass
class VoiceAnalysis:
    """Result of a single frame's voice frequency analysis."""
    rms: float = 0.0
    spectral_flatness: float = 1.0    # 0 = pure tone, 1 = white noise
    voice_band_energy: float = 0.0     # Fraction of energy in 200-1000Hz
    peak_frequency: float = 0.0        # Dominant frequency
    is_human_voice: bool = False
    confidence: float = 0.0
    state: str = STATE_SILENCE


@dataclass 
class LiveCallState:
    """Complete real-time state of an active call."""
    call_sid: str = ""
    started_at: Optional[datetime] = None
    elapsed_seconds: float = 0.0
    
    # Voice detection
    current_state: str = STATE_SILENCE
    human_confidence: float = 0.0       # Smoothed confidence (0-1)
    human_detected: bool = False        # Has human been confirmed at least once?
    human_first_detected_at: Optional[float] = None
    
    # Counters
    total_frames: int = 0
    human_frames: int = 0
    machine_frames: int = 0
    silence_frames: int = 0
    alan_speaking_frames: int = 0
    
    # Audio levels
    current_rms: float = 0.0
    peak_rms: float = 0.0
    avg_rms: float = 0.0
    
    # Conversation
    merchant_turns: int = 0
    alan_turns: int = 0
    last_merchant_speech: str = ""
    last_alan_speech: str = ""
    last_activity_time: float = 0.0
    
    # Cost sentinel
    cost_sentinel_status: str = "monitoring"
    
    def to_dict(self) -> dict:
        """JSON-serializable snapshot."""
        return {
            "call_sid": self.call_sid,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "current_state": self.current_state,
            "human_confidence": round(self.human_confidence, 3),
            "human_detected": self.human_detected,
            "human_first_detected_seconds": round(time.time() - self.human_first_detected_at, 1) if self.human_first_detected_at else None,
            "frame_counts": {
                "total": self.total_frames,
                "human": self.human_frames,
                "machine": self.machine_frames,
                "silence": self.silence_frames,
                "alan_speaking": self.alan_speaking_frames,
            },
            "human_percentage": round(self.human_frames / max(self.total_frames, 1) * 100, 1),
            "audio_levels": {
                "current_rms": round(self.current_rms, 0),
                "peak_rms": round(self.peak_rms, 0),
                "avg_rms": round(self.avg_rms, 1),
            },
            "conversation": {
                "merchant_turns": self.merchant_turns,
                "alan_turns": self.alan_turns,
                "last_merchant_speech": self.last_merchant_speech[-120:] if self.last_merchant_speech else "",
                "last_alan_speech": self.last_alan_speech[-120:] if self.last_alan_speech else "",
            },
            "verdict": self._verdict(),
            "cost_sentinel": self.cost_sentinel_status,
        }
    
    def _verdict(self) -> str:
        """Human-readable verdict: what's ACTUALLY happening on this call."""
        if self.elapsed_seconds < 5:
            return "CALL STARTING — establishing connection"
        
        if self.human_detected and self.merchant_turns >= 2:
            return f"LIVE CONVERSATION — Human confirmed, {self.merchant_turns} merchant turns"
        elif self.human_detected and self.merchant_turns == 1:
            return "HUMAN ANSWERED — waiting for dialogue"
        elif self.human_confidence > 0.5 and not self.human_detected:
            return "POSSIBLE HUMAN — voice patterns detected, not yet confirmed"
        elif self.current_state == STATE_MACHINE_AUDIO:
            return "IVR/MACHINE DETECTED — automated system audio"
        elif self.current_state == STATE_ALAN_SPEAKING:
            return "ALAN SPEAKING — waiting for merchant response"
        elif self.current_state == STATE_SILENCE and self.elapsed_seconds > 30:
            return "AIR CALL WARNING — extended silence, no activity"
        elif self.current_state == STATE_SILENCE:
            return "RINGING/CONNECTING — no audio yet"
        else:
            return f"MONITORING — state={self.current_state}"


def _simple_fft_magnitude(samples: List[float], n: int) -> List[float]:
    """
    Compute FFT magnitudes using a simple DFT implementation.
    We only need the magnitude spectrum, not phase, and only for
    the first n/2 bins (positive frequencies).
    
    For 256-point FFT at 8kHz, this gives us bins from 0 to 4000Hz.
    """
    magnitudes = []
    half_n = n // 2
    
    # Pad samples to n if needed
    if len(samples) < n:
        samples = samples + [0.0] * (n - len(samples))
    
    # DFT for positive frequency bins only
    for k in range(half_n):
        real = 0.0
        imag = 0.0
        for i in range(n):
            angle = -2.0 * math.pi * k * i / n
            real += samples[i] * math.cos(angle)
            imag += samples[i] * math.sin(angle)
        mag = math.sqrt(real * real + imag * imag)
        magnitudes.append(mag)
    
    return magnitudes


def analyze_voice_frame(pcm_data: bytes, rms: float, is_alan_talking: bool = False) -> VoiceAnalysis:
    """
    Analyze a single audio frame for human voice characteristics.
    
    Args:
        pcm_data: Raw PCM16 audio bytes (from audioop.ulaw2lin)
        rms: Pre-computed RMS value (already available from VAD)
        is_alan_talking: Whether Alan is currently outputting TTS
    
    Returns:
        VoiceAnalysis with human voice confidence and state
    """
    result = VoiceAnalysis(rms=rms)
    
    # If Alan is talking, mark as such and skip analysis
    if is_alan_talking:
        result.state = STATE_ALAN_SPEAKING
        return result
    
    # Below noise floor = silence
    if rms < MIN_RMS_FOR_ANALYSIS:
        result.state = STATE_SILENCE
        return result
    
    # Decode PCM16 samples
    try:
        num_samples = len(pcm_data) // 2
        samples = list(struct.unpack(f'<{num_samples}h', pcm_data[:num_samples * 2]))
    except struct.error:
        result.state = STATE_UNKNOWN
        return result
    
    if not samples:
        result.state = STATE_UNKNOWN
        return result
    
    # Normalize samples to [-1, 1]
    max_val = 32768.0
    normalized = [s / max_val for s in samples]
    
    # Compute FFT magnitudes  
    mags = _simple_fft_magnitude(normalized, FFT_SIZE)
    
    if not mags or max(mags) < 0.001:
        result.state = STATE_SILENCE
        return result
    
    # ── Spectral Flatness ──
    # Geometric mean / Arithmetic mean of magnitudes
    # Human speech: low flatness (formant peaks). Machine: high flatness.
    log_sum = 0.0
    arith_sum = 0.0
    count = 0
    for m in mags[1:]:  # Skip DC bin
        if m > 0.0001:
            log_sum += math.log(m)
            arith_sum += m
            count += 1
    
    if count > 0 and arith_sum > 0:
        geometric_mean = math.exp(log_sum / count)
        arithmetic_mean = arith_sum / count
        result.spectral_flatness = geometric_mean / arithmetic_mean
    else:
        result.spectral_flatness = 1.0
    
    # ── Voice Band Energy ──
    # What fraction of total energy is in the 200-1000Hz "voice" band?
    voice_low_bin = max(1, int(VOICE_LOW / BIN_RESOLUTION))
    voice_high_bin = min(len(mags) - 1, int(VOICE_HIGH / BIN_RESOLUTION))
    full_high_bin = min(len(mags) - 1, int(FULL_BAND_HIGH / BIN_RESOLUTION))
    
    voice_energy = sum(m * m for m in mags[voice_low_bin:voice_high_bin + 1])
    total_energy = sum(m * m for m in mags[1:full_high_bin + 1])
    
    result.voice_band_energy = voice_energy / max(total_energy, 0.0001)
    
    # ── Peak Frequency ──
    peak_bin = max(range(1, len(mags)), key=lambda i: mags[i])
    result.peak_frequency = peak_bin * BIN_RESOLUTION
    
    # ── Human Voice Decision ──
    # Human voice indicators:
    # 1. Low spectral flatness (spiky spectrum with formant peaks)
    # 2. High energy concentration in voice band (200-1000Hz)
    # 3. Peak frequency in voice range
    
    flatness_score = 1.0 - min(result.spectral_flatness / SPECTRAL_FLATNESS_HUMAN_THRESHOLD, 1.0)
    energy_score = min(result.voice_band_energy / VOICE_BAND_ENERGY_THRESHOLD, 1.0)
    peak_in_voice = 1.0 if VOICE_LOW <= result.peak_frequency <= VOICE_HIGH else 0.3
    
    result.confidence = (flatness_score * 0.4 + energy_score * 0.4 + peak_in_voice * 0.2)
    result.confidence = max(0.0, min(1.0, result.confidence))
    
    result.is_human_voice = result.confidence > 0.55
    result.state = STATE_HUMAN_SPEAKING if result.is_human_voice else STATE_MACHINE_AUDIO
    
    return result


class LiveCallMonitor:
    """
    Global singleton that tracks all active calls in real-time.
    
    Injected into the relay server's media processing loop.
    The control API reads from this to serve /call/live endpoint.
    """
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'LiveCallMonitor':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._calls: Dict[str, LiveCallState] = {}
        self._rms_accumulator: Dict[str, List[float]] = {}
    
    def register_call(self, call_sid: str, start_time: datetime = None):
        """Register a new call for monitoring."""
        state = LiveCallState(
            call_sid=call_sid,
            started_at=start_time or datetime.now(),
            last_activity_time=time.time(),
        )
        self._calls[call_sid] = state
        self._rms_accumulator[call_sid] = []
        logger.info(f"[LIVE MONITOR] Registered call {call_sid}")
    
    def unregister_call(self, call_sid: str):
        """Remove a completed call from monitoring."""
        self._calls.pop(call_sid, None)
        self._rms_accumulator.pop(call_sid, None)
        logger.info(f"[LIVE MONITOR] Unregistered call {call_sid}")
    
    def process_frame(self, call_sid: str, analysis: VoiceAnalysis):
        """
        Process a voice analysis frame and update live state.
        Called from the relay server's media processing loop.
        """
        state = self._calls.get(call_sid)
        if not state:
            return
        
        state.total_frames += 1
        state.current_rms = analysis.rms
        state.peak_rms = max(state.peak_rms, analysis.rms)
        
        # Rolling average RMS
        acc = self._rms_accumulator.get(call_sid, [])
        acc.append(analysis.rms)
        if len(acc) > 500:  # ~10s window
            acc = acc[-500:]
        self._rms_accumulator[call_sid] = acc
        state.avg_rms = sum(acc) / len(acc)
        
        # Update elapsed
        if state.started_at:
            state.elapsed_seconds = (datetime.now() - state.started_at).total_seconds()
        
        # Update state based on analysis
        state.current_state = analysis.state
        
        if analysis.state == STATE_HUMAN_SPEAKING:
            state.human_frames += 1
            state.last_activity_time = time.time()
            # Smooth confidence
            state.human_confidence = (
                HUMAN_CONFIDENCE_SMOOTHING * state.human_confidence +
                (1 - HUMAN_CONFIDENCE_SMOOTHING) * analysis.confidence
            )
            # Confirm human after sustained detection
            if not state.human_detected and state.human_frames >= 10:
                state.human_detected = True
                state.human_first_detected_at = time.time()
                logger.info(f"[LIVE MONITOR] HUMAN CONFIRMED on call {call_sid} — "
                           f"confidence={state.human_confidence:.2f}")
        elif analysis.state == STATE_MACHINE_AUDIO:
            state.machine_frames += 1
            state.last_activity_time = time.time()
            # Decay confidence
            state.human_confidence *= 0.98
        elif analysis.state == STATE_ALAN_SPEAKING:
            state.alan_speaking_frames += 1
        else:
            state.silence_frames += 1
            # Slow decay during silence
            state.human_confidence *= 0.995
    
    def record_merchant_speech(self, call_sid: str, text: str):
        """Record when merchant speaks (from STT)."""
        state = self._calls.get(call_sid)
        if state:
            state.merchant_turns += 1
            state.last_merchant_speech = text
            state.last_activity_time = time.time()
            # Direct speech = confirmed human
            if not state.human_detected:
                state.human_detected = True
                state.human_first_detected_at = time.time()
    
    def record_alan_speech(self, call_sid: str, text: str):
        """Record when Alan speaks (TTS)."""
        state = self._calls.get(call_sid)
        if state:
            state.alan_turns += 1
            state.last_alan_speech = text
    
    def update_sentinel_status(self, call_sid: str, status: str):
        """Update cost sentinel status for a call."""
        state = self._calls.get(call_sid)
        if state:
            state.cost_sentinel_status = status
    
    def get_live_state(self, call_sid: str = None) -> dict:
        """
        Get live state for a specific call or all calls.
        This is what Tim sees.
        """
        if call_sid and call_sid in self._calls:
            return self._calls[call_sid].to_dict()
        
        # All active calls
        if not self._calls:
            return {
                "active_calls": 0,
                "message": "No active calls. Alan is idle.",
                "calls": []
            }
        
        return {
            "active_calls": len(self._calls),
            "calls": [state.to_dict() for state in self._calls.values()]
        }
    
    def get_summary(self) -> str:
        """One-line human-readable summary."""
        if not self._calls:
            return "IDLE — No active calls"
        
        summaries = []
        for sid, state in self._calls.items():
            v = state._verdict()
            summaries.append(f"[{sid[-8:]}] {v} ({state.elapsed_seconds:.0f}s)")
        return " | ".join(summaries)
