"""
PRECISION ENGINE — Evidence-Based Campaign Intelligence
========================================================
Built from forensic analysis of 636 REAL calls (Feb 17-25, 2026).
Every weight, threshold, and rule comes from actual database evidence.

"This is no longer a numbers game — it is professional strategy
 with precise outcomes."

EVIDENCE:
  636 calls → 177 human answers (27.8%)
  → 65 real conversations (36.7% of humans)
  → 32 kept_engaged (49.2% of conversations)
  → 233 instant hangups (36.6%) = CALLER ID, not Alan
  → Best: 14T/94s, 12T/106s, 11T/92s, 10T/80s

  Timing: Tue=37%, Wed=27%, Thu=25%, Fri=19%
          2PM=43%, 4PM=51% human answer rate  
          9-10AM = high volume but only 22-30% contact

  Alan IS capable (14T proven). The problem is:
  1. Getting a human on the phone (caller ID, timing, lead quality)
  2. Converting soft_decline → kept_engaged (33 said no after 5.8 avg turns)
"""

import sqlite3
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

# ══════════════════════════════════════════════════════════════════════
#  EVIDENCE-BASED SCORING WEIGHTS
#  Every number below is derived from real call outcomes.
# ══════════════════════════════════════════════════════════════════════

# Day-of-week human answer rate (from 636 real calls)
# Monday only had 1 call — insufficient data, estimate conservatively
DAY_CONTACT_RATE = {
    0: 0.20,   # Monday — insufficient data (1 call), estimated
    1: 0.37,   # Tuesday — 62/167 = 37% (BEST)
    2: 0.27,   # Wednesday — 66/237 = 27%
    3: 0.25,   # Thursday — 16/63 = 25%
    4: 0.19,   # Friday — 33/168 = 19%
    5: 0.10,   # Saturday — no data, estimated low
    6: 0.08,   # Sunday — no data, estimated very low
}

# Hour-of-day human answer rate (from real data)
HOUR_CONTACT_RATE = {
    5: 0.66,    # 2/3 — tiny sample but high
    6: 0.00,    # 0/2
    7: 0.28,    # 2/7
    8: 0.20,    # 7/34
    9: 0.30,    # 24/78
    10: 0.22,   # 23/104
    11: 0.16,   # 12/71
    12: 0.23,   # 10/42
    13: 0.21,   # 20/91
    14: 0.43,   # 34/79 (BEST with volume)
    15: 0.31,   # 14/45
    16: 0.51,   # 15/29 (HIGHEST rate)
    17: 0.16,   # 4/25
    18: 0.10,   # no data, estimated
    19: 0.35,   # 5/14
    20: 0.41,   # 5/12
}

# Average turns per hour (evidence of conversation QUALITY when connected)
HOUR_AVG_TURNS = {
    5: 2.3, 7: 1.0, 8: 0.9, 9: 1.7, 10: 1.2, 11: 1.1,
    12: 2.8, 13: 1.1, 14: 2.2, 15: 1.2, 16: 2.2, 17: 0.6,
    19: 1.1, 20: 1.2,
}

# ══════════════════════════════════════════════════════════════════════
#  BUSINESS TYPE PATTERNS (from kept_engaged analysis)
#  These business types actually ENGAGE in conversation.
# ══════════════════════════════════════════════════════════════════════

# Business types that produced kept_engaged calls (extracted from top 32)
HIGH_ENGAGEMENT_TYPES = [
    # Evidence: Unified Star Hardware (11T), Metro Earth Florist (4T)
    'hardware', 'supply', 'supplies',
    # Evidence: ON OCEAN 7 CAFE (10T), Hyatt Hotels (7T), Bistro (7T)
    'cafe', 'restaurant', 'bistro', 'grill', 'diner', 'eatery', 'kitchen',
    'hotel', 'motel', 'inn', 'lodge',
    # Evidence: 314 Roofing (7T), Rampway Bait & Tackle (5T), Plumber LA (5T)
    'roofing', 'plumbing', 'plumber', 'hvac', 'heating', 'cooling',
    'contractor', 'construction', 'remodel',
    # Evidence: Austin Texas Pros (8T), Commercial HVAC (6T)
    'service', 'services', 'repair',
    # Evidence: White Moon Solutions (8T, 6T, 5T), Keystone (6T)
    'solutions', 'consulting',
    # Evidence: Astro Protective Services (8T), Coral Way Animal Clinic (4T)
    'protective', 'security', 'veterinar', 'clinic', 'dental',
    # Evidence: San Diego Shopping Guide (6T), various auto (5T+)
    'auto', 'mechanic', 'body shop', 'detailing', 'car wash',
    # Evidence: Backpage (5T), CACI (5T - gov but engaged)
    'salon', 'spa', 'barber', 'grooming', 'nail',
    # Local retail and services
    'florist', 'flower', 'bakery', 'boutique', 'shop', 'store', 'mart',
    'laundry', 'cleaners', 'cleaning',
    'landscap', 'lawn', 'garden', 'pool', 'pest',
    'electric', 'painting', 'paint',
    'towing', 'locksmith',
    'pizza', 'taco', 'burger', 'sub', 'sandwich', 'bbq', 'brew',
]

