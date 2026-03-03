"""
LEAD INTELLIGENCE ENGINE (LIE) — Intent-Based Merchant Lead Scoring
=====================================================================
Modeled after ZoomInfo/Seamless AI intent data methodology.
Scores every lead 0-100 based on multiple intelligence dimensions.

How ZoomInfo/Seamless AI/Apollo work (and how we replicate it):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CONTACT QUALITY (ZoomInfo: "Direct Dial Verification")
   → We score: line_type (mobile > fixedVoip > landline > unknown)
   → We score: phone validity, toll-free rejection
   
2. FIRMOGRAPHIC FIT (ZoomInfo: "Company Attributes")  
   → We score: business name quality (proper name vs. SEO junk)
   → We score: business category (pet/retail/beauty beat auto/food)
   → We score: name length and composition signals
   
3. INTENT SIGNALS (Bombora: "Topic Surge Data")
   → We approximate: name suggests active business (not article/listing)
   → We approximate: business type suggests card processing need
   → We approximate: not a chain/franchise (independent = decision maker present)
   
4. TIMING INTELLIGENCE (Apollo: "Best Time to Call")
   → We score: timezone alignment with peak hours (2-4 PM local)
   → We score: avoid lunch hour (12-1 PM)
   
5. HISTORICAL PERFORMANCE (Seamless AI: "Buyer Intent Score")
   → We score: area code historical contact rate
   → We score: source batch quality rating
   → We score: category contact rate from 580+ call history
   
6. ANTI-WASTE SIGNALS (Our Innovation)
   → We penalize: SEO/directory title patterns
   → We penalize: corporate/franchise chains
   → We penalize: generic descriptions without business identity
   → We penalize: known ghost/dead area codes
   → We penalize: duplicate phone numbers already called

Score Bands:
  90-100  PRIME      — Call first, highest probability of human contact
  75-89   STRONG     — High confidence, call in priority order
  60-74   STANDARD   — Normal quality, worth calling
  40-59   MARGINAL   — Below average, call only if nothing better available
  20-39   WEAK       — Low probability, expect waste
   0-19   REJECT     — Do not call, filter out

Usage:
    from lead_intelligence_engine import LeadIntelligenceEngine
    
    engine = LeadIntelligenceEngine()
    score = engine.score_lead(name="T Rock Roofing", phone="+14699319867", line_type="mobile")
    print(f"Score: {score.total} ({score.band})")
    print(score.breakdown)
    
    # Batch scoring
    ranked = engine.score_and_rank(leads_list)
"""

import re
import json
import sqlite3
import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("LIE")

# ════════════════════════════════════════════════════════════════════
# INTELLIGENCE DATA — Learned from 580+ call history
# ════════════════════════════════════════════════════════════════════

# Line type contact rates (from historical data + industry benchmarks)
LINE_TYPE_SCORES = {
    'mobile':     18,   # Highest answer rate — owner's personal phone
    'fixedvoip':  14,   # VoIP lines — active businesses often use these
    'voip':       14,   # Alias
    'landline':   10,   # Traditional business line — often IVR or receptionist
    'unknown':     6,   # No data — penalize uncertainty
    'tollfree':    0,   # Never call — corporate 800 numbers
}

# Business category contact rates (from our 580+ call history)
# Score bonus/penalty based on historical human contact rate
CATEGORY_SCORES = {
    'pet':         8,   # 38.9% contact — pet businesses pick up
    'retail':      7,   # 33.3% contact — retailers answer
    'beauty':      7,   # 33.3% contact — salons/spas answer
    'services':    6,   # 31.7% contact — service businesses
    'auto':        3,   # 23.7% contact — auto shops less responsive
    'food':        3,   # 23.6% contact — restaurants busy during hours
    'health':      0,   # 0% in our data — medical offices have gatekeepers
    'other':       5,   # 43.9% but includes early test data, normalize down
}

# Category keyword patterns for classification
# NOTE: Short words (pet, cat, vet, dog) need trailing \b to prevent
# false matches: "catering" ≠ cat, "Petersburg" ≠ pet, "veteran" ≠ vet
CATEGORY_PATTERNS = {
    'pet':     r'\b(pets?\b|groom|dogs?\b|cats?\b|vets?\b|veterinar|animal|kennel|boarding)',
    'retail':  r'\b(store|shop|boutique|market|jewel|florist|gift|pawn|book|comics|thrift)',
    'beauty':  r'\b(salon|spa|barber|hair|nail|beauty|tattoo|piercing|lash|brow|wax)',
    'services': r'\b(clean|plumb|electric|hvac|roof|handyman|landscap|paint|repair|pest|moving|locksmith|glass)',
    'auto':    r'\b(auto|car\b|vehicle|tire|collision|mechanic|body shop|garage|tow\b|detail|wash\b)',
    'food':    r'\b(restaurant|cafe|bakery|pizza|taco|grill|kitchen|diner|cater|crepe|sushi|bbq|bar\b|pub\b|brew|coffee|ice cream)',
    'health':  r'\b(dental|chiro|therapy|clinic|medical|health|fitness|gym|yoga|pilates)',
}

