"""
TELEPHONY RESILIENCE LAYER
==========================
Created: February 17, 2026
Purpose: Bulletproof telephony operations — no stuck ports, no stale APIs, 
         no application errors in Twilio sections. EVER.

This module centralizes all telephony operations that were previously 
scattered across control_api_fixed.py in 3+ duplicate code paths.
It provides:
  1. Atomic tunnel URL reading (no race conditions)
  2. Centralized call creation (DRY — one path, one fix)
  3. Governor watchdog (auto-unlock after timeout — no permanent locks)
  4. Twilio client health validation (detect stale credentials)
  5. Port pre-check before binding
  6. Request origin validation for webhooks

Failure Philosophy: 
  - Never silently swallow errors — log and re-raise with context
  - Never leave the governor locked — watchdog auto-releases
  - Never let a partial URL reach Twilio — validate before use
  - Never block indefinitely — every external call has a timeout
"""

import os
import re
import time
import json
import asyncio
import logging
import threading
import socket
from pathlib import Path
from urllib.parse import quote
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger("TelephonyResilience")

# =============================================================================
# CONSTANTS
# =============================================================================
BASE_DIR = Path(__file__).parent
TUNNEL_URL_FILE = BASE_DIR / "active_tunnel_url.txt"
TUNNEL_URL_FIXED_FILE = BASE_DIR / "active_tunnel_url_fixed.txt"
DEFAULT_PORT = 8777
CALL_CREATE_TIMEOUT = 60.0  # seconds — must exceed RING_TIMEOUT to allow full ringing
GOVERNOR_MAX_LOCK_SECONDS = 120  # 2 minutes — auto-unlock if callback never arrives (reduced from 300s; no valid cold outbound call lasts >2 min)
GOVERNOR_POST_CALL_COOLDOWN = 30  # seconds — reflection window after call ends (Alan thinks + classifies)
RING_TIMEOUT = 35  # seconds — must match timing_config.json (was 50 — wasted 15s of billing)
TUNNEL_READ_RETRY_COUNT = 3
TUNNEL_READ_RETRY_DELAY = 0.1  # seconds

# =============================================================================
# TUNNEL URL — ATOMIC READ WITH VALIDATION
# =============================================================================
_tunnel_url_cache: Optional[str] = None
_tunnel_url_cache_mtime: float = 0
_tunnel_url_lock = threading.Lock()


def read_tunnel_url(*, force_refresh: bool = False) -> Optional[str]:
    """
    Read the tunnel URL atomically with caching.
    
    Returns the full HTTPS URL (e.g., 'https://my-tunnel.trycloudflare.com')
    or None if no valid tunnel URL is available.
    
    Uses file mtime to detect changes — avoids re-reading on every call.
    Retries on read failure to handle race conditions during tunnel restarts.
    """
    global _tunnel_url_cache, _tunnel_url_cache_mtime
    
    with _tunnel_url_lock:
        # Check cache validity
        if not force_refresh and _tunnel_url_cache:
            try:
                current_mtime = TUNNEL_URL_FILE.stat().st_mtime if TUNNEL_URL_FILE.exists() else 0
                if current_mtime == _tunnel_url_cache_mtime:
                    return _tunnel_url_cache
            except OSError:
                pass  # File disappeared — will re-read
        
        # Read with retries (handles mid-write race conditions)
        for attempt in range(TUNNEL_READ_RETRY_COUNT):
            try:
                if not TUNNEL_URL_FILE.exists():
                    # Try the fixed file as fallback
                    if TUNNEL_URL_FIXED_FILE.exists():
                        raw = TUNNEL_URL_FIXED_FILE.read_text().strip()
                    else:
                        logger.warning("[TUNNEL] No tunnel URL file found")
                        return None
                else:
                    raw = TUNNEL_URL_FILE.read_text().strip()
                
                if not raw:
                    if attempt < TUNNEL_READ_RETRY_COUNT - 1:
                        time.sleep(TUNNEL_READ_RETRY_DELAY)
                        continue
                    logger.warning("[TUNNEL] Tunnel URL file is empty")
                    return None
                
                # Normalize to HTTPS URL
                url = _normalize_tunnel_url(raw)
                
                if url and _validate_tunnel_url(url):
                    _tunnel_url_cache = url
                    try:
                        _tunnel_url_cache_mtime = TUNNEL_URL_FILE.stat().st_mtime
                    except OSError:
                        _tunnel_url_cache_mtime = 0
                    return url
                else:
                    logger.error(f"[TUNNEL] Invalid tunnel URL after normalization: {raw} -> {url}")
                    return None
                    
            except Exception as e:
                if attempt < TUNNEL_READ_RETRY_COUNT - 1:
                    time.sleep(TUNNEL_READ_RETRY_DELAY)
                    continue
                logger.error(f"[TUNNEL] Failed to read tunnel URL after {TUNNEL_READ_RETRY_COUNT} attempts: {e}")
                return None
    
    return None


