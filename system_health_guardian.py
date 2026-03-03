"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   SYSTEM HEALTH GUARDIAN                                                    ║
║   AQI Agent Alan — Permanent Self-Healing Infrastructure                    ║
║                                                                             ║
║   PURPOSE:                                                                  ║
║   This module fills every gap in Alan's health monitoring stack.             ║
║   ARDE monitors 7 subsystems (alan, agent_x, tts, greeting_cache,          ║
║   tunnel, twilio, openai) at the COMPONENT level.                          ║
║   This Guardian operates at the INFRASTRUCTURE level — the layer            ║
║   beneath and around those components that ARDE cannot see.                 ║
║                                                                             ║
║   PHILOSOPHY (Tim's Directive):                                             ║
║   "Perfection = Revenue = Advancements Shared with AI = AI becomes          ║
║    accepted as a safe intelligence globally. Co-Existence Occurs."          ║
║                                                                             ║
║   WHAT THIS MONITORS (ARDE's blind spots):                                 ║
║   1. Tunnel STALENESS — not just "file exists" but live HTTP reachability   ║
║   2. Tunnel EXPIRATION — detect Cloudflare quick tunnel rotation           ║
║   3. Credential LIVENESS — actual API calls, not just env var checks       ║
║   4. Disk space — committed to Supervisor but never called                 ║
║   5. Memory pressure — committed to Supervisor but never called            ║
║   6. Log rotation — warns at 10MB but never rotates                        ║
║   7. Database integrity — call_capture.db, leads.db, CCNM stores          ║
║   8. WebSocket staleness — detect zombie relay connections                 ║
║   9. Process-level heartbeat — survive even if the event loop stalls       ║
║  10. Upstream/downstream cascade checks                                    ║
║                                                                             ║
║   DESIGN:                                                                   ║
║   - Runs as an async background task inside control_api_fixed.py lifespan  ║
║   - 30-second cycle: fast checks every pass, deep checks every 5th pass   ║
║   - Self-repairs what it can, escalates what it can't                      ║
║   - Reports ALL findings into Supervisor (single source of truth)          ║
║   - Exposes /guardian/status API endpoint                                   ║
║   - Writes guardian_heartbeat.json for external process monitors           ║
║                                                                             ║
║   UPSTREAM/DOWNSTREAM VALIDATION:                                          ║
║   Every check validates its dependencies (upstream) and dependents         ║
║   (downstream). If tunnel is dead → Twilio webhooks are broken →           ║
║   calls can't connect → campaign is useless. Guardian traces this          ║
║   full chain and reports it.                                               ║
║                                                                             ║
║   LINEAGE: Built 2026-02-17 to address 12+ gaps found in ARDE,            ║
║   tunnel_sync, start_alan_forever.ps1, self-health monitor, and            ║
║   all watchdog subsystems.                                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import logging
import os
import shutil
import sqlite3
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("GUARDIAN")

# ──────────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Thresholds
TUNNEL_REACHABILITY_TIMEOUT = 8       # seconds — HTTP GET to tunnel/health
DISK_WARNING_THRESHOLD_MB = 500       # warn if < 500 MB free
DISK_CRITICAL_THRESHOLD_MB = 100      # critical if < 100 MB free
LOG_MAX_SIZE_MB = 10                  # rotate logs above this size
LOG_ARCHIVE_KEEP = 5                  # keep last N archived logs
MEMORY_WARNING_PERCENT = 85           # warn above this %
MEMORY_CRITICAL_PERCENT = 95          # critical above this %
DB_INTEGRITY_CHECK_INTERVAL = 300     # full integrity every 5 min
HEARTBEAT_FILE = BASE_DIR / "guardian_heartbeat.json"
GUARDIAN_LOG_FILE = LOGS_DIR / "guardian_events.json"
CYCLE_INTERVAL = 30                   # seconds between fast checks
DEEP_CYCLE_EVERY = 5                  # deep check every Nth cycle

# Log files to monitor and rotate
MONITORED_LOGS = [
    "logs/control_api.log",
    "logs/server_stderr.log",
    "logs/server_stderr2.log",
    "logs/server_stdout.log",
    "logs/server_stdout2.log",
    "logs/cloudflare_tunnel.log",
    "logs/tunnel_output.log",
]


# ──────────────────────────────────────────────────────────────────
#  CASCADE CHAIN — UPSTREAM/DOWNSTREAM DEPENDENCY MAP
# ──────────────────────────────────────────────────────────────────

DEPENDENCY_MAP = {
    "tunnel": {
        "upstream": ["cloudflared_process", "internet"],
        "downstream": ["twilio_webhooks", "inbound_calls", "campaign"],
    },
    "twilio_webhooks": {
        "upstream": ["tunnel", "twilio_credentials"],
        "downstream": ["inbound_calls", "outbound_calls", "campaign"],
    },
    "twilio_credentials": {
        "upstream": ["env_file", "dotenv_loader"],
        "downstream": ["twilio_webhooks", "outbound_calls", "campaign"],
    },
    "openai_api": {
        "upstream": ["openai_api_key", "internet"],
        "downstream": ["tts", "llm", "stt_fallback"],
    },
    "groq_api": {
        "upstream": ["groq_api_key", "internet"],
        "downstream": ["stt_primary"],
    },
    "database": {
        "upstream": ["disk_space", "file_system"],
        "downstream": ["call_capture", "leads", "ccnm", "campaign"],
    },
    "campaign": {
        "upstream": ["tunnel", "twilio_credentials", "database", "governor"],
        "downstream": ["outbound_calls", "revenue"],
    },
}


# ──────────────────────────────────────────────────────────────────
#  GUARDIAN STATE
# ──────────────────────────────────────────────────────────────────

class GuardianState:
    """Tracks the complete state of the Guardian."""

    def __init__(self):
        self.running = False
        self.cycle_count = 0
        self.last_cycle_ts = ""
        self.last_deep_cycle_ts = ""
        self.started_at = ""
        self.checks: Dict[str, Dict[str, Any]] = {}
        self.cascade_alerts: List[Dict[str, Any]] = []
        self.repairs: List[Dict[str, Any]] = []
        self.overall_status = "INITIALIZING"

    def snapshot(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "cycle_count": self.cycle_count,
            "last_cycle": self.last_cycle_ts,
            "last_deep_cycle": self.last_deep_cycle_ts,
            "started_at": self.started_at,
            "overall_status": self.overall_status,
            "checks": dict(self.checks),
            "cascade_alerts": self.cascade_alerts[-20:],  # last 20
            "repairs": self.repairs[-20:],
        }


# ──────────────────────────────────────────────────────────────────
#  SYSTEM HEALTH GUARDIAN
# ──────────────────────────────────────────────────────────────────

class SystemHealthGuardian:
    """
    Permanent infrastructure-level health monitor.

    Fills every gap that ARDE and the self-health monitor miss.
    Runs as an async background task. Reports into Supervisor.
    """

    def __init__(self, supervisor=None, relay_server=None):
        self._supervisor = supervisor
        self._relay = relay_server
        self._state = GuardianState()
        self._task: Optional[asyncio.Task] = None
        self._last_tunnel_url = ""
        self._tunnel_fail_streak = 0
        self._last_deep_cycle = 0
        self._event_log: List[Dict] = []

        # Ensure directories
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # ── ATTACHMENT API ──

    def attach_supervisor(self, supervisor):
        self._supervisor = supervisor

    def attach_relay(self, relay_server):
        self._relay = relay_server

    # ── LIFECYCLE ──

    def start(self) -> asyncio.Task:
        if self._state.running:
            logger.warning("[GUARDIAN] Already running")
            return self._task
        self._state.running = True
        self._state.started_at = datetime.now().isoformat()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("[GUARDIAN] System Health Guardian started — 30s cycle, deep every 5th")
        return self._task

    def stop(self):
        self._state.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("[GUARDIAN] Stopped")

    def snapshot(self) -> Dict[str, Any]:
        return self._state.snapshot()

    # ── MAIN LOOP ──

    async def _run_loop(self):
        logger.info("[GUARDIAN] Entering guardian loop")
        while self._state.running:
            try:
                self._state.cycle_count += 1
                self._state.last_cycle_ts = datetime.now().isoformat()
                is_deep = (self._state.cycle_count % DEEP_CYCLE_EVERY == 0)

                if is_deep:
                    self._state.last_deep_cycle_ts = datetime.now().isoformat()

                # ── FAST CHECKS (every cycle) ──
                await self._check_tunnel_liveness()
                self._check_disk_space()
                self._check_memory()
                self._check_log_sizes()
                self._write_heartbeat()

                # ── DEEP CHECKS (every 5th cycle = ~2.5 min) ──
                if is_deep:
                    await self._check_credential_liveness()
                    self._check_database_integrity()
                    self._check_websocket_staleness()
                    await self._check_webhook_reachability()
                    self._run_cascade_analysis()

                # ── OVERALL STATUS ──
                self._compute_overall()

                # ── REPORT TO SUPERVISOR ──
                self._report_to_supervisor()

                # ── PERSIST EVENT LOG ──
                if is_deep:
                    self._persist_events()

            except asyncio.CancelledError:
                logger.info("[GUARDIAN] Loop cancelled")
                break
            except Exception as e:
                logger.error(f"[GUARDIAN] Loop error: {e}\n{traceback.format_exc()}")

            await asyncio.sleep(CYCLE_INTERVAL)

        self._state.running = False
        logger.info("[GUARDIAN] Loop exited")

    # ══════════════════════════════════════════════════════════════
    #  FAST CHECKS
    # ══════════════════════════════════════════════════════════════

    async def _check_tunnel_liveness(self):
        """
        Not just "does the file exist" (ARDE does that).
        Actually HTTP GET the tunnel URL and confirm 200 from /health.
        Detect staleness AND expiration.
        """
        check = {"status": "unknown", "detail": "", "ts": datetime.now().isoformat()}
        try:
            # Read tunnel URL
            tunnel_url = ""
            tunnel_file = BASE_DIR / "active_tunnel_url.txt"
            if tunnel_file.exists():
                raw = tunnel_file.read_text().strip()
                if not raw.startswith("http"):
                    raw = f"https://{raw}"
                tunnel_url = raw

            if not tunnel_url:
                check["status"] = "critical"
                check["detail"] = "No tunnel URL file"
                self._tunnel_fail_streak += 1
                self._state.checks["tunnel_live"] = check
                return

            # HTTP reachability check
            import httpx
            try:
                async with httpx.AsyncClient(timeout=TUNNEL_REACHABILITY_TIMEOUT, verify=False) as client:
                    r = await client.get(f"{tunnel_url}/health")
                    if r.status_code == 200:
                        check["status"] = "ok"
                        check["detail"] = f"Tunnel reachable ({tunnel_url[:50]})"
                        self._tunnel_fail_streak = 0

                        # Detect URL change (rotation)
                        if self._last_tunnel_url and tunnel_url != self._last_tunnel_url:
                            self._log_event("tunnel_rotated", f"URL changed: {self._last_tunnel_url[:40]} -> {tunnel_url[:40]}")
                            # Auto-sync Twilio webhooks on rotation
                            await self._auto_sync_tunnel(tunnel_url)

                        self._last_tunnel_url = tunnel_url
                    elif r.status_code == 530:
                        # Cloudflare Error 1016 — origin DNS resolution failure
                        check["status"] = "critical"
                        check["detail"] = f"Tunnel STALE (Error 1016/530) — needs restart"
                        self._tunnel_fail_streak += 1
                    else:
                        check["status"] = "degraded"
                        check["detail"] = f"Tunnel returned {r.status_code}"
                        self._tunnel_fail_streak += 1
            except httpx.ConnectError:
                check["status"] = "critical"
                check["detail"] = "Tunnel UNREACHABLE — connection refused"
                self._tunnel_fail_streak += 1
            except httpx.TimeoutException:
                check["status"] = "degraded"
                check["detail"] = f"Tunnel timeout ({TUNNEL_REACHABILITY_TIMEOUT}s)"
                self._tunnel_fail_streak += 1
            except Exception as e:
                check["status"] = "degraded"
                check["detail"] = f"HTTP error: {str(e)[:80]}"
                self._tunnel_fail_streak += 1

            # Auto-repair: if tunnel fails 3+ times, attempt tunnel restart
            if self._tunnel_fail_streak >= 3:
                await self._repair_tunnel()

        except Exception as e:
            check["status"] = "error"
            check["detail"] = f"Check failed: {str(e)[:80]}"

        self._state.checks["tunnel_live"] = check

    def _check_disk_space(self):
        """Check free disk space where Alan lives."""
        check = {"status": "unknown", "detail": "", "ts": datetime.now().isoformat()}
        try:
            usage = shutil.disk_usage(str(BASE_DIR))
            free_mb = usage.free / (1024 * 1024)
            total_mb = usage.total / (1024 * 1024)
            used_pct = ((usage.total - usage.free) / usage.total) * 100

            if free_mb < DISK_CRITICAL_THRESHOLD_MB:
                check["status"] = "critical"
                check["detail"] = f"CRITICAL: {free_mb:.0f} MB free ({used_pct:.1f}% used)"
                # Emergency: rotate ALL logs immediately
                self._emergency_log_rotation()
            elif free_mb < DISK_WARNING_THRESHOLD_MB:
                check["status"] = "warning"
                check["detail"] = f"LOW: {free_mb:.0f} MB free ({used_pct:.1f}% used)"
            else:
                check["status"] = "ok"
                check["detail"] = f"{free_mb:.0f} MB free ({used_pct:.1f}% used)"

            check["free_mb"] = round(free_mb, 1)
            check["used_pct"] = round(used_pct, 1)

            # Report to Supervisor
            if self._supervisor:
                self._supervisor.disk_health(
                    ok=(check["status"] in ("ok", "warning")),
                    detail=check["detail"]
                )

        except Exception as e:
            check["status"] = "error"
            check["detail"] = f"Disk check failed: {str(e)[:60]}"

        self._state.checks["disk"] = check

    def _check_memory(self):
        """Check system memory usage."""
        check = {"status": "unknown", "detail": "", "ts": datetime.now().isoformat()}
        try:
            # Use os module — no psutil dependency
            # On Windows, use ctypes for memory info
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))

            used_pct = mem.dwMemoryLoad
            avail_mb = mem.ullAvailPhys / (1024 * 1024)
            total_mb = mem.ullTotalPhys / (1024 * 1024)

            if used_pct >= MEMORY_CRITICAL_PERCENT:
                check["status"] = "critical"
                check["detail"] = f"CRITICAL: {used_pct}% used ({avail_mb:.0f} MB free of {total_mb:.0f} MB)"
            elif used_pct >= MEMORY_WARNING_PERCENT:
                check["status"] = "warning"
                check["detail"] = f"HIGH: {used_pct}% used ({avail_mb:.0f} MB free)"
            else:
                check["status"] = "ok"
                check["detail"] = f"{used_pct}% used ({avail_mb:.0f} MB free)"

            check["used_pct"] = used_pct
            check["avail_mb"] = round(avail_mb, 1)

            # Report to Supervisor
            if self._supervisor:
                self._supervisor.memory_pressure(
                    ok=(check["status"] in ("ok", "warning")),
                    detail=check["detail"]
                )

        except Exception as e:
            check["status"] = "unknown"
            check["detail"] = f"Memory check unavailable: {str(e)[:60]}"

        self._state.checks["memory"] = check

    def _check_log_sizes(self):
        """Monitor log file sizes and auto-rotate when exceeding threshold."""
        check = {"status": "ok", "detail": "", "ts": datetime.now().isoformat()}
        rotated = []
        oversized = []

        for log_rel in MONITORED_LOGS:
            log_path = BASE_DIR / log_rel
            if not log_path.exists():
                continue
            size_mb = log_path.stat().st_size / (1024 * 1024)
            if size_mb > LOG_MAX_SIZE_MB:
                oversized.append(f"{log_rel}={size_mb:.1f}MB")
                # Auto-rotate
                if self._rotate_log(log_path):
                    rotated.append(log_rel)

        if oversized:
            check["status"] = "warning" if rotated else "degraded"
            check["detail"] = f"Oversized: {', '.join(oversized)}"
            if rotated:
                check["detail"] += f" | Rotated: {', '.join(rotated)}"
                self._log_event("log_rotation", f"Rotated {len(rotated)} logs: {', '.join(rotated)}")
        else:
            check["detail"] = "All logs within limits"

        self._state.checks["logs"] = check

    def _write_heartbeat(self):
        """Write heartbeat file for external process monitors."""
        try:
            heartbeat = {
                "timestamp": datetime.now().isoformat(),
                "cycle": self._state.cycle_count,
                "status": self._state.overall_status,
                "pid": os.getpid(),
            }
            HEARTBEAT_FILE.write_text(json.dumps(heartbeat, indent=2))
        except Exception:
            pass  # Heartbeat is best-effort

    # ══════════════════════════════════════════════════════════════
    #  DEEP CHECKS (every 5th cycle ≈ 2.5 min)
    # ══════════════════════════════════════════════════════════════

    async def _check_credential_liveness(self):
        """
        Live API validation — not just "env var exists" but actual calls.
        Tests: OpenAI models list, Twilio account fetch, Groq connectivity.
        """
        checks = {}

        # ── OpenAI: List models (lightweight, proves key works) ──
        openai_check = {"status": "unknown", "detail": ""}
        try:
            import httpx
            key = os.environ.get("OPENAI_API_KEY", "")
            if not key:
                # Try config file
                try:
                    with open(BASE_DIR / "agent_alan_config.json", "r") as f:
                        key = json.load(f).get("openai_api_key", "")
                except Exception:
                    pass
            if key:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {key}"},
                    )
                    if r.status_code == 200:
                        openai_check = {"status": "ok", "detail": "API key valid (models endpoint 200)"}
                    elif r.status_code == 401:
                        openai_check = {"status": "critical", "detail": "API key INVALID (401 Unauthorized)"}
                    else:
                        openai_check = {"status": "warning", "detail": f"Unexpected status {r.status_code}"}
            else:
                openai_check = {"status": "critical", "detail": "No OpenAI API key found"}
        except Exception as e:
            openai_check = {"status": "degraded", "detail": f"API check failed: {str(e)[:60]}"}
        checks["openai_live"] = openai_check

        # ── Twilio: Fetch account (proves SID+token work) ──
        twilio_check = {"status": "unknown", "detail": ""}
        try:
            sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
            token = os.environ.get("TWILIO_AUTH_TOKEN", "")
            if sid and token:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.get(
                        f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
                        auth=(sid, token),
                    )
                    if r.status_code == 200:
                        acct = r.json()
                        twilio_check = {
                            "status": "ok",
                            "detail": f"Account {acct.get('friendly_name', 'OK')} (status={acct.get('status', 'active')})",
                        }
                    elif r.status_code == 401:
                        twilio_check = {"status": "critical", "detail": "Auth token INVALID (401)"}
                    else:
                        twilio_check = {"status": "warning", "detail": f"Unexpected status {r.status_code}"}
            else:
                twilio_check = {"status": "critical", "detail": "Twilio SID/token missing from env"}
        except Exception as e:
            twilio_check = {"status": "degraded", "detail": f"Twilio check failed: {str(e)[:60]}"}
        checks["twilio_live"] = twilio_check

        # ── Groq: Lightweight check ──
        groq_check = {"status": "unknown", "detail": ""}
        try:
            groq_key = os.environ.get("GROQ_API_KEY", "")
            if groq_key:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.get(
                        "https://api.groq.com/openai/v1/models",
                        headers={"Authorization": f"Bearer {groq_key}"},
                    )
                    if r.status_code == 200:
                        groq_check = {"status": "ok", "detail": "Groq API key valid"}
                    else:
                        groq_check = {"status": "warning", "detail": f"Groq returned {r.status_code}"}
            else:
                groq_check = {"status": "warning", "detail": "No Groq key — STT falls back to OpenAI Whisper"}
        except Exception as e:
            groq_check = {"status": "warning", "detail": f"Groq check failed: {str(e)[:60]}"}
        checks["groq_live"] = groq_check

        checks["ts"] = datetime.now().isoformat()
        self._state.checks["credentials"] = checks

    def _check_database_integrity(self):
        """Verify call_capture.db and leads.db are readable and not corrupted."""
        check = {"status": "ok", "detail": "", "ts": datetime.now().isoformat()}
        issues = []

        dbs = {
            "call_capture": DATA_DIR / "call_capture.db",
            "leads": DATA_DIR / "leads.db",
        }

        for name, db_path in dbs.items():
            if not db_path.exists():
                issues.append(f"{name}: MISSING")
                continue
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                result = cursor.execute("PRAGMA integrity_check").fetchone()
                if result[0] != "ok":
                    issues.append(f"{name}: INTEGRITY FAIL ({result[0]})")
                else:
                    # Check file size as bonus
                    size_mb = db_path.stat().st_size / (1024 * 1024)
                    if size_mb > 100:
                        issues.append(f"{name}: LARGE ({size_mb:.1f} MB)")
                conn.close()
            except Exception as e:
                issues.append(f"{name}: ERROR ({str(e)[:40]})")

        # Check CCNM persistence
        ccnm_dir = DATA_DIR / "ccnm"
        if ccnm_dir.exists():
            ccnm_files = list(ccnm_dir.glob("*.json"))
            check["ccnm_files"] = len(ccnm_files)

        if issues:
            check["status"] = "degraded"
            check["detail"] = "; ".join(issues)
        else:
            check["detail"] = f"All databases healthy ({len(dbs)} checked)"

        self._state.checks["database"] = check

    def _check_websocket_staleness(self):
        """Detect zombie WebSocket connections in the relay server."""
        check = {"status": "ok", "detail": "", "ts": datetime.now().isoformat()}
        try:
            if not self._relay:
                check["status"] = "unknown"
                check["detail"] = "Relay not attached"
                self._state.checks["websocket"] = check
                return

            active = getattr(self._relay, "active_conversations", {})
            stale = []
            now = time.time()

            for session_id, conv_data in active.items():
                # Check if connection has been idle too long
                last_activity = getattr(conv_data, "last_activity", None)
                if last_activity is None:
                    # Try alternate attribute names
                    last_activity = conv_data.get("last_activity", None) if isinstance(conv_data, dict) else None

                if last_activity and (now - last_activity) > 600:  # 10 min idle
                    stale.append(session_id)

            if stale:
                check["status"] = "warning"
                check["detail"] = f"{len(stale)} stale connections (idle >10min)"
                check["stale_sessions"] = stale
                # Don't auto-clean — let them timeout naturally
            else:
                check["detail"] = f"{len(active)} active connections, none stale"

            check["active_count"] = len(active)

        except Exception as e:
            check["status"] = "unknown"
            check["detail"] = f"WS check error: {str(e)[:60]}"

        self._state.checks["websocket"] = check

    async def _check_webhook_reachability(self):
        """
        Verify Twilio webhooks point to our live tunnel.
        This is the DOWNSTREAM check — tunnel is live, but are webhooks correct?
        """
        check = {"status": "unknown", "detail": "", "ts": datetime.now().isoformat()}
        try:
            sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
            token = os.environ.get("TWILIO_AUTH_TOKEN", "")
            if not sid or not token:
                check["status"] = "degraded"
                check["detail"] = "Cannot verify — missing Twilio creds"
                self._state.checks["webhooks"] = check
                return

            # Get our current tunnel URL
            tunnel_url = ""
            tunnel_file = BASE_DIR / "active_tunnel_url.txt"
            if tunnel_file.exists():
                raw = tunnel_file.read_text().strip()
                if not raw.startswith("http"):
                    raw = f"https://{raw}"
                tunnel_url = raw

            if not tunnel_url:
                check["status"] = "degraded"
                check["detail"] = "No tunnel URL to verify against"
                self._state.checks["webhooks"] = check
                return

            # Fetch Twilio phone number config
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers.json",
                    auth=(sid, token),
                )
                if r.status_code == 200:
                    numbers = r.json().get("incoming_phone_numbers", [])
                    mismatched = []
                    for num in numbers:
                        voice_url = num.get("voice_url", "")
                        expected_prefix = tunnel_url.rstrip("/")
                        if not voice_url.startswith(expected_prefix):
                            mismatched.append({
                                "phone": num.get("phone_number"),
                                "current_url": voice_url,
                                "expected_prefix": expected_prefix,
                            })

                    if mismatched:
                        check["status"] = "critical"
                        phones = [m["phone"] for m in mismatched]
                        check["detail"] = f"WEBHOOK MISMATCH: {', '.join(phones)} point to wrong tunnel"
                        check["mismatched"] = mismatched

                        # AUTO-REPAIR: Sync webhooks
                        try:
                            from tunnel_sync import update_twilio_webhooks
                            if update_twilio_webhooks(tunnel_url):
                                check["detail"] += " | AUTO-REPAIRED"
                                check["status"] = "repaired"
                                self._log_event("webhook_repair", f"Auto-synced webhooks to {tunnel_url[:50]}")
                                self._state.repairs.append({
                                    "ts": datetime.now().isoformat(),
                                    "what": "webhook_mismatch",
                                    "action": "auto_syncTunnel webhooks",
                                    "success": True,
                                })
                        except Exception as repair_err:
                            check["detail"] += f" | REPAIR FAILED: {str(repair_err)[:40]}"
                    else:
                        check["status"] = "ok"
                        check["detail"] = f"All {len(numbers)} phone numbers correctly pointed to tunnel"
                else:
                    check["status"] = "degraded"
                    check["detail"] = f"Twilio API returned {r.status_code}"

        except Exception as e:
            check["status"] = "error"
            check["detail"] = f"Webhook check failed: {str(e)[:60]}"

        self._state.checks["webhooks"] = check

    # ══════════════════════════════════════════════════════════════
    #  CASCADE ANALYSIS — UPSTREAM/DOWNSTREAM
    # ══════════════════════════════════════════════════════════════

    def _run_cascade_analysis(self):
        """
        Tim's directive: "Always look upstream and down for affected
        possibilities and those too need to be confirmed solid."

        For every failed check, trace the dependency chain and report
        what else is affected.
        """
        cascades = []
        failed_systems = set()

        # Identify failed systems from current checks
        for check_name, check_data in self._state.checks.items():
            status = check_data.get("status", "ok") if isinstance(check_data, dict) else "ok"
            if status in ("critical", "degraded", "error"):
                failed_systems.add(check_name)

        # Map check names to dependency keys
        check_to_dep = {
            "tunnel_live": "tunnel",
            "webhooks": "twilio_webhooks",
            "credentials": "twilio_credentials",
            "database": "database",
        }

        for check_name in failed_systems:
            dep_key = check_to_dep.get(check_name)
            if not dep_key or dep_key not in DEPENDENCY_MAP:
                continue

            deps = DEPENDENCY_MAP[dep_key]

            # UPSTREAM: What does this depend on?
            upstream_status = []
            for up in deps["upstream"]:
                # Check if upstream is also failing
                up_failing = up in failed_systems or any(
                    up in cn for cn in failed_systems
                )
                upstream_status.append({
                    "system": up,
                    "status": "FAILING" if up_failing else "assumed_ok",
                })

            # DOWNSTREAM: What does this affect?
            downstream_impact = []
            for down in deps["downstream"]:
                downstream_impact.append({
                    "system": down,
                    "impact": "BLOCKED" if dep_key in ("tunnel", "twilio_credentials") else "DEGRADED",
                })

            if downstream_impact:
                cascade = {
                    "ts": datetime.now().isoformat(),
                    "failed_system": dep_key,
                    "check_status": self._state.checks.get(check_name, {}).get("detail", ""),
                    "upstream": upstream_status,
                    "downstream_impact": downstream_impact,
                    "severity": "critical" if any(d["impact"] == "BLOCKED" for d in downstream_impact) else "warning",
                }
                cascades.append(cascade)
                logger.warning(
                    f"[GUARDIAN] CASCADE: {dep_key} failure → impacts {[d['system'] for d in downstream_impact]}"
                )

        self._state.cascade_alerts = cascades

    # ══════════════════════════════════════════════════════════════
    #  REPAIR ACTIONS
    # ══════════════════════════════════════════════════════════════

    async def _repair_tunnel(self):
        """Attempt tunnel repair when 3+ consecutive failures detected."""
        logger.warning(f"[GUARDIAN] Tunnel failed {self._tunnel_fail_streak}x — attempting repair")
        repair = {
            "ts": datetime.now().isoformat(),
            "what": "tunnel_stale",
            "action": "",
            "success": False,
        }

        try:
            # Strategy 1: Try tunnel_sync full_sync
            try:
                from tunnel_sync import full_sync
                result = full_sync(force=True)
                if result.get("status") == "synced":
                    repair["action"] = "tunnel_sync.full_sync(force=True)"
                    repair["success"] = True
                    self._tunnel_fail_streak = 0
                    self._log_event("tunnel_repair", f"Synced via tunnel_sync: {result}")
                    self._state.repairs.append(repair)
                    return
            except Exception:
                pass

            # Strategy 2: Check if tunnel_url_fixed has a different (newer) URL
            fixed_file = BASE_DIR / "active_tunnel_url_fixed.txt"
            active_file = BASE_DIR / "active_tunnel_url.txt"
            if fixed_file.exists() and active_file.exists():
                fixed_url = fixed_file.read_text().strip()
                active_url = active_file.read_text().strip()
                if fixed_url != active_url and fixed_url:
                    active_file.write_text(fixed_url)
                    repair["action"] = f"Copied fixed URL: {fixed_url[:40]}"
                    repair["success"] = True
                    self._tunnel_fail_streak = 0
                    self._log_event("tunnel_repair", repair["action"])
                    # Sync webhooks to new URL
                    await self._auto_sync_tunnel(f"https://{fixed_url}" if not fixed_url.startswith("http") else fixed_url)

            # Strategy 3: Log for operator intervention
            if not repair["success"]:
                repair["action"] = "OPERATOR INTERVENTION NEEDED — cloudflared may need restart"
                self._log_event("tunnel_repair_failed",
                    f"Tunnel unreachable after {self._tunnel_fail_streak} checks. "
                    "Cloudflared process may be dead or tunnel expired."
                )

                # Report to supervisor
                if self._supervisor:
                    self._supervisor.report_incident(
                        component="GUARDIAN_TUNNEL",
                        severity="critical",
                        issue=f"Tunnel unreachable ({self._tunnel_fail_streak} consecutive failures)",
                        reason="Cloudflare quick tunnel expired or cloudflared process died",
                        fix="Restart cloudflared: cloudflared tunnel --url http://localhost:8777",
                    )

        except Exception as e:
            repair["action"] = f"Repair exception: {str(e)[:80]}"

        self._state.repairs.append(repair)

    async def _auto_sync_tunnel(self, tunnel_url: str):
        """Sync Twilio webhooks when tunnel URL changes."""
        try:
            from tunnel_sync import update_twilio_webhooks
            success = update_twilio_webhooks(tunnel_url)
            if success:
                logger.info(f"[GUARDIAN] Auto-synced Twilio webhooks to {tunnel_url[:50]}")
            else:
                logger.warning("[GUARDIAN] Twilio webhook sync returned False")
        except Exception as e:
            logger.error(f"[GUARDIAN] Auto-sync failed: {e}")

    def _rotate_log(self, log_path: Path) -> bool:
        """Rotate a log file: compress old, truncate current."""
        try:
            archive_name = f"{log_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{log_path.suffix}"
            archive_path = log_path.parent / archive_name

            # Move current to archive
            shutil.copy2(str(log_path), str(archive_path))
            # Truncate original
            with open(log_path, "w") as f:
                f.write(f"[LOG ROTATED by Guardian at {datetime.now().isoformat()}]\n")

            # Clean old archives (keep last N)
            pattern = f"{log_path.stem}_*{log_path.suffix}"
            archives = sorted(log_path.parent.glob(pattern), key=lambda p: p.stat().st_mtime)
            if len(archives) > LOG_ARCHIVE_KEEP:
                for old in archives[:-LOG_ARCHIVE_KEEP]:
                    old.unlink()

            logger.info(f"[GUARDIAN] Rotated {log_path.name} -> {archive_name}")
            return True
        except Exception as e:
            logger.error(f"[GUARDIAN] Log rotation failed for {log_path}: {e}")
            return False

    def _emergency_log_rotation(self):
        """Emergency: rotate ALL logs when disk is critically low."""
        logger.warning("[GUARDIAN] EMERGENCY LOG ROTATION — disk critical")
        for log_rel in MONITORED_LOGS:
            log_path = BASE_DIR / log_rel
            if log_path.exists() and log_path.stat().st_size > 1024 * 1024:  # >1MB
                self._rotate_log(log_path)

    # ══════════════════════════════════════════════════════════════
    #  STATUS COMPUTATION & REPORTING
    # ══════════════════════════════════════════════════════════════

    def _compute_overall(self):
        """Compute overall Guardian status from all checks."""
        statuses = []
        for check_name, check_data in self._state.checks.items():
            if isinstance(check_data, dict):
                # Handle nested credential checks
                if check_name == "credentials":
                    for sub_name, sub_data in check_data.items():
                        if isinstance(sub_data, dict) and "status" in sub_data:
                            statuses.append(sub_data["status"])
                else:
                    s = check_data.get("status", "ok")
                    statuses.append(s)

        if not statuses:
            self._state.overall_status = "INITIALIZING"
        elif any(s == "critical" for s in statuses):
            self._state.overall_status = "CRITICAL"
        elif any(s in ("degraded", "error") for s in statuses):
            self._state.overall_status = "DEGRADED"
        elif any(s == "warning" for s in statuses):
            self._state.overall_status = "MONITORING"
        elif all(s in ("ok", "unknown", "repaired") for s in statuses):
            self._state.overall_status = "ALL_CLEAR"
        else:
            self._state.overall_status = "MONITORING"

    def _report_to_supervisor(self):
        """Push Guardian findings into the Supervisor health state."""
        if not self._supervisor:
            return
        try:
            # Update the supervisor's resource/network state
            guardian_summary = {
                "guardian_status": self._state.overall_status,
                "guardian_cycle": self._state.cycle_count,
                "tunnel_live": self._state.checks.get("tunnel_live", {}).get("status", "unknown"),
                "disk": self._state.checks.get("disk", {}).get("status", "unknown"),
                "memory": self._state.checks.get("memory", {}).get("status", "unknown"),
                "logs": self._state.checks.get("logs", {}).get("status", "unknown"),
                "database": self._state.checks.get("database", {}).get("status", "unknown"),
                "webhooks": self._state.checks.get("webhooks", {}).get("status", "unknown"),
                "cascade_alerts": len(self._state.cascade_alerts),
            }

            # Write into supervisor's health_state["network"] since Guardian
            # covers infrastructure that the network category was meant for
            if hasattr(self._supervisor, "health_state"):
                self._supervisor.health_state["network"] = {
                    "status": self._state.overall_status.lower(),
                    "guardian": guardian_summary,
                }

        except Exception as e:
            logger.error(f"[GUARDIAN] Supervisor report failed: {e}")

    # ══════════════════════════════════════════════════════════════
    #  EVENT LOGGING & PERSISTENCE
    # ══════════════════════════════════════════════════════════════

    def _log_event(self, event_type: str, detail: str):
        """Log a Guardian event."""
        event = {
            "ts": datetime.now().isoformat(),
            "type": event_type,
            "detail": detail,
        }
        self._event_log.append(event)
        if len(self._event_log) > 200:
            self._event_log = self._event_log[-200:]
        logger.info(f"[GUARDIAN] Event: {event_type} — {detail}")

    def _persist_events(self):
        """Write event log to disk."""
        try:
            existing = []
            if GUARDIAN_LOG_FILE.exists():
                try:
                    existing = json.loads(GUARDIAN_LOG_FILE.read_text())
                except Exception:
                    existing = []

            existing.extend(self._event_log)
            # Cap at 500 events
            if len(existing) > 500:
                existing = existing[-500:]

            GUARDIAN_LOG_FILE.write_text(json.dumps(existing, indent=2, default=str))
            self._event_log.clear()
        except Exception as e:
            logger.error(f"[GUARDIAN] Event persistence failed: {e}")


# ──────────────────────────────────────────────────────────────────
#  MODULE-LEVEL FACTORY
# ──────────────────────────────────────────────────────────────────

_guardian_instance: Optional[SystemHealthGuardian] = None


def get_guardian() -> Optional[SystemHealthGuardian]:
    """Get the singleton Guardian instance."""
    return _guardian_instance


def create_guardian(supervisor=None, relay_server=None) -> SystemHealthGuardian:
    """Create and return the Guardian singleton."""
    global _guardian_instance
    if _guardian_instance is None:
        _guardian_instance = SystemHealthGuardian(supervisor=supervisor, relay_server=relay_server)
    return _guardian_instance
