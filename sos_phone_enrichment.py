#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
  SOS PHONE ENRICHMENT ENGINE — Triangulated Phone Number Discovery
  "Three points make a fact"

  TRIANGULATION PRINCIPLE:
    Source A: SOS data      → business name + owner name + city/state
    Source B: Web search    → phone number candidate
    Source C: Twilio Lookup → caller_name must match biz OR owner name

    Only when Source C CONFIRMS do we accept the phone.
    Without confirmation, the phone is REJECTED — no guessing.

  STRATEGIES (Source B):
    1. OpenAI web_search  → searches for business website + phone
    2. Google Maps search → searches Maps listings via OpenAI
    3. Website scraping    → if a website URL is found, scrape it for phones
    4. Bing search         → fallback HTML search

  VALIDATION (Source C):
    - Twilio Lookup v2 with caller_name + line_type_intelligence
    - Caller name must fuzzy-match business name OR owner name
    - Area code must match geographic region
    - Phone must be valid US number

  Pipeline:
    DISCOVER → VALIDATE → CONFIRM → ACCEPT/REJECT
═══════════════════════════════════════════════════════════════════════
"""

import os
import re
import json
import time
import sqlite3
import requests
import hashlib
import argparse
from datetime import datetime
from openai import OpenAI
from twilio.rest import Client as TwilioClient

# Web Intelligence — technographic + intent signal detection
try:
    from web_intel import analyze_website, analyze_business_presence, compute_web_intelligence_score
    WEB_INTEL_AVAILABLE = True
except ImportError:
    WEB_INTEL_AVAILABLE = False

# ── Paths ────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADS_DB  = os.path.join(BASE_DIR, "data", "leads.db")
SOS_CACHE = os.path.join(BASE_DIR, "data", "sos_cache.db")
ENRICH_LOG = os.path.join(BASE_DIR, "data", "enrichment_log.json")

# ── Clients ──────────────────────────────────────────────────────
openai_client = OpenAI()
twilio_client = TwilioClient(
    os.environ.get("TWILIO_ACCOUNT_SID"),
    os.environ.get("TWILIO_AUTH_TOKEN"),
)

# ── Colorado Area Code Map ───────────────────────────────────────
AREA_CODES_BY_CITY = {
    # Denver metro (303/720)
    "Denver": ["303", "720"], "Aurora": ["303", "720"], "Lakewood": ["303", "720"],
    "Arvada": ["303", "720"], "Westminster": ["303", "720"], "Thornton": ["303", "720"],
    "Centennial": ["303", "720"], "Littleton": ["303", "720"], "Broomfield": ["303", "720"],
    "Boulder": ["303", "720"], "Longmont": ["303", "720"], "Golden": ["303", "720"],
    "Brighton": ["303", "720"], "Lafayette": ["303", "720"], "Lone Tree": ["303", "720"],
    "Firestone": ["303", "720"], "Frederick": ["303", "720"], "Erie": ["303", "720"],
    "Castle Rock": ["303", "720"], "Parker": ["303", "720"], "Highlands Ranch": ["303", "720"],
    "Commerce City": ["303", "720"], "Northglenn": ["303", "720"], "Wheat Ridge": ["303", "720"],
    "Englewood": ["303", "720"], "Greenwood Village": ["303", "720"], "Superior": ["303", "720"],
    "Louisville": ["303", "720"], "Dacono": ["303", "720"], "Federal Heights": ["303", "720"],
    # Colorado Springs area (719)
    "Colorado Springs": ["719"], "Pueblo": ["719"], "Canon City": ["719"],
    "Fountain": ["719"], "Woodland Park": ["719"], "Monument": ["719"],
    "Security-Widefield": ["719"], "Cripple Creek": ["719"], "Manitou Springs": ["719"],
    "Florence": ["719"], "Penrose": ["719"],
    # Fort Collins / mountain (970)
    "Fort Collins": ["970"], "Greeley": ["970"], "Loveland": ["970"],
    "Grand Junction": ["970"], "Steamboat Springs": ["970"], "Durango": ["970"],
    "Glenwood Springs": ["970"], "Rifle": ["970"], "Kremmling": ["970"],
    "Severance": ["970"], "Windsor": ["970"], "Johnstown": ["970"],
    "Berthoud": ["970"], "Evans": ["970"], "Montrose": ["970"],
    "Delta": ["970"], "Craig": ["970"], "Meeker": ["970"],
    "Silverthorne": ["970"], "Frisco": ["970"], "Breckenridge": ["970"],
    "Vail": ["970"], "Aspen": ["970"], "Basalt": ["970"],
}
CO_ALL_AREA_CODES = ["303", "719", "720", "970"]


# ═══════════════════════════════════════════════════════════════════
#  SOURCE B: PHONE DISCOVERY STRATEGIES
# ═══════════════════════════════════════════════════════════════════

def discover_openai_web(biz_name, city, state):
    """Strategy B1: OpenAI Responses API with web_search to find business phone + website."""
    prompt = (
        f"Find the official website and phone number for the business called "
        f"'{biz_name}' located in {city}, {state}. "
        f"If you find a website, provide the URL and any phone number listed on it. "
        f"Format: WEBSITE: [url] PHONE: [number] or NOT FOUND if neither exists."
    )
    try:
        resp = openai_client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
            max_output_tokens=300,
        )
        result = ""
        for item in resp.output:
            if hasattr(item, "content"):
                for c in item.content:
                    if hasattr(c, "text"):
                        result += c.text

        phone = extract_phone(result)
        website = extract_url(result)
        return {"phone": phone, "website": website, "raw": result[:300], "source": "openai_web"}
    except Exception as e:
        return {"phone": None, "website": None, "raw": str(e)[:200], "source": "openai_web"}


def discover_google_maps(biz_name, city, state):
    """Strategy B2: Search Google Maps listings via OpenAI."""
    prompt = (
        f"Search for '{biz_name}' in {city}, {state} on Google Maps. "
        f"What is the phone number listed? "
        f"Return ONLY the phone number or NOT FOUND."
    )
    try:
        resp = openai_client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
            max_output_tokens=200,
        )
        result = ""
        for item in resp.output:
            if hasattr(item, "content"):
                for c in item.content:
                    if hasattr(c, "text"):
                        result += c.text

        phone = extract_phone(result)
        return {"phone": phone, "raw": result[:200], "source": "gmaps"}
    except Exception as e:
        return {"phone": None, "raw": str(e)[:200], "source": "gmaps"}


def discover_website_scrape(url):
    """Strategy B3: Scrape a website URL for phone numbers."""
    if not url or "google.com/maps" in url:
        return {"phone": None, "source": "scrape"}
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return {"phone": None, "source": "scrape"}

        phones = set()
        for pattern in [
            r"\((\d{3})\)\s*(\d{3})-(\d{4})",
            r"(\d{3})-(\d{3})-(\d{4})",
            r"(\d{3})\.(\d{3})\.(\d{4})",
            r'tel:\+?1?(\d{3})(\d{3})(\d{4})',
        ]:
            for m in re.findall(pattern, resp.text):
                area, prefix, line = m
                if area[0] not in ("0", "1") and prefix[0] not in ("0", "1"):
                    phones.add(f"+1{area}{prefix}{line}")

        phone = list(phones)[0] if phones else None
        return {"phone": phone, "all_phones": list(phones)[:5], "source": "scrape"}
    except Exception:
        return {"phone": None, "source": "scrape"}


def discover_bing(biz_name, city, state):
    """Strategy B4: Bing HTML search for phone number."""
    query = f'"{biz_name}" {city} {state} phone number'
    url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {"phone": None, "source": "bing"}

        phones = set()
        for pattern in [r"\((\d{3})\)\s*(\d{3})-(\d{4})", r"(\d{3})-(\d{3})-(\d{4})"]:
            for m in re.findall(pattern, resp.text):
                area, prefix, line = m
                if area[0] not in ("0", "1") and prefix[0] not in ("0", "1"):
                    phones.add(f"+1{area}{prefix}{line}")

        phone = list(phones)[0] if phones else None
        return {"phone": phone, "all_phones": list(phones)[:5], "source": "bing"}
    except Exception:
        return {"phone": None, "source": "bing"}


# ═══════════════════════════════════════════════════════════════════
#  SOURCE C: TWILIO VALIDATION + FUZZY NAME MATCHING
# ═══════════════════════════════════════════════════════════════════

def validate_via_twilio(phone):
    """
    Call Twilio Lookup v2 for caller_name and line_type.
    Returns dict with caller info or None on error.
    Cost: $0.01 per lookup (caller_name) + $0.005 (line_type)
    """
    if not phone:
        return None
    try:
        lookup = twilio_client.lookups.v2.phone_numbers(phone).fetch(
            fields="caller_name,line_type_intelligence"
        )
        caller_name = ""
        caller_type = ""
        line_type = ""
        carrier = ""

        if lookup.caller_name:
            caller_name = lookup.caller_name.get("caller_name", "") or ""
            caller_type = lookup.caller_name.get("caller_type", "") or ""
        if lookup.line_type_intelligence:
            line_type = lookup.line_type_intelligence.get("type", "") or ""
            carrier = lookup.line_type_intelligence.get("carrier_name", "") or ""

        return {
            "valid": lookup.valid,
            "caller_name": caller_name,
            "caller_type": caller_type,
            "line_type": line_type,
            "carrier": carrier,
            "national_format": lookup.national_format,
        }
    except Exception as e:
        return {"valid": False, "caller_name": "", "error": str(e)}


def fuzzy_name_match(caller_name, biz_name, owner_name=""):
    """
    Check if Twilio's caller_name matches:
    (a) the business name, OR
    (b) the owner's last name (personal cell)

    Returns (matched: bool, match_type: str, detail: str)
    """
    if not caller_name:
        return False, "none", "no_caller_name"

    cn = caller_name.upper().strip()

    # Clean suffixes
    for suf in ["LLC", "INC", "CORP", "CO", "L.L.C.", "LTD", ",", "."]:
        cn = cn.replace(suf, "").strip()

    # ── Check against business name ──
    bn = biz_name.upper().strip()
    for suf in ["LLC", "INC", "CORP", "CO", "L.L.C.", "LTD", ",", "."]:
        bn = bn.replace(suf, "").strip()

    # Direct containment
    if cn and bn and (cn in bn or bn in cn):
        return True, "biz_direct", f"'{cn}' ↔ '{bn}'"

    # Significant word overlap (words > 2 chars)
    cn_words = set(w for w in cn.split() if len(w) > 2)
    bn_words = set(w for w in bn.split() if len(w) > 2)
    overlap = cn_words & bn_words
    if len(overlap) >= 1:
        return True, "biz_word_overlap", f"shared: {overlap}"

    # First significant word match (4+ char prefix)
    cn_sig = [w for w in cn.split() if len(w) >= 4]
    bn_sig = [w for w in bn.split() if len(w) >= 4]
    if cn_sig and bn_sig:
        for cw in cn_sig:
            for bw in bn_sig:
                # Check if first 4 characters match (handles truncation like MY SELLER → MY CELLAR)
                if cw[:4] == bw[:4]:
                    return True, "biz_prefix_match", f"'{cw}' ~ '{bw}'"

    # ── Check against owner name ──
    if owner_name:
        on = owner_name.upper().strip()
        on_parts = set(w for w in on.split() if len(w) > 2)
        # Caller name contains owner's last name (most common for personal cells)
        # Last name is usually the last part of owner_name
        owner_parts = owner_name.strip().split()
        if owner_parts:
            last_name = owner_parts[-1].upper()
            if len(last_name) >= 3 and last_name in cn:
                return True, "owner_lastname", f"'{last_name}' found in '{cn}'"

        # Owner's last name formatted as "LASTNAME,FIRST" in caller name
        for part in cn.replace(",", " ").split():
            if len(part) >= 3 and part in on.upper():
                return True, "owner_name_part", f"'{part}' found in owner '{on}'"

    return False, "no_match", f"'{cn}' vs biz='{bn}' / owner='{owner_name}'"


def check_area_code(phone, city):
    """Verify phone area code matches city's expected area codes."""
    if not phone:
        return False
    digits = re.sub(r"[^\d]", "", phone)
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10:
        return False
    area = digits[:3]
    expected = AREA_CODES_BY_CITY.get(city, CO_ALL_AREA_CODES)
    return area in expected