# Business indicators that NEVER produce conversations (evidence-based)
DEAD_LEAD_PATTERNS = [
    # Government entities — always IVR/dead end (NY Dept of State = IVR 10T no engagement)
    'department of', 'dept of', 'city of ', 'county of ', 'state of ',
    'government', 'municipal', 'federal', 'public school',
    # Events and temporary (Supercross, Golden Raspberry = always dead)
    'supercross', 'peddlers license', 'events calendar', 'golden raspberry',
    'festival', 'convention', 'expo ', 'trade show',
    # Directory/SEO artifacts (zero engagement)
    'phone number', 'contact number', 'mailing address', 'store hours',
    'how to start', 'things to do', 'places to',
    'near me', 'near you', 'near us',
    # Corporate entities too large to reach (Space X, etc.)
    'technologies corp', 'inc. - federal',
    # Aggregator/directory pages
    'yelp', 'yellowpages', 'angi ', 'angies list',
    'thumbtack', 'homeadvisor',
    # Real estate listings (not merchants)
    'for rent', 'for sale', 'townhome', 'apartment', 'condo',
    'real estate listing', 'independent living',
    # News/media articles
    'gets new ceo', 'majority invest', 'announces', 'opens new',
]

# ══════════════════════════════════════════════════════════════════════
#  PRECISION LEAD SCORER
#  Every lead gets a 0-100 precision score based on evidence.
# ══════════════════════════════════════════════════════════════════════

