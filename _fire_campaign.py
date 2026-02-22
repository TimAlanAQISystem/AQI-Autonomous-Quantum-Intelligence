"""
SPACED CAMPAIGN LAUNCHER
========================
Fires calls one at a time with proper spacing.
Waits for each call to fully complete before firing the next.
Tim's directive: "Space calls accordingly. All leads do not need to be called in one day."

Usage:
  python _fire_campaign.py              # Fire 10 calls (default)
  python _fire_campaign.py --count 5    # Fire 5 calls
  python _fire_campaign.py --dry        # Dry run — show what would fire

Regime Engine Integration (CW23):
  Reads data/regime_config_live.json to:
  - Reorder leads by segment health (STABLE first, DEGRADED last)
  - Adjust pacing per-lead based on segment status
  - Skip leads in OFF segments
"""
import sys, os, time, json, argparse, sqlite3, requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API_BASE = "http://127.0.0.1:8777"
SPACE_BETWEEN_CALLS = 45  # seconds between calls — let each call breathe (regime may override)
MAX_WAIT_FOR_COMPLETION = 180  # max seconds to wait for a call to finish
POLL_INTERVAL = 5  # check every 5 seconds if call completed

# ── Lead tracking (CW23: fix recycling) ──────────────────────────────
from lead_database import LeadDB
_lead_db = LeadDB()

# ── Regime Engine Integration (CW23) ────────────────────────────────
try:
    from regime_queue_integrator import (
        score_and_sort_leads, get_pacing_delay, should_skip_lead,
        get_regime_summary,
    )
    REGIME_AVAILABLE = True
except ImportError:
    REGIME_AVAILABLE = False

def mark_lead_dialed(lead, call_sid="", outcome="dialed"):
    """Mark a lead as dialed immediately after firing — prevents recycling."""
    try:
        _lead_db.record_attempt(
            lead['id'],
            outcome=outcome,
            details=f"Campaign call SID: {call_sid}",
            call_sid=call_sid,
        )
    except Exception as e:
        print(f"  [!] Failed to mark lead as dialed: {e}")

def get_pending_leads(limit=20):
    """Pull pending leads from database — excludes already-dialed numbers.
    CW23: Regime Engine reorders leads by segment health when available."""
    from lead_database import LeadDB
    db = LeadDB()
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone_number, lead_source, outcome, attempts, max_attempts,
               business_type
        FROM leads 
        WHERE outcome = 'pending' AND do_not_call = 0 AND attempts < max_attempts
          AND phone_number NOT IN (
              SELECT DISTINCT phone_number FROM leads WHERE outcome != 'pending'
          )
        ORDER BY id
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    # CW23 Regime Engine: reorder by segment health
    if REGIME_AVAILABLE and rows:
        rows = score_and_sort_leads(rows)
        print(f"  [REGIME] Leads reordered by segment health ({len(rows)} scored)")

    return rows

def check_governor():
    """Check if we can fire a call (governor ready, no call in progress)."""
    try:
        r = requests.get(f"{API_BASE}/health", timeout=5)
        data = r.json()
        # Governor FSM is the source of truth
        fsm = data.get("governor_fsm", {})
        if fsm:
            is_active = fsm.get("is_active", False)
            can_start = fsm.get("can_start_call", False)
            cooldown = fsm.get("cooldown_remaining", 0)
            state = fsm.get("state", "UNKNOWN")
            return can_start and not is_active, is_active, cooldown
        # Fallback: assume ready (let the /call endpoint do its own governor check)
        return True, False, 0
    except Exception as e:
        print(f"  [!] Health check failed: {e}")
        return False, True, 999

def wait_for_ready(max_wait=MAX_WAIT_FOR_COMPLETION):
    """Wait until the governor is ready for the next call."""
    start = time.time()
    while time.time() - start < max_wait:
        ready, in_progress, cooldown = check_governor()
        if ready:
            return True
        elapsed = int(time.time() - start)
        if in_progress:
            print(f"  ... call in progress ({elapsed}s waited)", end="\r")
        elif cooldown > 0:
            print(f"  ... cooldown {cooldown:.0f}s remaining ({elapsed}s waited)", end="\r")
        time.sleep(POLL_INTERVAL)
    print()
    return False

