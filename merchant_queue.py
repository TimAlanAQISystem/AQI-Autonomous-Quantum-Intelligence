"""
Merchant Queue Management for Agent X Outbound Campaigns
Persistent queue with outcome tracking and retry logic
"""

import json
import os
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, fields
from enum import Enum

class CallOutcome(Enum):
    PENDING = "pending"
    ANSWERED = "answered"
    CONNECTED = "connected"
    CALLBACK_SCHEDULED = "callback_scheduled"  # Explicitly tracking scheduled callbacks
    VOICEMAIL = "voicemail"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    INTERESTED = "interested"
    DECLINED = "declined"
    QUALIFIED = "qualified"
    CLOSED_WON = "closed_won"
    DO_NOT_CALL = "do_not_call"
    CANCELLED_BY_USER = "cancelled_by_user"

@dataclass
class Merchant:
    """Represents a merchant in the outbound queue"""
    id: str
    phone_number: str
    name: Optional[str] = None
    business_type: Optional[str] = None
    priority: str = "normal"  # normal, high, URGENT
    # line_type moved to end
    attempts: int = 0
    max_attempts: int = 3
    last_attempt: Optional[datetime] = None
    next_attempt: Optional[datetime] = None
    outcome: CallOutcome = CallOutcome.PENDING
    outcome_details: Optional[str] = None
    interested_products: List[str] = None
    notes: List[str] = None
    do_not_call: bool = False
    created_at: datetime = None
    updated_at: datetime = None
    line_type: Optional[str] = None  # mobile, landline, voip, etc.
    
    # [CAMPAIGN WIRING] Context Fields
    monthly_volume: Optional[float] = None
    lead_source: Optional[str] = None
    tier: Optional[str] = None
    expected_pitch: Optional[str] = None
    fallback_pitch: Optional[str] = None

    def __post_init__(self):
        if self.interested_products is None:
            self.interested_products = []
        if self.notes is None:
            self.notes = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def can_attempt_now(self) -> bool:
        """Check if merchant can be calling now"""
        # DEBUG: Temporary logging to find why eligible is 0
        reason = ""
        now = datetime.now()
        
        if self.do_not_call:
            reason = "do_not_call"
        elif self.priority != "URGENT" and self.attempts >= self.max_attempts:
            reason = "max_attempts"
        elif self.last_attempt and (now - self.last_attempt).days > 7:
            reason = "expired_7_days"
        # FIX: Only check future schedule if we have actually tried calling before
        elif self.attempts > 0 and self.next_attempt and now < self.next_attempt:
            reason = "next_attempt_future"
        
        # [DIRECTIVE]: CIRCUIT BREAKER - DUPLICATE SQUELCH
        # Prevent more than 2 attempts in rolling 24h window
        if self.last_attempt and (now - self.last_attempt).total_seconds() < 86400:
             # Check how many attempts today (simple heuristic: if called today and attempts > 2)
             # Better: If called within last 10 minutes, prevent rapid retry
             if (now - self.last_attempt).total_seconds() < 600 and self.priority != "URGENT":
                 reason = "rapid_redial_prevention"
        
        if reason:
             return False
        return True

    def record_attempt(self, outcome: CallOutcome, details: str = None, next_attempt: datetime = None):
        """Record a call attempt"""
        self.attempts += 1
        self.last_attempt = datetime.now()
        self.outcome = outcome
        self.outcome_details = details or ""
        self.updated_at = datetime.now()

        # If a specific appointment is requested, honor it primarily
        if outcome == CallOutcome.CALLBACK_SCHEDULED and next_attempt:
            self.next_attempt = next_attempt
            # Reset attempts counter for scheduled callbacks to ensure it doesn't get skipped by max_attempts logic
            # However, we don't zero it completely to avoid infinite loops, but we treat it as a fresh start or give it a high priority
            self.priority = "URGENT" 
            return

        if next_attempt:
            self.next_attempt = next_attempt
            return

        # Schedule next attempt based on outcome
        if outcome in [CallOutcome.VOICEMAIL, CallOutcome.NO_ANSWER, CallOutcome.BUSY, CallOutcome.FAILED]:
            
            # URGENT Priority Logic: Retry sooner and don't stop
            if self.priority == "URGENT":
                 if self.attempts < 5:
                     self.next_attempt = datetime.now() + timedelta(minutes=30) # Aggressive initial retries
                 else:
                     self.next_attempt = datetime.now() + timedelta(hours=2) # Then every 2 hours
            
            # Normal Priority Logic
            elif self.attempts < 3:
                # Optimized for aggressive day-calling (User Request: 2026-01-14)
                # Attempt 1 -> Retry in 45 mins (catch them after lunch/meeting)
                # Attempt 2 -> Retry in 90 mins
                if self.attempts == 1:
                    self.next_attempt = datetime.now() + timedelta(minutes=45)
                elif self.attempts == 2:
                    self.next_attempt = datetime.now() + timedelta(minutes=90)
                # After 3 attempts, will be marked as do_not_call by can_attempt_now check
            else:
                # After 3 attempts, mark as do not call
                self.do_not_call = True
        elif outcome in [CallOutcome.DECLINED, CallOutcome.DO_NOT_CALL]:
            # Mark as do not call immediately
            self.do_not_call = True
        elif outcome in [CallOutcome.ANSWERED, CallOutcome.CONNECTED, CallOutcome.INTERESTED, CallOutcome.QUALIFIED]:
            # Successful engagement - follow up in 1 day
            self.next_attempt = datetime.now() + timedelta(days=1)

    def add_note(self, note: str):
        """Add a note to the merchant record"""
        self.notes.append(f"{datetime.now().isoformat()}: {note}")
        self.updated_at = datetime.now()

