#!/usr/bin/env python3
"""
ALAN AGENT X - CONTROL API (FIXED VERSION)
Voice-enabled conversational AI with Twilio integration
"""

import sys
import codecs

# [FIX] Force UTF-8 for Windows Console to prevent 'charmap' crashes on Emojis
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, Exception):
        # Fallback for older python versions
        import io
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except Exception:
            pass  # Best-effort encoding setup

import asyncio
import base64
import json
import logging
import os
import time
import uuid
import traceback
import contextlib
from contextlib import asynccontextmanager

# ── [HYPERCORN §8] Pin event loop policy BEFORE any async work ───────────
# Prevents uvloop/winloop from hijacking the loop on import.
# Must be set before any asyncio.get_event_loop() call.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Form

# Load environment variables (override=True ensures .env wins over empty shell vars)
load_dotenv(override=True)

from supervisor import AlanSupervisor
from dataclasses import asdict
from autonomous_repair_engine import AutonomousRepairEngine
from system_health_guardian import SystemHealthGuardian, create_guardian
from timing_loader import TIMING  # [TIMING CONFIG] Central timing mixing board

# [ARDE] Autonomous Repair & Diagnostics Engine — global instance
arde = AutonomousRepairEngine()

# [GUARDIAN] System Health Guardian — permanent infrastructure watchdog
guardian = create_guardian()

# [ORGAN RECONNECT] Call Monitor API endpoints
try:
    from alan_call_monitor_integration import register_monitoring_endpoints
    MONITOR_ENDPOINTS_AVAILABLE = True
except ImportError:
    MONITOR_ENDPOINTS_AVAILABLE = False

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from enum import Enum
from twilio.rest import Client

# Tunnel auto-sync module
try:
    from tunnel_sync import full_sync as tunnel_full_sync, background_tunnel_monitor
    TUNNEL_SYNC_AVAILABLE = True
except ImportError:
    TUNNEL_SYNC_AVAILABLE = False

# [REPLICATION] Alan fleet replication engine — concurrent call management
try:
    from alan_replication import get_replication_engine
    REPLICATION_AVAILABLE = True
except ImportError:
    REPLICATION_AVAILABLE = False
    logging.warning("[REPLICATION] alan_replication.py not available — fleet management disabled")

# [CRO] Contact Rate Optimizer — local presence dialing + number reputation
try:
    from contact_rate_optimizer import LocalPresenceManager, NumberReputationTracker
    _cro_lpm = LocalPresenceManager()
    _cro_nrt = NumberReputationTracker()
    CRO_DIALER_AVAILABLE = True
except ImportError:
    CRO_DIALER_AVAILABLE = False
    _cro_lpm = None
    _cro_nrt = None

# Configure enhanced logging with rotation
from logging.handlers import RotatingFileHandler

