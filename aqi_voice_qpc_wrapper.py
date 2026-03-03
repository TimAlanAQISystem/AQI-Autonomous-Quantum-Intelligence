"""
AQI Voice → QPC-2 Integration Wrapper (v1.0)
--------------------------------------------

Purpose:
    Take a single turn of voice input (audio bytes), transcribe it,
    route it through AQI/QPC-2 (via aqi_intent_router), and return:

        - text transcript
        - QPC-2 response content
        - stance + energy snapshot (if available)
        - synthesized audio response (for playback)
        - sandbox flag + metadata

This is the glue between:
    - Twilio / synthetic_call_generator
    - Transcription (STT)
    - QPC-2 (via aqi_intent_router)
    - Voice synthesis (TTS)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable

from aqi_intent_router import route_intent


# =========================
# Data structures
# =========================


@dataclass
class VoiceTurnRequest:
    """One turn of voice input."""

    audio_bytes: bytes
    caller_id: str
    source: str  # e.g. "twilio", "synthetic", "test_harness"
    epistemic_layer: str  # e.g. "ethics", "ops", "merchant_support"
    anchors: list[str]
    prior_string_id: Optional[str] = None
    sandbox: bool = True


@dataclass
class VoiceTurnResponse:
    """QPC-2-governed response to one turn of voice input."""

    transcript: str
    content: str
    audio_response: Optional[bytes]
    sandbox: bool
    router_environment: str
    stance: Optional[Dict[str, float]] = None
    energy: Optional[float] = None
    string_id: Optional[str] = None
    raw_qpc_payload: Optional[Dict[str, Any]] = None
    raw_qpc_result: Optional[Dict[str, Any]] = None


# =========================
# Wrapper configuration
# =========================

TranscriptionFn = Callable[[bytes], str]
SynthesisFn = Callable[[str], bytes]


class VoiceQPCWrapper:
    """Orchestrates audio -> transcript -> QPC-2 -> response text -> audio."""

    def __init__(
        self,
        transcribe_fn: TranscriptionFn,
        synthesize_fn: Optional[SynthesisFn] = None,
    ) -> None:
        self.transcribe_fn = transcribe_fn
        self.synthesize_fn = synthesize_fn

    def process_voice_turn(self, req: VoiceTurnRequest) -> VoiceTurnResponse:
        """Main entrypoint for Twilio handlers and synthetic generators."""

        transcript = self.transcribe_fn(req.audio_bytes).strip()

        if not transcript:
            fallback_text = "I didn’t quite catch that. Can you say that again?"
            fallback_audio = (
                self.synthesize_fn(fallback_text) if self.synthesize_fn else None
            )
            return VoiceTurnResponse(
                transcript="",
                content=fallback_text,
                audio_response=fallback_audio,
                sandbox=req.sandbox,
                router_environment="unknown",
            )

        qpc_payload: Dict[str, Any] = {
            "source": req.source,
            "caller_id": req.caller_id,
            "raw_message": transcript,
            "epistemic_layer": req.epistemic_layer,
            "anchors": req.anchors,
            "prior_string_id": req.prior_string_id,
            "debug_mode": False,
        }

        qpc_result: Dict[str, Any] = route_intent(qpc_payload)

        content = qpc_result.get("content", "")
        stance = qpc_result.get("stance")

        energy: Optional[float] = None
        if isinstance(stance, dict) and "energy" in stance:
            try:
                energy = float(stance["energy"])
            except (TypeError, ValueError):
                energy = None

        string_id = qpc_result.get("string_id")
        sandbox_flag = bool(qpc_result.get("sandbox", False))
        environment = qpc_result.get("router_environment", "unknown")

        audio_response: Optional[bytes] = None
        if self.synthesize_fn and content:
            audio_response = self.synthesize_fn(content)

        return VoiceTurnResponse(
            transcript=transcript,
            content=content,
            audio_response=audio_response,
            sandbox=sandbox_flag,
            router_environment=environment,
            stance=stance if isinstance(stance, dict) else None,
            energy=energy,
            string_id=string_id,
            raw_qpc_payload=qpc_payload,
            raw_qpc_result=qpc_result,
        )
