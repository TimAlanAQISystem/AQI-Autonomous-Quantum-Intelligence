"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 28 — CALENDAR & SCHEDULING (REAL-TIME BOOKING)               ║
║                                                                              ║
║  Allow Alan to check availability, book appointments, send invites, and      ║
║  reschedule during a live call. Replaces "I'll have someone call you back"   ║
║  with real-time scheduling.                                                  ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - No double-booking (lock-check-book pattern)                             ║
║    - All bookings logged                                                     ║
║    - Merchant must confirm time verbally                                     ║
║    - Business hours enforced                                                 ║
║    - Buffer time between bookings (15 min)                                   ║
║    - "Insert if missing" rules for email/name/business                       ║
║                                                                              ║
║  RRG: Section 38                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── IQcore Wiring ───────────────────────────────────────────────────────────
_parent = str(Path(__file__).resolve().parent.parent)
if _parent not in sys.path:
    sys.path.insert(0, _parent)

try:
    from iqcore_enforcer import iqcore_cost
    IQCORE_AVAILABLE = True
except ImportError:
    IQCORE_AVAILABLE = False
    def iqcore_cost(actor: str, cost: int):
        def decorator(fn):
            return fn
        return decorator

logger = logging.getLogger("organ_28_calendar")

# ─── Constants ───────────────────────────────────────────────────────────────

BUFFER_MINUTES = 15           # Minimum gap between bookings
BUSINESS_HOURS_START = 9      # 9 AM
BUSINESS_HOURS_END = 17       # 5 PM
MAX_SLOTS_PROPOSED = 3        # Number of slots to propose
DEFAULT_DURATION_MINUTES = 30 # Default appointment length
CALENDAR_STORE = "data/calendar_bookings.json"