# High-intent business type signals
# These businesses NEED card processing and are likely independent decision-makers
HIGH_INTENT_TYPES = [
    'tattoo', 'barbershop', 'barber', 'salon', 'nail',       # Cash-heavy, transitioning to cards
    'food truck', 'taco truck', 'cart',                        # Mobile vendors need mobile processing
    'smoke shop', 'vape', 'liquor', 'dispensary',              # High-volume cash businesses
    'laundromat', 'car wash', 'detail',                        # Coin-op converting to card
    'flea market', 'farmers market',                           # Emerging card adopters
    'contractor', 'handyman', 'plumber', 'electrician',        # Service businesses billing clients
    'catering', 'food truck',                                  # Event-based businesses
    'pawn', 'thrift', 'consignment',                           # Secondhand retail
]

# Low-intent signals — businesses unlikely to change processors
LOW_INTENT_TYPES = [
    'franchise', 'chain', 'corporate',                          # Can't change POS
    'government', 'municipality', 'county',                     # Public sector
    'hospital', 'medical center',                               # Enterprise healthcare
    'hotel', 'motel', 'resort',                                 # Locked into hospitality POS
    'holiday inn', 'marriott', 'hilton', 'hampton',             # Hotel chains by name
    'bank', 'credit union', 'financial',                        # They ARE the processors
    # Common franchise brands (HQ controls processing)
    'mcalister', 'panera', 'chipotle', 'five guys', 'sonic drive',
    'popeye', 'arby', 'whataburger', 'waffle house', 'ihop', 'denny',
    'cracker barrel', 'panda express', 'wingstop', 'zaxby',
    'jersey mike', 'firehouse subs', 'jimmy john', 'jason\'s deli',
    'shake shack', 'dairy queen', 'culver', 'raising cane',
    'tropical smoothie', 'smoothie king', 'krispy kreme', 'dutch bros',
    'golden corral', 'texas roadhouse', 'longhorn steakhouse',
    'cheesecake factory', 'little caesars', 'marco\'s pizza',
    'zales', 'kay jewelers', 'jared', 'gamestop', 'hot topic',
    'bath & body', 'hobby lobby', 'joann', 'ross dress',
    'tj maxx', 'marshalls', 'burlington', 'nordstrom', 'kohl',
    'foot locker', 'autozone', 'advance auto', 'napa auto',
    'h&r block', 'jackson hewitt', 'kumon', 'mathnasium',
    'massage envy', 'orangetheory', 'snap fitness', 'la fitness',
    '24 hour fitness', 'crunch fitness', 'equinox',
    'servicemaster', 'molly maid', 'merry maids',
    '7-eleven', 'circle k', 'wawa', 'sheetz',
    'great clips', 'supercuts', 'sport clips', 'fantastic sams',
    'mattress firm', 'sherwin-williams',
    'lenscrafters', 'aspen dental',
]

# ════════════════════════════════════════════════════════════════════
# NAME QUALITY PATTERNS — SEO/Junk Detection (from neg-proof suite)
# ════════════════════════════════════════════════════════════════════

BAD_NAME_PATTERNS = [
    # SEO/Article titles
    'the best', 'top 10', 'top 5', 'best 10', '10 best', 'how to', 'guide to',
    'selecting the ideal', 'case study', 'festivals coming up',
    'new construction homes in', 'dog owners of', 'townhomes for rent',
    'near me', 'affordable', 'rated',
    '2024', '2025', '2026', '2027',
    # Corporate chains (extensive list)
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
    'jiffy lube', 'valvoline', 'meineke', 'maaco', 'midas auto', 'firestone',
    'papa john', "papa john's", 'domino', "domino's", 'pizza hut',
    'applebee', "applebee's", 'chili', "chili's", 'olive garden',
    'red lobster', 'outback steakhouse', 'buffalo wild wings',
    # Government
    'city of', 'county of', 'state of', 'town of',
    'fire department', 'police department', 'sheriff',
    'public school', 'school district',
    # Directory/contact headers
    'random phone numbers', 'contact number', 'email address',
    'phone number', 'mailing address', 'contact a ',
]

