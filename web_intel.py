#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
  WEB INTELLIGENCE MODULE — Technographic + Intent Signal Detection
  "Know what they use, know when they're buying"

  FROM THE EXPERT PLAYBOOK:
  ─────────────────────────────────────────────────────────────────
  #4 Technographic Data — "Knowing a company uses X but not Y = warm lead"
  #2 Intent Data       — "Track buying signals — who is actively looking"
  #6 Job Posting Analysis — "What they're hiring for reveals priorities"
  #10 Verification     — "Confirm contacts are real and active"
  ─────────────────────────────────────────────────────────────────

  FOR MERCHANT SERVICES:
    - No payment processor detected → HOT lead (needs processing NOW)
    - Uses Square/Stripe/PayPal → WARM lead (can be saved money)
    - Uses enterprise POS (Toast, Clover enterprise, Fiserv) → COLD
    - "Coming soon" / "Opening soon" → PRIME INTENT (still setting up!)
    - Hiring cashiers/servers → OPERATIONAL (needs processing)
    - No website at all → Day-one business (HIGHEST intent for SOS leads)

  IMPLEMENTATION:
    - Scrapes business websites found during phone enrichment
    - Detects payment/POS tech stack from HTML + JS references
    - Identifies intent signals from page content
    - Returns structured intelligence dict for lead scoring

  Usage:
    from web_intel import analyze_website, analyze_business_presence

    # Analyze a specific website
    intel = analyze_website("https://mybusiness.com")

    # Full business presence analysis (website + social + hiring)
    intel = analyze_business_presence("My Bakery", "Denver", "CO")