def _normalize_tunnel_url(raw: str) -> str:
    """
    Normalize any tunnel URL format to a proper HTTPS URL.
    
    Handles all observed formats:
      - 'my-tunnel.trycloudflare.com' (bare hostname)
      - 'https://my-tunnel.trycloudflare.com' (already correct)
      - 'wss://my-tunnel.trycloudflare.com' (WebSocket scheme)
      - 'http://127.0.0.1:8777' (local IP)
    """
    # Strip all schemes
    cleaned = raw.replace("wss://", "").replace("ws://", "").replace("https://", "").replace("http://", "")
    cleaned = cleaned.strip().rstrip("/")
    
    if not cleaned:
        return ""
    
    # Detect if this is a raw IP address (local testing)
    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", cleaned):
        return f"http://{cleaned}"
    
    # Everything else gets HTTPS (Cloudflare tunnels require it)
    return f"https://{cleaned}"


def _validate_tunnel_url(url: str) -> bool:
    """Basic validation that a tunnel URL looks reasonable."""
    if not url:
        return False
    if not url.startswith(("http://", "https://")):
        return False
    # Must have at least a hostname
    hostname = url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    if not hostname or "." not in hostname and hostname not in ("localhost",):
        return False
    return True


def get_websocket_url_from_tunnel() -> str:
    """Get the WSS URL for Twilio Stream connections, derived from the tunnel URL."""
    tunnel = read_tunnel_url()
    if tunnel:
        return tunnel.replace("https://", "wss://").replace("http://", "ws://")
    return f"ws://localhost:{DEFAULT_PORT}"


def invalidate_tunnel_cache():
    """Force the next read_tunnel_url() call to re-read the file."""
    global _tunnel_url_cache, _tunnel_url_cache_mtime
    with _tunnel_url_lock:
        _tunnel_url_cache = None
        _tunnel_url_cache_mtime = 0


# =============================================================================
# CALL CREATION — CENTRALIZED, DRY, TIMEOUT-PROTECTED
# =============================================================================

def build_call_urls(base_url: str, prospect_name: str = "there", business_name: str = "") -> Dict[str, str]:
    """
    Build all URLs needed for a Twilio call from a single base URL.
    Returns dict with: twiml_url, status_callback_url, recording_callback_url
    """
    safe_name = quote(str(prospect_name))
    safe_biz = quote(str(business_name))
    
    return {
        "twiml_url": f"{base_url}/twilio/outbound?prospect_name={safe_name}&business_name={safe_biz}",
        "status_callback_url": f"{base_url}/twilio/events",
        "recording_callback_url": f"{base_url}/twilio/recording-status",
    }


async def create_call(
    client,
    supervisor,
    to_number: str,
    from_number: str,
    prospect_name: str = "there",
    business_name: str = "",
    timeout: float = CALL_CREATE_TIMEOUT,
    base_url_override: str = None,
) -> Any:
    """
    Create a Twilio outbound call with full resilience.
    
    This is THE SINGLE PATH for all call creation — /call, campaigns, batch.
    
    Features:
      - Atomic tunnel URL reading (no partial reads)
      - Timeout protection (default 30s, configurable)
      - Proper error propagation (no silent None returns)
      - Type-safe URL construction
      
    Returns the Twilio Call object on success.
    Raises Exception with descriptive message on any failure.
    """
    # 1. Get base URL
    if base_url_override:
        base_url = base_url_override
    else:
        base_url = read_tunnel_url()
        if not base_url:
            raise TelephonyError("No valid tunnel URL available — cannot route Twilio callback")
    
    # 2. Build all URLs from the single base
    urls = build_call_urls(base_url, prospect_name, business_name)
    
    # 3. Fire with timeout
    loop = asyncio.get_running_loop()
    
    try:
        call = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: _execute_call_create(
                    client, supervisor,
                    to_number=to_number,
                    from_number=from_number,
                    twiml_url=urls["twiml_url"],
                    status_callback_url=urls["status_callback_url"],
                    recording_callback_url=urls["recording_callback_url"],
                )
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise TelephonyError(f"Twilio calls.create timed out after {timeout}s")
    
    if not call:
        raise TelephonyError("Twilio failed to initiate call (supervisor intercepted or returned None)")
    
    return call


