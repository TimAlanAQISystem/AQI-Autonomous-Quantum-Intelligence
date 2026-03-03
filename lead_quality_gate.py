#!/usr/bin/env python3
"""
LEAD QUALITY GATE — Alan's Bouncer
====================================
Screens all leads before they enter the database or dialer.
Rejects: corporate/franchise/government, article headlines, search queries,
non-businesses, competitors, foreign numbers, toll-free numbers, and garbage.

Usage:
    from lead_quality_gate import screen_lead, screen_batch
    
    # Single lead
    result = screen_lead(name="First Field Grocer", phone="+13477822856")
    if result["pass"]:
        # Import the lead
    
    # Batch screening
    results = screen_batch(leads_list)
"""

import re
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("QUALITY_GATE")

# =====================================================
# REJECTION PATTERNS — Built from real garbage data
# =====================================================

# Corporate/Franchise/Chain keywords (case-insensitive substring match)
CORPORATE_KEYWORDS = [
    "spacex", "space exploration technologies", "general dynamics", "caci inc",
    "cbs news", "nbc ", "abc news", "fox news", "cnn ", "msnbc",
    "walmart", "target corp", "amazon", "google", "microsoft", "apple inc",
    "jpmorgan", "bank of america", "wells fargo", "chase ", "citibank",
    "jimmy choo", "louis vuitton", "gucci", "prada", "chanel",
    "starbucks", "mcdonald", "burger king", "wendy's", "taco bell",
    "subway ", "chipotle", "domino's", "pizza hut", "papa john",
    "home depot", "lowe's", "costco", "sam's club", "best buy",
    "heartland dental", "aspen dental", "western dental",
    "sugared + bronzed", "sugared and bronzed",
    "la la land kind cafe", "la la land kind café",
    "snooze an a.m. eatery", "snooze, an a.m.",
    "handel's homemade", "handel's ice cream",
    "fox in the snow", "kimpton", "hilton", "marriott", "hyatt",
    "sheraton", "westin", "ritz-carlton", "four seasons",
    "y combinator", "yc s2", "yc x2", "yc w2",
    "general electric", "ge ", "ibm ", "oracle", "salesforce",
    "uber ", "lyft ", "airbnb", "doordash", "grubhub",
    "yelp for business", "yelp inc",
    "united states postal", "usps", "fedex", "ups ",
]

# Government/institutional keywords
GOVERNMENT_KEYWORDS = [
    "department of", "dept of", "county of", "city of",
    "state of", "united states", "u.s. ", "us government",
    "public school", "school district", "board of education",
    "police department", "fire department", "sheriff",
    "social security", "irs ", "fbi ", "cia ", "dea ",
    "epa ", "fda ", "sec ", "fcc ", "ftc ",
    "union station", "port authority", "transit authority",
    "miami-dade county", "miami dade county",
    "public library", "municipal", "government",
]

# Competitor keywords (merchant services, POS, payment processors)
COMPETITOR_KEYWORDS = [
    "merchant services", "merchant cash advance", "payment processing",
    "credit card processing", "pos system", "point of sale",
    "square ", "stripe ", "clover ", "toast pos", "lightspeed",
    "shopify pos", "paypal ", "braintree", "adyen ", "worldpay",
    "firstdata", "first data", "fiserv", "global payments",
    "dharma merchant", "helcim", "stax ", "fattmerchant",
    "onehubpos", "hubpos",
]

# Article headline patterns (regex)
ARTICLE_PATTERNS = [
    r'\b(opening|opens|opened)\s+(soon|next|this|in|at|on|quietly|officially)',
    r'\b(grand\s+opening)',
    r'\b(new\s+.{3,30}\s+opens?\b)',
    r'\b(officially\s+open)',
    r'\b(construction\s+update)',
    r'\b(under\s+new\s+management)',
    r'\b(celebrates?\s+\d+\s+years?)',
    r'\b(prepares?\s+to\s+open)',
    r'\b(delays?\s+.{3,20}\s+opening)',
    r'\b(makes?\s+plans?\s+in)',
    r'\b(now\s+open\s+in)',
    r'\b(to\s+open\s+\d+\s)',
    r'\b(updated?:)',
    r'^\s*new\s+.{5,40}\s+restaurant',
    r'\bvs\b.*(live|score|game|match)',
    r'\b(gets?\s+a\s+glamorous)',
    r'\b(beauty\s+scene)',
    r'\b(hottest\s+new)',
    r'\b(opening\s+(second|third|new)\s+)',
    r'^\s*breaking:',
    r'^\s*exclusive:',
    r'^\s*report:',
]

