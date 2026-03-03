#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
  SOS LEAD SCRAPER v2 — Secretary of State New Business Lead Generator
  "Platinum leads with actual intent"

  FRESHNESS RULES (non-negotiable):
    0-1 days old = PRIME       (🔥 call immediately)
    2 days old   = ACCEPTABLE  (still fresh)
    3 days old   = TRANSFERRING (fresh → old, lower priority)
    4+ days      = DO NOT CONSIDER (stale — excluded)

  KEY PRINCIPLES:
    • Fresh as fresh can be — 1 day is gold
    • NO repeated filings — only brand-new formations
    • Classify by NAICS sector (what the business IS)
    • Extract owner names from registered agent / officer data
    • Track NAICS category for merchant-services targeting

  Pipeline:
    1. SCRAPE    — Pull new filings from SOS APIs (1-3 days ONLY)
    2. DEDUP     — Remove repeated filings, annual reports, re-registrations
    3. CLASSIFY  — NAICS-based business type classification
    4. FILTER    — Remove non-merchant-services businesses
    5. SCORE     — Rate by freshness × merchant potential × owner info
    6. IMPORT    — Insert into leads.db as SOS_CO_PLATINUM source

  Currently supported:
    • Colorado (Socrata Open Data API — updated daily, ~490 new/day)