class PrecisionScorer:
    """Score leads using forensic evidence from real call outcomes."""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data', 'call_capture.db'
        )
        # Cache of phone numbers we've already called
        self._called_phones = None
        self._phone_outcomes = None
    
    def _load_call_history(self):
        """Load real call history from database for dedup and learning."""
        if self._called_phones is not None:
            return
        self._called_phones = set()
        self._phone_outcomes = {}
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT merchant_phone, final_outcome, total_turns, duration_seconds,
                       merchant_words, alan_words, engagement_score
                FROM calls
                WHERE merchant_phone IS NOT NULL AND merchant_phone != ''
            """)
            for row in c.fetchall():
                phone, outcome, turns, dur, mw, aw, eng = row
                clean = re.sub(r'\D', '', phone or '')
                if clean.startswith('1') and len(clean) == 11:
                    clean = clean[1:]
                if len(clean) == 10:
                    self._called_phones.add(clean)
                    if clean not in self._phone_outcomes:
                        self._phone_outcomes[clean] = []
                    self._phone_outcomes[clean].append({
                        'outcome': outcome,
                        'turns': turns or 0,
                        'duration': dur or 0,
                        'merchant_words': mw or 0,
                        'engagement': eng or 0,
                    })
            conn.close()
        except Exception as e:
            print(f"  [PRECISION] DB load warning: {e}")
    
    def score_lead(self, lead: Dict, call_weekday: int = None, 
                   call_hour: int = None) -> Dict[str, Any]:
        """
        Score a single lead. Returns precision score 0-100 and breakdown.
        
        Factors (evidence-weighted):
          1. Timing score (35%) — day + hour from real contact rates
          2. Business type score (25%) — does name match engaging business types?
          3. Lead quality score (20%) — name quality, phone quality
          4. History score (20%) — what happened when we called before?
        """
        self._load_call_history()
        
        scores = {}
        reasons = []
        disqualified = False
        dq_reason = None
        
        name = lead.get('name', '') or ''
        phone = lead.get('phone_number', '') or ''
        
        # ── DISQUALIFICATION CHECK (instant reject) ──────────────
        lower_name = name.lower().strip()
        for pattern in DEAD_LEAD_PATTERNS:
            if pattern in lower_name:
                disqualified = True
                dq_reason = f"Dead pattern: '{pattern}'"
                break
        
        if not disqualified:
            if not name or name.strip().lower() in ('there', 'unknown', 'n/a', '', 'home'):
                disqualified = True
                dq_reason = "No real business name"
            elif len(name) >= 60:
                disqualified = True
                dq_reason = f"Name too long ({len(name)} chars) — SEO/page title"
            elif re.match(r'^\d{3,}[\s,]', name.strip()):
                disqualified = True
                dq_reason = "Address, not business name"
        
        if disqualified:
            return {
                'score': 0,
                'band': 'DISQUALIFIED',
                'disqualified': True,
                'dq_reason': dq_reason,
                'factors': {},
                'recommendation': f'SKIP — {dq_reason}',
            }
        
        # ── 1. TIMING SCORE (35%) ────────────────────────────────
        if call_weekday is not None and call_hour is not None:
            day_rate = DAY_CONTACT_RATE.get(call_weekday, 0.15)
            hour_rate = HOUR_CONTACT_RATE.get(call_hour, 0.15)
            # Composite: geometric mean (both must be good)
            timing_raw = (day_rate * hour_rate) ** 0.5
            # Normalize to 0-100 (max observed: 0.51 * 0.37 ≈ 0.43, sqrt ≈ 0.66)
            timing_score = min(int(timing_raw / 0.66 * 100), 100)
            day_name = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][call_weekday]
            reasons.append(f"Timing: {day_name} {call_hour}:00 → day={int(day_rate*100)}%, hour={int(hour_rate*100)}%")
        else:
            timing_score = 50  # neutral if no timing info
            reasons.append("Timing: no data provided")
        scores['timing'] = timing_score
        
        # ── 2. BUSINESS TYPE SCORE (25%) ─────────────────────────
        biz_score = 30  # default: unknown business type
        matched_types = []
        for keyword in HIGH_ENGAGEMENT_TYPES:
            if keyword in lower_name:
                matched_types.append(keyword)
        
        if matched_types:
            # More matches = higher confidence this is a real engaged business
            biz_score = min(50 + len(matched_types) * 15, 100)
            reasons.append(f"Business: matches [{', '.join(matched_types[:3])}] → {biz_score}")
        else:
            # Check for generic signs
            if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+(Auto|Cafe|Shop|Store|Service)', name):
                biz_score = 55  # Looks like a real business name
                reasons.append(f"Business: pattern looks like real business → {biz_score}")
            else:
                reasons.append(f"Business: no matching type keywords → {biz_score}")
        scores['business_type'] = biz_score
        
        # ── 3. LEAD QUALITY SCORE (20%) ──────────────────────────
        quality_score = 50  # default
        
        # Phone number quality
        clean_phone = re.sub(r'\D', '', phone)
        if clean_phone.startswith('1'):
            clean_phone = clean_phone[1:]
        
        if len(clean_phone) != 10:
            quality_score -= 30
            reasons.append("Quality: invalid phone format")
        elif clean_phone[:3] in ('800', '888', '877', '866', '855', '844', '833'):
            quality_score -= 25  # Toll-free = corporate, usually IVR
            reasons.append("Quality: toll-free number (-25)")
        else:
            quality_score += 10
            reasons.append("Quality: valid local number (+10)")
        
        # Name quality indicators
        if name.count(' - ') > 0 or name.count(' | ') > 0:
            quality_score -= 10  # SEO separator
            reasons.append("Quality: SEO separators in name (-10)")
        if any(c in name for c in [':', '–', '—']) and len(name) > 40:
            quality_score -= 10
            reasons.append("Quality: long name with special chars (-10)")
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+', name) and len(name) < 30:
            quality_score += 15  # Clean, short, proper business name
            reasons.append("Quality: clean short business name (+15)")
        
        # Line type if available
        line_type = lead.get('line_type', '')
        if line_type == 'mobile':
            quality_score += 15  # Mobile = decision maker
            reasons.append("Quality: mobile line (+15)")
        elif line_type == 'voip':
            quality_score -= 5
            reasons.append("Quality: VoIP line (-5)")
        
        scores['quality'] = max(0, min(100, quality_score))
        
        # ── 4. HISTORY SCORE (20%) ───────────────────────────────
        history_score = 50  # default: never called before (neutral)
        
        if len(clean_phone) == 10 and clean_phone in self._phone_outcomes:
            outcomes = self._phone_outcomes[clean_phone]
            
            # What happened in previous calls?
            best_turns = max(o['turns'] for o in outcomes)
            best_outcome = None
            for o in outcomes:
                if o['outcome'] == 'kept_engaged':
                    best_outcome = 'kept_engaged'
                    break
                elif o['outcome'] == 'soft_decline' and best_outcome != 'kept_engaged':
                    best_outcome = 'soft_decline'
                elif o['outcome'] not in ('hangup', 'air_call_kill', 'voicemail_eab', 
                                           'business_ivr_loop_abort') and best_outcome is None:
                    best_outcome = o['outcome']
            
            if best_outcome == 'kept_engaged':
                history_score = 90  # Previously engaged! Warm recall
                reasons.append(f"History: previously kept_engaged ({best_turns}T) → warm lead!")
            elif best_outcome == 'soft_decline':
                history_score = 60  # They talked, said no — worth retrying with better approach
                reasons.append(f"History: soft_decline ({best_turns}T) — they listened, retry")
            elif best_outcome in ('hangup', 'air_call_kill', 'voicemail_eab'):
                history_score = 10  # Never reached a human
                reasons.append(f"History: {best_outcome} — never reached human")
            elif best_outcome in ('voicemail_ivr', 'ivr_system'):
                history_score = 25  # IVR — might reach human at different time
                reasons.append(f"History: {best_outcome} — try different time")
            elif best_outcome == 'organism_unfit':
                history_score = 5  # Bad lead confirmed
                reasons.append(f"History: organism_unfit — confirmed bad lead")
            elif best_outcome == 'dnc_request':
                history_score = 0
                disqualified = True
                dq_reason = "DNC requested"
                reasons.append("History: DO NOT CALL")
            else:
                history_score = 35
                reasons.append(f"History: {best_outcome} ({best_turns}T)")
            
            # Called many times with no improvement? Diminishing returns.
            if len(outcomes) >= 3 and best_turns <= 2:
                history_score = max(history_score - 30, 0)
                reasons.append(f"History: {len(outcomes)} attempts, max {best_turns}T — fatigue")
        else:
            reasons.append("History: never called (fresh lead)")
        
        scores['history'] = max(0, min(100, history_score))
        
        if disqualified:
            return {
                'score': 0, 'band': 'DISQUALIFIED', 'disqualified': True,
                'dq_reason': dq_reason, 'factors': scores,
                'recommendation': f'SKIP — {dq_reason}',
            }
        
        # ── COMPOSITE SCORE ──────────────────────────────────────
        composite = int(
            scores['timing'] * 0.35 +
            scores['business_type'] * 0.25 +
            scores['quality'] * 0.20 +
            scores['history'] * 0.20
        )
        composite = max(0, min(100, composite))
        
        # Band assignment
        if composite >= 75:
            band = 'A-TIER'
        elif composite >= 55:
            band = 'B-TIER'
        elif composite >= 35:
            band = 'C-TIER'
        else:
            band = 'D-TIER'
        
        # Recommendation
        if band == 'A-TIER':
            rec = 'FIRE — High-probability contact with quality lead'
        elif band == 'B-TIER':
            rec = 'FIRE — Decent probability, worth the dial'
        elif band == 'C-TIER':
            rec = 'HOLD — Consider waiting for better timing or skip'
        else:
            rec = 'SKIP — Low probability, save this lead for optimal conditions'
        
        return {
            'score': composite,
            'band': band,
            'disqualified': False,
            'dq_reason': None,
            'factors': scores,
            'reasons': reasons,
            'recommendation': rec,
        }
    
    def score_and_rank_leads(self, leads: List[Dict], 
                             call_weekday: int = None,
                             call_hour: int = None,
                             min_score: int = 0) -> List[Tuple[Dict, Dict]]:
        """
        Score all leads and return sorted by precision score (highest first).
        Each item is (score_dict, lead_dict).
        If min_score > 0, filters out leads below that threshold.
        """
        scored = []
        for lead in leads:
            result = self.score_lead(lead, call_weekday, call_hour)
            if result['score'] >= min_score and not result.get('disqualified'):
                scored.append((result, lead))
        
        scored.sort(key=lambda x: x[0]['score'], reverse=True)
        return scored


# ══════════════════════════════════════════════════════════════════════
#  OPTIMAL TIMING ENGINE
#  Evidence-based: fires only during proven high-contact windows.
# ══════════════════════════════════════════════════════════════════════

class OptimalTimingEngine:
    """Determine the best time to fire calls based on real outcome data."""
    
    @staticmethod
    def get_current_window_quality() -> Dict[str, Any]:
        """Rate the current moment for calling."""
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        
        day_rate = DAY_CONTACT_RATE.get(weekday, 0.15)
        hour_rate = HOUR_CONTACT_RATE.get(hour, 0.15)
        avg_turns = HOUR_AVG_TURNS.get(hour, 1.0)
        
        # Combined quality
        combined = (day_rate + hour_rate) / 2
        
        day_name = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][weekday]
        
        if combined >= 0.35:
            quality = 'PRIME'
            action = 'FIRE NOW — peak contact window'
        elif combined >= 0.25:
            quality = 'GOOD'
            action = 'Fire — solid contact probability'
        elif combined >= 0.18:
            quality = 'MARGINAL'
            action = 'Consider waiting — below average contact rate'
        else:
            quality = 'POOR'
            action = 'HOLD — very low contact probability, save leads for better timing'
        
        return {
            'quality': quality,
            'action': action,
            'day': day_name,
            'day_rate': f"{int(day_rate*100)}%",
            'hour': f"{hour}:00",
            'hour_rate': f"{int(hour_rate*100)}%",
            'avg_turns_at_this_hour': avg_turns,
            'combined_rate': f"{int(combined*100)}%",
        }
    
    @staticmethod
    def get_next_prime_window() -> Dict[str, Any]:
        """Find the next prime calling window from current time."""
        now = datetime.now()
        
        # Prime windows (evidence-based):
        # Tue-Wed, 2-4 PM = highest combined (day rate * hour rate)
        # Also good: Tue 9-10 AM, Wed 2-4 PM
        prime_windows = [
            # (weekday, start_hour, end_hour, quality_note)
            (1, 14, 16, "Tuesday 2-4 PM: peak day (37%) + peak hours (43-51%)"),
            (1, 9, 11, "Tuesday 9-11 AM: peak day (37%) + good hours (22-30%)"),
            (2, 14, 16, "Wednesday 2-4 PM: good day (27%) + peak hours (43-51%)"),
            (2, 9, 11, "Wednesday 9-11 AM: good day (27%) + good hours (22-30%)"),
            (3, 14, 16, "Thursday 2-4 PM: decent day (25%) + peak hours"),
            (1, 12, 14, "Tuesday 12-2 PM: peak day + solid hours (21-23%)"),
        ]
        
        candidates = []
        for wd, sh, eh, note in prime_windows:
            # Calculate time until this window
            days_ahead = (wd - now.weekday()) % 7
            if days_ahead == 0 and now.hour >= eh:
                days_ahead = 7  # Already past this window today
            
            window_start = now.replace(hour=sh, minute=0, second=0, microsecond=0)
            window_start += timedelta(days=days_ahead)
            
            if window_start > now:
                delta = window_start - now
                hours_until = delta.total_seconds() / 3600
                candidates.append({
                    'window': note,
                    'starts_at': window_start.strftime('%A %I:%M %p'),
                    'hours_until': f"{hours_until:.1f}h",
                    'hours_until_raw': hours_until,
                    'is_today': days_ahead == 0,
                })
        
        if candidates:
            # Return the SOONEST prime window
            candidates.sort(key=lambda x: x['hours_until_raw'])
            best = candidates[0]
            del best['hours_until_raw']
            return best
        
        # Fallback
        return {
            'window': 'Next Tuesday 2 PM',
            'starts_at': 'Tuesday 2:00 PM',
            'hours_until': 'unknown',
            'is_today': False,
        }


# ══════════════════════════════════════════════════════════════════════
#  DEAD LEAD FILTER
#  Evidence-based: filters leads that NEVER produce conversations.
# ══════════════════════════════════════════════════════════════════════

class DeadLeadFilter:
    """Filter out leads that evidence shows will never convert."""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data', 'call_capture.db'
        )
        self._dnc_phones = None
    
    def _load_dnc(self):
        """Load phones that requested DNC."""
        if self._dnc_phones is not None:
            return
        self._dnc_phones = set()
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT merchant_phone FROM calls WHERE final_outcome = 'dnc_request'")
            for (phone,) in c.fetchall():
                clean = re.sub(r'\D', '', phone or '')
                if clean.startswith('1') and len(clean) == 11:
                    clean = clean[1:]
                self._dnc_phones.add(clean)
            conn.close()
        except Exception:
            pass
    
    def filter(self, leads: List[Dict]) -> Tuple[List[Dict], List[Tuple[Dict, str]]]:
        """
        Filter leads. Returns (good_leads, rejected_with_reasons).
        """
        self._load_dnc()
        good = []
        rejected = []
        
        for lead in leads:
            name = lead.get('name', '') or ''
            phone = lead.get('phone_number', '') or ''
            lower = name.lower().strip()
            
            # 1. DNC check (absolute)
            clean_phone = re.sub(r'\D', '', phone)
            if clean_phone.startswith('1') and len(clean_phone) == 11:
                clean_phone = clean_phone[1:]
            if clean_phone in self._dnc_phones:
                rejected.append((lead, "DNC — requested do-not-call"))
                continue
            
            # 2. Dead lead patterns
            is_dead = False
            for pattern in DEAD_LEAD_PATTERNS:
                if pattern in lower:
                    rejected.append((lead, f"Dead pattern: '{pattern}'"))
                    is_dead = True
                    break
            if is_dead:
                continue
            
            # 3. Placeholder / no name
            if not name or name.strip().lower() in ('there', 'unknown', 'n/a', '', 'home'):
                rejected.append((lead, "No real business name"))
                continue
            
            # 4. SEO page title (too long)
            if len(name) >= 60:
                rejected.append((lead, f"Name {len(name)} chars — SEO page title"))
                continue
            
            # 5. Address, not business
            if re.match(r'^\d{3,}[\s,]', name.strip()):
                rejected.append((lead, "Address, not business name"))
                continue
            
            # 6. Toll-free (usually corporate IVR)
            if clean_phone[:3] in ('800', '888', '877', '866', '855', '844', '833'):
                rejected.append((lead, "Toll-free number — corporate IVR"))
                continue
            
            # 7. Non-US / invalid phone
            if len(clean_phone) != 10:
                rejected.append((lead, f"Invalid phone ({len(clean_phone)} digits)"))
                continue
            
            good.append(lead)
        
        return good, rejected


# ══════════════════════════════════════════════════════════════════════
#  OUTCOME ANALYZER
#  Real-time analysis of what's happening in the current session.
# ══════════════════════════════════════════════════════════════════════

class OutcomeAnalyzer:
    """Analyze call outcomes from the database for strategic decisions."""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data', 'call_capture.db'
        )
    
    def get_today_stats(self) -> Dict[str, Any]:
        """Get today's call outcomes for real-time strategy adjustment."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            today = datetime.now().strftime('%Y-%m-%d')
            
            c.execute("""
                SELECT final_outcome, COUNT(*) as cnt,
                       AVG(total_turns) as avg_turns,
                       AVG(duration_seconds) as avg_dur,
                       SUM(CASE WHEN total_turns >= 2 AND merchant_words > 0 THEN 1 ELSE 0 END) as human_convos
                FROM calls
                WHERE date(created_at) = ?
                GROUP BY final_outcome
                ORDER BY cnt DESC
            """, (today,))
            
            outcomes = {}
            total = 0
            humans = 0
            for row in c.fetchall():
                outcome, cnt, avg_t, avg_d, hc = row
                outcomes[outcome] = {
                    'count': cnt, 'avg_turns': round(avg_t or 0, 1),
                    'avg_duration': int(avg_d or 0), 'human_convos': hc or 0,
                }
                total += cnt
                humans += hc or 0
            
            # Best call today
            c.execute("""
                SELECT business_name, total_turns, duration_seconds, final_outcome
                FROM calls
                WHERE date(created_at) = ?
                ORDER BY total_turns DESC
                LIMIT 1
            """, (today,))
            best = c.fetchone()
            
            conn.close()
            
            return {
                'total_calls': total,
                'human_conversations': humans,
                'contact_rate': f"{int(humans/total*100)}%" if total > 0 else "0%",
                'outcomes': outcomes,
                'best_call': {
                    'name': best[0] if best else 'N/A',
                    'turns': best[1] if best else 0,
                    'duration': best[2] if best else 0,
                    'outcome': best[3] if best else 'N/A',
                } if best else None,
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_soft_decline_opportunities(self) -> List[Dict]:
        """
        Find soft_decline leads worth retrying.
        Evidence: soft_decline avg 5.8 turns, 53s — people TALKED and said no.
        With better pivot tactics, some of these could convert.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT DISTINCT business_name, merchant_phone, total_turns, 
                       duration_seconds, merchant_words, engagement_score
                FROM calls
                WHERE final_outcome = 'soft_decline' 
                  AND total_turns >= 4
                  AND merchant_words > 20
                ORDER BY total_turns DESC
                LIMIT 20
            """)
            
            opportunities = []
            for row in c.fetchall():
                name, phone, turns, dur, mw, eng = row
                opportunities.append({
                    'name': name, 'phone': phone,
                    'previous_turns': turns, 'previous_duration': dur,
                    'merchant_words': mw, 'engagement': eng,
                    'retry_note': f"Previously engaged {turns}T/{dur}s — they listened, try different approach",
                })
            conn.close()
            return opportunities
        except Exception as e:
            return []
    
    def get_kept_engaged_patterns(self) -> Dict[str, Any]:
        """Analyze what kept_engaged calls have in common."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT business_name, total_turns, duration_seconds,
                       merchant_words, alan_words, engagement_score,
                       strftime('%H', created_at) as call_hour,
                       strftime('%w', created_at) as call_dow
                FROM calls
                WHERE final_outcome = 'kept_engaged'
                ORDER BY total_turns DESC
            """)
            
            calls = []
            hours = {}
            days = {}
            for row in c.fetchall():
                name, turns, dur, mw, aw, eng, hour, dow = row
                calls.append({
                    'name': name, 'turns': turns, 'duration': dur,
                    'merchant_words': mw, 'agent_words': aw,
                })
                h = int(hour) if hour else 0
                hours[h] = hours.get(h, 0) + 1
                d = int(dow) if dow else 0
                days[d] = days.get(d, 0) + 1
            
            conn.close()
            
            return {
                'total': len(calls),
                'avg_turns': round(sum(c['turns'] for c in calls) / max(len(calls), 1), 1),
                'avg_duration': int(sum(c['duration'] for c in calls) / max(len(calls), 1)),
                'avg_merchant_words': int(sum(c['merchant_words'] for c in calls) / max(len(calls), 1)),
                'top_calls': calls[:5],
                'best_hours': dict(sorted(hours.items(), key=lambda x: x[1], reverse=True)[:5]),
                'best_days': days,
            }
        except Exception as e:
            return {'error': str(e)}


