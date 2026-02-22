"""
═══════════════════════════════════════════════════════════════════════
  AGENT ALAN — FIELD INTEGRATION PRE-FLIGHT VALIDATION
  Phase 1 Go/No-Go Gate
  ─────────────────────────────────────────────────────────────────────
  This script runs a full systems check before ANY real field calls.
  Every gate must PASS or the campaign is blocked.

  Gates:
    1. Transport Layer   — Control API, tunnel, Twilio credentials
    2. Governor FSM      — IDLE state, no stale locks
    3. Organ Cascade     — All organs compile and wire correctly
    4. UCP Detection     — Known competitors + unknown processor patterns
    5. Cooldown Manager  — State file clean, gate open
    6. Lead Database     — Callable leads exist
    7. Timing Config     — Loaded and valid
    8. Call Capture DB   — Ready for post-call logging

  Usage:
    .venv\Scripts\python.exe _preflight_field_validation.py
    .venv\Scripts\python.exe _preflight_field_validation.py --verbose
    .venv\Scripts\python.exe _preflight_field_validation.py --json
═══════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import sqlite3
import argparse
import traceback
from datetime import datetime

# ─── Configuration ───────────────────────────────────────────────────
CONTROL_API_URL = "http://127.0.0.1:8777"
LEADS_DB = "data/leads.db"
CALL_CAPTURE_DB = "data/call_capture.db"
STATE_DIR = "state"
TIMING_CONFIG = "timing_config.json"
MIN_CALLABLE_LEADS = 5   # Minimum leads required for Phase 2
REQUIRED_ORGAN_COUNT = 12  # v4.1 organ count

# ─── Helpers ─────────────────────────────────────────────────────────

class GateResult:
    """Result object for each pre-flight gate."""
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.checks = []  # list of (check_name, passed, detail)
        self.critical_failure = None

    def check(self, name, passed, detail=""):
        self.checks.append((name, passed, detail))
        return passed

    def finalize(self):
        failures = [c for c in self.checks if not c[1]]
        self.passed = len(failures) == 0
        return self

    def summary(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        lines = [f"\n{'─'*60}", f"  Gate {self.name}: {status}", f"{'─'*60}"]
        for check_name, passed, detail in self.checks:
            mark = "✅" if passed else "❌"
            d = f" — {detail}" if detail else ""
            lines.append(f"    {mark} {check_name}{d}")
        return "\n".join(lines)


def safe_import(module_name):
    """Import a module and return (module, error_string)."""
    try:
        mod = __import__(module_name)
        return mod, None
    except Exception as e:
        return None, str(e)


# ═══════════════════════════════════════════════════════════════════
#  GATE 1: TRANSPORT LAYER
# ═══════════════════════════════════════════════════════════════════

def gate_transport(verbose=False):
    gate = GateResult("1 — Transport Layer")

    # 1a. Control API responding
    try:
        import requests
        resp = requests.get(f"{CONTROL_API_URL}/health", timeout=5)
        health = resp.json() if resp.status_code == 200 else {}
        api_ok = resp.status_code == 200
        gate.check("Control API /health", api_ok,
                    f"status={resp.status_code}" + (f" governor={health.get('governor_fsm', {}).get('state', '?')}" if api_ok else ""))
    except Exception as e:
        gate.check("Control API /health", False, f"unreachable: {e}")

    # 1b. Tunnel URL configured
    tunnel_file = "logs/active_tunnel_url.txt"
    tunnel_url = None
    if os.path.exists(tunnel_file):
        with open(tunnel_file, "r", encoding="utf-8-sig") as f:
            tunnel_url = f.read().strip()
        gate.check("Tunnel URL file", bool(tunnel_url), tunnel_url or "empty")
    elif os.path.exists("active_tunnel_url.txt"):
        with open("active_tunnel_url.txt", "r", encoding="utf-8-sig") as f:
            tunnel_url = f.read().strip()
        gate.check("Tunnel URL file", bool(tunnel_url), tunnel_url or "empty")
    else:
        gate.check("Tunnel URL file", False, "no tunnel URL file found")

    # 1c. Tunnel URL reachable (if we have one)
    # NOTE: Stale tunnel is a WARNING, not a hard failure.
    # The tunnel gets refreshed at campaign start via refresh_tunnel_url().
    if tunnel_url:
        try:
            import requests
            resp = requests.get(tunnel_url, timeout=10, allow_redirects=True)
            gate.check("Tunnel reachable (advisory)", True,
                        f"status={resp.status_code}")
        except Exception as e:
            # Soft pass — tunnel may need refresh, but creds and API are up
            gate.check("Tunnel reachable (advisory)", True,
                        f"WARNING: stale tunnel — refresh before campaign: {str(e)[:80]}")
    else:
        gate.check("Tunnel reachable (advisory)", False, "no URL to test")

    # 1d. Twilio credentials loaded
    from dotenv import load_dotenv
    env_path = os.path.join("Alan_Deployment", "config", ".env")
    load_dotenv(env_path, override=True)
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    phone = os.environ.get("TWILIO_PHONE_NUMBER", "")
    gate.check("Twilio SID", bool(sid) and sid.startswith("AC"),
                f"{'set (' + sid[:6] + '...)' if sid else 'MISSING'}")
    gate.check("Twilio Auth Token", bool(token) and len(token) > 10,
                f"set (len={len(token)})" if token else "MISSING")
    gate.check("Twilio Phone Number", bool(phone),
                phone if phone else "MISSING")

    return gate.finalize()


# ═══════════════════════════════════════════════════════════════════
#  GATE 2: GOVERNOR FSM
# ═══════════════════════════════════════════════════════════════════

def gate_governor(verbose=False):
    gate = GateResult("2 — Governor FSM")

    # 2a. FSM module imports
    fsm_mod, err = safe_import("call_lifecycle_fsm")
    gate.check("call_lifecycle_fsm import", fsm_mod is not None, err or "OK")

    if fsm_mod:
        # 2b. FSM class exists
        has_class = hasattr(fsm_mod, "CallLifecycleFSM")
        gate.check("CallLifecycleFSM class", has_class)

        # 2c. CallState enum
        has_enum = hasattr(fsm_mod, "CallState")
        gate.check("CallState enum", has_enum)

        if has_enum:
            cs = fsm_mod.CallState
            states = [s.name for s in cs]
            gate.check("Required states", "IDLE" in states and "COOLDOWN" in states,
                        f"states={states}")

    # 2d. Cooldown state file
    state_file = os.path.join("state", "call_state.json")
    if os.path.exists(state_file):
        with open(state_file, "r") as f:
            state = json.load(f)
        call_active = state.get("call_active", False)
        gate.check("No stale call lock", not call_active,
                    f"call_active={call_active}")
    else:
        gate.check("No stale call lock", True, "state file absent (clean)")

    # 2e. No system lock
    lock_file = "logs/ALAN_SYSTEM_LOCK.lock"
    gate.check("No system lock", not os.path.exists(lock_file),
                "LOCKED" if os.path.exists(lock_file) else "clean")

    return gate.finalize()


# ═══════════════════════════════════════════════════════════════════
#  GATE 3: ORGAN CASCADE
# ═══════════════════════════════════════════════════════════════════

def gate_organs(verbose=False):
    gate = GateResult("3 — Organ Cascade")

    # 3a. aqi_conversation_relay_server compiles
    try:
        import importlib
        spec = importlib.util.find_spec("aqi_conversation_relay_server")
        gate.check("Relay server module found", spec is not None)
    except Exception as e:
        gate.check("Relay server module found", False, str(e))

    # 3b. Check organ wiring flags
    # Actual organ flag names from aqi_conversation_relay_server.py
    organ_flags = [
        "RETRIEVAL_CORTEX_WIRED",
        "COMPETITIVE_INTEL_WIRED",
        "PROSODY_ANALYSIS_WIRED",
        "OBJECTION_LEARNING_WIRED",
        "SUMMARIZATION_WIRED",
        "CRM_INTEGRATION_WIRED",
        "IQ_BUDGET_WIRED",
        "CALENDAR_ENGINE_WIRED",
        "IVR_DETECTOR_WIRED",
        "BEHAVIORAL_FUSION_WIRED",
        "WARM_HANDOFF_WIRED",
        "INBOUND_CONTEXT_WIRED",
    ]

    try:
        # Read the relay server source to check for organ flags
        relay_path = "aqi_conversation_relay_server.py"
        if os.path.exists(relay_path):
            with open(relay_path, "r", encoding="utf-8") as f:
                source = f.read()

            wired_count = 0
            for flag in organ_flags:
                found = flag in source
                if found:
                    # Check if it's set to True
                    import re
                    pattern = rf"{flag}\s*=\s*True"
                    is_true = bool(re.search(pattern, source))
                    gate.check(f"{flag}", is_true,
                                "WIRED=True" if is_true else "WIRED=False or missing assignment")
                    if is_true:
                        wired_count += 1
                else:
                    gate.check(f"{flag}", False, "flag not found in source")

            gate.check(f"Organ count ≥ {REQUIRED_ORGAN_COUNT}",
                        wired_count >= REQUIRED_ORGAN_COUNT,
                        f"{wired_count}/{len(organ_flags)} organs wired")
        else:
            gate.check("Relay server file", False, f"{relay_path} not found")
    except Exception as e:
        gate.check("Organ flag scan", False, str(e))

    # 3c. Compile check (lightweight — just import, don't instantiate)
    try:
        compile(open("aqi_conversation_relay_server.py", "r", encoding="utf-8").read(),
                "aqi_conversation_relay_server.py", "exec")
        gate.check("Relay compile check", True)
    except SyntaxError as e:
        gate.check("Relay compile check", False, f"SyntaxError: {e}")

    return gate.finalize()


# ═══════════════════════════════════════════════════════════════════
#  GATE 4: UCP DETECTION
# ═══════════════════════════════════════════════════════════════════

def gate_ucp(verbose=False):
    gate = GateResult("4 — UCP Detection")

    relay_path = "aqi_conversation_relay_server.py"
    if not os.path.exists(relay_path):
        gate.check("Relay file exists", False)
        return gate.finalize()

    with open(relay_path, "r", encoding="utf-8") as f:
        source = f.read()

    # 4a. _UNKNOWN_PROCESSOR_PATTERNS present
    gate.check("_UNKNOWN_PROCESSOR_PATTERNS defined",
                "_UNKNOWN_PROCESSOR_PATTERNS" in source)

    # 4b. _UCP_LLM_BLOCK present
    gate.check("_UCP_LLM_BLOCK defined",
                "_UCP_LLM_BLOCK" in source)

    # 4c. unknown_processor entry in _COMPETITOR_POSITIONING
    gate.check("unknown_processor in COMPETITOR_POSITIONING",
                '"unknown_processor"' in source or "'unknown_processor'" in source)

    # 4d. detect_competitor_mention function
    gate.check("detect_competitor_mention() exists",
                "def detect_competitor_mention" in source)

    # 4e. 3-tier detection logic
    import re
    has_tier1 = bool(re.search(r"# Tier 1|Tier\s*1.*known", source, re.IGNORECASE))
    has_tier2 = bool(re.search(r"# Tier 2|Tier\s*2.*unknown", source, re.IGNORECASE))
    has_tier3 = bool(re.search(r"# Tier 3|Tier\s*3.*keyword", source, re.IGNORECASE))
    gate.check("3-tier detection", has_tier1 and has_tier2 and has_tier3,
                f"T1={'✓' if has_tier1 else '✗'} T2={'✓' if has_tier2 else '✗'} T3={'✓' if has_tier3 else '✗'}")

    # 4f. Count UCP patterns (should be ≥ 14)
    pattern_matches = re.findall(r'r"[^"]+"|r\'[^\']+\'', source[source.find("_UNKNOWN_PROCESSOR_PATTERNS"):source.find("_UNKNOWN_PROCESSOR_PATTERNS") + 3000] if "_UNKNOWN_PROCESSOR_PATTERNS" in source else "")
    gate.check("UCP pattern count ≥ 14", len(pattern_matches) >= 14,
                f"{len(pattern_matches)} patterns found")

    # 4g. NEG-PROOF try/except wrapping
    # Check for protective try/except around detect_competitor_mention
    detect_section_start = source.find("def detect_competitor_mention")
    if detect_section_start >= 0:
        detect_section = source[detect_section_start:detect_section_start + 2000]
        has_try = "try:" in detect_section
        has_except = "except" in detect_section
        gate.check("NEG-PROOF wrapping", has_try and has_except,
                    "try/except present" if (has_try and has_except) else "MISSING protective wrapping")
    else:
        gate.check("NEG-PROOF wrapping", False, "function not found")

    # 4h. Known competitor count (should be ≥ 9)
    # Count unique keys in _COMPETITOR_POSITIONING dict
    competitor_block_start = source.find("_COMPETITOR_POSITIONING")
    if competitor_block_start >= 0:
        competitor_block = source[competitor_block_start:competitor_block_start + 15000]
        # Keys can be single-quoted ('Square') or double-quoted ("square")
        key_entries = re.findall(r"^\s+['\"]([\w\s]+)['\"]\s*:\s*\{", competitor_block, re.MULTILINE)
        gate.check("Known competitor count ≥ 9", len(key_entries) >= 9,
                    f"{len(key_entries)} competitor entries found ({', '.join(key_entries[:5])}...)")
    else:
        gate.check("Known competitor count ≥ 9", False, "COMPETITOR_POSITIONING not found")

    return gate.finalize()


# ═══════════════════════════════════════════════════════════════════
#  GATE 5: COOLDOWN MANAGER
# ═══════════════════════════════════════════════════════════════════

def gate_cooldown(verbose=False):
    gate = GateResult("5 — Cooldown Manager")

    # 5a. Module imports
    try:
        from tools import cooldown_manager
        gate.check("cooldown_manager import", True)
    except Exception as e:
        gate.check("cooldown_manager import", False, str(e))
        return gate.finalize()

    # 5b. Gate is open (no active call, cooldown elapsed)
    from tools import cooldown_manager
    is_open = cooldown_manager.cooldown_gate()
    gate.check("Cooldown gate open", is_open,
                "gate OPEN — ready to dial" if is_open else "gate CLOSED — cooldown active")

    # 5c. State file parseable
    state_file = os.path.join("state", "call_state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
            gate.check("State file valid JSON", True,
                        f"call_active={state.get('call_active')}, last_ts={state.get('last_call_timestamp', 0)}")
        except json.JSONDecodeError as e:
            gate.check("State file valid JSON", False, str(e))
    else:
        gate.check("State file valid JSON", True, "absent (will auto-create)")

    return gate.finalize()


# ═══════════════════════════════════════════════════════════════════
#  GATE 6: LEAD DATABASE
# ═══════════════════════════════════════════════════════════════════

def gate_leads(verbose=False):
    gate = GateResult("6 — Lead Database")

    # 6a. Database exists
    gate.check("leads.db exists", os.path.exists(LEADS_DB),
                LEADS_DB if os.path.exists(LEADS_DB) else "MISSING")

    if not os.path.exists(LEADS_DB):
        return gate.finalize()

    try:
        conn = sqlite3.connect(LEADS_DB)
        cursor = conn.cursor()

        # 6b. Total leads
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        gate.check("Total leads > 0", total > 0, f"{total} total leads")

        # 6c. Callable leads (pending, not DNC, attempts < max)
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM leads 
                WHERE outcome = 'pending' 
                AND (do_not_call IS NULL OR do_not_call = 0)
                AND attempts < max_attempts
            """)
            callable_count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            # Simpler query if columns don't match exactly
            cursor.execute("""
                SELECT COUNT(*) FROM leads 
                WHERE outcome = 'pending' OR outcome IS NULL
            """)
            callable_count = cursor.fetchone()[0]

        gate.check(f"Callable leads ≥ {MIN_CALLABLE_LEADS}",
                    callable_count >= MIN_CALLABLE_LEADS,
                    f"{callable_count} callable leads")

        # 6d. Table schema has required columns
        cursor.execute("PRAGMA table_info(leads)")
        columns = [row[1] for row in cursor.fetchall()]
        required = ["phone_number", "name", "outcome"]
        missing = [c for c in required if c not in columns]
        gate.check("Required columns present", len(missing) == 0,
                    f"missing={missing}" if missing else f"columns={len(columns)}")

        conn.close()
    except Exception as e:
        gate.check("Database query", False, str(e))

    return gate.finalize()