═══════════════════════════════════════════════════════════════════════
"""

import re
import json
import requests
import os
from openai import OpenAI
from datetime import datetime

# ── OpenAI client ────────────────────────────────────────────────
openai_client = OpenAI()


# ═══════════════════════════════════════════════════════════════════
#  TECHNOGRAPHIC DETECTION — Payment processors & POS systems
# ═══════════════════════════════════════════════════════════════════

# Payment processors detectable from website HTML/JS
PAYMENT_PROCESSORS = {
    # ── Budget/DIY processors (WARM leads — can be undercut) ──
    "square": {
        "patterns": [
            r"squareup\.com", r"square-.*\.js", r"sq-payment",
            r"squareonlinestore\.com", r"square\.site",
            r"powered.?by.?square", r"squarecdn\.com",
        ],
        "tier": "warm",
        "monthly_cost": "$0 + 2.6%+10¢",
        "pitch_angle": "Lower effective rate for high volume",
    },
    "stripe": {
        "patterns": [
            r"stripe\.com", r"js\.stripe\.com", r"stripe-button",
            r"stripe-js", r"checkout\.stripe",
        ],
        "tier": "warm",
        "monthly_cost": "2.9%+30¢ online",
        "pitch_angle": "Better in-person rates than online-only",
    },
    "paypal": {
        "patterns": [
            r"paypal\.com", r"paypalobjects\.com", r"paypal-button",
            r"paypal\.me", r"venmo\.com",
        ],
        "tier": "warm",
        "monthly_cost": "2.99%+49¢",
        "pitch_angle": "Highest rates in industry — easy savings",
    },

    # ── Mid-tier processors (LUKEWARM — may be under contract) ──
    "clover": {
        "patterns": [
            r"clover\.com", r"clover-.*\.js", r"clovergo",
        ],
        "tier": "lukewarm",
        "monthly_cost": "$14.95/mo + 2.3%+10¢",
        "pitch_angle": "Contract buyout opportunity",
    },
    "shopify_payments": {
        "patterns": [
            r"cdn\.shopify\.com", r"myshopify\.com", r"shopify-buy",
            r"shopify\.com/payments",
        ],
        "tier": "lukewarm",
        "monthly_cost": "$29-299/mo + 2.4-2.9%",
        "pitch_angle": "Integrated but can add terminal for in-person",
    },

    # ── Enterprise POS (COLD — locked in, long contracts) ──
    "toast": {
        "patterns": [
            r"toasttab\.com", r"toast-.*\.js", r"order\.toasttab",
        ],
        "tier": "cold",
        "monthly_cost": "$0-165/mo + 2.49-3.69%",
        "pitch_angle": "Very sticky — skip unless contract ending",
    },
    "lightspeed": {
        "patterns": [
            r"lightspeedhq\.com", r"lightspeedrestaurant",
        ],
        "tier": "cold",
        "monthly_cost": "$69-399/mo",
        "pitch_angle": "Enterprise commitment — not a target",
    },
    "fiserv": {
        "patterns": [
            r"fiserv\.com", r"firstdata\.com",
        ],
        "tier": "cold",
        "monthly_cost": "Contract-based",
        "pitch_angle": "Enterprise processor — skip",
    },

    # ── Online-only platforms ──
    "woocommerce": {
        "patterns": [
            r"woocommerce", r"wc-payment", r"wc-checkout",
        ],
        "tier": "warm",
        "monthly_cost": "Varies by gateway",
        "pitch_angle": "Can integrate our gateway for better rates",
    },
}

# Online ordering / booking platforms (indicates they handle transactions)
ORDERING_PLATFORMS = {
    "doordash": [r"doordash\.com", r"order\.doordash"],
    "ubereats": [r"ubereats\.com"],
    "grubhub": [r"grubhub\.com"],
    "opentable": [r"opentable\.com"],
    "yelp_ordering": [r"yelp\.com/biz.*order"],
    "square_online": [r"squareonlinestore\.com", r"square\.site"],
    "toast_online": [r"order\.toasttab\.com"],
    "chownow": [r"chownow\.com"],
    "slice": [r"slicelife\.com"],
    "booksy": [r"booksy\.com"],
    "vagaro": [r"vagaro\.com"],
    "schedulicity": [r"schedulicity\.com"],
    "mindbody": [r"mindbodyonline\.com", r"mindbody\.io"],
    "acuity": [r"acuityscheduling\.com"],
}

# Website builder platforms (indicates technical sophistication)
WEBSITE_BUILDERS = {
    "wordpress": [r"wp-content", r"wp-includes", r"wordpress\.org"],
    "wix": [r"wixsite\.com", r"wix\.com", r"static\.wixstatic\.com"],
    "squarespace": [r"squarespace\.com", r"sqsp\.com", r"static1\.squarespace"],
    "godaddy": [r"godaddysites\.com", r"secureserver\.net"],
    "weebly": [r"weebly\.com"],
    "google_sites": [r"sites\.google\.com"],
    "carrd": [r"carrd\.co"],
}


# ═══════════════════════════════════════════════════════════════════
#  INTENT SIGNAL DETECTION
# ═══════════════════════════════════════════════════════════════════

# Strong intent signals (detected from website content)
INTENT_SIGNALS = {
    # ── HIGHEST INTENT: Still setting up ──
    "coming_soon": {
        "patterns": [
            r"coming\s+soon", r"opening\s+soon", r"under\s+construction",
            r"grand\s+opening", r"launching\s+soon", r"stay\s+tuned",
            r"opening\s+\w+\s+\d{4}", r"we['']re\s+almost\s+(ready|there|open)",
            r"check\s+back\s+soon", r"pardon\s+our\s+dust",
        ],
        "weight": 25,  # MASSIVE boost — they're setting up RIGHT NOW
        "meaning": "Business is still setting up — needs everything including POS",
    },

    # ── HIGH INTENT: Growing / expanding ──
    "expansion": {
        "patterns": [
            r"new\s+location", r"now\s+open", r"just\s+opened",
            r"newly\s+opened", r"recently\s+opened",
            r"second\s+location", r"expanding", r"new\s+menu",
        ],
        "weight": 15,
        "meaning": "New/expanding — may need additional terminals or new processor",
    },

    # ── MEDIUM INTENT: Hiring (operational, growing) ──
    "hiring": {
        "patterns": [
            r"now\s+hiring", r"we['']re\s+hiring", r"join\s+our\s+team",
            r"help\s+wanted", r"careers", r"job\s+opening",
            r"apply\s+(now|today|within|here)", r"positions?\s+available",
        ],
        "weight": 10,
        "meaning": "Hiring staff — business is active and growing",
    },

    # ── POSITIVE: Cash acceptance signals ──
    "cash_focused": {
        "patterns": [
            r"cash\s+only", r"cash\s+preferred", r"no\s+cards",
            r"atm\s+available", r"atm\s+on[\s-]?site",
        ],
        "weight": 20,
        "meaning": "Cash-only business — PRIME candidate for card processing",
    },

    # ── NEUTRAL-POSITIVE: Online ordering without own processor ──
    "third_party_ordering": {
        "patterns": [
            r"order\s+(on|through|via)\s+(doordash|ubereats|grubhub)",
            r"find\s+us\s+on\s+(doordash|ubereats|grubhub|yelp)",
        ],
        "weight": 8,
        "meaning": "Uses third-party ordering — may not have own processor",
    },

    # ── NEGATIVE: Already established with processor ──
    "online_ordering_own": {
        "patterns": [
            r"order\s+online\s+(now|here|today)",
            r"online\s+ordering\s+available",
            r"buy\s+gift\s+cards\s+online",
        ],
        "weight": -5,
        "meaning": "Has own online ordering — likely already has processor",
    },
}

# Social media presence patterns
SOCIAL_PATTERNS = {
    "facebook": r"facebook\.com/[a-zA-Z0-9]",
    "instagram": r"instagram\.com/[a-zA-Z0-9]",
    "twitter": r"(twitter\.com|x\.com)/[a-zA-Z0-9]",
    "tiktok": r"tiktok\.com/@[a-zA-Z0-9]",
    "yelp": r"yelp\.com/biz/[a-zA-Z0-9]",
    "google_biz": r"(g\.page|maps\.google\.com|goo\.gl/maps)",
    "linkedin": r"linkedin\.com/(company|in)/[a-zA-Z0-9]",
}


# ═══════════════════════════════════════════════════════════════════
#  WEBSITE ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_website(url, verbose=True):
    """
    Analyze a business website for technographic + intent intelligence.

    Returns:
    {
        "url": str,
        "accessible": bool,
        "payment_processors": [{"name": str, "tier": str, "pitch_angle": str}],
        "ordering_platforms": [str],
        "website_builder": str,
        "intent_signals": [{"signal": str, "weight": int, "meaning": str}],
        "social_presence": [str],
        "has_payment_processing": bool,
        "tech_tier": "none" | "diy" | "mid" | "enterprise",
        "intent_score": int,         # -20 to +100
        "technographic_score": int,  # 0-100 (higher = more opportunity)
        "overall_opportunity": int,  # 0-100 combined
    }
    """
    result = {
        "url": url,
        "accessible": False,
        "payment_processors": [],
        "ordering_platforms": [],
        "website_builder": None,
        "intent_signals": [],
        "social_presence": [],
        "has_payment_processing": False,
        "tech_tier": "none",
        "intent_score": 0,
        "technographic_score": 0,
        "overall_opportunity": 0,
    }

    if not url:
        # No website = brand new business, highest opportunity
        result["tech_tier"] = "none"
        result["technographic_score"] = 95  # No processor detected = huge opportunity
        result["intent_score"] = 20         # No website = still setting up
        result["overall_opportunity"] = 90
        return result

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        resp = requests.get(url, headers=headers, timeout=12, allow_redirects=True)
        if resp.status_code != 200:
            result["accessible"] = False
            result["technographic_score"] = 80  # Can't verify = assume opportunity
            result["overall_opportunity"] = 70
            return result

        result["accessible"] = True
        html = resp.text.lower()

    except Exception as e:
        if verbose:
            print(f"    [WebIntel] Fetch error: {str(e)[:60]}")
        result["technographic_score"] = 75
        result["overall_opportunity"] = 65
        return result

    # ── Detect Payment Processors ──
    for proc_name, proc_data in PAYMENT_PROCESSORS.items():
        for pattern in proc_data["patterns"]:
            if re.search(pattern, html, re.IGNORECASE):
                result["payment_processors"].append({
                    "name": proc_name,
                    "tier": proc_data["tier"],
                    "pitch_angle": proc_data["pitch_angle"],
                })
                break

    # ── Detect Ordering Platforms ──
    for platform, patterns in ORDERING_PLATFORMS.items():
        for pattern in patterns:
            if re.search(pattern, html, re.IGNORECASE):
                result["ordering_platforms"].append(platform)
                break

    # ── Detect Website Builder ──
    for builder, patterns in WEBSITE_BUILDERS.items():
        for pattern in patterns:
            if re.search(pattern, html, re.IGNORECASE):
                result["website_builder"] = builder
                break
        if result["website_builder"]:
            break

    # ── Detect Intent Signals ──
    total_intent = 0
    for signal_name, signal_data in INTENT_SIGNALS.items():
        for pattern in signal_data["patterns"]:
            if re.search(pattern, html, re.IGNORECASE):
                result["intent_signals"].append({
                    "signal": signal_name,
                    "weight": signal_data["weight"],
                    "meaning": signal_data["meaning"],
                })
                total_intent += signal_data["weight"]
                break

    result["intent_score"] = max(-20, min(100, total_intent))

    # ── Detect Social Presence ──
    for social, pattern in SOCIAL_PATTERNS.items():
        if re.search(pattern, html, re.IGNORECASE):
            result["social_presence"].append(social)

    # ── Calculate Technographic Score ──
    processors = result["payment_processors"]
    if not processors:
        # NO payment processor detected — huge opportunity
        result["has_payment_processing"] = False
        result["tech_tier"] = "none"
        result["technographic_score"] = 95
    else:
        result["has_payment_processing"] = True
        # Use the highest-tier (worst for us) processor found
        tiers = [p["tier"] for p in processors]
        if "cold" in tiers:
            result["tech_tier"] = "enterprise"
            result["technographic_score"] = 15  # Locked in — low opportunity
        elif "lukewarm" in tiers:
            result["tech_tier"] = "mid"
            result["technographic_score"] = 45  # Some opportunity
        else:
            result["tech_tier"] = "diy"
            result["technographic_score"] = 75  # Using budget processor — easy win

    # ── Calculate Overall Opportunity ──
    #  Technographic (60%) + Intent (40%)
    intent_normalized = max(0, min(100, 50 + total_intent))  # Normalize to 0-100 range
    result["overall_opportunity"] = round(
        result["technographic_score"] * 0.60 +
        intent_normalized * 0.40
    )

    if verbose:
        _print_intel(result)

    return result


def _print_intel(intel):
    """Pretty-print web intelligence results."""
    print(f"    [WebIntel] URL: {intel['url']}")
    if intel["payment_processors"]:
        procs = ", ".join(f"{p['name']}({p['tier']})" for p in intel["payment_processors"])
        print(f"    [WebIntel] Payment Processors: {procs}")
    else:
        print(f"    [WebIntel] Payment Processors: NONE DETECTED ← opportunity!")
    if intel["ordering_platforms"]:
        print(f"    [WebIntel] Ordering: {', '.join(intel['ordering_platforms'])}")
    if intel["website_builder"]:
        print(f"    [WebIntel] Built with: {intel['website_builder']}")
    if intel["intent_signals"]:
        sigs = ", ".join(f"{s['signal']}(+{s['weight']})" for s in intel["intent_signals"])
        print(f"    [WebIntel] Intent Signals: {sigs}")
    if intel["social_presence"]:
        print(f"    [WebIntel] Social: {', '.join(intel['social_presence'])}")
    print(f"    [WebIntel] Tech Tier: {intel['tech_tier']} | "
          f"Techno Score: {intel['technographic_score']} | "
          f"Intent: {intel['intent_score']} | "
          f"Opportunity: {intel['overall_opportunity']}")


# ═══════════════════════════════════════════════════════════════════
#  FULL BUSINESS PRESENCE ANALYSIS (via OpenAI web search)
# ═══════════════════════════════════════════════════════════════════

def analyze_business_presence(biz_name, city, state, verbose=True):
    """
    Full business intelligence profile via OpenAI web search.
    Answers the three key questions:
      1. FIRMOGRAPHIC: What kind of business is this? How big?
      2. TECHNOGRAPHIC: What payment/POS tech do they use?
      3. INTENT: Are they new, growing, or established?

    Returns structured intelligence dict.
    """
    prompt = f"""Analyze the business "{biz_name}" in {city}, {state} for a merchant services sales team.

