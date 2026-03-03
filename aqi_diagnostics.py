"""
aqi_diagnostics.py

Live-first Twilio → Tunnel → Backend diagnostic layer.
- Always reads from live system as source of truth.
- Uses history only as reference (patterns, regressions, deltas).
"""

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


# ========= Data models =========

@dataclasses.dataclass
class TunnelConfig:
    """Represents the *current* active tunnel configuration."""
    provider: str            # "ngrok", "cloudflared", etc.
    public_url: str          # e.g. "https://hierodulic-unfacaded-gemma.ngrok-free.dev"
    inspector_url: Optional[str] = None  # e.g. "http://127.0.0.1:4040"


@dataclasses.dataclass
class TwilioConfigSnapshot:
    """Snapshot of the *current* Twilio number configuration."""
    phone_number: str
    configure_with: str              # e.g. "Webhook"
    voice_webhook_url: str
    voice_webhook_method: str        # e.g. "POST"
    status_webhook_url: str
    status_webhook_method: str       # e.g. "POST"
    has_messaging_service: bool      # True if attached to a Messaging Service
    messaging_service_sid: Optional[str] = None


@dataclasses.dataclass
class BackendStatus:
    """Represents the *current* backend health."""
    is_running: bool
    base_url: str                    # e.g. "http://localhost:8777"
    details: Optional[str] = None


@dataclasses.dataclass
class WebhookProbeResult:
    """Result of a direct probe to a webhook endpoint."""
    url: str
    success: bool
    status_code: Optional[int]
    error: Optional[str] = None
    timestamp: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)


@dataclasses.dataclass
class InspectorRequestSummary:
    """Summary of live requests seen in the tunnel inspector."""
    total_requests: int
    last_request_at: Optional[datetime.datetime]
    last_paths: List[str]


@dataclasses.dataclass
class CallDiagnostic:
    """Single-call diagnostic combining live observations + historical reference."""
    call_sid: str
    duration_seconds: int
    status: str
    ai_engaged: bool
    live_tunnel_reached: bool
    live_backend_reached: bool
    twilio_config: TwilioConfigSnapshot
    tunnel_config: TunnelConfig
    backend_status: BackendStatus
    inspector_summary: InspectorRequestSummary
    webhook_probe_voice: WebhookProbeResult
    webhook_probe_status: WebhookProbeResult
    root_cause: str
    contributing_factors: List[str]
    created_at: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.utcnow)


# ========= History store (reference only, never treated as ground truth) =========