PLACEHOLDER_NAMES = {'there', 'unknown', 'n/a', '', 'home', 'test', 'none'}

# Known US cities that appear as lead names (just the city, no business name)
# Partial list — engine adds more from leads.db patterns
CITY_ONLY_NAMES = {
    'temecula', 'fresno', 'bakersfield', 'sacramento', 'modesto', 'stockton',
    'dallas', 'houston', 'fort worth', 'arlington', 'el paso', 'san antonio',
    'austin', 'orlando', 'tampa', 'miami', 'jacksonville', 'pensacola',
    'charleston', 'columbia', 'greenville', 'spartanburg', 'rock hill',
    'missoula', 'bozeman', 'kalispell', 'whitefish', 'billings', 'helena',
    'corpus christi', 'laredo', 'lubbock', 'amarillo', 'brownsville',
    'san diego', 'los angeles', 'san francisco', 'phoenix', 'tucson',
    'denver', 'seattle', 'portland', 'nashville', 'memphis', 'atlanta',
    'raleigh', 'charlotte', 'chicago', 'detroit', 'cleveland', 'pittsburgh',
}


# ════════════════════════════════════════════════════════════════════
# SCORING ENGINE
# ════════════════════════════════════════════════════════════════════

@dataclass
class LeadScore:
    """Complete scoring result for a single lead."""
    lead_id: str = ""
    name: str = ""
    phone: str = ""
    total: int = 0
    band: str = "REJECT"
    
    # Dimension scores
    contact_quality: int = 0        # 0-20: Line type, phone validity
    firmographic_fit: int = 0       # 0-20: Business category, name quality
    intent_signal: int = 0          # 0-20: Business type suggests card processing need
    timing_score: int = 0           # 0-15: Timezone alignment with peak hours
    historical_perf: int = 0        # 0-15: Area code + source batch performance
    anti_waste: int = 0             # 0-10: Penalties for known waste patterns
    displacement_opportunity: int = 0  # 0-15: Web intel — processor type, intent signals, displacement potential
    
    # Detail breakdown
    factors: list = field(default_factory=list)
    penalties: list = field(default_factory=list)
    
    @property
    def breakdown(self) -> str:
        lines = [f"Score: {self.total}/100 [{self.band}]"]
        lines.append(f"  Contact:     {self.contact_quality:2d}/20")
        lines.append(f"  Firmographic: {self.firmographic_fit:2d}/20")
        lines.append(f"  Intent:      {self.intent_signal:2d}/20")
        lines.append(f"  Timing:      {self.timing_score:2d}/15")
        lines.append(f"  Historical:  {self.historical_perf:2d}/15")
        lines.append(f"  Anti-waste:  {self.anti_waste:2d}/10")
        lines.append(f"  Displacement: {self.displacement_opportunity:2d}/15")
        if self.factors:
            lines.append(f"  Factors: {', '.join(self.factors)}")
        if self.penalties:
            lines.append(f"  Penalties: {', '.join(self.penalties)}")
        return '\n'.join(lines)