Answer these questions about this specific business (not generic info):

1. WEBSITE: What is their official website URL? (exact URL or "none found")
2. PAYMENT PROCESSING: Do they appear to accept credit/debit cards? What POS or payment system do they use? (Square, Stripe, Clover, Toast, PayPal, etc. or "unknown")
3. ONLINE PRESENCE: Do they have Yelp, Google Business, Facebook, Instagram pages? How many reviews?
4. BUSINESS STATUS: Are they open/operating, coming soon, under construction, or recently opened?
5. SIZE ESTIMATE: Solo operation, small team (2-5), medium (6-20), or larger?
6. HIRING: Are they currently posting any jobs?

Be specific and factual. If you can't find info, say "not found" for that field. Format each answer clearly with the number prefix."""

    try:
        resp = openai_client.responses.create(
            model="gpt-4o-mini",
            tools=[{"type": "web_search_preview"}],
            input=prompt,
            max_output_tokens=500,
        )
        result_text = ""
        for item in resp.output:
            if hasattr(item, "content"):
                for c in item.content:
                    if hasattr(c, "text"):
                        result_text += c.text

        intel = _parse_presence_response(result_text, biz_name)

        if verbose:
            print(f"    [Presence] {biz_name}:")
            print(f"      Website: {intel.get('website', '?')}")
            print(f"      POS/Payment: {intel.get('payment_system', '?')}")
            print(f"      Status: {intel.get('business_status', '?')}")
            print(f"      Size: {intel.get('size_estimate', '?')}")
            print(f"      Hiring: {intel.get('hiring', '?')}")
            print(f"      Reviews: {intel.get('review_count', '?')}")

        return intel

    except Exception as e:
        if verbose:
            print(f"    [Presence] Error: {str(e)[:80]}")
        return {
            "website": None,
            "payment_system": "unknown",
            "business_status": "unknown",
            "size_estimate": "unknown",
            "hiring": False,
            "review_count": 0,
            "social_profiles": [],
            "error": str(e)[:100],
        }