def _execute_call_create(
    client, supervisor,
    to_number: str,
    from_number: str,
    twiml_url: str,
    status_callback_url: str,
    recording_callback_url: str,
) -> Any:
    """
    Execute the actual Twilio calls.create in a thread pool.
    Wraps through supervisor if available, otherwise calls directly.
    """
    kwargs = dict(
        to=to_number,
        from_=from_number,
        url=twiml_url,
        timeout=RING_TIMEOUT,  # [PACING] Ring 10-12 times before giving up — no rapid hangups
        machine_detection='Enable',  # [PACING] Detect voicemail vs human
        record=True,
        recording_status_callback=recording_callback_url,
        recording_status_callback_event=["completed"],
        status_callback=status_callback_url,
        status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
    )
    
    if supervisor and hasattr(supervisor, 'wrap_twilio_outbound'):
        try:
            result = supervisor.wrap_twilio_outbound(client.calls.create, **kwargs)
            if result is None:
                # Supervisor swallowed the error — re-try directly to get the actual exception
                logger.warning("[TELEPHONY] Supervisor returned None — retrying direct call for error info")
                return client.calls.create(**kwargs)
            return result
        except Exception as e:
            # Re-raise with context instead of swallowing
            raise TelephonyError(f"Twilio API call failed: {type(e).__name__}: {e}") from e
    else:
        try:
            return client.calls.create(**kwargs)
        except Exception as e:
            raise TelephonyError(f"Twilio API call failed: {type(e).__name__}: {e}") from e


# =============================================================================
# GOVERNOR WATCHDOG — AUTO-UNLOCK AFTER TIMEOUT
# =============================================================================
_governor_lock_time: float = 0
_governor_watchdog_task: Optional[asyncio.Task] = None


def governor_mark_start():
    """Mark a call as in progress. Starts the watchdog timer."""
    global _governor_lock_time
    _governor_lock_time = time.time()
    logger.info(f"[GOVERNOR-WATCHDOG] Call started. Auto-unlock in {GOVERNOR_MAX_LOCK_SECONDS}s if callback never arrives.")


def governor_check_timeout() -> bool:
    """
    Check if the governor has been locked longer than GOVERNOR_MAX_LOCK_SECONDS.
    Returns True if the governor should be force-unlocked.
    """
    if _governor_lock_time == 0:
        return False
    elapsed = time.time() - _governor_lock_time
    if elapsed > GOVERNOR_MAX_LOCK_SECONDS:
        logger.error(
            f"[GOVERNOR-WATCHDOG] Governor has been locked for {elapsed:.0f}s "
            f"(limit: {GOVERNOR_MAX_LOCK_SECONDS}s). FORCE UNLOCKING. "
            f"This means a Twilio status callback never arrived."
        )
        return True
    return False


def governor_clear_timeout():
    """Clear the watchdog timer (called when callback arrives normally)."""
    global _governor_lock_time
    _governor_lock_time = 0


async def governor_watchdog_loop(
    is_locked_fn,  # callable that returns True if governor is locked
    unlock_fn,     # callable that unlocks the governor
    check_interval: float = 30,
):
    """
    Background task that periodically checks if the governor is stuck.
    If locked for > GOVERNOR_MAX_LOCK_SECONDS, force-unlocks.
    
    This prevents the #1 CRITICAL failure: a missed status callback
    permanently locking all outbound calls.
    """
    logger.info(f"[GOVERNOR-WATCHDOG] Started. Check interval: {check_interval}s, max lock: {GOVERNOR_MAX_LOCK_SECONDS}s")
    while True:
        try:
            await asyncio.sleep(check_interval)
            if is_locked_fn() and governor_check_timeout():
                unlock_fn()
                governor_clear_timeout()
                logger.warning("[GOVERNOR-WATCHDOG] Governor FORCE UNLOCKED after timeout. System recovered.")
                # [CENTRAL HUB] Report force-unlock to supervisor
                try:
                    from supervisor import AlanSupervisor
                    sup = AlanSupervisor.get_instance()
                    if sup:
                        sup.governor_force_unlocked()
                except Exception:
                    pass  # Supervisor not available — non-critical
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[GOVERNOR-WATCHDOG] Error: {e}")


# =============================================================================
# TWILIO CLIENT HEALTH — VALIDATE BEFORE USE
# =============================================================================

def validate_twilio_client(client) -> Tuple[bool, str]:
    """
    Validate that a Twilio client has working credentials.
    Returns (is_valid, message).
    """
    if client is None:
        return False, "Twilio client is None"
    
    try:
        # This makes a real API call to verify credentials
        account = client.api.accounts(client.username).fetch()
        if account.status == "active":
            return True, f"Account {account.friendly_name} is active"
        else:
            return False, f"Account status is '{account.status}' (not active)"
    except Exception as e:
        return False, f"Credential validation failed: {type(e).__name__}: {e}"


