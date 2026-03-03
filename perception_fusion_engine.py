from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional, Dict, Any
import time


class PerceptionHealth(Enum):
    OK = "ok"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class PerceptionMode(Enum):
    NORMAL = "normal"
    IVR = "ivr"
    VOICEMAIL = "voicemail"
    DEAD_AIR = "dead_air"
    CONNECTION_LOSS = "connection_loss"
    AUDIO_DRIFT = "audio_drift"
    UNKNOWN = "unknown"


@dataclass
class PerceptionSnapshot:
    timestamp_ms: int
    mode: PerceptionMode
    health: PerceptionHealth
    stt_confidence: float
    tts_drift_score: float
    inbound_silence_ms: int
    packet_gap_ms: int
    ivr_score: float
    voicemail_score: float
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mode"] = self.mode.value
        d["health"] = self.health.value
        return d


class PerceptionFusionEngine:
    """
    Fuses inbound silence, outbound drift, classifier scores, and transport health
    into a single perception state vector per call.
    """

    def __init__(self, config: Dict[str, Any]):
        self.cfg = config
        self._last_snapshot: Optional[PerceptionSnapshot] = None

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def fuse(
        self,
        *,
        stt_confidence: float,
        tts_drift_score: float,
        inbound_silence_ms: int,
        packet_gap_ms: int,
        ivr_score: float,
        voicemail_score: float,
    ) -> PerceptionSnapshot:
        mode = self._infer_mode(
            inbound_silence_ms=inbound_silence_ms,
            packet_gap_ms=packet_gap_ms,
            ivr_score=ivr_score,
            voicemail_score=voicemail_score,
            tts_drift_score=tts_drift_score,
        )
        health = self._infer_health(
            mode=mode,
            stt_confidence=stt_confidence,
            tts_drift_score=tts_drift_score,
            inbound_silence_ms=inbound_silence_ms,
            packet_gap_ms=packet_gap_ms,
        )

        snapshot = PerceptionSnapshot(
            timestamp_ms=self._now_ms(),
            mode=mode,
            health=health,
            stt_confidence=stt_confidence,
            tts_drift_score=tts_drift_score,
            inbound_silence_ms=inbound_silence_ms,
            packet_gap_ms=packet_gap_ms,
            ivr_score=ivr_score,
            voicemail_score=voicemail_score,
            notes=None,
        )
        self._last_snapshot = snapshot
        return snapshot

    def _infer_mode(
        self,
        *,
        inbound_silence_ms: int,
        packet_gap_ms: int,
        ivr_score: float,
        voicemail_score: float,
        tts_drift_score: float,
    ) -> PerceptionMode:
        if packet_gap_ms >= self.cfg.get("connection_loss_timeout_ms", 3000):
            return PerceptionMode.CONNECTION_LOSS

        if inbound_silence_ms >= self.cfg.get("dead_air_timeout_ms", 5000):
            return PerceptionMode.DEAD_AIR

        if tts_drift_score >= self.cfg.get("tts_drift_severe_threshold", 0.60):
            return PerceptionMode.AUDIO_DRIFT

        if ivr_score >= self.cfg.get("ivr_hard_threshold", 0.80):
            return PerceptionMode.IVR

        if voicemail_score >= self.cfg.get("voicemail_hard_threshold", 0.80):
            return PerceptionMode.VOICEMAIL

        return PerceptionMode.NORMAL

    def _infer_health(
        self,
        *,
        mode: PerceptionMode,
        stt_confidence: float,
        tts_drift_score: float,
        inbound_silence_ms: int,
        packet_gap_ms: int,
    ) -> PerceptionHealth:
        if mode in (
            PerceptionMode.CONNECTION_LOSS,
            PerceptionMode.AUDIO_DRIFT,
            PerceptionMode.DEAD_AIR,
        ):
            return PerceptionHealth.CRITICAL

        if stt_confidence < self.cfg.get("stt_confidence_degraded_threshold", 0.75):
            return PerceptionHealth.DEGRADED

        if tts_drift_score >= self.cfg.get("tts_drift_mild_threshold", 0.25):
            return PerceptionHealth.DEGRADED

        if inbound_silence_ms >= self.cfg.get("dead_air_warn_timeout_ms", 3000):
            return PerceptionHealth.DEGRADED

        if packet_gap_ms >= self.cfg.get("connection_loss_warn_timeout_ms", 1500):
            return PerceptionHealth.DEGRADED

        return PerceptionHealth.OK

    def last_snapshot(self) -> Optional[PerceptionSnapshot]:
        return self._last_snapshot
