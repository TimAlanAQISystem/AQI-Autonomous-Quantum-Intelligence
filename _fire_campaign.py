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

# ── Contact Rate Optimizer Integration (Feb 25, 2026) ────────────────
# "Same Alan. Same script. Completely different results."
# The difference between 10% and 45% contact rate is entirely infrastructure.
try:
    from contact_rate_optimizer import (
        get_call_timing_score, get_day_quality, is_prime_window,
        LocalPresenceManager, MultiTouchSequencer, ContactRateAnalytics,
        score_data_quality, assess_lead_contact_probability,
    )
    CRO_AVAILABLE = True
except ImportError:
    CRO_AVAILABLE = False

# ── Precision Engine Integration (Feb 25, 2026) ─────────────────────
# "This is no longer a numbers game — it is professional strategy
#  with precise outcomes." — Built from 636 real call forensics.
try:
    from precision_engine import (
        PrecisionScorer, DeadLeadFilter, OptimalTimingEngine,
        OutcomeAnalyzer, generate_precision_briefing,
    )
    PRECISION_AVAILABLE = True
except ImportError:
    PRECISION_AVAILABLE = False

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

# ── Small-City Filter (Feb 25, 2026) ────────────────────────────────
# Tim: "Call cities that have a population of 100K or less and away from major
#        cities like LA, NY — merchants there actually answer calls."
# Area codes primarily serving cities/metros with population >100K are EXCLUDED.
# Toll-free numbers are always excluded (not geographic, usually corporate).
_MAJOR_METRO_AREA_CODES = {
    # New York Metro / NJ
    '212','347','646','718','917','929','516','631','914','845',
    '201','551','732','848','862','908','973',
    # Los Angeles Metro
    '213','310','323','424','562','626','657','714','747','818','909','949','951',
    # Chicago Metro
    '312','331','630','708','773','779','815','847','872',
    # Houston Metro
    '281','346','713','832',
    # Phoenix / Tucson
    '480','602','623','520',
    # Dallas–Fort Worth
    '214','469','682','817','972','940',
    # Philadelphia Metro
    '215','267','484','610',
    # San Antonio
    '210',
    # San Diego
    '619','858',
    # SF Bay Area / San Jose
    '408','415','510','628','650','669','925',
    # Austin
    '512','737',
    # Seattle Metro
    '206','253','425',
    # Denver / Colorado Springs
    '303','719','720',
    # Washington DC Metro
    '202','240','301','571','703',
    # Boston Metro
    '339','508','617','774','781','857',
    # Atlanta Metro
    '404','470','678','770',
    # Miami / Fort Lauderdale
    '305','754','786','954',
    # Tampa / St Pete / Orlando
    '321','407','727','813','941',
    # Detroit Metro
    '248','313','586',
    # Minneapolis / St Paul
    '612','651','763','952',
    # Portland OR
    '503','971',
    # Las Vegas
    '702','725',
    # Charlotte
    '704','980',
    # Nashville
    '615','629',
    # Salt Lake City
    '385','801',
    # Baltimore
    '410','443',
    # St Louis
    '314',
    # Raleigh / Durham
    '919','984',
    # Cleveland / Akron
    '216','330','440',
    # Pittsburgh
    '412','724',
    # Kansas City
    '816','913',
    # Indianapolis
    '317','463',
    # Cincinnati
    '513',
    # Columbus OH
    '614',
    # Jacksonville FL
    '904',
    # Sacramento
    '916',
    # Fresno / Bakersfield
    '559','661',
    # Oklahoma City
    '405',
    # Memphis
    '901',
    # Louisville
    '502',
    # Milwaukee
    '414',
    # Albuquerque
    '505',
    # New Orleans
    '504',
    # Omaha
    '402',
    # El Paso
    '915',
    # Virginia Beach / Norfolk / Richmond
    '757','804',
    # Corpus Christi / McAllen / Laredo
    '361','956',
    # Baton Rouge
    '225',
    # Honolulu
    '808',
    # Birmingham AL
    '205',
    # Buffalo / Rochester NY
    '585','716',
    # Boise
    '208',
    # Grand Rapids
    '616',
    # Knoxville / Chattanooga
    '423','865',
    # Des Moines
    '515',
    # Stockton / Modesto
    '209',
    # Lexington KY
    '859',
    # Toll-free (not geographic, usually corporate)
    '800','833','844','855','866','877','888',
}