# ═══════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def extract_phone(text):
    """Extract first valid US phone number from text."""
    if not text:
        return None
    match = re.search(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}", text)
    if not match:
        return None
    digits = re.sub(r"[^\d]", "", match.group())
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits[0] == "1":
        return f"+{digits}"
    return None


def extract_url(text):
    """Extract first URL from text, excluding Google Maps redirect links."""
    if not text:
        return None
    match = re.search(r"https?://[^\s\)\]>]+", text)
    if not match:
        return None
    url = match.group().rstrip(".,;)")
    # Skip Google Maps search URLs — they're not the actual website
    if "google.com/maps/search" in url:
        return None
    return url


# ═══════════════════════════════════════════════════════════════════
#  MAIN ENRICHMENT FUNCTION
# ═══════════════════════════════════════════════════════════════════

def enrich_lead(biz_name, owner_name, city, state, address="", verbose=True):
    """
    Full triangulation enrichment for a single lead.

    Source A: biz_name + owner_name + city + state (from SOS)
    Source B: Multi-strategy web phone discovery
    Source C: Twilio caller_name confirmation

    Returns:
    {
        "phone": str or None,
        "confidence": "CONFIRMED" | "HIGH" | "MEDIUM" | "REJECTED" | "NOT_FOUND",
        "caller_name": str,
        "match_type": str,
        "line_type": str,
        "sources": list,
        "confirmations": list,
    }
    """
    log = lambda msg: print(msg) if verbose else None

    log(f"\n  ── {biz_name} ({owner_name or 'no owner'}, {city}, {state}) ──")

    candidates = {}  # phone -> [source_names]

    # ── Source B1: OpenAI web search ──
    log(f"    [B1] OpenAI web search...")
    r1 = discover_openai_web(biz_name, city, state)
    if r1["phone"]:
        candidates.setdefault(r1["phone"], []).append("openai_web")
        log(f"         → {r1['phone']}")
        # B3: If website found, scrape it
        if r1.get("website"):
            log(f"    [B3] Scraping: {r1['website'][:60]}...")
            r3 = discover_website_scrape(r1["website"])
            if r3["phone"]:
                candidates.setdefault(r3["phone"], []).append("website_scrape")
                log(f"         → {r3['phone']}")
    else:
        log(f"         → miss")

    # ── Source B2: Google Maps listing ──
    log(f"    [B2] Google Maps listing...")
    r2 = discover_google_maps(biz_name, city, state)
    if r2["phone"]:
        candidates.setdefault(r2["phone"], []).append("gmaps")
        log(f"         → {r2['phone']}")
    else:
        log(f"         → miss")

    # ── Source B4: Bing search ──
    log(f"    [B4] Bing search...")
    r4 = discover_bing(biz_name, city, state)
    if r4["phone"]:
        candidates.setdefault(r4["phone"], []).append("bing")
        log(f"         → {r4['phone']}")
    else:
        log(f"         → miss")

    if not candidates:
        log(f"    [RESULT] NOT_FOUND — no phone candidates from any source")
        return {
            "phone": None, "confidence": "NOT_FOUND",
            "caller_name": "", "match_type": "",
            "line_type": "", "sources": [], "confirmations": [],
        }

    # ── Source C: Twilio Validation (THE confirmation) ──
    log(f"    [C] Twilio Lookup validation...")

    best_result = None
    best_rank = -1

    for phone, sources in sorted(candidates.items(), key=lambda x: -len(x[1])):
        log(f"        Validating {phone} (from {sources})...")

        # C1: Twilio Lookup
        twilio_data = validate_via_twilio(phone)
        if not twilio_data or not twilio_data.get("valid", False):
            log(f"          → INVALID phone number")
            continue

        caller_name = twilio_data.get("caller_name", "")
        line_type = twilio_data.get("line_type", "")
        carrier = twilio_data.get("carrier", "")

        log(f"          CallerName: {caller_name}")
        log(f"          LineType: {line_type} | Carrier: {carrier}")

        # C2: Fuzzy name match against business OR owner
        matched, match_type, detail = fuzzy_name_match(caller_name, biz_name, owner_name)

        # C3: Area code check
        ac_ok = check_area_code(phone, city)

        # ── Calculate confidence ──
        confirmations = []
        source_count = len([s for s in sources if s != "bing_secondary"])

        if matched:
            confirmations.append(f"name_match:{match_type}")
        if ac_ok:
            confirmations.append("area_code_match")
        if source_count >= 2:
            confirmations.append(f"multi_source({source_count})")
        if line_type in ("fixedVoip", "landline"):
            confirmations.append("business_line")
        if twilio_data.get("caller_type") == "BUSINESS":
            confirmations.append("business_caller")

        # Confidence hierarchy:
        # CONFIRMED = name match + at least 1 other confirmation
        # HIGH      = name match only
        # MEDIUM    = no name match but multi-source + area code (risky)
        # REJECTED  = no name match (Source C says NO)

        if matched and len(confirmations) >= 2:
            confidence = "CONFIRMED"
            rank = 5
        elif matched:
            confidence = "HIGH"
            rank = 4
        elif source_count >= 2 and ac_ok and caller_name == "":
            # Edge case: no caller_name data available but strong Source B
            confidence = "MEDIUM"
            rank = 2
        else:
            confidence = "REJECTED"
            rank = 0
            log(f"          → REJECTED: caller_name '{caller_name}' doesn't match '{biz_name}' or '{owner_name}'")

        if rank > best_rank:
            best_rank = rank
            best_result = {
                "phone": phone,
                "confidence": confidence,
                "caller_name": caller_name,
                "match_type": match_type,
                "match_detail": detail,
                "line_type": line_type,
                "carrier": carrier,
                "sources": sources,
                "confirmations": confirmations,
            }

    if not best_result or best_result["confidence"] == "REJECTED":
        rejection = best_result or {}
        log(f"    [RESULT] REJECTED — Source C (Twilio) did not confirm any candidate")
        if rejection.get("caller_name"):
            log(f"             Caller name '{rejection['caller_name']}' ≠ biz '{biz_name}' / owner '{owner_name}'")
        return {
            "phone": None, "confidence": "REJECTED",
            "caller_name": rejection.get("caller_name", ""),
            "match_type": "rejected",
            "line_type": rejection.get("line_type", ""),
            "sources": list(candidates.keys()),
            "confirmations": [],
            "rejected_phones": list(candidates.keys()),
        }

    log(f"    [RESULT] {best_result['confidence']}: {best_result['phone']}")
    log(f"             CallerName: {best_result['caller_name']} → {best_result['match_type']}")
    log(f"             Confirmations: {best_result['confirmations']}")

    # ── Web Intelligence: Analyze website found during discovery ──
    if WEB_INTEL_AVAILABLE:
        website_url = None
        # Check if we found a website during phone discovery
        if r1 and r1.get("website"):
            website_url = r1["website"]

        log(f"    [WebIntel] Analyzing technographic + intent signals...")
        try:
            # Website technographic analysis
            website_intel = analyze_website(website_url, verbose=verbose)

            # Business presence analysis (reviews, status, hiring, POS)
            presence_intel = analyze_business_presence(biz_name, city, state, verbose=verbose)

            # Composite web intelligence score
            web_score = compute_web_intelligence_score(
                website_intel=website_intel,
                presence_intel=presence_intel,
            )

            best_result["web_intel"] = {
                "web_score": web_score["web_score"],
                "tech_tier": website_intel.get("tech_tier", "unknown"),
                "payment_processors": [p["name"] for p in website_intel.get("payment_processors", [])],
                "intent_signals": [s["signal"] for s in website_intel.get("intent_signals", [])],
                "business_status": presence_intel.get("business_status", "unknown"),
                "payment_system": presence_intel.get("payment_system", "unknown"),
                "review_count": presence_intel.get("review_count", 0),
                "hiring": presence_intel.get("hiring", False),
                "size_estimate": presence_intel.get("size_estimate", "unknown"),
                "website": website_url,
                "factors": web_score.get("factors", []),
                "penalties": web_score.get("penalties", []),
            }

            log(f"    [WebIntel] Score: {web_score['web_score']}/100 | "
                f"Tech: {website_intel.get('tech_tier', '?')} | "
                f"POS: {presence_intel.get('payment_system', '?')} | "
                f"Status: {presence_intel.get('business_status', '?')}")

        except Exception as e:
            log(f"    [WebIntel] Error: {str(e)[:60]}")
            best_result["web_intel"] = None
    else:
        best_result["web_intel"] = None

    return best_result


