"""
AQI Twilio Test Harness (v1.0)
------------------------------

Inbound/outbound Twilio endpoints that route audio through the
AQI Voice → QPC-2 wrapper for controlled testing.
"""

from __future__ import annotations

from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
from twilio.rest import Client

from aqi_voice_qpc_wrapper import VoiceQPCWrapper, VoiceTurnRequest


app = Flask(__name__)
wrapper: VoiceQPCWrapper | None = None

TWILIO_ACCOUNT_SID = "YOUR_SID"
TWILIO_AUTH_TOKEN = "YOUR_TOKEN"
TWILIO_FROM_NUMBER = "+15551234567"

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def _ensure_wrapper() -> VoiceQPCWrapper:
    if wrapper is None:
        raise RuntimeError("VoiceQPCWrapper not initialized. Set aqi_twilio_test_harness.wrapper before serving requests.")
    return wrapper


@app.route("/twilio/inbound-test", methods=["POST"])
def inbound_test() -> Response:
    voice_wrapper = _ensure_wrapper()

    caller = request.form.get("From", "unknown")
    recording_url = request.form.get("RecordingUrl")

    if not recording_url:
        vr = VoiceResponse()
        vr.say("No audio received.")
        return Response(str(vr), mimetype="text/xml")

    import requests

    audio_bytes = requests.get(recording_url).content

    req = VoiceTurnRequest(
        audio_bytes=audio_bytes,
        caller_id=caller,
        source="twilio_inbound_test",
        epistemic_layer="merchant_support",
        anchors=["twilio_inbound_test"],
        sandbox=True,
    )
    resp = voice_wrapper.process_voice_turn(req)

    vr = VoiceResponse()
    if resp.audio_response:
        vr.say(resp.content)
    else:
        vr.say(resp.content)

    return Response(str(vr), mimetype="text/xml")


def place_outbound_test_call(to_number: str, twiml_url: str) -> str:
    call = client.calls.create(
        from_=TWILIO_FROM_NUMBER,
        to=to_number,
        url=twiml_url,
    )
    return call.sid


@app.route("/twilio/outbound-test", methods=["POST"])
def outbound_test() -> Response:
    voice_wrapper = _ensure_wrapper()

    if "RecordingUrl" not in request.form:
        vr = VoiceResponse()
        vr.say("This is the AQI outbound test harness. Please speak after the beep.")
        vr.record(action="/twilio/outbound-test", max_length=10, play_beep=True)
        return Response(str(vr), mimetype="text/xml")

    caller = request.form.get("From", "unknown")
    recording_url = request.form["RecordingUrl"]

    import requests

    audio_bytes = requests.get(recording_url).content

    req = VoiceTurnRequest(
        audio_bytes=audio_bytes,
        caller_id=caller,
        source="twilio_outbound_test",
        epistemic_layer="merchant_support",
        anchors=["twilio_outbound_test"],
        sandbox=True,
    )
    resp = voice_wrapper.process_voice_turn(req)

    vr = VoiceResponse()
    vr.say(resp.content)
    return Response(str(vr), mimetype="text/xml")