class DiagnosticHistory:
    """
    In-memory history of diagnostics.
    Used ONLY for pattern analysis and comparison, never as current truth.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: List[CallDiagnostic] = []

    def add(self, diag: CallDiagnostic) -> None:
        with self._lock:
            self._entries.append(diag)

    def last_n(self, n: int = 5) -> List[CallDiagnostic]:
        with self._lock:
            return self._entries[-n:]

    def to_json(self) -> str:
        with self._lock:
            return json.dumps([dataclasses.asdict(d) for d in self._entries], default=str, indent=2)


history = DiagnosticHistory()


# ========= Live config fetchers =========

def get_current_tunnel_config() -> TunnelConfig:
    """Fetch current tunnel config from environment."""
    import os
    url = os.environ.get('PUBLIC_TUNNEL_URL')
    if not url:
        return TunnelConfig(provider="unknown", public_url="")
    
    # Detect provider
    if "ngrok" in url:
        provider = "ngrok"
        inspector_url = "http://127.0.0.1:4040"
    elif "trycloudflare" in url:
        provider = "cloudflared"
        inspector_url = None  # cloudflared doesn't have inspector
    else:
        provider = "unknown"
        inspector_url = None
    
    return TunnelConfig(provider=provider, public_url=url, inspector_url=inspector_url)


def get_current_twilio_config() -> TwilioConfigSnapshot:
    """Fetch current Twilio number config from API."""
    import os
    sid = os.environ.get('TWILIO_ACCOUNT_SID')
    token = os.environ.get('TWILIO_AUTH_TOKEN')
    phone = os.environ.get('TWILIO_PHONE_NUMBER')
    
    if not all([sid, token, phone]):
        raise ValueError("Missing Twilio env vars")
    
    client = Client(sid, token)
    # Fetch number config
    numbers = client.incoming_phone_numbers.list(phone_number=phone)
    if not numbers:
        raise ValueError(f"Phone number {phone} not found in Twilio account")
    
    number = numbers[0]
    
    configure_with = getattr(number, 'voice_configure_with', 'unknown')
    voice_url = getattr(number, 'voice_url', '')
    voice_method = getattr(number, 'voice_method', 'POST')
    status_url = getattr(number, 'status_callback', '')
    status_method = getattr(number, 'status_callback_method', 'POST')
    messaging_service_sid = getattr(number, 'messaging_service_sid', None)
    has_messaging_service = messaging_service_sid is not None
    
    return TwilioConfigSnapshot(
        phone_number=phone,
        configure_with=configure_with,
        voice_webhook_url=voice_url,
        voice_webhook_method=voice_method,
        status_webhook_url=status_url,
        status_webhook_method=status_method,
        has_messaging_service=has_messaging_service,
        messaging_service_sid=messaging_service_sid,
    )


def get_current_backend_status() -> BackendStatus:
    """Check if backend is running on port 8777."""
    import socket
    base_url = "http://localhost:8777"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', 8777))
            is_running = result == 0
    except:
        is_running = False
    
    details = "Running" if is_running else "Not running"
    return BackendStatus(is_running=is_running, base_url=base_url, details=details)


# ========= Live probe helpers =========

def probe_webhook(url: str, method: str = "POST", timeout: int = 5) -> WebhookProbeResult:
    """Hit the webhook directly from the backend's environment."""
    try:
        if method.upper() == "POST":
            resp = requests.post(url, json={"diagnostic": True}, timeout=timeout)
        else:
            resp = requests.get(url, timeout=timeout)

        return WebhookProbeResult(
            url=url,
            success=resp.ok,
            status_code=resp.status_code,
            error=None
        )
    except Exception as e:
        return WebhookProbeResult(
            url=url,
            success=False,
            status_code=None,
            error=str(e)
        )


def fetch_ngrok_inspector_summary(inspector_url: str) -> InspectorRequestSummary:
    """
    Reads live request data from ngrok inspector.
    Never guesses; if it can't read, it reports '0 requests' + error in logs.
    """
    try:
        resp = requests.get(f"{inspector_url}/api/requests/http")
        resp.raise_for_status()
        data = resp.json()

        requests_list = data.get("requests", [])
        total = len(requests_list)

        last_paths = []
        last_request_at = None

        if requests_list:
            # Sort by latest
            requests_list.sort(key=lambda r: r.get("start", ""), reverse=True)
            last = requests_list[0]
            last_paths.append(last.get("uri", ""))
            last_request_at = _parse_ngrok_time(last.get("start"))

        return InspectorRequestSummary(
            total_requests=total,
            last_request_at=last_request_at,
            last_paths=last_paths
        )
    except Exception as e:
        logger.warning(f"Failed to read ngrok inspector: {e}")
        return InspectorRequestSummary(
            total_requests=0,
            last_request_at=None,
            last_paths=[]
        )


def _parse_ngrok_time(value: Optional[str]) -> Optional[datetime.datetime]:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


# ========= Core diagnostic function =========