# Non-business patterns (search queries, directories, addresses, etc.)
NON_BUSINESS_PATTERNS = [
    r'^\d+\s+\w+\s+(st|ave|blvd|dr|rd|ln|ct|way|circle)\b',  # Street addresses
    r'\b(for\s+sale|for sale)\b',
    r'\b(how\s+to\s+start)',
    r'\b(find\s+a\s+)',
    r'\b(directory|listings?\b)',
    r'\b(business\s+directory)',
    r'\b(faqs?\s*[—–-])',
    r'\b(project\s+categories)',
    r'\b(locations?\s*[—–-])',
    r'menu\s*$',  # "restaurant menu" searches
    r'\b(in\s+(illinois|california|texas|florida|new york|ohio)\s*$)',  # "X in State" search
    r'bodyrubs?\b',
    r'\b(contractors|electricians|plumbers|lawyers|dentists?)\s+(in\s+|near\s+)',  # Service searches
    r'\b(motor\s+city\s+match)',
    r'\bmanta\.com\b',
    r'\bbehance\b',
    r'^\s*@\w+',  # Social media handles as names
    r'^\s*credit\s+card\s+(machine|processing|terminal)',
    r'\b(timeline\s+of\s+)',
    r'^\s*(best|top)\s+\d+\s+',  # "Best 10..." listicles
]

# Foreign phone patterns (non-US/Canada)
def is_foreign_phone(phone: str) -> bool:
    """Reject non-US/Canada phone numbers"""
    if not phone:
        return True
    clean = re.sub(r'[^\d+]', '', phone)
    digits = clean.lstrip('+')
    
    # Must be 10-11 digits for US
    if len(digits) == 10:
        return False  # Valid US
    if len(digits) == 11 and digits.startswith('1'):
        return False  # Valid US with country code
    return True  # Foreign or invalid


def is_toll_free(phone: str) -> bool:
    """Reject toll-free numbers (not direct SMB lines)"""
    if not phone:
        return True
    clean = re.sub(r'[^\d]', '', phone)
    # Remove leading 1 for country code
    if len(clean) == 11 and clean.startswith('1'):
        clean = clean[1:]
    if len(clean) >= 10:
        prefix = clean[:3]
        return prefix in ('800', '888', '877', '866', '855', '844', '833')
    return False


def is_generic_name(name: str) -> bool:
    """Reject names that are just a person's name (no business name)"""
    if not name or name.strip().upper() in ('UNKNOWN', 'N/A', 'NONE', ''):
        return True
    # Just first name + last name (2 words, both capitalized, no business words)
    words = name.strip().split()
    if len(words) == 2 and all(w[0].isupper() and w[1:].islower() for w in words if len(w) > 1):
        # Check if it looks like a business name (has business-type words)
        business_words = ['cafe', 'grill', 'bistro', 'salon', 'shop', 'store', 
                         'market', 'auto', 'dental', 'spa', 'bar', 'pub',
                         'restaurant', 'bakery', 'florist', 'grocer', 'boutique',
                         'jewelers', 'motors', 'books', 'sports', 'music',
                         'hardware', 'diner', 'cycles', 'toys', 'clothing',
                         'solutions', 'systems', 'services', 'retail',
                         'inc', 'llc', 'corp', 'ltd', 'co']
        name_lower = name.lower()
        if not any(bw in name_lower for bw in business_words):
            return True  # Looks like a person's name, not a business
    return False


# =====================================================
# MAIN SCREENING FUNCTION
# =====================================================