def _parse_presence_response(text, biz_name):
    """Parse OpenAI's structured response into intelligence dict."""
    intel = {
        "website": None,
        "payment_system": "unknown",
        "business_status": "operating",
        "size_estimate": "unknown",
        "hiring": False,
        "review_count": 0,
        "social_profiles": [],
        "raw": text[:500],
    }

    text_lower = text.lower()

    # Website extraction
    url_match = re.search(r"https?://[^\s\)\]>\"]+", text)
    if url_match:
        url = url_match.group().rstrip(".,;)")
        # Skip social media and directory links
        if not any(s in url for s in ["facebook.com", "instagram.com", "yelp.com", "google.com/maps"]):
            intel["website"] = url

    # Payment system detection
    pos_systems = {
        "square": "diy", "stripe": "diy", "paypal": "diy",
        "clover": "mid", "shopify": "mid",
        "toast": "enterprise", "lightspeed": "enterprise",
        "fiserv": "enterprise", "first data": "enterprise",
        "revel": "enterprise", "aloha": "enterprise",
    }
    for pos, tier in pos_systems.items():
        if pos in text_lower:
            intel["payment_system"] = pos
            intel["payment_tier"] = tier
            break

    # Business status
    if any(s in text_lower for s in ["coming soon", "opening soon", "under construction",
                                      "not yet open", "launching"]):
        intel["business_status"] = "coming_soon"
    elif any(s in text_lower for s in ["recently opened", "just opened", "newly opened",
                                        "now open", "grand opening"]):
        intel["business_status"] = "newly_opened"
    elif any(s in text_lower for s in ["closed", "permanently closed", "out of business"]):
        intel["business_status"] = "closed"

    # Size estimate
    if any(s in text_lower for s in ["solo", "sole", "one-person", "individual"]):
        intel["size_estimate"] = "solo"
    elif any(s in text_lower for s in ["small team", "2-5", "few employees"]):
        intel["size_estimate"] = "small"
    elif any(s in text_lower for s in ["medium", "6-20", "growing team", "several"]):
        intel["size_estimate"] = "medium"
    elif any(s in text_lower for s in ["large", "20+", "many employees"]):
        intel["size_estimate"] = "large"

    # Hiring
    if any(s in text_lower for s in ["hiring", "job open", "positions available",
                                      "help wanted", "looking for staff"]):
        intel["hiring"] = True

    # Review count (attempt extraction)
    review_match = re.search(r"(\d+)\s+reviews?", text_lower)
    if review_match:
        intel["review_count"] = int(review_match.group(1))

    # Social profiles
    for platform in ["facebook", "instagram", "yelp", "google business", "tiktok"]:
        if platform in text_lower:
            intel["social_profiles"].append(platform)

    return intel