═══════════════════════════════════════════════════════════════════════
"""

import requests
import re
import json
import sqlite3
import hashlib
import time
import os
import sys
import argparse
from datetime import datetime, timedelta, date
from urllib.parse import quote_plus, urlencode

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_DB  = os.path.join(BASE_DIR, "data", "leads.db")
SOS_CACHE = os.path.join(BASE_DIR, "data", "sos_cache.db")

# ── Colorado SODA API ────────────────────────────────────────────────
CO_DATASET = "4ykn-tg5h"
CO_BASE    = f"https://data.colorado.gov/resource/{CO_DATASET}.json"

# ═══════════════════════════════════════════════════════════════════
#  FRESHNESS TIERS — These are law
# ═══════════════════════════════════════════════════════════════════
FRESHNESS_TIERS = {
    0: ("PRIME",        "🔥", 100),   # Filed today
    1: ("PRIME",        "🔥", 100),   # Filed yesterday
    2: ("ACCEPTABLE",   "✓",   80),   # 2 days old
    3: ("TRANSFERRING", "⚠",   55),   # 3 days — fresh→old
    # 4+ = DO NOT CONSIDER — filtered out before scoring
}
MAX_DAYS_OLD = 3  # Hard ceiling. 4+ days = dead.

# ═══════════════════════════════════════════════════════════════════
#  ENTITY TYPES — Domestic = new businesses, Foreign = re-registrations
# ═══════════════════════════════════════════════════════════════════
TARGET_ENTITY_TYPES = {"DLLC", "DPC"}  # Domestic LLC + Domestic Profit Corp ONLY

SKIP_ENTITY_TYPES = {
    # Nonprofits
    "DNC", "FNC", "DNPC",
    # Foreign entities (re-registrations, NOT new businesses — "repeated filings")
    "FLLC", "FPC", "FNC", "FLP", "FLLP", "FLLLP", "FO", "FLPA", "FLCA",
    # Partnerships, cooperatives, trusts, etc.
    "DLP", "DLLP", "DLLLP", "GP", "UNA", "CS", "DT", "WC",
    "DC55", "DC56", "IC", "DLPA", "DLCA", "FCOOP", "CU", "SL", "SP",
    # PBC variants
    "DPC-PBC", "DLCA-PBC", "DC56-PBC", "DC55-PBC",
}

# ═══════════════════════════════════════════════════════════════════
#  REPEATED FILING DETECTION
# ═══════════════════════════════════════════════════════════════════
# Known Registered Agent / Incorporation Service company names
# These file dozens of shells per day — NOT the actual business owner
KNOWN_RA_COMPANIES = [
    "colorado registered agents",
    "northwest registered agent",
    "incorp services",
    "legalinc",
    "cogency global",
    "ct corporation",
    "csc global",
    "united states corporation agents",
    "registered agents inc",
    "nrai",
    "vcorp services",
    "harvard business services",
    "incorporate.com",
    "mybizfiling",
    "swyft filings",
    "zenbusiness",
    "legalzoom",
    "rocket lawyer",
    "bizfilings",
    "incfile",
    "sunbiz corp",
    "national registered agents",
    "paracorp",
    "blumberg excelsior",
    "corporation service company",
    "the company corporation",
    "wolters kluwer",
]

# Known Registered Agent ADDRESSES (high-volume filing mills)
KNOWN_RA_ADDRESSES = [
    "1500 N GRANT ST",        # Colorado Registered Agents Inc
    "1675 LARIMER ST",        # Various RA offices
    "7700 E ARAPAHOE RD",    # Various RA offices
    "1801 CALIFORNIA ST",    # Various RA offices
    "1999 BROADWAY",         # Various RA offices
    "1580 N LOGAN ST",       # US Corporation Agents
    "110 16TH STREET",       # Various RA offices
]

# Name patterns that indicate a repeated / shell / non-operational filing
REPEATED_FILING_PATTERNS = [
    # Holdings / series / master structures
    r'\b(series\s+[a-z0-9]|master\s+llc|holding|holdings)\b',
    # Re-registration / amendment language
    r'\b(amendment|amended|restated|conversion|merger|reorganiz)\b',
]

# ═══════════════════════════════════════════════════════════════════
#  NAICS-BASED BUSINESS CLASSIFICATION
#  Maps business name patterns to NAICS 2-digit sectors
#  with merchant-services scoring
# ═══════════════════════════════════════════════════════════════════
NAICS_CLASSIFICATION = [
    # ── NAICS 72: Accommodation and Food Services (HIGHEST INTENT) ──
    (r'\b(restaurant|cafe|coffee|bakery|pizz|grill|kitchen|catering|bar\b|pub\b|tavern|bistro|diner|eatery|taqueri|burrito|sushi|ramen|pho|bbq|barbecue|steakh|wing|donut|doughnut|bagel|deli|sandwich|juice|smoothie|ice\s*cream|frozen\s*yogurt|food\s*truck|meal\s*prep|brew\s*pub|cantina|chophouse|creamery|pastry|noodle|wok|boba|acai|poke)\b',
     "72", 98, "food_bev"),

    # ── NAICS 81: Other Services — Beauty/Personal Care ──
    (r'\b(salon|beauty|hair|barber|nail|spa\b|lash|brow|wax|facial|skin|aesthet|cosmet|tattoo|pierc|massage|wellness|medspa|med\s*spa|tanning|threading)\b',
     "81", 96, "beauty_personal"),

    # ── NAICS 81: Other Services — Auto Repair/Services ──
    (r'\b(auto\s*(repair|body|detail|wash|glass|parts|service)|mechanic|tire|brake|muffler|oil\s*change|car\s*wash|transmission|collision|windshield|smog|tune[\s-]*up|lube|alignment)\b',
     "81", 94, "auto_service"),

    # ── NAICS 44-45: Retail Trade ──
    (r'\b(boutique|store|shop\b|retail|mart\b|market(?!ing)|supply|supplies|gifts?|florist|flower|floral|pet\s*store|pet\s*shop|jewel|optical|eyewear|tobacco|vape|smoke\s*shop|thrift|consignment|pawn|antique|hobby|craft|fabric|yarn|sewing|bead|candle|comic|book\s*store|toy|game\s*store|sport\s*shop|surf\s*shop|skate\s*shop|bike\s*shop|gun\s*shop|liquor|wine\s*shop|beer\s*store|pharmacy|drugstore|convenience)\b',
     "44", 92, "retail"),

    # ── NAICS 62: Health Care — Consumer-facing ──
    (r'\b(dental|dentist|orthodont|chiropr|physioth|physical\s*therapy|optometr|veterinar|vet\s*clinic|urgent\s*care|medical\s*(spa|clinic)|dermatol|pediatr|wellness\s*center|acupunctur|naturopath|holistic|mental\s*health|counsel|therap(y|ist)|psycholog|psychiatr)\b',
     "62", 88, "healthcare"),

    # ── NAICS 71: Arts, Entertainment, Recreation ──
    (r'\b(gym|fitness|crossfit|yoga|pilates|martial\s*art|boxing|training|personal\s*train|dance\s*studio|swim|aquatic|bowling|skating|rock\s*climb|trampoline|escape\s*room|arcade|mini\s*golf|go[\s-]*kart|laser\s*tag|paintball|golf\s*course|tennis|pickleball|batting\s*cage)\b',
     "71", 86, "fitness_recreation"),

    # ── NAICS 81: Other Services — Pet Services ──
    (r'\b(dog\s*(groom|walk|board|train|daycare|sit)|pet\s*(groom|sit|care|board|hotel|resort|supply)|kennel|cattery|animal\s*(hospital|clinic|care))\b',
     "81", 82, "pet_services"),

    # ── NAICS 81: Other Services — Home Services (consumer-facing) ──
    (r'\b(plumb(ing|er)|electric(al|ian)|hvac|heat(ing)?|cool(ing)?|air\s*condition|roofing|roofer|paint(ing|er)|landscap|lawn|garden|tree\s*service|pest\s*control|clean(ing|ers)|maid|janitorial|handyman|locksmith|garage\s*door|window\s*(clean|install|repair)|carpet|flooring|fencing|gutter|pressur\s*wash|power\s*wash|pool\s*(service|clean|maintenance)|appliance\s*repair|chimney|deck|patio|remodel|renovation|restor(ation|e)|waterproof|insulation|solar)\b',
     "81", 84, "home_services"),

    # ── NAICS 72: Accommodation ──
    (r'\b(hotel|motel|inn\b|lodge|hostel|resort|bed\s*(&|and)\s*breakfast|airbnb|vacation\s*rental|glamping)\b',
     "72", 80, "accommodation"),

    # ── NAICS 54: Professional Services (consumer-facing subset) ──
    (r'\b(accounting|bookkeep|tax\s*(prepar|service)|cpas?\b|insurance|notary|tutor|music\s*lesson|driving\s*school|photo(graph)?|videograph|wedding|event\s*(plan|rent)|dj\s*service|print\s*shop|sign\s*(shop|making)|design\s*studio|graphic\s*design|web\s*design|marketing\s*agency)\b',
     "54", 78, "professional_svc"),

    # ── NAICS 61: Educational Services ──
    (r'\b(daycare|childcare|preschool|montessori|learning\s*center|tutoring|after[\s-]*school|summer\s*camp|music\s*school|art\s*school|dance\s*school|swim\s*school|karate|coding\s*(school|camp|academy)|driver\'?s?\s*ed)\b',
     "61", 76, "education"),

    # ── NAICS 48-49: Transportation (consumer-facing) ──
    (r'\b(moving|movers|storage|pack(ing|ers)|relocat|courier|delivery|freight|trucking|towing|limo(usine)?|shuttle|taxi|rideshare)\b',
     "48", 70, "transportation"),

    # ── NAICS 51: Information / Tech Services ──
    (r'\b(computer\s*repair|it\s*support|tech\s*support|phone\s*repair|screen\s*repair|data\s*recovery|managed\s*service|cloud\s*service)\b',
     "51", 72, "tech_service"),
]

# ═══════════════════════════════════════════════════════════════════
#  SKIP PATTERNS — businesses that DON'T need merchant card processing
# ═══════════════════════════════════════════════════════════════════
SKIP_NAME_PATTERNS = [
    # Real estate / property / land
    r'\b(real\s*estate|realty|properties|property|holdings?|rentals?)\b',
    r'\b(land\b|lot\b|acres|home\s*buyers?|housing|apartments?)\b',
    r'\b(mortgage|title\s*(co|company|service)|escrow|closing)\b',

    # Investment / finance / holding / shell
    r'\b(invest(ment|ing|ors?)|capital|ventures?|fund\b|equity|assets?)\b',
    r'\b(trust|trusts|fiduciary|hedge|portfolio)\b',
    r'\b(financial|finance|banking|securities)\b',

    # Consulting / management (B2B, invoice-based)
    r'\b(consulting|consultants?|advisory|advisors?)\b',
    r'\bmanagement\s+(company|co|corp|group|llc|inc)\b',

    # Legal structures / shell companies
    r'\b(registered\s+agent|statutory\s+agent)\b',
    r'\b(series\s+llc|master\s+llc)\b',

    # Heavy construction / B2B contracting
    r'\b(general\s+contract(or|ing)|subcontract)\b',
    r'\b(excavat|demolition|paving|asphalt)\b',

    # Mining / oil / gas / agriculture
    r'\b(mining|mineral|petroleum|oil\s+(&|and)\s+gas|drilling|fracking)\b',
    r'\b(ranch|farm|cattle|livestock|grain|crop|harvest|dairy|poultry|hatchery)\b',

    # Nonprofit keywords that slip through entity type filter
    r'\b(foundation|charitable|charity|ministry|ministries|church)\b',
    r'\b(outreach|mission\b|fellowship|congregation)\b',

    # Cannabis (can't process standard merchant services)
    r'\b(cannabis|marijuana|dispensary|weed\b|hemp\b|cbd\b)\b',

    # Crypto / blockchain
    r'\b(crypto|blockchain|bitcoin|nft\b|token|defi\b|dao\b)\b',

    # Staffing / temp agencies (B2B)
    r'\b(staffing|temp\s*(agency|service)|recruitment|headhunt)\b',

    # Wholesale / distribution (B2B)
    r'\b(wholesale|distribut(or|ion)|import|export)\b',

    # Insurance / financial services (heavy regulation)
    r'\b(insurance\s+(agency|broker|co)|underwrit|actuari|claims?\s+adjust)\b',

    # Logistics / freight brokerage (B2B)
    r'\b(logistics|freight\s*broker|supply\s*chain|warehouse(?!.*sale))\b',
]


# ═══════════════════════════════════════════════════════════════════
#  OWNER NAME EXTRACTION
# ═══════════════════════════════════════════════════════════════════
def extract_owner_info(entity):
    """
    Extract the owner/organizer name from SOS data.
    Colorado provides agent info which is often the owner for small LLCs.
    Returns dict with name parts, full name, and confidence level.
    """
    first = (entity.get("agentfirstname") or "").strip()
    middle = (entity.get("agentmiddlename") or "").strip()
    last = (entity.get("agentlastname") or "").strip()
    org = (entity.get("agentorganizationname") or "").strip()

    # If agent is an organization, check if it's a known RA company
    if org:
        org_lower = org.lower()
        is_ra_company = any(ra in org_lower for ra in KNOWN_RA_COMPANIES)
        if is_ra_company:
            return {
                "owner_name": None,
                "owner_first": None,
                "owner_last": None,
                "agent_org": org,
                "is_ra_service": True,
                "confidence": "none",
            }
        # Org name that's NOT a known RA — might be the actual business or related entity
        return {
            "owner_name": None,
            "owner_first": None,
            "owner_last": None,
            "agent_org": org,
            "is_ra_service": False,
            "confidence": "low",
        }

    # Individual agent — likely the owner/organizer for a brand-new LLC
    if first and last:
        parts = [first.title(), middle.title(), last.title()] if middle else [first.title(), last.title()]
        full = " ".join(parts)
        return {
            "owner_name": full,
            "owner_first": first.title(),
            "owner_last": last.title(),
            "agent_org": None,
            "is_ra_service": False,
            "confidence": "high",
        }

    return {
        "owner_name": None,
        "owner_first": None,
        "owner_last": None,
        "agent_org": None,
        "is_ra_service": False,
        "confidence": "none",
    }


# ═══════════════════════════════════════════════════════════════════
#  CACHE DB — Track seen entities, avoid re-processing
# ═══════════════════════════════════════════════════════════════════
def init_sos_cache():
    """Create cache DB to track seen entities and avoid re-processing."""
    os.makedirs(os.path.dirname(SOS_CACHE), exist_ok=True)
    conn = sqlite3.connect(SOS_CACHE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_entities (
            entity_id    TEXT PRIMARY KEY,
            entity_name  TEXT,
            state        TEXT,
            formed_date  TEXT,
            freshness    TEXT,
            naics_cat    TEXT,
            score        INTEGER DEFAULT 0,
            owner_name   TEXT,
            imported     INTEGER DEFAULT 0,
            first_seen   TEXT DEFAULT (datetime('now')),
            raw_json     TEXT
        )
    """)
    conn.commit()
    return conn


