"""
SPACED CAMPAIGN LAUNCHER
========================
Fires calls one at a time with proper spacing.
Waits for each call to fully complete before firing the next.
Tim's directive: "Space calls accordingly. All leads do not need to be called in one day."
Tim's directive: "Make sure the time zones are respected. No reason to burn a lead."

Usage:
  python _fire_campaign.py              # Fire 10 calls (default)
  python _fire_campaign.py --count 5    # Fire 5 calls
  python _fire_campaign.py --dry        # Dry run — show what would fire
  python _fire_campaign.py --no-tz      # Skip timezone filter (call any time)

Regime Engine Integration (CW23):
  Reads data/regime_config_live.json to:
  - Reorder leads by segment health (STABLE first, DEGRADED last)
  - Adjust pacing per-lead based on segment status
  - Skip leads in OFF segments

Timezone Filter (Feb 24, 2026):
  Filters leads by area code → timezone → local business hours.
  Only calls leads where it's currently 9 AM – 5 PM local time.
  Prevents burning leads by calling after hours.
"""
import sys, os, time, json, argparse, sqlite3, requests, re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API_BASE = "http://127.0.0.1:8777"
SPACE_BETWEEN_CALLS = 45  # seconds between calls — let each call breathe (regime may override)
MAX_WAIT_FOR_COMPLETION = 180  # max seconds to wait for a call to finish
POLL_INTERVAL = 5  # check every 5 seconds if call completed

# ── Timezone-Aware Campaign Filter (Feb 24, 2026) ───────────────────
# Tim: "Make sure the time zones are respected. No reason to burn a lead."
# Area code → timezone mapping (US only, comprehensive)
_TZ_PT = {'206','209','213','253','310','323','341','360','408','415','424','425','442',
          '458','503','509','510','530','541','559','562','564','619','626','628','650',
          '657','661','669','707','714','725','747','760','775','805','818','831',
          '858','909','916','925','935','949','951','971'}
_TZ_MT = {'303','307','385','406','435','480','505','520','575','602','623','719','720',
          '801','928','915','970'}
_TZ_CT = {'205','210','214','217','218','254','262','270','281','308','309','312','314',
          '316','318','319','325','331','337','346','361','402','405','409','414',
          '417','430','432','469','479','501','504','507','512','515','531','563','573',
          '580','601','605','608','612','615','618','620','682','701','708','712','713',
          '715','763','769','773','779','785','806','815','816','817','830','832','847',
          '870','901','903','913','918','920','936','938','940','952','956','972','979','985'}
# Everything not in PT/MT/CT → ET

BUSINESS_HOUR_START = 9   # 9 AM local
BUSINESS_HOUR_END = 17    # 5 PM local

# ── Bad Lead Name Filter (Feb 24, 2026) ─────────────────────────────
# Tim: "No reason to burn a lead."
# SEO article titles, event listings, generic aggregator pages — not real businesses.
_BAD_LEAD_PATTERNS = [
    # SEO/Article titles
    'the best', 'top 10', 'top 5', 'best 10', 'how to', 'guide to',
    'selecting the ideal', 'case study', 'festivals coming up',
    'new construction homes in', 'dog owners of', 'townhomes for rent',
    # Generic aggregator listings
    'near me', 'affordable', 'rated',
    # Year in name (article/event, not a business)
    '2024', '2025', '2026', '2027',
    # Too generic
    'landscaping', 'florist floral', 
]

def _is_bad_lead_name(name):
    """Return (is_bad, reason) if the lead name looks like an SEO title, not a real business."""
    if not name or name.strip().lower() in ('there', 'unknown', 'n/a', ''):
        return True, "placeholder name"
    lower = name.lower().strip()
    for pattern in _BAD_LEAD_PATTERNS:
        if pattern in lower:
            return True, f"SEO pattern: '{pattern}'"
    # Very long names (>55 chars) are usually page titles
    if len(name) > 55:
        return True, f"name too long ({len(name)} chars) — likely page title"
    # Starts with a street number (address, not a business name)
    import re as _re
    if _re.match(r'^\d{3,}[\s,]', name.strip()):
        return True, "starts with street number — address, not business"
    return False, ""

def _get_area_code(phone):
    """Extract area code from E.164 phone number."""
    clean = re.sub(r'\D', '', phone or '')
    if clean.startswith('1') and len(clean) == 11:
        return clean[1:4]
    elif len(clean) == 10:
        return clean[:3]
    return None

def _get_timezone(area_code):
    """Map area code to timezone name."""
    if area_code in _TZ_PT: return 'PT'
    if area_code in _TZ_MT: return 'MT'
    if area_code in _TZ_CT: return 'CT'
    return 'ET'

