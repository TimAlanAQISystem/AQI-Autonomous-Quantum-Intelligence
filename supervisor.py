# supervisor.py

from __future__ import annotations
import logging
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List, Literal, Optional, Callable
import traceback
import uuid
import threading

Severity = Literal["info", "warning", "error", "critical"]


@dataclass
class Incident:
    id: str
    timestamp: str
    component: str
    severity: Severity
    issue: str
    reason: str
    fix: str
    affected: List[str]
    context: Dict[str, Any]


@dataclass
class ComponentMeta:
    name: str
    depends_on: List[str]
    affects: List[str]


class AlanSupervisor:
    """
    Complete Systems Supervisor for Alan.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AlanSupervisor, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> Optional[AlanSupervisor]:
        return cls._instance

    def __init__(self, logger=None):
        # Prevent re-initialization if already initialized
        if hasattr(self, 'initialized') and self.initialized:
            return
        
        self.logger = logger or logging.getLogger("SUPERVISOR")
        self.incidents: List[Incident] = []
        self.components: Dict[str, ComponentMeta] = {}
        self._lock = threading.Lock()
        self.initialized = True

        # High-level health snapshot — THE SINGLE SOURCE OF TRUTH
        # Tim's directive: "The supervisor should be the main one, and if it
        # can be upgraded to include everything so you just need to watch
        # the supervision, that may help?"
        self.health_state: Dict[str, Any] = {
            # --- Original 8 categories ---
            "event_loop": {"status": "unknown", "latency_ms": None},
            "resources": {"memory_ok": True, "disk_ok": True},
            "network": {"status": "unknown"},
            "audio_pipeline": {"status": "unknown"},
            "conversation_loop": {"status": "unknown"},
            "business_logic": {"status": "unknown"},
            "telemetry": {"status": "unknown"},
            "supervisor": {"status": "ok"},
            # --- NEW: Central Monitoring Hub additions ---
            "governor": {
                "call_in_progress": False,
                "cooldown_remaining": 0,
                "last_call_ts": 0,
                "lock_duration_seconds": 0,
                "watchdog_active": False,
                "status": "idle",  # idle | active | cooldown | stuck
            },
            "tunnel": {
                "url": None,
                "valid": False,
                "reachable": "unknown",
                "last_check_ts": None,
                "status": "unknown",
            },
            "telephony": {
                "ring_timeout": 35,  # [TIMING AUDIT] Must match timing_config.json
                "api_timeout": 60,
                "cooldown_seconds": 30,
                "machine_detection": True,
                "twilio_creds_ok": False,
                "openai_key_ok": False,
                "status": "unknown",
            },
            "call_outcomes": {
                "last_call_sid": None,
                "last_outcome": None,
                "last_call_ts": None,
                "total_calls": 0,
                "conversations": 0,
                "voicemails": 0,
                "no_answers": 0,
                "busy": 0,
                "failed": 0,
            },
            "pacing": {
                "calls_today": 0,
                "governor_blocks": 0,
                "cooldown_blocks": 0,
                "day_reset_date": None,
            },
            "ccnm": {
                "status": "unknown",
                "seed_active": False,
                "confidence": 0.0,
                "calls_analyzed": 0,
                "successful_calls": 0,
                "success_rate": 0.0,
                "last_seed_ts": None,
            },
        }
        
        # Start a health watchdog thread
        self._stop_event = threading.Event()
        self._watchdog_thread = threading.Thread(target=self._health_watchdog, daemon=True)
        self._watchdog_thread.start()

    def _health_watchdog(self):
        """Background thread to monitor system health without blocking asyncio"""
        import time
        import os
        
        while not self._stop_event.is_set():
            try:
                # Basic resource check
                # Note: fully implementing psutil checks would be better, but this is a lightweight placeholder
                self.health_state["resources"]["memory_ok"] = True 
                
                # Check for critical log files
                if os.path.exists("logs/server_hardened_err.log"):
                    size = os.path.getsize("logs/server_hardened_err.log")
                    if size > 10 * 1024 * 1024: # 10MB
                        self.report_incident(
                            component="LOG_SYSTEM",
                            severity="warning",
                            issue="Error log file getting large",
                            reason=f"Log size: {size} bytes",
                            fix="Rotate logs or check for high-frequency errors"
                        )
                
                # Update status
                self.health_state["supervisor"]["status"] = "ok"
                
            except Exception as e:
                self.logger.warning(f"[WATCHDOG] Health check error: {e}")
            
            time.sleep(30) # Check every 30 seconds

    # ---------- Time / ID helpers ----------

    def _now(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

    def _gen_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4()}"

    # ---------- Component registration ----------

    def register_component(
        self,
        name: str,
        depends_on: Optional[List[str]] = None,
        affects: Optional[List[str]] = None,
    ):
        meta = ComponentMeta(
            name=name,
            depends_on=depends_on or [],
            affects=affects or [],
        )
        self.components[name] = meta
        self.logger.info(f"[SUPERVISOR] Registered component: {name}")

    def _resolve_affected(self, component: str) -> List[str]:
        meta = self.components.get(component)
        if not meta:
            return []
        return list(meta.affects)

    # ---------- Incident handling ----------

    def report_incident(
        self,
        component: str,
        severity: Severity,
        issue: str,
        reason: str,
        fix: str,
        context: Optional[Dict[str, Any]] = None,
        id_prefix: str = "incident",
    ) -> Incident:
        incident = Incident(
            id=self._gen_id(id_prefix),
            timestamp=self._now(),
            component=component,
            severity=severity,
            issue=issue,
            reason=reason,
            fix=fix,
            affected=self._resolve_affected(component),
            context=context or {},
        )
        with self._lock:
            self.incidents.append(incident)
            # [SWEEP] Cap incidents to prevent unbounded memory growth
            if len(self.incidents) > 1000:
                self.incidents = self.incidents[-500:]
        self._log_incident(incident)
        return incident

    def _log_incident(self, incident: Incident):
        payload = asdict(incident)
        # Single, machine-readable line for AI consumption
        self.logger.error(f"[ALAN_INCIDENT] {payload}")

    def latest_incidents(self, limit: int = 50) -> List[Incident]:
        with self._lock:
            return self.incidents[-limit:]

    # ---------- Global exception hook ----------

    def install_global_excepthook(self):
        import sys

        def global_excepthook(exctype, value, tb):
            self.report_incident(
                component="GLOBAL",
                severity="critical",
                issue="Uncaught exception in main process",
                reason=f"{exctype.__name__}: {value}",
                fix="Process may be unstable; restart recommended",
                context={"traceback": "".join(traceback.format_tb(tb))},
                id_prefix="global",
            )

        sys.excepthook = global_excepthook
        self.logger.info("[SUPERVISOR] Global excepthook installed")

    # ---------- Internal subsystem wrappers ----------

    def wrap_protocol_start(self, name: str, fn: Callable[[], Any]):
        try:
            fn()
            self.logger.info(f"[SUPERVISOR] Protocol {name} started successfully")
        except Exception as e:
            self.report_incident(
                component=name,
                severity="error",
                issue=f"{name} failed to start",
                reason=str(e),
                fix=f"{name} disabled; server continues in degraded mode",
                context={"traceback": traceback.format_exc()},
                id_prefix=f"protocol-{name}",
            )

    async def acquire_lock_with_watchdog(
        self,
        lock,
        name: str,
        timeout: float = 2.0,
    ):
        import asyncio

        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self.report_incident(
                component=name,
                severity="warning",
                issue=f"Lock '{name}' timeout",
                reason="Lock held too long or deadlocked",
                fix="Lock force-released; investigate contention",
                context={},
                id_prefix=f"lock-{name}",
            )
            if lock.locked():
                lock.release()
            await lock.acquire()

    def governor_triggered(self, name: str, reason: str):
        self.report_incident(
            component=name,
            severity="warning",
            issue=f"Governor '{name}' triggered",
            reason=reason,
            fix="Calls throttled; no shutdown performed",
            context={},
            id_prefix=f"governor-{name}",
        )

    # ---------- Event loop & executor health ----------

    def event_loop_latency(self, latency_ms: float, threshold_ms: float = 100.0):
        self.health_state["event_loop"]["latency_ms"] = latency_ms
        if latency_ms > threshold_ms:
            self.health_state["event_loop"]["status"] = "degraded"
            self.report_incident(
                component="EVENT_LOOP",
                severity="warning",
                issue="Event loop latency high",
                reason=f"{latency_ms}ms > {threshold_ms}ms",
                fix="Move CPU-heavy work off main loop; check TTS/external calls",
                context={"latency_ms": latency_ms},
                id_prefix="event-loop",
            )
        else:
            self.health_state["event_loop"]["status"] = "ok"

    def executor_saturation(self, queue_depth: int, threshold: int = 100):
        if queue_depth > threshold:
            self.report_incident(
                component="EXECUTOR",
                severity="warning",
                issue="Executor queue saturation",
                reason=f"Queue depth {queue_depth} > {threshold}",
                fix="Increase workers or reduce blocking tasks",
                context={"queue_depth": queue_depth},
                id_prefix="executor",
            )

    # ---------- Resource health (memory / disk) ----------

    def memory_pressure(self, ok: bool, detail: str = ""):
        self.health_state["resources"]["memory_ok"] = ok
        if not ok:
            self.report_incident(
                component="MEMORY",
                severity="warning",
                issue="Memory pressure high",
                reason=detail or "Memory usage exceeded threshold",
                fix="Prune caches, restart long-lived processes if needed",
                context={},
                id_prefix="memory",
            )

    def disk_health(self, ok: bool, detail: str = ""):
        self.health_state["resources"]["disk_ok"] = ok
        if not ok:
            self.report_incident(
                component="DISK",
                severity="warning",
                issue="Disk I/O or space issue",
                reason=detail or "Disk space low or I/O slow",
                fix="Clear logs, check disk quota",
                context={},
                id_prefix="disk",
            )

    def validate_response_compliance(self, text: str, context: Dict[str, Any]) -> bool:
        """
        Lightweight CRG compliance check for the Supervisor.
        Checks for sandbox language and invented patterns.
        """
        text_lower = text.lower()
        forbidden_patterns = [
            "let's pretend", 
            "imagine if", 
            "roleplay", 
            "role-play",
            "simulated response",
            "as an ai",
            "i can stop calling you if you want" # Behavioral compliance
        ]
        
        for pattern in forbidden_patterns:
            if pattern in text_lower:
                self.report_incident(
                    component="CRG_GUARDRAIL",
                    severity="warning",
                    issue="Non-compliant response generated",
                    reason=f"Found forbidden pattern: '{pattern}'",
                    fix="System should apply identity-safe phrasing while maintaining conversational arc",
                    context={"response": text}
                )
                return False
        
        return True

    # ---------- Config integrity ----------

    def config_issue(self, name: str, issue: str, reason: str, fix: str):
        self.report_incident(
            component=f"CONFIG:{name}",
            severity="error",
            issue=issue,
            reason=reason,
            fix=fix,
            context={},
            id_prefix="config",
        )

    # ---------- Network / vendor health ----------

    def network_issue(self, issue: str, reason: str, fix: str):
        self.health_state["network"]["status"] = "degraded"
        self.report_incident(
            component="NETWORK",
            severity="warning",
            issue=issue,
            reason=reason,
            fix=fix,
            context={},
            id_prefix="network",
        )

    def vendor_rate_limit(self, vendor: str, detail: str, retry_after: Optional[float]):
        self.report_incident(
            component=f"{vendor}_RATE_LIMIT",
            severity="warning",
            issue=f"{vendor} rate limit hit",
            reason=detail,
            fix=f"Backing off {retry_after}s" if retry_after else "Backing off",
            context={"retry_after": retry_after},
            id_prefix=f"{vendor.lower()}-ratelimit",
        )

    # ---------- Twilio wrappers ----------

    def wrap_twilio_outbound(self, fn: Callable, **kwargs):
        try:
            return fn(**kwargs)
        except Exception as e:
            self.report_incident(
                component="TWILIO_OUTBOUND",
                severity="error",
                issue="Twilio outbound call failed",
                reason=str(e),
                fix="Call aborted; retry recommended",
                context={"kwargs": kwargs, "traceback": traceback.format_exc()},
                id_prefix="twilio-outbound",
            )
            return None

    def twilio_media_disconnect(self, reason: str):
        self.report_incident(
            component="TWILIO_MEDIA_STREAM",
            severity="warning",
            issue="Media stream disconnected",
            reason=reason,
            fix="Attempting reconnection",
            context={},
            id_prefix="twilio-media",
        )

    # ---------- PSTN / SIP events ----------

    def pstn_event(self, event: str, detail: str):
        self.report_incident(
            component="PSTN",
            severity="warning",
            issue=f"PSTN event: {event}",
            reason=detail,
            fix="Monitoring; retry if needed",
            context={},
            id_prefix="pstn",
        )

    # ---------- TTS (OpenAI) ----------

    def wrap_tts(self, fn: Callable, text: str, **kwargs):
        """Wraps any TTS call with incident tracking. Vendor-agnostic."""
        try:
            return fn(text=text, **kwargs)
        except Exception as e:
            self.report_incident(
                component="TTS",
                severity="error",
                issue="TTS generation failed",
                reason=str(e),
                fix="Using fallback voice or retrying",
                context={"text": text, "traceback": traceback.format_exc()},
                id_prefix="tts",
            )
            return None

    def tts_latency(self, latency_ms: float, threshold_ms: float = 2000.0):
        if latency_ms > threshold_ms:
            self.report_incident(
                component="TTS",
                severity="warning",
                issue="High TTS latency",
                reason=f"{latency_ms}ms > {threshold_ms}ms",
                fix="Switching to cached audio or shorter prompts",
                context={"latency": latency_ms},
                id_prefix="tts-latency",
            )

    # ---------- Audio pipeline ----------

    def audio_pipeline_status(self, ok: bool, detail: str = ""):
        self.health_state["audio_pipeline"]["status"] = "ok" if ok else "degraded"
        if not ok:
            self.report_incident(
                component="AUDIO_PIPELINE",
                severity="error",
                issue="Audio pipeline failure",
                reason=detail or "Unknown audio pipeline error",
                fix="Check TTS, encoding, and media stream",
                context={},
                id_prefix="audio",
            )

    # ---------- Conversation loop ----------

    def conversation_issue(self, issue: str, reason: str, fix: str):
        self.health_state["conversation_loop"]["status"] = "degraded"
        self.report_incident(
            component="CONVERSATION_LOOP",
            severity="warning",
            issue=issue,
            reason=reason,
            fix=fix,
            context={},
            id_prefix="conversation",
        )

    # ---------- Business logic router ----------

    def business_logic_issue(self, issue: str, reason: str, fix: str):
        self.health_state["business_logic"]["status"] = "degraded"
        self.report_incident(
            component="BUSINESS_LOGIC",
            severity="error",
            issue=issue,
            reason=reason,
            fix=fix,
            context={},
            id_prefix="business-logic",
        )

    # ---------- Telemetry / logging health ----------

    def telemetry_issue(self, issue: str, reason: str, fix: str):
        self.health_state["telemetry"]["status"] = "degraded"
        self.report_incident(
            component="TELEMETRY",
            severity="warning",
            issue=issue,
            reason=reason,
            fix=fix,
            context={},
            id_prefix="telemetry",
        )

    # ---------- Supervisor self-health ----------

    def supervisor_issue(self, issue: str, reason: str, fix: str):
        self.health_state["supervisor"]["status"] = "degraded"
        self.report_incident(
            component="SUPERVISOR",
            severity="critical",
            issue=issue,
            reason=reason,
            fix=fix,
            context={},
            id_prefix="supervisor",
        )

    # ---------- Health snapshot for /health or /diagnostics ----------

    def snapshot(self) -> Dict[str, Any]:
        """
        Returns a machine-readable snapshot of current health state
        plus a small tail of recent incidents.
        """
        return {
            "timestamp": self._now(),
            "health": self.health_state,
            "recent_incidents": [asdict(i) for i in self.latest_incidents(20)],
        }

    # ==========================================================================
    # CENTRAL MONITORING HUB — Tim's Directive (Feb 17, 2026)
    # ==========================================================================
    # "The supervisor should be the main one, and if it can be upgraded to
    #  include everything so you just need to watch the supervision, that
    #  may help?"
    #
    # These methods allow all scattered monitors to REPORT INTO one place.
    # An instance only needs to call get_unified_dashboard() to know everything.
    # ==========================================================================

    # ---------- Governor State ----------

    def update_governor_state(
        self,
        call_in_progress: bool,
        cooldown_remaining: float = 0,
        last_call_ts: float = 0,
        lock_duration: float = 0,
        watchdog_active: bool = True,
    ):
        """Called by mark_call_start, mark_call_end, and governor_watchdog_loop."""
        gov = self.health_state["governor"]
        gov["call_in_progress"] = call_in_progress
        gov["cooldown_remaining"] = round(cooldown_remaining, 1)
        gov["last_call_ts"] = last_call_ts
        gov["lock_duration_seconds"] = round(lock_duration, 1)
        gov["watchdog_active"] = watchdog_active
        if call_in_progress:
            gov["status"] = "active"
        elif cooldown_remaining > 0:
            gov["status"] = "cooldown"
        else:
            gov["status"] = "idle"

    def governor_force_unlocked(self):
        """Called when the watchdog force-unlocks the governor."""
        self.health_state["governor"]["status"] = "idle"
        self.health_state["governor"]["call_in_progress"] = False
        self.report_incident(
            component="GOVERNOR",
            severity="warning",
            issue="Governor force-unlocked by watchdog",
            reason="Locked beyond GOVERNOR_MAX_LOCK_SECONDS — Twilio callback likely missed",
            fix="Governor reset to idle. System recovered automatically.",
            context={},
            id_prefix="governor-watchdog",
        )

    def governor_blocked(self, reason: str):
        """Called when can_fire_call() blocks a call attempt."""
        pacing = self.health_state["pacing"]
        if "Cooldown" in reason:
            pacing["cooldown_blocks"] += 1
        else:
            pacing["governor_blocks"] += 1

    # ---------- Tunnel State ----------

    def update_tunnel_state(
        self,
        url: Optional[str],
        valid: bool,
        reachable: str = "unknown",
    ):
        """Called by background_tunnel_monitor and _self_health_monitor."""
        tunnel = self.health_state["tunnel"]
        tunnel["url"] = url
        tunnel["valid"] = valid
        tunnel["reachable"] = reachable
        tunnel["last_check_ts"] = self._now()
        if not url:
            tunnel["status"] = "no_url"
        elif not valid:
            tunnel["status"] = "invalid"
        elif reachable == "ok":
            tunnel["status"] = "ok"
        elif reachable.startswith("down") or reachable.startswith("error"):
            tunnel["status"] = "degraded"
        else:
            tunnel["status"] = "unknown"

    # ---------- Telephony Config / Creds ----------

    def update_telephony_creds(self, twilio_ok: bool, openai_ok: bool):
        """Called by _self_health_monitor after credential checks."""
        tele = self.health_state["telephony"]
        tele["twilio_creds_ok"] = twilio_ok
        tele["openai_key_ok"] = openai_ok
        if twilio_ok and openai_ok:
            tele["status"] = "ok"
        elif not twilio_ok and not openai_ok:
            tele["status"] = "critical"
        else:
            tele["status"] = "degraded"

    # ---------- Call Outcomes ----------

    def update_call_outcome(
        self,
        call_sid: str,
        outcome: str,
        duration: int = 0,
    ):
        """
        Called by /twilio/events after classifying call outcome.
        outcome: CONVERSATION | VOICEMAIL | NO_ANSWER | BUSY | FAILED
        """
        co = self.health_state["call_outcomes"]
        co["last_call_sid"] = call_sid
        co["last_outcome"] = outcome
        co["last_call_ts"] = self._now()
        co["total_calls"] += 1

        outcome_upper = outcome.upper().replace(" ", "_")
        if outcome_upper == "CONVERSATION":
            co["conversations"] += 1
        elif outcome_upper == "VOICEMAIL":
            co["voicemails"] += 1
        elif outcome_upper == "NO_ANSWER":
            co["no_answers"] += 1
        elif outcome_upper == "BUSY":
            co["busy"] += 1
        elif outcome_upper == "FAILED":
            co["failed"] += 1

        # Update daily pacing counter
        self._increment_daily_calls()

    def _increment_daily_calls(self):
        """Auto-resets the daily counter at midnight."""
        from datetime import date
        today = date.today().isoformat()
        pacing = self.health_state["pacing"]
        if pacing["day_reset_date"] != today:
            pacing["calls_today"] = 0
            pacing["governor_blocks"] = 0
            pacing["cooldown_blocks"] = 0
            pacing["day_reset_date"] = today
        pacing["calls_today"] += 1

    # ---------- CCNM State ----------

    def update_ccnm_state(self, seed_active: bool, confidence: float,
                          calls_analyzed: int, successful_calls: int,
                          success_rate: float):
        """
        Called after CCNM seed generation to report cross-call learning status.
        """
        from datetime import datetime as _dt
        ccnm = self.health_state["ccnm"]
        ccnm["seed_active"] = seed_active
        ccnm["confidence"] = round(confidence, 3)
        ccnm["calls_analyzed"] = calls_analyzed
        ccnm["successful_calls"] = successful_calls
        ccnm["success_rate"] = round(success_rate, 3)
        ccnm["last_seed_ts"] = _dt.now().isoformat()
        ccnm["status"] = "active" if seed_active else "neutral"

    # ---------- Self-Health Check Results ----------

    def update_self_health(self, checks: Dict[str, str]):
        """
        Called by _self_health_monitor after each health cycle.
        checks dict: {"server": "ok", "tunnel": "ok|down:...", "twilio": "ok|missing_creds", "openai": "ok|missing_key"}
        """
        # Update tunnel
        tunnel_status = checks.get("tunnel", "unknown")
        self.update_tunnel_state(
            url=self.health_state["tunnel"].get("url"),
            valid=self.health_state["tunnel"].get("valid", False),
            reachable=tunnel_status,
        )
        # Update creds
        twilio_ok = checks.get("twilio") == "ok"
        openai_ok = checks.get("openai") == "ok"
        self.update_telephony_creds(twilio_ok, openai_ok)
        # Update network
        if tunnel_status == "ok":
            self.health_state["network"]["status"] = "ok"
        elif tunnel_status.startswith("down"):
            self.health_state["network"]["status"] = "degraded"

    # ---------- UNIFIED DASHBOARD — The Single Thing to Watch ----------

    def get_unified_dashboard(self, arde_snapshot: Optional[Dict] = None) -> Dict[str, Any]:
        """
        THE SINGLE SOURCE OF TRUTH.

        Returns everything an AI instance needs to know about system health
        in one call. No need to check 5+ scattered monitors individually.

        Includes: governor state, tunnel health, telephony config, call outcomes,
        pacing metrics, ARDE status, all original 8 health categories, and
        recent incidents.

        Usage:
            dashboard = supervisor.get_unified_dashboard(arde_snapshot=arde.snapshot() if arde else None)
        """
        # [TIMING AUDIT] Refresh telephony values from live TIMING object every call
        try:
            from timing_loader import TIMING
            tele = self.health_state["telephony"]
            tele["ring_timeout"] = TIMING.ring_timeout
            tele["cooldown_seconds"] = TIMING.post_call_cooldown
        except Exception:
            pass  # If TIMING unavailable, keep whatever was set

        dashboard = {
            "timestamp": self._now(),
            "system_status": self._compute_overall_status(),
            "health": self.health_state,
            "recent_incidents": [asdict(i) for i in self.latest_incidents(20)],
            "incident_count_total": len(self.incidents),
        }

        # Merge ARDE if available
        if arde_snapshot:
            dashboard["arde"] = arde_snapshot

        return dashboard

    def _compute_overall_status(self) -> str:
        """
        Single word summary: ALL_GREEN | DEGRADED | CRITICAL

        ALL_GREEN: Governor idle or in cooldown, tunnel OK, creds OK, no CRITICAL incidents in last 5 min.
        DEGRADED: Something non-critical is off (tunnel unknown, creds missing, governor stuck).
        CRITICAL: Governor stuck > max lock, tunnel down, creds missing, or CRITICAL incident.
        """
        gov = self.health_state["governor"]
        tunnel = self.health_state["tunnel"]
        tele = self.health_state["telephony"]

        # Critical checks
        if gov["status"] == "stuck":
            return "CRITICAL"
        if tunnel.get("status") == "degraded":
            return "DEGRADED"
        if tele.get("status") == "critical":
            return "CRITICAL"

        # Check for recent critical incidents (last 5 min)
        from datetime import datetime as dt, timedelta
        now = dt.utcnow()
        recent_criticals = [
            i for i in self.latest_incidents(50)
            if i.severity == "critical"
            and (now - dt.fromisoformat(i.timestamp.rstrip("Z"))) < timedelta(minutes=5)
        ]
        if recent_criticals:
            return "CRITICAL"

        # Degraded checks
        degraded_categories = [
            k for k, v in self.health_state.items()
            if isinstance(v, dict) and v.get("status") in ("degraded", "unknown")
        ]
        # Ignore initial "unknown" states for categories that haven't reported yet
        # These only get set after first call / first health monitor cycle
        initial_unknown_ok = {
            "event_loop", "audio_pipeline", "conversation_loop",
            "business_logic", "telemetry", "network",
        }
        significant_degraded = [
            k for k in degraded_categories
            if k not in initial_unknown_ok
        ]
        if significant_degraded:
            return "DEGRADED"

        return "ALL_GREEN"