# ═══════════════════════════════════════════════════════════════════
#  COMPOSITE INTELLIGENCE SCORING
# ═══════════════════════════════════════════════════════════════════

def compute_web_intelligence_score(website_intel=None, presence_intel=None):
    """
    Combine website analysis + business presence into a single
    web intelligence score (0-100) suitable for lead scoring.

    Dimensions:
      Technographic Opportunity (40%): No processor = 100, DIY = 75, Enterprise = 15
      Intent Signals (30%): Coming soon = 100, expansion = 80, hiring = 60
      Digital Maturity (15%): Has website + social = lower urgency but real biz
      Validation (15%): Reviews, status = real business confirmation

    Returns: {"web_score": int, "factors": list, "penalties": list}
    """
    score_parts = {
        "technographic": 50,  # Default mid
        "intent": 50,
        "maturity": 50,
        "validation": 50,
    }
    factors = []
    penalties = []

    # ── Technographic (from website analysis) ──
    if website_intel:
        score_parts["technographic"] = website_intel.get("technographic_score", 50)

        tier = website_intel.get("tech_tier", "none")
        if tier == "none":
            factors.append("no_payment_processor")
        elif tier == "diy":
            factors.append(f"diy_processor:{','.join(p['name'] for p in website_intel.get('payment_processors', []))}")
        elif tier == "enterprise":
            penalties.append(f"enterprise_pos:{','.join(p['name'] for p in website_intel.get('payment_processors', []))}")

    # ── Intent (from website + presence) ──
    intent_total = 0

    if website_intel:
        for sig in website_intel.get("intent_signals", []):
            intent_total += sig["weight"]
            if sig["weight"] > 0:
                factors.append(f"intent:{sig['signal']}")
            else:
                penalties.append(f"anti_intent:{sig['signal']}")

    if presence_intel:
        status = presence_intel.get("business_status", "")
        if status == "coming_soon":
            intent_total += 30
            factors.append("coming_soon_business")
        elif status == "newly_opened":
            intent_total += 20
            factors.append("newly_opened")
        elif status == "closed":
            intent_total -= 50
            penalties.append("business_closed")

        if presence_intel.get("hiring"):
            intent_total += 10
            factors.append("actively_hiring")

        pay = presence_intel.get("payment_system", "unknown")
        if pay == "unknown":
            intent_total += 10  # Can't find their POS = likely don't have one
            factors.append("no_known_pos")
        elif presence_intel.get("payment_tier") == "diy":
            intent_total += 5
            factors.append(f"uses_{pay}_switchable")
        elif presence_intel.get("payment_tier") == "enterprise":
            intent_total -= 15
            penalties.append(f"uses_{pay}_locked")

    score_parts["intent"] = max(0, min(100, 50 + intent_total))

    # ── Digital Maturity ──
    if website_intel:
        has_website = website_intel.get("accessible", False)
        social_count = len(website_intel.get("social_presence", []))
        ordering = len(website_intel.get("ordering_platforms", []))

        if not has_website and not website_intel.get("url"):
            # No website = very new, high opportunity
            score_parts["maturity"] = 80
            factors.append("no_website_new_biz")
        elif has_website and social_count >= 2:
            # Established online = real business
            score_parts["maturity"] = 60
            factors.append("established_online_presence")
        elif has_website:
            score_parts["maturity"] = 70
        else:
            score_parts["maturity"] = 75

    if presence_intel:
        social = presence_intel.get("social_profiles", [])
        if len(social) >= 3:
            score_parts["maturity"] = min(score_parts["maturity"], 55)
            factors.append("strong_digital_presence")

    # ── Validation ──
    if presence_intel:
        reviews = presence_intel.get("review_count", 0)
        if reviews > 50:
            score_parts["validation"] = 65  # Established business, real but not urgent
        elif reviews > 10:
            score_parts["validation"] = 75  # Growing, good sign
        elif reviews > 0:
            score_parts["validation"] = 85  # New with some traction
        else:
            score_parts["validation"] = 70  # No reviews = very new OR no online presence

        if presence_intel.get("business_status") == "closed":
            score_parts["validation"] = 0
            penalties.append("failed_validation_closed")

        size = presence_intel.get("size_estimate", "unknown")
        if size == "solo":
            score_parts["validation"] += 5   # Solo = owner answers phone
            factors.append("solo_operator")
        elif size == "large":
            score_parts["validation"] -= 10  # Large = harder to reach decision maker
            penalties.append("large_company")

    # ── Composite weighted score ──
    web_score = round(
        score_parts["technographic"] * 0.40 +
        score_parts["intent"] * 0.30 +
        score_parts["maturity"] * 0.15 +
        score_parts["validation"] * 0.15
    )
    web_score = max(0, min(100, web_score))

    return {
        "web_score": web_score,
        "detail_scores": score_parts,
        "factors": factors,
        "penalties": penalties,
    }


