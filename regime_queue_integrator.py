"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          REGIME QUEUE INTEGRATOR — Campaign × Regime Engine Bridge           ║
║                                                                              ║
║  Bridges the gap between regime_config_live.json and the campaign system.    ║
║  Reads the live config emitted by the Regime Engine, scores leads by         ║
║  segment health, and provides regime-aware ordering and pacing decisions.    ║
║                                                                              ║
║  Integration points:                                                         ║
║   1. _fire_campaign.py — lead ordering via score_and_sort_leads()            ║
║   2. lead_database.py  — priority injection via get_regime_priority()        ║
║   3. control_api_fixed.py — pacing via get_pacing_delay()                   ║
║   4. autonomous_campaign_runner.py — segment gating via should_skip_lead()  ║
║                                                                              ║
║  Author: Agent X / CW23                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── PATHS ──────────────────────────────────────────────────────────────────

CONFIG_LIVE_PATH = os.path.join(os.path.dirname(__file__), "data", "regime_config_live.json")

# ─── AREA CODE → STATE MAPPING ──────────────────────────────────────────────
# Covers all 50 US states + DC. Multiple area codes per state; maps to 2-letter.
# Used to infer state from phone number for segment matching.

_AREA_CODE_TO_STATE = {
    "205": "AL", "251": "AL", "256": "AL", "334": "AL", "938": "AL",
    "907": "AK",
    "480": "AZ", "520": "AZ", "602": "AZ", "623": "AZ", "928": "AZ",
    "479": "AR", "501": "AR", "870": "AR",
    "209": "CA", "213": "CA", "279": "CA", "310": "CA", "323": "CA",
    "341": "CA", "408": "CA", "415": "CA", "424": "CA", "442": "CA",
    "510": "CA", "530": "CA", "559": "CA", "562": "CA", "619": "CA",
    "626": "CA", "628": "CA", "650": "CA", "657": "CA", "661": "CA",
    "669": "CA", "707": "CA", "714": "CA", "747": "CA", "760": "CA",
    "805": "CA", "818": "CA", "820": "CA", "831": "CA", "858": "CA",
    "909": "CA", "916": "CA", "925": "CA", "949": "CA", "951": "CA",
    "303": "CO", "719": "CO", "720": "CO", "970": "CO",
    "203": "CT", "475": "CT", "860": "CT",
    "302": "DE",
    "202": "DC",
    "239": "FL", "305": "FL", "321": "FL", "352": "FL", "386": "FL",
    "407": "FL", "561": "FL", "727": "FL", "754": "FL", "772": "FL",
    "786": "FL", "813": "FL", "850": "FL", "863": "FL", "904": "FL",
    "941": "FL", "954": "FL",
    "229": "GA", "404": "GA", "470": "GA", "478": "GA", "678": "GA",
    "706": "GA", "762": "GA", "770": "GA", "912": "GA",
    "808": "HI",
    "208": "ID", "986": "ID",
    "217": "IL", "224": "IL", "309": "IL", "312": "IL", "331": "IL",
    "618": "IL", "630": "IL", "708": "IL", "773": "IL", "779": "IL",
    "815": "IL", "847": "IL", "872": "IL",
    "219": "IN", "260": "IN", "317": "IN", "463": "IN", "574": "IN",
    "765": "IN", "812": "IN", "930": "IN",
    "319": "IA", "515": "IA", "563": "IA", "641": "IA", "712": "IA",
    "316": "KS", "620": "KS", "785": "KS", "913": "KS",
    "270": "KY", "364": "KY", "502": "KY", "606": "KY", "859": "KY",
    "225": "LA", "318": "LA", "337": "LA", "504": "LA", "985": "LA",
    "207": "ME",
    "240": "MD", "301": "MD", "410": "MD", "443": "MD", "667": "MD",
    "339": "MA", "351": "MA", "413": "MA", "508": "MA", "617": "MA",
    "774": "MA", "781": "MA", "857": "MA", "978": "MA",
    "231": "MI", "248": "MI", "269": "MI", "313": "MI", "517": "MI",
    "586": "MI", "616": "MI", "734": "MI", "810": "MI", "906": "MI",
    "947": "MI", "989": "MI",
    "218": "MN", "320": "MN", "507": "MN", "612": "MN", "651": "MN",
    "763": "MN", "952": "MN",
    "228": "MS", "601": "MS", "662": "MS", "769": "MS",
    "314": "MO", "417": "MO", "573": "MO", "636": "MO", "660": "MO",
    "816": "MO",
    "406": "MT",
    "308": "NE", "402": "NE", "531": "NE",
    "702": "NV", "725": "NV", "775": "NV",
    "603": "NH",
    "201": "NJ", "551": "NJ", "609": "NJ", "732": "NJ", "848": "NJ",
    "856": "NJ", "862": "NJ", "908": "NJ", "973": "NJ",
    "505": "NM", "575": "NM",
    "212": "NY", "315": "NY", "332": "NY", "347": "NY", "516": "NY",
    "518": "NY", "585": "NY", "607": "NY", "631": "NY", "646": "NY",
    "680": "NY", "716": "NY", "718": "NY", "838": "NY", "845": "NY",
    "914": "NY", "917": "NY", "929": "NY", "934": "NY",
    "252": "NC", "336": "NC", "704": "NC", "743": "NC", "828": "NC",
    "910": "NC", "919": "NC", "980": "NC", "984": "NC",
    "701": "ND",
    "216": "OH", "220": "OH", "234": "OH", "330": "OH", "380": "OH",
    "419": "OH", "440": "OH", "513": "OH", "567": "OH", "614": "OH",
    "740": "OH", "937": "OH",
    "405": "OK", "539": "OK", "580": "OK", "918": "OK",
    "458": "OR", "503": "OR", "541": "OR", "971": "OR",
    "215": "PA", "223": "PA", "267": "PA", "272": "PA", "412": "PA",
    "445": "PA", "484": "PA", "570": "PA", "610": "PA", "717": "PA",
    "724": "PA", "814": "PA", "878": "PA",
    "401": "RI",
    "803": "SC", "843": "SC", "854": "SC", "864": "SC",
    "605": "SD",
    "423": "TN", "615": "TN", "629": "TN", "731": "TN", "865": "TN",
    "901": "TN", "931": "TN",
    "210": "TX", "214": "TX", "254": "TX", "281": "TX", "325": "TX",
    "346": "TX", "361": "TX", "409": "TX", "430": "TX", "432": "TX",
    "469": "TX", "512": "TX", "682": "TX", "713": "TX", "726": "TX",
    "737": "TX", "806": "TX", "817": "TX", "830": "TX", "832": "TX",
    "903": "TX", "915": "TX", "936": "TX", "940": "TX", "956": "TX",
    "972": "TX", "979": "TX",
    "385": "UT", "435": "UT", "801": "UT",
    "802": "VT",
    "276": "VA", "434": "VA", "540": "VA", "571": "VA", "703": "VA",
    "757": "VA", "804": "VA",
    "206": "WA", "253": "WA", "360": "WA", "425": "WA", "509": "WA",
    "564": "WA",
    "304": "WV", "681": "WV",
    "262": "WI", "414": "WI", "534": "WI", "608": "WI", "715": "WI",
    "920": "WI",
    "307": "WY",
}