def _is_small_city_lead(phone):
    """Return True if this phone number is from a small-city area code (not a major metro)."""
    ac = _get_area_code(phone)
    if not ac:
        return False
    return ac not in _MAJOR_METRO_AREA_CODES

# ── Bad Lead Name Filter (Feb 24, 2026) ─────────────────────────────
# Tim: "No reason to burn a lead."
# SEO article titles, event listings, generic aggregator pages — not real businesses.
_BAD_LEAD_PATTERNS = [
    # SEO/Article titles
    'the best', 'top 10', 'top 5', 'best 10', '10 best', 'how to', 'guide to',
    'selecting the ideal', 'case study', 'festivals coming up',
    'new construction homes in', 'dog owners of', 'townhomes for rent',
    # Generic aggregator listings
    'near me', 'affordable', 'rated',
    # Year in name (article/event, not a business)
    '2024', '2025', '2026', '2027',
    # Too generic
    'landscaping', 'florist floral',
    # Corporate / franchise chains (can't change POS, waste of call)
    'petsmart', 'ace hardware', 'woof gang', 'petco',
    'certapro', 'servpro', 'anytime fitness', 'planet fitness',
    'great clips', 'supercuts', 'sports clips',
    'dollar general', 'dollar tree', 'family dollar',
    'walgreens', 'cvs pharmacy', 'rite aid',
    'walmart', 'target store', 'costco', 'home depot', 'lowes', "lowe's",
    'mcdonald', 'burger king', 'taco bell', 'subway', 'starbucks',
    'dunkin', 'chick-fil-a', 'wendys', "wendy's",
    'hilton', 'marriott', 'holiday inn', 'hampton inn', 'comfort inn',
    'motel 6', 'super 8', 'days inn', 'la quinta',
    'wells fargo', 'bank of america', 'chase bank', 'citibank',
    'fedex', 'ups store',
    'marble slab creamery', 'cold stone creamery', 'baskin-robbins', 'baskin robbins',
    'jiffy lube', 'valvoline', 'meineke', 'maaco', 'midas auto', 'midas muffler', 'midas brake', 'firestone',
    'papa john', "papa john's", 'domino', "domino's", 'pizza hut',
    'applebee', "applebee's", 'chili', "chili's", 'olive garden',
    'red lobster', 'outback steakhouse', 'buffalo wild wings',
    # More restaurant/food franchises
    'mcalister', "mcalister's", 'panera', 'chipotle', 'five guys', 'sonic drive',
    'popeye', "popeye's", 'arby', "arby's", 'jack in the box', 'whataburger',
    'waffle house', 'ihop', 'denny', "denny's", 'cracker barrel',
    'panda express', 'wingstop', 'zaxby', "zaxby's", 'jersey mike',
    'firehouse subs', 'jimmy john', "jimmy john's", 'jason\'s deli',
    'noodles & company', 'noodles and company', 'mod pizza', 'blaze pizza',
    'shake shack', 'dairy queen', 'culver', "culver's", 'raising cane',
    'tropical smoothie', 'smoothie king', 'jamba', 'krispy kreme',
    'tim horton', 'caribou coffee', 'dutch bros', 'scooter\'s coffee',
    'el pollo loco', 'del taco', 'moe\'s southwest', 'qdoba',
    'golden corral', 'cracker barrel', 'bob evans', 'perkins',
    'texas roadhouse', 'longhorn steakhouse', 'ruth\'s chris',
    'the cheesecake factory', 'cheesecake factory', 'bj\'s restaurant',
    'hooters', 'twin peaks', 'wingstop', 'buffalo wild wings',
    'little caesars', 'marco\'s pizza', 'hungry howie', 'cicis pizza',
    # Retail franchises
    'zales', 'kay jewelers', 'jared', 'signet jewelers',
    'gamestop', 'hot topic', 'spencer', 'bath & body', 'bath and body',
    'yankee candle', 'hallmark', 'michaels', 'hobby lobby', 'joann',
    'pier 1', 'world market', 'bed bath', 'tuesday morning',
    'ross dress', 'tj maxx', 'tjmaxx', 'marshalls', 'burlington',
    'nordstrom', 'macy', "macy's", 'sears', 'jcpenney', 'j.c. penney', 'kohl',
    'old navy', 'gap store', 'banana republic', 'express store',
    'foot locker', 'finish line', 'shoe carnival', 'famous footwear',
    'autozone', 'o\'reilly auto', 'advance auto', 'napa auto',
    'pep boys', 'discount tire', 'goodyear', 'big o tires',
    # Service franchises
    'h&r block', 'jackson hewitt', 'liberty tax',
    'kumon', 'mathnasium', 'sylvan learning', 'huntington learning',
    'sport clips', 'fantastic sams', 'cost cutters',
    'massage envy', 'hand and stone', 'european wax',
    'orangetheory', 'crossfit', 'f45 training', 'snap fitness', 'gold\'s gym',
    'curves fitness', 'la fitness', '24 hour fitness', 'lifetime fitness',
    'crunch fitness', 'equinox',
    'batteries plus', 'mattress firm', 'sleep number',
    'aaron\'s', 'rent-a-center',
    'sherwin-williams', 'benjamin moore', 'ppg paints',
    'servicemaster', 'stanley steemer', 'molly maid', 'merry maids',
    'two men and a truck', 'u-haul', 'public storage', 'extra space',
    'tire kingdom', 'ntb national tire',
    'lenscrafters', 'pearle vision', 'americas best',
    'aspen dental', 'heartland dental', 'bright now dental',
    'minute clinic', 'patient first', 'concentra',
    # Convenience / gas
    '7-eleven', '7 eleven', 'seven eleven', 'circle k', 'wawa',
    'sheetz', 'quiktrip', 'racetrac', 'casey\'s', 'pilot flying j',
    'loves travel', 'speedway', 'shell station', 'bp station',
    # Government / public entities
    'city of', 'county of', 'state of', 'town of',
    'fire department', 'police department', 'sheriff',
    'public school', 'school district',
    # Directory / contact-info headers
    'random phone numbers', 'contact number', 'email address',
    'phone number', 'mailing address',
    'contact a ',
    # Website scraping artifacts
    'store hours', '.com',
]

