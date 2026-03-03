"""
Contact Rate Optimizer
======================
Intelligence layer that maximizes the probability of reaching a human on
every outbound call. Implements the five pillars of contact rate optimization:

  1. CALLER ID / LOCAL PRESENCE — match outbound number to destination area code
  2. NUMBER REPUTATION — track per-number call volume, flag/retire degraded numbers
  3. CALL TIMING — day-of-week quality + optimal time windows in merchant's local TZ
  4. DATA QUALITY — score leads by source freshness, line type, and phone reliability
  5. MULTI-TOUCH SEQUENCING — automated attempt cadence (call/text/voicemail)

This module is the BRAIN behind Alan's calling infrastructure.
The hard part (Alan's conversational ability) is already solved.
Contact rate is an infrastructure problem — and this module solves it.

Wired into: _fire_campaign.py, control_api_fixed.py, lead_database.py

Design Philosophy:
  "Same Alan. Same script. Completely different results." — The difference
  between a 10% contact rate and a 45% contact rate is entirely infrastructure.

Created: Feb 25, 2026
"""

import os
import re
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("CRO")

# ══════════════════════════════════════════════════════════════════════
#  PILLAR 1: CALL TIMING — Day-of-Week + Time-of-Day Optimization
# ══════════════════════════════════════════════════════════════════════

# Day quality scores (0-100, higher = better contact rate)
DAY_QUALITY = {
    0: ("Monday",    35, "Owners catching up from weekend"),
    1: ("Tuesday",   95, "Best overall day"),
    2: ("Wednesday", 90, "Second best"),
    3: ("Thursday",  80, "Decisions get made Thursday"),
    4: ("Friday",    40, "Mentally checked out by afternoon"),
    5: ("Saturday",  25, "Retail good, professional services bad"),
    6: ("Sunday",    10, "Almost nobody answers"),
}

# Time window quality (hour → quality score)
# All times are LOCAL to the merchant being called
TIME_QUALITY = {
    8:  20,   # Just opening
    9:  60,   # Warming up — good after 9:30
    10: 95,   # PEAK morning window
    11: 90,   # Still strong morning
    12: 30,   # Lunch — avoid
    13: 65,   # Post-lunch warmup — good after 1:30
    14: 100,  # PEAK — highest contact rate hour (1:30-3:30)
    15: 85,   # Still strong afternoon
    16: 60,   # Wrapping up
    17: 20,   # After hours for most
}

# Optimal calling windows (merchant local time)
PRIME_WINDOWS = [
    (9, 30, 11, 30, "Morning prime window"),
    (13, 30, 15, 30, "Afternoon prime window — peak decision-making"),
]

def get_day_quality(weekday: int) -> Tuple[str, int, str]:
    """Get day quality for a given weekday (0=Monday, 6=Sunday).
    Returns (day_name, quality_score, notes)."""
    return DAY_QUALITY.get(weekday, ("Unknown", 50, ""))

def get_time_quality(hour: int) -> int:
    """Get contact rate quality for a given hour (merchant local time).
    Returns 0-100 quality score."""
    return TIME_QUALITY.get(hour, 10)

def is_prime_window(local_hour: int, local_minute: int) -> Tuple[bool, str]:
    """Check if current merchant local time is in a prime calling window.
    Returns (is_prime, window_description)."""
    for start_h, start_m, end_h, end_m, desc in PRIME_WINDOWS:
        current_mins = local_hour * 60 + local_minute
        start_mins = start_h * 60 + start_m
        end_mins = end_h * 60 + end_m
        if start_mins <= current_mins < end_mins:
            return True, desc
    return False, ""

def get_call_timing_score(weekday: int, hour: int, minute: int = 0) -> Dict[str, Any]:
    """Compute composite timing score for a call.
    Returns dict with day_quality, time_quality, is_prime, composite_score."""
    day_name, day_score, day_note = get_day_quality(weekday)
    time_score = get_time_quality(hour)
    is_prime, prime_desc = is_prime_window(hour, minute)
    
    # Composite: 40% day + 50% time + 10% prime bonus
    prime_bonus = 10 if is_prime else 0
    composite = int(day_score * 0.4 + time_score * 0.5 + prime_bonus)
    
    return {
        "day": day_name,
        "day_score": day_score,
        "day_note": day_note,
        "time_score": time_score,
        "is_prime": is_prime,
        "prime_window": prime_desc,
        "composite": composite,
        "recommendation": _timing_recommendation(composite),
    }

def _timing_recommendation(score: int) -> str:
    if score >= 80:
        return "FIRE — optimal calling time"
    elif score >= 60:
        return "GOOD — reasonable contact rate expected"
    elif score >= 40:
        return "FAIR — consider waiting for prime window"
    else:
        return "HOLD — poor timing, queue for better window"


# ══════════════════════════════════════════════════════════════════════
#  PILLAR 2: LOCAL PRESENCE DIALING
# ══════════════════════════════════════════════════════════════════════

