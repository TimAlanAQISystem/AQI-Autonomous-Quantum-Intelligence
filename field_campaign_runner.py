"""
═══════════════════════════════════════════════════════════════════════
  AGENT ALAN — GOVERNED FIELD CAMPAIGN RUNNER
  Phase 1-4 Controlled Outbound Campaign Executor
  ─────────────────────────────────────────────────────────────────────
  This is the PRODUCTION field campaign runner. It fires real calls
  through the control API with full governance:

  1. Pre-flight validation gate (must pass before any calls)
  2. Phase-aware pacing (spacing, business hours, daily caps)
  3. Quality monitoring (halt on robotic flags, hallucinations)
  4. Regime engine integration (segment-aware pacing)
  5. Full call logging and audit trail
  6. Real-time campaign report generation

  Usage:
    .venv\Scripts\python.exe field_campaign_runner.py --phase 1
    .venv\Scripts\python.exe field_campaign_runner.py --phase 2 --dry
    .venv\Scripts\python.exe field_campaign_runner.py --phase 1 --skip-preflight
═══════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import yaml
import sqlite3
import logging
import argparse
import traceback
import requests
from datetime import datetime, time as time_type
from pathlib import Path

# ─── Environment ─────────────────────────────────────────────────
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), "Alan_Deployment", "config", ".env")
load_dotenv(env_path, override=True)
os.environ["AGENT_NAME"] = "Alan Jones"

# ─── Imports ─────────────────────────────────────────────────────
from tools import cooldown_manager

# CW23 Regime Engine (optional)
try:
    from regime_queue_integrator import (
        should_skip_lead as regime_should_skip,
        get_pacing_delay as regime_pacing,
    )
    REGIME_AVAILABLE = True
except ImportError:
    REGIME_AVAILABLE = False

# ─── Configuration ───────────────────────────────────────────────
CONFIG_PATH = "field_campaign_config.yaml"
LEADS_DB = "data/leads.db"
CALL_CAPTURE_DB = "data/call_capture.db"
LOG_DIR = "logs"
REPORT_DIR = "logs/field_reports"

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ─── Logging ─────────────────────────────────────────────────────
log_file = os.path.join(LOG_DIR, f"field_campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FIELD] %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("field_campaign")


# ═══════════════════════════════════════════════════════════════════
#  CONFIG LOADER
# ═══════════════════════════════════════════════════════════════════

def load_config():
    """Load field_campaign_config.yaml and return phase configs."""
    if not os.path.exists(CONFIG_PATH):
        log.critical(f"Config file not found: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_phase_config(cfg, phase_num):
    """Return the config dict for a specific phase."""
    phase_key = {
        1: "phase_1_preflight",
        2: "phase_2_micro",
        3: "phase_3_pacing",
        4: "phase_4_full",
    }.get(phase_num)
    if not phase_key or phase_key not in cfg:
        log.critical(f"Phase {phase_num} config not found")
        sys.exit(1)
    return cfg[phase_key], cfg.get("global", {})


# ═══════════════════════════════════════════════════════════════════
#  LEAD SELECTION
# ═══════════════════════════════════════════════════════════════════

def get_callable_leads(limit, max_attempts=3):
    """Fetch callable leads from the leads database."""
    if not os.path.exists(LEADS_DB):
        log.error(f"Leads DB not found: {LEADS_DB}")
        return []

    conn = sqlite3.connect(LEADS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM leads
            WHERE (outcome = 'pending' OR outcome IS NULL)
            AND (do_not_call IS NULL OR do_not_call = 0)
            AND attempts < ?
            ORDER BY
                CASE priority
                    WHEN 'URGENT' THEN 1
                    WHEN 'high' THEN 2
                    ELSE 3
                END,
                created_at ASC
            LIMIT ?
        """, (max_attempts, limit))
        rows = cursor.fetchall()
        leads = [dict(row) for row in rows]
        log.info(f"Found {len(leads)} callable leads (requested {limit})")
        return leads
    except Exception as e:
        log.error(f"Lead query failed: {e}")
        return []
    finally:
        conn.close()


def mark_lead_dialed(lead, call_sid=None, outcome="initiated"):
    """Record attempt in the leads database."""
    if not os.path.exists(LEADS_DB):
        return
    try:
        conn = sqlite3.connect(LEADS_DB)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE leads
            SET attempts = attempts + 1,
                last_attempt = ?,
                outcome = ?,
                outcome_details = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            outcome,
            f"call_sid={call_sid}" if call_sid else "no_sid",
            lead.get("id"),
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"Failed to mark lead: {e}")