# Setup logging with rotation (10MB max, 5 backups)
log_formatter = logging.Formatter(
    fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler with rotation
file_handler = RotatingFileHandler(
    'control_api.log', 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

# Initialize Supervisor
supervisor = AlanSupervisor(logger=logger)
supervisor.install_global_excepthook()

# Register Components
supervisor.register_component(
    name="CLOAKING_PROTOCOL",
    depends_on=["CONFIG"],
    affects=["OUTBOUND_ROUTING", "IDENTITY_MASKING", "STABILITY_GOVERNOR"],
)
supervisor.register_component(
    name="TELEPORT_PROTOCOL",
    depends_on=["CONFIG", "NETWORK"],
    affects=["OUTBOUND_ROUTING"],
)
supervisor.register_component(
    name="TWILIO_OUTBOUND",
    depends_on=["NETWORK", "CONFIG"],
    affects=["OUTBOUND_CALL_INITIATION"],
)
supervisor.register_component(
    name="TWILIO_MEDIA_STREAM",
    depends_on=["NETWORK"],
    affects=["MEDIA_STREAM", "CONVERSATION_LOOP"],
)
supervisor.register_component(
    name="TTS",
    depends_on=["NETWORK", "CONFIG"],
    affects=["AUDIO_PIPELINE", "CONVERSATION_LOOP"],
)
supervisor.register_component(
    name="AUDIO_PIPELINE",
    depends_on=["TTS"],
    affects=["MEDIA_STREAM", "CONVERSATION_LOOP"],
)
supervisor.register_component(
    name="CONVERSATION_LOOP",
    depends_on=["AUDIO_PIPELINE", "BUSINESS_LOGIC"],
    affects=["CALL_QUALITY"],
)
supervisor.register_component(
    name="BUSINESS_LOGIC",
    depends_on=["CONFIG"],
    affects=["CONVERSATION_LOOP", "FOLLOW_UP"],
)
supervisor.register_component(
    name="RELAY_SERVER",
    depends_on=["CONFIG", "NETWORK"],
    affects=["CONVERSATION_LOOP", "AUDIO_PIPELINE"],
)

# --- GLOBAL EXCEPTION HOOK ---
def global_excepthook(exctype, value, tb):
    logger.error("[GLOBAL EXCEPTION UNCAUGHT]", exc_info=(exctype, value, tb))
    # Print to console as well just in case
    traceback.print_exception(exctype, value, tb)

sys.excepthook = global_excepthook

# --- CALL GOVERNOR & LOCKING ---
CALL_IN_PROGRESS = False
LAST_CALL_TS = 0
COOLDOWN = TIMING.post_call_cooldown  # [TIMING CONFIG] seconds — post-call reflection window
CALL_LOCK = asyncio.Lock()

# --- CALL LIFECYCLE FSM (Phase 1: Shadow Mode) ---
# Three Laws Doctrine, Law 3: Governors Must Be State Machines, Not Booleans.
# The FSM tracks state alongside the boolean governor. It does NOT control yet.
# Desync detection logs any divergence between boolean and FSM for validation.
try:
    from call_lifecycle_fsm import CallLifecycleFSM, fsm_watchdog_loop
    call_fsm = CallLifecycleFSM()
    CALL_FSM_AVAILABLE = True
    logger.info("[FSM] Call Lifecycle FSM loaded (Phase 1: Shadow Mode)")
except ImportError as _fsm_err:
    call_fsm = None
    CALL_FSM_AVAILABLE = False
    logger.warning(f"[FSM] call_lifecycle_fsm not available: {_fsm_err}")

@contextlib.asynccontextmanager
async def outbound_call_lock():
    """Atomic, self-healing lock for outbound calls using Supervisor Watchdog.
    
    [NEG-PROOF] Single yield — if lock acquisition fails, we raise instead of
    proceeding unprotected. The finally block always releases if held.
    """
    acquired = False
    try:
        # Use supervisor watchdog for lock acquisition
        if supervisor:
            await supervisor.acquire_lock_with_watchdog(CALL_LOCK, "OUTBOUND_CALL_LOCK", timeout=5.0)
            acquired = True
            logger.info("[LOCK] Call Lock Acquired (Supervised)")
        else:
            await CALL_LOCK.acquire()
            acquired = True
            logger.info("[LOCK] Call Lock Acquired (Basic)")
        yield
    except Exception as e:
        if not acquired:
            # Lock acquisition itself failed — do NOT yield, do NOT run call logic
            logger.error(f"[LOCK] Lock acquisition FAILED: {e} — call aborted (not yielding)")
            raise  # Propagate so the caller's `async with` block is skipped
        else:
            # Lock was acquired but something inside the yield block failed.
            # Re-raise so the caller's except handler can deal with it.
            logger.warning(f"[LOCK] Error inside locked section: {e}")
            raise
    finally:
        if acquired and CALL_LOCK.locked():
            CALL_LOCK.release()
            logger.info("[LOCK] Call Lock Released")
        # [NEG-PROOF] Safety net: if CALL_IN_PROGRESS is still True and we're
        # exiting the lock context, something went wrong. The /twilio/events
        # callback should handle the happy path, but if we got here via exception
        # and mark_call_end() wasn't called, we leave it for the watchdog.
        # We do NOT force mark_call_end() here because on a successful fire,
        # the call is still in progress — Twilio is ringing the phone.

def can_fire_call():
    global CALL_IN_PROGRESS, LAST_CALL_TS
    if CALL_IN_PROGRESS:
        logger.warning(f"[GOVERNOR] Blocked! CALL_IN_PROGRESS={CALL_IN_PROGRESS}")
        if supervisor:
            supervisor.governor_blocked("CALL_IN_PROGRESS")
        return False
    time_since_last = time.time() - LAST_CALL_TS
    if time_since_last < COOLDOWN:
        logger.warning(f"[GOVERNOR] Blocked! Cooldown active ({COOLDOWN - time_since_last:.1f}s remaining)")
        if supervisor:
            supervisor.governor_blocked("Cooldown")
        return False
    return True

def mark_call_start(call_id: str = ""):
    global CALL_IN_PROGRESS
    CALL_IN_PROGRESS = True
    logger.info("[GOVERNOR] Call LOCKED")
    # [FSM SHADOW] Track state transition in FSM (telemetry only — does not control)
    if CALL_FSM_AVAILABLE and call_fsm:
        call_fsm.start_call(call_id)
    if supervisor:
        supervisor.update_governor_state(
            call_in_progress=True,
            cooldown_remaining=0,
            last_call_ts=LAST_CALL_TS,
            lock_duration=0,
            watchdog_active=True,
        )

def mark_call_end():
    global CALL_IN_PROGRESS, LAST_CALL_TS
    CALL_IN_PROGRESS = False
    LAST_CALL_TS = time.time()
    logger.info("[GOVERNOR] Call UNLOCKED")
    # [FSM SHADOW] Force-end in FSM if it's still active (it should have transitioned via events)
    if CALL_FSM_AVAILABLE and call_fsm and call_fsm.is_active():
        call_fsm.force_end("mark_call_end (boolean governor)")
    # [FSM DESYNC] Check for divergence between boolean and FSM
    if CALL_FSM_AVAILABLE and call_fsm:
        if CALL_IN_PROGRESS != call_fsm.is_active():
            logger.error(
                f"[GOVERNOR-DESYNC] Boolean={CALL_IN_PROGRESS}, "
                f"FSM={call_fsm.state.name}. THIS IS A STRUCTURAL BUG."
            )
    if supervisor:
        supervisor.update_governor_state(
            call_in_progress=False,
            cooldown_remaining=float(COOLDOWN),
            last_call_ts=LAST_CALL_TS,
            lock_duration=0,
            watchdog_active=True,
        )

# --- LAZY DIALER ---
TWILIO_CLIENT = None

def ensure_dialer_ready():
    global TWILIO_CLIENT
    if TWILIO_CLIENT:
        return TWILIO_CLIENT
        
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    if not all([account_sid, auth_token]):
        logger.error("[DIALER] Missing Twilio Credentials in Env")
        raise HTTPException(status_code=500, detail="Twilio Credentials Unconfigured")
        
    TWILIO_CLIENT = Client(account_sid, auth_token)
    logger.info("[DIALER] Twilio Outbound Client Initialized (Lazy)")
    return TWILIO_CLIENT

# Create FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events"""
    try:
        logger.info("[LIFESPAN] Starting application lifespan...")
        
        # [AUTO] Sync tunnel URL to Twilio webhooks on every boot
        if TUNNEL_SYNC_AVAILABLE:
            logger.info("[LIFESPAN] Running automatic tunnel -> Twilio webhook sync...")
            try:
                sync_result = tunnel_full_sync(force=True)
                logger.info(f"[LIFESPAN] Tunnel sync result: {sync_result}")
                # Start background monitor for tunnel URL changes
                asyncio.create_task(background_tunnel_monitor(check_interval=30))
                logger.info("[LIFESPAN] Background tunnel monitor started (30s interval)")
            except Exception as e:
                logger.error(f"[LIFESPAN] Tunnel sync failed: {e}")
        else:
            logger.warning("[LIFESPAN] tunnel_sync module not available - manual webhook sync required")
        
        # [RESILIENCE] Start Governor Watchdog — auto-unlocks if Twilio callback never arrives
        try:
            from telephony_resilience import governor_watchdog_loop
            asyncio.create_task(governor_watchdog_loop(
                is_locked_fn=lambda: CALL_IN_PROGRESS,
                unlock_fn=mark_call_end,
                check_interval=30,
            ))
            logger.info("[LIFESPAN] Governor Watchdog started (30s check, 300s max lock)")
        except ImportError:
            logger.warning("[LIFESPAN] telephony_resilience not available — Governor Watchdog DISABLED")

        # [FSM] Start Call Lifecycle FSM Watchdog (Phase 1: Shadow Mode)
        if CALL_FSM_AVAILABLE and call_fsm:
            def _get_supervisor():
                try:
                    return AlanSupervisor.get_instance()
                except Exception:
                    return None
            asyncio.create_task(fsm_watchdog_loop(
                fsm=call_fsm,
                check_interval=10,
                supervisor_getter=_get_supervisor,
            ))
            logger.info("[LIFESPAN] FSM Watchdog started (10s check, shadow mode)")

        # [AUTO] Start self-health monitoring (checks tunnel, creds every 5 min)
        asyncio.create_task(_self_health_monitor())
        logger.info("[LIFESPAN] Self-health monitor started (300s interval)")
        
        # [ARDE] Start Autonomous Repair & Diagnostics Engine
        arde.attach_relay(relay_server)
        arde.attach_supervisor(supervisor)
        arde.start()
        logger.info("[LIFESPAN] ARDE started (60s diagnostic cycle, auto-repair enabled)")
        
        # [GUARDIAN] Start System Health Guardian — infrastructure-level watchdog
        guardian.attach_supervisor(supervisor)
        guardian.attach_relay(relay_server)
        guardian.start()
        logger.info(f"[LIFESPAN] System Health Guardian started ({TIMING.health_check_interval}s cycle, deep every {TIMING.deep_check_interval}s)")

        # [AUTONOMY] Start follow-up execution worker (checks every 5 min for due callbacks)
        asyncio.create_task(_follow_up_execution_worker())
        logger.info("[LIFESPAN] Follow-up execution worker started (300s interval)")
        
        # [AUTONOMY] Start education learning cycle (runs once daily)
        asyncio.create_task(_education_learning_cycle())
        logger.info("[LIFESPAN] Education learning cycle started (daily)")
        
        # [AUTO-DIALER] DISABLED — campaigns now require explicit start via POST /campaign/start
        # Previous behavior auto-resumed campaigns 30s after boot, which caused race conditions
        # with mode switching (instructor mode set after auto-dialer already fired).
        # Tim can start campaigns explicitly when ready.
        logger.info("[AUTO-DIALER] Auto-resume DISABLED — use POST /campaign/start to begin")
        
        logger.info("[LIFESPAN] Minimal startup complete.")
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"[LIFESPAN] Exception: {e}")
        logger.error(traceback.format_exc())
        raise
    finally:
        logger.info("[LIFESPAN] Application shutting down...")

app = FastAPI(
    title="Agent X Control API",
    description="Voice-enabled conversational AI with Twilio integration",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# [ORGAN RECONNECT] Register Call Monitor API endpoints
if MONITOR_ENDPOINTS_AVAILABLE:
    register_monitoring_endpoints(app)
    logger.info("[ORGAN] Call Monitor API endpoints registered")

# [VOICEMAIL FALLBACK] Register voicemail routes
try:
    from voicemail_fallback import register_voicemail_routes
    register_voicemail_routes(app)
    VOICEMAIL_FALLBACK_AVAILABLE = True
    logger.info("[VOICEMAIL] Fallback routes registered — Signature Card Service Direct Merchant Center")
except ImportError:
    VOICEMAIL_FALLBACK_AVAILABLE = False
    logger.warning("[VOICEMAIL] voicemail_fallback.py not found — fallback routes not available")
except Exception as _vf_err:
    VOICEMAIL_FALLBACK_AVAILABLE = False
    logger.warning(f"[VOICEMAIL] Fallback registration failed: {_vf_err}")

# --- AQI VOICE MODULE INTEGRATION (Ascendrym Compliant) ---
voice_functions_available = False
disable_voice_module_for_testing = False

async def audio_pipeline_ready():
    """Default fallback if voice module is not loaded"""
    return True

if not disable_voice_module_for_testing:
    try:
        from aqi_voice_module import router as voice_router, register_stt_callback, send_text_to_voice, register_connect_callback, voice_sessions, cancel_speech, VoiceSession
        app.include_router(voice_router)
        voice_functions_available = True
        logger.info("AQI Voice Module router enabled (ASCENDRYM COMPLIANT)")

        # Connect STT to Brain
        def process_voice_transcript(text: str, session_id: str):
            logger.info(f"[BRAIN] Received: {text}")
            # Integration point for Agent Alan Logic would go here
            
        register_stt_callback(process_voice_transcript)
        
    except ImportError as e:
        logger.error(f"[STARTUP] Failed to import AQI Voice Module: {e}")

# Add CORS Middleware to allow WebSocket connections from Twilio (and everywhere for now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable to hold the agent instance
agent = None

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the Agent X Command Center dashboard"""
    dashboard_path = Path(__file__).parent / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Agent X Online</h1><p>Dashboard not found.</p>")

@app.get("/health")
async def health_check():
    """
    Returns the UNIFIED health dashboard — the single source of truth.
    Tim's directive: 'The supervisor should be the main one, and if it can
    be upgraded to include everything so you just need to watch the
    supervision, that may help?'
    """
    if supervisor:
        # [CENTRAL HUB] Compute live governor state before returning
        # [NEG-PROOF] Use explicit > 0 check, NOT truthiness.
        # LAST_CALL_TS=0 is falsy but valid (means "no calls yet").
        # Old code: `if LAST_CALL_TS else 0` → time_since_last=0 → permanent cooldown.
        if LAST_CALL_TS > 0:
            time_since_last = time.time() - LAST_CALL_TS
        else:
            time_since_last = 99999  # No calls yet → no cooldown (safe finite value for JSON)
        supervisor.update_governor_state(
            call_in_progress=CALL_IN_PROGRESS,
            cooldown_remaining=max(0, COOLDOWN - time_since_last) if not CALL_IN_PROGRESS else 0,
            last_call_ts=LAST_CALL_TS,
            lock_duration=time_since_last if CALL_IN_PROGRESS else 0,
            watchdog_active=True,
        )
        base = supervisor.get_unified_dashboard(
            arde_snapshot=arde.snapshot() if arde else None
        )
        # [FSM SHADOW] Include FSM state in health dashboard for comparison
        if CALL_FSM_AVAILABLE and call_fsm:
            base["governor_fsm"] = call_fsm.get_state_dict()
            # Desync detection — visible in dashboard
            if CALL_IN_PROGRESS != call_fsm.is_active():
                base["governor_desync"] = {
                    "boolean": CALL_IN_PROGRESS,
                    "fsm_state": call_fsm.state.name,
                    "fsm_active": call_fsm.is_active(),
                    "severity": "CRITICAL",
                }
    else:
        base = {"status": "ok", "supervisor": "disabled"}
    # [COUPLED BOOT] Always report both subsystem statuses
    if relay_server and hasattr(relay_server, 'subsystem_status'):
        base["subsystems"] = relay_server.subsystem_status()
    else:
        base["subsystems"] = {
            "alan": "OFFLINE",
            "agent_x": "OFFLINE",
            "coupled": False,
            "status": "RELAY_DOWN",
        }
    return base

@app.get("/diagnostics")
async def diagnostics():
    """Full diagnostics: health + incidents + component map + architecture info."""
    diag = {
        "timestamp": supervisor._now() if supervisor else None,
        "architecture": {
            "tts": "OpenAI TTS (model=tts-1, voice=echo)",
            "stt": "Groq Whisper (whisper-large-v3-turbo) + OpenAI fallback",
            "llm": "GPT-4o-mini (streaming, max_tokens=100)",
            "telephony": "Twilio",
            "tunnel": "Cloudflare",
            "server": "control_api_fixed.py (Hypercorn, port 8777)",
        },
    }
    if supervisor:
        diag["health"] = supervisor.health_state
        diag["components"] = {k: {"depends_on": v.depends_on, "affects": v.affects} for k, v in supervisor.components.items()}
        diag["incidents"] = [{"id": i.id, "timestamp": i.timestamp, "component": i.component, "severity": i.severity, "issue": i.issue} for i in supervisor.latest_incidents(50)]
        diag["incident_count"] = len(supervisor.incidents)
    return diag

# ---- TUNNEL SYNC API ----
@app.post("/tunnel/sync")
async def tunnel_sync_endpoint():
    """Force-sync tunnel URL to Twilio webhooks"""
    if not TUNNEL_SYNC_AVAILABLE:
        raise HTTPException(status_code=503, detail="tunnel_sync module not available")
    try:
        result = tunnel_full_sync(force=True)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ================================================================
# [LIVE CALL MONITOR] Tim's Directive: "There must always be an 
#   active way to confirm that Alan is on the Phone with an Actual
#   Human... I want to know what is actually happening, LIVE."
# ================================================================
@app.get("/call/live")
async def call_live():
    """Real-time live call state with human voice frequency confirmation.
    
    Returns exactly what's happening on any active call RIGHT NOW:
    - Is there a human on the line? (voice frequency analysis)
    - What are they saying? (last speech from both sides)
    - How long has the call been going?
    - Is cost sentinel active?
    - Verdict: LIVE CONVERSATION / IVR / AIR CALL / etc.
    """
    try:
        from live_call_monitor import LiveCallMonitor
        monitor = LiveCallMonitor.get_instance()
        live_state = monitor.get_live_state()
        live_state["server_time"] = datetime.now().isoformat()
        live_state["summary"] = monitor.get_summary()
        return live_state
    except ImportError:
        return {"error": "Live Call Monitor not available", "active_calls": 0}
    except Exception as e:
        return {"error": str(e), "active_calls": 0}

@app.get("/tunnel/status")
async def tunnel_status():
    """Get current tunnel URL and sync status"""
    from tunnel_sync import get_current_tunnel_url, _last_synced_url
    return {
        "current_url": get_current_tunnel_url(),
        "last_synced": _last_synced_url,
        "sync_available": TUNNEL_SYNC_AVAILABLE,
        "env_url": os.environ.get("PUBLIC_TUNNEL_URL", "NOT SET"),
    }

@app.get("/incidents")
async def get_incidents(limit: int = 50):
    """Returns a list of recent structured incidents."""
    if supervisor:
        return [asdict(i) for i in supervisor.latest_incidents(limit)]
    else:
        return []

@app.get("/test/supervisor")
async def test_supervisor(type: str):
    """Test Harness for Supervisor failure modes."""
    if not supervisor:
        return {"status": "supervisor disabled"}
    
    # 1. Protocol failure
    if type == "protocol":
        def bad_protocol():
            raise RuntimeError("Simulated protocol startup failure")
        supervisor.wrap_protocol_start("CLOAKING_PROTOCOL", bad_protocol)
        return {"status": "triggered", "type": type}

    # 2. Twilio outbound failure
    if type == "twilio":
        def bad_twilio(**kwargs):
            raise Exception("Simulated Twilio outbound failure")
        supervisor.wrap_twilio_outbound(bad_twilio, to="123", from_="456", url="http://x")
        return {"status": "triggered", "type": type}

    # 3. Media stream disconnect
    if type == "media":
        supervisor.twilio_media_disconnect("Simulated disconnect")
        return {"status": "triggered", "type": type}

    # 4. TTS failure (OpenAI)
    if type == "tts":
        def bad_tts(text, **kwargs):
            raise Exception("Simulated TTS failure")
        supervisor.wrap_tts(bad_tts, text="Hello")
        return {"status": "triggered", "type": type}

    # 5. TTS latency spike
    if type == "latency":
        supervisor.tts_latency(5000)  # 5 seconds
        return {"status": "triggered", "type": type}

    # 6. Lock deadlock
    if type == "lock":
        import asyncio
        lock = asyncio.Lock()
        await lock.acquire()  # create deadlock
        # We don't await this in the test harness or it will hang the test route itself if not careful
        # but the supervisor.acquire_lock_with_watchdog IS async, so we should run it as a task maybe?
        # or just await it with a shorter timeout in the watchdog logic.
        asyncio.create_task(supervisor.acquire_lock_with_watchdog(lock, "OUTBOUND_CALL_LOCK"))
        return {"status": "triggered", "type": type}

    # 7. Governor misfire
    if type == "governor":
        supervisor.governor_triggered("CALL_RATE_GOVERNOR", "Simulated overload")
        return {"status": "triggered", "type": type}

    # 8. Audio pipeline failure
    if type == "audio":
        supervisor.audio_pipeline_status(False, "Simulated audio encoder failure")
        return {"status": "triggered", "type": type}

    # 9. Conversation loop failure
    if type == "conversation":
        supervisor.conversation_issue(
            issue="Simulated stuck loop",
            reason="Loop iteration exceeded threshold",
            fix="Resetting conversation state"
        )
        return {"status": "triggered", "type": type}

    # 10. Business logic routing failure
    if type == "business":
        supervisor.business_logic_issue(
            issue="Simulated routing failure",
            reason="Missing handler for 'TEST_SCENARIO'",
            fix="Fallback to default handler"
        )
        return {"status": "triggered", "type": type}

    # 11. Config integrity failure
    if type == "config":
        supervisor.config_issue(
            name="voice_profile",
            issue="Missing config key",
            reason="Simulated missing key",
            fix="Using default voice"
        )
        return {"status": "triggered", "type": type}

    # 12. Network degradation
    if type == "network":
        supervisor.network_issue(
            issue="Simulated network timeout",
            reason="DNS resolution failed",
            fix="Retrying with exponential backoff"
        )
        return {"status": "triggered", "type": type}

    # 13. Memory pressure
    if type == "memory":
        supervisor.memory_pressure(False, "Simulated memory threshold exceeded")
        return {"status": "triggered", "type": type}

    # 14. Disk I/O failure
    if type == "disk":
        supervisor.disk_health(False, "Simulated disk write failure")
        return {"status": "triggered", "type": type}

    # 15. Global uncaught exception
    if type == "global":
        raise RuntimeError("Simulated uncaught global exception")

    return {"status": "unknown test type", "type": type}

# ── ARDE ENDPOINTS ──
@app.get("/diagnostics/arde")
async def arde_status():
    """Returns the Autonomous Repair & Diagnostics Engine status and history."""
    return arde.snapshot()

@app.get("/diagnostics/deep")
async def arde_deep_diagnostic():
    """Runs a comprehensive deep diagnostic across all subsystems."""
    return arde.deep_diagnostic()

@app.post("/repair/force")
async def force_repair():
    """Force an immediate diagnostic + repair cycle (on-demand)."""
    diag = arde.force_diagnostic()
    repairs_attempted = []
    for sub_id, check in diag.items():
        if isinstance(check, dict) and check.get("status") in ("degraded", "critical"):
            await arde._attempt_repair(sub_id, check)
            repairs_attempted.append(sub_id)
    return {
        "diagnostic": diag,
        "repairs_attempted": repairs_attempted,
        "post_repair_state": arde.snapshot(),
    }

# [GUARDIAN] Infrastructure health guardian endpoint
@app.get("/guardian/status")
async def guardian_status():
    """Full System Health Guardian status — infrastructure-level checks."""
    return guardian.snapshot()

# [FIX] Moved duplicate /diagnostics content into /readiness endpoint
# The primary /diagnostics route (above) handles full architecture diagnostics.
@app.get("/readiness")
async def readiness_check():
    """Industrial grade operational readiness check — call-level health."""
    greeting_cache_count = len(relay_server.greeting_cache) if relay_server and hasattr(relay_server, 'greeting_cache') else 0
    return {
        "status": "online",
        "call_ready": await audio_pipeline_ready(),
        "lock_locked": CALL_LOCK.locked(),
        "dialer_active": TWILIO_CLIENT is not None,
        "cooldown_remaining": max(0, COOLDOWN - (time.time() - LAST_CALL_TS)),
        "relay_server_ready": relay_server is not None,
        "subsystems": relay_server.subsystem_status() if relay_server and hasattr(relay_server, 'subsystem_status') else {"alan": "OFFLINE", "agent_x": "OFFLINE", "coupled": False, "status": "RELAY_DOWN"},
        "relay_greeting_cache": greeting_cache_count,
        "autonomy": {
            "follow_up_worker": True,
            "education_cycle": True,
            "post_call_outcome": True,
            "agent_coaching": True,
            "tunnel_monitor": True,
            "health_monitor": True,
        },
        "env_check": {
            "TWILIO_SID": bool(os.environ.get('TWILIO_ACCOUNT_SID')),
            "TWILIO_TOKEN": bool(os.environ.get('TWILIO_AUTH_TOKEN')),
            "PHONE": bool(os.environ.get('TWILIO_PHONE_NUMBER')),
            "NORTH_API_KEY": bool(os.environ.get('NORTH_API_KEY')),
            "OPENAI_API_KEY": bool(os.environ.get('OPENAI_API_KEY')),
            "GROQ_API_KEY": bool(os.environ.get('GROQ_API_KEY')),
            "SMTP_CONFIGURED": bool(os.environ.get('SMTP_USERNAME') and os.environ.get('SMTP_PASSWORD')),
        }
    }

@app.get("/readiness/vip")
async def vip_readiness_gate():
    """Constitutional Readiness Gate — 6 checks that must ALL pass before VIP traffic is allowed.
    In VIP Launch Mode, additional hardened checks are enforced."""
    import datetime as _dt

    is_vip = arde.vip_mode if arde else False
    checks = []
    all_pass = True

    # ── VIP MODE PRE-CHECK: Traffic Halt ──
    if arde and arde.traffic_halted:
        return {
            "allowed": False,
            "posture": "HALTED",
            "passed": "0/?",
            "vip_mode": is_vip,
            "traffic_halted": True,
            "halt_reason": arde.traffic_halt_reason,
            "timestamp": _dt.datetime.now().isoformat(),
            "checks": [{"name": "Traffic Halt Override", "pass": False, "reason": arde.traffic_halt_reason}],
            "action": "POST /vip/clear-halt to resume after fixing the issue",
        }

    # ── CHECK 1: Coupled Boot Integrity ──
    try:
        sub = relay_server.subsystem_status() if relay_server and hasattr(relay_server, 'subsystem_status') else {}
        alan_ok = sub.get("alan") == "ONLINE"
        agentx_ok = sub.get("agent_x") == "ONLINE"
        coupled_ok = sub.get("coupled", False) is True
        # Verify ARDE not mid-repair on either
        arde_snap = arde.snapshot() if arde else {}
        sub_health = arde_snap.get("subsystem_health", {})
        arde_repairing_alan = sub_health.get("alan", {}).get("status") == "repairing" if isinstance(sub_health.get("alan"), dict) else False
        arde_repairing_agentx = sub_health.get("agent_x", {}).get("status") == "repairing" if isinstance(sub_health.get("agent_x"), dict) else False
        boot_pass = alan_ok and agentx_ok and coupled_ok and not arde_repairing_alan and not arde_repairing_agentx
        reason = "Alan+AgentX ONLINE, coupled=true, no active ARDE repairs" if boot_pass else f"alan={sub.get('alan')} agentx={sub.get('agent_x')} coupled={sub.get('coupled')} arde_repairing={'yes' if arde_repairing_alan or arde_repairing_agentx else 'no'}"
    except Exception as e:
        boot_pass = False
        reason = f"Error checking boot: {e}"
    checks.append({"name": "Coupled Boot Integrity", "pass": boot_pass, "reason": reason})
    if not boot_pass:
        all_pass = False

    # ── CHECK 2: ARDE Stability Window (10 min) ──
    try:
        snap = arde.snapshot() if arde else {}
        cycle_count = snap.get("cycle_count", 0)
        enough_cycles = cycle_count >= 5
        repair_history = snap.get("repair_history", [])
        now_ts = time.time()
        ten_min_ago = now_ts - 600
        recent_repairs = [r for r in repair_history if r.get("timestamp", 0) > ten_min_ago]
        has_critical = any(r.get("severity") == "CRITICAL" for r in recent_repairs)
        # Thrashing: any subsystem repaired more than once in 10 min
        from collections import Counter as _Ctr
        repair_targets = [r.get("subsystem", "unknown") for r in recent_repairs]
        thrashing = any(c > 1 for c in _Ctr(repair_targets).values())
        # Cooldown check
        sub_h = snap.get("subsystem_health", {})
        in_cooldown = False
        for _sk, _sv in sub_h.items():
            if isinstance(_sv, dict) and _sv.get("cooldown_until", 0) > now_ts:
                in_cooldown = True
                break
        arde_pass = enough_cycles and not has_critical and not thrashing and not in_cooldown
        reason = f"cycles={cycle_count}, recent_repairs={len(recent_repairs)}, critical={has_critical}, thrashing={thrashing}, cooldown={in_cooldown}"
    except Exception as e:
        arde_pass = False
        reason = f"Error checking ARDE: {e}"
    checks.append({"name": "ARDE Stability Window (10m)", "pass": arde_pass, "reason": reason})
    if not arde_pass:
        all_pass = False

    # ── CHECK 3: Tunnel Integrity + Twilio Sync ──
    try:
        tunnel_path = Path(__file__).parent / "active_tunnel_url.txt"
        tunnel_exists = tunnel_path.exists()
        tunnel_url = tunnel_path.read_text(encoding="utf-8").strip() if tunnel_exists else ""
        url_valid = tunnel_url.startswith("https://") and len(tunnel_url) > 15
        # Quick reachability test (non-blocking, 3s timeout)
        reachable = False
        if url_valid:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(tunnel_url + "/health", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        reachable = resp.status == 200
            except Exception:
                reachable = False
        tunnel_pass = tunnel_exists and url_valid and reachable
        reason = f"file={'yes' if tunnel_exists else 'no'}, url_valid={'yes' if url_valid else 'no'}, reachable={'yes' if reachable else 'no'}"
        if url_valid:
            reason += f", url={tunnel_url[:40]}..."
    except Exception as e:
        tunnel_pass = False
        reason = f"Error checking tunnel: {e}"
    checks.append({"name": "Tunnel Integrity + Twilio Sync", "pass": tunnel_pass, "reason": reason})
    if not tunnel_pass:
        all_pass = False

    # ── CHECK 4: TTS + Greeting Cache ──
    try:
        tts_ok = relay_server is not None and hasattr(relay_server, 'tts_client') and relay_server.tts_client is not None
        cache_count = len(relay_server.greeting_cache) if relay_server and hasattr(relay_server, 'greeting_cache') else 0
        cache_min = 5 if is_vip else 3  # VIP requires ≥5
        cache_ok = cache_count >= cache_min
        # Check for recent TTS repairs in ARDE history
        snap = arde.snapshot() if arde else {}
        repair_hist = snap.get("repair_history", [])
        five_min_ago = time.time() - 300
        recent_tts_repair = any(
            r.get("subsystem") == "tts" and r.get("timestamp", 0) > five_min_ago
            for r in repair_hist
        )
        tts_pass = tts_ok and cache_ok and not recent_tts_repair
        reason = f"tts_online={'yes' if tts_ok else 'no'}, greetings={cache_count} (min={cache_min}), recent_tts_repair={'yes' if recent_tts_repair else 'no'}"
    except Exception as e:
        tts_pass = False
        reason = f"Error checking TTS: {e}"
    checks.append({"name": "TTS + Greeting Cache", "pass": tts_pass, "reason": reason})
    if not tts_pass:
        all_pass = False

    # ── CHECK 5: Real Call Dry Run (Manual Gate) ──
    # This is advisory — cannot be auto-verified. Operator must confirm.
    dry_run_path = Path(__file__).parent / ".vip_dry_run_confirmed"
    dry_run_pass = dry_run_path.exists()
    reason = "Confirmed" if dry_run_pass else "NOT CONFIRMED — touch .vip_dry_run_confirmed after successful test call"
    checks.append({"name": "Real Call Dry Run", "pass": dry_run_pass, "reason": reason})
    if not dry_run_pass:
        all_pass = False

    # ── CHECK 6: Log + Incident Cleanliness ──
    try:
        snap = arde.snapshot() if arde else {}
        repair_hist = snap.get("repair_history", [])
        thirty_min_ago = time.time() - 1800
        recent_critical = any(
            r.get("severity") == "CRITICAL" and r.get("timestamp", 0) > thirty_min_ago
            for r in repair_hist
        )
        log_pass = not recent_critical
        reason = f"critical_last_30m={'yes — BLOCK' if recent_critical else 'clean'}"
    except Exception as e:
        log_pass = False
        reason = f"Error checking logs: {e}"
    checks.append({"name": "Log + Incident Cleanliness", "pass": log_pass, "reason": reason})
    if not log_pass:
        all_pass = False

    # ── VIP-ONLY HARDENED CHECKS ──
    if is_vip:
        # VIP CHECK A: No ARDE repairs in last 5 minutes
        try:
            snap = arde.snapshot() if arde else {}
            repair_hist = snap.get("repair_history", [])
            five_min_ago = time.time() - 300
            recent_any_repair = [r for r in repair_hist if isinstance(r.get("timestamp"), (int, float)) and r["timestamp"] > five_min_ago]
            # Also check string timestamps
            if not recent_any_repair:
                recent_any_repair = []  # All clear
            vip_stability = len(recent_any_repair) == 0
            reason = f"repairs_last_5m={len(recent_any_repair)}"
        except Exception as e:
            vip_stability = False
            reason = f"Error: {e}"
        checks.append({"name": "[VIP] No Recent Repairs (5m)", "pass": vip_stability, "reason": reason})
        if not vip_stability:
            all_pass = False

        # VIP CHECK B: No subsystem in WARN state
        try:
            snap = arde.snapshot() if arde else {}
            sub_h = snap.get("subsystem_health", {})
            warn_subs = [k for k, v in sub_h.items() if v in ("warning", "degraded")]
            no_warnings = len(warn_subs) == 0
            reason = f"warn/degraded={warn_subs}" if warn_subs else "all subsystems clean"
        except Exception as e:
            no_warnings = False
            reason = f"Error: {e}"
        checks.append({"name": "[VIP] No Subsystem Warnings", "pass": no_warnings, "reason": reason})
        if not no_warnings:
            all_pass = False

        # VIP CHECK C: Deep probe integrity for Alan + Agent X
        try:
            deep = arde.deep_diagnostic() if arde else {}
            alan_deep = deep.get("alan_deep", {})
            x_deep = deep.get("agent_x_deep", {})
            alan_integrity = (
                alan_deep.get("status") == "operational"
                and alan_deep.get("has_system_prompt", False)
                and alan_deep.get("has_build_llm_prompt", False)
            )
            x_integrity = (
                x_deep.get("status") == "operational"
                and x_deep.get("has_process_turn", False)
                and x_deep.get("has_pve", False)
                and x_deep.get("has_priority_dispatch", False)
            )
            deep_pass = alan_integrity and x_integrity
            reason = f"alan_integrity={'pass' if alan_integrity else 'FAIL'}, agentx_integrity={'pass' if x_integrity else 'FAIL'}"
        except Exception as e:
            deep_pass = False
            reason = f"Error: {e}"
        checks.append({"name": "[VIP] Deep Probe Integrity", "pass": deep_pass, "reason": reason})
        if not deep_pass:
            all_pass = False

    passed_count = sum(1 for c in checks if c["pass"])
    return {
        "allowed": all_pass,
        "posture": "GREEN" if all_pass else "RED",
        "passed": f"{passed_count}/{len(checks)}",
        "vip_mode": is_vip,
        "traffic_halted": arde.traffic_halted if arde else False,
        "timestamp": _dt.datetime.now().isoformat(),
        "checks": checks,
    }

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_vip_dashboard():
    """Serve the VIP Telemetry Dashboard."""
    vip_path = Path(__file__).parent / "vip_dashboard.html"
    if vip_path.exists():
        return HTMLResponse(content=vip_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>VIP Dashboard not found</h1>", status_code=404)

# ──────────────────────────────────────────────────────────────────
#  VIP LAUNCH MODE ENDPOINTS
# ──────────────────────────────────────────────────────────────────

@app.post("/vip/activate")
async def activate_vip_mode():
    """Activate VIP Launch Mode — tightens ARDE thresholds, halts traffic on CRITICAL."""
    result = arde.activate_vip_mode()
    return {"vip_launch_mode": result, "arde_status": arde.vip_status()}

@app.post("/vip/deactivate")
async def deactivate_vip_mode():
    """Deactivate VIP Launch Mode — return to normal operating thresholds."""
    result = arde.deactivate_vip_mode()
    return {"vip_launch_mode": result, "arde_status": arde.vip_status()}

@app.get("/vip/status")
async def vip_mode_status():
    """Current VIP mode status, traffic halt state, and effective thresholds."""
    return arde.vip_status()

@app.post("/vip/clear-halt")
async def clear_traffic_halt():
    """Manually clear the traffic halt flag after resolving a CRITICAL issue."""
    result = arde.clear_traffic_halt()
    return result

@app.get("/deep-layer")
async def deep_layer_status():
    """Diagnostic endpoint for the QPC + Fluidic + Continuum deep layer state."""
    if not relay_server:
        return {"status": "offline", "reason": "relay_server not initialized"}
    
    active = relay_server.active_conversations if hasattr(relay_server, 'active_conversations') else {}
    results = {}
    
    for cid, ctx in active.items():
        dl = ctx.get('deep_layer')
        if dl:
            try:
                snap = dl.get_snapshot()
                # Convert numpy arrays to lists for JSON serialization
                if 'continuum_fields' in snap:
                    for k, v in snap['continuum_fields'].items():
                        snap['continuum_fields'][k] = v.tolist() if hasattr(v, 'tolist') else v
                results[cid] = snap
            except Exception as e:
                results[cid] = {"error": str(e)}
        else:
            results[cid] = {"status": "not_initialized"}
    
    try:
        from aqi_deep_layer import CONVERSATION_MODES
        wired = True
    except ImportError:
        wired = False
    
    return {
        "deep_layer_wired": wired,
        "active_sessions": len(results),
        "sessions": results,
        "available_modes": list(CONVERSATION_MODES.keys()) if wired else [],
    }

# =============================================================================
# SYSTEM MODE MANAGEMENT — Campaign vs Instructor vs Idle
# =============================================================================
# Global mode state. Controls how Alan operates:
#   - "campaign"   : Sales mode — calling leads, applying 2-strike, rate governor
#   - "instructor" : Training mode — calling Tim's colleagues for practice
#   - "idle"       : Standing by — no active calls, no campaigns
# =============================================================================
SYSTEM_MODE = "idle"  # Default on startup

@app.get("/mode")
async def get_mode():
    """Get current system mode."""
    global SYSTEM_MODE
    return {
        "mode": SYSTEM_MODE,
        "campaign_active": CAMPAIGN_ACTIVE,
        "available_modes": ["campaign", "instructor", "idle"],
    }

@app.post("/mode/set")
async def set_mode(request: Request):
    """Switch system mode. Stops campaign if switching away from campaign mode."""
    global SYSTEM_MODE, CAMPAIGN_ACTIVE, CAMPAIGN_TASK
    data = await request.json()
    new_mode = data.get("mode", "").lower().strip()
    
    if new_mode not in ("campaign", "instructor", "idle"):
        return JSONResponse(status_code=400, content={
            "status": "error", 
            "message": f"Invalid mode '{new_mode}'. Valid: campaign, instructor, idle"
        })
    
    old_mode = SYSTEM_MODE
    
    # If leaving campaign mode, stop any active campaign
    if old_mode == "campaign" and new_mode != "campaign":
        if CAMPAIGN_ACTIVE:
            CAMPAIGN_ACTIVE = False
            if CAMPAIGN_TASK:
                CAMPAIGN_TASK.cancel()
                CAMPAIGN_TASK = None
            logger.info(f"[MODE] Campaign stopped — switching to {new_mode}")
    
    SYSTEM_MODE = new_mode
    logger.info(f"[MODE] System mode changed: {old_mode} → {new_mode}")
    
    return {
        "status": "ok",
        "previous_mode": old_mode,
        "current_mode": new_mode,
        "message": f"Alan is now in {new_mode.upper()} mode",
    }

# =============================================================================
# INSTRUCTOR MODE — Governed Learning API
# =============================================================================
# Tim's approval workflow for instructor training sessions.
# Alan cannot integrate any learnings without Tim's sign-off.
# =============================================================================

@app.get("/instructor/review")
async def instructor_review():
    """Review pending training signals from instructor sessions."""
    try:
        from instructor_mode import ApprovalWorkflow
        review = ApprovalWorkflow.review_pending()
        return {
            "status": "ok",
            "pending_signals": review.get("pending_signals", 0),
            "total_sessions": review.get("total_sessions", 0),
            "signals": review.get("signals", []),
            "sessions_summary": review.get("sessions_summary", []),
        }
    except ImportError:
        return {"status": "error", "reason": "instructor_mode module not available"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

@app.post("/instructor/approve")
async def instructor_approve(request: Request):
    """Approve specific training signals for integration into Alan's behavior."""
    try:
        from instructor_mode import ApprovalWorkflow, governance_check
        data = await request.json()
        signal_ids = data.get("signal_ids", [])
        notes = data.get("notes", "")
        
        if not signal_ids:
            return {"status": "error", "reason": "No signal_ids provided"}
        
        result = ApprovalWorkflow.approve_signals(signal_ids, notes=notes)
        
        return {
            "status": "ok",
            "approved": result.get("approved", 0),
            "notes": notes,
        }
    except ImportError:
        return {"status": "error", "reason": "instructor_mode module not available"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

@app.post("/instructor/reject")
async def instructor_reject(request: Request):
    """Reject specific training signals — they will NOT be integrated."""
    try:
        from instructor_mode import ApprovalWorkflow
        data = await request.json()
        signal_ids = data.get("signal_ids", [])
        reason = data.get("reason", "")
        
        if not signal_ids:
            return {"status": "error", "reason": "No signal_ids provided"}
        
        result = ApprovalWorkflow.reject_signals(signal_ids, notes=reason)
        
        return {
            "status": "ok",
            "rejected": result.get("rejected", 0),
            "reason": reason,
        }
    except ImportError:
        return {"status": "error", "reason": "instructor_mode module not available"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

@app.get("/instructor/sessions")
async def instructor_sessions():
    """View all instructor training sessions (active and completed)."""
    try:
        from instructor_mode import get_learning_engine
        engine = get_learning_engine()
        
        # Active sessions
        active = {}
        for sid, session in engine._active_sessions.items():
            active[sid] = {
                "instructor": session.instructor_name,
                "turn_count": session.turn_count,
                "signal_count": session.signal_count,
                "started": session.start_time if hasattr(session, 'start_time') else "unknown",
            }
        
        # Completed sessions from log file
        completed = []
        log_path = engine.SESSION_LOG
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            completed.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        
        return {
            "status": "ok",
            "active_sessions": active,
            "active_count": len(active),
            "completed_sessions": completed[-20:],  # Last 20
            "completed_count": len(completed),
        }
    except ImportError:
        return {"status": "error", "reason": "instructor_mode module not available"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}

@app.post("/call")
async def trigger_call(request: Request):
    """Trigger an outbound call through Twilio with a rate governor and atomic locking."""
    # 1. Preflight Audio Check
    if not await audio_pipeline_ready():
        logger.error("[DIALER] Audio Pipeline Not Ready (Cache Empty). Aborting call.")
        return JSONResponse(status_code=503, content={"status": "error", "message": "Audio Pipeline Initializing"})

    # Parse data early to check for instructor/demo mode bypass
    try:
        _early_data = await request.json()
    except Exception:
        _early_form = await request.form()
        _early_data = dict(_early_form)
    _early_instructor = str(_early_data.get('instructor_mode', 'false')).lower() == 'true'
    _early_demo = str(_early_data.get('demo_mode', '')).strip()
    _bypass_governor = _early_instructor or bool(_early_demo)
    
    # 2. Check Governor (bypassed for instructor/demo calls)
    if not _bypass_governor and not can_fire_call():
        return JSONResponse(
            status_code=429,
            content={"status": "blocked", "reason": "rate_governor", "cooldown": COOLDOWN}
        )
    
    try:
        async with outbound_call_lock():
            try:
                # 2. Lazy Load Dialer
                client = ensure_dialer_ready()
                
                # 3. Use already-parsed data
                data = _early_data
                    
                target_number = data.get("to")
                if not target_number:
                    return JSONResponse(status_code=400, content={"status": "error", "message": "Missing 'to' number"})
                
                # [2-STRIKE PRE-CHECK] Tim's directive: "if it hits 2, that is it for that number"
                # Bypassed for instructor/demo calls — these are training, not sales
                if not _bypass_governor:
                    try:
                        from lead_database import LeadDB
                        _precall_db = LeadDB()
                        if _precall_db.apply_two_strike_check(target_number):
                            logger.warning(f"[2-STRIKE] BLOCKED call to {target_number} — number has reached 2-strike limit")
                            mark_call_end()
                            return JSONResponse(status_code=403, content={
                                "status": "blocked",
                                "message": "2-strike rule: this number has failed 2+ times and is exhausted"
                            })
                    except Exception as _pre_err:
                        logger.debug(f"[2-STRIKE] Pre-check failed (allowing call): {_pre_err}")
                    
                from_number = os.environ.get('TWILIO_PHONE_NUMBER')
                
                # [CRO] Local Presence: match caller ID to destination area code
                if CRO_DIALER_AVAILABLE and _cro_lpm and target_number:
                    try:
                        _local_num = _cro_lpm.get_best_caller_id(target_number)
                        if _local_num and _local_num != from_number:
                            logger.info(f"[CRO] Local presence: {from_number} → {_local_num} for {target_number}")
                            from_number = _local_num
                    except Exception as _lp_err:
                        logger.debug(f"[CRO] Local presence fallback: {_lp_err}")
                
                # 4. Get base tunnel URL (for Twilio to fetch TwiML)
                base_url = ""
                if os.path.exists("active_tunnel_url.txt"):
                    with open("active_tunnel_url.txt", "r") as f:
                        base_url = f.read().strip()
                
                # Clean base_url for HTTP use
                if base_url:
                    # [FIX] Force HTTPS for tunnel URLs (Cloudflare requires it)
                    # Only use HTTP for raw IPs (local testing)
                    import re
                    is_ip = re.match(r"^(http|https|wss|ws)://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", base_url)
                    
                    # Strip any websocket scheme first
                    base_url = base_url.replace("wss://", "").replace("ws://", "")
                    # Strip any existing http(s) scheme
                    base_url = base_url.replace("https://", "").replace("http://", "")
                    
                    # Re-apply correct scheme: HTTPS for tunnels, HTTP for IPs
                    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", base_url):
                        base_url = f"http://{base_url}"
                    else:
                        base_url = f"https://{base_url}"
                else:
                    host = request.headers.get("host") or "localhost:8777"
                    base_url = f"http://{host}"

                # Include prospect info in TwiML URL for personalized greeting
                from urllib.parse import quote
                prospect_name = data.get('name', data.get('prospect_name', 'there'))
                business_name = data.get('business', data.get('business_name', ''))
                instructor_mode = str(data.get('instructor_mode', 'false')).lower()
                demo_mode = str(data.get('demo_mode', '')).strip()
                _is_instructor_call = instructor_mode == 'true'
                prospect_phone = quote(str(target_number))
                twiml_url = f"{base_url}/twilio/outbound?prospect_name={quote(str(prospect_name))}&business_name={quote(str(business_name))}&prospect_phone={prospect_phone}&instructor_mode={instructor_mode}&demo_mode={quote(str(demo_mode))}"
                status_callback_url = f"{base_url}/twilio/events"
                
                # 5. Lock Governor & Fire (Isolated Task Simulation)
                mark_call_start()
                
                # [RESILIENCE] Start governor watchdog timer
                try:
                    from telephony_resilience import governor_mark_start
                    governor_mark_start()
                except ImportError:
                    pass
                
                # We wrap the blocking Twilio SDK call in a thread pool to avoid blocking the event loop
                loop = asyncio.get_running_loop()
                
                # [DEMO/INSTRUCTOR MODE] Skip AMD for demo/personal/training calls — connect straight through
                _amd_mode = None if (demo_mode or _is_instructor_call) else TIMING.machine_detection
                
                try:
                    call = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, 
                            lambda: supervisor.wrap_twilio_outbound(
                                client.calls.create,
                                to=target_number,
                                from_=from_number,
                                url=twiml_url,
                                timeout=TIMING.ring_timeout,  # [TIMING CONFIG] Ring timeout
                                machine_detection=_amd_mode,  # [TIMING CONFIG] AMD mode (disabled for demo)
                                record=True,
                                recording_status_callback=f"{base_url}/twilio/recording-status",
                                recording_status_callback_event=["completed"],
                                status_callback=status_callback_url,
                                status_callback_event=['initiated', 'ringing', 'answered', 'completed']
                            )
                        ),
                        timeout=60.0  # 60s timeout on Twilio API call (must exceed ring timeout)
                    )
                except asyncio.TimeoutError:
                    logger.error("[DIALER] Twilio calls.create timed out after 60s")
                    raise Exception("Twilio API call timed out")
                
                if not call:
                    raise Exception("Twilio failed to initiate call (Supervisor Intercepted)")

                logger.info(f"[DIALER] Outbound call FIRE SUCCESS. SID: {call.sid} to {target_number}")
                return {"status": "fired", "sid": call.sid}
                
            except Exception as e:
                logger.error(f"[DIALER] Error triggering call: {e}")
                # Release if we failed to even fire
                mark_call_end()
                return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    except Exception as lock_err:
        # [NEG-PROOF] Lock acquisition failed — body never ran, governor clean, return structured error
        logger.error(f"[DIALER] Call lock acquisition failed: {lock_err}")
        return JSONResponse(status_code=503, content={"status": "error", "message": "Call system busy — try again shortly"})

# =====================================================
# CAMPAIGN AUTOMATION — Batch Lead Processing
# =====================================================
# CAMPAIGN AUTOMATION — SQLite-Backed Lead Processing
# =====================================================
CAMPAIGN_ACTIVE = False
CAMPAIGN_TASK = None

# Initialize Lead Database
try:
    from lead_database import LeadDB
    lead_db = LeadDB()
    LEAD_DB_AVAILABLE = True
    logger.info(f"[LEAD_DB] SQLite lead database loaded ({lead_db._count()} leads)")
except Exception as e:
    lead_db = None
    LEAD_DB_AVAILABLE = False
    logger.warning(f"[LEAD_DB] Failed to load: {e}")

# CW23 Regime Engine Integration
try:
    from regime_queue_integrator import (
        get_regime_summary, get_pacing_delay, should_skip_lead,
        score_lead, get_regime_priority,
    )
    REGIME_AVAILABLE = True
    logger.info("[REGIME] Regime Queue Integrator loaded")
except ImportError:
    REGIME_AVAILABLE = False
    logger.warning("[REGIME] Regime Queue Integrator not available")

@app.post("/campaign/start")
async def start_campaign(request: Request):
    """Start an automated campaign that processes leads from SQLite database"""
    global CAMPAIGN_ACTIVE, CAMPAIGN_TASK, SYSTEM_MODE
    
    if SYSTEM_MODE == "instructor":
        return JSONResponse(status_code=409, content={
            "status": "blocked", 
            "reason": "Alan is in INSTRUCTOR mode. Switch to campaign mode first: POST /mode/set {\"mode\": \"campaign\"}"
        })
    
    if not LEAD_DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lead database not available")
    
    if CAMPAIGN_ACTIVE:
        return JSONResponse(status_code=409, content={"status": "already_running"})
    
    try:
        data = await request.json()
    except Exception:
        data = {}
    
    max_calls = data.get("max_calls", 80)
    delay_between = max(data.get("delay_seconds", 30), 30)  # [COST GUARD] Minimum 30s between calls — tightened for 80-call/day throughput
    
    CAMPAIGN_ACTIVE = True
    CAMPAIGN_TASK = asyncio.create_task(_run_campaign(max_calls, delay_between))
    
    return {"status": "started", "max_calls": max_calls, "delay_seconds": delay_between}

@app.post("/campaign/stop")
async def stop_campaign():
    """Stop the active campaign"""
    global CAMPAIGN_ACTIVE, CAMPAIGN_TASK
    CAMPAIGN_ACTIVE = False
    if CAMPAIGN_TASK and not CAMPAIGN_TASK.done():
        CAMPAIGN_TASK.cancel()
    return {"status": "stopped"}

@app.get("/campaign/status")
async def campaign_status():
    """Get campaign status with lead database stats"""
    status = {
        "active": CAMPAIGN_ACTIVE,
        "task_running": CAMPAIGN_TASK is not None and not CAMPAIGN_TASK.done() if CAMPAIGN_TASK else False,
        "db_available": LEAD_DB_AVAILABLE
    }
    if LEAD_DB_AVAILABLE and lead_db:
        status["stats"] = lead_db.get_stats()
    return status


# ── Verified Caller ID Status Callback ──────────────────────────────────

@app.post("/verify-callback")
async def verify_callback(request: Request):
    """
    Twilio POSTs here after a caller ID verification attempt completes.
    
    Updates the local verification tracker with success/failure.
    Twilio sends: AccountSid, PhoneNumber, VerificationStatus, OutgoingCallerIdSid
    """
    try:
        form = await request.form()
        data = dict(form)
        
        phone = data.get("PhoneNumber", "")
        status_val = data.get("VerificationStatus", "")
        cid_sid = data.get("OutgoingCallerIdSid", "")
        
        logger.info(f"[VERIFY-CALLBACK] Phone={phone} Status={status_val} SID={cid_sid}")
        
        # Update tracker
        tracker_file = os.path.join(os.path.dirname(__file__), "data", "verification_tracker.json")
        tracker = {"pending": {}, "verified": {}, "failed": {}}
        if os.path.exists(tracker_file):
            try:
                with open(tracker_file, "r") as f:
                    tracker = json.load(f)
            except Exception:
                pass
        
        if status_val == "success" and phone:
            pending_info = tracker["pending"].pop(phone, {})
            tracker["verified"][phone] = {
                "sid": cid_sid,
                "friendly_name": pending_info.get("friendly_name", ""),
                "verified_at": datetime.now().isoformat(),
                "initiated_at": pending_info.get("initiated_at", ""),
                "callback": True,
            }
            logger.info(f"[VERIFY-CALLBACK] ✓ {phone} verified successfully")
        elif phone:
            pending_info = tracker["pending"].pop(phone, {})
            tracker["failed"][phone] = {
                "reason": f"Twilio callback: {status_val}",
                "failed_at": datetime.now().isoformat(),
                "initiated_at": pending_info.get("initiated_at", ""),
            }
            logger.warning(f"[VERIFY-CALLBACK] ✗ {phone} verification failed: {status_val}")
        
        os.makedirs(os.path.dirname(tracker_file), exist_ok=True)
        with open(tracker_file, "w") as f:
            json.dump(tracker, f, indent=2)
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"[VERIFY-CALLBACK] Error: {e}")
        return JSONResponse(status_code=200, content={"status": "error", "detail": str(e)})


# ── CW23 Regime Engine Endpoints ────────────────────────────────────────

@app.get("/regime/status")
async def regime_status():
    """Get current Regime Engine status — segment health, model actions, events."""
    if not REGIME_AVAILABLE:
        return JSONResponse(status_code=503, content={
            "status": "unavailable",
            "message": "Regime Engine module not loaded"
        })
    summary = get_regime_summary()
    return {"status": "ok", "regime": summary}

@app.get("/regime/score/{phone}")
async def regime_score_phone(phone: str, business_type: str = ""):
    """Score a phone number against the Regime Engine for real-time segment check."""
    if not REGIME_AVAILABLE:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    score, seg_key, seg_info = score_lead(phone, business_type)
    skip, reason = should_skip_lead(phone, business_type)
    pacing = get_pacing_delay(phone, business_type)
    return {
        "phone": phone,
        "segment_key": seg_key,
        "segment_info": seg_info,
        "score": score,
        "recommended_pacing": pacing,
        "should_skip": skip,
        "skip_reason": reason,
        "regime_priority": get_regime_priority(phone, business_type),
    }

# ── IQcore Cognitive Economy Endpoints (v3.0.0) ─────────────────────────────

try:
    from iqcore_dashboard import get_dashboard as _iqcore_get_dashboard
    from iqcore_enforcer import IQCORES as _iqcore_ledger
    IQCORE_AVAILABLE = True
    logger.info("[IQCORE] IQcore dashboard loaded")
except ImportError:
    IQCORE_AVAILABLE = False
    logger.warning("[IQCORE] IQcore dashboard not available")

@app.get("/iqcore/status")
async def iqcore_status():
    """Return IQcore dashboard — actor budgets, burn logs, and ledger snapshot."""
    if not IQCORE_AVAILABLE:
        return JSONResponse(status_code=503, content={
            "status": "unavailable",
            "message": "IQcore system not loaded"
        })
    dashboard = _iqcore_get_dashboard()
    dashboard["ledger"] = _iqcore_ledger.snapshot()
    return {"status": "ok", "iqcore": dashboard}

@app.get("/iqcore/alerts")
async def iqcore_alerts():
    """Return IQcore burn-rate alert history."""
    if not IQCORE_AVAILABLE:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    try:
        from iqcore_alerts import get_alert_history
        history = get_alert_history()
        return {"status": "ok", "alerts": history}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/iqcore/cost-map")
async def iqcore_cost_map():
    """Return the canonical IQcore cost map for introspection."""
    return {
        "Alan": {
            "lead_routing": 5,
            "script_selection": 3,
            "pacing_decision": 4,
            "segment_selection": 4,
            "regime_skip_check": 2,
            "objection_sensitive_routing": 3,
            "value_sensitive_routing": 3,
            "total_per_cycle": 24,
            "budget": 60,
        },
        "AgentX": {
            "review_proposal": 8,
            "approve_or_reject": 5,
            "model_lifecycle_decision": 6,
            "segment_split_merge_decision": 6,
            "constitutional_check": 4,
            "supervision_cycle": 3,
            "total_per_cycle": 32,
            "budget": 40,
        },
        "RegimeEngine": {
            "total_per_cycle": 0,
            "budget": 0,
            "note": "Meta-organ — observer only, consumes 0 IQcores",
        },
    }

async def _run_campaign(max_calls: int, delay_between: float):
    """Internal campaign runner — processes leads from SQLite database"""
    global CAMPAIGN_ACTIVE
    
    try:
        calls_made = 0
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 5  # [WATCHDOG] Auto-stop after 5 consecutive failures
        
        while CAMPAIGN_ACTIVE and calls_made < max_calls:
            # [WATCHDOG] Stop campaign if too many consecutive failures
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.error(f"[CAMPAIGN] [WATCHDOG] {MAX_CONSECUTIVE_FAILURES} consecutive failures — auto-stopping campaign to prevent waste")
                break
            
            # Get next callable lead from DB
            lead = lead_db.get_next_lead()
            if not lead:
                logger.info("[CAMPAIGN] No more callable leads in queue")
                break
            
            phone = lead["phone_number"]
            lead_id = lead["id"]
            attempts = lead["attempts"]
            max_attempts = lead["max_attempts"]
            
            # [PHONE GUARD] Skip leads with empty/invalid phone numbers
            if not phone or not phone.strip():
                logger.warning(f"[CAMPAIGN] [PHONE GUARD] Skipping {lead.get('name', 'Unknown')} — no phone number")
                lead_db.record_attempt(lead_id, "invalid_number", "No phone number on file")
                continue
            
            # [PHONE GUARD] Basic E.164 validation — must have digits
            import re as _re
            digits_only = _re.sub(r'[^\d]', '', phone)
            if len(digits_only) < 10:
                logger.warning(f"[CAMPAIGN] [PHONE GUARD] Skipping {lead.get('name', 'Unknown')} — phone too short: {phone}")
                lead_db.record_attempt(lead_id, "invalid_number", f"Phone number too short: {phone}")
                continue
            
            # CW23 Regime Engine: skip check
            if REGIME_AVAILABLE:
                skip, skip_reason = should_skip_lead(phone, lead.get("business_type", ""))
                if skip:
                    logger.info(f"[CAMPAIGN] [REGIME SKIP] {lead.get('name', 'Unknown')} — {skip_reason}")
                    lead_db.record_attempt(lead_id, "regime_skipped", skip_reason)
                    continue
            
            # Wait for governor to be ready
            wait_loops = 0
            while not can_fire_call() and CAMPAIGN_ACTIVE and wait_loops < 300:
                await asyncio.sleep(1)
                wait_loops += 1
            
            if not CAMPAIGN_ACTIVE:
                break
            
            logger.info(f"[CAMPAIGN] Calling {lead.get('name', 'Unknown')} at {phone} (attempt {attempts + 1}/{max_attempts})")
            
            try:
                client = ensure_dialer_ready()
                from_number = os.environ.get('TWILIO_PHONE_NUMBER')
                
                # [CRO] Local Presence: match caller ID to destination area code
                if CRO_DIALER_AVAILABLE and _cro_lpm and phone:
                    try:
                        _local_num = _cro_lpm.get_best_caller_id(phone)
                        if _local_num and _local_num != from_number:
                            logger.info(f"[CRO] Local presence: {from_number} → {_local_num} for {phone}")
                            from_number = _local_num
                    except Exception as _lp_err:
                        logger.debug(f"[CRO] Local presence fallback: {_lp_err}")
                
                # Get tunnel URL
                base_url = ""
                if os.path.exists("active_tunnel_url.txt"):
                    with open("active_tunnel_url.txt", "r") as f:
                        base_url = f.read().strip()
                
                if base_url:
                    import re
                    base_url = base_url.replace("wss://", "").replace("ws://", "").replace("https://", "").replace("http://", "")
                    if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", base_url):
                        base_url = f"http://{base_url}"
                    else:
                        base_url = f"https://{base_url}"
                else:
                    base_url = "http://localhost:8777"
                
                # Pass lead info through TwiML for personalized greeting
                from urllib.parse import quote
                lead_name = quote(str(lead.get('name', 'there')))
                lead_biz = quote(str(lead.get('business_type', '')))
                lead_phone = quote(str(phone))
                twiml_url = f"{base_url}/twilio/outbound?prospect_name={lead_name}&business_name={lead_biz}&prospect_phone={lead_phone}"
                status_callback_url = f"{base_url}/twilio/events"
                
                mark_call_start()
                
                # [RESILIENCE] Start governor watchdog timer
                try:
                    from telephony_resilience import governor_mark_start
                    governor_mark_start()
                except ImportError:
                    pass
                
                loop = asyncio.get_running_loop()
                supervisor = AlanSupervisor.get_instance()
                try:
                    call = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: supervisor.wrap_twilio_outbound(
                                client.calls.create,
                                to=phone,
                                from_=from_number,
                                url=twiml_url,
                                timeout=TIMING.ring_timeout,  # [TIMING CONFIG] Ring timeout
                                machine_detection=TIMING.machine_detection,  # [TIMING CONFIG] AMD mode
                                record=True,
                                recording_status_callback=f"{base_url}/twilio/recording-status",
                                recording_status_callback_event=["completed"],
                                status_callback=status_callback_url,
                                status_callback_event=['initiated', 'ringing', 'answered', 'completed']
                            )
                        ),
                        timeout=60.0  # 60s timeout on Twilio API call (must exceed ring timeout)
                    )
                except asyncio.TimeoutError:
                    logger.error(f"[CAMPAIGN] Twilio calls.create timed out after 60s for {phone}")
                    mark_call_end()
                    lead_db.record_attempt(lead_id, "error", "Twilio API call timed out")
                    # [COST GUARD] Still wait between calls even on timeout — prevents rapid-fire
                    pass
                
                if call:
                    logger.info(f"[CAMPAIGN] Call fired: SID {call.sid} to {phone}")
                    calls_made += 1
                    consecutive_failures = 0  # [WATCHDOG] Reset on success
                    lead_db.record_attempt(lead_id, "connected", f"Campaign call SID: {call.sid}", call_sid=call.sid)
                else:
                    logger.warning(f"[CAMPAIGN] Call failed for {phone}")
                    consecutive_failures += 1  # [WATCHDOG] Track consecutive failures
                    lead_db.record_attempt(lead_id, "failed", "Twilio call creation failed")
                    logger.warning(f"[CAMPAIGN] [WATCHDOG] Consecutive failures: {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}")
                    
            except Exception as e:
                logger.error(f"[CAMPAIGN] Error calling {phone}: {e}")
                consecutive_failures += 1  # [WATCHDOG] Errors count as failures too
                lead_db.record_attempt(lead_id, "error", str(e))
                mark_call_end()
                logger.warning(f"[CAMPAIGN] [WATCHDOG] Consecutive failures: {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}")
            
            # Wait between calls — CW23 regime-aware pacing
            actual_delay = delay_between
            if REGIME_AVAILABLE:
                regime_delay = get_pacing_delay(phone, lead.get("business_type", ""), default_delay=int(delay_between))
                if regime_delay != int(delay_between):
                    actual_delay = max(regime_delay, 30)  # [COST GUARD] Minimum 30s — tightened for throughput, other safety layers still active
                    logger.info(f"[CAMPAIGN] [REGIME] Pacing adjusted: {delay_between}s → {actual_delay}s for segment")

            logger.info(f"[CAMPAIGN] Waiting {actual_delay}s before next call...")
            for _ in range(int(actual_delay)):
                if not CAMPAIGN_ACTIVE:
                    break
                await asyncio.sleep(1)
        
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            logger.error(f"[CAMPAIGN] HALTED by watchdog — {consecutive_failures} consecutive failures. {calls_made} successful calls made.")
        else:
            logger.info(f"[CAMPAIGN] Complete. {calls_made} calls made.")
        
    except Exception as e:
        logger.error(f"[CAMPAIGN] Fatal error: {e}")
    finally:
        CAMPAIGN_ACTIVE = False