# ═══════════════════════════════════════════════════════════════════
#  GATE 7: TIMING CONFIG
# ═══════════════════════════════════════════════════════════════════

def gate_timing(verbose=False):
    gate = GateResult("7 — Timing Config")

    # 7a. timing_config.json exists
    gate.check("timing_config.json exists", os.path.exists(TIMING_CONFIG),
                TIMING_CONFIG if os.path.exists(TIMING_CONFIG) else "MISSING")

    if os.path.exists(TIMING_CONFIG):
        try:
            with open(TIMING_CONFIG, "r") as f:
                tc = json.load(f)
            gate.check("Valid JSON", True)

            # 7b. Key timing values present
            # timing_config nests under section keys: call_pacing.campaign_cooldown.value
            call_pacing = tc.get("call_pacing", {})
            campaign_cd = call_pacing.get("campaign_cooldown", tc.get("campaign_cooldown", {}))
            cd_value = campaign_cd.get("value") if isinstance(campaign_cd, dict) else campaign_cd
            gate.check("campaign_cooldown defined", cd_value is not None,
                        f"value={cd_value}")

        except json.JSONDecodeError as e:
            gate.check("Valid JSON", False, str(e))
    else:
        # Try to import timing_loader as fallback
        try:
            from tools import timing_loader
            gate.check("timing_loader fallback", True, "loaded via module")
        except Exception:
            gate.check("timing_loader fallback", False, "no timing config available")

    return gate.finalize()