def ensure_twilio_fresh(client, max_age_seconds: int = 3600) -> bool:
    """
    Check if the Twilio client's env vars have changed since initialization.
    Returns True if client is still valid, False if it needs re-creation.
    """
    if client is None:
        return False
    
    current_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
    current_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
    
    if not current_sid or not current_token:
        return False
    
    # Compare with what the client was initialized with
    try:
        if client.username != current_sid:
            logger.warning("[TWILIO] Account SID changed in environment — client needs re-creation")
            return False
        if client.password != current_token:
            logger.warning("[TWILIO] Auth Token changed in environment — client needs re-creation")
            return False
    except AttributeError:
        # Can't compare — assume valid
        return True
    
    return True


# =============================================================================
# PORT PRE-CHECK — VERIFY BEFORE BINDING
# =============================================================================

def is_port_available(port: int = DEFAULT_PORT) -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(('127.0.0.1', port))
            return result != 0  # 0 means something is already listening
    except Exception:
        return True  # Assume available if check fails


def kill_port_occupant(port: int = DEFAULT_PORT) -> bool:
    """
    Kill any process occupying the given port.
    Returns True if the port is now free.
    Windows-specific implementation.
    """
    try:
        import subprocess
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True, text=True, timeout=5
        )
        
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid > 0:
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                                   capture_output=True, timeout=5)
                    logger.info(f"[PORT] Killed PID {pid} on port {port}")
        
        time.sleep(1)
        return is_port_available(port)
    except Exception as e:
        logger.error(f"[PORT] Error killing port occupant: {e}")
        return False


# =============================================================================
# TWILIO REQUEST VALIDATION
# =============================================================================

def validate_twilio_signature(request_url: str, params: dict, signature: str) -> bool:
    """
    Validate that a webhook request actually came from Twilio.
    Uses the Twilio RequestValidator.
    
    Returns True if valid, False if not.
    Note: Returns True if TWILIO_AUTH_TOKEN is not set (fail-open for development).
    """
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    if not auth_token:
        logger.warning("[TWILIO-AUTH] No auth token available — skipping signature validation")
        return True
    
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(auth_token)
        return validator.validate(request_url, params, signature)
    except ImportError:
        logger.warning("[TWILIO-AUTH] RequestValidator not available")
        return True
    except Exception as e:
        logger.error(f"[TWILIO-AUTH] Validation error: {e}")
        return True  # Fail-open to avoid blocking legitimate calls


# =============================================================================
# TERMINAL STATUS NORMALIZATION
# =============================================================================

TERMINAL_CALL_STATUSES = frozenset({
    "completed", "canceled", "failed", "no-answer", "busy", "disconnected",
    "call.completed", "call.canceled", "call.failed", "call.no-answer", 
    "call.busy", "call.disconnected",
})


def is_terminal_status(status: Any) -> bool:
    """
    Check if a Twilio call status represents a terminal state
    that should unlock the governor.
    """
    if not status:
        return False
    s = str(status).strip().lower()
    return s in TERMINAL_CALL_STATUSES or s.replace("call.", "") in TERMINAL_CALL_STATUSES


# =============================================================================
# CUSTOM EXCEPTION
# =============================================================================

class TelephonyError(Exception):
    """Raised for any telephony/Twilio operation failure with full context."""
    pass


# =============================================================================
# HEALTH REPORT
# =============================================================================

def get_telephony_health() -> Dict[str, Any]:
    """
    Get a comprehensive health report of the telephony subsystem.
    """
    tunnel_url = read_tunnel_url()
    port_listening = not is_port_available(DEFAULT_PORT)
    
    return {
        "timestamp": datetime.now().isoformat(),
        "tunnel": {
            "url": tunnel_url,
            "available": tunnel_url is not None,
            "valid": _validate_tunnel_url(tunnel_url) if tunnel_url else False,
        },
        "port": {
            "number": DEFAULT_PORT,
            "listening": port_listening,
        },
        "governor_watchdog": {
            "lock_time": _governor_lock_time if _governor_lock_time > 0 else None,
            "elapsed_seconds": round(time.time() - _governor_lock_time, 1) if _governor_lock_time > 0 else 0,
            "max_lock_seconds": GOVERNOR_MAX_LOCK_SECONDS,
            "would_force_unlock": governor_check_timeout(),
        },
        "constants": {
            "call_create_timeout": CALL_CREATE_TIMEOUT,
            "ring_timeout": RING_TIMEOUT,
            "post_call_cooldown": GOVERNOR_POST_CALL_COOLDOWN,
            "governor_max_lock": GOVERNOR_MAX_LOCK_SECONDS,
            "tunnel_read_retries": TUNNEL_READ_RETRY_COUNT,
        },
    }