_TZ_ZONE_MAP = {
    'PT': 'America/Los_Angeles',
    'MT': 'America/Denver',
    'CT': 'America/Chicago',
    'ET': 'America/New_York',
}

def _is_business_hours(tz_name):
    """Check if it's currently business hours in the given timezone.
    Returns (bool, local_datetime)."""
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports.zoneinfo import ZoneInfo

    tz = ZoneInfo(_TZ_ZONE_MAP.get(tz_name, 'America/New_York'))
    local_now = datetime.now(tz)
    is_weekday = local_now.weekday() < 5
    in_hours = is_weekday and BUSINESS_HOUR_START <= local_now.hour < BUSINESS_HOUR_END
    return in_hours, local_now

def filter_leads_by_timezone(leads):
    """Filter leads to only those currently in business hours.
    Returns (callable_leads, skipped_leads) — skipped leads are preserved for later."""
    callable_leads = []
    skipped_leads = []

    for lead in leads:
        ac = _get_area_code(lead.get('phone_number', ''))
        tz = _get_timezone(ac) if ac else 'ET'
        in_hours, local_time = _is_business_hours(tz)
        lead['_tz'] = tz
        lead['_local_time'] = local_time.strftime('%I:%M %p')

        if in_hours:
            callable_leads.append(lead)
        else:
            skipped_leads.append(lead)

    return callable_leads, skipped_leads

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
    parser.add_argument("--no-tz", action="store_true", dest="no_tz", help="Skip timezone filter — call any time")
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
    leads = get_pending_leads(args.count * 3 if not args.no_tz else args.count)  # Pull extra to survive TZ filter
    if not leads:
        print("\n  [!] No pending callable leads found.")
        return

    # ── Timezone Filter ──────────────────────────────────────────────
    if not args.no_tz:
        callable_leads, skipped_leads = filter_leads_by_timezone(leads)

        if skipped_leads:
            print(f"\n  [TZ FILTER] Skipped {len(skipped_leads)} leads (outside business hours):")
            for sl in skipped_leads:
                print(f"    SKIP  {sl['name'][:35]:35s} | {sl['_tz']} ~{sl['_local_time']} | {sl['phone_number']}")

        if not callable_leads:
            print(f"\n  [!] No leads in callable time zones right now.")
            print(f"  [!] All {len(skipped_leads)} pending leads are outside 9 AM – 5 PM local time.")
            print(f"  [!] Try again during Pacific/Mountain business hours, or use --no-tz to override.")
            return

        leads = callable_leads[:args.count]  # Trim to requested count
        print(f"\n  [TZ FILTER] {len(callable_leads)} leads in business hours, firing {len(leads)}")

        # Show current times
        tz_counts = {}
        for cl in callable_leads:
            tz = cl.get('_tz', '??')
            tz_counts[tz] = tz_counts.get(tz, 0) + 1
        tz_summary = ', '.join(f"{tz}: {ct}" for tz, ct in sorted(tz_counts.items()))
        print(f"  [TZ FILTER] Callable breakdown: {tz_summary}")
    else:
        print(f"\n  [TZ FILTER] DISABLED — calling regardless of local time")

    # ── Bad Lead Name Filter ─────────────────────────────────────────
    clean_leads = []
    bad_leads_skipped = []
    for lead in leads:
        is_bad, reason = _is_bad_lead_name(lead.get('name', ''))
        if is_bad:
            bad_leads_skipped.append((lead, reason))
        else:
            clean_leads.append(lead)
    
    if bad_leads_skipped:
        print(f"\n  [LEAD FILTER] Skipped {len(bad_leads_skipped)} bad lead names:")
        for sl, reason in bad_leads_skipped:
            print(f"    SKIP  {sl['name'][:45]:45s} | {reason}")
        leads = clean_leads
        if not leads:
            print(f"\n  [!] All leads filtered out. No callable leads remain.")
            return

    print(f"\n  Found {len(leads)} leads to call:\n")
    for i, lead in enumerate(leads, 1):
        regime_tag = ""
        tz_tag = ""
        if REGIME_AVAILABLE and "_regime_status" in lead:
            regime_tag = f" | R:{lead['_regime_status']}"
        if "_tz" in lead:
            tz_tag = f" | {lead['_tz']} ~{lead['_local_time']}"
        print(f"  {i:2d}. {lead['name'][:40]:40s} | {lead['phone_number']:15s} | {lead['lead_source']}{regime_tag}{tz_tag}")

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