# ═══════════════════════════════════════════════════════════════════
#  CLI — Test Analysis
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python web_intel.py URL                         — Analyze specific website")
        print("  python web_intel.py 'Biz Name' 'City' 'State'  — Full presence analysis")
        sys.exit(0)

    if sys.argv[1].startswith("http"):
        # URL analysis
        url = sys.argv[1]
        print(f"\n{'='*70}")
        print(f"  Website Intelligence Analysis: {url}")
        print(f"{'='*70}\n")
        intel = analyze_website(url, verbose=True)

        # Compute composite score
        composite = compute_web_intelligence_score(website_intel=intel)
        print(f"\n  Composite Web Intelligence Score: {composite['web_score']}/100")
        if composite["factors"]:
            print(f"  Factors: {', '.join(composite['factors'])}")
        if composite["penalties"]:
            print(f"  Penalties: {', '.join(composite['penalties'])}")
    else:
        # Business presence analysis
        biz = sys.argv[1]
        city = sys.argv[2] if len(sys.argv) > 2 else "Denver"
        state = sys.argv[3] if len(sys.argv) > 3 else "CO"

        print(f"\n{'='*70}")
        print(f"  Business Presence Intelligence: {biz} ({city}, {state})")
        print(f"{'='*70}\n")

        # Step 1: Get overall business presence
        presence = analyze_business_presence(biz, city, state, verbose=True)

        # Step 2: If we found a website, analyze it
        website_intel = None
        if presence.get("website"):
            print(f"\n  Analyzing website: {presence['website']}")
            website_intel = analyze_website(presence["website"], verbose=True)
        else:
            print(f"\n  No website found — very new business or pre-launch")
            website_intel = analyze_website(None, verbose=False)

        # Step 3: Composite score
        composite = compute_web_intelligence_score(
            website_intel=website_intel,
            presence_intel=presence,
        )
        print(f"\n  {'─'*50}")
        print(f"  Composite Web Intelligence Score: {composite['web_score']}/100")
        print(f"  Detail: tech={composite['detail_scores']['technographic']} "
              f"intent={composite['detail_scores']['intent']} "
              f"maturity={composite['detail_scores']['maturity']} "
              f"valid={composite['detail_scores']['validation']}")
        if composite["factors"]:
            print(f"  ✅ Factors: {', '.join(composite['factors'])}")
        if composite["penalties"]:
            print(f"  ❌ Penalties: {', '.join(composite['penalties'])}")
        print(f"  {'─'*50}")