# =====================================================
# FLEET REPLICATION — Concurrent Call Management (Hive Mind)
# =====================================================

@app.get("/fleet/status")
async def fleet_status():
    """Get real-time fleet status — active instances, capacity, Hive Mind stats."""
    if not REPLICATION_AVAILABLE:
        return JSONResponse(status_code=503, content={"error": "Replication engine not available"})
    engine = get_replication_engine()
    return engine.get_fleet_status()

@app.post("/call/batch")
async def batch_call(request: Request):
    """
    Fire multiple concurrent outbound calls.
    
    Body: {
        "leads": [
            {"to": "+1234567890", "name": "John", "business": "Joe's Pizza"},
            {"to": "+0987654321", "name": "Jane", "business": "Jane's Salon"}
        ],
        "max_concurrent": 5,
        "stagger_seconds": 2
    }
    
    Each call gets its own Alan instance on the relay server.
    Fleet capacity is enforced via fleet_manifest.json max_instances.
    """
    if not REPLICATION_AVAILABLE:
        return JSONResponse(status_code=503, content={"error": "Replication engine not available"})
    
    engine = get_replication_engine()
    
    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})
    
    leads = data.get("leads", [])
    max_concurrent = data.get("max_concurrent", 5)
    stagger_seconds = data.get("stagger_seconds", 2)
    
    if not leads:
        return JSONResponse(status_code=400, content={"error": "No leads provided"})
    
    # Validate leads have phone numbers
    for lead in leads:
        if not lead.get("to"):
            return JSONResponse(status_code=400, content={"error": "Each lead must have a 'to' phone number"})
    
    # Check capacity
    plan = await engine.prepare_batch(leads, max_concurrent)
    
    if plan["accepted"] == 0:
        return JSONResponse(status_code=429, content={
            "error": "No capacity available",
            "fleet_capacity": plan["fleet_capacity"],
            "active_calls": engine.current_count
        })
    
    # Fire accepted calls (staggered to avoid Twilio rate limits)
    asyncio.create_task(_fire_batch_calls(plan["leads_accepted"], stagger_seconds))
    
    return {
        "status": "batch_started",
        "calls_accepted": plan["accepted"],
        "calls_queued": plan["queued"],
        "fleet_capacity": plan["fleet_capacity"],
        "stagger_seconds": stagger_seconds,
    }