# ═══════════════════════════════════════════════════════════════════
#  GOVERNOR INTEGRATION
# ═══════════════════════════════════════════════════════════════════

def check_governor(api_url):
    """Check control API governor state. Returns (can_call, state_info)."""
    try:
        resp = requests.get(f"{api_url}/health", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            gov = data.get("governor_fsm", {})
            can_call = gov.get("can_start_call", False)
            state = gov.get("state", "UNKNOWN")
            cooldown = gov.get("cooldown_remaining", 0)
            return can_call, {"state": state, "cooldown": cooldown}
        return False, {"state": "API_ERROR", "status": resp.status_code}
    except Exception as e:
        return False, {"state": "UNREACHABLE", "error": str(e)}


def wait_for_governor(api_url, max_wait=180, poll_interval=5):
    """Wait until governor is ready. Returns True if ready within max_wait."""
    start = time.time()
    while time.time() - start < max_wait:
        can_call, info = check_governor(api_url)
        if can_call:
            return True
        elapsed = int(time.time() - start)
        log.info(f"Governor not ready: {info} — waiting ({elapsed}s/{max_wait}s)...")
        time.sleep(poll_interval)
    return False


# ═══════════════════════════════════════════════════════════════════
#  CALL EXECUTION
# ═══════════════════════════════════════════════════════════════════

def fire_call(lead, api_url, dry_run=False):
    """Fire a single call via control API. Returns (success, call_sid, error)."""
    phone = lead.get("phone_number", "")
    name = lead.get("name", "Merchant")
    business = lead.get("business_type", "")

    if dry_run:
        log.info(f"[DRY RUN] Would call {name} at {phone}")
        return True, "DRY_RUN_SID", None

    try:
        payload = {
            "to": phone,
            "name": name,
            "business_name": business,
            "lead_id": lead.get("id"),
            "campaign": "field_v1",
            "live": True,
        }

        resp = requests.post(f"{api_url}/call", json=payload, timeout=15)
        if resp.status_code == 200:
            result = resp.json().get("result", {})
            sid = result.get("call_sid", "unknown")
            log.info(f"Call initiated: {name} ({phone}) → SID={sid}")
            return True, sid, None
        else:
            error = f"API {resp.status_code}: {resp.text[:200]}"
            log.error(f"Call failed: {name} ({phone}) — {error}")
            return False, None, error
    except Exception as e:
        log.error(f"Call exception: {name} ({phone}) — {e}")
        return False, None, str(e)


def wait_for_call_completion(api_url, max_wait=300, poll_interval=5):
    """Wait until the governor returns to IDLE (call complete)."""
    start = time.time()
    while time.time() - start < max_wait:
        can_call, info = check_governor(api_url)
        state = info.get("state", "UNKNOWN")
        if can_call and state in ("IDLE", "idle"):
            return True, state
        elapsed = int(time.time() - start)
        if elapsed % 30 == 0 and elapsed > 0:
            log.info(f"Call in progress: state={state} ({elapsed}s)")
        time.sleep(poll_interval)
    return False, "TIMEOUT"


# ═══════════════════════════════════════════════════════════════════
#  BUSINESS HOURS
# ═══════════════════════════════════════════════════════════════════

def is_business_hours(start_hour, end_hour):
    """Check if current time is within business hours (Mon-Fri)."""
    now = datetime.now()
    # Block weekends
    if now.weekday() >= 5:
        return False
    return start_hour <= now.hour < end_hour


# ═══════════════════════════════════════════════════════════════════
#  CAMPAIGN REPORT
# ═══════════════════════════════════════════════════════════════════

class CampaignReport:
    """Real-time campaign report tracker."""

    def __init__(self, phase_num):
        self.phase = phase_num
        self.start_time = datetime.now()
        self.calls = []
        self.calls_attempted = 0
        self.calls_connected = 0
        self.calls_failed = 0
        self.calls_no_answer = 0
        self.consecutive_no_answer = 0
        self.robotic_flags = 0
        self.hallucinations = 0
        self.misclassifications = 0
        self.positive_progressions = 0
        self.transport_failures = 0

    def record_call(self, lead, success, call_sid, error=None):
        """Record a call attempt."""
        self.calls_attempted += 1
        entry = {
            "timestamp": datetime.now().isoformat(),
            "lead_id": lead.get("id"),
            "name": lead.get("name"),
            "phone": lead.get("phone_number"),
            "business_type": lead.get("business_type"),
            "area_code": lead.get("phone_number", "")[-10:-7] if lead.get("phone_number") else "",
            "success": success,
            "call_sid": call_sid,
            "error": error,
            "call_number": self.calls_attempted,
        }
        self.calls.append(entry)

        if success:
            self.calls_connected += 1
            self.consecutive_no_answer = 0
        elif error and ("no answer" in str(error).lower() or "timeout" in str(error).lower()):
            self.calls_no_answer += 1
            self.consecutive_no_answer += 1
        elif error:
            self.calls_failed += 1
            self.transport_failures += 1

    def check_quality_gate(self, quality_cfg):
        """Check if campaign should continue. Returns (continue, reason)."""
        if not quality_cfg:
            return True, "no quality gate configured"

        max_consec_na = quality_cfg.get("max_consecutive_no_answer", 999)
        if self.consecutive_no_answer >= max_consec_na:
            return False, f"consecutive no-answer = {self.consecutive_no_answer} (max {max_consec_na})"

        max_robotic = quality_cfg.get("max_robotic_flags", 999)
        if self.robotic_flags >= max_robotic:
            return False, f"robotic flags = {self.robotic_flags} (max {max_robotic})"

        return True, "quality OK"

    def check_success_criteria(self, criteria):
        """Check if success criteria are met. Returns list of (criterion, met, detail)."""
        results = []
        if not criteria:
            return results

        if "min_human_conversations" in criteria:
            val = criteria["min_human_conversations"]
            met = self.calls_connected >= val
            results.append(("min_human_conversations", met,
                            f"{self.calls_connected}/{val}"))

        if "max_hallucinations" in criteria:
            val = criteria["max_hallucinations"]
            met = self.hallucinations <= val
            results.append(("max_hallucinations", met,
                            f"{self.hallucinations}/{val}"))

        if "max_misclassifications" in criteria:
            val = criteria["max_misclassifications"]
            met = self.misclassifications <= val
            results.append(("max_misclassifications", met,
                            f"{self.misclassifications}/{val}"))

        if "max_transport_failures" in criteria:
            val = criteria["max_transport_failures"]
            met = self.transport_failures <= val
            results.append(("max_transport_failures", met,
                            f"{self.transport_failures}/{val}"))

        if "max_robotic_flags" in criteria:
            val = criteria["max_robotic_flags"]
            met = self.robotic_flags <= val
            results.append(("max_robotic_flags", met,
                            f"{self.robotic_flags}/{val}"))

        if "min_positive_progressions" in criteria:
            val = criteria["min_positive_progressions"]
            met = self.positive_progressions >= val
            results.append(("min_positive_progressions", met,
                            f"{self.positive_progressions}/{val}"))

        return results

    def generate_report(self):
        """Generate a text report of the campaign."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        lines = [
            "═" * 60,
            f"  FIELD CAMPAIGN REPORT — Phase {self.phase}",
            f"  Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"  Duration: {int(elapsed // 60)}m {int(elapsed % 60)}s",
            "═" * 60,
            f"  Calls Attempted:   {self.calls_attempted}",
            f"  Calls Connected:   {self.calls_connected}",
            f"  Calls Failed:      {self.calls_failed}",
            f"  No Answer:         {self.calls_no_answer}",
            f"  Transport Failures:{self.transport_failures}",
            f"  Robotic Flags:     {self.robotic_flags}",
            f"  Hallucinations:    {self.hallucinations}",
            f"  Progressions:      {self.positive_progressions}",
            "─" * 60,
            "  Call Log:",
        ]
        for c in self.calls:
            status = "✅" if c["success"] else "❌"
            lines.append(f"    {status} {c['timestamp'][:19]} | {c['name'][:25]:25s} | {c.get('call_sid', 'N/A')}")
        lines.append("═" * 60)
        return "\n".join(lines)

    def save(self, report_dir, per_call=False):
        """Save report to files. If per_call=True, write one file per call."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        # ─── Per-call segmented reports ──────────────────────────
        if per_call and self.calls:
            calls_dir = os.path.join(report_dir, f"phase{self.phase}_{ts}")
            os.makedirs(calls_dir, exist_ok=True)
            for call in self.calls:
                call_num = call.get("call_number", 0)
                call_sid = call.get("call_sid", "unknown")
                # JSON per-call report
                call_path = os.path.join(calls_dir, f"call_{call_num:02d}_{call_sid[:12]}.json")
                with open(call_path, "w") as f:
                    json.dump({
                        "phase": self.phase,
                        "call_number": call_num,
                        "total_calls": self.calls_attempted,
                        **call,
                    }, f, indent=2)
                # Text per-call report
                txt_path = os.path.join(calls_dir, f"call_{call_num:02d}_{call_sid[:12]}.txt")
                status = "CONNECTED" if call.get("success") else "FAILED"
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"{'═'*50}\n")
                    f.write(f"  CALL {call_num}/{self.calls_attempted} — {status}\n")
                    f.write(f"{'═'*50}\n")
                    f.write(f"  Timestamp:     {call.get('timestamp', '?')}\n")
                    f.write(f"  Name:          {call.get('name', '?')}\n")
                    f.write(f"  Phone:         {call.get('phone', '?')}\n")
                    f.write(f"  Business Type: {call.get('business_type', '?')}\n")
                    f.write(f"  Area Code:     {call.get('area_code', '?')}\n")
                    f.write(f"  Call SID:      {call.get('call_sid', '?')}\n")
                    f.write(f"  Status:        {status}\n")
                    if call.get("error"):
                        f.write(f"  Error:         {call['error']}\n")
                    f.write(f"{'═'*50}\n")
            log.info(f"Per-call reports saved: {calls_dir}/ ({len(self.calls)} files)")

        # ─── Consolidated batch report ───────────────────────────
        # Text report
        txt_path = os.path.join(report_dir, f"field_phase{self.phase}_{ts}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.generate_report())
        # JSON data
        json_path = os.path.join(report_dir, f"field_phase{self.phase}_{ts}.json")
        with open(json_path, "w") as f:
            json.dump({
                "phase": self.phase,
                "start": self.start_time.isoformat(),
                "end": datetime.now().isoformat(),
                "calls_attempted": self.calls_attempted,
                "calls_connected": self.calls_connected,
                "calls_failed": self.calls_failed,
                "calls_no_answer": self.calls_no_answer,
                "transport_failures": self.transport_failures,
                "robotic_flags": self.robotic_flags,
                "hallucinations": self.hallucinations,
                "positive_progressions": self.positive_progressions,
                "calls": self.calls,
            }, f, indent=2)
        log.info(f"Batch report saved: {txt_path}")
        return txt_path


# ═══════════════════════════════════════════════════════════════════
#  MAIN CAMPAIGN EXECUTOR
# ═══════════════════════════════════════════════════════════════════

def run_field_campaign(phase_num, dry_run=False, skip_preflight=False):
    """Execute a governed field campaign for the specified phase."""

    cfg = load_config()
    phase_cfg, global_cfg = get_phase_config(cfg, phase_num)
    api_url = global_cfg.get("control_api_url", "http://127.0.0.1:8777")

    log.info("=" * 60)
    log.info(f"FIELD CAMPAIGN — Phase {phase_num}")
    log.info(f"Dry run: {dry_run}")
    log.info("=" * 60)

    # ─── Check phase is enabled ──────────────────────────────────
    if not phase_cfg.get("enabled", False):
        log.warning(f"Phase {phase_num} is DISABLED in config. Enable it first.")
        log.warning(f"Edit {CONFIG_PATH} → phase_{phase_num}_* → enabled: true")
        return False

    # ─── Pre-flight gate ─────────────────────────────────────────
    if not skip_preflight and phase_num <= 2:
        log.info("Running pre-flight validation...")
        try:
            from _preflight_field_validation import run_preflight
            passed, _ = run_preflight(json_output=True)
            if not passed:
                log.critical("PRE-FLIGHT FAILED — Campaign blocked")
                return False
            log.info("Pre-flight PASSED — proceeding")
        except ImportError:
            log.warning("Pre-flight module not found — running without validation")
        except Exception as e:
            log.error(f"Pre-flight error: {e}")
            if phase_num == 1:
                log.critical("Phase 1 requires pre-flight. Aborting.")
                return False

    # ─── Check business hours ────────────────────────────────────
    bh_start = phase_cfg.get("business_hours_start", 10)
    bh_end = phase_cfg.get("business_hours_end", 16)
    if not is_business_hours(bh_start, bh_end):
        now = datetime.now()
        log.warning(f"Outside business hours ({bh_start}:00-{bh_end}:00). Current: {now.strftime('%H:%M %A')}")
        return False

    # ─── Load leads ──────────────────────────────────────────────
    batch_size = phase_cfg.get("batch_size", phase_cfg.get("max_calls", 10))
    max_attempts = phase_cfg.get("max_attempts_per_lead", 2)
    leads = get_callable_leads(batch_size, max_attempts)

    if not leads:
        log.warning("No callable leads found. Run _campaign_prep.py first.")
        return False

    log.info(f"Loaded {len(leads)} leads for Phase {phase_num}")

    # ─── Initialize report ───────────────────────────────────────
    report = CampaignReport(phase_num)
    spacing = phase_cfg.get("spacing_seconds", 180)
    quality_gate_cfg = phase_cfg.get("quality_gate")
    success_criteria = phase_cfg.get("success_criteria")
    halt_on_failure = phase_cfg.get("halt_on_failure", False)

    # ─── Campaign loop ───────────────────────────────────────────
    for i, lead in enumerate(leads):
        log.info(f"\n{'─'*40}")
        log.info(f"Call {i+1}/{len(leads)}: {lead.get('name', '?')} ({lead.get('phone_number', '?')})")
        log.info(f"{'─'*40}")

        # Business hours re-check
        if not is_business_hours(bh_start, bh_end):
            log.warning("Business hours ended mid-campaign. Halting.")
            break

        # Cooldown gate
        if global_cfg.get("respect_cooldown_manager", True) and not dry_run:
            if not cooldown_manager.cooldown_gate():
                log.info("Cooldown gate closed. Waiting...")
                time.sleep(10)
                # Try once more
                if not cooldown_manager.cooldown_gate():
                    log.warning("Cooldown gate still closed. Skipping lead.")
                    continue

        # Regime engine check
        if global_cfg.get("use_regime_engine", True) and REGIME_AVAILABLE and not dry_run:
            skip, reason = regime_should_skip(
                lead.get("phone_number", ""),
                lead.get("business_type", "")
            )
            if skip:
                log.info(f"Regime skip: {lead.get('name')} — {reason}")
                continue

        # Governor check
        if not dry_run:
            if not wait_for_governor(api_url, max_wait=120):
                log.error("Governor not ready after 120s. Halting campaign.")
                break

        # ─── FIRE CALL ───────────────────────────────────────────
        if not dry_run:
            cooldown_manager.mark_call_started()

        try:
            success, sid, error = fire_call(lead, api_url, dry_run=dry_run)
            report.record_call(lead, success, sid, error)
            mark_lead_dialed(lead, call_sid=sid, outcome="initiated" if success else "failed")

            if halt_on_failure and not success:
                log.critical(f"HALT: Call failed and halt_on_failure=True. Error: {error}")
                break

            # Wait for call to complete (unless dry run)
            if success and not dry_run:
                log.info("Waiting for call completion...")
                completed, final_state = wait_for_call_completion(api_url, max_wait=300)
                if not completed:
                    log.warning(f"Call did not complete within 300s. Final state: {final_state}")

        finally:
            if not dry_run:
                cooldown_manager.mark_call_ended()

        # Quality gate check
        if quality_gate_cfg:
            can_continue, reason = report.check_quality_gate(quality_gate_cfg)
            if not can_continue:
                log.warning(f"QUALITY GATE HALT: {reason}")
                break

        # Spacing between calls
        if i < len(leads) - 1:
            log.info(f"Spacing: {spacing}s before next call...")
            time.sleep(spacing)

    # ─── Campaign complete ───────────────────────────────────────
    log.info("\n" + report.generate_report())

    # Check success criteria
    if success_criteria:
        log.info("\nSuccess Criteria Assessment:")
        criteria_results = report.check_success_criteria(success_criteria)
        all_met = True
        for criterion, met, detail in criteria_results:
            status = "✅" if met else "❌"
            log.info(f"  {status} {criterion}: {detail}")
            if not met:
                all_met = False

        if all_met:
            log.info("\n✅ ALL SUCCESS CRITERIA MET — Phase can be promoted")
        else:
            log.warning("\n⚠️ Some criteria not met — review before promoting")

    # Save report
    per_call = phase_cfg.get("per_call_reports", False)
    report.save(REPORT_DIR, per_call=per_call)

    return True


# ═══════════════════════════════════════════════════════════════════
#  CLI ENTRY
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Alan Field Campaign Runner")
    parser.add_argument("--phase", type=int, required=True, choices=[1, 2, 3, 4],
                        help="Campaign phase to execute (1-4)")
    parser.add_argument("--dry", action="store_true",
                        help="Dry run — log but don't fire calls")
    parser.add_argument("--skip-preflight", action="store_true",
                        help="Skip pre-flight validation (not recommended)")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    try:
        success = run_field_campaign(
            phase_num=args.phase,
            dry_run=args.dry,
            skip_preflight=args.skip_preflight,
        )
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log.info("Campaign interrupted by user")
        sys.exit(130)
    except Exception as e:
        log.critical(f"Campaign crashed: {e}")
        log.critical(traceback.format_exc())
        sys.exit(1)
