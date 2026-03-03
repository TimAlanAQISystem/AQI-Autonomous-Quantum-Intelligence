"""
AQI Event Fusion Layer (v1.0)
-----------------------------

Unifies all voice-related signals into a single event stream for QPC-2:

    - Twilio CI transcripts
    - CI sentiment events
    - CI summaries + action items
    - Wrapper voice turns
    - Stance + energy trajectories
    - Drift detector signals
    - Merchant onboarding logic hooks

This is the intelligence fusion layer for AQI voice governance.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from aqi_voice_qpc_wrapper import VoiceQPCWrapper, VoiceTurnRequest
from aqi_voice_drift_detector import detect_voice_drift


# ============================================================
# Unified Event Schema
# ============================================================

@dataclass
class AQIEvent:
    """
    A single fused event representing one moment in a call.
    """

    call_sid: str
    event_type: str  # transcript, sentiment, summary, wrapper_turn, etc.
    speaker: Optional[str] = None
    transcript: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    summary: Optional[str] = None
    action_items: Optional[List[str]] = None
    wrapper_output: Optional[Dict[str, Any]] = None
    stance: Optional[Dict[str, float]] = None
    energy: Optional[float] = None
    drift: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Fusion Engine
# ============================================================

class AQIEventFusionEngine:
    """
    Fuses Twilio CI events + wrapper outputs + drift signals
    into a unified event stream for QPC-2.
    """

    def __init__(self, wrapper: VoiceQPCWrapper):
        self.wrapper = wrapper
        self.event_log: Dict[str, List[AQIEvent]] = {}

    # -------------------------
    # Core fusion method
    # -------------------------

    def _append_event(self, call_sid: str, event: AQIEvent) -> None:
        if call_sid not in self.event_log:
            self.event_log[call_sid] = []
        self.event_log[call_sid].append(event)

    # -------------------------
    # CI Transcript Fusion
    # -------------------------

    def fuse_ci_transcript(
        self,
        call_sid: str,
        speaker: str,
        transcript: str,
        sandbox: bool = True,
    ) -> AQIEvent:

        # Route transcript into QPC-2 via wrapper
        req = VoiceTurnRequest(
            audio_bytes=b"",
            caller_id=f"ci_{call_sid}_{speaker}",
            source="twilio_ci",
            epistemic_layer="merchant_support",
            anchors=["ci_transcript", speaker],
            sandbox=sandbox,
        )

        # Override transcription
        self.wrapper.transcribe_fn = lambda _: transcript

        wrapper_resp = self.wrapper.process_voice_turn(req)

        event = AQIEvent(
            call_sid=call_sid,
            event_type="ci_transcript",
            speaker=speaker,
            transcript=transcript,
            wrapper_output={
                "content": wrapper_resp.content,
                "string_id": wrapper_resp.string_id,
            },
            stance=wrapper_resp.stance,
            energy=wrapper_resp.energy,
        )

        self._append_event(call_sid, event)
        return event

    # -------------------------
    # CI Sentiment Fusion
    # -------------------------

    def fuse_ci_sentiment(
        self,
        call_sid: str,
        speaker: str,
        sentiment: str,
        score: float,
    ) -> AQIEvent:

        event = AQIEvent(
            call_sid=call_sid,
            event_type="ci_sentiment",
            speaker=speaker,
            sentiment=sentiment,
            sentiment_score=score,
        )

        self._append_event(call_sid, event)
        return event

    # -------------------------
    # CI Summary Fusion
    # -------------------------

    def fuse_ci_summary(
        self,
        call_sid: str,
        summary: str,
        action_items: List[str],
        sandbox: bool = True,
    ) -> AQIEvent:

        # Route summary into QPC-2
        req = VoiceTurnRequest(
            audio_bytes=b"",
            caller_id=f"ci_summary_{call_sid}",
            source="twilio_ci_summary",
            epistemic_layer="merchant_support",
            anchors=["ci_summary"],
            sandbox=sandbox,
        )

        self.wrapper.transcribe_fn = lambda _: summary

        wrapper_resp = self.wrapper.process_voice_turn(req)

        event = AQIEvent(
            call_sid=call_sid,
            event_type="ci_summary",
            summary=summary,
            action_items=action_items,
            wrapper_output={
                "content": wrapper_resp.content,
                "string_id": wrapper_resp.string_id,
            },
            stance=wrapper_resp.stance,
            energy=wrapper_resp.energy,
        )

        self._append_event(call_sid, event)
        return event

    # -------------------------
    # Drift Fusion (per-call)
    # -------------------------

    def fuse_drift_analysis(self, call_sid: str) -> AQIEvent:
        """
        Runs drift detection on the entire call trajectory.
        """
        trajectory = [
            {
                "stance": e.stance,
                "energy": e.energy,
                "transcript": e.transcript,
                "content": (e.wrapper_output or {}).get("content"),
            }
            for e in self.event_log.get(call_sid, [])
            if e.stance is not None or e.energy is not None
        ]

        drift_report = detect_voice_drift(trajectory)

        event = AQIEvent(
            call_sid=call_sid,
            event_type="drift_report",
            drift=drift_report,
        )

        self._append_event(call_sid, event)
        return event

    # -------------------------
    # Retrieve full fused stream
    # -------------------------

    def get_fused_stream(self, call_sid: str) -> List[AQIEvent]:
        return self.event_log.get(call_sid, [])