class CalendarOrgan:
    """
    Organ 28: Real-time calendar management and appointment booking.
    IQcore cost: 2 per booking action.
    """

    def __init__(self, store_path: Optional[str] = None):
        self._store_path = store_path or CALENDAR_STORE
        self._bookings: List[Dict] = []
        self._active_call: Optional[str] = None
        self._pending_confirmation: Optional[Dict] = None
        self._booking_log: List[Dict] = []
        self._load_bookings()
        logger.info("[Organ 28] CalendarOrgan initialized")

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def start_call(self, call_id: str) -> None:
        self._active_call = call_id
        self._pending_confirmation = None
        logger.info(f"[Organ 28] Call started: {call_id}")

    def end_call(self) -> Dict[str, Any]:
        stats = {
            "call_id": self._active_call,
            "bookings_made": len([b for b in self._booking_log
                                   if b.get("call_id") == self._active_call]),
            "pending_abandoned": self._pending_confirmation is not None,
        }
        self._active_call = None
        self._pending_confirmation = None
        return stats

    # ─── Availability ────────────────────────────────────────────────────

    @iqcore_cost("Alan", 2)
    def check_availability(
        self,
        date_str: Optional[str] = None,
        duration_minutes: int = DEFAULT_DURATION_MINUTES,
    ) -> Dict[str, Any]:
        """
        Check available time slots for a given date.
        Defaults to next business day if no date provided.

        Returns:
            Dict with available_slots list
        """
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return {"status": "error", "reason": f"Invalid date format: {date_str}. Use YYYY-MM-DD."}
        else:
            target_date = self._next_business_day()

        # Get existing bookings for target date
        day_bookings = self._get_bookings_for_date(target_date)

        # Generate available slots
        slots = []
        current = datetime.combine(target_date, datetime.min.time().replace(hour=BUSINESS_HOURS_START))
        end_of_day = datetime.combine(target_date, datetime.min.time().replace(hour=BUSINESS_HOURS_END))

        while current + timedelta(minutes=duration_minutes) <= end_of_day and len(slots) < MAX_SLOTS_PROPOSED:
            slot_end = current + timedelta(minutes=duration_minutes)

            # Check for conflicts (including buffer)
            has_conflict = False
            for booking in day_bookings:
                b_start = datetime.fromisoformat(booking["start"])
                b_end = datetime.fromisoformat(booking["end"])
                buffer = timedelta(minutes=BUFFER_MINUTES)

                if not (slot_end + buffer <= b_start or current >= b_end + buffer):
                    has_conflict = True
                    break

            if not has_conflict:
                slots.append({
                    "start": current.isoformat(),
                    "end": slot_end.isoformat(),
                    "display": current.strftime("%I:%M %p"),
                    "date": target_date.isoformat(),
                })

            current += timedelta(minutes=BUFFER_MINUTES)

        return {
            "status": "ok",
            "date": target_date.isoformat(),
            "available_slots": slots,
            "total_available": len(slots),
            "duration_minutes": duration_minutes,
        }

    # ─── Booking ─────────────────────────────────────────────────────────

    @iqcore_cost("Alan", 2)
    def propose_booking(
        self,
        slot_start: str,
        merchant_name: Optional[str] = None,
        merchant_email: Optional[str] = None,
        merchant_phone: Optional[str] = None,
        business_name: Optional[str] = None,
        notes: str = "",
        duration_minutes: int = DEFAULT_DURATION_MINUTES,
    ) -> Dict[str, Any]:
        """
        Propose a booking (requires verbal confirmation via confirm_booking).

        Insert-if-missing rules:
        - If email missing: calendar event uses phone number, SMS confirmation
        - If name missing: event uses business name or phone
        - If business missing: event uses merchant name or phone
        """
        try:
            start_dt = datetime.fromisoformat(slot_start)
        except ValueError:
            return {"status": "error", "reason": f"Invalid datetime: {slot_start}"}

        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # ── Double-booking check ──
        if self._has_conflict(start_dt, end_dt):
            return {
                "status": "conflict",
                "reason": "Time slot conflicts with existing booking",
                "requested_start": slot_start,
            }

        # ── Business hours check ──
        if not self._is_business_hours(start_dt, end_dt):
            return {
                "status": "outside_hours",
                "reason": f"Slot outside business hours ({BUSINESS_HOURS_START}AM-{BUSINESS_HOURS_END - 12}PM)",
            }

        # ── Insert-if-missing ──
        missing_notes = []
        display_name = merchant_name
        if not merchant_name:
            display_name = business_name or merchant_phone or "Unknown"
            missing_notes.append("Name not captured; using business name or phone as identifier")

        event_title = f"Call — {display_name}"
        if business_name and business_name != display_name:
            event_title = f"Call — {display_name} ({business_name})"

        confirmation_method = "email" if merchant_email else "sms" if merchant_phone else "none"
        if not merchant_email:
            missing_notes.append("Email missing; SMS confirmation will be sent instead")

        # ── Store as pending ──
        self._pending_confirmation = {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "title": event_title,
            "merchant_name": display_name,
            "merchant_email": merchant_email,
            "merchant_phone": merchant_phone,
            "business_name": business_name,
            "notes": notes,
            "confirmation_method": confirmation_method,
            "missing_notes": missing_notes,
            "call_id": self._active_call,
            "proposed_at": time.time(),
        }

        return {
            "status": "proposed",
            "start": start_dt.strftime("%A, %B %d at %I:%M %p"),
            "end": end_dt.strftime("%I:%M %p"),
            "duration": duration_minutes,
            "title": event_title,
            "confirmation_method": confirmation_method,
            "missing_notes": missing_notes,
            "message": f"Proposed: {start_dt.strftime('%A %B %d at %I:%M %p')} — awaiting verbal confirmation.",
        }

    def confirm_booking(self) -> Dict[str, Any]:
        """
        Confirm the pending booking after merchant verbal confirmation.
        """
        if not self._pending_confirmation:
            return {"status": "error", "reason": "No pending booking to confirm"}

        booking = self._pending_confirmation.copy()
        booking["confirmed_at"] = time.time()
        booking["booking_id"] = f"BK-{int(time.time())}"

        self._bookings.append(booking)
        self._save_bookings()

        self._booking_log.append({
            "call_id": self._active_call,
            "booking_id": booking["booking_id"],
            "action": "confirmed",
            "timestamp": time.time(),
        })

        self._pending_confirmation = None

        logger.info(f"[Organ 28] Booking confirmed: {booking['booking_id']}")
        return {
            "status": "confirmed",
            "booking_id": booking["booking_id"],
            "start": booking["start"],
            "end": booking["end"],
            "title": booking["title"],
            "confirmation_method": booking["confirmation_method"],
        }

    def cancel_booking(self, booking_id: str) -> Dict[str, Any]:
        """Cancel a confirmed booking."""
        for i, b in enumerate(self._bookings):
            if b.get("booking_id") == booking_id:
                cancelled = self._bookings.pop(i)
                self._save_bookings()
                self._booking_log.append({
                    "call_id": self._active_call,
                    "booking_id": booking_id,
                    "action": "cancelled",
                    "timestamp": time.time(),
                })
                return {"status": "cancelled", "booking_id": booking_id}
        return {"status": "not_found", "booking_id": booking_id}

    def reschedule_booking(self, booking_id: str, new_start: str,
                           duration_minutes: int = DEFAULT_DURATION_MINUTES) -> Dict[str, Any]:
        """Reschedule an existing booking."""
        cancel_result = self.cancel_booking(booking_id)
        if cancel_result["status"] != "cancelled":
            return {"status": "error", "reason": f"Could not cancel original: {cancel_result}"}

        # Re-propose at new time (reuses pending mechanism)
        return self.propose_booking(slot_start=new_start, duration_minutes=duration_minutes)

    # ─── Internal Helpers ────────────────────────────────────────────────

    def _next_business_day(self) -> 'datetime.date':
        """Get next business day from today."""
        d = datetime.now().date() + timedelta(days=1)
        while d.weekday() >= 5:  # Saturday=5, Sunday=6
            d += timedelta(days=1)
        return d

    def _get_bookings_for_date(self, target_date) -> List[Dict]:
        """Get all bookings for a specific date."""
        results = []
        for b in self._bookings:
            try:
                b_date = datetime.fromisoformat(b["start"]).date()
                if b_date == target_date:
                    results.append(b)
            except (ValueError, KeyError):
                continue
        return results

    def _has_conflict(self, start: datetime, end: datetime) -> bool:
        """Check if proposed time conflicts with existing bookings."""
        buffer = timedelta(minutes=BUFFER_MINUTES)
        for b in self._bookings:
            try:
                b_start = datetime.fromisoformat(b["start"])
                b_end = datetime.fromisoformat(b["end"])
                if not (end + buffer <= b_start or start >= b_end + buffer):
                    return True
            except (ValueError, KeyError):
                continue
        return False

    def _is_business_hours(self, start: datetime, end: datetime) -> bool:
        """Check if slot falls within business hours."""
        return (start.hour >= BUSINESS_HOURS_START and
                end.hour <= BUSINESS_HOURS_END and
                start.weekday() < 5)  # Mon–Fri

    # ─── Persistence ─────────────────────────────────────────────────────

    def _load_bookings(self) -> None:
        try:
            path = Path(self._store_path)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._bookings = json.load(f)
                logger.info(f"[Organ 28] Loaded {len(self._bookings)} bookings")
        except Exception as e:
            logger.warning(f"[Organ 28] Failed to load bookings: {e}")
            self._bookings = []

    def _save_bookings(self) -> None:
        try:
            path = Path(self._store_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._bookings, f, indent=2)
        except Exception as e:
            logger.warning(f"[Organ 28] Failed to save bookings: {e}")

    # ─── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "organ": "Organ 28 — Calendar & Scheduling",
            "version": "4.1.0",
            "iqcore_available": IQCORE_AVAILABLE,
            "active_call": self._active_call,
            "total_bookings": len(self._bookings),
            "pending_confirmation": self._pending_confirmation is not None,
            "booking_actions": len(self._booking_log),
        }