def screen_lead(
    name: str = "",
    phone: str = "",
    business_type: str = "",
    notes: str = "",
    strict: bool = True
) -> Dict[str, Any]:
    """
    Screen a single lead for quality.
    
    Returns:
        {
            "pass": bool,
            "reject_reason": str or None,
            "reject_category": str or None,
            "confidence": float (0-1)
        }
    """
    name_lower = (name or "").lower().strip()
    phone_clean = (phone or "").strip()
    
    # CHECK 1: No name
    if not name_lower or name_lower in ('unknown', 'n/a', 'none', 'test', 'test merchant'):
        return _reject("NO_NAME", "No business name provided", 1.0)
    
    # CHECK 2: Foreign phone
    if is_foreign_phone(phone_clean):
        return _reject("FOREIGN_PHONE", f"Non-US phone number: {phone_clean}", 1.0)
    
    # CHECK 3: Toll-free
    if is_toll_free(phone_clean):
        return _reject("TOLL_FREE", f"Toll-free number: {phone_clean}", 0.95)
    
    # CHECK 4: Corporate/Franchise
    for keyword in CORPORATE_KEYWORDS:
        if keyword in name_lower:
            return _reject("CORPORATE", f"Corporate/franchise match: '{keyword}'", 0.95)
    
    # CHECK 5: Government
    for keyword in GOVERNMENT_KEYWORDS:
        if keyword in name_lower:
            return _reject("GOVERNMENT", f"Government/institutional match: '{keyword}'", 0.95)
    
    # CHECK 6: Competitor
    for keyword in COMPETITOR_KEYWORDS:
        if keyword in name_lower:
            return _reject("COMPETITOR", f"Competitor match: '{keyword}'", 0.98)
    
    # CHECK 7: Article headline
    for pattern in ARTICLE_PATTERNS:
        if re.search(pattern, name_lower, re.IGNORECASE):
            return _reject("ARTICLE", f"Article headline pattern: '{pattern}'", 0.90)
    
    # CHECK 8: Non-business
    for pattern in NON_BUSINESS_PATTERNS:
        if re.search(pattern, name_lower, re.IGNORECASE):
            return _reject("NON_BUSINESS", f"Non-business pattern: '{pattern}'", 0.85)
    
    # CHECK 9: Person's name (not a business)
    if strict and is_generic_name(name):
        return _reject("PERSON_NAME", f"Looks like a person's name, not a business: '{name}'", 0.70)
    
    # PASSED ALL CHECKS
    return {"pass": True, "reject_reason": None, "reject_category": None, "confidence": 1.0}


def _reject(category: str, reason: str, confidence: float) -> Dict[str, Any]:
    return {
        "pass": False,
        "reject_reason": reason,
        "reject_category": category,
        "confidence": confidence
    }


def screen_batch(leads: List[Dict]) -> Dict[str, Any]:
    """
    Screen a batch of leads.
    
    Args:
        leads: List of dicts with keys: name, phone, business_type, notes
    
    Returns:
        {
            "total": int,
            "passed": int,
            "rejected": int,
            "rejection_breakdown": {category: count},
            "passed_leads": [lead dicts that passed],
            "rejected_leads": [lead dicts with reject info]
        }
    """
    passed_leads = []
    rejected_leads = []
    breakdown = {}
    
    for lead in leads:
        result = screen_lead(
            name=lead.get("name", ""),
            phone=lead.get("phone", lead.get("phone_number", "")),
            business_type=lead.get("business_type", ""),
            notes=lead.get("notes", "")
        )
        
        if result["pass"]:
            passed_leads.append(lead)
        else:
            lead_copy = dict(lead)
            lead_copy["_reject_reason"] = result["reject_reason"]
            lead_copy["_reject_category"] = result["reject_category"]
            rejected_leads.append(lead_copy)
            cat = result["reject_category"]
            breakdown[cat] = breakdown.get(cat, 0) + 1
    
    return {
        "total": len(leads),
        "passed": len(passed_leads),
        "rejected": len(rejected_leads),
        "rejection_breakdown": breakdown,
        "passed_leads": passed_leads,
        "rejected_leads": rejected_leads
    }


# =====================================================
# CLI TEST MODE
# =====================================================
if __name__ == "__main__":
    # Test with known garbage
    test_cases = [
        ("First Field Grocer", "+13477822856"),           # SHOULD PASS
        ("Classic Ocean Jewelers", "+17475647853"),        # SHOULD PASS
        ("SPACE EXPLORATION TECHNOLOGIES CORP.", "+13103636000"),  # CORPORATE
        ("Miami-dade county public schools", "+13056918021"),      # GOVERNMENT
        ("Merchant Cash Advance For Business", "+18666106569"),    # COMPETITOR
        ("Bistro Opening Soon in Downtown", "+15551234567"),       # ARTICLE
        ("Washington Wizards vs Clippers Live", "+12026283200"),   # ARTICLE
        ("Find a Cruise", "+18004604518"),                        # NON-BUSINESS + TOLL-FREE
        ("1124 Sunnymeade Dr Nashville TN", "+16155609753"),       # ADDRESS
        ("Jennifer Chen", "+13236819198"),                        # PERSON NAME
        ("Unknown", "+15551234567"),                              # NO NAME
        ("Moon Toys", "+97142678494"),                            # FOREIGN PHONE
    ]
    
    print("LEAD QUALITY GATE — TEST RESULTS")
    print("=" * 80)
    for name, phone in test_cases:
        result = screen_lead(name=name, phone=phone)
        status = "PASS" if result["pass"] else f"REJECT [{result['reject_category']}]"
        print(f"  {name:45s} | {status}")
    
    print()
    print("Testing complete.")