class LocalPresenceManager:
    """
    Manages a pool of phone numbers for local presence dialing.
    
    When Alan calls a merchant, the caller ID should display a local
    area code matching the merchant's area code. A restaurant in Miami
    should see a 305 or 786 number. This single change can DOUBLE
    contact rates overnight.
    
    Number pool is configured via data/number_pool.json:
    {
      "numbers": [
        {"number": "+13055551234", "area_code": "305", "region": "Miami",
         "calls_today": 0, "total_calls": 0, "flagged": false, "active": true},
        ...
      ],
      "config": {
        "max_calls_per_number_per_day": 80,
        "retire_after_total_calls": 600,
        "rotation_strategy": "area_code_match_first"
      }
    }
    """
    
    POOL_FILE = os.path.join(os.path.dirname(__file__), "data", "number_pool.json")
    
    # Area code geographic groupings — numbers in the same group provide
    # "close enough" local presence when exact match isn't available
    AREA_CODE_GROUPS = {
        # Miami / South Florida
        "miami": {"305", "786", "954", "561"},
        # Los Angeles Metro
        "la": {"213", "310", "323", "424", "562", "626", "657", "714", "747", "818"},
        # New York City
        "nyc": {"212", "347", "646", "718", "917", "929"},
        # Chicago
        "chicago": {"312", "331", "630", "708", "773", "779", "815", "847", "872"},
        # Dallas-Fort Worth
        "dfw": {"214", "469", "682", "817", "972", "940"},
        # Houston
        "houston": {"281", "346", "713", "832"},
        # Phoenix
        "phoenix": {"480", "602", "623"},
        # San Francisco Bay
        "sfbay": {"408", "415", "510", "628", "650", "669", "925"},
        # Atlanta
        "atlanta": {"404", "470", "678", "770"},
        # Denver / Colorado
        "denver": {"303", "719", "720"},
        # Seattle
        "seattle": {"206", "253", "425"},
        # Boston
        "boston": {"339", "508", "617", "774", "781", "857"},
        # DC Metro
        "dc": {"202", "240", "301", "571", "703"},
        # Tampa / Orlando
        "tampa_orlando": {"321", "407", "727", "813", "941"},
        # Philadelphia
        "philly": {"215", "267", "484", "610"},
        # San Diego
        "sandiego": {"619", "858"},
        # Austin
        "austin": {"512", "737"},
        # San Antonio
        "sanantonio": {"210",},
        # Detroit
        "detroit": {"248", "313", "586"},
        # Minneapolis
        "minneapolis": {"612", "651", "763", "952"},
        # Portland
        "portland": {"503", "971"},
        # Las Vegas
        "vegas": {"702", "725"},
        # St Louis
        "stlouis": {"314", "636"},
    }
    
    # Reverse lookup: area_code → group_name
    _AC_TO_GROUP = {}
    for group, codes in AREA_CODE_GROUPS.items():
        for code in codes:
            _AC_TO_GROUP[code] = group
    
    def __init__(self):
        self.pool = self._load_pool()
        self.config = self.pool.get("config", {})
        self.max_daily = self.config.get("max_calls_per_number_per_day", 80)
        self.retire_after = self.config.get("retire_after_total_calls", 600)
    
    def _load_pool(self) -> dict:
        """Load number pool from JSON. Returns empty if not configured."""
        if not os.path.exists(self.POOL_FILE):
            return {"numbers": [], "config": {}}
        try:
            with open(self.POOL_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[CRO] Failed to load number pool: {e}")
            return {"numbers": [], "config": {}}
    
    def _save_pool(self):
        """Persist number pool state."""
        os.makedirs(os.path.dirname(self.POOL_FILE), exist_ok=True)
        with open(self.POOL_FILE, "w") as f:
            json.dump(self.pool, f, indent=2)
    
    def get_best_caller_id(self, destination_number: str) -> Optional[str]:
        """
        Select the best caller ID for a given destination number.
        
        Priority:
        1. Exact area code match with lowest daily call count
        2. Same metro group match (e.g., 305 calling 786 — both Miami)
        3. Same state / closest geographic match
        4. Fallback to default TWILIO_PHONE_NUMBER
        
        Returns E.164 phone number or None (use default).
        """
        numbers = self.pool.get("numbers", [])
        if not numbers:
            return None  # No pool configured — use default
        
        dest_ac = self._extract_area_code(destination_number)
        if not dest_ac:
            return None
        
        dest_group = self._AC_TO_GROUP.get(dest_ac)
        
        # Filter to active, non-flagged, under daily limit, under retirement
        eligible = [
            n for n in numbers
            if n.get("active", True)
            and not n.get("flagged", False)
            and n.get("calls_today", 0) < self.max_daily
            and n.get("total_calls", 0) < self.retire_after
        ]
        
        if not eligible:
            logger.warning("[CRO] No eligible numbers in pool — all at limit or flagged")
            return None
        
        # Priority 1: Exact area code match
        exact = [n for n in eligible if n.get("area_code") == dest_ac]
        if exact:
            best = min(exact, key=lambda n: n.get("calls_today", 0))
            logger.info(f"[CRO] Local presence: exact match {best['area_code']} for dest {dest_ac}")
            return best["number"]
        
        # Priority 2: Same metro group
        if dest_group:
            group_codes = self.AREA_CODE_GROUPS.get(dest_group, set())
            group_match = [n for n in eligible if n.get("area_code") in group_codes]
            if group_match:
                best = min(group_match, key=lambda n: n.get("calls_today", 0))
                logger.info(f"[CRO] Local presence: group match {best['area_code']} ({dest_group}) for dest {dest_ac}")
                return best["number"]
        
        # Priority 3: Lowest usage number (any area code)
        best = min(eligible, key=lambda n: n.get("calls_today", 0))
        logger.info(f"[CRO] Local presence: no local match, using lowest-usage {best['area_code']} for dest {dest_ac}")
        return best["number"]
    
    def record_call(self, from_number: str):
        """Record that a call was made from this number (increment counters)."""
        for n in self.pool.get("numbers", []):
            if n["number"] == from_number:
                n["calls_today"] = n.get("calls_today", 0) + 1
                n["total_calls"] = n.get("total_calls", 0) + 1
                n["last_used"] = datetime.now().isoformat()
                self._save_pool()
                return
    
    def reset_daily_counts(self):
        """Reset daily call counts (run at midnight or start of day)."""
        for n in self.pool.get("numbers", []):
            n["calls_today"] = 0
        self._save_pool()
        logger.info(f"[CRO] Daily call counts reset for {len(self.pool.get('numbers', []))} numbers")
    
    def check_health(self) -> Dict[str, Any]:
        """Return pool health summary."""
        numbers = self.pool.get("numbers", [])
        if not numbers:
            return {
                "configured": False,
                "message": "No number pool configured — using single TWILIO_PHONE_NUMBER",
                "recommendation": "Configure data/number_pool.json with 50+ clean numbers for local presence dialing"
            }
        
        active = [n for n in numbers if n.get("active", True) and not n.get("flagged", False)]
        flagged = [n for n in numbers if n.get("flagged", False)]
        near_retirement = [n for n in numbers if n.get("total_calls", 0) > self.retire_after * 0.8]
        area_codes = set(n.get("area_code") for n in active)
        
        return {
            "configured": True,
            "total_numbers": len(numbers),
            "active": len(active),
            "flagged": len(flagged),
            "near_retirement": len(near_retirement),
            "area_codes_covered": len(area_codes),
            "area_codes": sorted(area_codes),
        }
    
    @staticmethod
    def _extract_area_code(phone: str) -> Optional[str]:
        clean = re.sub(r'\D', '', phone or '')
        if clean.startswith('1') and len(clean) == 11:
            return clean[1:4]
        elif len(clean) == 10:
            return clean[:3]
        return None


# ══════════════════════════════════════════════════════════════════════
#  PILLAR 3: NUMBER REPUTATION TRACKING
# ══════════════════════════════════════════════════════════════════════

class NumberReputationTracker:
    """
    Tracks per-number call volume and reputation signals.
    
    Key rules:
    - Never exceed 80 calls per number per day (carrier flagging threshold)
    - Retire numbers after 500-700 total calls regardless of flagging
    - If contact rate drops below 10% for a number → flag for review
    - Monitor for spam flagging indicators (very low answer rates)
    
    Reputation portals (manual registration recommended):
    - Free Caller Registry (freecallerregistry.com)
    - Hiya (hiya.com/for-businesses)
    - TNS (tnsi.com/products/robocall-protection)
    - First Orion (firstorion.com)
    """
    
    REPUTATION_DB = os.path.join(os.path.dirname(__file__), "data", "number_reputation.db")
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        os.makedirs(os.path.dirname(self.REPUTATION_DB), exist_ok=True)
        with sqlite3.connect(self.REPUTATION_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS number_stats (
                    phone_number TEXT PRIMARY KEY,
                    calls_today INTEGER DEFAULT 0,
                    calls_total INTEGER DEFAULT 0,
                    connects_total INTEGER DEFAULT 0,
                    last_used TEXT,
                    last_reset_date TEXT,
                    flagged INTEGER DEFAULT 0,
                    flag_reason TEXT,
                    registered_portals TEXT DEFAULT '[]',
                    stir_shaken_grade TEXT DEFAULT 'unknown',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    phone_number TEXT,
                    date TEXT,
                    calls INTEGER DEFAULT 0,
                    connects INTEGER DEFAULT 0,
                    connect_rate REAL DEFAULT 0.0,
                    PRIMARY KEY (phone_number, date)
                )
            """)
    
    def record_call(self, from_number: str, connected: bool = False):
        """Record a call attempt from a number."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        with sqlite3.connect(self.REPUTATION_DB) as conn:
            # Upsert number_stats
            conn.execute("""
                INSERT INTO number_stats (phone_number, calls_today, calls_total, connects_total,
                    last_used, last_reset_date, created_at, updated_at)
                VALUES (?, 1, 1, ?, ?, ?, ?, ?)
                ON CONFLICT(phone_number) DO UPDATE SET
                    calls_today = CASE
                        WHEN last_reset_date != ? THEN 1
                        ELSE calls_today + 1
                    END,
                    calls_total = calls_total + 1,
                    connects_total = connects_total + ?,
                    last_used = ?,
                    last_reset_date = ?,
                    updated_at = ?
            """, (
                from_number, 1 if connected else 0,
                now.isoformat(), today, now.isoformat(), now.isoformat(),
                today, 1 if connected else 0,
                now.isoformat(), today, now.isoformat()
            ))
            
            # Upsert daily_stats
            conn.execute("""
                INSERT INTO daily_stats (phone_number, date, calls, connects)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(phone_number, date) DO UPDATE SET
                    calls = calls + 1,
                    connects = connects + ?,
                    connect_rate = CAST(connects + ? AS REAL) / (calls + 1)
            """, (from_number, today, 1 if connected else 0, 1 if connected else 0, 1 if connected else 0))
    
    def should_retire(self, from_number: str, max_total: int = 600) -> Tuple[bool, str]:
        """Check if a number should be retired."""
        with sqlite3.connect(self.REPUTATION_DB) as conn:
            row = conn.execute(
                "SELECT calls_total, connects_total, calls_today, flagged FROM number_stats WHERE phone_number = ?",
                (from_number,)
            ).fetchone()
            
            if not row:
                return False, "no_data"
            
            calls_total, connects_total, calls_today, flagged = row
            
            if flagged:
                return True, "flagged_for_spam"
            if calls_total >= max_total:
                return True, f"total_calls_{calls_total}_exceeds_{max_total}"
            if calls_today >= 80:
                return True, f"daily_limit_{calls_today}_calls_today"
            if calls_total >= 50 and connects_total / max(calls_total, 1) < 0.05:
                return True, f"contact_rate_below_5pct_{connects_total}/{calls_total}"
            
            return False, "healthy"
    
    def get_daily_report(self) -> List[Dict]:
        """Get today's per-number stats."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.REPUTATION_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM daily_stats WHERE date = ? ORDER BY calls DESC",
                (today,)
            ).fetchall()
            return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════
#  PILLAR 4: MULTI-TOUCH SEQUENCER
# ══════════════════════════════════════════════════════════════════════

class MultiTouchSequencer:
    """
    Manages the multi-touch follow-up sequence for each lead.
    
    Research shows contacts happen most on attempts 3-5.
    Most systems give up after attempt 1-2. Alan never gives up prematurely.
    
    Standard Sequence:
    ┌─────────┬──────────────────────┬──────────┐
    │ Attempt │ Method               │ Timing   │
    ├─────────┼──────────────────────┼──────────┤
    │ 1       │ Call — morning       │ Day 1    │
    │ 2       │ Text if no answer    │ Day 1+1h │
    │ 3       │ Call — afternoon     │ Day 1 PM │
    │ 4       │ Call                 │ Day 3    │
    │ 5       │ Voicemail + text     │ Day 5    │
    │ 6       │ Final call           │ Day 10   │
    │ 7       │ Retire or recycle    │ Day 30   │
    └─────────┴──────────────────────┴──────────┘
    """
    
    SEQUENCE_DB = os.path.join(os.path.dirname(__file__), "data", "multi_touch.db")
    
    # The sequence definition
    SEQUENCE = [
        {"attempt": 1, "method": "call",          "delay_hours": 0,       "window": "morning",   "note": "Initial outreach — morning prime window"},
        {"attempt": 2, "method": "text",           "delay_hours": 1,       "window": "any",       "note": "Text follow-up if no answer on attempt 1"},
        {"attempt": 3, "method": "call",           "delay_hours": 4,       "window": "afternoon", "note": "Same day — different time window"},
        {"attempt": 4, "method": "call",           "delay_hours": 48,      "window": "morning",   "note": "Day 3 — fresh approach"},
        {"attempt": 5, "method": "voicemail_text", "delay_hours": 96,      "window": "afternoon", "note": "Day 5 — voicemail + immediate text"},
        {"attempt": 6, "method": "call",           "delay_hours": 216,     "window": "morning",   "note": "Day 10 — final attempt"},
        {"attempt": 7, "method": "retire",         "delay_hours": 720,     "window": "any",       "note": "Day 30 — retire or recycle to new campaign"},
    ]
    
    # Text templates for automated follow-up
    TEXT_TEMPLATES = {
        "after_no_answer": (
            "Hi {name} — just tried to reach you about your card processing. "
            "Quick question: do you know what your effective processing rate is right now? "
            "Worth a 10 minute conversation. — Alan, Signature Card {phone}"
        ),
        "after_voicemail": (
            "Hi {name} — just left you a voicemail. Quick question: do you know "
            "what your effective processing rate is right now? Worth a 10 minute "
            "conversation. — Alan {phone}"
        ),
        "day3_followup": (
            "Hey {name}, it's Alan from Signature Card. Tried reaching you earlier "
            "this week. Most business owners I review save $200-500/mo on processing. "
            "Worth a quick chat? Text me back when you get a sec."
        ),
    }
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        os.makedirs(os.path.dirname(self.SEQUENCE_DB), exist_ok=True)
        with sqlite3.connect(self.SEQUENCE_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS touch_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER,
                    phone_number TEXT,
                    lead_name TEXT,
                    attempt_number INTEGER DEFAULT 1,
                    method TEXT,
                    outcome TEXT,
                    call_sid TEXT,
                    next_action TEXT,
                    next_action_time TEXT,
                    created_at TEXT,
                    notes TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sequence_state (
                    phone_number TEXT PRIMARY KEY,
                    lead_id INTEGER,
                    lead_name TEXT,
                    current_attempt INTEGER DEFAULT 0,
                    last_method TEXT,
                    last_outcome TEXT,
                    next_method TEXT,
                    next_time TEXT,
                    sequence_status TEXT DEFAULT 'active',
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_touch_phone ON touch_log(phone_number)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seq_status ON sequence_state(sequence_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_seq_next ON sequence_state(next_time)")
    
    def record_touch(self, lead_id: int, phone: str, name: str,
                     method: str, outcome: str, call_sid: str = "") -> Dict:
        """
        Record a touch attempt and compute the next action.
        
        Outcomes that STOP the sequence:
        - "connected" — human answered, conversation happened
        - "appointment" — appointment set
        - "dnc" — do not call requested
        - "wrong_number" — not a valid lead
        
        Outcomes that CONTINUE the sequence:
        - "no_answer" — no pickup
        - "voicemail" — went to voicemail
        - "busy" — line busy
        - "ivr" — hit IVR/phone tree
        - "screened" — call screened/blocked
        """
        now = datetime.now()
        
        with sqlite3.connect(self.SEQUENCE_DB) as conn:
            # Get current state
            state = conn.execute(
                "SELECT current_attempt, sequence_status FROM sequence_state WHERE phone_number = ?",
                (phone,)
            ).fetchone()
            
            current_attempt = (state[0] if state else 0) + 1
            
            # Check if outcome stops the sequence
            terminal_outcomes = {"connected", "appointment", "dnc", "wrong_number", "exhausted"}
            is_terminal = outcome in terminal_outcomes
            
            # Determine next action
            if is_terminal:
                next_method = "none"
                next_time = None
                seq_status = f"completed_{outcome}"
            elif current_attempt >= len(self.SEQUENCE):
                next_method = "retire"
                next_time = None
                seq_status = "exhausted"
            else:
                next_step = self.SEQUENCE[current_attempt]  # Next step (0-indexed from current)
                next_method = next_step["method"]
                delay = timedelta(hours=next_step["delay_hours"])
                next_time = (now + delay).isoformat()
                seq_status = "active"
            
            # Log the touch
            conn.execute("""
                INSERT INTO touch_log (lead_id, phone_number, lead_name, attempt_number,
                    method, outcome, call_sid, next_action, next_action_time, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (lead_id, phone, name, current_attempt, method, outcome,
                  call_sid, next_method, next_time, now.isoformat(),
                  f"Attempt {current_attempt}/{len(self.SEQUENCE)}"))
            
            # Update state
            conn.execute("""
                INSERT INTO sequence_state (phone_number, lead_id, lead_name, current_attempt,
                    last_method, last_outcome, next_method, next_time, sequence_status,
                    created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(phone_number) DO UPDATE SET
                    current_attempt = ?,
                    last_method = ?,
                    last_outcome = ?,
                    next_method = ?,
                    next_time = ?,
                    sequence_status = ?,
                    updated_at = ?
            """, (phone, lead_id, name, current_attempt, method, outcome,
                  next_method, next_time, seq_status, now.isoformat(), now.isoformat(),
                  current_attempt, method, outcome, next_method, next_time,
                  seq_status, now.isoformat()))
        
        return {
            "attempt": current_attempt,
            "outcome": outcome,
            "next_method": next_method,
            "next_time": next_time,
            "sequence_status": seq_status,
        }
    
    def get_due_actions(self, method_filter: Optional[str] = None) -> List[Dict]:
        """Get all leads with due follow-up actions.
        Optionally filter by method (call, text, voicemail_text)."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.SEQUENCE_DB) as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT * FROM sequence_state
                WHERE sequence_status = 'active'
                  AND next_time IS NOT NULL
                  AND next_time <= ?
            """
            params = [now]
            if method_filter:
                query += " AND next_method = ?"
                params.append(method_filter)
            query += " ORDER BY next_time ASC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
    
    def get_sequence_summary(self) -> Dict[str, Any]:
        """Summary of all sequences."""
        with sqlite3.connect(self.SEQUENCE_DB) as conn:
            total = conn.execute("SELECT COUNT(*) FROM sequence_state").fetchone()[0]
            active = conn.execute(
                "SELECT COUNT(*) FROM sequence_state WHERE sequence_status = 'active'"
            ).fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM sequence_state WHERE sequence_status LIKE 'completed_%'"
            ).fetchone()[0]
            exhausted = conn.execute(
                "SELECT COUNT(*) FROM sequence_state WHERE sequence_status = 'exhausted'"
            ).fetchone()[0]
            due_now = conn.execute(
                "SELECT COUNT(*) FROM sequence_state WHERE sequence_status = 'active' AND next_time <= ?",
                (datetime.now().isoformat(),)
            ).fetchone()[0]
            
            return {
                "total_sequences": total,
                "active": active,
                "completed": completed,
                "exhausted": exhausted,
                "due_now": due_now,
            }


# ══════════════════════════════════════════════════════════════════════
#  PILLAR 5: DATA QUALITY SCORING
# ══════════════════════════════════════════════════════════════════════

# Lead source quality multipliers (higher = better expected contact rate)
SOURCE_QUALITY = {
    "referral":              0.95,   # 60-75% contact rate — warm introduction
    "linkedin_verified":     0.80,   # 40-50% — decision maker confirmed
    "new_business_filing":   0.75,   # 40-55% — owner just filed, highly reachable
    "intent_verified_mobile": 0.70,  # 35-50% — verified mobile reaches DMs directly
    "google_my_business":    0.60,   # 30-40% — often owner's direct number
    "web_enriched":          0.50,   # 25-35% — enriched but not verified
    "yelp":                  0.45,   # 25-35% — public listing
    "directory":             0.30,   # 15-25% — general directory listing
    "scraped_landline":      0.15,   # 8-15% — worst performing, avoid
    "unknown":               0.35,   # Default
}

def score_data_quality(lead: Dict) -> Dict[str, Any]:
    """Score a lead's data quality for contact rate prediction.
    Returns quality metrics and recommendations."""
    source = lead.get("lead_source", "unknown").lower().replace(" ", "_")
    line_type = lead.get("line_type", "unknown").lower()
    phone = lead.get("phone_number", "")
    
    # Source quality
    source_score = SOURCE_QUALITY.get(source, SOURCE_QUALITY["unknown"])
    
    # Line type bonus/penalty
    line_multiplier = 1.0
    if "mobile" in line_type or "cell" in line_type:
        line_multiplier = 1.3  # Mobile numbers reach DMs directly
    elif "voip" in line_type:
        line_multiplier = 0.7  # VOIP often has call screening
    elif "landline" in line_type:
        line_multiplier = 0.8  # Landline often hits gatekeeper
    
    # Phone format check
    clean_phone = re.sub(r'\D', '', phone)
    has_valid_phone = len(clean_phone) == 10 or (len(clean_phone) == 11 and clean_phone[0] == '1')
    
    # Toll-free check (toll-free outbound is a red flag for data, not for our outbound)
    area_code = clean_phone[1:4] if len(clean_phone) == 11 else clean_phone[:3] if len(clean_phone) == 10 else ""
    is_toll_free = area_code in {"800", "833", "844", "855", "866", "877", "888"}
    
    composite = source_score * line_multiplier * (0.3 if is_toll_free else 1.0)
    
    return {
        "source": source,
        "source_score": source_score,
        "line_type": line_type,
        "line_multiplier": line_multiplier,
        "has_valid_phone": has_valid_phone,
        "is_toll_free": is_toll_free,
        "composite_quality": round(composite, 3),
        "expected_contact_rate": f"{int(composite * 100)}%",
    }


# ══════════════════════════════════════════════════════════════════════
#  CONTACT RATE ANALYTICS
# ══════════════════════════════════════════════════════════════════════

class ContactRateAnalytics:
    """
    Tracks and analyzes contact rates across multiple dimensions:
    - By area code
    - By time of day
    - By day of week
    - By vertical/business type
    - By data source
    
    Alan feeds this data back to optimize targeting in real time.
    """
    
    ANALYTICS_DB = os.path.join(os.path.dirname(__file__), "data", "contact_analytics.db")
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        os.makedirs(os.path.dirname(self.ANALYTICS_DB), exist_ok=True)
        with sqlite3.connect(self.ANALYTICS_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS call_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT,
                    area_code TEXT,
                    timezone TEXT,
                    local_hour INTEGER,
                    day_of_week INTEGER,
                    business_type TEXT,
                    lead_source TEXT,
                    connected INTEGER DEFAULT 0,
                    human_contact INTEGER DEFAULT 0,
                    duration_seconds INTEGER DEFAULT 0,
                    outcome TEXT,
                    call_sid TEXT,
                    from_number TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ce_ac ON call_events(area_code)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ce_hour ON call_events(local_hour)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ce_dow ON call_events(day_of_week)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ce_btype ON call_events(business_type)")
    
    def record_call_event(self, phone: str, area_code: str, timezone: str,
                          local_hour: int, business_type: str, lead_source: str,
                          connected: bool, human_contact: bool,
                          duration: int = 0, outcome: str = "",
                          call_sid: str = "", from_number: str = ""):
        """Record a call event for analytics."""
        now = datetime.now()
        with sqlite3.connect(self.ANALYTICS_DB) as conn:
            conn.execute("""
                INSERT INTO call_events (phone_number, area_code, timezone, local_hour,
                    day_of_week, business_type, lead_source, connected, human_contact,
                    duration_seconds, outcome, call_sid, from_number, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (phone, area_code, timezone, local_hour, now.weekday(),
                  business_type, lead_source, 1 if connected else 0,
                  1 if human_contact else 0, duration, outcome,
                  call_sid, from_number, now.isoformat()))
    
    def get_contact_rate_by(self, dimension: str, min_calls: int = 10) -> List[Dict]:
        """Get contact rate breakdown by a dimension.
        Dimension: 'area_code', 'local_hour', 'day_of_week', 'business_type', 'lead_source'."""
        valid = {"area_code", "local_hour", "day_of_week", "business_type", "lead_source"}
        if dimension not in valid:
            return []
        
        with sqlite3.connect(self.ANALYTICS_DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"""
                SELECT {dimension},
                    COUNT(*) as total_calls,
                    SUM(connected) as connects,
                    SUM(human_contact) as human_contacts,
                    ROUND(CAST(SUM(connected) AS REAL) / COUNT(*) * 100, 1) as connect_rate,
                    ROUND(CAST(SUM(human_contact) AS REAL) / COUNT(*) * 100, 1) as human_rate,
                    ROUND(AVG(duration_seconds), 0) as avg_duration
                FROM call_events
                GROUP BY {dimension}
                HAVING COUNT(*) >= ?
                ORDER BY human_rate DESC
            """, (min_calls,)).fetchall()
            return [dict(r) for r in rows]
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall contact rate stats."""
        with sqlite3.connect(self.ANALYTICS_DB) as conn:
            row = conn.execute("""
                SELECT COUNT(*) as total,
                    SUM(connected) as connects,
                    SUM(human_contact) as humans,
                    ROUND(AVG(duration_seconds), 0) as avg_dur
                FROM call_events
            """).fetchone()
            
            total, connects, humans, avg_dur = row
            return {
                "total_calls": total or 0,
                "total_connects": connects or 0,
                "total_human_contacts": humans or 0,
                "connect_rate": round((connects or 0) / max(total or 1, 1) * 100, 1),
                "human_contact_rate": round((humans or 0) / max(total or 1, 1) * 100, 1),
                "avg_duration": int(avg_dur or 0),
            }


# ══════════════════════════════════════════════════════════════════════
#  STIR/SHAKEN REFERENCE
# ══════════════════════════════════════════════════════════════════════

STIR_SHAKEN_GRADES = {
    "A": {
        "name": "Full Attestation",
        "meaning": "Number verified, caller verified",
        "impact": "Displays normally — best possible grade",
        "target": True,
    },
    "B": {
        "name": "Partial Attestation",
        "meaning": "Number verified, caller uncertain",
        "impact": "Sometimes flagged — acceptable for most carriers",
        "target": False,
    },
    "C": {
        "name": "Gateway Attestation",
        "meaning": "Neither verified",
        "impact": "Often flagged as spam — AVOID for outbound campaigns",
        "target": False,
    },
}

# Recommended carrier platforms for high-volume legitimate outbound
RECOMMENDED_PLATFORMS = {
    "bandwidth": {
        "name": "Bandwidth.com",
        "strength": "Carrier-grade, excellent A attestation, built for enterprise volume",
        "stir_shaken": "A grade standard",
        "note": "Best for serious volume with clean reputation",
    },
    "telnyx": {
        "name": "Telnyx",
        "strength": "Strong reputation management tools built in",
        "stir_shaken": "A/B grade",
        "note": "Good number management dashboard",
    },
    "twilio": {
        "name": "Twilio",
        "strength": "Highly programmable, good for custom AI integration",
        "stir_shaken": "B grade typical (A with verified numbers)",
        "note": "Current platform — requires careful number management",
    },
    "plivo": {
        "name": "Plivo",
        "strength": "Similar to Twilio, competitive pricing",
        "stir_shaken": "B grade typical",
        "note": "Alternative carrier option",
    },
}


# ══════════════════════════════════════════════════════════════════════
#  OPTIMIZED TARGET METRICS
# ══════════════════════════════════════════════════════════════════════

CURRENT_METRICS = {
    "contact_rate_per_dial": "10-15%",
    "contact_rate_per_lead_multi_touch": "15-20%",
    "voicemail_to_callback_rate": "2-5%",
    "text_response_rate": "5-8%",
    "appointments_per_50_dials": "1-2",
}

OPTIMIZED_TARGETS = {
    "contact_rate_per_dial": "30-45%",
    "contact_rate_per_lead_multi_touch": "50-65%",
    "voicemail_to_callback_rate": "8-12%",
    "text_response_rate": "15-25%",
    "appointments_per_50_dials": "4-8",
}

OPTIMIZATION_KEYS = {
    "local_presence": "40-60% improvement — match caller ID to merchant area code",
    "stir_shaken_A": "20-30% improvement — verified attestation prevents spam flagging",
    "number_rotation": "15-25% improvement — no single number exceeds carrier threshold",
    "optimal_timing": "15-20% improvement — Tue-Thu, 9:30-11:30 & 1:30-3:30 local",
    "data_quality": "200-400% improvement — verified mobile vs scraped landline",
    "multi_touch": "150-250% improvement — 7-touch sequence vs single attempt",
}


# ══════════════════════════════════════════════════════════════════════
#  CONVENIENCE: Full CRO Assessment for a Lead
# ══════════════════════════════════════════════════════════════════════

def assess_lead_contact_probability(lead: Dict, local_weekday: int = None,
                                     local_hour: int = None,
                                     local_minute: int = 0) -> Dict[str, Any]:
    """
    Full CRO assessment for a single lead.
    Combines timing, data quality, and infrastructure readiness
    into a single contact probability estimate.
    """
    # Timing
    if local_weekday is not None and local_hour is not None:
        timing = get_call_timing_score(local_weekday, local_hour, local_minute)
    else:
        timing = {"composite": 50, "recommendation": "No timing data"}
    
    # Data quality
    quality = score_data_quality(lead)
    
    # Local presence
    lpm = LocalPresenceManager()
    pool_health = lpm.check_health()
    has_local_presence = pool_health.get("configured", False)
    
    # Composite probability
    base = quality["composite_quality"]
    timing_mult = timing["composite"] / 100  # 0-1
    presence_mult = 1.5 if has_local_presence else 1.0  # 50% boost with local presence
    
    estimated_contact_rate = min(base * timing_mult * presence_mult, 0.95)
    
    return {
        "estimated_contact_rate": f"{int(estimated_contact_rate * 100)}%",
        "timing": timing,
        "data_quality": quality,
        "local_presence": {
            "configured": has_local_presence,
            "boost": "+50%" if has_local_presence else "NOT CONFIGURED — missing ~50% potential contact rate",
        },
        "recommendations": _get_recommendations(timing, quality, has_local_presence),
    }

def _get_recommendations(timing: Dict, quality: Dict, has_presence: bool) -> List[str]:
    recs = []
    if timing["composite"] < 60:
        recs.append(f"TIMING: Wait for prime window — current score {timing['composite']}/100")
    if quality["composite_quality"] < 0.3:
        recs.append(f"DATA: Low quality source ({quality['source']}) — consider better data")
    if quality["is_toll_free"]:
        recs.append("DATA: Toll-free number — very low DM contact rate expected")
    if not has_presence:
        recs.append("INFRASTRUCTURE: No local presence configured — set up number pool for +50% boost")
    if quality["line_multiplier"] < 1.0:
        recs.append(f"LINE TYPE: {quality['line_type']} — consider sourcing mobile numbers")
    return recs


# ══════════════════════════════════════════════════════════════════════
#  CLI: Quick Stats
# ══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("  CONTACT RATE OPTIMIZER — Infrastructure Assessment")
    print("=" * 70)
    
    # Check number pool
    lpm = LocalPresenceManager()
    health = lpm.check_health()
    print(f"\n  LOCAL PRESENCE DIALING:")
    if health["configured"]:
        print(f"    Pool: {health['total_numbers']} numbers ({health['active']} active)")
        print(f"    Area codes covered: {health['area_codes_covered']}")
        print(f"    Flagged: {health['flagged']} | Near retirement: {health['near_retirement']}")
    else:
        print(f"    ❌ NOT CONFIGURED — using single TWILIO_PHONE_NUMBER")
        print(f"    💡 Configure data/number_pool.json with 50+ clean numbers")
        print(f"    💡 This single change can DOUBLE contact rates")
    
    # Current timing
    from datetime import datetime
    now = datetime.now()
    timing = get_call_timing_score(now.weekday(), now.hour, now.minute)
    print(f"\n  CALL TIMING (right now):")
    print(f"    Day: {timing['day']} (score: {timing['day_score']}/100) — {timing['day_note']}")
    print(f"    Time: {now.strftime('%I:%M %p')} (score: {timing['time_score']}/100)")
    print(f"    Prime window: {'YES — ' + timing['prime_window'] if timing['is_prime'] else 'No'}")
    print(f"    Composite: {timing['composite']}/100 — {timing['recommendation']}")
    
    # Multi-touch sequencer
    mts = MultiTouchSequencer()
    seq_summary = mts.get_sequence_summary()
    print(f"\n  MULTI-TOUCH SEQUENCER:")
    print(f"    Total sequences: {seq_summary['total_sequences']}")
    print(f"    Active: {seq_summary['active']} | Completed: {seq_summary['completed']} | Exhausted: {seq_summary['exhausted']}")
    print(f"    Due now: {seq_summary['due_now']}")
    
    # Analytics
    cra = ContactRateAnalytics()
    stats = cra.get_overall_stats()
    print(f"\n  CONTACT RATE ANALYTICS:")
    print(f"    Total calls tracked: {stats['total_calls']}")
    print(f"    Connect rate: {stats['connect_rate']}%")
    print(f"    Human contact rate: {stats['human_contact_rate']}%")
    
    # Targets
    print(f"\n  OPTIMIZATION TARGETS:")
    print(f"    {'Metric':<40s} {'Current':>12s} {'Target':>12s}")
    print(f"    {'─'*64}")
    for key in CURRENT_METRICS:
        label = key.replace("_", " ").title()
        print(f"    {label:<40s} {CURRENT_METRICS[key]:>12s} {OPTIMIZED_TARGETS[key]:>12s}")
    
    # Key optimizations
    print(f"\n  KEY OPTIMIZATIONS (impact ranking):")
    for key, desc in OPTIMIZATION_KEYS.items():
        label = key.replace("_", " ").upper()
        print(f"    {label}: {desc}")
    
    print()