class MerchantQueue:
    """Manages the merchant calling queue with persistence"""

    def __init__(self, storage_file: str = "merchant_queue.json"):
        self.storage_file = storage_file
        self._merchants: Dict[str, Merchant] = {}
        self._lock = threading.Lock()
        self._load_queue()

    def _load_queue(self):
        """Load queue from persistent storage"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    for mid, merchant_data in data.items():
                        # Convert datetime strings and enums
                        for key in ['last_attempt', 'next_attempt', 'created_at', 'updated_at']:
                            if key in merchant_data and merchant_data[key]:
                                merchant_data[key] = datetime.fromisoformat(merchant_data[key])

                        if 'outcome' in merchant_data:
                            merchant_data['outcome'] = CallOutcome(merchant_data['outcome'])

                        # Robust loading: Filter unidentified keys
                        valid_keys = {f.name for f in fields(Merchant)}
                        filtered_data = {k: v for k, v in merchant_data.items() if k in valid_keys}
                        
                        self._merchants[mid] = Merchant(**filtered_data)
        except Exception as e:
            print(f"Error loading merchant queue: {e}")
            self._merchants = {}

    def _save_queue(self):
        """Save queue to persistent storage (Atomic Write)"""
        try:
            data = {}
            for mid, merchant in self._merchants.items():
                merchant_dict = asdict(merchant)
                # Convert datetime objects and enums to serializable format
                for key in ['last_attempt', 'next_attempt', 'created_at', 'updated_at']:
                    if merchant_dict[key]:
                        merchant_dict[key] = merchant_dict[key].isoformat()
                merchant_dict['outcome'] = merchant.outcome.value

                data[mid] = merchant_dict

            # Atomic write: write to temp file then rename
            temp_file = f"{self.storage_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic replacement
            os.replace(temp_file, self.storage_file)
            
        except Exception as e:
            print(f"Error saving merchant queue: {e}")

    def add_merchant(self, phone_number: str, name: str = None, business_type: str = None, priority: str = "normal") -> str:
        """Add a new merchant to the queue"""
        with self._lock:
            self._load_queue()  # Reload to get latest state
            merchant_id = f"merchant_{len(self._merchants) + 1}"
            merchant = Merchant(
                id=merchant_id,
                phone_number=phone_number,
                name=name,
                business_type=business_type,
                priority=priority
            )
            self._merchants[merchant_id] = merchant
            self._save_queue()
            return merchant_id

    def add_merchants_batch(self, leads_data: List[Dict]) -> int:
        """Add multiple merchants to the queue at once (Performance Optimized)"""
        with self._lock:
            self._load_queue()
            count = 0
            for lead in leads_data:
                merchant_id = f"merchant_{len(self._merchants) + 1}"
                merchant = Merchant(
                    id=merchant_id,
                    phone_number=lead['phone_number'],
                    name=lead.get('name'),
                    business_type=lead.get('business_type'),
                    priority=lead.get('priority', 'normal')
                )
                self._merchants[merchant_id] = merchant
                count += 1
            
            self._save_queue()
            return count

    def get_next_merchant(self, exclude_area_codes: List[str] = None) -> Optional[Merchant]:
        """Get the next merchant eligible for calling"""
        with self._lock:
            self._load_queue()  # Reload to get latest state from other processes
            
            # Helper to check area code
            def has_excluded_ac(m_phone):
                if not exclude_area_codes: return False
                clean = m_phone.replace("+1", "").replace("(", "").replace(")", "").replace("-", "").strip()
                if len(clean) >= 3:
                    ac = clean[:3]
                    return ac in exclude_area_codes
                return False

            eligible = [m for m in self._merchants.values() if m.can_attempt_now() and not has_excluded_ac(m.phone_number)]
            if not eligible:
                # If no eligible leads after exclusion, try relaxing the exclusion?
                # For strict entropy, we return None and let the runner handle waiting.
                # However, if ONLY excluded area codes are available, strict entropy stops the campaign.
                # Let's trust the runner to manage exclusions.
                return None

            # Sort by priority (URGENT > high > normal), then by attempts, then by last attempt time
            # Primary sort key: Priority Score (Method to convert string to int)
            def priority_score(m):
                if m.priority == "URGENT": return 0
                if m.priority == "high": return 1
                return 2

            eligible.sort(key=lambda m: (priority_score(m), m.attempts, m.last_attempt or datetime.min))
            return eligible[0]

    def update_merchant_outcome(self, merchant_id: str, outcome: CallOutcome, details: str = None, next_attempt: datetime = None):
        """Update merchant call outcome"""
        with self._lock:
            self._load_queue()  # Reload to ensure we don't overwrite other updates
            if merchant_id in self._merchants:
                self._merchants[merchant_id].record_attempt(outcome, details, next_attempt)
                self._save_queue()

    def update_merchant_outcome_by_phone(self, phone_number: str, outcome: CallOutcome, details: str = None, next_attempt: datetime = None):
        """Update merchant call outcome by phone number"""
        with self._lock:
            self._load_queue()  # Reload to ensure we don't overwrite other updates
            for merchant in self._merchants.values():
                if merchant.phone_number == phone_number:
                    merchant.record_attempt(outcome, details, next_attempt)
                    self._save_queue()
                    break

    def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        """Get merchant by ID"""
        with self._lock:
            return self._merchants.get(merchant_id)

    def get_all_merchants(self) -> List[Merchant]:
        """Get all merchants"""
        with self._lock:
            return list(self._merchants.values())

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        with self._lock:
            total = len(self._merchants)
            eligible = sum(1 for m in self._merchants.values() if m.can_attempt_now())
            attempted = sum(1 for m in self._merchants.values() if m.attempts > 0)
            completed = sum(1 for m in self._merchants.values() if m.outcome != CallOutcome.PENDING)

            outcome_counts = {}
            for outcome in CallOutcome:
                outcome_counts[outcome.value] = sum(1 for m in self._merchants.values() if m.outcome == outcome)

            return {
                "total_merchants": total,
                "eligible_for_call": eligible,
                "previously_attempted": attempted,
                "completed_calls": completed,
                "outcome_breakdown": outcome_counts
            }

    def cleanup_completed(self):
        """Remove merchants marked as do_not_call or completed"""
        with self._lock:
            to_remove = []
            for mid, merchant in self._merchants.items():
                if merchant.do_not_call or merchant.outcome in [CallOutcome.CLOSED_WON, CallOutcome.DECLINED]:
                    to_remove.append(mid)

            for mid in to_remove:
                del self._merchants[mid]

            if to_remove:
                self._save_queue()
                print(f"Cleaned up {len(to_remove)} completed merchants")

# Global queue instance
merchant_queue = MerchantQueue()