async def _fire_batch_calls(leads: List[Dict], stagger_seconds: float):
    """Internal: fire a batch of calls with staggered timing."""
    for i, lead in enumerate(leads):
        try:
            client = ensure_dialer_ready()
            from_number = os.environ.get('TWILIO_PHONE_NUMBER')
            
            # [CRO] Local Presence: match caller ID to destination area code
            phone = lead.get('phone_number', '')
            if CRO_DIALER_AVAILABLE and _cro_lpm and phone:
                try:
                    _local_num = _cro_lpm.get_best_caller_id(phone)
                    if _local_num and _local_num != from_number:
                        logger.info(f"[CRO] Local presence: {from_number} → {_local_num} for {phone}")
                        from_number = _local_num
                except Exception as _lp_err:
                    logger.debug(f"[CRO] Local presence fallback: {_lp_err}")
            
            # Get tunnel URL
            base_url = ""
            if os.path.exists("active_tunnel_url.txt"):
                with open("active_tunnel_url.txt", "r") as f:
                    base_url = f.read().strip()
            
            if base_url:
                import re
                base_url = base_url.replace("wss://", "").replace("ws://", "").replace("https://", "").replace("http://", "")
                if re.match(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", base_url):
                    base_url = f"http://{base_url}"
                else:
                    base_url = f"https://{base_url}"
            else:
                base_url = "http://localhost:8777"
            
            from urllib.parse import quote
            prospect_name = quote(str(lead.get("name", lead.get("prospect_name", "there"))))
            business_name = quote(str(lead.get("business", lead.get("business_name", ""))))
            target = lead["to"]
            prospect_phone = quote(str(target))
            
            twiml_url = f"{base_url}/twilio/outbound?prospect_name={prospect_name}&business_name={business_name}&prospect_phone={prospect_phone}"
            status_callback_url = f"{base_url}/twilio/events"
            
            mark_call_start()
            
            # [RESILIENCE] Start governor watchdog timer
            try:
                from telephony_resilience import governor_mark_start
                governor_mark_start()
            except ImportError:
                pass
            
            loop = asyncio.get_running_loop()
            try:
                call = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda t=target: supervisor.wrap_twilio_outbound(
                            client.calls.create,
                            to=t,
                            from_=from_number,
                            url=twiml_url,
                            timeout=TIMING.ring_timeout,  # [TIMING CONFIG] Ring timeout
                            machine_detection=TIMING.machine_detection,  # [TIMING CONFIG] AMD mode
                            record=True,
                            recording_status_callback=f"{base_url}/twilio/recording-status",
                            recording_status_callback_event=["completed"],
                            status_callback=status_callback_url,
                            status_callback_event=['initiated', 'ringing', 'answered', 'completed']
                        )
                    ),
                    timeout=60.0  # 60s timeout on Twilio API call (must exceed ring timeout)
                )
            except asyncio.TimeoutError:
                logger.error(f"[BATCH] Twilio calls.create timed out after 60s for {target}")
                mark_call_end()  # [RESILIENCE] Release governor on timeout
                continue
            
            if call:
                logger.info(f"[BATCH] Call {i+1}/{len(leads)} fired: SID {call.sid} to {target}")
            else:
                logger.warning(f"[BATCH] Call {i+1}/{len(leads)} failed for {target}")
            
        except Exception as e:
            logger.error(f"[BATCH] Error on call {i+1}/{len(leads)}: {e}")
            mark_call_end()  # [RESILIENCE] Release governor on batch error
        
        # Stagger between calls
        if i < len(leads) - 1 and stagger_seconds > 0:
            await asyncio.sleep(stagger_seconds)