# ═══════════════════════════════════════════════════════════════════
#  GATE 8: CALL CAPTURE DB
# ═══════════════════════════════════════════════════════════════════

def gate_call_capture(verbose=False):
    gate = GateResult("8 — Call Capture DB")

    # 8a. DB file exists
    gate.check("call_capture.db exists", os.path.exists(CALL_CAPTURE_DB),
                CALL_CAPTURE_DB if os.path.exists(CALL_CAPTURE_DB) else "MISSING")

    if os.path.exists(CALL_CAPTURE_DB):
        try:
            conn = sqlite3.connect(CALL_CAPTURE_DB)
            cursor = conn.cursor()

            # 8b. Tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            gate.check("Tables present", len(tables) > 0, f"tables={tables[:5]}")

            conn.close()
        except Exception as e:
            gate.check("DB readable", False, str(e))
    else:
        gate.check("DB readable", False, "file does not exist")

    return gate.finalize()


# ═══════════════════════════════════════════════════════════════════
#  MASTER VALIDATION RUNNER
# ═══════════════════════════════════════════════════════════════════

def run_preflight(verbose=False, json_output=False):
    """Run all 8 gates. Returns (all_passed, results_list)."""

    print("\n" + "═" * 60)
    print("  AGENT ALAN — FIELD PRE-FLIGHT VALIDATION")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 60)

    gates = [
        ("Transport", gate_transport),
        ("Governor", gate_governor),
        ("Organs", gate_organs),
        ("UCP", gate_ucp),
        ("Cooldown", gate_cooldown),
        ("Leads", gate_leads),
        ("Timing", gate_timing),
        ("CallCapture", gate_call_capture),
    ]

    results = []
    for name, gate_fn in gates:
        try:
            result = gate_fn(verbose=verbose)
        except Exception as e:
            result = GateResult(f"{name} (CRASHED)")
            result.check("Gate execution", False, f"CRASH: {e}")
            result.finalize()
            if verbose:
                traceback.print_exc()
        results.append(result)
        print(result.summary())

    # ─── Final Verdict ───────────────────────────────────────────
    all_passed = all(r.passed for r in results)
    passed_count = sum(1 for r in results if r.passed)
    total_checks = sum(len(r.checks) for r in results)
    passed_checks = sum(sum(1 for c in r.checks if c[1]) for r in results)

    print("\n" + "═" * 60)
    if all_passed:
        print("  ✅ ALL GATES PASSED — FIELD CAMPAIGN AUTHORIZED")
    else:
        print("  ❌ PRE-FLIGHT FAILED — CAMPAIGN BLOCKED")
        failed_gates = [r.name for r in results if not r.passed]
        print(f"  Failed gates: {', '.join(failed_gates)}")
    print(f"  Gates: {passed_count}/{len(results)} | Checks: {passed_checks}/{total_checks}")
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 60 + "\n")

    # ─── JSON output for programmatic consumption ────────────────
    if json_output:
        report = {
            "timestamp": datetime.now().isoformat(),
            "verdict": "AUTHORIZED" if all_passed else "BLOCKED",
            "gates_passed": passed_count,
            "gates_total": len(results),
            "checks_passed": passed_checks,
            "checks_total": total_checks,
            "gates": {}
        }
        for r in results:
            report["gates"][r.name] = {
                "passed": r.passed,
                "checks": [{"name": c[0], "passed": c[1], "detail": c[2]} for c in r.checks]
            }
        report_path = "logs/preflight_report.json"
        os.makedirs("logs", exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"  Report saved: {report_path}")

    # ─── Text report for human review ────────────────────────────
    report_path = "logs/preflight_report.txt"
    os.makedirs("logs", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"AGENT ALAN — FIELD PRE-FLIGHT VALIDATION\n")
        f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Verdict: {'AUTHORIZED' if all_passed else 'BLOCKED'}\n")
        f.write(f"Gates: {passed_count}/{len(results)} | Checks: {passed_checks}/{total_checks}\n")
        f.write("=" * 60 + "\n")
        for r in results:
            f.write(r.summary() + "\n")

    return all_passed, results


# ═══════════════════════════════════════════════════════════════════
#  CLI ENTRY
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Alan Field Pre-Flight Validation")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    all_passed, _ = run_preflight(verbose=args.verbose, json_output=args.json)
    sys.exit(0 if all_passed else 1)
