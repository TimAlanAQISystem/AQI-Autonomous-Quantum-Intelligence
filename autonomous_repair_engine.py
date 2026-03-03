"""
╔══════════════════════════════════════════════════════════════════════════╗
║   AUTONOMOUS REPAIR & DIAGNOSTICS ENGINE (ARDE)                        ║
║   AQI Agent X / Alan — Self-Healing Subsystem                          ║
║                                                                        ║
║   Purpose: Continuously monitors Alan and Agent X, detects degradation, ║
║   attempts autonomous repair, and logs all actions for operator review. ║
║                                                                        ║
║   Policy: If one goes down, attempt repair. If repair fails after      ║
║   MAX_REPAIR_ATTEMPTS, raise CRITICAL alert. Never silently degrade.    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import os
import time
import traceback
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum

logger = logging.getLogger("ARDE")

# ──────────────────────────────────────────────────────────────────
#  STATUS & EVENT TYPES
# ──────────────────────────────────────────────────────────────────

class SubsystemID(str, Enum):
    ALAN = "alan"
    AGENT_X = "agent_x"
    TUNNEL = "tunnel"
    TWILIO = "twilio"
    OPENAI = "openai"
    TTS = "tts"
    GREETING_CACHE = "greeting_cache"


class RepairAction(str, Enum):
    REINIT_ALAN = "reinit_alan"
    REINIT_AGENT_X = "reinit_agent_x"
    REBUILD_GREETING_CACHE = "rebuild_greeting_cache"
    RECONNECT_TTS = "reconnect_tts"
    RESYNC_TUNNEL = "resync_tunnel"
    FULL_RELAY_RESTART = "full_relay_restart"


class DiagnosticSeverity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"


@dataclass
class DiagnosticEvent:
    """Single diagnostic check result."""
    timestamp: str
    subsystem: str
    status: str
    detail: str = ""
    latency_ms: float = 0.0


@dataclass
class RepairEvent:
    """Record of an autonomous repair attempt."""
    timestamp: str
    subsystem: str
    action: str
    success: bool
    detail: str = ""
    duration_ms: float = 0.0


@dataclass
class ARDEState:
    """Full engine state — serializable for /diagnostics/arde endpoint."""
    running: bool = False
    cycle_count: int = 0
    last_cycle: str = ""
    last_full_pass: str = ""
    consecutive_failures: Dict[str, int] = field(default_factory=dict)
    repair_history: List[Dict] = field(default_factory=list)
    subsystem_health: Dict[str, str] = field(default_factory=dict)
    overall_status: str = "INITIALIZING"


# ──────────────────────────────────────────────────────────────────
#  AUTONOMOUS REPAIR & DIAGNOSTICS ENGINE
# ──────────────────────────────────────────────────────────────────

class AutonomousRepairEngine:
    """
    Self-healing engine that monitors Alan and Agent X and attempts
    autonomous repair when degradation is detected.

    Runs as an asyncio background task inside the control_api lifespan.

    VIP LAUNCH MODE: Activated via activate_vip_mode() or VIP_LAUNCH_MODE=1 env var.
    Tightens thresholds, accelerates monitoring, and halts traffic on CRITICAL.
    """

    # ── Normal Mode Configuration ──
    CHECK_INTERVAL = 60          # Seconds between diagnostic cycles
    MAX_REPAIR_ATTEMPTS = 3      # Per subsystem before declaring CRITICAL
    REPAIR_COOLDOWN = 120        # Seconds between repair attempts on same subsystem
    HISTORY_CAP = 200            # Max repair events to keep in memory
    LOG_FILE = "logs/arde_repair_log.json"

    # ── VIP Mode Configuration ──
    VIP_CHECK_INTERVAL = 20      # 3× monitoring density
    VIP_MAX_REPAIR_ATTEMPTS = 2  # Faster escalation to CRITICAL
    VIP_REPAIR_COOLDOWN = 45     # Faster but controlled repair cadence
    VIP_GREETING_CACHE_MIN = 5   # Stricter greeting cache minimum
    VIP_STABILITY_WINDOW = 300   # 5 min — no repairs allowed in window for readiness

    def __init__(self, relay_server=None, supervisor=None):
        self._relay = relay_server
        self._supervisor = supervisor
        self._state = ARDEState()
        self._last_repair_time: Dict[str, float] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # ── VIP Launch Mode ──
        self._vip_mode = os.environ.get("VIP_LAUNCH_MODE", "0") == "1"
        self._traffic_halted = False  # Global traffic halt flag — set on CRITICAL in VIP mode
        self._traffic_halt_reason = ""
        self._vip_activated_at: Optional[str] = None
        if self._vip_mode:
            self._vip_activated_at = datetime.now().isoformat()
            logger.info("[ARDE] ⚡ VIP LAUNCH MODE ACTIVE (via env var)")

        # Ensure log directory
        Path(self.LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    # ── PUBLIC API ──

    def attach_relay(self, relay_server):
        """Hot-attach relay server (may not be available at init time)."""
        self._relay = relay_server
        logger.info("[ARDE] Relay server attached")

    def attach_supervisor(self, supervisor):
        """Hot-attach supervisor."""
        self._supervisor = supervisor
        logger.info("[ARDE] Supervisor attached")

    # ── VIP LAUNCH MODE API ──

    def activate_vip_mode(self):
        """Switch to VIP Launch Mode — tightened thresholds, faster cycles, traffic halt on CRITICAL."""
        if self._vip_mode:
            logger.info("[ARDE] VIP mode already active")
            return {"status": "already_active", "activated_at": self._vip_activated_at}
        self._vip_mode = True
        self._vip_activated_at = datetime.now().isoformat()
        logger.info("[ARDE] ⚡ VIP LAUNCH MODE ACTIVATED — thresholds tightened, cycle=20s, cooldown=45s")
        if self._supervisor:
            self._supervisor.report_incident(
                component="ARDE_VIP",
                severity="info",
                issue="VIP Launch Mode activated",
                reason="Operator-initiated hardened governance",
                fix="Deactivate via POST /vip/deactivate when VIP traffic ends",
            )
        return {"status": "activated", "activated_at": self._vip_activated_at}

    def deactivate_vip_mode(self):
        """Return to normal operating thresholds."""
        if not self._vip_mode:
            return {"status": "already_normal"}
        self._vip_mode = False
        self._traffic_halted = False
        self._traffic_halt_reason = ""
        logger.info("[ARDE] VIP Launch Mode deactivated — returning to normal thresholds")
        return {"status": "deactivated"}

    @property
    def vip_mode(self) -> bool:
        return self._vip_mode

    @property
    def traffic_halted(self) -> bool:
        return self._traffic_halted

    @property
    def traffic_halt_reason(self) -> str:
        return self._traffic_halt_reason

    def clear_traffic_halt(self):
        """Manually clear the traffic halt flag (after resolving the issue)."""
        self._traffic_halted = False
        self._traffic_halt_reason = ""
        logger.info("[ARDE] Traffic halt cleared by operator")
        return {"status": "cleared"}

    def vip_status(self) -> Dict[str, Any]:
        """Full VIP mode status snapshot."""
        return {
            "vip_mode": self._vip_mode,
            "activated_at": self._vip_activated_at,
            "traffic_halted": self._traffic_halted,
            "traffic_halt_reason": self._traffic_halt_reason,
            "effective_check_interval": self._effective_check_interval,
            "effective_repair_cooldown": self._effective_repair_cooldown,
            "effective_max_attempts": self._effective_max_attempts,
        }

    @property
    def _effective_check_interval(self) -> int:
        return self.VIP_CHECK_INTERVAL if self._vip_mode else self.CHECK_INTERVAL

    @property
    def _effective_repair_cooldown(self) -> int:
        return self.VIP_REPAIR_COOLDOWN if self._vip_mode else self.REPAIR_COOLDOWN

    @property
    def _effective_max_attempts(self) -> int:
        return self.VIP_MAX_REPAIR_ATTEMPTS if self._vip_mode else self.MAX_REPAIR_ATTEMPTS

    def start(self) -> asyncio.Task:
        """Start the autonomous background loop. Returns the asyncio Task."""
        if self._running:
            logger.warning("[ARDE] Already running — ignoring duplicate start")
            return self._task
        self._running = True
        self._state.running = True
        self._task = asyncio.create_task(self._run_loop())
        mode = "VIP" if self._vip_mode else "NORMAL"
        logger.info(f"[ARDE] Autonomous Repair Engine started (mode={mode}, interval={self._effective_check_interval}s)")
        return self._task

    def stop(self):
        """Gracefully stop the engine."""
        self._running = False
        self._state.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("[ARDE] Autonomous Repair Engine stopped")

    def snapshot(self) -> Dict[str, Any]:
        """Full engine state snapshot for API endpoints."""
        snap = asdict(self._state)
        snap["vip_mode"] = self._vip_mode
        snap["traffic_halted"] = self._traffic_halted
        snap["traffic_halt_reason"] = self._traffic_halt_reason
        snap["effective_interval"] = self._effective_check_interval
        snap["effective_cooldown"] = self._effective_repair_cooldown
        snap["effective_max_attempts"] = self._effective_max_attempts
        return snap

    def force_diagnostic(self) -> Dict[str, Any]:
        """Run a synchronous (non-repairing) diagnostic sweep — for on-demand checks."""
        results = {}
        results["alan"] = self._check_alan()
        results["agent_x"] = self._check_agent_x()
        results["tts"] = self._check_tts()
        results["greeting_cache"] = self._check_greeting_cache()
        results["tunnel"] = self._check_tunnel()
        results["twilio"] = self._check_twilio()
        results["openai"] = self._check_openai()

        # Overall
        statuses = [r["status"] for r in results.values()]
        if all(s == "ok" for s in statuses):
            results["overall"] = "ALL_SYSTEMS_GO"
        elif any(s == "critical" for s in statuses):
            results["overall"] = "CRITICAL"
        elif any(s == "degraded" for s in statuses):
            results["overall"] = "DEGRADED"
        else:
            results["overall"] = "WARNING"

        results["timestamp"] = datetime.now().isoformat()
        return results

    # ── MAIN LOOP ──

    async def _run_loop(self):
        """Core autonomous loop: diagnose → repair → log → sleep → repeat."""
        logger.info("[ARDE] Entering autonomous repair loop")
        while self._running:
            try:
                self._state.cycle_count += 1
                self._state.last_cycle = datetime.now().isoformat()

                # 1. DIAGNOSE — check every subsystem
                diag = self.force_diagnostic()

                # 2. UPDATE HEALTH MAP
                for sub_id in [s.value for s in SubsystemID]:
                    if sub_id in diag:
                        self._state.subsystem_health[sub_id] = diag[sub_id]["status"]

                # 3. REPAIR — attempt autonomous fixes for anything not "ok"
                repair_needed = {
                    k: v for k, v in diag.items()
                    if isinstance(v, dict) and v.get("status") in ("degraded", "critical")
                }

                for sub_id, check_result in repair_needed.items():
                    await self._attempt_repair(sub_id, check_result)

                # 4. OVERALL STATUS
                health_vals = list(self._state.subsystem_health.values())
                if all(v == "ok" for v in health_vals):
                    self._state.overall_status = "ALL_SYSTEMS_GO"
                    self._state.last_full_pass = datetime.now().isoformat()
                    # Auto-clear traffic halt if everything is green and stable
                    if self._traffic_halted and self._vip_mode:
                        logger.info("[ARDE] All subsystems recovered — clearing traffic halt")
                        self._traffic_halted = False
                        self._traffic_halt_reason = ""
                elif any(v == "critical" for v in health_vals):
                    self._state.overall_status = "CRITICAL"
                    # ── VIP MODE: HALT TRAFFIC ON CRITICAL ──
                    if self._vip_mode and not self._traffic_halted:
                        critical_subs = [k for k, v in self._state.subsystem_health.items() if v == "critical"]
                        self._traffic_halted = True
                        self._traffic_halt_reason = f"CRITICAL subsystem(s): {', '.join(critical_subs)}"
                        logger.error(f"[ARDE] ⛔ VIP TRAFFIC HALTED — {self._traffic_halt_reason}")
                        if self._supervisor:
                            self._supervisor.report_incident(
                                component="ARDE_VIP_HALT",
                                severity="critical",
                                issue=f"Traffic halted — {self._traffic_halt_reason}",
                                reason="VIP Launch Mode: CRITICAL subsystem detected",
                                fix="Resolve the subsystem failure, then POST /vip/clear-halt",
                            )
                elif any(v == "degraded" for v in health_vals):
                    self._state.overall_status = "DEGRADED"
                else:
                    self._state.overall_status = "MONITORING"

                # 5. LOG to file (append)
                if repair_needed:
                    self._persist_log()

            except asyncio.CancelledError:
                logger.info("[ARDE] Loop cancelled — shutting down cleanly")
                break
            except Exception as e:
                logger.error(f"[ARDE] Loop error: {e}\n{traceback.format_exc()}")

            await asyncio.sleep(self._effective_check_interval)

        self._state.running = False
        logger.info("[ARDE] Autonomous repair loop exited")

    # ── DIAGNOSTIC CHECKS ──

    def _check_alan(self) -> Dict[str, str]:
        """Check if Alan (AgentAlanBusinessAI) is alive and responsive."""
        if not self._relay:
            return {"status": "critical", "detail": "relay_server not attached"}
        agent = getattr(self._relay, "shared_agent_instance", None)
        if agent is None:
            return {"status": "critical", "detail": "shared_agent_instance is None"}
        # Verify agent has core methods
        if not hasattr(agent, "build_llm_prompt"):
            return {"status": "degraded", "detail": "build_llm_prompt missing"}
        if not hasattr(agent, "system_prompt"):
            return {"status": "degraded", "detail": "system_prompt missing"}
        return {"status": "ok", "detail": "Alan AI operational"}

    def _check_agent_x(self) -> Dict[str, str]:
        """Check if Agent X Conversation Support is alive."""
        if not self._relay:
            return {"status": "critical", "detail": "relay_server not attached"}
        support = getattr(self._relay, "agent_x_support", None)
        if support is None:
            return {"status": "critical", "detail": "agent_x_support is None"}
        # Verify critical capabilities
        if not hasattr(support, "process_turn"):
            return {"status": "degraded", "detail": "process_turn missing"}
        if not hasattr(support, "_apply_prompt_velocity"):
            return {"status": "degraded", "detail": "PVE not wired"}
        return {"status": "ok", "detail": "Agent X operational"}

    def _check_tts(self) -> Dict[str, str]:
        """Check TTS client availability."""
        if not self._relay:
            return {"status": "critical", "detail": "relay_server not attached"}
        tts = getattr(self._relay, "tts_client", None)
        if tts is None:
            return {"status": "critical", "detail": "tts_client is None — voice is muted"}
        return {"status": "ok", "detail": "TTS client ready"}

    def _check_greeting_cache(self) -> Dict[str, str]:
        """Check pre-cached greeting audio."""
        if not self._relay:
            return {"status": "degraded", "detail": "relay_server not attached"}
        cache = getattr(self._relay, "greeting_cache", {})
        count = len(cache)
        if count == 0:
            return {"status": "degraded", "detail": "greeting_cache empty — first-call latency risk"}
        if count < 3:
            return {"status": "warning", "detail": f"greeting_cache partial ({count} entries)"}
        return {"status": "ok", "detail": f"greeting_cache ready ({count} entries)"}

    def _check_tunnel(self) -> Dict[str, str]:
        """Check tunnel URL file exists and looks valid."""
        try:
            tunnel_file = Path("active_tunnel_url.txt")
            if not tunnel_file.exists():
                return {"status": "degraded", "detail": "active_tunnel_url.txt missing"}
            url = tunnel_file.read_text().strip()
            if not url or len(url) < 10:
                return {"status": "degraded", "detail": "tunnel URL empty or too short"}
            if not url.startswith("http"):
                # URL without scheme is valid — it gets prefixed at use time
                return {"status": "ok", "detail": f"tunnel URL loaded (no scheme): {url[:40]}"}
            return {"status": "ok", "detail": f"tunnel URL loaded ({url[:40]}...)"}
        except Exception as e:
            return {"status": "degraded", "detail": f"tunnel check error: {str(e)[:60]}"}

    def _check_twilio(self) -> Dict[str, str]:
        """Check Twilio credentials are present."""
        sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        phone = os.environ.get("TWILIO_PHONE_NUMBER", "")
        missing = []
        if not sid or len(sid) < 10:
            missing.append("TWILIO_ACCOUNT_SID")
        if not token or len(token) < 10:
            missing.append("TWILIO_AUTH_TOKEN")
        if not phone:
            missing.append("TWILIO_PHONE_NUMBER")
        if missing:
            return {"status": "degraded", "detail": f"missing: {', '.join(missing)}"}
        return {"status": "ok", "detail": "Twilio credentials present"}

    def _check_openai(self) -> Dict[str, str]:
        """Check OpenAI API key presence."""
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key or len(key) < 10:
            # Try config file fallback
            try:
                with open("agent_alan_config.json", "r") as f:
                    cfg_key = json.load(f).get("openai_api_key", "")
                if cfg_key and len(cfg_key) > 10:
                    return {"status": "ok", "detail": "OpenAI key from config file"}
            except Exception:
                pass
            return {"status": "degraded", "detail": "OPENAI_API_KEY missing"}
        return {"status": "ok", "detail": "OpenAI key present"}

    # ── REPAIR ACTIONS ──

    async def _attempt_repair(self, subsystem: str, check_result: Dict):
        """Attempt autonomous repair for a degraded subsystem."""
        now = time.time()

        # Check cooldown (VIP-adaptive)
        cooldown = self._effective_repair_cooldown
        last_attempt = self._last_repair_time.get(subsystem, 0)
        if now - last_attempt < cooldown:
            remaining = int(cooldown - (now - last_attempt))
            logger.info(f"[ARDE] Repair cooldown for {subsystem}: {remaining}s remaining")
            return

        # Check max attempts (VIP-adaptive)
        max_attempts = self._effective_max_attempts
        consec = self._state.consecutive_failures.get(subsystem, 0)
        if consec >= max_attempts:
            logger.error(f"[ARDE] {subsystem}: MAX REPAIR ATTEMPTS ({max_attempts}) reached — CRITICAL ALERT")
            self._state.subsystem_health[subsystem] = "critical"
            # Report to supervisor
            if self._supervisor:
                self._supervisor.report_incident(
                    component=f"ARDE_{subsystem.upper()}",
                    severity="critical",
                    issue=f"Autonomous repair failed after {max_attempts} attempts",
                    reason=check_result.get("detail", "unknown"),
                    fix="Manual intervention required — check logs/arde_repair_log.json",
                )
            return

        self._last_repair_time[subsystem] = now
        start = time.time()
        success = False
        detail = ""

        try:
            if subsystem == "alan":
                success, detail = await self._repair_alan()
            elif subsystem == "agent_x":
                success, detail = await self._repair_agent_x()
            elif subsystem == "tts":
                success, detail = await self._repair_tts()
            elif subsystem == "greeting_cache":
                success, detail = await self._repair_greeting_cache()
            elif subsystem == "tunnel":
                success, detail = await self._repair_tunnel()
            else:
                detail = f"No repair handler for {subsystem}"
                logger.warning(f"[ARDE] {detail}")
        except Exception as e:
            detail = f"Repair exception: {str(e)[:100]}"
            logger.error(f"[ARDE] Repair {subsystem} failed: {e}\n{traceback.format_exc()}")

        elapsed = (time.time() - start) * 1000

        # Record event
        event = RepairEvent(
            timestamp=datetime.now().isoformat(),
            subsystem=subsystem,
            action=f"repair_{subsystem}",
            success=success,
            detail=detail,
            duration_ms=round(elapsed, 1),
        )
        self._state.repair_history.append(asdict(event))
        if len(self._state.repair_history) > self.HISTORY_CAP:
            self._state.repair_history = self._state.repair_history[-self.HISTORY_CAP:]

        # Update consecutive failure counter
        if success:
            self._state.consecutive_failures[subsystem] = 0
            self._state.subsystem_health[subsystem] = "ok"
            logger.info(f"[ARDE] ✅ REPAIR SUCCESS: {subsystem} — {detail} ({elapsed:.0f}ms)")
            # Report recovery to supervisor
            if self._supervisor:
                self._supervisor.report_incident(
                    component=f"ARDE_{subsystem.upper()}",
                    severity="info",
                    issue=f"Autonomous repair succeeded for {subsystem}",
                    reason=detail,
                    fix="No action needed — self-healed",
                )
        else:
            self._state.consecutive_failures[subsystem] = consec + 1
            logger.warning(f"[ARDE] ❌ REPAIR FAILED: {subsystem} — {detail} (attempt {consec + 1}/{max_attempts})")

    async def _repair_alan(self) -> tuple:
        """Attempt to re-initialize AgentAlanBusinessAI."""
        if not self._relay:
            return False, "No relay server to repair Alan into"
        try:
            from agent_alan_business_ai import AgentAlanBusinessAI
            logger.info("[ARDE] Attempting Alan re-initialization...")
            new_alan = AgentAlanBusinessAI()
            self._relay.shared_agent_instance = new_alan
            # Verify
            if self._relay.shared_agent_instance is not None and hasattr(new_alan, "build_llm_prompt"):
                return True, "Alan re-initialized successfully"
            return False, "Alan instance created but missing expected methods"
        except Exception as e:
            return False, f"Alan re-init failed: {str(e)[:100]}"

    async def _repair_agent_x(self) -> tuple:
        """Attempt to re-initialize AgentXConversationSupport."""
        if not self._relay:
            return False, "No relay server to repair Agent X into"
        try:
            from agent_x_conversation_support import AgentXConversationSupport
            rapport = getattr(self._relay, "rapport_layer", {})
            base_dir = os.path.dirname(os.path.abspath(__file__))
            logger.info("[ARDE] Attempting Agent X re-initialization...")
            new_x = AgentXConversationSupport(rapport, base_dir=base_dir)
            self._relay.agent_x_support = new_x
            # Verify
            if self._relay.agent_x_support is not None and hasattr(new_x, "process_turn"):
                return True, "Agent X re-initialized successfully"
            return False, "Agent X instance created but missing expected methods"
        except Exception as e:
            return False, f"Agent X re-init failed: {str(e)[:100]}"

    async def _repair_tts(self) -> tuple:
        """Attempt to reconnect OpenAI TTS client."""
        if not self._relay:
            return False, "No relay server"
        try:
            from openai import OpenAI as OpenAIClient
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                try:
                    with open("agent_alan_config.json", "r") as f:
                        openai_key = json.load(f).get("openai_api_key")
                except Exception:
                    pass
            if not openai_key:
                return False, "No OpenAI API key available for TTS reconnect"
            self._relay.tts_client = OpenAIClient(api_key=openai_key, base_url="https://api.openai.com/v1")
            return True, "TTS client reconnected"
        except Exception as e:
            return False, f"TTS reconnect failed: {str(e)[:100]}"

    async def _repair_greeting_cache(self) -> tuple:
        """Attempt to rebuild greeting cache."""
        if not self._relay:
            return False, "No relay server"
        try:
            if not self._relay.tts_client:
                # Try to fix TTS first
                tts_ok, tts_detail = await self._repair_tts()
                if not tts_ok:
                    return False, f"Cannot rebuild greetings — TTS unavailable: {tts_detail}"
            logger.info("[ARDE] Rebuilding greeting cache...")
            self._relay._precache_greetings()
            count = len(getattr(self._relay, "greeting_cache", {}))
            if count > 0:
                return True, f"Greeting cache rebuilt ({count} entries)"
            return False, "Greeting cache still empty after rebuild"
        except Exception as e:
            return False, f"Greeting cache rebuild failed: {str(e)[:100]}"

    async def _repair_tunnel(self) -> tuple:
        """Check and sync tunnel URL."""
        try:
            # Try dynamic sync if available
            try:
                from tunnel_sync import tunnel_full_sync, get_current_tunnel_url
                result = tunnel_full_sync(force=True)
                return True, f"Tunnel resynced: {result}"
            except ImportError:
                pass

            # Fallback: check if fixed URL exists
            fixed = Path("active_tunnel_url_fixed.txt")
            active = Path("active_tunnel_url.txt")
            if fixed.exists() and not active.exists():
                import shutil
                shutil.copy2(str(fixed), str(active))
                return True, "Copied active_tunnel_url_fixed.txt to active_tunnel_url.txt"

            if active.exists():
                url = active.read_text().strip()
                if url and len(url) > 10:
                    return True, f"Tunnel URL present: {url[:40]}"

            return False, "No tunnel URL file found and tunnel_sync module unavailable"
        except Exception as e:
            return False, f"Tunnel repair failed: {str(e)[:100]}"

    # ── PERSISTENCE ──

    def _persist_log(self):
        """Append recent repair history to disk log."""
        try:
            log_path = Path(self.LOG_FILE)
            existing = []
            if log_path.exists():
                try:
                    existing = json.loads(log_path.read_text())
                except Exception:
                    existing = []
            existing.extend(self._state.repair_history[-10:])  # Last 10 events
            # Cap file at 500 entries
            if len(existing) > 500:
                existing = existing[-500:]
            log_path.write_text(json.dumps(existing, indent=2, default=str))
        except Exception as e:
            logger.error(f"[ARDE] Failed to persist log: {e}")

    # ── DEEP DIAGNOSTIC (On-demand comprehensive check) ──

    def deep_diagnostic(self) -> Dict[str, Any]:
        """
        Comprehensive diagnostic — more thorough than force_diagnostic.
        Checks internal state of both AI subsystems.
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "engine_state": self.snapshot(),
            "subsystem_checks": self.force_diagnostic(),
        }

        # Alan deep probe
        alan_deep = {"status": "unknown"}
        if self._relay and self._relay.shared_agent_instance:
            agent = self._relay.shared_agent_instance
            alan_deep = {
                "status": "operational",
                "has_system_prompt": hasattr(agent, "system_prompt") and bool(getattr(agent, "system_prompt", "")),
                "has_build_llm_prompt": hasattr(agent, "build_llm_prompt"),
                "has_config": hasattr(agent, "config") and bool(getattr(agent, "config", {})),
                "model": getattr(agent, "model", "unknown"),
                "max_tokens": getattr(agent, "max_tokens", "unknown"),
            }
        else:
            alan_deep = {"status": "OFFLINE", "detail": "No agent instance"}
        report["alan_deep"] = alan_deep

        # Agent X deep probe
        x_deep = {"status": "unknown"}
        if self._relay and self._relay.agent_x_support:
            support = self._relay.agent_x_support
            x_deep = {
                "status": "operational",
                "has_process_turn": hasattr(support, "process_turn"),
                "has_pve": hasattr(support, "_apply_prompt_velocity"),
                "has_priority_dispatch": hasattr(support, "priority_dispatch"),
                "has_mannerism_advisory": hasattr(support, "_mannerism_advisory"),
                "iq_cores_loaded": hasattr(support, "iq_cores") and bool(getattr(support, "iq_cores", {})),
                "rapport_loaded": hasattr(support, "rapport_layer") and bool(getattr(support, "rapport_layer", {})),
            }
        else:
            x_deep = {"status": "OFFLINE", "detail": "No Agent X support instance"}
        report["agent_x_deep"] = x_deep

        # Relay server internals
        relay_deep = {"status": "unknown"}
        if self._relay:
            relay_deep = {
                "status": "operational",
                "active_conversations": len(getattr(self._relay, "active_conversations", {})),
                "greeting_cache_count": len(getattr(self._relay, "greeting_cache", {})),
                "has_predictive_engine": hasattr(self._relay, "predictive_engine") and self._relay.predictive_engine is not None,
                "has_closing_engine": hasattr(self._relay, "closing_engine") and self._relay.closing_engine is not None,
                "has_master_closer": hasattr(self._relay, "master_closer") and self._relay.master_closer is not None,
                "has_behavior_engine": hasattr(self._relay, "behavior_engine") and self._relay.behavior_engine is not None,
                "has_crg": hasattr(self._relay, "crg") and self._relay.crg is not None,
                "has_evolution": hasattr(self._relay, "evolution") and self._relay.evolution is not None,
                "has_coordinator": hasattr(self._relay, "coordinator") and self._relay.coordinator is not None,
                "tts_voice": getattr(self._relay, "_tts_voice", "unknown"),
                "tts_model": getattr(self._relay, "_tts_model", "unknown"),
            }
        else:
            relay_deep = {"status": "OFFLINE", "detail": "Relay server not initialized"}
        report["relay_deep"] = relay_deep

        # Overall verdict
        all_ok = (
            alan_deep.get("status") == "operational"
            and x_deep.get("status") == "operational"
            and relay_deep.get("status") == "operational"
            and report["subsystem_checks"].get("overall") == "ALL_SYSTEMS_GO"
        )
        report["verdict"] = "ALL_SYSTEMS_GO" if all_ok else "ISSUES_DETECTED"

        return report
