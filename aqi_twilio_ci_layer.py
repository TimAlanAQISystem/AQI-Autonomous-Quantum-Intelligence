"""
AQI Twilio CI Integration Layer (v1.0)
--------------------------------------

Consumes Twilio Conversational Intelligence (CI) webhooks and
routes structured call intelligence into AQI's QPC-2 reasoning loop.
"""

from __future__ import annotations

from flask import Flask, request, jsonify
from typing import Dict, Any

from aqi_voice_qpc_wrapper import VoiceQPCWrapper, VoiceTurnRequest

app = Flask(__name__)
wrapper: VoiceQPCWrapper | None = None


def _require_wrapper() -> VoiceQPCWrapper:
    if wrapper is None:
        raise RuntimeError("VoiceQPCWrapper not initialized. Assign aqi_twilio_ci_layer.wrapper at startup.")
    return wrapper


def _route_ci_transcript_to_qpc(
    call_sid: str,
    speaker: str,
    transcript: str,
    sandbox: bool = True,
) -> Dict[str, Any]:
    voice_wrapper = _require_wrapper()

    req = VoiceTurnRequest(
        audio_bytes=b"",
        caller_id=f"ci_{call_sid}_{speaker}",
        source="twilio_ci",
        epistemic_layer="merchant_support",
        anchors=["twilio_ci", speaker],
        prior_string_id=None,
        sandbox=sandbox,
    )

    original_transcribe_fn = voice_wrapper.transcribe_fn
    voice_wrapper.transcribe_fn = lambda _: transcript
    try:
        resp = voice_wrapper.process_voice_turn(req)
    finally:
        voice_wrapper.transcribe_fn = original_transcribe_fn

    return {
        "transcript": resp.transcript,
        "content": resp.content,
        "stance": resp.stance,
        "energy": resp.energy,
        "string_id": resp.string_id,
        "sandbox": resp.sandbox,
    }


@app.route("/twilio/ci/transcript", methods=["POST"])
def ci_transcript():
    data = request.json or {}

    call_sid = data.get("call_sid")
    speaker = data.get("speaker", "unknown")
    transcript = data.get("transcript", "")

    if not transcript:
        return jsonify({"status": "ignored", "reason": "empty transcript"})

    qpc_result = _route_ci_transcript_to_qpc(
        call_sid=call_sid,
        speaker=speaker,
        transcript=transcript,
        sandbox=True,
    )

    return jsonify({"status": "ok", "qpc_result": qpc_result})


@app.route("/twilio/ci/sentiment", methods=["POST"])
def ci_sentiment():
    data = request.json or {}

    call_sid = data.get("call_sid")
    speaker = data.get("speaker")
    sentiment = data.get("sentiment")
    score = data.get("score")

    return jsonify({
        "status": "ok",
        "event": "sentiment",
        "call_sid": call_sid,
        "speaker": speaker,
        "sentiment": sentiment,
        "score": score,
    })


@app.route("/twilio/ci/summary", methods=["POST"])
def ci_summary():
    data = request.json or {}

    call_sid = data.get("call_sid")
    summary = data.get("summary") or "Call summary received."
    action_items = data.get("action_items", [])

    voice_wrapper = _require_wrapper()

    req = VoiceTurnRequest(
        audio_bytes=b"",
        caller_id=f"ci_summary_{call_sid}",
        source="twilio_ci_summary",
        epistemic_layer="merchant_support",
        anchors=["twilio_ci_summary"],
        sandbox=True,
    )

    original_transcribe_fn = voice_wrapper.transcribe_fn
    voice_wrapper.transcribe_fn = lambda _: summary

    try:
        resp = voice_wrapper.process_voice_turn(req)
    finally:
        voice_wrapper.transcribe_fn = original_transcribe_fn

    return jsonify({
        "status": "ok",
        "summary": summary,
        "action_items": action_items,
        "qpc_result": {
            "content": resp.content,
            "stance": resp.stance,
            "energy": resp.energy,
            "string_id": resp.string_id,
        },
    })


@app.route("/twilio/ci/call-end", methods=["POST"])
def ci_call_end():
    data = request.json or {}

    call_sid = data.get("call_sid")
    metrics = data.get("metrics", {})

    return jsonify({
        "status": "ok",
        "event": "call_end",
        "call_sid": call_sid,
        "metrics": metrics,
    })