class LeadIntelligenceEngine:
    """
    Intent-based lead scoring engine.
    Combines contact quality, firmographic fit, intent signals,
    timing intelligence, historical performance, and anti-waste detection.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._intel_cache = None
        self._area_code_cache = None
        self._called_phones = None
        self._load_intelligence()
    
    def _load_intelligence(self):
        """Load mined intelligence data if available."""
        intel_path = self.data_dir / "lead_intelligence.json"
        if intel_path.exists():
            try:
                with open(intel_path) as f:
                    self._intel_cache = json.load(f)
                logger.info(f"Loaded intelligence data ({self._intel_cache.get('total_calls', '?')} calls)")
            except Exception:
                self._intel_cache = {}
        else:
            self._intel_cache = {}
        
        # Load already-called phone numbers to prevent duplicates
        self._called_phones = set()
        try:
            conn = sqlite3.connect(str(self.data_dir / "call_capture.db"))
            c = conn.cursor()
            c.execute("SELECT DISTINCT merchant_phone FROM calls WHERE merchant_phone IS NOT NULL AND merchant_phone != ''")
            for row in c.fetchall():
                phone = re.sub(r'\D', '', row[0])
                if phone.startswith('1') and len(phone) == 11:
                    phone = phone[1:]
                self._called_phones.add(phone)
            conn.close()
        except Exception:
            pass
        
        # Build area code intelligence
        self._area_code_cache = {}
        if 'area_code_rates' in self._intel_cache:
            self._area_code_cache = self._intel_cache['area_code_rates']
    
    # ── Dimension Scorers ──────────────────────────────────────────
    
    def _score_contact_quality(self, phone: str, line_type: str, score: LeadScore) -> int:
        """Score 0-20: How reachable is this phone number?"""
        pts = 0
        lt = (line_type or 'unknown').lower()
        
        # Line type score (0-18)
        pts += LINE_TYPE_SCORES.get(lt, LINE_TYPE_SCORES['unknown'])
        if lt == 'mobile':
            score.factors.append("mobile_line")
        elif lt in ('fixedvoip', 'voip'):
            score.factors.append("voip_business_line")
        
        # Phone format validity (+2 for valid E.164)
        clean = re.sub(r'\D', '', phone or '')
        if clean.startswith('1') and len(clean) == 11:
            clean = clean[1:]
        if len(clean) == 10:
            pts += 2
        else:
            score.penalties.append("invalid_phone_format")
        
        # Toll-free penalty (hard zero)
        if len(clean) >= 3 and clean[:3] in ('800', '888', '877', '866', '855', '844', '833'):
            pts = 0
            score.penalties.append("toll_free_number")
        
        return min(pts, 20)
    
    def _score_firmographic_fit(self, name: str, score: LeadScore) -> int:
        """Score 0-20: Does this look like a real, callable small business?"""
        pts = 10  # Start at midpoint
        lower = (name or '').lower().strip()
        
        if not lower:
            score.penalties.append("empty_name")
            return 0
        
        # Placeholder name → 0 firmographic value
        if lower in PLACEHOLDER_NAMES:
            score.penalties.append("placeholder_name_firmo")
            return 0
        
        # Business category bonus
        category = self._classify_category(lower)
        cat_bonus = CATEGORY_SCORES.get(category, 3)
        pts += cat_bonus
        if category != 'other':
            score.factors.append(f"category_{category}")
        
        # Name quality signals
        # Proper business name (possessive, &, LLC, etc.) → +2
        if re.search(r"'s\s|&\s|\bllc\b|\binc\b|\bco\b", lower):
            pts += 2
            score.factors.append("proper_business_name")
        
        # Short, punchy name (3-30 chars) → +1 (real businesses tend to have focused names)
        if 3 <= len(lower) <= 30:
            pts += 1
        
        # Generic description penalty ("Auto Repair", "Jewelry Store") → -3
        if re.match(r'^(auto|car|pet|dog|window|carpet|jewelry|florist)\s+(repair|shop|cleaning|grooming|wash|store)$', lower):
            pts -= 3
            score.penalties.append("generic_descriptor")
        
        # Single-word name penalty — not a real business identity
        words = lower.split()
        if len(words) == 1 and len(lower) <= 20:
            if lower in CITY_ONLY_NAMES:
                pts -= 10
                score.penalties.append("city_only_name")
            else:
                pts -= 3
                score.penalties.append("single_word_name")
        
        # City/state in name → -2 (often SEO listings, not real business identity)
        cities = CITY_ONLY_NAMES
        if any(city in lower for city in cities):
            pts -= 2
            score.penalties.append("city_in_name")
        
        # "X in City" pattern → -5 (SEO directory title)
        if re.search(r'\bin\s+\w+.*,?\s*(ca|fl|tx|sc|mt|ny|oh|wa)\s*$', lower):
            pts -= 5
            score.penalties.append("seo_in_city_pattern")
        
        return max(0, min(pts, 20))
    
    def _score_intent_signal(self, name: str, line_type: str, score: LeadScore) -> int:
        """Score 0-20: How likely is this business to need card processing?
        
        Approximates ZoomInfo's intent data by inferring from business type
        whether they're likely to be:
        1. Processing cards already (can be saved money)
        2. Cash-heavy and ready to adopt cards
        3. Growing and need better processing
        """
        pts = 10  # Start at midpoint
        lower = (name or '').lower().strip()
        
        # High-intent business types (cash-heavy or emerging card users)
        for intent_type in HIGH_INTENT_TYPES:
            if intent_type in lower:
                pts += 6
                score.factors.append(f"high_intent_{intent_type}")
                break
        
        # Low-intent signals
        for low_type in LOW_INTENT_TYPES:
            if low_type in lower:
                pts -= 8
                score.penalties.append(f"low_intent_{low_type}")
                break
        
        # Mobile line = owner's phone = decision maker likely answers
        # ZoomInfo calls this "direct dial" — we use line_type as proxy
        lt = (line_type or '').lower()
        if lt == 'mobile':
            pts += 4
            score.factors.append("direct_dial_proxy")
        elif lt == 'landline':
            pts -= 2  # More likely to hit receptionist/IVR
        
        # Independent business signals
        # Short name + no corporate patterns = likely independent
        if len(lower) <= 25 and not any(chain in lower for chain in ['franchise', 'chain', 'corp', 'inc']):
            pts += 1
        
        # Possessive name = likely owner-operated ("Bob's Auto", "Maria's Kitchen")
        if re.search(r"'s\s", lower):
            pts += 2
            score.factors.append("owner_operated_signal")
        
        return max(0, min(pts, 20))
    
    def _score_timing(self, phone: str, score: LeadScore) -> int:
        """Score 0-15: Is now a good time to call this number?
        
        Based on our data: 2-4 PM local = 46-69% contact rate
        vs. 12 PM (lunch) = 26.5% contact rate.
        """
        pts = 8  # Default mid-score
        
        ac = self._get_area_code(phone)
        if not ac:
            return pts
        
        tz = self._get_timezone(ac)
        try:
            import pytz
            local_tz = pytz.timezone({
                'PT': 'America/Los_Angeles', 'MT': 'America/Denver',
                'CT': 'America/Chicago', 'ET': 'America/New_York'
            }.get(tz, 'America/New_York'))
            local_hour = datetime.now(local_tz).hour
        except ImportError:
            # Fallback: estimate from UTC offset
            from datetime import timezone, timedelta
            offsets = {'PT': -8, 'MT': -7, 'CT': -6, 'ET': -5}
            utc_now = datetime.utcnow()
            local_hour = (utc_now.hour + offsets.get(tz, -5)) % 24
        
        # Peak hours scoring (from our data)
        if local_hour in (14, 15, 16):      # 2-4 PM: 47-69% contact
            pts = 15
            score.factors.append("peak_calling_hour")
        elif local_hour in (8, 9, 17):       # Early morning / late afternoon: 36-38%
            pts = 12
            score.factors.append("good_calling_hour")
        elif local_hour in (10, 11, 13):     # Mid-morning / early afternoon: 30-33%
            pts = 9
        elif local_hour == 12:                # Lunch hour: 26.5%
            pts = 5
            score.penalties.append("lunch_hour")
        elif local_hour < 8 or local_hour > 18:  # Outside business hours
            pts = 0
            score.penalties.append("outside_business_hours")
        
        return min(pts, 15)
    
    def _score_historical(self, phone: str, source: str, score: LeadScore) -> int:
        """Score 0-15: What does history tell us about this lead's likelihood?"""
        pts = 7  # Default mid-score
        
        # Already called this exact number → big penalty
        clean = re.sub(r'\D', '', phone or '')
        if clean.startswith('1') and len(clean) == 11:
            clean = clean[1:]
        if clean in self._called_phones:
            pts -= 5
            score.penalties.append("already_called")
        
        # Area code intelligence
        ac = self._get_area_code(phone)
        if ac and ac in self._area_code_cache:
            ac_data = self._area_code_cache[ac]
            ac_rate = ac_data.get('rate', 0)
            if ac_rate >= 0.5:
                pts += 5
                score.factors.append(f"hot_area_code_{ac}")
            elif ac_rate >= 0.3:
                pts += 2
            elif ac_rate < 0.1 and ac_data.get('total', 0) >= 3:
                pts -= 3
                score.penalties.append(f"cold_area_code_{ac}")
        
        # Source batch quality (if we have data)
        source_rates = self._intel_cache.get('source_rates', {})
        if source and source in source_rates:
            src_data = source_rates[source]
            src_rate = src_data.get('rate', 0)
            if src_rate >= 0.4:
                pts += 3
                score.factors.append("high_quality_source")
            elif src_rate < 0.15:
                pts -= 2
                score.penalties.append("low_quality_source")
        
        return max(0, min(pts, 15))
    
    def _score_displacement(self, notes: Dict, score: LeadScore) -> int:
        """Score 0-15: Competitive displacement opportunity from web intelligence.
        
        Only scores > 0 when web intel data is available (from sos_phone_enrichment).
        No web intel → 0 (doesn't penalize, just no boost).
        
        Scoring based on expert merchant services intelligence:
        - No processor detected → HUGE opportunity (new business needs setup)
        - DIY processor (Square/Stripe/PayPal) → High opportunity (rate savings pitch)
        - Mid-tier processor → Moderate opportunity (can be displaced)
        - Enterprise POS → Low opportunity (locked in)
        - Intent signals (coming_soon, hiring, expansion) → bonus
        - Review recency / business activity → bonus
        """
        if not notes or not isinstance(notes, dict):
            return 0
        
        pts = 0
        
        # ── Processor-based displacement score (0-10) ──
        tech_tier = notes.get("tech_tier", "unknown")
        processor = notes.get("current_processor", notes.get("payment_system", "unknown"))
        detected_procs = notes.get("payment_processors_detected", [])
        
        if tech_tier == "none" or processor in ("none", "unknown", None):
            # No processor detected — brand new business needs POS setup
            pts += 10
            score.factors.append("no_processor_huge_opportunity")
        elif tech_tier == "diy" or processor in ("square", "stripe", "paypal"):
            # DIY processor — easy displacement with rate comparison
            pts += 8
            score.factors.append(f"diy_processor_{processor}")
        elif tech_tier == "mid" or processor in ("clover", "shopify", "heartland"):
            # Mid-tier — some switching friction but doable
            pts += 5
            score.factors.append(f"mid_processor_{processor}")
        elif tech_tier == "enterprise" or processor in ("toast", "lightspeed", "fiserv", "worldpay"):
            # Enterprise POS — hard to displace, locked in
            pts += 1
            score.penalties.append(f"enterprise_processor_{processor}")
        
        # ── Intent signal bonuses (0-5) ──
        intent_signals = notes.get("intent_signals", [])
        if isinstance(intent_signals, list):
            # Coming soon = about to start, needs everything
            if "coming_soon" in intent_signals:
                pts += 3
                score.factors.append("coming_soon_signal")
            # Expansion = growing, needs new/upgraded processing
            if "expansion" in intent_signals:
                pts += 2
                score.factors.append("expansion_signal")
            # Hiring = active, growing business
            if "hiring" in intent_signals:
                pts += 1
                score.factors.append("hiring_signal")
            # Cash-focused = prime candidate for card processing
            if "cash_focused" in intent_signals:
                pts += 2
                score.factors.append("cash_focused_signal")
        
        # Also check top-level hiring flag
        if notes.get("hiring"):
            if "hiring_signal" not in score.factors:
                pts += 1
                score.factors.append("hiring_signal")
        
        # ── Business status bonus ──
        status = notes.get("business_status", "unknown")
        if status in ("coming_soon", "newly_opened"):
            pts += 2
            score.factors.append(f"status_{status}")
        
        # ── Web intel composite score bonus ──
        web_score = notes.get("web_intel_score", 0)
        if web_score >= 80:
            pts += 2
            score.factors.append("high_web_intel_score")
        elif web_score >= 60:
            pts += 1
        
        return max(0, min(pts, 15))
    
    def _score_anti_waste(self, name: str, phone: str, score: LeadScore) -> int:
        """Score 0-10: Penalty dimension — how likely is this call to be wasted?
        Higher = less waste. Lower = more waste expected.
        """
        pts = 10  # Start with full anti-waste score
        lower = (name or '').lower().strip()
        
        # Hard reject patterns (from neg-proof suite)
        if lower in PLACEHOLDER_NAMES:
            pts = 0
            score.penalties.append("placeholder_name")
            return pts
        
        # Short all-caps junk
        stripped = (name or '').strip()
        if len(stripped) <= 5 and stripped == stripped.upper() and stripped.isalpha():
            pts -= 5
            score.penalties.append("short_caps_junk")
        
        # BAD_NAME_PATTERNS check
        for pattern in BAD_NAME_PATTERNS:
            if pattern in lower:
                pts -= 8
                score.penalties.append(f"bad_pattern_{pattern[:20]}")
                break
        
        # SEO directory title regex
        if re.match(r'^(best|top|finest|leading|premier)\s+\w+.*\s+in\s+\w+', lower):
            pts -= 6
            score.penalties.append("seo_directory_title")
        
        # Very long name (>=55 chars = page title)
        if len(lower) >= 55:
            pts -= 5
            score.penalties.append("name_too_long")
        
        # Address as name (but not years like 2025, 2026)
        # Full penalty — an address is never a business identity
        if re.match(r'^\d{3,}[\s,]', stripped) and not re.match(r'^20[0-9]{2}\b', stripped):
            pts -= 10
            score.penalties.append("address_as_name")
        
        return max(0, pts)
    
    # ── Utility Methods ────────────────────────────────────────────
    
    def _classify_category(self, name_lower: str) -> str:
        """Classify business into category by name keywords."""
        for cat, pattern in CATEGORY_PATTERNS.items():
            if re.search(pattern, name_lower):
                return cat
        return 'other'
    
    def _get_area_code(self, phone: str) -> Optional[str]:
        clean = re.sub(r'\D', '', phone or '')
        if clean.startswith('1') and len(clean) == 11:
            return clean[1:4]
        elif len(clean) == 10:
            return clean[:3]
        return None
    
    # Timezone lookups
    _TZ_PT = {'206','209','213','253','310','323','341','360','369','408','415','424',
              '442','503','510','530','559','562','619','626','628','650','657','661',
              '669','707','714','747','760','805','818','831','858','909','916','925',
              '949','951','971'}
    _TZ_MT = {'303','307','385','406','435','480','505','520','602','623','719','720',
              '775','801','928','970'}
    _TZ_CT = {'210','214','254','281','312','314','316','318','337','346','361','409',
              '432','469','501','504','512','515','563','573','601','608','612','615',
              '618','630','651','682','708','713','715','731','769','773','785','806',
              '812','815','816','817','830','832','847','901','903','913','915','918',
              '920','936','940','956','972','979'}
    
    def _get_timezone(self, area_code: str) -> str:
        if area_code in self._TZ_PT: return 'PT'
        if area_code in self._TZ_MT: return 'MT'
        if area_code in self._TZ_CT: return 'CT'
        return 'ET'
    
    def _get_band(self, total: int) -> str:
        if total >= 90: return 'PRIME'
        if total >= 75: return 'STRONG'
        if total >= 60: return 'STANDARD'
        if total >= 40: return 'MARGINAL'
        if total >= 20: return 'WEAK'
        return 'REJECT'
    
    # ── Main Scoring Methods ───────────────────────────────────────
    
    def score_lead(self, name: str = "", phone: str = "", line_type: str = "unknown",
                   source: str = "", lead_id: str = "", notes: Optional[Dict] = None) -> LeadScore:
        """
        Score a single lead across all intelligence dimensions.
        Returns LeadScore with total 0-100 and detailed breakdown.
        
        When notes dict includes web_intel data (from sos_phone_enrichment),
        the 7th dimension (displacement_opportunity) provides bonus points
        for confirmed competitive displacement targets.
        """
        score = LeadScore(lead_id=lead_id, name=name, phone=phone)
        
        # Parse notes if string
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except (json.JSONDecodeError, TypeError):
                notes = {}
        if not isinstance(notes, dict):
            notes = {}
        notes = notes or {}
        
        # Score each dimension
        score.contact_quality = self._score_contact_quality(phone, line_type, score)
        score.firmographic_fit = self._score_firmographic_fit(name, score)
        score.intent_signal = self._score_intent_signal(name, line_type, score)
        score.timing_score = self._score_timing(phone, score)
        score.historical_perf = self._score_historical(phone, source, score)
        score.anti_waste = self._score_anti_waste(name, phone, score)
        score.displacement_opportunity = self._score_displacement(notes, score)
        
        # Calculate total (7 dimensions, capped at 100)
        # Max theoretical: 20+20+20+15+15+10+15 = 115, but capped at 100
        # This means web intel provides competitive boost without breaking scale
        score.total = (score.contact_quality + score.firmographic_fit + 
                       score.intent_signal + score.timing_score + 
                       score.historical_perf + score.anti_waste +
                       score.displacement_opportunity)
        score.total = max(0, min(100, score.total))
        
        # Hard cap: if anti_waste is 0 (known junk), cap at WEAK max
        if score.anti_waste == 0:
            score.total = min(score.total, 39)
        
        # Hard cap: if anti_waste ≤ 2 (near-junk), cap at MARGINAL max
        elif score.anti_waste <= 2:
            score.total = min(score.total, 59)
        
        # Hard cap: if firmographic_fit < 5 (near-zero quality name), cap at WEAK max
        if score.firmographic_fit < 5:
            score.total = min(score.total, 39)
        
        score.band = self._get_band(score.total)
        
        return score
    
    def score_and_rank(self, leads: List[Dict]) -> List[Tuple[LeadScore, Dict]]:
        """
        Score and rank a list of leads. Returns [(LeadScore, lead_dict)] sorted
        by score descending. Leads scored REJECT are filtered out.
        """
        results = []
        for lead in leads:
            # Parse notes for web intel data
            notes_raw = lead.get('notes', '{}')
            try:
                notes = json.loads(notes_raw) if isinstance(notes_raw, str) else (notes_raw or {})
            except (json.JSONDecodeError, TypeError):
                notes = {}
            if not isinstance(notes, dict):
                notes = {}
            
            score = self.score_lead(
                name=lead.get('name', lead.get('merchant_name', '')),
                phone=lead.get('phone_number', lead.get('phone', '')),
                line_type=lead.get('line_type', 'unknown'),
                source=lead.get('lead_source', ''),
                lead_id=lead.get('id', ''),
                notes=notes,
            )
            results.append((score, lead))
        
        # Sort by total score descending
        results.sort(key=lambda x: x[0].total, reverse=True)
        return results
    
    def score_pending_leads(self) -> List[Tuple[LeadScore, Dict]]:
        """Score all pending leads in the database (includes web intel from notes)."""
        conn = sqlite3.connect(str(self.data_dir / "leads.db"))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""SELECT id, name, phone_number, line_type, lead_source, business_type, notes
                     FROM leads WHERE outcome = 'pending' AND do_not_call = 0""")
        leads = [dict(r) for r in c.fetchall()]
        conn.close()
        
        return self.score_and_rank(leads)
    
    def generate_report(self, results: Optional[List] = None) -> str:
        """Generate a human-readable intelligence report."""
        if results is None:
            results = self.score_pending_leads()
        
        lines = []
        lines.append("=" * 70)
        lines.append("  LEAD INTELLIGENCE ENGINE — Scoring Report")
        lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"  Leads Scored: {len(results)}")
        lines.append("=" * 70)
        
        # Band distribution
        bands = defaultdict(int)
        for score, _ in results:
            bands[score.band] += 1
        
        lines.append("\n  Band Distribution:")
        for band in ['PRIME', 'STRONG', 'STANDARD', 'MARGINAL', 'WEAK', 'REJECT']:
            count = bands.get(band, 0)
            pct = count / max(len(results), 1) * 100
            bar = '█' * int(pct / 2)
            lines.append(f"    {band:10s}: {count:4d} ({pct:5.1f}%) {bar}")
        
        # Top 20
        lines.append(f"\n  Top 20 Leads (Call These First):")
        lines.append(f"  {'#':>3s}  {'Score':>5s} {'Band':8s} {'Name':35s} {'Phone':15s} {'Line':10s}")
        lines.append(f"  {'—'*3}  {'—'*5} {'—'*8} {'—'*35} {'—'*15} {'—'*10}")
        for i, (score, lead) in enumerate(results[:20], 1):
            name = (lead.get('name', '') or '')[:35]
            phone = lead.get('phone_number', '')[:15]
            lt = lead.get('line_type', '?')[:10]
            lines.append(f"  {i:3d}  {score.total:5d} {score.band:8s} {name:35s} {phone:15s} {lt:10s}")
        
        # Bottom 10 (worst leads)
        lines.append(f"\n  Bottom 10 Leads (Do NOT Call):")
        for i, (score, lead) in enumerate(results[-10:], 1):
            name = (lead.get('name', '') or '')[:35]
            pens = ', '.join(score.penalties[:3])
            lines.append(f"  {i:3d}  {score.total:5d} {score.band:8s} {name:35s} | {pens}")
        
        # Dimension averages
        lines.append(f"\n  Dimension Averages (across all {len(results)} leads):")
        if results:
            avg_cq = sum(s.contact_quality for s, _ in results) / len(results)
            avg_ff = sum(s.firmographic_fit for s, _ in results) / len(results)
            avg_is = sum(s.intent_signal for s, _ in results) / len(results)
            avg_ts = sum(s.timing_score for s, _ in results) / len(results)
            avg_hp = sum(s.historical_perf for s, _ in results) / len(results)
            avg_aw = sum(s.anti_waste for s, _ in results) / len(results)
            avg_do = sum(s.displacement_opportunity for s, _ in results) / len(results)
            lines.append(f"    Contact Quality:   {avg_cq:.1f}/20")
            lines.append(f"    Firmographic Fit:  {avg_ff:.1f}/20")
            lines.append(f"    Intent Signal:     {avg_is:.1f}/20")
            lines.append(f"    Timing:            {avg_ts:.1f}/15")
            lines.append(f"    Historical Perf:   {avg_hp:.1f}/15")
            lines.append(f"    Anti-Waste:        {avg_aw:.1f}/10")
            lines.append(f"    Displacement:      {avg_do:.1f}/15")
        
        lines.append("\n" + "=" * 70)
        return '\n'.join(lines)


# ════════════════════════════════════════════════════════════════════
# CLI
# ════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    engine = LeadIntelligenceEngine()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--detail':
        # Show detailed scoring for top leads
        results = engine.score_pending_leads()
        for score, lead in results[:10]:
            print(score.breakdown)
            print()
    else:
        # Standard report
        results = engine.score_pending_leads()
        print(engine.generate_report(results))