def fire_call(lead):
    """Fire a single call through the /call endpoint."""
    payload = {
        "to": lead["phone_number"],
        "name": lead.get("name", "there"),
        "business_name": lead.get("name", ""),
    }
    try:
        r = requests.post(f"{API_BASE}/call", json=payload, timeout=15)
        data = r.json()
        return data
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Spaced Campaign Launcher")
    parser.add_argument("--count", type=int, default=10, help="Number of calls to fire (default: 10)")
    parser.add_argument("--dry", action="store_true", help="Dry run — show what would fire")
    parser.add_argument("--space", type=int, default=SPACE_BETWEEN_CALLS, help=f"Seconds between calls (default: {SPACE_BETWEEN_CALLS})")
    args = parser.parse_args()

    print("=" * 70)
    print("  SPACED CAMPAIGN LAUNCHER")
    print(f"  Target: {args.count} calls | Spacing: {args.space}s between calls")
    print("=" * 70)

    # CW23 Regime Engine status
    if REGIME_AVAILABLE:
        rsummary = get_regime_summary()
        if rsummary.get("available"):
            print(f"\n  [REGIME ENGINE] Active — {rsummary['total_segments']} segments")
            print(f"  Status Distribution: {rsummary['status_distribution']}")
            print(f"  Model Actions Pending: {rsummary['model_actions_pending']}")
        else:
            print(f"\n  [REGIME ENGINE] Not available — using default ordering")
    else:
        print(f"\n  [REGIME ENGINE] Module not loaded — using default ordering")

    # Get leads
    leads = get_pending_leads(args.count)
    if not leads:
        print("\n  [!] No pending callable leads found.")
        return

    print(f"\n  Found {len(leads)} leads to call:\n")
    for i, lead in enumerate(leads, 1):
        regime_tag = ""
        if REGIME_AVAILABLE and "_regime_status" in lead:
            regime_tag = f" | R:{lead['_regime_status']}"
        print(f"  {i:2d}. {lead['name'][:40]:40s} | {lead['phone_number']:15s} | {lead['lead_source']}{regime_tag}")

    if args.dry:
        print(f"\n  [DRY RUN] Would fire {len(leads)} calls. Exiting.")
        return

    print(f"\n  Starting in 5 seconds... (Ctrl+C to abort)")
    time.sleep(5)

    # Fire calls one at a time
    results = []
    for i, lead in enumerate(leads, 1):
        print(f"\n{'='*70}")
        print(f"  CALL {i}/{len(leads)}: {lead['name'][:45]}")
        print(f"  Phone: {lead['phone_number']} | Source: {lead['lead_source']}")
        print(f"{'='*70}")

        # CW23 Regime Engine: skip check
        if REGIME_AVAILABLE:
            skip, skip_reason = should_skip_lead(lead["phone_number"], lead.get("business_type", ""))
            if skip:
                print(f"  [REGIME SKIP] {skip_reason}")
                results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": "N/A", "status": "skipped"})
                continue

        # Wait for governor to be ready
        print("  Checking governor...")
        if not wait_for_ready():
            print("  [!] Governor not ready after max wait. Skipping remaining calls.")
            break

        # Fire the call
        print(f"  >>> FIRING CALL to {lead['phone_number']}...")
        result = fire_call(lead)
        
        sid = result.get("sid", "N/A")
        status = result.get("status", "unknown")
        
        if status == "fired":
            print(f"  [OK] Call fired! SID: {sid}")
            mark_lead_dialed(lead, call_sid=sid, outcome="dialed")
            results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": sid, "status": "fired"})
        elif status == "blocked":
            reason = result.get("reason", "unknown")
            cooldown_left = result.get("cooldown", 30)
            wait_time = max(cooldown_left + 5, 10)  # wait for cooldown + buffer
            print(f"  [BLOCKED] {reason} — waiting {wait_time}s then retrying...")
            time.sleep(wait_time)
            # Retry
            result = fire_call(lead)
            if result.get("status") == "fired":
                print(f"  [OK] Retry succeeded! SID: {result.get('sid')}")
                mark_lead_dialed(lead, call_sid=result.get('sid', ''), outcome='dialed')
                results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": result.get("sid"), "status": "fired"})
            else:
                # One more wait and try
                print(f"  [!] Still blocked, waiting 40s for full clear...")
                time.sleep(40)
                result = fire_call(lead)
                if result.get("status") == "fired":
                    print(f"  [OK] 2nd retry succeeded! SID: {result.get('sid')}")
                    mark_lead_dialed(lead, call_sid=result.get('sid', ''), outcome='dialed')
                    results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": result.get("sid"), "status": "fired"})
                else:
                    print(f"  [FAIL] Giving up on this lead: {result}")
                    results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": "N/A", "status": "failed"})
        else:
            print(f"  [FAIL] {result.get('message', result)}")
            results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": "N/A", "status": status})

        # Wait for this call to complete before proceeding
        if status == "fired" or (len(results) > 0 and results[-1]["status"] == "fired"):
            print(f"  Waiting for call to complete...")
            wait_for_ready()
            
            # Extra spacing between calls — regime-aware pacing
            if i < len(leads):
                space = args.space
                if REGIME_AVAILABLE:
                    regime_space = get_pacing_delay(
                        lead["phone_number"], lead.get("business_type", ""),
                        default_delay=args.space
                    )
                    if regime_space != args.space:
                        print(f"  [REGIME] Pacing adjusted: {args.space}s → {regime_space}s")
                        space = regime_space
                print(f"  Spacing: waiting {space}s before next call...")
                for remaining in range(space, 0, -1):
                    print(f"  ... next call in {remaining}s  ", end="\r")
                    time.sleep(1)
                print()

    # Summary
    print(f"\n{'='*70}")
    print(f"  CAMPAIGN SESSION COMPLETE")
    print(f"{'='*70}")
    fired = sum(1 for r in results if r["status"] == "fired")
    failed = sum(1 for r in results if r["status"] in ("failed", "error"))
    skipped = sum(1 for r in results if r["status"] == "skipped")
    print(f"  Fired:   {fired}")
    print(f"  Failed:  {failed}")
    print(f"  Skipped: {skipped}")
    print(f"  Total:   {len(results)}/{len(leads)}")
    print()
    for r in results:
        icon = "OK" if r["status"] == "fired" else "XX"
        print(f"  [{icon}] {r['lead'][:35]:35s} | {r['phone']:15s} | {r['sid'][:20]}")
    print()

if __name__ == "__main__":
    main()