def diagnose_call(
    call_sid: str,
    duration_seconds: int,
    status: str,
    ai_engaged: bool,
    twilio_cfg: TwilioConfigSnapshot,
    tunnel_cfg: TunnelConfig,
    backend: BackendStatus,
) -> CallDiagnostic:
    """
    Core diagnostic: Twilio -> Tunnel -> Backend.
    Live-first, history-aware, never trusts cached state as truth.
    """

    # 1. Live checks only – no history, no assumptions

    # 1a. Probe voice webhook directly
    voice_probe = probe_webhook(
        url=twilio_cfg.voice_webhook_url,
        method=twilio_cfg.voice_webhook_method
    )

    # 1b. Probe status webhook directly
    status_probe = probe_webhook(
        url=twilio_cfg.status_webhook_url,
        method=twilio_cfg.status_webhook_method
    )

    # 1c. If we have a tunnel inspector, read live requests
    if tunnel_cfg.inspector_url:
        inspector_summary = fetch_ngrok_inspector_summary(tunnel_cfg.inspector_url)
    else:
        inspector_summary = InspectorRequestSummary(
            total_requests=0,
            last_request_at=None,
            last_paths=[]
        )

    # 1d. Live booleans
    live_tunnel_reached = inspector_summary.total_requests > 0
    live_backend_reached = backend.is_running and (voice_probe.success or status_probe.success)

    # 2. Determine root cause from *live* facts only

    root_cause = "Unknown"
    contributing: List[str] = []

    # Short-circuit obvious cases
    if not backend.is_running:
        root_cause = "Backend is not running"
        contributing.append("Twilio cannot reach a service that is offline.")

    elif not voice_probe.success and not status_probe.success:
        # Neither webhook responds successfully
        root_cause = "Webhooks unreachable from backend environment"
        contributing.append("Direct HTTP probe to Twilio webhooks failed from the backend host.")

    elif not live_tunnel_reached and duration_seconds <= 5 and not ai_engaged:
        root_cause = "Twilio is not sending requests to the tunnel"
        contributing.append("Tunnel inspector shows no live requests during or after the call.")

    elif live_tunnel_reached and not live_backend_reached:
        root_cause = "Tunnel reachable but backend unreachable"
        contributing.append("Tunnel receives traffic but backend does not respond successfully.")

    elif status.lower() == "completed" and duration_seconds <= 5 and not ai_engaged:
        root_cause = "Call ended before AI engagement due to early termination"
        contributing.append("Twilio completed the call quickly with no successful AI interaction.")

    # 3. History-aware adjustments (reference only)

    recent = history.last_n(3)
    if recent:
        # Example: detect persistent pattern of "Twilio is not sending requests to the tunnel"
        same_root = all(r.root_cause == root_cause for r in recent)
        if same_root and root_cause != "Unknown":
            contributing.append(f"Pattern matches last {len(recent)} calls with same root cause: {root_cause}.")

        # Example: detect regression
        previously_successful = any(r.live_tunnel_reached and r.live_backend_reached for r in recent)
        if previously_successful and (not live_tunnel_reached or not live_backend_reached):
            contributing.append("This represents a regression from earlier successful tunnel/backend connectivity.")

    diag = CallDiagnostic(
        call_sid=call_sid,
        duration_seconds=duration_seconds,
        status=status,
        ai_engaged=ai_engaged,
        live_tunnel_reached=live_tunnel_reached,
        live_backend_reached=live_backend_reached,
        twilio_config=twilio_cfg,
        tunnel_config=tunnel_cfg,
        backend_status=backend,
        inspector_summary=inspector_summary,
        webhook_probe_voice=voice_probe,
        webhook_probe_status=status_probe,
        root_cause=root_cause,
        contributing_factors=contributing,
    )

    # 4. Persist for reference (never future truth)
    history.add(diag)

    return diag


# ========= Example usage =========

def run_live_diagnostic_example(call_sid: str, duration: int, status: str, ai_engaged: bool):
    try:
        tunnel_cfg = get_current_tunnel_config()
        twilio_cfg = get_current_twilio_config()
        backend = get_current_backend_status()
        
        diag = diagnose_call(
            call_sid=call_sid,
            duration_seconds=duration,
            status=status,
            ai_engaged=ai_engaged,
            twilio_cfg=twilio_cfg,
            tunnel_cfg=tunnel_cfg,
            backend=backend,
        )
        
        print("Root cause:", diag.root_cause)
        print("Contributing factors:")
        for c in diag.contributing_factors:
            print(" -", c)
        
        return diag
    except Exception as e:
        print(f"Error running diagnostic: {e}")
        return None


if __name__ == "__main__":
    # Example with last call SID
    run_live_diagnostic_example("CA0ff11c066dacf0a5001320d3cbb01cca", 3, "completed", False)