# ═══════════════════════════════════════════════════════════════════
#  STEP 1: SCRAPE — Colorado SOS via Socrata API
# ═══════════════════════════════════════════════════════════════════
def scrape_colorado(max_days=MAX_DAYS_OLD, limit=1000):
    """
    Pull new DOMESTIC business formations from Colorado SOS.
    Only pulls entities formed within max_days (default 3, hard max 3).
    Foreign entities (FLLC, FPC, etc.) are excluded — they are re-registrations
    of businesses that already exist elsewhere, not true new formations.
    """
    today = date.today()
    since_date = (today - timedelta(days=max_days)).strftime("%Y-%m-%dT00:00:00.000")

    # Only domestic entities (DLLC, DPC) — foreign = re-registrations
    type_filter = " OR ".join(f"entitytype='{t}'" for t in TARGET_ENTITY_TYPES)
    where_clause = (
        f"entityformdate >= '{since_date}' "
        f"AND ({type_filter}) "
        f"AND entitystatus='Good Standing'"
    )

    params = {
        "$where": where_clause,
        "$order": "entityformdate DESC",
        "$limit": limit,
    }

    url = f"{CO_BASE}?{urlencode(params)}"
    print(f"\n  [CO] Querying Socrata API...")
    print(f"  [CO] Window: {since_date[:10]} → {today} ({max_days} days, DOMESTIC ONLY)")
    print(f"  [CO] Entity types: {sorted(TARGET_ENTITY_TYPES)}")

    try:
        resp = requests.get(url, timeout=30, headers={"Accept": "application/json"})
        resp.raise_for_status()
        entities = resp.json()
        print(f"  [CO] Retrieved {len(entities)} entities")
        return entities
    except Exception as e:
        print(f"  [CO] ERROR: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
#  STEP 2: DEDUP — Remove repeated / shell / junk filings
# ═══════════════════════════════════════════════════════════════════
def detect_repeated_filing(entity):
    """
    Detect repeated filings, shell entities, and junk.
    Returns (is_repeated: bool, reason: str).
    """
    name = (entity.get("entityname") or "").strip()
    addr = (entity.get("principaladdress1") or "").upper()
    org = (entity.get("agentorganizationname") or "").lower()

    # 1. Name patterns that indicate re-filing / amendments / holdings
    for pattern in REPEATED_FILING_PATTERNS:
        if re.search(pattern, name, re.IGNORECASE):
            return True, f"shell_pattern: {name[:50]}"

    # 2. Gibberish entity names (random letters — shell LLCs)
    name_no_suffix = re.sub(
        r'\s*(LLC|Inc|Corp|L\.?L\.?C\.?|Inc\.?|Corp\.?|Co\.?|Company|Group|Enterprises?)\s*\.?\s*$',
        '', name, flags=re.IGNORECASE
    ).strip()

    if name_no_suffix and len(name_no_suffix) >= 4:
        alpha_only = re.sub(r'[^a-zA-Z]', '', name_no_suffix)
        if alpha_only and len(alpha_only) >= 4:
            vowel_ratio = sum(1 for c in alpha_only.lower() if c in 'aeiou') / len(alpha_only)
            if vowel_ratio < 0.15:  # Less than 15% vowels = likely gibberish
                return True, f"gibberish_name: {name}"

    # 3. Known RA company as agent — flag for scoring but don't auto-reject
    if org:
        for ra in KNOWN_RA_COMPANIES:
            if ra in org:
                entity["_uses_ra_service"] = True
                break

    # 4. Known RA addresses as principal address — likely shell
    for ra_addr in KNOWN_RA_ADDRESSES:
        if ra_addr in addr:
            entity["_uses_ra_address"] = True
            # If BOTH agent is RA company AND address is RA address = very likely shell
            if entity.get("_uses_ra_service"):
                return True, f"ra_shell: RA agent + RA address"
            break

    # 5. Name too short or just initials
    if len(name_no_suffix) < 2:
        return True, f"name_too_short: {name}"
    if re.match(r'^[A-Z]{1,3}$', name_no_suffix):
        return True, f"initials_only: {name}"

    return False, "ok"


# ═══════════════════════════════════════════════════════════════════
#  STEP 3: CLASSIFY — NAICS-based business type detection
# ═══════════════════════════════════════════════════════════════════
def classify_business(entity):
    """
    Classify business type using NAICS-aligned pattern matching on name.
    Returns (naics_sector, merchant_score, category_label).
    """
    name = (entity.get("entityname") or "").strip()
    name_lower = name.lower()

    best_match = None
    best_score = 0

    for pattern, naics, score, category in NAICS_CLASSIFICATION:
        if re.search(pattern, name_lower, re.IGNORECASE):
            if score > best_score:
                best_match = (naics, score, category)
                best_score = score

    if best_match:
        return best_match

    # Can't classify from name alone — generic business
    return ("99", 50, "unclassified")


# ═══════════════════════════════════════════════════════════════════
#  STEP 4: FILTER — Remove non-merchant-services businesses
# ═══════════════════════════════════════════════════════════════════
def filter_entity(entity):
    """
    Filter out entities that are NOT good merchant-services leads.
    Returns (passed: bool, reason: str).
    """
    name = (entity.get("entityname") or "").strip()
    etype = (entity.get("entitytype") or "").strip()

    # Skip non-target entity types
    if etype not in TARGET_ENTITY_TYPES:
        return False, f"wrong_type:{etype}"

    # Skip if no name
    if not name or len(name) < 3:
        return False, "no_name"

    # Apply skip patterns (non-merchant-services businesses)
    name_lower = name.lower()
    for pattern in SKIP_NAME_PATTERNS:
        if re.search(pattern, name_lower, re.IGNORECASE):
            return False, "skip_pattern"

    return True, "passed"


# ═══════════════════════════════════════════════════════════════════
#  STEP 5: SCORE — Freshness × Merchant Potential × Data Quality
# ═══════════════════════════════════════════════════════════════════
def compute_freshness(entity):
    """
    Compute freshness tier based on formation date.
    Returns (days_old, tier_name, tier_icon, tier_score).
    """
    formed = entity.get("entityformdate", "")
    if not formed:
        return 99, "UNKNOWN", "?", 0

    try:
        formed_date = datetime.fromisoformat(formed.split("T")[0]).date()
        days_old = (date.today() - formed_date).days
    except Exception:
        return 99, "UNKNOWN", "?", 0

    if days_old > MAX_DAYS_OLD:
        return days_old, "STALE", "✗", 0

    tier = FRESHNESS_TIERS.get(days_old, FRESHNESS_TIERS[MAX_DAYS_OLD])
    return days_old, tier[0], tier[1], tier[2]


def score_entity(entity):
    """
    Composite score across three dimensions:
      Freshness       (40%) — 1d=🔥, 2d=✓, 3d=⚠
      Merchant Score  (40%) — from NAICS classification
      Data Quality    (20%) — owner info, address, location
    Scale: 0-100.
    """
    # ── Freshness (40% weight) ──
    days_old, tier_name, tier_icon, freshness_score = compute_freshness(entity)
    entity["_days_old"] = days_old
    entity["_freshness_tier"] = tier_name
    entity["_freshness_icon"] = tier_icon

    if tier_name == "STALE":
        entity["_score"] = 0
        entity["_score_breakdown"] = "STALE (4+ days)"
        return 0

    # ── Merchant Potential (40% weight, from NAICS classification) ──
    naics, merchant_score, category = classify_business(entity)
    entity["_naics_sector"] = naics
    entity["_category"] = category
    entity["_merchant_score"] = merchant_score

    # ── Data Quality (20% weight) ──
    quality_score = 50  # base
    owner = extract_owner_info(entity)
    entity["_owner"] = owner

    if owner["owner_name"]:
        quality_score += 25  # Has owner name = huge value
    if owner["is_ra_service"]:
        quality_score -= 15  # Using RA service (less likely owner-operated)
    if entity.get("_uses_ra_address"):
        quality_score -= 10  # RA address

    addr = (entity.get("principaladdress1") or "").strip()
    if addr and "PO BOX" not in addr.upper() and "P.O." not in addr.upper():
        quality_score += 10  # Has street address (real location)
    if (entity.get("principalstate") or "").upper() == "CO":
        quality_score += 5   # Local Colorado business

    quality_score = max(0, min(100, quality_score))
    entity["_quality_score"] = quality_score

    # ── Composite ──
    composite = (
        freshness_score * 0.40 +
        merchant_score  * 0.40 +
        quality_score   * 0.20
    )

    # Bonus: high-value NAICS categories get a bump
    if category in ("food_bev", "beauty_personal", "auto_service", "retail"):
        composite = min(composite + 5, 100)

    entity["_score"] = round(composite)
    entity["_score_breakdown"] = f"F:{freshness_score} M:{merchant_score} Q:{quality_score}"
    return round(composite)


# ═══════════════════════════════════════════════════════════════════
#  STEP 6: IMPORT — Push to leads.db
# ═══════════════════════════════════════════════════════════════════
def import_to_leads_db(entities, dry_run=False):
    """
    Import qualified entities into leads.db.
    SOS leads without phone numbers are stored for later enrichment.
    """
    conn = sqlite3.connect(LEADS_DB)
    imported = 0
    skipped_dup = 0

    for entity in entities:
        name = entity.get("entityname", "Unknown")
        city = entity.get("principalcity", "")
        state = entity.get("principalstate", "CO")
        score = entity.get("_score", 0)
        category = entity.get("_category", "general")
        formed = (entity.get("entityformdate") or "")[:10]
        entity_id = entity.get("entityid", "")
        owner = entity.get("_owner", {})
        freshness = entity.get("_freshness_tier", "?")
        days_old = entity.get("_days_old", 99)

        # Deterministic ID based on SOS entity
        lead_id = hashlib.md5(f"SOS_CO_{entity_id}".encode()).hexdigest()[:16]
        existing = conn.execute("SELECT id FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if existing:
            skipped_dup += 1
            continue

        # Business type with NAICS label
        naics = entity.get("_naics_sector", "99")
        biz_type = f"New {category.replace('_', ' ').title()}"
        if city:
            biz_type += f" in {city.title()}, {state}"

        # Rich notes with all SOS data
        notes = json.dumps({
            "sos_entity_id": entity_id,
            "sos_state": state,
            "formed_date": formed,
            "freshness": freshness,
            "days_old": days_old,
            "naics_sector": naics,
            "naics_category": category,
            "owner_name": owner.get("owner_name"),
            "owner_first": owner.get("owner_first"),
            "owner_last": owner.get("owner_last"),
            "agent_org": owner.get("agent_org"),
            "principal_address": entity.get("principaladdress1", ""),
            "principal_city": city,
            "principal_state": state,
            "principal_zip": entity.get("principalzipcode", ""),
            "entity_type": entity.get("entitytype", ""),
            "sos_score": score,
            "score_breakdown": entity.get("_score_breakdown", ""),
            "merchant_score": entity.get("_merchant_score", 0),
        })

        # Priority from freshness + score
        if freshness == "PRIME" and score >= 75:
            priority = "high"
        elif freshness in ("PRIME", "ACCEPTABLE") and score >= 60:
            priority = "medium"
        else:
            priority = "low"

        if dry_run:
            owner_display = owner.get("owner_name") or "—"
            print(f"    [{freshness:12}] {name[:40]:40} | {city[:15]:15} | owner={owner_display[:20]:20} | S:{score} | {priority}")
            imported += 1
            continue

        try:
            # Store WITHOUT phone — SOS leads need separate phone enrichment
            conn.execute("""
                INSERT OR IGNORE INTO leads
                (id, phone_number, name, business_type, priority, outcome,
                 line_type, lead_source, notes, created_at, attempts, max_attempts, do_not_call)
                VALUES (?, '', ?, ?, ?, 'pending',
                        'unknown', 'SOS_CO_PLATINUM', ?, datetime('now'), 0, 3, 0)
            """, (lead_id, name, biz_type, priority, notes))
            imported += 1
        except Exception as e:
            print(f"    [ERR] {name}: {e}")

    conn.commit()
    conn.close()
    return imported, skipped_dup


# ═══════════════════════════════════════════════════════════════════
#  DISPLAY — Pretty-print results grouped by freshness tier
# ═══════════════════════════════════════════════════════════════════
def display_results(entities, top_n=40):
    """Display scored entities grouped by freshness tier."""
    sorted_ents = sorted(entities, key=lambda x: (-x.get("_score", 0), x.get("_days_old", 99)))

    # Group by freshness
    tiers = {"PRIME": [], "ACCEPTABLE": [], "TRANSFERRING": []}
    for e in sorted_ents:
        tier = e.get("_freshness_tier", "?")
        if tier in tiers:
            tiers[tier].append(e)

    total_shown = 0
    for tier_name, tier_entities in tiers.items():
        if not tier_entities or total_shown >= top_n:
            continue

        icon = {"PRIME": "🔥", "ACCEPTABLE": "✓", "TRANSFERRING": "⚠"}.get(tier_name, "?")
        print(f"\n  {'─'*80}")
        print(f"  {icon} {tier_name} ({len(tier_entities)} leads)")
        print(f"  {'─'*80}")

        for e in tier_entities:
            if total_shown >= top_n:
                break
            total_shown += 1

            name = (e.get("entityname") or "?")[:40]
            city = (e.get("principalcity") or "?")[:15]
            score = e.get("_score", 0)
            cat = e.get("_category", "?")[:16]
            formed = (e.get("entityformdate") or "")[:10]
            owner = e.get("_owner", {})
            owner_name = owner.get("owner_name") or "—"
            days = e.get("_days_old", "?")

            # Score band
            if score >= 85:
                band = "PLATINUM"
            elif score >= 70:
                band = "GOLD"
            elif score >= 55:
                band = "SILVER"
            else:
                band = "BRONZE"

            print(f"    [{score:3}] {band:8} | {name:40} | {city:15} | {cat:16} | {formed} | Owner: {owner_name[:25]}")


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="SOS Lead Scraper v2 — Platinum Lead Generator")
    parser.add_argument("--days", type=int, default=MAX_DAYS_OLD,
                        help=f"Max days old (default: {MAX_DAYS_OLD}, hard max: 3)")
    parser.add_argument("--limit", type=int, default=1000,
                        help="Max entities to pull from API (default: 1000)")
    parser.add_argument("--import", action="store_true", dest="do_import",
                        help="Import qualified leads to leads.db")
    parser.add_argument("--dry", action="store_true",
                        help="Dry run — show what would import")
    parser.add_argument("--min-score", type=int, default=55,
                        help="Min score for display/import (default: 55)")
    parser.add_argument("--state", type=str, default="CO",
                        help="State to scrape (default: CO)")
    parser.add_argument("--top", type=int, default=40,
                        help="Show top N results (default: 40)")
    args = parser.parse_args()

    # Enforce max 3 days — non-negotiable
    if args.days > MAX_DAYS_OLD:
        print(f"  [!] --days capped at {MAX_DAYS_OLD} (you asked {args.days}). SOS leads >3 days = stale.")
        args.days = MAX_DAYS_OLD

    print("=" * 80)
    print("  SOS LEAD SCRAPER v2 — Platinum Leads with Intent")
    print(f"  State: {args.state} | Freshness Window: {args.days} days MAX")
    print(f"  Tiers: 0-1d=🔥PRIME | 2d=✓ACCEPTABLE | 3d=⚠TRANSFERRING | 4d+=✗REJECTED")
    print("=" * 80)

    cache_conn = init_sos_cache()

    # ── STEP 1: SCRAPE ───────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  STEP 1: SCRAPING SOS DATA (Domestic formations only)")
    print(f"{'─'*65}")

    if args.state.upper() == "CO":
        raw = scrape_colorado(max_days=args.days, limit=args.limit)
    else:
        print(f"  [!] State '{args.state}' not yet supported.")
        return

    if not raw:
        print("  [!] No entities found.")
        return

    # ── STEP 2: DEDUP ────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  STEP 2: REMOVING REPEATED FILINGS & SHELLS")
    print(f"{'─'*65}")

    deduped = []
    repeat_stats = {}
    for entity in raw:
        is_repeat, reason = detect_repeated_filing(entity)
        if is_repeat:
            bucket = reason.split(":")[0]
            repeat_stats[bucket] = repeat_stats.get(bucket, 0) + 1
        else:
            deduped.append(entity)

    repeats_removed = len(raw) - len(deduped)
    print(f"  [DEDUP] {len(raw)} raw → {len(deduped)} unique ({repeats_removed} repeated/shell removed)")
    for reason, count in sorted(repeat_stats.items(), key=lambda x: -x[1]):
        print(f"    REMOVED ({count:3}): {reason}")

    # ── STEP 3+4: CLASSIFY + FILTER ─────────────────────────────
    print(f"\n{'─'*65}")
    print("  STEP 3: CLASSIFYING (NAICS) & FILTERING")
    print(f"{'─'*65}")

    filtered = []
    filter_stats = {}
    for entity in deduped:
        passed, reason = filter_entity(entity)
        if passed:
            filtered.append(entity)
        else:
            bucket = reason.split(":")[0] if ":" in reason else reason
            filter_stats[bucket] = filter_stats.get(bucket, 0) + 1

    print(f"  [FILTER] {len(deduped)} deduped → {len(filtered)} passed ({len(deduped) - len(filtered)} filtered)")
    for reason, count in sorted(filter_stats.items(), key=lambda x: -x[1])[:10]:
        print(f"    SKIP ({count:3}): {reason}")

    # ── STEP 5: SCORE ────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print("  STEP 4: SCORING (Freshness × Merchant Potential × Quality)")
    print(f"{'─'*65}")

    for entity in filtered:
        score_entity(entity)

    # Freshness tier counts
    tier_counts = {}
    for e in filtered:
        tier = e.get("_freshness_tier", "?")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    print(f"  [FRESHNESS TIERS]")
    for tier in ["PRIME", "ACCEPTABLE", "TRANSFERRING"]:
        ct = tier_counts.get(tier, 0)
        icon = {"PRIME": "🔥", "ACCEPTABLE": "✓", "TRANSFERRING": "⚠"}.get(tier, "?")
        print(f"    {icon} {tier:14} {ct:4} leads")

    # NAICS category distribution
    cat_counts = {}
    for e in filtered:
        cat = e.get("_category", "unclassified")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    print(f"\n  [NAICS CLASSIFICATION]")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"    {cat:20} {count:4} leads")

    # Score bands
    scores = [e["_score"] for e in filtered]
    plat = sum(1 for s in scores if s >= 85)
    gold = sum(1 for s in scores if 70 <= s < 85)
    silver = sum(1 for s in scores if 55 <= s < 70)
    bronze = sum(1 for s in scores if s < 55)
    print(f"\n  [SCORE BANDS]")
    print(f"    PLATINUM (85+): {plat}")
    print(f"    GOLD   (70-84): {gold}")
    print(f"    SILVER (55-69): {silver}")
    print(f"    BRONZE  (<55) : {bronze}")

    # Owner data stats
    with_owner = sum(1 for e in filtered if e.get("_owner", {}).get("owner_name"))
    ra_service = sum(1 for e in filtered if e.get("_owner", {}).get("is_ra_service"))
    print(f"\n  [OWNER DATA]")
    print(f"    With owner name:  {with_owner}/{len(filtered)} ({round(with_owner/max(len(filtered),1)*100)}%)")
    print(f"    Using RA service: {ra_service}/{len(filtered)}")

    # Filter by min score
    qualified = [e for e in filtered if e["_score"] >= args.min_score]
    print(f"\n  [QUALIFIED] {len(qualified)} leads score >= {args.min_score}")

    # ── DISPLAY ──────────────────────────────────────────────────
    display_results(qualified, top_n=args.top)

    # ── IMPORT ───────────────────────────────────────────────────
    if args.do_import or args.dry:
        print(f"\n{'─'*65}")
        print(f"  {'DRY RUN' if args.dry else 'IMPORTING TO LEADS DB'}")
        print(f"{'─'*65}")
        imported, dupes = import_to_leads_db(qualified, dry_run=args.dry)
        print(f"\n  [IMPORT] Processed: {imported} | Duplicates skipped: {dupes}")

    # ── Cache results ────────────────────────────────────────────
    for e in qualified:
        try:
            cache_conn.execute("""
                INSERT OR REPLACE INTO seen_entities
                (entity_id, entity_name, state, formed_date, freshness, naics_cat, score, owner_name, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                e.get("entityid", ""),
                e.get("entityname", ""),
                args.state,
                (e.get("entityformdate") or "")[:10],
                e.get("_freshness_tier", "?"),
                e.get("_category", "?"),
                e.get("_score", 0),
                e.get("_owner", {}).get("owner_name", ""),
                json.dumps({k: v for k, v in e.items() if not k.startswith("_")}),
            ))
        except Exception:
            pass
    cache_conn.commit()
    cache_conn.close()

    # ── Summary ──────────────────────────────────────────────────
    print(f"\n{'='*80}")
    with_owner_q = sum(1 for e in qualified if e.get("_owner", {}).get("owner_name"))
    prime = sum(1 for e in qualified if e.get("_freshness_tier") == "PRIME")
    classified = sum(1 for e in qualified if e.get("_category") != "unclassified")
    print(f"  SUMMARY: {len(raw)} scraped → {len(deduped)} deduped → {len(filtered)} filtered → {len(qualified)} qualified")
    print(f"  🔥 {prime} PRIME leads | {with_owner_q} with owner names | {classified} NAICS-classified")
    print(f"  NOTE: SOS leads need phone enrichment before calling.")
    print(f"        Use --dry to preview import, --import to store in leads.db")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