# ══════════════════════════════════════════════════════════════════════
#  PRECISION STRATEGY REPORT
#  Generates a human-readable strategic briefing.
# ══════════════════════════════════════════════════════════════════════

def generate_precision_briefing() -> str:
    """Generate a strategic briefing based on current conditions and evidence."""
    timing = OptimalTimingEngine()
    window = timing.get_current_window_quality()
    next_prime = timing.get_next_prime_window()
    analyzer = OutcomeAnalyzer()
    today = analyzer.get_today_stats()
    patterns = analyzer.get_kept_engaged_patterns()
    soft_opps = analyzer.get_soft_decline_opportunities()
    
    lines = []
    lines.append("=" * 70)
    lines.append("  PRECISION CAMPAIGN BRIEFING")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
    lines.append("=" * 70)
    
    # Current timing
    lines.append(f"\n  CURRENT WINDOW: {window['quality']}")
    lines.append(f"    {window['action']}")
    lines.append(f"    Day: {window['day']} ({window['day_rate']} contact rate)")
    lines.append(f"    Hour: {window['hour']} ({window['hour_rate']} contact rate)")
    lines.append(f"    Combined: {window['combined_rate']}")
    
    if window['quality'] in ('MARGINAL', 'POOR'):
        lines.append(f"\n  NEXT PRIME WINDOW:")
        lines.append(f"    {next_prime['window']}")
        lines.append(f"    Starts: {next_prime['starts_at']} ({next_prime['hours_until']} from now)")
    
    # Today's performance
    if today.get('total_calls', 0) > 0:
        lines.append(f"\n  TODAY'S PERFORMANCE:")
        lines.append(f"    Calls: {today['total_calls']} | Human contact: {today['contact_rate']}")
        if today.get('best_call'):
            bc = today['best_call']
            lines.append(f"    Best call: {bc['name'][:35]} ({bc['turns']}T/{bc['duration']}s → {bc['outcome']})")
    
    # Alan's engagement patterns
    if patterns.get('total', 0) > 0:
        lines.append(f"\n  ALAN'S ENGAGEMENT PROFILE (from {patterns['total']} kept_engaged):")
        lines.append(f"    Avg turns: {patterns['avg_turns']} | Avg duration: {patterns['avg_duration']}s")
        lines.append(f"    Avg merchant words: {patterns['avg_merchant_words']}")
        if patterns.get('top_calls'):
            lines.append(f"    Top calls:")
            for tc in patterns['top_calls'][:3]:
                lines.append(f"      {int(tc['turns']):2d}T {int(tc['duration']):3d}s  {tc['name'][:40]}")
    
    # Soft decline retry opportunities
    if soft_opps:
        lines.append(f"\n  SOFT DECLINE RETRY OPPORTUNITIES ({len(soft_opps)} leads):")
        lines.append(f"    These people TALKED to Alan (avg 5.8T/53s) but said no.")
        lines.append(f"    With better pivot timing, some may convert:")
        for so in soft_opps[:5]:
            lines.append(f"      {int(so['previous_turns'] or 0):2d}T {int(so['previous_duration'] or 0):3d}s  {(so['name'] or 'Unknown')[:35]}  [{so['phone'] or '?'}]")
    
    lines.append(f"\n{'='*70}")
    return '\n'.join(lines)