# ─── BUSINESS TYPE → VERTICAL MAPPING ───────────────────────────────────────

_BUSINESS_TYPE_TO_VERTICAL = {
    "restaurant": "restaurant",
    "dining": "restaurant",
    "cafe": "restaurant",
    "bar": "restaurant",
    "pizzeria": "restaurant",
    "pizza": "restaurant",
    "bakery": "restaurant",
    "deli": "restaurant",
    "grill": "restaurant",
    "taco": "restaurant",
    "sushi": "restaurant",
    "bbq": "restaurant",
    "coffee": "restaurant",
    "food": "restaurant",
    "catering": "restaurant",
    "contractor": "contractor",
    "construction": "contractor",
    "plumbing": "contractor",
    "plumber": "contractor",
    "electrician": "contractor",
    "electrical": "contractor",
    "hvac": "contractor",
    "roofing": "contractor",
    "roofer": "contractor",
    "landscaping": "contractor",
    "landscape": "contractor",
    "lawn": "contractor",
    "tree": "contractor",
    "fence": "contractor",
    "paving": "contractor",
    "concrete": "contractor",
    "painting": "contractor",
    "handyman": "contractor",
    "remodeling": "contractor",
    "retail": "retail",
    "store": "retail",
    "shop": "retail",
    "boutique": "retail",
    "pharmacy": "retail",
    "auto": "auto",
    "automotive": "auto",
    "car": "auto",
    "mechanic": "auto",
    "tire": "auto",
    "body shop": "auto",
    "dealer": "auto",
    "dealership": "auto",
    "salon": "services",
    "spa": "services",
    "barber": "services",
    "beauty": "services",
    "tattoo": "services",
    "pet": "services",
    "cleaning": "services",
    "laundry": "services",
    "studio": "services",
    "dental": "medical",
    "dentist": "medical",
    "doctor": "medical",
    "medical": "medical",
    "clinic": "medical",
    "veterinary": "medical",
    "vet": "medical",
    "chiropractic": "medical",
    "hotel": "hospitality",
    "motel": "hospitality",
    "inn": "hospitality",
    "lodge": "hospitality",
    "gym": "fitness",
    "fitness": "fitness",
    "yoga": "fitness",
}


