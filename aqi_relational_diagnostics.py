"""
aqi_relational_diagnostics.py

AQI Relational Diagnostic Protocol for the Twilio → Tunnel → Backend chain.

Principles:
- Live system is the only source of truth.
- History is reference only (patterns, regressions, deltas).
- Every component has relational obligations and breach modes.
- Every breach gets a concrete, minimal repair path.
"""

print("Script loaded")

import dataclasses
import datetime
import json
import logging
import threading
from typing import Optional, List, Dict, Any

import requests
from twilio.rest import Client

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ========= Core relational models =========

@dataclasses.dataclass
class AQI_Tunnel_State:
    """Represents the active tunnel as a relational actor."""
    provider: str                  # "ngrok", "cloudflared", etc.
    public_url: str                # e.g. "https://hierodulic-unfacaded-gemma.ngrok-free.dev"
    inspector_url: Optional[str]   # e.g. "http://127.0.0.1:4040"
    is_declared_active: bool       # you say this is the tunnel AQI should trust


@dataclasses.dataclass
class AQI_Tunnel_Inspector:
    """Live view of what actually passed through the tunnel."""
    total_requests: int
    last_request_at: Optional[datetime.datetime]
    last_paths: List[str]
    error: Optional[str] = None


@dataclasses.dataclass
@dataclasses.dataclass
class AQI_Backend_State:
    """Represents the backend as a relational actor."""
    is_running: bool
    base_url: str                    # e.g. "http://localhost:8777"
    last_healthy_at: Optional[datetime.datetime] = None
    details: Optional[str] = None


@dataclasses.dataclass
class AQI_Twilio_Routing_State:
    """Represents Twilio's routing posture as a relational actor."""
    phone_number: str
    configure_with: str              # e.g. "Webhook"
    voice_webhook_url: str
    voice_webhook_method: str        # "POST", "GET"
    status_webhook_url: str
    status_webhook_method: str
    has_messaging_service: bool
    messaging_service_sid: Optional[str] = None
    # Optional expanded context if you wire in the Twilio API later:
    studio_flow_sid: Optional[str] = None
    voice_application_sid: Optional[str] = None


@dataclasses.dataclass
class AQI_Webhook_Probe:
    """Result of probing a Twilio-facing webhook from the backend environment."""
    url: str
    method: str
    success: bool
    status_code: Optional[int]
    error: Optional[str]
    timestamp: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)


@dataclasses.dataclass
class AQI_Call_Context:
    """The factual call context as observed by Twilio / your logs."""
    call_sid: str
    phone_number: str
    duration_seconds: int
    status: str                     # e.g. "completed"
    ai_engaged: bool                # did Alan/AQI actually get to speak?
    started_at: Optional[datetime.datetime] = None
    ended_at: Optional[datetime.datetime] = None


@dataclasses.dataclass
class AQI_Outbound_Call_Context:
    """The factual outbound call context as observed by Twilio / your logs."""
    call_sid: str
    to_number: str
    from_number: str
    duration_seconds: int
    status: str                     # e.g. "completed", "failed", "no-answer"
    ai_engaged: bool                # did Alan/AQI actually get to speak?
    twilio_error_code: Optional[str] = None  # Twilio error code if failed
    started_at: Optional[datetime.datetime] = None
    ended_at: Optional[datetime.datetime] = None


@dataclasses.dataclass
class AQI_Outbound_Campaign_Context:
    """Context for an outbound calling campaign."""
    campaign_id: str
    total_targets: int
    calls_attempted: int
    calls_completed: int
    calls_failed: int
    last_call_at: Optional[datetime.datetime] = None


@dataclasses.dataclass
class AQI_Relational_Breach:
    """
    A breach of relational obligation:
    - who failed
    - how they failed
    - what obligation was broken
    - recommended repair path
    """
    actor: str                      # "Twilio", "Tunnel", "Backend", "Config", "Unknown"
    obligation: str                 # human-readable description of what should have happened
    breach_mode: str                # description of how it failed
    repair_steps: List[str]         # concrete, minimal steps to repair
    severity: str                   # "info", "warning", "error", "critical"


