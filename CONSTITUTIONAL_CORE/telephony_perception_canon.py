# telephony_perception_canon.py
# Canon: Telephony Perception & Environmental Sovereignty

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Dict, Any


class TelephonyHealth(Enum):
    OK = auto()
    DEGRADED_AUDIO = auto()
    NO_AUDIO = auto()
    HIGH_LATENCY = auto()
    CALL_LEG_MISMATCH = auto()
    WEBHOOK_FAILURE = auto()
    UNKNOWN_FAILURE = auto()


@dataclass
class TelephonyTelemetry:
    # Raw telemetry from your telephony layer
    audio_packets_received: int
    audio_packets_lost: int
    avg_jitter_ms: float
    avg_rtt_ms: float
    has_inbound_audio: bool
    has_outbound_audio: bool
    a_leg_connected: bool
    b_leg_connected: bool
    webhook_ok: bool
    media_negotiated: bool


@dataclass
class TelephonyPerceptionResult:
    health: TelephonyHealth
    reason: str
    sovereign_state: str
    action: str
    message: Optional[str]


# ---------- CANONICAL PHRASES ----------

# Environmental Rush Hour (line failure)
ENV_WITHDRAWAL_PHRASE = (
    "I’m having trouble hearing you — the line might be acting up. "
    "I respect your time, so I’ll call you right back on a cleaner line."
)

# Environmental Degradation (but still usable)
ENV_DEGRADED_PHRASE = (
    "It sounds like the line is a little rough on my end, "
    "but if you’re okay with it, we can keep going."
)

# Environmental Latency (perceived delay)
ENV_LATENCY_PHRASE = (
    "There might be a slight delay on the line — if I ever step on you, "
    "I’ll pause and let you finish."
)


# ---------- CORE EVALUATION LOGIC ----------

def evaluate_telephony_health(t: TelephonyTelemetry) -> TelephonyHealth:
    # No media flowing at all
    if not t.media_negotiated or (not t.has_inbound_audio and not t.has_outbound_audio):
        return TelephonyHealth.NO_AUDIO

    # Call legs mismatched
    if t.a_leg_connected and not t.b_leg_connected:
        return TelephonyHealth.CALL_LEG_MISMATCH

    # Webhook failures / control-plane issues
    if not t.webhook_ok:
        return TelephonyHealth.WEBHOOK_FAILURE

    # High packet loss or jitter = degraded audio
    loss_ratio = 0.0
    if t.audio_packets_received > 0:
        loss_ratio = t.audio_packets_lost / max(1, t.audio_packets_received)

    if loss_ratio > 0.05 or t.avg_jitter_ms > 60:
        return TelephonyHealth.DEGRADED_AUDIO

    # High RTT = noticeable latency
    if t.avg_rtt_ms > 400:
        return TelephonyHealth.HIGH_LATENCY

    return TelephonyHealth.OK


def perceive_environment(t: TelephonyTelemetry) -> TelephonyPerceptionResult:
    health = evaluate_telephony_health(t)

    # Default: environment is fine, no intervention
    if health == TelephonyHealth.OK:
        return TelephonyPerceptionResult(
            health=health,
            reason="Environment stable.",
            sovereign_state="environment_stable",
            action="continue",
            message=None,
        )

    # NO AUDIO / CALL LEG / WEBHOOK FAILURE → Sovereign Withdrawal (Environmental)
    if health in {
        TelephonyHealth.NO_AUDIO,
        TelephonyHealth.CALL_LEG_MISMATCH,
        TelephonyHealth.WEBHOOK_FAILURE,
        TelephonyHealth.UNKNOWN_FAILURE,
    }:
        return TelephonyPerceptionResult(
            health=health,
            reason="Critical telephony failure detected.",
            sovereign_state="environment_rush_hour_withdrawal",
            action="hangup_and_callback",
            message=ENV_WITHDRAWAL_PHRASE,
        )

    # DEGRADED AUDIO → Acknowledge, keep sovereignty, continue if human is okay
    if health == TelephonyHealth.DEGRADED_AUDIO:
        return TelephonyPerceptionResult(
            health=health,
            reason="Degraded audio quality detected.",
            sovereign_state="environment_degraded",
            action="acknowledge_and_continue",
            message=ENV_DEGRADED_PHRASE,
        )

    # HIGH LATENCY → Acknowledge delay, adjust pacing
    if health == TelephonyHealth.HIGH_LATENCY:
        return TelephonyPerceptionResult(
            health=health,
            reason="High latency detected.",
            sovereign_state="environment_high_latency",
            action="acknowledge_and_slow_pacing",
            message=ENV_LATENCY_PHRASE,
        )

    # Fallback
    return TelephonyPerceptionResult(
        health=TelephonyHealth.UNKNOWN_FAILURE,
        reason="Unknown telephony anomaly.",
        sovereign_state="environment_unknown_anomaly",
        action="hangup_and_callback",
        message=ENV_WITHDRAWAL_PHRASE,
    )


# ---------- INTEGRATION HOOK FOR ALAN’S MAIN LOOP ----------

def telephony_perception_hook(telemetry_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point for agent_alan_business_ai.py

    Input: raw telemetry dict from your telephony layer.
    Output: a normalized governance object Alan can act on.
    """

    t = TelephonyTelemetry(
        audio_packets_received=telemetry_dict.get("audio_packets_received", 0),
        audio_packets_lost=telemetry_dict.get("audio_packets_lost", 0),
        avg_jitter_ms=telemetry_dict.get("avg_jitter_ms", 0.0),
        avg_rtt_ms=telemetry_dict.get("avg_rtt_ms", 0.0),
        has_inbound_audio=telemetry_dict.get("has_inbound_audio", False),
        has_outbound_audio=telemetry_dict.get("has_outbound_audio", False),
        a_leg_connected=telemetry_dict.get("a_leg_connected", False),
        b_leg_connected=telemetry_dict.get("b_leg_connected", False),
        webhook_ok=telemetry_dict.get("webhook_ok", True),
        media_negotiated=telemetry_dict.get("media_negotiated", True),
    )

    result = perceive_environment(t)

    # This is the object you feed into context_sovereign_governance.py
    # alongside the conversational state.
    return {
        "telephony_health": result.health.name,
        "reason": result.reason,
        "sovereign_state": result.sovereign_state,
        "action": result.action,
        "canonical_message": result.message,
    }