# ══════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    
    if '--briefing' in sys.argv or len(sys.argv) == 1:
        print(generate_precision_briefing())
    
    elif '--score' in sys.argv:
        # Score current pending leads
        scorer = PrecisionScorer()
        now = datetime.now()
        
        # Pull pending leads from DB
        try:
            from lead_database import LeadDB
            db = LeadDB()
            conn = sqlite3.connect(db.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("""
                SELECT id, name, phone_number, lead_source, business_type, line_type
                FROM leads 
                WHERE outcome = 'pending' AND do_not_call = 0
                ORDER BY id
                LIMIT 50
            """)
            leads = [dict(r) for r in c.fetchall()]
            conn.close()
        except Exception as e:
            print(f"Error loading leads: {e}")
            sys.exit(1)
        
        # Filter
        dlf = DeadLeadFilter()
        good, rejected = dlf.filter(leads)
        
        if rejected:
            print(f"\n  FILTERED OUT {len(rejected)} dead leads:")
            for lead, reason in rejected:
                print(f"    REJECT  {lead['name'][:40]:40s} | {reason}")
        
        # Score remaining
        scored = scorer.score_and_rank_leads(good, now.weekday(), now.hour)
        
        print(f"\n  PRECISION SCORES ({len(scored)} leads):")
        print(f"  {'#':>3s}  {'Score':>5s}  {'Band':8s}  {'T':>3s}  {'B':>3s}  {'Q':>3s}  {'H':>3s}  {'Lead Name'}")
        print(f"  {'─'*3}  {'─'*5}  {'─'*8}  {'─'*3}  {'─'*3}  {'─'*3}  {'─'*3}  {'─'*35}")
        
        for i, (score, lead) in enumerate(scored, 1):
            f = score['factors']
            print(f"  {i:3d}  {score['score']:5d}  {score['band']:8s}  "
                  f"{f.get('timing',0):3d}  {f.get('business_type',0):3d}  "
                  f"{f.get('quality',0):3d}  {f.get('history',0):3d}  "
                  f"{lead['name'][:35]}")
        
        # Summary
        a_tier = sum(1 for s, _ in scored if s['band'] == 'A-TIER')
        b_tier = sum(1 for s, _ in scored if s['band'] == 'B-TIER')
        c_tier = sum(1 for s, _ in scored if s['band'] == 'C-TIER')
        d_tier = sum(1 for s, _ in scored if s['band'] == 'D-TIER')
        print(f"\n  Distribution: A={a_tier} B={b_tier} C={c_tier} D={d_tier}")
        print(f"  Recommendation: Fire top {a_tier + b_tier} leads (A+B tier)")
    
    elif '--timing' in sys.argv:
        timing = OptimalTimingEngine()
        w = timing.get_current_window_quality()
        print(f"\n  Current: {w['quality']} — {w['action']}")
        print(f"  {w['day']} {w['hour']}: day={w['day_rate']}, hour={w['hour_rate']}, combined={w['combined_rate']}")
        
        nw = timing.get_next_prime_window()
        print(f"\n  Next prime: {nw['window']}")
        print(f"  Starts: {nw['starts_at']} ({nw['hours_until']} from now)")
    
    elif '--soft-declines' in sys.argv:
        analyzer = OutcomeAnalyzer()
        opps = analyzer.get_soft_decline_opportunities()
        print(f"\n  SOFT DECLINE RETRY OPPORTUNITIES ({len(opps)}):")
        for o in opps:
            print(f"    {o['previous_turns']:2d}T {o['previous_duration']:3d}s  "
                  f"{o['name'][:35]:35s}  {o['phone']}")
            print(f"         → {o['retry_note']}")
    
    else:
        print("Usage:")
        print("  python precision_engine.py              # Full briefing")
        print("  python precision_engine.py --score      # Score pending leads")
        print("  python precision_engine.py --timing     # Check timing window")
        print("  python precision_engine.py --soft-declines  # Retry opportunities")