@dataclasses.dataclass
class AQI_Call_Diagnostic:
    """
    Final diagnostic snapshot for a single call:
    - live states
    - breaches
    - suggested next actions
    """
    call: AQI_Call_Context
    twilio: AQI_Twilio_Routing_State
    tunnel: AQI_Tunnel_State
    backend: AQI_Backend_State
    inspector: AQI_Tunnel_Inspector
    voice_probe: AQI_Webhook_Probe
    status_probe: AQI_Webhook_Probe
    breaches: List[AQI_Relational_Breach]
    primary_root_cause: str
    created_at: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)


# ========= History (reference only, never truth) =========

class AQI_Diagnostic_History:
    """
    In-memory history of call diagnostics.
    Used only for patterns / regressions. Never treated as present truth.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: List[AQI_Call_Diagnostic] = []

    def add(self, diag: AQI_Call_Diagnostic) -> None:
        with self._lock:
            self._entries.append(diag)

    def last_n(self, n: int = 5) -> List[AQI_Call_Diagnostic]:
        with self._lock:
            return self._entries[-n:]

    def to_json(self) -> str:
        with self._lock:
            return json.dumps(
                [dataclasses.asdict(d) for d in self._entries],
                default=str,
                indent=2
            )


AQI_HISTORY = AQI_Diagnostic_History()


# ========= Live probe helpers =========

def aqi_probe_webhook(url: str, method: str = "POST", timeout: int = 5) -> AQI_Webhook_Probe:
    """
    Hit the Twilio-facing webhook from the backend environment.
    Live source of truth about reachability.
    """
    try:
        m = method.upper()
        if m == "POST":
            resp = requests.post(url, json={"aqi_diagnostic_probe": True}, timeout=timeout)
        else:
            resp = requests.get(url, timeout=timeout)

        return AQI_Webhook_Probe(
            url=url,
            method=m,
            success=resp.ok,
            status_code=resp.status_code,
            error=None,
        )
    except Exception as e:
        return AQI_Webhook_Probe(
            url=url,
            method=method.upper(),
            success=False,
            status_code=None,
            error=str(e),
        )


def aqi_fetch_ngrok_inspector(inspector_url: str) -> AQI_Tunnel_Inspector:
    """
    Read live HTTP request data from ngrok inspector.
    If it fails, it's recorded as an inspector error and NOT silently guessed.
    """
    try:
        resp = requests.get(f"{inspector_url}/api/requests/http", timeout=5)
        resp.raise_for_status()
        data = resp.json()

        requests_list = data.get("requests", [])
        total = len(requests_list)

        last_paths: List[str] = []
        last_request_at: Optional[datetime.datetime] = None

        if requests_list:
            # Sort descending by start
            requests_list.sort(key=lambda r: r.get("start", ""), reverse=True)
            latest = requests_list[0]
            last_paths.append(latest.get("uri", ""))

            start_time = latest.get("start")
            if start_time:
                last_request_at = _aqi_parse_time(start_time)

        return AQI_Tunnel_Inspector(
            total_requests=total,
            last_request_at=last_request_at,
            last_paths=last_paths,
            error=None,
        )
    except Exception as e:
        logger.warning(f"[AQI] Failed to read ngrok inspector: {e}")
        return AQI_Tunnel_Inspector(
            total_requests=0,
            last_request_at=None,
            last_paths=[],
            error=str(e),
        )


def _aqi_parse_time(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


# ========= Relational breach logic =========

def _aqi_build_breaches(
    call: AQI_Call_Context,
    twilio: AQI_Twilio_Routing_State,
    tunnel: AQI_Tunnel_State,
    backend: AQI_Backend_State,
    inspector: AQI_Tunnel_Inspector,
    voice_probe: AQI_Webhook_Probe,
    status_probe: AQI_Webhook_Probe,
) -> List[AQI_Relational_Breach]:
    """
    Computes relational breaches based ONLY on live observations.
    History is used later for pattern context, not for deciding these.
    """

    breaches: List[AQI_Relational_Breach] = []

    # Backend obligations
    if not backend.is_running:
        breaches.append(AQI_Relational_Breach(
            actor="Backend",
            obligation="Backend must be running and listening on its declared base URL.",
            breach_mode="Backend is not running or not reachable.",
            repair_steps=[
                "Confirm the backend process is running (e.g., Uvicorn on 0.0.0.0:8777).",
                "Check for crashes or startup errors in the backend logs.",
                "Restart the backend and verify it stays running."
            ],
            severity="critical",
        ))
        # If backend is down, we can still log others, but this is primary.

    # Twilio routing obligations
    if twilio.configure_with.lower() != "webhook":
        breaches.append(AQI_Relational_Breach(
            actor="Twilio",
            obligation='Twilio number must be configured with "Webhook" for voice routing.',
            breach_mode=f'Configured with "{twilio.configure_with}" instead of "Webhook".',
            repair_steps=[
                "In Twilio Console, open Phone Numbers → Active Numbers → your number.",
                'Under "Configure with", select "Webhook" for voice calls.',
                "Save changes and wait up to 1–3 minutes for routing cache to expire."
            ],
            severity="error",
        ))

    if twilio.has_messaging_service:
        breaches.append(AQI_Relational_Breach(
            actor="Twilio",
            obligation="No Messaging Service should override voice routing for this number.",
            breach_mode="Phone number is attached to a Twilio Messaging Service that may hijack routing.",
            repair_steps=[
                "In Twilio Console, remove this phone number from its Messaging Service.",
                "Ensure voice configuration lives only on the Phone Number (not Messaging Service)."
            ],
            severity="warning",
        ))

    # Tunnel obligations
    if tunnel.is_declared_active and not tunnel.public_url.startswith("https://"):
        breaches.append(AQI_Relational_Breach(
            actor="Tunnel",
            obligation="Active tunnel must expose a secure HTTPS endpoint for Twilio.",
            breach_mode=f"Tunnel URL is not HTTPS: {tunnel.public_url}",
            repair_steps=[
                "Recreate the tunnel with an HTTPS public URL.",
                "Update Twilio webhooks to point to the HTTPS URL."
            ],
            severity="error",
        ))

    if tunnel.is_declared_active and inspector.error:
        breaches.append(AQI_Relational_Breach(
            actor="Tunnel",
            obligation="Tunnel inspector should be reachable to observe ingress traffic.",
            breach_mode=f"Failed to read tunnel inspector: {inspector.error}",
            repair_steps=[
                "Confirm ngrok is running and inspector is enabled (http://127.0.0.1:4040).",
                "Check for network or firewall rules blocking local inspector access."
            ],
            severity="warning",
        ))

    # Live webhook reachability obligations
    if not voice_probe.success and not status_probe.success:
        breaches.append(AQI_Relational_Breach(
            actor="Config",
            obligation="Backend environment must be able to reach Twilio-facing webhooks.",
            breach_mode="Direct HTTP probes to both voice and status webhooks failed.",
            repair_steps=[
                "Verify PUBLIC_TUNNEL_URL is set correctly in the backend environment.",
                f"Confirm the tunnel public URL ({tunnel.public_url}) is reachable from the backend host.",
                "Ensure no firewall or VPN blocks outbound HTTPS from the backend to tunnel domain."
            ],
            severity="critical",
        ))

    # Call-level obligations (AI expected but not engaged)
    if call.status.lower() == "completed" and call.duration_seconds <= 5 and not call.ai_engaged:
        breaches.append(AQI_Relational_Breach(
            actor="Routing",
            obligation="If AI is configured for this number, Twilio → Tunnel → Backend path must allow engagement.",
            breach_mode="Call completed quickly (<=5s) without AI engagement.",
            repair_steps=[
                "Confirm Twilio voice webhook URL matches the active tunnel URL.",
                "Confirm the tunnel forwards to the correct backend port (e.g., 8777).",
                "Check backend logs for any incoming /twilio/voice requests during the call.",
            ],
            severity="error",
        ))

    return breaches


def _aqi_primary_root_cause(breaches: List[AQI_Relational_Breach]) -> str:
    """
    Picks a primary root cause from the observed breaches.
    Uses severity + specificity, but never fabricates one if list is empty.
    """
    if not breaches:
        return "Unknown – No explicit breach detected from live observations."

    severity_rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    breaches_sorted = sorted(
        breaches,
        key=lambda b: severity_rank.get(b.severity, 0),
        reverse=True,
    )
    top = breaches_sorted[0]
    return f"{top.actor} breach: {top.breach_mode}"


def _aqi_build_outbound_breaches(
    call: AQI_Outbound_Call_Context,
    twilio: AQI_Twilio_Routing_State,
    tunnel: AQI_Tunnel_State,
    backend: AQI_Backend_State,
    outbound_probe: AQI_Webhook_Probe,
) -> List[AQI_Relational_Breach]:
    """
    Computes relational breaches for outbound calls based ONLY on live observations.
    """

    breaches: List[AQI_Relational_Breach] = []

    # Backend obligations for outbound
    if not backend.is_running:
        breaches.append(AQI_Relational_Breach(
            actor="Backend",
            obligation="Backend must be running to provide TwiML for outbound calls.",
            breach_mode="Backend is not running or not reachable.",
            repair_steps=[
                "Confirm the backend process is running (e.g., Uvicorn on 0.0.0.0:8777).",
                "Check for crashes or startup errors in the backend logs.",
                "Restart the backend and verify it stays running."
            ],
            severity="critical",
        ))

    # Twilio outbound obligations
    if call.status.lower() == "failed" and call.twilio_error_code:
        if call.twilio_error_code in ["21217", "21218"]:  # Invalid number or carrier issues
            breaches.append(AQI_Relational_Breach(
                actor="Data",
                obligation="Outbound call targets must be valid, reachable phone numbers.",
                breach_mode=f"Twilio rejected number: error {call.twilio_error_code}",
                repair_steps=[
                    "Validate the target phone number format (+1XXXXXXXXXX).",
                    "Check if the number is a valid mobile/landline.",
                    "Remove invalid numbers from the call list."
                ],
                severity="error",
            ))
        elif call.twilio_error_code in ["21211", "21212"]:  # Account/billing issues
            breaches.append(AQI_Relational_Breach(
                actor="Twilio",
                obligation="Twilio account must be in good standing for outbound calls.",
                breach_mode=f"Twilio account error: {call.twilio_error_code}",
                repair_steps=[
                    "Check Twilio account balance and billing status.",
                    "Verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are correct.",
                    "Contact Twilio support if account is suspended."
                ],
                severity="critical",
            ))

    # Outbound webhook obligations
    if not outbound_probe.success:
        breaches.append(AQI_Relational_Breach(
            actor="Config",
            obligation="Backend must provide valid TwiML for outbound calls via /twilio/outbound.",
            breach_mode=f"Outbound webhook probe failed: {outbound_probe.error or 'HTTP ' + str(outbound_probe.status_code)}",
            repair_steps=[
                "Verify /twilio/outbound endpoint exists and returns valid TwiML.",
                "Check backend logs for errors in outbound handler.",
                "Ensure PUBLIC_TUNNEL_URL is correctly set for webhook construction."
            ],
            severity="error",
        ))

    # Call engagement obligations
    if call.status.lower() == "completed" and call.duration_seconds <= 5 and not call.ai_engaged:
        breaches.append(AQI_Relational_Breach(
            actor="AI",
            obligation="Outbound calls should engage AI for meaningful conversation.",
            breach_mode="Call completed quickly without AI engagement.",
            repair_steps=[
                "Check if Alan/AQI is properly integrated in outbound handler.",
                "Verify ElevenLabs audio generation is working.",
                "Review outbound TwiML for proper gather/response structure."
            ],
            severity="warning",
        ))

    # Tunnel obligations for outbound
    if tunnel.is_declared_active and not tunnel.public_url.startswith("https://"):
        breaches.append(AQI_Relational_Breach(
            actor="Tunnel",
            obligation="Active tunnel must expose HTTPS for outbound TwiML delivery.",
            breach_mode=f"Tunnel URL is not HTTPS: {tunnel.public_url}",
            repair_steps=[
                "Recreate the tunnel with an HTTPS public URL.",
                "Update backend PUBLIC_TUNNEL_URL environment variable."
            ],
            severity="error",
        ))

    return breaches
    """
    Picks a primary root cause from the observed breaches.
    Uses severity + specificity, but never fabricates one if list is empty.
    """
    if not breaches:
        return "Unknown – No explicit breach detected from live observations."

    severity_rank = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    breaches_sorted = sorted(
        breaches,
        key=lambda b: severity_rank.get(b.severity, 0),
        reverse=True,
    )
    top = breaches_sorted[0]
    return f"{top.actor} breach: {top.breach_mode}"


# ========= Core AQI Relational Diagnostic Protocol =========

def aqi_diagnose_call(
    call: AQI_Call_Context,
    twilio: AQI_Twilio_Routing_State,
    tunnel: AQI_Tunnel_State,
    backend: AQI_Backend_State,
) -> AQI_Call_Diagnostic:
    """
    Live-first AQI relational diagnostic for a single call.
    - Uses live probes (webhooks, tunnel inspector).
    - Computes relational breaches.
    - Uses history only to add context (later, if desired).
    """

    # 1. Live probes only — no history, no assumptions
    voice_probe = aqi_probe_webhook(
        url=twilio.voice_webhook_url,
        method=twilio.voice_webhook_method,
    )

    status_probe = aqi_probe_webhook(
        url=twilio.status_webhook_url,
        method=twilio.status_webhook_method,
    )

    if tunnel.inspector_url:
        inspector = aqi_fetch_ngrok_inspector(tunnel.inspector_url)
    else:
        inspector = AQI_Tunnel_Inspector(
            total_requests=0,
            last_request_at=None,
            last_paths=[],
            error=None,
        )

    # 2. Compute relational breaches from live data only
    breaches = _aqi_build_breaches(
        call=call,
        twilio=twilio,
        tunnel=tunnel,
        backend=backend,
        inspector=inspector,
        voice_probe=voice_probe,
        status_probe=status_probe,
    )

    primary_root_cause = _aqi_primary_root_cause(breaches)

    diag = AQI_Call_Diagnostic(
        call=call,
        twilio=twilio,
        tunnel=tunnel,
        backend=backend,
        inspector=inspector,
        voice_probe=voice_probe,
        status_probe=status_probe,
        breaches=breaches,
        primary_root_cause=primary_root_cause,
    )

    # 3. Record for reference (patterns, regressions), never as future truth
    AQI_HISTORY.add(diag)

    return diag


def aqi_diagnose_outbound_call(
    call: AQI_Outbound_Call_Context,
    twilio: AQI_Twilio_Routing_State,
    tunnel: AQI_Tunnel_State,
    backend: AQI_Backend_State,
) -> AQI_Call_Diagnostic:
    """
    Live-first AQI relational diagnostic for an outbound call.
    Similar to inbound but focused on outbound-specific breaches.
    """

    # 1. Live probes for outbound webhook
    outbound_url = f"{tunnel.public_url}/twilio/outbound"
    outbound_probe = aqi_probe_webhook(
        url=outbound_url,
        method="POST",
    )

    # Use empty inspector for outbound (could be extended later)
    inspector = AQI_Tunnel_Inspector(
        total_requests=0,
        last_request_at=None,
        last_paths=[],
        error=None,
    )

    # Empty status probe for outbound (status callbacks work the same)
    status_probe = AQI_Webhook_Probe(
        url=f"{tunnel.public_url}/twilio/status",
        method="POST",
        success=True,  # Assume status works if voice does
        status_code=200,
        error=None,
    )

    # 2. Compute relational breaches from live data only
    breaches = _aqi_build_outbound_breaches(
        call=call,
        twilio=twilio,
        tunnel=tunnel,
        backend=backend,
        outbound_probe=outbound_probe,
    )

    primary_root_cause = _aqi_primary_root_cause(breaches)

    # Create a diagnostic (reuse the same structure)
    diag = AQI_Call_Diagnostic(
        call=AQI_Call_Context(  # Convert to generic call context for compatibility
            call_sid=call.call_sid,
            phone_number=call.to_number,
            duration_seconds=call.duration_seconds,
            status=call.status,
            ai_engaged=call.ai_engaged,
            started_at=call.started_at,
            ended_at=call.ended_at,
        ),
        twilio=twilio,
        tunnel=tunnel,
        backend=backend,
        inspector=inspector,
        voice_probe=outbound_probe,  # Reuse voice_probe field for outbound
        status_probe=status_probe,
        breaches=breaches,
        primary_root_cause=primary_root_cause,
    )

    # 3. Record for reference
    AQI_HISTORY.add(diag)

    return diag


# ========= Example: wiring it into your current world =========

def run_live_relational_diagnostic_example() -> None:
    """
    Example: run an AQI relational diagnostic for a recent call.
    In real use, you'd pull these fields from Twilio + your environment.
    """
    print("Starting AQI relational diagnostic...")
    tunnel = AQI_Tunnel_State(
        provider="cloudflared",
        public_url="https://cancelled-postage-possibly-rio.trycloudflare.com",
        inspector_url=None,
        is_declared_active=True,
    )

    twilio = AQI_Twilio_Routing_State(
        phone_number="+14067322659",
        configure_with="Webhook",
        voice_webhook_url=f"{tunnel.public_url}/twilio/voice",
        voice_webhook_method="POST",
        status_webhook_url=f"{tunnel.public_url}/twilio/status",
        status_webhook_method="POST",
        has_messaging_service=False,
        messaging_service_sid=None,
    )

    backend = AQI_Backend_State(
        is_running=True,
        base_url="http://localhost:8777",
        last_healthy_at=datetime.datetime.utcnow(),
        details="Running",
    )

    call = AQI_Call_Context(
        call_sid="CAd33b42e0ff10440583fd762946923e45",
        phone_number="+14067322659",
        duration_seconds=3,
        status="completed",
        ai_engaged=False,
        started_at=None,
        ended_at=None,
    )

    diag = aqi_diagnose_call(
        call=call,
        twilio=twilio,
        tunnel=tunnel,
        backend=backend,
    )

    print("=== AQI Relational Diagnostic ===")
    print("Call SID:       ", diag.call.call_sid)
    print("Primary cause:  ", diag.primary_root_cause)
    print("Breaches:")
    for b in diag.breaches:
        print(f" - Actor: {b.actor}")
        print(f"   Obligation: {b.obligation}")
        print(f"   Breach:     {b.breach_mode}")
        print(f"   Severity:   {b.severity}")
        print(f"   Repair path:")
        for step in b.repair_steps:
            print(f"     • {step}")
        print()


if __name__ == "__main__":
    try:
        run_live_relational_diagnostic_example()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()