def _is_bad_lead_name(name):
    """Return (is_bad, reason) if the lead name looks like an SEO title, not a real business."""
    if not name or name.strip().lower() in ('there', 'unknown', 'n/a', '', 'home'):
        return True, "placeholder name"
    # All-caps short names are usually junk (HOME, INFO, etc.)
    stripped = name.strip()
    if len(stripped) <= 5 and stripped == stripped.upper() and stripped.isalpha():
        return True, "short all-caps junk name"
    lower = name.lower().strip()
    for pattern in _BAD_LEAD_PATTERNS:
        if pattern in lower:
            return True, f"SEO pattern: '{pattern}'"
    # "Best X in [City]" or "Top X in [City]" — directory/SEO entry
    import re as _re
    if _re.match(r'^(best|top|finest|leading|premier)\s+\w+.*\s+in\s+\w+', lower):
        return True, "SEO directory title (Best/Top X in City)"
    # Very long names (>=55 chars) are usually page titles
    if len(name) >= 55:
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
    Lead Intelligence Engine scores and ranks leads by probability of human contact.
    Fallback: CW23 Regime Engine reorders by segment health."""
    from lead_database import LeadDB
    db = LeadDB()
    conn = sqlite3.connect(db.db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone_number, lead_source, outcome, attempts, max_attempts,
               business_type, line_type, notes
        FROM leads 
        WHERE outcome = 'pending' AND do_not_call = 0 AND attempts < max_attempts
          AND phone_number IS NOT NULL AND phone_number != ''
          AND phone_number NOT IN (
              SELECT DISTINCT phone_number FROM leads WHERE outcome != 'pending'
          )
        ORDER BY id
        LIMIT ?
    """, (limit * 10,))  # Pull 10x — need headroom for TZ + name quality filters
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    # Lead Intelligence Engine: score and rank by contact probability
    try:
        from lead_intelligence_engine import LeadIntelligenceEngine
        engine = LeadIntelligenceEngine()
        scored = engine.score_and_rank(rows)
        # Attach score data to each lead dict and re-sort
        ranked = []
        for score_obj, lead_dict in scored:
            lead_dict['_lie_score'] = score_obj.total
            lead_dict['_lie_band'] = score_obj.band
            lead_dict['_lie_factors'] = score_obj.factors[:3]  # top 3 factors
            ranked.append(lead_dict)
        rows = ranked[:limit]
        if rows:
            top = rows[0]
            bot = ranked[-1] if len(ranked) > 1 else rows[0]
            print(f"  [LIE] Leads ranked by intelligence score ({len(ranked)} scored)")
            print(f"  [LIE] Top: {top['name'][:30]} ({top['_lie_score']} {top['_lie_band']}) | Bottom: {bot['name'][:30]} ({bot['_lie_score']} {bot['_lie_band']})")
    except Exception as e:
        print(f"  [LIE] Engine not available ({e}) — using fallback ordering")
        # CW23 Regime Engine fallback: reorder by segment health
        if REGIME_AVAILABLE and rows:
            rows = score_and_sort_leads(rows)
            print(f"  [REGIME] Leads reordered by segment health ({len(rows)} scored)")
        rows = rows[:limit]

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
    parser.add_argument("--small-city", action="store_true", dest="small_city",
                        help="Only call leads from small cities (<100K pop, no major metros)")
    parser.add_argument("--precision", action="store_true",
                        help="Enable Precision Engine: evidence-based scoring, dead lead filter, timing intelligence")
    parser.add_argument("--min-score", type=int, default=35, dest="min_score",
                        help="Minimum precision score to fire (0-100, default: 35)")
    parser.add_argument("--briefing", action="store_true",
                        help="Show precision briefing and exit")
    args = parser.parse_args()

    print("=" * 70)
    print("  SPACED CAMPAIGN LAUNCHER")
    print(f"  Target: {args.count} calls | Spacing: {args.space}s between calls")
    if args.small_city:
        print(f"  MODE: SMALL-CITY ONLY (pop <100K, no major metros)")
    if args.precision and PRECISION_AVAILABLE:
        print(f"  MODE: PRECISION ENGINE ACTIVE (min score: {args.min_score})")
    print("=" * 70)

    # ── Precision Briefing ────────────────────────────────────────────
    if args.briefing and PRECISION_AVAILABLE:
        print(generate_precision_briefing())
        return

    # ── Precision Engine: Timing Check ────────────────────────────────
    if (args.precision or PRECISION_AVAILABLE) and PRECISION_AVAILABLE:
        timing_engine = OptimalTimingEngine()
        window = timing_engine.get_current_window_quality()
        print(f"\n  [PRECISION] Current Window: {window['quality']}")
        print(f"    {window['action']}")
        print(f"    {window['day']} {window['hour']}: day={window['day_rate']}, hour={window['hour_rate']}")
        if window['quality'] == 'POOR' and not args.dry:
            next_w = timing_engine.get_next_prime_window()
            print(f"\n    NEXT PRIME: {next_w['window']}")
            print(f"    Starts: {next_w['starts_at']} ({next_w['hours_until']} from now)")
            print(f"    Proceeding anyway — but expect lower contact rates.")

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

    # ── Contact Rate Optimizer: Timing Intelligence ──────────────────
    if CRO_AVAILABLE:
        now = datetime.now()
        timing = get_call_timing_score(now.weekday(), now.hour, now.minute)
        day_name, day_score, day_note = get_day_quality(now.weekday())
        is_prime, prime_desc = is_prime_window(now.hour, now.minute)
        
        print(f"\n  [CRO] Call Timing Intelligence:")
        print(f"    Day: {day_name} (quality: {day_score}/100) — {day_note}")
        print(f"    Time: {now.strftime('%I:%M %p')} (quality: {timing['time_score']}/100)")
        prime_str = f"YES — {prime_desc}" if is_prime else "No — consider waiting for 9:30-11:30 or 1:30-3:30"
        print(f"    Prime window: {prime_str}")
        print(f"    Composite: {timing['composite']}/100 — {timing['recommendation']}")
        
        if timing['composite'] < 40 and not args.dry:
            print(f"\n  ⚠️  [CRO WARNING] Poor timing (score: {timing['composite']}/100)")
            print(f"      Best times: Tue-Thu, 9:30-11:30 AM or 1:30-3:30 PM merchant local time")
            print(f"      Proceeding anyway — but contact rate will be lower than optimal")
        
        # Local presence check
        lpm = LocalPresenceManager()
        pool_health = lpm.check_health()
        if pool_health["configured"]:
            print(f"    Local Presence: {pool_health['active']} numbers across {pool_health['area_codes_covered']} area codes")
        else:
            print(f"    Local Presence: NOT CONFIGURED — using single number (contact rate -40-60%)")

    # Get leads
    pull_factor = 5 if args.small_city else (3 if not args.no_tz else 1)
    leads = get_pending_leads(args.count * pull_factor)  # Pull extra to survive filters
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

    # ── Small-City Filter (Feb 25, 2026) ─────────────────────────────
    if args.small_city:
        small_city_leads = []
        metro_skipped = []
        for lead in leads:
            if _is_small_city_lead(lead.get('phone_number', '')):
                small_city_leads.append(lead)
            else:
                ac = _get_area_code(lead.get('phone_number', ''))
                metro_skipped.append((lead, ac))
        
        if metro_skipped:
            print(f"\n  [SMALL-CITY] Filtered out {len(metro_skipped)} major-metro leads:")
            for sl, ac in metro_skipped[:10]:  # Show first 10
                print(f"    SKIP  ({ac}) {sl['name'][:40]:40s}")
            if len(metro_skipped) > 10:
                print(f"    ... and {len(metro_skipped) - 10} more")
        
        leads = small_city_leads
        if not leads:
            print(f"\n  [!] No small-city leads found. All {len(metro_skipped)} leads are from major metros.")
            return
        print(f"\n  [SMALL-CITY] {len(leads)} leads from small cities (<100K pop)")

    # ── Precision Engine: Dead Lead Filter + Scoring ──────────────────
    if PRECISION_AVAILABLE and (args.precision or True):  # Always filter dead leads
        dlf = DeadLeadFilter()
        good_leads, dead_leads = dlf.filter(leads)
        if dead_leads:
            print(f"\n  [PRECISION] Filtered {len(dead_leads)} dead leads:")
            for dl, reason in dead_leads[:10]:
                print(f"    REJECT  {dl['name'][:40]:40s} | {reason}")
            if len(dead_leads) > 10:
                print(f"    ... and {len(dead_leads) - 10} more")
        leads = good_leads
        if not leads:
            print(f"\n  [!] All leads filtered as dead. No callable leads remain.")
            return
        
        # Score and rank by precision
        scorer = PrecisionScorer()
        now = datetime.now()
        scored = scorer.score_and_rank_leads(leads, now.weekday(), now.hour, min_score=args.min_score)
        
        if not scored:
            print(f"\n  [!] No leads meet minimum precision score ({args.min_score}).")
            print(f"      Consider lowering --min-score or waiting for better timing.")
            return
        
        # Replace leads with precision-ranked order
        leads = [lead for _, lead in scored[:args.count]]
        
        # Display precision scores
        print(f"\n  [PRECISION] Scored {len(scored)} leads (min score: {args.min_score}):")
        a_count = sum(1 for s, _ in scored if s['band'] == 'A-TIER')
        b_count = sum(1 for s, _ in scored if s['band'] == 'B-TIER')
        c_count = sum(1 for s, _ in scored if s['band'] == 'C-TIER')
        print(f"    A-tier: {a_count} | B-tier: {b_count} | C-tier: {c_count}")
        print(f"    Firing top {len(leads)} by precision score")
        
        # Attach scores to leads for display
        for score_dict, lead_dict in scored[:args.count]:
            lead_dict['_precision_score'] = score_dict['score']
            lead_dict['_precision_band'] = score_dict['band']
    else:
        # Fallback: original bad lead name filter
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
        lie_tag = ""
        cro_tag = ""
        if REGIME_AVAILABLE and "_regime_status" in lead:
            regime_tag = f" | R:{lead['_regime_status']}"
        if "_tz" in lead:
            tz_tag = f" | {lead['_tz']} ~{lead['_local_time']}"
        if "_lie_score" in lead:
            lie_tag = f" | S:{lead['_lie_score']} {lead['_lie_band']}"
        if CRO_AVAILABLE:
            dq = score_data_quality(lead)
            cro_tag = f" | DQ:{dq['expected_contact_rate']}"
        prec_tag = ""
        if "_precision_score" in lead:
            prec_tag = f" | P:{lead['_precision_score']} {lead['_precision_band']}"
        print(f"  {i:2d}. {lead['name'][:40]:40s} | {lead['phone_number']:15s} | {lead['lead_source']}{prec_tag}{lie_tag}{cro_tag}{regime_tag}{tz_tag}")

    if args.dry:
        print(f"\n  [DRY RUN] Would fire {len(leads)} calls. Exiting.")
        return

    print(f"\n  Starting in 5 seconds... (Ctrl+C to abort)")
    time.sleep(5)

    # Initialize CRO multi-touch sequencer
    mts = None
    cro_analytics = None
    if CRO_AVAILABLE:
        try:
            mts = MultiTouchSequencer()
            cro_analytics = ContactRateAnalytics()
            print("  [CRO] Multi-touch sequencer + analytics active")
        except Exception as e:
            print(f"  [CRO] Init warning: {e}")

    # Fire calls one at a time
    results = []
    for i, lead in enumerate(leads, 1):
        print(f"\n{'='*70}")
        print(f"  CALL {i}/{len(leads)}: {lead['name'][:45]}")
        print(f"  Phone: {lead['phone_number']} | Source: {lead['lead_source']}")

        # CRO: show contact probability assessment
        if CRO_AVAILABLE:
            try:
                assessment = assess_lead_contact_probability(lead)
                print(f"  CRO: {assessment['probability']} contact probability | Timing: {assessment['timing_score']}/100 | DQ: {assessment['data_quality']['expected_contact_rate']}")
            except Exception:
                pass

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
            if mts:
                try:
                    # Record as 'no_answer' at fire-time — real outcome comes via Twilio callback
                    mts.record_touch(lead.get('id', lead['phone_number']), lead['phone_number'], lead['name'], 'call', 'no_answer', call_sid=sid)
                except Exception:
                    pass
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
                if mts:
                    try:
                        mts.record_touch(lead.get('id', lead['phone_number']), lead['phone_number'], lead['name'], 'call', 'no_answer', call_sid=result.get('sid', ''))
                    except Exception:
                        pass
                results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": result.get("sid"), "status": "fired"})
            else:
                # One more wait and try
                print(f"  [!] Still blocked, waiting 40s for full clear...")
                time.sleep(40)
                result = fire_call(lead)
                if result.get("status") == "fired":
                    print(f"  [OK] 2nd retry succeeded! SID: {result.get('sid')}")
                    mark_lead_dialed(lead, call_sid=result.get('sid', ''), outcome='dialed')
                    if mts:
                        try:
                            mts.record_touch(lead.get('id', lead['phone_number']), lead['phone_number'], lead['name'], 'call', 'no_answer', call_sid=result.get('sid', ''))
                        except Exception:
                            pass
                    results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": result.get("sid"), "status": "fired"})
                else:
                    print(f"  [FAIL] Giving up on this lead: {result}")
                    if mts:
                        try:
                            mts.record_touch(lead.get('id', lead['phone_number']), lead['phone_number'], lead['name'], 'call', 'no_answer')
                        except Exception:
                            pass
                    results.append({"lead": lead["name"], "phone": lead["phone_number"], "sid": "N/A", "status": "failed"})
        else:
            print(f"  [FAIL] {result.get('message', result)}")
            if mts:
                try:
                    mts.record_touch(lead.get('id', lead['phone_number']), lead['phone_number'], lead['name'], 'call', 'no_answer')
                except Exception:
                    pass
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

    # CRO: Record session analytics + show multi-touch due actions
    # [CRO] Analytics: actual outcome recording happens in control_api_fixed.py /twilio/events
    # handler when Twilio sends the real AnsweredBy/CallStatus callbacks.
    # We do NOT record here because at fire-time we don't know if calls connected.
    if cro_analytics and fired > 0:
        print(f"\n  [CRO] {fired} calls fired — real analytics will be recorded via Twilio callbacks")

    if mts:
        try:
            due = mts.get_due_actions()
            if due:
                print(f"\n  [CRO] Multi-touch: {len(due)} follow-up actions due:")
                for action in due[:5]:
                    print(f"    - {action['business_name'][:30]} | Step {action['step_number']}: {action['action_type']} | Due: {action['scheduled_date']}")
                if len(due) > 5:
                    print(f"    ... and {len(due) - 5} more")
        except Exception as e:
            print(f"  [CRO] Multi-touch warning: {e}")

    print()
    for r in results:
        icon = "OK" if r["status"] == "fired" else "XX"
        print(f"  [{icon}] {r['lead'][:35]:35s} | {r['phone']:15s} | {r['sid'][:20]}")
    print()

if __name__ == "__main__":
    main()