# =====================================================
# ANALYTICS & DASHBOARD API
# =====================================================

@app.get("/analytics/overview")
async def analytics_overview():
    """Get a full analytics overview — lead stats, call history, daily trends"""
    if not LEAD_DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lead database not available")
    
    return {
        "stats": lead_db.get_stats(),
        "daily_trends": lead_db.get_daily_stats(30),
        "recent_calls": lead_db.get_call_history(limit=20),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/analytics/leads")
async def analytics_leads(status: str = None, limit: int = 50):
    """Query leads by status"""
    if not LEAD_DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lead database not available")
    
    with lead_db._conn() as conn:
        if status:
            rows = conn.execute("SELECT * FROM leads WHERE outcome = ? ORDER BY updated_at DESC LIMIT ?", (status, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM leads ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

@app.post("/analytics/add-lead")
async def add_lead(request: Request):
    """Add a new lead to the queue"""
    if not LEAD_DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Lead database not available")
    
    data = await request.json()
    phone = data.get("phone_number")
    if not phone:
        raise HTTPException(status_code=400, detail="phone_number required")
    
    lead_id = lead_db.add_lead(
        phone_number=phone,
        name=data.get("name", "Unknown"),
        business_type=data.get("business_type", "Unknown"),
        priority=data.get("priority", "medium"),
        lead_source=data.get("lead_source")
    )
    return {"status": "added", "lead_id": lead_id}

@app.get("/analytics/recordings")
async def analytics_recordings(limit: int = 50):
    """Get call recordings log"""
    recordings_file = Path(__file__).parent / "data" / "call_recordings.json"
    if not recordings_file.exists():
        return []
    try:
        recordings = json.loads(recordings_file.read_text())
        return recordings[-limit:]
    except Exception:
        return []

# =====================================================
# EXCEL LEAD IMPORT — Feed Alan His Call Lists
# =====================================================

@app.post("/leads/import")
async def import_leads_endpoint(request: Request):
    """
    Import leads from an uploaded Excel (.xlsx) or CSV file.
    
    Usage with curl:
        curl -X POST http://localhost:8777/leads/import -F "file=@leads.xlsx"
    
    Or from the dashboard with a file upload form.
    """
    from fastapi import UploadFile, File
    
    try:
        form = await request.form()
        file = form.get("file")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file uploaded. Send as form field 'file'")
        
        # Get optional parameters
        source = form.get("source", None)
        dry_run = form.get("dry_run", "false").lower() == "true"
        
        # Save to temp file
        import tempfile
        suffix = Path(file.filename).suffix
        if suffix.lower() not in ('.xlsx', '.xls', '.csv'):
            raise HTTPException(status_code=400, detail=f"Unsupported format: {suffix}. Use .xlsx, .xls, or .csv")
        
        temp_path = Path(tempfile.gettempdir()) / f"agentx_import_{int(time.time())}{suffix}"
        content = await file.read()
        temp_path.write_bytes(content)
        
        # Import
        from excel_lead_importer import import_leads
        result = import_leads(
            str(temp_path),
            default_source=source or file.filename,
            dry_run=dry_run
        )
        
        # Cleanup temp file
        try:
            temp_path.unlink()
        except Exception:
            pass  # Best-effort cleanup
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LEAD IMPORT] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/leads/import-path")
async def import_leads_from_path(request: Request):
    """
    Import leads from a file path on the server filesystem.
    
    Body: {"path": "C:/path/to/leads.xlsx", "source": "Feb Campaign", "dry_run": false}
    """
    try:
        data = await request.json()
        filepath = data.get("path")
        if not filepath:
            raise HTTPException(status_code=400, detail="'path' required")
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail=f"File not found: {filepath}")
        
        from excel_lead_importer import import_leads
        result = import_leads(
            filepath,
            default_source=data.get("source"),
            dry_run=data.get("dry_run", False)
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LEAD IMPORT] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# FOLLOW-UP EXECUTION WORKER
# =====================================================

async def _follow_up_execution_worker():
    """
    Background task that checks for due follow-up tasks every 5 minutes
    and executes them by triggering outbound calls via the /call endpoint.
    This is the missing link that makes Alan's callback promises real.
    """
    # Wait 60s after startup before first check (let system stabilize)
    await asyncio.sleep(60)
    
    while True:
        try:
            from src.follow_up import FollowUpManager
            base_dir = os.path.dirname(os.path.abspath(__file__))
            fm = FollowUpManager(os.path.join(base_dir, 'data', 'agent_x.db'))
            
            pending_tasks = fm.get_pending_tasks()
            
            if pending_tasks:
                logger.info(f"[FOLLOW-UP WORKER] Found {len(pending_tasks)} due follow-up tasks")
                
                for task in pending_tasks:
                    task_id = task[0]
                    phone = task[1]
                    priority = task[2]
                    task_type = task[4]
                    context = task[5]
                    
                    # Only auto-execute call-type follow-ups during business hours
                    from datetime import datetime as dt
                    now = dt.now()
                    hour = now.hour
                    weekday = now.weekday()  # 0=Monday, 6=Sunday
                    
                    # Business hours: 8am-5pm, Monday-Saturday
                    if hour < 8 or hour >= 17 or weekday == 6:
                        logger.info(f"[FOLLOW-UP WORKER] Task {task_id} deferred — outside business hours ({hour}:00, day {weekday})")
                        continue
                    
                    if "call" in task_type.lower() or "outbound" in task_type.lower():
                        # Trigger outbound call via internal API
                        try:
                            caller_id = os.environ.get("TWILIO_PHONE_NUMBER", "")
                            if not caller_id:
                                logger.warning(f"[FOLLOW-UP WORKER] Cannot execute call — no TWILIO_PHONE_NUMBER")
                                continue
                            
                            async with httpx.AsyncClient(timeout=30) as client:
                                call_payload = {
                                    "to": phone,
                                    "from_number": caller_id,
                                    "context": f"Follow-up: {context}"
                                }
                                resp = await client.post("http://127.0.0.1:8777/call", json=call_payload)
                                
                                if resp.status_code == 200:
                                    fm.mark_completed(task_id)
                                    logger.info(f"[FOLLOW-UP WORKER] Executed callback to {phone} (task {task_id}, priority: {priority})")
                                else:
                                    logger.warning(f"[FOLLOW-UP WORKER] Call to {phone} returned {resp.status_code}: {resp.text[:100]}")
                        except Exception as call_err:
                            logger.warning(f"[FOLLOW-UP WORKER] Call execution failed for {phone}: {call_err}")
                    
                    elif "email" in task_type.lower() or "nurture" in task_type.lower():
                        # Log email follow-ups — they require SMTP which may not be configured
                        logger.info(f"[FOLLOW-UP WORKER] Email/Nurture task {task_id} for {phone} — SMTP not yet configured, marking for manual review")
                        # Don't mark as completed — leave for when email is wired
                    
                    else:
                        # Unknown task type — mark completed to prevent queue rot
                        fm.mark_completed(task_id)
                        logger.info(f"[FOLLOW-UP WORKER] Completed generic task {task_id}: {task_type} for {phone}")
            
        except Exception as e:
            logger.error(f"[FOLLOW-UP WORKER] Error: {e}")
        
        await asyncio.sleep(300)  # Check every 5 minutes

# =====================================================
# EDUCATION LEARNING CYCLE
# =====================================================

async def _education_learning_cycle():
    """
    Background task that runs Alan's education/self-learning module once daily.
    Scrapes fintech news, analyzes revenue signals, and stores insights.
    These insights are automatically injected into Alan's system prompt.
    """
    # Wait 120s after startup, then run immediately, then daily
    await asyncio.sleep(120)
    
    while True:
        try:
            from datetime import datetime as dt
            now = dt.now()
            
            logger.info(f"[EDUCATION] Starting daily learning cycle at {now.isoformat()}")
            
            # Run education in a thread to avoid blocking the event loop 
            # (it does web scraping which can take 10-30s)
            import threading
            learn_complete = asyncio.Event()
            learn_error = [None]
            
            def _learn():
                try:
                    from src.education import AgentEducation
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    edu = AgentEducation(os.path.join(base_dir, 'data', 'agent_x.db'))
                    edu.explore_and_learn()
                    
                    # Also run coaching analysis on the most recent conversation
                    try:
                        from src.agent_coach import AgentCoach
                        coach = AgentCoach(
                            os.path.join(base_dir, 'data', 'agent_x.db'),
                            os.path.join(base_dir, 'data', 'conversation_history.json')
                        )
                        coach.analyze_last_conversation()
                        logger.info("[EDUCATION] Daily coaching review completed")
                    except Exception as coach_err:
                        logger.warning(f"[EDUCATION] Coaching review skipped: {coach_err}")
                    
                    logger.info("[EDUCATION] Daily learning cycle completed successfully")
                except Exception as e:
                    learn_error[0] = e
                    logger.error(f"[EDUCATION] Learning cycle failed: {e}")
                finally:
                    # Signal completion back to the async event loop
                    try:
                        _loop.call_soon_threadsafe(learn_complete.set)
                    except Exception:
                        pass  # Best effort signal
            
            # Capture the running event loop before spawning the thread
            _loop = asyncio.get_running_loop()
            threading.Thread(target=_learn, daemon=True).start()
            
            # Wait up to 120s for learning to complete
            try:
                await asyncio.wait_for(learn_complete.wait(), timeout=120)
            except asyncio.TimeoutError:
                logger.warning("[EDUCATION] Learning cycle timed out after 120s — will retry tomorrow")
            
            if learn_error[0]:
                logger.error(f"[EDUCATION] Cycle error: {learn_error[0]}")
            
        except Exception as e:
            logger.error(f"[EDUCATION] Cycle error: {e}")
        
        # Sleep until next day (run at ~6 AM daily)
        from datetime import datetime as dt
        now = dt.now()
        # Calculate seconds until next 6 AM
        next_run = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now.hour >= 6:
            next_run = next_run + __import__('datetime').timedelta(days=1)
        sleep_seconds = (next_run - now).total_seconds()
        logger.info(f"[EDUCATION] Next learning cycle in {sleep_seconds/3600:.1f} hours (at {next_run.isoformat()})")
        await asyncio.sleep(sleep_seconds)

# =====================================================
# SELF-HEALTH MONITORING
# =====================================================

async def _self_health_monitor():
    """Background task that periodically verifies system health"""
    while True:
        try:
            checks = {
                "timestamp": datetime.now().isoformat(),
                "server": "ok",
                "tunnel": "unknown",
                "twilio": "unknown",
                "openai": "unknown",
            }
            
            # Check tunnel
            try:
                tunnel_url = ""
                if os.path.exists("active_tunnel_url.txt"):
                    with open("active_tunnel_url.txt", "r") as f:
                        tunnel_url = f.read().strip()
                if tunnel_url:
                    if not tunnel_url.startswith("http"):
                        tunnel_url = f"https://{tunnel_url}"
                    async with httpx.AsyncClient(timeout=10) as client:
                        r = await client.get(f"{tunnel_url}/health")
                        checks["tunnel"] = "ok" if r.status_code == 200 else f"error:{r.status_code}"
            except Exception as e:
                checks["tunnel"] = f"down:{str(e)[:50]}"
                logger.warning(f"[HEALTH] Tunnel check failed: {e}")
            
            # Check Twilio credentials
            try:
                sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
                token = os.environ.get("TWILIO_AUTH_TOKEN", "")
                checks["twilio"] = "ok" if sid and token and len(sid) > 10 else "missing_creds"
            except Exception:
                checks["twilio"] = "error"
            
            # Check OpenAI key
            try:
                key = os.environ.get("OPENAI_API_KEY", "")
                checks["openai"] = "ok" if key and len(key) > 10 else "missing_key"
            except Exception:
                checks["openai"] = "error"
            
            # Log if anything is wrong
            issues = [k for k, v in checks.items() if v not in ("ok", "unknown") and k != "timestamp"]
            if issues:
                logger.warning(f"[HEALTH MONITOR] Issues detected: {checks}")
            
            # [CENTRAL HUB] Report self-health results into supervisor
            if supervisor:
                supervisor.update_self_health(checks)
            
        except Exception as e:
            logger.error(f"[HEALTH MONITOR] Error: {e}")
        
        await asyncio.sleep(300)  # Check every 5 minutes

@app.post("/twilio/events")
async def twilio_events(request: Request):
    """Handle Twilio status callbacks to manage the call governor and classify call outcomes."""
    try:
        # Twilio status callbacks are typically form-encoded
        form_data = await request.form()
        call_status = form_data.get("CallStatus")
        call_sid = form_data.get("CallSid")
        call_duration = form_data.get("CallDuration", "0")
        answered_by = form_data.get("AnsweredBy", "")  # human, machine_start, fax, unknown
        
        # Support 'event_type' if passed in JSON or other formats
        if not call_status:
            try:
                json_data = await request.json()
                call_status = json_data.get("event_type") or json_data.get("CallStatus")
            except Exception:
                pass  # JSON parse failed, use form data

        logger.info(f"[GOVERNOR] Received Twilio Event '{call_status}' for SID {call_sid} (duration={call_duration}s, answered_by={answered_by})")
        
        # [FSM SHADOW] Feed every Twilio event into the FSM for state tracking
        if CALL_FSM_AVAILABLE and call_fsm:
            call_fsm.on_twilio_event(
                call_status=call_status or "",
                answered_by=answered_by or "",
                call_sid=call_sid or "",
            )
        
        # ================================================================
        # [VOICEMAIL BLOCK] Tim's Directive: "No voice mails. Not allowed
        #   and a waste of time and resources." Exception: "Voice mail only
        #   allowed with a current contact or merchant."
        # When AMD detects machine/fax, immediately terminate the call
        # unless the lead has had a previous successful conversation.
        # ================================================================
        if answered_by in ("machine_start", "machine_end", "fax") and call_sid:
            _allow_voicemail = False
            _vm_reason = "no_prior_contact"
            try:
                from lead_database import LeadDB
                _vm_db = LeadDB()
                # Check call history for this call's phone number
                # Look through recent call history for any 'connected'/'interested'/'sale' outcomes
                _vm_history = _vm_db.get_call_history(limit=200)
                # Find the lead associated with this call by looking at recent calls
                # Since we don't have phone directly, check if any lead has a prior successful outcome
                for _vh in _vm_history:
                    if _vh.get('call_sid') == call_sid:
                        _vm_lead_id = _vh.get('lead_id')
                        if _vm_lead_id:
                            _vm_lead = _vm_db.get_lead(_vm_lead_id)
                            if _vm_lead and _vm_lead.get('outcome') in ('connected', 'interested', 'sale', 'callback_scheduled'):
                                _allow_voicemail = True
                                _vm_reason = f"existing_contact_outcome={_vm_lead['outcome']}"
                            # Also check if they have prior successful calls in history
                            _lead_calls = _vm_db.get_call_history(lead_id=_vm_lead_id)
                            for _lc in _lead_calls:
                                if _lc.get('outcome') in ('connected', 'interested', 'sale') and _lc.get('call_sid') != call_sid:
                                    _allow_voicemail = True
                                    _vm_reason = f"prior_successful_call={_lc.get('call_sid')}"
                                    break
                        break
            except Exception as _vm_err:
                logger.warning(f"[VOICEMAIL BLOCK] DB check failed (blocking anyway): {_vm_err}")

            if not _allow_voicemail:
                logger.warning(
                    f"[VOICEMAIL BLOCK] KILLING CALL {call_sid} — answered_by={answered_by}, "
                    f"reason={_vm_reason}. Tim's directive: No voicemails."
                )
                try:
                    _vm_client = ensure_dialer_ready()
                    import asyncio as _vm_asyncio
                    _loop = _vm_asyncio.get_running_loop()
                    await _loop.run_in_executor(
                        None,
                        lambda: _vm_client.calls(call_sid).update(status='completed')
                    )
                    logger.info(f"[VOICEMAIL BLOCK] Call {call_sid} terminated successfully.")
                except Exception as _vm_kill_err:
                    logger.error(f"[VOICEMAIL BLOCK] Failed to terminate call: {_vm_kill_err}")
                
                # Record as voicemail outcome
                _outcome_label = "VOICEMAIL_BLOCKED"
                if supervisor and call_sid:
                    supervisor.update_call_outcome(call_sid=call_sid, outcome="VOICEMAIL_BLOCKED", duration=0)
                
                # Apply strike to lead (part of 2-strike rule)
                try:
                    from lead_database import LeadDB
                    _strike_db = LeadDB()
                    # Find lead by checking recent campaign state
                    _phone = form_data.get("To", "")
                    if _phone:
                        _strike_lead = _strike_db.get_lead_by_phone(_phone)
                        if _strike_lead:
                            _strike_db.record_attempt(
                                _strike_lead['id'], 'voicemail_blocked',
                                f"AMD={answered_by}, auto-killed by voicemail block",
                                call_sid=call_sid
                            )
                            logger.info(f"[2-STRIKE] Recorded voicemail strike for lead {_strike_lead['id']} "
                                       f"(attempts now: {_strike_lead['attempts'] + 1})")
                except Exception as _str_err:
                    logger.warning(f"[2-STRIKE] Failed to record strike: {_str_err}")
                
                # Release governor
                mark_call_end()
                return {"status": "voicemail_blocked"}
            else:
                logger.info(
                    f"[VOICEMAIL BLOCK] ALLOWING voicemail for {call_sid} — "
                    f"reason={_vm_reason}. Existing contact/merchant exception."
                )

        # [PACING] Classify call outcome for post-call reflection
        status_str = str(call_status).lower() if call_status else ""
        _outcome_label = None  # For supervisor reporting
        if status_str in ("completed", "call.completed"):
            duration_int = int(call_duration) if call_duration else 0
            if duration_int > 10:
                logger.info(f"[CALL-OUTCOME] SID {call_sid}: CONVERSATION ({duration_int}s) — Alan spoke with prospect. Post-call reflection: {COOLDOWN}s cooldown before next call.")
                _outcome_label = "CONVERSATION"
            elif answered_by in ("machine_start", "machine_end", "fax"):
                logger.info(f"[CALL-OUTCOME] SID {call_sid}: VOICEMAIL/MACHINE — Detected: {answered_by}. Moving to next lead.")
                _outcome_label = "VOICEMAIL"
            else:
                logger.info(f"[CALL-OUTCOME] SID {call_sid}: BRIEF CONNECT ({duration_int}s) — Short interaction.")
                _outcome_label = "CONVERSATION"
        elif status_str in ("no-answer", "call.no-answer"):
            logger.info(f"[CALL-OUTCOME] SID {call_sid}: NO ANSWER — Rang full duration (timeout={TIMING.ring_timeout}s). Moving to next lead.")
            _outcome_label = "NO_ANSWER"
        elif status_str in ("busy", "call.busy"):
            logger.info(f"[CALL-OUTCOME] SID {call_sid}: BUSY — Line occupied. Will retry later.")
            _outcome_label = "BUSY"
        elif status_str in ("canceled", "call.canceled", "failed", "call.failed"):
            logger.info(f"[CALL-OUTCOME] SID {call_sid}: {status_str.upper()} — Call did not connect.")
            _outcome_label = "FAILED"
        
        # [CENTRAL HUB] Report call outcome to supervisor
        if _outcome_label and supervisor and call_sid:
            supervisor.update_call_outcome(
                call_sid=call_sid,
                outcome=_outcome_label,
                duration=int(call_duration) if call_duration else 0,
            )
        
        # Release governor on terminal states
        # [RESILIENCE] Use centralized terminal status detection
        try:
            from telephony_resilience import is_terminal_status, governor_clear_timeout
            if is_terminal_status(call_status):
                mark_call_end()
                governor_clear_timeout()  # Clear watchdog — normal unlock
                logger.info(f"[GOVERNOR] Call {call_sid} ended. {COOLDOWN}s cooldown before next call (post-call reflection window).")
        except ImportError:
            # Fallback to inline check
            if status_str in ("completed", "canceled", "failed", "no-answer", "busy", "disconnected"):
                mark_call_end()
            elif status_str and status_str.replace("call.", "") in ("completed", "canceled", "failed", "no-answer", "busy", "disconnected"):
                mark_call_end()
        
        # ================================================================
        # [2-STRIKE RULE] Tim's Directive: "if it hits 2, that is it for
        #   that number." Record strikes for non-conversation outcomes.
        # Any terminal status that wasn't a real conversation = 1 strike.
        # After 2 strikes, lead is exhausted (won't be called again).
        # ================================================================
        if _outcome_label and _outcome_label in ("NO_ANSWER", "BUSY", "FAILED", "VOICEMAIL"):
            try:
                from lead_database import LeadDB
                _strike_db = LeadDB()
                _phone = form_data.get("To", "")
                if _phone:
                    _strike_lead = _strike_db.get_lead_by_phone(_phone)
                    if _strike_lead:
                        _strike_db.record_attempt(
                            _strike_lead['id'], _outcome_label.lower(),
                            f"Auto-recorded by 2-strike rule. Status={call_status}, AnsweredBy={answered_by}",
                            call_sid=call_sid or "",
                            duration=int(call_duration) if call_duration else 0
                        )
                        new_attempts = _strike_lead['attempts'] + 1
                        if new_attempts >= 2:
                            logger.warning(
                                f"[2-STRIKE] Lead {_strike_lead['id']} ({_strike_lead.get('name', 'Unknown')}) "
                                f"has reached {new_attempts} strikes — EXHAUSTED. "
                                f"Phone: {_phone}. Will not be called again."
                            )
                        else:
                            logger.info(
                                f"[2-STRIKE] Lead {_strike_lead['id']} — strike {new_attempts}/2. "
                                f"Outcome: {_outcome_label}"
                            )
            except Exception as _strike_err:
                logger.warning(f"[2-STRIKE] Failed to record strike: {_strike_err}")

        # [CRO] Record call event for contact rate analytics
        if CRO_DIALER_AVAILABLE and _outcome_label:
            try:
                from contact_rate_optimizer import ContactRateAnalytics
                _cro_ana = ContactRateAnalytics()
                _phone = form_data.get("To", "")
                _from_phone = form_data.get("From", "")
                _dest_clean = _phone.replace("+1", "").replace("+", "")
                _area = _dest_clean[:3] if len(_dest_clean) >= 10 else "000"
                _connected = _outcome_label in ("CONVERSATION",)
                from datetime import datetime as _cro_dt
                _cro_now = _cro_dt.now()
                _cro_ana.record_call_event(
                    phone=_phone, area_code=_area,
                    timezone="US", local_hour=_cro_now.hour,
                    business_type="merchant_services",
                    lead_source="campaign",
                    connected=_connected, human_contact=_connected,
                    duration=int(call_duration) if call_duration else 0,
                    outcome=_outcome_label or "",
                    call_sid=call_sid or "",
                    from_number=_from_phone
                )
                if _cro_nrt and _from_phone:
                    _cro_nrt.record_call(_from_phone, _connected)
                    logger.debug(f"[CRO] Analytics recorded: area={_area}, connected={_connected}, from={_from_phone}")
            except Exception as _cro_err:
                logger.debug(f"[CRO] Analytics recording failed: {_cro_err}")

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in twilio_events: {e}")
        return {"status": "error"}

@app.post("/twilio/recording-status")
async def twilio_recording_status(request: Request):
    """Handle Twilio recording completion callbacks — log recording URLs for QA review."""
    try:
        form_data = await request.form()
        recording_sid = form_data.get("RecordingSid", "")
        recording_url = form_data.get("RecordingUrl", "")
        call_sid = form_data.get("CallSid", "")
        duration = form_data.get("RecordingDuration", "0")
        status = form_data.get("RecordingStatus", "")
        
        logger.info(f"[RECORDING] Call {call_sid} | Recording {recording_sid} | Duration: {duration}s | Status: {status}")
        logger.info(f"[RECORDING] URL: {recording_url}.mp3")
        
        # Store recording metadata for analytics
        recording_entry = {
            "call_sid": call_sid,
            "recording_sid": recording_sid,
            "recording_url": f"{recording_url}.mp3",
            "duration_seconds": int(duration) if duration else 0,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        # Append to recordings log
        recordings_file = Path(__file__).parent / "data" / "call_recordings.json"
        recordings_file.parent.mkdir(parents=True, exist_ok=True)
        
        recordings = []
        if recordings_file.exists():
            try:
                recordings = json.loads(recordings_file.read_text())
            except Exception:
                recordings = []
        
        recordings.append(recording_entry)
        recordings_file.write_text(json.dumps(recordings, indent=2, default=str))
        
        return {"status": "ok", "recording_sid": recording_sid}
    except Exception as e:
        logger.error(f"[RECORDING] Error handling recording callback: {e}")
        return {"status": "error"}

# Mount AQI Voice Module router
try:
    from aqi_voice_module import router as voice_router, register_stt_callback, send_text_to_voice, register_connect_callback, voice_sessions, cancel_speech, VoiceSession
    app.include_router(voice_router)
    logging.info("AQI Voice Module router enabled")
except (ImportError, Exception) as e:
    logging.error(f"Failed to import AQI Voice Module: {e}. Using stubs.")
    voice_sessions = {}

from aqi_conversation_relay_server import AQIConversationRelayServer

# [DIRECTIVE] Import Relay Server
try:
    print("[INIT] Initializing Embedded Relay Server...")
    relay_server = AQIConversationRelayServer()
    # [COUPLED BOOT] Verify both Alan and Agent X came online together
    boot_status = relay_server.subsystem_status()
    if boot_status["coupled"]:
        print(f"[INIT] Relay Server Initialized Successfully")
        print(f"[COUPLED BOOT] Alan: {boot_status['alan']} | Agent X: {boot_status['agent_x']} — BOTH ONLINE")
    else:
        print(f"[COUPLED BOOT VIOLATION] Alan: {boot_status['alan']} | Agent X: {boot_status['agent_x']}")
        print(f"[COUPLED BOOT] POLICY: If one comes online, they both must. Aborting.")
        relay_server = None
        raise RuntimeError(f"Coupled boot failed: {boot_status}")
except Exception as e:
    print(f"[CRITICAL] Failed to initialize relay server: {e}")
    relay_server = None

async def audio_pipeline_ready():
    """Preflight: Verify TTS is ready before burning Twilio minutes.
    Checks relay server's greeting_cache (populated at startup via OpenAI TTS).
    """
    try:
        # Primary check: relay server's own greeting cache
        if relay_server and hasattr(relay_server, 'greeting_cache') and len(relay_server.greeting_cache) > 0:
            return True
        # If relay server exists but cache is empty, still allow calls
        # (relay server will synthesize greetings on-demand if needed)
        if relay_server and hasattr(relay_server, 'tts_client') and relay_server.tts_client:
            return True
        return False
    except Exception:
        return True  # Fail-open: allow calls if readiness check errors

def get_websocket_url(request: Request):
    """Determine the correct WSS URL for the stream"""
    try:
        # Try to read valid tunnel file
        if os.path.exists("active_tunnel_url.txt"):
            with open("active_tunnel_url.txt", "r") as f:
                content = f.read().strip()
                if content:
                    # If it's a full URL, ensure wss scheme
                    if "://" in content:
                        return content.replace("https://", "wss://").replace("http://", "wss://")
                    return f"wss://{content}"
    except Exception as e:
        logger.error(f"Failed to read tunnel file: {e}")
    
    # Fallback to request host
    host = request.headers.get("host") or "localhost:8777"
    return f"wss://{host}"

@app.post("/twilio/voice")
@app.post("/twilio/outbound")
@app.post("/twilio/inbound")
async def handle_twilio_voice(request: Request):
    """Handle incoming and outbound Twilio calls by connecting to the Relay Stream.
    Accepts query params: prospect_name, business_name for personalized greetings."""
    wss_url = get_websocket_url(request)
    stream_url = f"{wss_url}/twilio/relay"
    
    # Determine call direction from the route
    path = request.url.path
    call_direction = "inbound" if path == "/twilio/inbound" else "outbound"
    
    # Extract prospect info from query params (passed from /call or campaign)
    prospect_name = request.query_params.get('prospect_name', 'there')
    business_name = request.query_params.get('business_name', '')
    prospect_phone = request.query_params.get('prospect_phone', '')
    instructor_mode = request.query_params.get('instructor_mode', 'false')
    demo_mode = request.query_params.get('demo_mode', '')
    
    _mode_tag = " [INSTRUCTOR MODE]" if instructor_mode == 'true' else ""
    if demo_mode:
        _mode_tag = f" [DEMO MODE: {demo_mode}]"
    logger.info(f"[TWILIO] Handling {call_direction} call. Prospect: {prospect_name}.{_mode_tag} Routing to: {stream_url}")
    
    # HTML-escape values for XML safety
    import html
    prospect_name_safe = html.escape(prospect_name)
    business_name_safe = html.escape(business_name)
    prospect_phone_safe = html.escape(prospect_phone)
    instructor_mode_safe = html.escape(instructor_mode)
    demo_mode_safe = html.escape(demo_mode)
    
    twiml_response = f'''<?xml version="1.0" encoding="UTF-8"?>
    <Response>
        <Connect>
            <Stream url="{stream_url}" track="inbound_track">
                <Parameter name="call_direction" value="{call_direction}" />
                <Parameter name="prospect_name" value="{prospect_name_safe}" />
                <Parameter name="business_name" value="{business_name_safe}" />
                <Parameter name="prospect_phone" value="{prospect_phone_safe}" />
                <Parameter name="instructor_mode" value="{instructor_mode_safe}" />
                <Parameter name="demo_mode" value="{demo_mode_safe}" />
            </Stream>
        </Connect>
    </Response>'''
    
    return HTMLResponse(content=twiml_response, media_type="application/xml")

@app.websocket('/twilio/relay')
async def twilio_conversation_relay(websocket: WebSocket):
    logging.info(f"DEBUG: WebSocket connection attempt from {websocket.client}")
    """
    WebSocket endpoint for Twilio ConversationRelay.
    Handles AI-powered voice conversations with Alan.
    """
    if not relay_server:
        logging.error("Relay Server not initialized")
        await websocket.close(code=1011, reason="Relay Server not initialized")
        return

    try:
        await websocket.accept()
        logging.info("ConversationRelay WebSocket connected")
        
        # [FIX] Shim to make Starlette WebSocket behave like websockets standard
        # The relay server checks for .iter_text() but expects the message iterator API when iterating
        # We need to ensure the websocket object passed down has the expected behavior
        
        # Delegate to AQI Conversation Relay Server
        await relay_server.handle_conversation(websocket)
        
    except WebSocketDisconnect:
        logging.info("📞 ConversationRelay disconnected normally")
    except Exception as e:
        logging.error(f"ConversationRelay error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except Exception:
            pass  # Socket already closed

if __name__ == "__main__":
    import signal
    import subprocess

    SERVER_PORT = 8777
    MAX_PORT_WAIT = 30  # seconds to wait for port to clear

    # ── PRE-FLIGHT: Kill stale processes on our port ──────────────────────
    def _preflight_port_cleanup(port: int) -> bool:
        """Kill any process occupying our port and wait for it to clear.
        Returns True if port is ready, False if cleanup failed."""
        try:
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=5
            )
            stale_pids = set()
            for line in result.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        try:
                            pid = int(parts[-1])
                            if pid != os.getpid() and pid > 0:
                                stale_pids.add(pid)
                        except (ValueError, IndexError):
                            pass

            if stale_pids:
                for pid in stale_pids:
                    logger.warning(f"[PREFLIGHT] Killing stale process PID {pid} on port {port}")
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(pid)],
                            capture_output=True, timeout=5
                        )
                    except Exception as e:
                        logger.error(f"[PREFLIGHT] Failed to kill PID {pid}: {e}")

            # Wait for port to fully clear (LISTENING + TIME_WAIT)
            import time as _time
            for attempt in range(MAX_PORT_WAIT):
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True, text=True, timeout=5
                )
                listeners = [l for l in result.stdout.splitlines()
                             if f":{port}" in l and "LISTENING" in l]
                if not listeners:
                    if attempt > 0:
                        logger.info(f"[PREFLIGHT] Port {port} cleared after {attempt}s")
                    else:
                        logger.info(f"[PREFLIGHT] Port {port} is free")
                    return True
                _time.sleep(1)

            logger.error(f"[PREFLIGHT] Port {port} still occupied after {MAX_PORT_WAIT}s — proceeding anyway")
            return False

        except Exception as e:
            logger.warning(f"[PREFLIGHT] Port cleanup check failed: {e} — proceeding anyway")
            return True  # Don't block startup on cleanup failure

    # ── Run port cleanup ──────────────────────────────────────────────────
    logger.info(f"[PREFLIGHT] Checking port {SERVER_PORT}...")
    _preflight_port_cleanup(SERVER_PORT)

    # ── Signal handling ───────────────────────────────────────────────────
    _shutdown_event = asyncio.Event()

    def handle_exit(sig, frame):
        sig_name = signal.Signals(sig).name if hasattr(signal, 'Signals') else str(sig)
        logger.warning(f"[SHUTDOWN] Received {sig_name} — initiating graceful shutdown...")
        _shutdown_event.set()

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # ══════════════════════════════════════════════════════════════════════
    # TIM'S 9-POINT HYPERCORN SMOOTHING PLAN (v2)
    # Directive: "Get it to be smooth, no more binding issues."
    #
    # §1  Worker model: asyncio only (no threads)
    # §2  Workers = 2 (one serving, one draining on restart)
    # §3  Access logging disabled (removes 5-15ms log-write jitter)
    # §4  Keep-alive = 75s (long-lived telephony connections)
    # §5  Max incomplete event threshold = 2048
    # §6  Max body size = 32MB (audio payloads)
    # §7  HTTP/2 disabled (Twilio doesn't use it, saves memory)
    # §8  Event loop policy pinned (done at module level above)
    # §9  Pre-flight port cleanup + retry binding (kept from v1)
    # ══════════════════════════════════════════════════════════════════════

    async def run_server():
        import hypercorn.asyncio
        from hypercorn.config import Config

        config = Config()

        # §1 — Worker model: pure asyncio, no thread pool
        config.worker_class = "asyncio"

        # §2 — Workers: 2 for zero-downtime restart capability
        config.workers = 2

        # Core binding
        config.bind = [f"0.0.0.0:{SERVER_PORT}"]

        # §3 — Access logging: DISABLED (removes 5-15ms jitter per request)
        config.accesslog = None
        config.errorlog = "-"  # Keep error logging to stderr

        # §4 — Keep-alive: 75s for long-lived telephony connections
        # (Twilio holds connections open; short timeouts cause reconnects)
        config.keep_alive_timeout = 75

        # §5 — Max incomplete event size: 2048 bytes
        # (Protects against slow-loris without choking legitimate requests)
        config.h11_max_incomplete_size = 2048

        # §6 — Max body size: 32MB (audio payloads from Twilio)
        # Hypercorn uses h2_max_content_length and h11_max_content_length
        config.h2_max_content_length = 32 * 1024 * 1024  # 32MB
        config.h11_max_content_length = 32 * 1024 * 1024  # 32MB

        # §7 — HTTP/2: DISABLED (Twilio doesn't negotiate h2, saves memory)
        config.h2_max_concurrent_streams = 0  # Effectively disables HTTP/2

        # Shutdown/Graceful tuning
        config.shutdown_timeout = 5       # Active connections get 5s to finish
        config.graceful_timeout = 3       # Max wait for graceful worker shutdown

        # WebSocket health
        config.websocket_ping_interval = 20  # Detect dead WS connections

        # Log the config
        logger.info(f"[HYPERCORN] Config: workers={config.workers}, "
                     f"worker_class={config.worker_class}, "
                     f"keep_alive={config.keep_alive_timeout}s, "
                     f"accesslog={config.accesslog}, "
                     f"h2_disabled=(max_streams=0), "
                     f"max_body=32MB, "
                     f"h11_max_incomplete={config.h11_max_incomplete_size}")

        async def shutdown_trigger():
            """Async callable that Hypercorn awaits for shutdown signal."""
            await _shutdown_event.wait()

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[STARTUP] Binding to 0.0.0.0:{SERVER_PORT} (attempt {attempt}/{max_retries})...")
                await hypercorn.asyncio.serve(app, config, shutdown_trigger=shutdown_trigger)
                break  # Clean exit from serve()
            except OSError as e:
                if e.errno in (10048, 98) and attempt < max_retries:
                    # 10048 = Windows EADDRINUSE, 98 = Linux EADDRINUSE
                    logger.warning(f"[STARTUP] Port {SERVER_PORT} busy (attempt {attempt}), retrying in 5s...")
                    await asyncio.sleep(5)
                else:
                    logger.error(f"[STARTUP] Failed to bind port {SERVER_PORT}: {e}")
                    raise
            except Exception as e:
                logger.error(f"[STARTUP] Server error: {e}")
                logger.error(traceback.format_exc())
                raise
            finally:
                if attempt == max_retries or not _shutdown_event.is_set():
                    logger.info(f"[SHUTDOWN] Server process finished — port {SERVER_PORT} released.")

    # ── Run ───────────────────────────────────────────────────────────────
    try:
        logging.info(f"Starting Agent X Control API on port {SERVER_PORT} (Hypercorn 9-Point Tuned)...")
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("[SHUTDOWN] KeyboardInterrupt caught — exiting cleanly.")