# ═══════════════════════════════════════════════════════════════════
#  BATCH ENRICHMENT — Process SOS scraper output
# ═══════════════════════════════════════════════════════════════════

def enrich_sos_cache(max_leads=20, min_score=55, max_cost_usd=2.0, verbose=True):
    """
    Enrich SOS leads from the cache DB.
    Each Twilio lookup costs ~$0.015 per phone candidate validated.
    Each OpenAI web_search call costs ~$0.005-0.01.

    Budget: ~$0.05-0.08 per lead (2-3 OpenAI calls + 1-2 Twilio lookups)
    """
    if not os.path.exists(SOS_CACHE):
        print("[!] No SOS cache found. Run sos_lead_scraper.py first.")
        return

    conn = sqlite3.connect(SOS_CACHE)
    conn.row_factory = sqlite3.Row

    # Get leads that haven't been enriched yet
    rows = conn.execute("""
        SELECT entity_id, entity_name, state, formed_date, naics_cat, score, owner_name, raw_json
        FROM seen_entities
        WHERE imported = 0 AND score >= ?
        ORDER BY score DESC
        LIMIT ?
    """, (min_score, max_leads)).fetchall()

    if not rows:
        print("[!] No unenriched leads found in cache.")
        conn.close()
        return

    print(f"{'='*80}")
    print(f"  SOS PHONE ENRICHMENT — Triangulated Discovery")
    print(f"  Leads to process: {len(rows)} | Min score: {min_score}")
    print(f"  Budget: ~${max_cost_usd:.2f} max | ~$0.06/lead")
    print(f"{'='*80}")

    results = []
    cost_estimate = 0.0
    confirmed_count = 0
    high_count = 0
    medium_count = 0
    rejected_count = 0
    not_found_count = 0

    for i, row in enumerate(rows):
        if cost_estimate >= max_cost_usd:
            print(f"\n  [!] Budget limit reached (~${cost_estimate:.2f})")
            break

        raw = json.loads(row["raw_json"]) if row["raw_json"] else {}
        biz_name = row["entity_name"] or ""
        owner_name = row["owner_name"] or ""
        city = raw.get("principalcity", "")
        state = row["state"] or "CO"
        entity_id = row["entity_id"]
        score = row["score"] or 0

        # Clean business name for search
        biz_clean = re.sub(r'\s*(LLC|Inc|Corp|L\.?L\.?C\.?|Co\.?|Company)\s*\.?\s*$',
                           '', biz_name, flags=re.IGNORECASE).strip()

        print(f"\n  [{i+1}/{len(rows)}] {biz_clean} (score={score}, owner={owner_name or '?'})")

        result = enrich_lead(biz_clean, owner_name, city, state, verbose=verbose)
        result["entity_id"] = entity_id
        result["biz_name"] = biz_name
        result["score"] = score
        results.append(result)

        # Track costs (~3 OpenAI calls + 1-2 Twilio lookups per lead)
        cost_estimate += 0.06

        if result["confidence"] == "CONFIRMED":
            confirmed_count += 1
        elif result["confidence"] == "HIGH":
            high_count += 1
        elif result["confidence"] == "MEDIUM":
            medium_count += 1
        elif result["confidence"] == "REJECTED":
            rejected_count += 1
        else:
            not_found_count += 1

        # Rate limit
        time.sleep(1)

    # ── Import confirmed leads to leads.db ──
    imported = 0
    leads_conn = sqlite3.connect(LEADS_DB)
    leads_conn.row_factory = sqlite3.Row

    for r in results:
        if r["confidence"] not in ("CONFIRMED", "HIGH", "MEDIUM"):
            continue
        if not r["phone"]:
            continue

        entity_id = r["entity_id"]
        phone = r["phone"]
        biz_name = r["biz_name"]

        # Get full entity data from cache
        cached = conn.execute(
            "SELECT raw_json, naics_cat, score, owner_name, formed_date FROM seen_entities WHERE entity_id = ?",
            (entity_id,)
        ).fetchone()
        if not cached:
            continue

        raw = json.loads(cached["raw_json"]) if cached["raw_json"] else {}
        score = cached["score"] or 0
        category = cached["naics_cat"] or "general"
        owner = cached["owner_name"] or ""
        formed = cached["formed_date"] or ""
        city = raw.get("principalcity", "")
        state_code = raw.get("principalstate", "CO")

        lead_id = hashlib.md5(f"SOS_CO_{entity_id}".encode()).hexdigest()[:16]

        # Check if another lead already has this phone number (avoid dupes)
        phone_dupe = leads_conn.execute(
            "SELECT id FROM leads WHERE phone_number = ? AND id != ?", (phone, lead_id)
        ).fetchone()
        if phone_dupe:
            continue

        # Check if lead already exists (from scraper import with no phone)
        existing = leads_conn.execute(
            "SELECT id, phone_number FROM leads WHERE id = ?", (lead_id,)
        ).fetchone()

        biz_type = f"New {category.replace('_', ' ').title()}"
        if city:
            biz_type += f" in {city.title()}, {state_code}"

        # Build notes with full enrichment + web intel data
        notes_dict = {
            "sos_entity_id": entity_id,
            "formed_date": formed,
            "naics_category": category,
            "owner_name": owner,
            "enrichment_confidence": r["confidence"],
            "enrichment_sources": r["sources"],
            "caller_name": r["caller_name"],
            "match_type": r["match_type"],
            "line_type": r["line_type"],
            "principal_city": city,
            "principal_state": state_code,
            "sos_score": score,
        }

        # Attach web intelligence if available (technographic + intent + displacement data)
        web_intel = r.get("web_intel")
        if web_intel:
            notes_dict["web_intel_score"] = web_intel.get("web_score", 0)
            notes_dict["tech_tier"] = web_intel.get("tech_tier", "unknown")
            notes_dict["current_processor"] = web_intel.get("payment_system", "unknown")
            notes_dict["payment_processors_detected"] = web_intel.get("payment_processors", [])
            notes_dict["intent_signals"] = web_intel.get("intent_signals", [])
            notes_dict["business_status"] = web_intel.get("business_status", "unknown")
            notes_dict["review_count"] = web_intel.get("review_count", 0)
            notes_dict["hiring"] = web_intel.get("hiring", False)
            notes_dict["size_estimate"] = web_intel.get("size_estimate", "unknown")
            notes_dict["website"] = web_intel.get("website")
            notes_dict["web_intel_factors"] = web_intel.get("factors", [])

            # Competitive displacement pitch angle
            proc = web_intel.get("payment_system", "unknown")
            tier = web_intel.get("tech_tier", "unknown")
            if proc in ("square", "stripe", "paypal"):
                notes_dict["pitch_angle"] = f"On {proc.title()} — offer free statement analysis, show rate savings"
                notes_dict["displacement_target"] = proc
            elif tier == "none":
                notes_dict["pitch_angle"] = "No processor detected — new business needs POS setup"
                notes_dict["displacement_target"] = "none"
            elif tier == "enterprise":
                notes_dict["pitch_angle"] = f"Enterprise POS ({proc}) — may be locked in, approach carefully"
                notes_dict["displacement_target"] = proc
            else:
                notes_dict["pitch_angle"] = "Free statement review — find hidden fees"
                notes_dict["displacement_target"] = "unknown"

        notes = json.dumps(notes_dict)

        # Priority calculation: enrichment confidence + SOS score + web intel
        web_score = 0
        if web_intel:
            web_score = web_intel.get("web_score", 0)

        if r["confidence"] == "CONFIRMED" and score >= 70:
            priority = "high"
        elif r["confidence"] == "CONFIRMED" and web_score >= 80:  # Web intel says hot opportunity
            priority = "high"
        elif web_intel and web_intel.get("business_status") in ("coming_soon", "newly_opened"):
            priority = "high"  # Coming soon / just opened = IMMEDIATE need
        else:
            priority = "medium"

        try:
            if existing and (not existing["phone_number"] or existing["phone_number"] == ''):
                # Lead exists from scraper but has no phone — UPDATE it
                leads_conn.execute("""
                    UPDATE leads SET phone_number = ?, line_type = ?,
                    notes = ?, priority = ?, business_type = ?
                    WHERE id = ?
                """, (phone, r.get("line_type", "unknown"), notes, priority,
                      biz_type, lead_id))
                imported += 1
            elif not existing:
                # Brand new lead — INSERT
                leads_conn.execute("""
                    INSERT OR IGNORE INTO leads
                    (id, phone_number, name, business_type, priority, outcome,
                     line_type, lead_source, notes, created_at, attempts, max_attempts, do_not_call)
                    VALUES (?, ?, ?, ?, ?, 'pending',
                            ?, 'SOS_CO_PLATINUM', ?, datetime('now'), 0, 3, 0)
                """, (lead_id, phone, biz_name, biz_type, priority,
                      r.get("line_type", "unknown"), notes))
                imported += 1

            # Mark as imported in SOS cache
            conn.execute("UPDATE seen_entities SET imported = 1 WHERE entity_id = ?", (entity_id,))
        except Exception as e:
            print(f"    [ERR] Import failed: {e}")

    leads_conn.commit()
    leads_conn.close()
    conn.commit()
    conn.close()

    # ── Save enrichment log ──
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "total_processed": len(results),
        "confirmed": confirmed_count,
        "high": high_count,
        "medium": medium_count,
        "rejected": rejected_count,
        "not_found": not_found_count,
        "imported": imported,
        "cost_estimate": round(cost_estimate, 2),
        "results": [
            {
                "biz": r["biz_name"],
                "phone": r.get("phone"),
                "confidence": r["confidence"],
                "caller_name": r.get("caller_name", ""),
                "match_type": r.get("match_type", ""),
            }
            for r in results
        ],
    }
    try:
        with open(ENRICH_LOG, "w") as f:
            json.dump(log_data, f, indent=2)
    except Exception:
        pass

    # ── Summary ──
    print(f"\n{'='*80}")
    print(f"  ENRICHMENT RESULTS")
    print(f"{'='*80}")

    for r in results:
        phone = r.get("phone") or "—"
        conf = r["confidence"]
        icon = {"CONFIRMED": "✅", "HIGH": "🟢", "MEDIUM": "🟡", "REJECTED": "❌", "NOT_FOUND": "—"}.get(conf, "?")
        print(f"  {icon} {r['biz_name'][:40]:40} | {phone:15} | {conf:10} | caller: {r.get('caller_name', '')[:25]}")

    print(f"\n  ✅ CONFIRMED: {confirmed_count}")
    print(f"  🟢 HIGH:      {high_count}")
    print(f"  🟡 MEDIUM:    {medium_count}")
    print(f"  ❌ REJECTED:  {rejected_count}")
    print(f"  —  NOT FOUND: {not_found_count}")
    print(f"\n  Imported to leads.db: {imported}")
    print(f"  Est. cost: ~${cost_estimate:.2f}")
    hit = confirmed_count + high_count + medium_count
    total = len(results)
    print(f"  Hit rate: {hit}/{total} ({round(hit/max(total,1)*100)}%)")
    print(f"{'='*80}\n")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SOS Phone Enrichment Engine — Triangulated Discovery")
    parser.add_argument("--max", type=int, default=20, help="Max leads to enrich (default: 20)")
    parser.add_argument("--min-score", type=int, default=70, help="Min SOS score (default: 70)")
    parser.add_argument("--budget", type=float, default=2.0, help="Max budget in USD (default: $2.00)")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-lead output")

    # Single lead test mode
    parser.add_argument("--test", action="store_true", help="Test single lead")
    parser.add_argument("--biz", type=str, help="Business name for --test")
    parser.add_argument("--owner", type=str, default="", help="Owner name for --test")
    parser.add_argument("--city", type=str, default="Denver", help="City for --test")
    parser.add_argument("--state", type=str, default="CO", help="State for --test")

    args = parser.parse_args()

    if args.test:
        if not args.biz:
            print("Usage: --test --biz 'Business Name' --owner 'Owner Name' --city Denver --state CO")
            return
        result = enrich_lead(args.biz, args.owner, args.city, args.state, verbose=True)
        print(f"\n  Result: {json.dumps(result, indent=2, default=str)}")
    else:
        enrich_sos_cache(
            max_leads=args.max,
            min_score=args.min_score,
            max_cost_usd=args.budget,
            verbose=not args.quiet,
        )


if __name__ == "__main__":
    main()
