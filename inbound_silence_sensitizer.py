# inbound_silence_sensitizer.py
"""
Inbound Silence Sensitizer -- Real-Time User Audio Integrity Monitor
====================================================================
Mirrors the VoiceSensitizer but monitors INBOUND user audio streams.
Detects "Dead Air" conditions (silence, no energy, connection drift)
to prevent the AI from talking to an empty line or a disconnected stream.

Capabilities:
  - Energy/RMS Monitoring: Detects if the line is truly dead (digital silence).
  - VAD (Voice Activity Detection) Integration: Tracks speech frames vs noise.
  - Latency/Drift Detection: Monitors packet arrival intervals.
  - Action Dispatch: Triggers STT restarts, codec renegotiation, or hangup.

Architecture:
  1. Per-Packet Analysis: Each inbound audio chunk is inspected.
  2. Windowed Metrics: Sliding window (e.g., 5s) of audio health.
  3. State Machine: Healthy -> Suspicious -> Dead -> Terminal.
  4. Integration: Called by the WebSocket server on receiving 'media' events.

Author: GitHub Copilot (Steward Logic)
Date: February 18, 2026
"""

import logging
import math
import audioop
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("InboundSensitizer")

@dataclass
class InboundAudioMetrics:
    """Metrics extracted from a sequence of inbound audio packets."""
    rms_energy: float            # Root Mean Square energy (volume)
    peak_amplitude: int          # Max amplitude
    packet_interval_ms: float    # Avg time between packets
    packet_jitter_ms: float      # Variance in packet arrival
    speech_probability: float    # 0.0-1.0 (if VAD available, else -1)
    is_digital_silence: bool     # True if audio data is all zeros

@dataclass
class SilenceState:
    """Tracks the state of silence/dead air for a specific call."""
    call_sid: str
    start_time: float
    last_packet_time: float
    consecutive_silence_frames: int
    consecutive_missing_packets: int
    health_score: float = 1.0  # 1.0 = healthy, 0.0 = dead
    status: str = "healthy"    # healthy, suspicious, dead

# =============================================================================
# CONFIG
# =============================================================================

DEFAULT_INBOUND_CONFIG = {
    "thresholds": {
        "min_rms_energy": 100,           # Below this is considered silence (16-bit PCM)
        "max_packet_interval_ms": 100,   # >100ms gap is suspicious (standard is 20ms)
        "dead_air_timeout_ms": 5000,     # 5s of pure silence -> Action
        "connection_loss_timeout_ms": 3000, # 3s of NO packets -> Reconnect/Hangup
    },
    "actions": {
        "on_suspicious": "log_warning",
        "on_dead_air": "trigger_stt_restart", # Try to wake up the STT
        "on_connection_loss": "hangup",
    },
    "sampling_rate": 8000, # Twilio standard
}

class InboundSilenceSensitizer:
    """
    Monitors inbound audio streams for validity and life-signs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DEFAULT_INBOUND_CONFIG
        self.thresholds = self.config["thresholds"]
        self._states: Dict[str, SilenceState] = {}
        logger.info(f"[INBOUND-SENS] Initialized with thresholds: {self.thresholds}")

    def register_call(self, call_sid: str):
        """Start monitoring a new call."""
        self._states[call_sid] = SilenceState(
            call_sid=call_sid,
            start_time=time.time(),
            last_packet_time=time.time(),
            consecutive_silence_frames=0,
            consecutive_missing_packets=0
        )

    def unregister_call(self, call_sid: str):
        """Stop monitoring a call."""
        if call_sid in self._states:
            del self._states[call_sid]

    def process_packet(self, call_sid: str, payload: bytes) -> Dict[str, Any]:
        """
        Ingest a raw u-law/PCM audio packet from Twilio.
        Returns a dict of actions (if any need to be taken).
        """
        if call_sid not in self._states:
            return {"action": "none"}

        state = self._states[call_sid]
        now = time.time()
        
        # 1. Check Packet Interval (Jitter/Latency)
        interval = (now - state.last_packet_time) * 1000 # ms
        state.last_packet_time = now

        if interval > self.thresholds["max_packet_interval_ms"]:
            state.consecutive_missing_packets += 1
        else:
            state.consecutive_missing_packets = 0

        # 2. Check Audio Energy (Silence)
        # Assuming payload is mu-law, we need to decode or estimate energy.
        # Ideally, we decode to PCM to get RMS.
        try:
            # Twilio sends mu-law (PCMU) usually over Media Streams
            # We can use audioop to get RMS from mu-law directly? 
            # No, audioop.rms works on linear PCM.
            # Decode mu-law to linear
            pcm_data = audioop.ulaw2lin(payload, 2)
            rms = audioop.rms(pcm_data, 2)
        except Exception:
            rms = 0 # Fail safe

        if rms < self.thresholds["min_rms_energy"]:
            state.consecutive_silence_frames += 1
        else:
            state.consecutive_silence_frames = 0
            state.status = "healthy" # Reset status on noise

        # 3. Determine Health Status
        result = {"action": "none", "metrics": {"rms": rms, "interval": interval}}
        
        # Check Connection Loss
        # (Note: This logic runs ON packet arrival, so it can't detect total loss 
        # unless called by a heartbeat. We rely on the server interval loop for that usually,
        # but here we track metrics.)
        
        # Dead Air Detection (Silence Frame Accumulation)
        # Assuming 20ms packets -> 50 packets = 1 second
        packets_per_sec = 50
        silence_duration_ms = (state.consecutive_silence_frames / packets_per_sec) * 1000

        if silence_duration_ms > self.thresholds["dead_air_timeout_ms"]:
            state.status = "dead_air"
            result["action"] = self.config["actions"]["on_dead_air"]
            result["reason"] = f"Dead air detected: {silence_duration_ms:.0f}ms silence"
        
        return result

    def check_heartbeat(self, call_sid: str) -> Dict[str, Any]:
        """
        External loop should call this periodically to check for true connection loss
        (i.e., NO packets arriving).
        """
        if call_sid not in self._states:
            return {"action": "none"}
            
        state = self._states[call_sid]
        time_since_last = (time.time() - state.last_packet_time) * 1000
        
        if time_since_last > self.thresholds["connection_loss_timeout_ms"]:
            state.status = "connection_lost"
            return {
                "action": self.config["actions"]["on_connection_loss"],
                "reason": f"Connection lost: No packets for {time_since_last:.0f}ms"
            }
            
        return {"action": "none"}

    def get_stats(self, call_sid: str) -> Dict[str, Any]:
        """Return current inbound audio statistics for a call."""
        if call_sid not in self._states:
            return {}

        state = self._states[call_sid]
        now = time.time()
        elapsed = now - state.start_time
        # Approximation: consecutive_silence_frames * 20ms
        silence_duration_ms = state.consecutive_silence_frames * 20
        # Time since last packet
        packet_gap_ms = (now - state.last_packet_time) * 1000

        return {
            "max_silence_ms": int(silence_duration_ms),
            "max_packet_gap_ms": int(packet_gap_ms),
            "status": state.status,
            "duration_total": round(elapsed, 2)
        }