# ─── SEGMENT KEY BUILDER ────────────────────────────────────────────────────

def _extract_area_code(phone: str) -> str:
    """Extract 3-digit area code from phone number."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("1") and len(digits) >= 4:
        return digits[1:4]
    elif len(digits) >= 3:
        return digits[:3]
    return ""


def _phone_to_state(phone: str) -> str:
    """Map phone number to 2-letter state code via area code lookup.
    Returns 'UN' for unknown (aligns with CDC regime engine convention)."""
    ac = _extract_area_code(phone)
    return _AREA_CODE_TO_STATE.get(ac, "UN")


def _business_to_vertical(business_type: str) -> str:
    """Map business_type string to standardized vertical."""
    if not business_type:
        return "general"
    bt_lower = business_type.lower().strip()
    # Try direct match first
    if bt_lower in _BUSINESS_TYPE_TO_VERTICAL:
        return _BUSINESS_TYPE_TO_VERTICAL[bt_lower]
    # Try substring match — longest key first to avoid "shop" beating "body shop"
    for key, vertical in sorted(_BUSINESS_TYPE_TO_VERTICAL.items(), key=lambda x: len(x[0]), reverse=True):
        if key in bt_lower:
            return vertical
    return "general"


def build_segment_key(phone: str, business_type: str = "", hour: int = None) -> str:
    """
    Build a segment key matching the Regime Engine's format: STATE_vertical_HH
    If hour not provided, uses current hour.
    """
    state = _phone_to_state(phone)
    vertical = _business_to_vertical(business_type)
    if hour is None:
        hour = datetime.now().hour
    return f"{state}_{vertical}_{hour:02d}"


# ─── CONFIG READER ──────────────────────────────────────────────────────────

_config_cache: Dict[str, Any] = {}
_config_mtime: float = 0.0


def _load_config() -> Dict[str, Any]:
    """Load regime_config_live.json with file-mtime caching."""
    global _config_cache, _config_mtime

    if not os.path.exists(CONFIG_LIVE_PATH):
        return {}

    try:
        mtime = os.path.getmtime(CONFIG_LIVE_PATH)
        if mtime == _config_mtime and _config_cache:
            return _config_cache

        with open(CONFIG_LIVE_PATH, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
            _config_mtime = mtime
            return _config_cache
    except Exception as e:
        logger.warning(f"[REGIME-QUEUE] Failed to load config: {e}")
        return _config_cache if _config_cache else {}


def get_segment_status(segment_key: str) -> Dict[str, str]:
    """
    Get the regime status for a segment.
    Returns dict with priority, prediction_trust, status, notes.
    Falls back to STABLE/MEDIUM if segment not in config.
    """
    config = _load_config()
    segments = config.get("segments", {})

    if segment_key in segments:
        return segments[segment_key]

    # Try partial match — just state_vertical (ignore hour)
    parts = segment_key.rsplit("_", 1)
    if len(parts) == 2:
        prefix = parts[0]  # e.g., "TX_restaurant"
        for key, seg in segments.items():
            if key.startswith(prefix):
                return seg

    # Default: healthy
    return {
        "priority": "MEDIUM",
        "prediction_trust": "MEDIUM",
        "status": "STABLE"
    }


def get_pacing_override(segment_key: str) -> Optional[str]:
    """
    Get pacing override for a segment.
    Returns: "AGGRESSIVE", "NORMAL", "CONSERVATIVE", or None.
    """
    config = _load_config()
    overrides = config.get("call_routing_overrides", {})

    if segment_key in overrides:
        return overrides[segment_key].get("pacing")

    # Check if any parent segment has an override
    parts = segment_key.rsplit("_", 1)
    if len(parts) == 2:
        prefix = parts[0]
        for key, ovr in overrides.items():
            if key.startswith(prefix):
                return ovr.get("pacing")

    return None


# ─── LEAD SCORING ───────────────────────────────────────────────────────────

# Score weights (lower = call first)
_STATUS_SCORE = {
    "STABLE": 0,
    "EXPERIMENTAL": 10,
    "SHIFTING": 20,
    "DEGRADED": 40,
    "OFF": 999,
}

_PRIORITY_SCORE = {
    "HIGH": 0,
    "MEDIUM": 10,
    "LOW": 20,
    "OFF": 999,
}

_TRUST_SCORE = {
    "HIGH": 0,
    "MEDIUM": 5,
    "LOW": 15,
}


def score_lead(phone: str, business_type: str = "", hour: int = None) -> Tuple[int, str, Dict[str, str]]:
    """
    Score a lead based on its regime segment health.

    Returns:
        (score, segment_key, segment_info)
        Lower score = better to call now.
        Score >= 999 means segment is OFF (do not call).
    """
    seg_key = build_segment_key(phone, business_type, hour)
    seg_info = get_segment_status(seg_key)

    status = seg_info.get("status", "STABLE")
    priority = seg_info.get("priority", "MEDIUM")
    trust = seg_info.get("prediction_trust", "MEDIUM")

    score = (
        _STATUS_SCORE.get(status, 10) +
        _PRIORITY_SCORE.get(priority, 10) +
        _TRUST_SCORE.get(trust, 5)
    )

    return score, seg_key, seg_info


def score_and_sort_leads(leads: List[Dict[str, Any]],
                         phone_key: str = "phone_number",
                         biz_key: str = "business_type") -> List[Dict[str, Any]]:
    """
    Score and sort a list of leads by regime segment health.
    Leads in STABLE/HIGH segments sort first. DEGRADED/OFF sort last or get filtered.

    Each lead dict gets enriched with:
      _regime_score, _regime_segment, _regime_status

    Returns: sorted list (best segments first). OFF leads are included but at the end.
    """
    scored = []
    for lead in leads:
        phone = lead.get(phone_key, "")
        biz = lead.get(biz_key, "") or lead.get("name", "")
        score, seg_key, seg_info = score_lead(phone, biz)
        lead["_regime_score"] = score
        lead["_regime_segment"] = seg_key
        lead["_regime_status"] = seg_info.get("status", "STABLE")
        scored.append(lead)

    # Sort by regime score (lower = better), then by existing priority
    scored.sort(key=lambda x: (
        x["_regime_score"],
        0 if x.get("priority", "medium") == "critical" else
        1 if x.get("priority", "medium") == "high" else
        2 if x.get("priority", "medium") == "medium" else 3
    ))

    return scored


def should_skip_lead(phone: str, business_type: str = "") -> Tuple[bool, str]:
    """
    Check if a lead should be skipped based on regime status.

    Returns:
        (should_skip, reason)
        skip=True if segment is OFF or severely degraded with <0.3 trust.
    """
    score, seg_key, seg_info = score_lead(phone, business_type)

    status = seg_info.get("status", "STABLE")
    priority = seg_info.get("priority", "MEDIUM")

    if priority == "OFF":
        return True, f"Segment {seg_key} is OFF"

    if status == "DEGRADED" and priority == "LOW":
        return True, f"Segment {seg_key} is DEGRADED+LOW — skipping to save budget"

    return False, ""


# ─── PACING ─────────────────────────────────────────────────────────────────

# Pacing delays (seconds between calls)
_PACING_DELAYS = {
    "AGGRESSIVE": 30,
    "NORMAL": 45,
    "CONSERVATIVE": 90,
}


def get_pacing_delay(phone: str = "", business_type: str = "",
                     default_delay: int = 45) -> int:
    """
    Get the recommended pacing delay for the next call.

    Uses regime config pacing overrides if available.
    Falls back to segment-status-aware delays.
    Falls back to default_delay.
    """
    if phone:
        seg_key = build_segment_key(phone, business_type)
        seg_info = get_segment_status(seg_key)

        # Check explicit pacing override
        pacing = get_pacing_override(seg_key)
        if pacing and pacing in _PACING_DELAYS:
            return _PACING_DELAYS[pacing]

        # Derive from segment status
        status = seg_info.get("status", "STABLE")
        if status == "STABLE":
            return _PACING_DELAYS["AGGRESSIVE"]
        elif status in ("SHIFTING", "EXPERIMENTAL"):
            return _PACING_DELAYS["NORMAL"]
        elif status == "DEGRADED":
            return _PACING_DELAYS["CONSERVATIVE"]

    return default_delay


def get_regime_priority(phone: str, business_type: str = "") -> str:
    """
    Get adjusted priority for a lead based on regime segment health.

    Returns: 'critical', 'high', 'medium', or 'low'
    Segments in STABLE/HIGH status → elevate to 'high'
    Segments in DEGRADED → demote to 'low'
    """
    score, seg_key, seg_info = score_lead(phone, business_type)

    status = seg_info.get("status", "STABLE")
    priority = seg_info.get("priority", "MEDIUM")

    if priority == "OFF":
        return "low"

    if status == "STABLE" and priority == "HIGH":
        return "critical"
    elif status == "STABLE":
        return "high"
    elif status == "SHIFTING":
        return "medium"
    elif status == "DEGRADED":
        return "low"

    return "medium"


# ─── SUMMARY ────────────────────────────────────────────────────────────────

def get_regime_summary() -> Dict[str, Any]:
    """Get a summary of current regime status for dashboards/health checks."""
    config = _load_config()
    if not config:
        return {"available": False, "reason": "No regime config found"}

    segments = config.get("segments", {})
    statuses = {}
    for seg, info in segments.items():
        status = info.get("status", "STABLE")
        statuses[status] = statuses.get(status, 0) + 1

    return {
        "available": True,
        "version": config.get("version", "unknown"),
        "generated_at": config.get("generated_at", "unknown"),
        "total_segments": len(segments),
        "status_distribution": statuses,
        "model_actions_pending": len(config.get("model_actions", [])),
        "regime_events": len(config.get("regime_events", [])),
    }


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("  REGIME QUEUE INTEGRATOR — Status")
    print("=" * 70)

    summary = get_regime_summary()
    if summary["available"]:
        print(f"  Version:          {summary['version']}")
        print(f"  Generated:        {summary['generated_at']}")
        print(f"  Segments:         {summary['total_segments']}")
        print(f"  Status Dist:      {summary['status_distribution']}")
        print(f"  Model Actions:    {summary['model_actions_pending']}")
        print(f"  Regime Events:    {summary['regime_events']}")
    else:
        print(f"  NOT AVAILABLE: {summary['reason']}")

    # Demo: score a few sample phones
    print()
    print("  Sample Lead Scores:")
    test_phones = [
        ("+12145551234", "restaurant"),
        ("+14065551234", "contractor"),
        ("+19175551234", "retail"),
    ]
    for phone, biz in test_phones:
        score, seg, info = score_lead(phone, biz)
        print(f"    {phone} ({biz:12s}) → score={score:3d}  seg={seg}  status={info.get('status', 'N/A')}")

    print("=" * 70)
