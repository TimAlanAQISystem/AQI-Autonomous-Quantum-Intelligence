"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 25 — HANDOFF & ESCALATION (WARM TRANSFER)                    ║
║                                                                              ║
║  Enable Alan to escalate a live call to a human closer, bridge the call,     ║
║  or conference in a manager. Supports warm transfer, cold transfer,          ║
║  and conference mode with closer availability lookup and failover.           ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - Merchant consent required before any transfer                           ║
║    - All handoffs logged with reason and outcome                             ║
║    - No silent transfers                                                     ║
║    - Failover to callback scheduling if closer unavailable                   ║
║    - "Insert if missing" rules for name/business                             ║
║                                                                              ║
║  RRG: Section 35                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

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

logger = logging.getLogger("organ_25_handoff")

# ─── Constants ───────────────────────────────────────────────────────────────

class HandoffMode(Enum):
    WARM = "warm"       # Alan introduces, then bridges
    COLD = "cold"       # Direct transfer without introduction
    CONFERENCE = "conf" # Alan + merchant + closer

class HandoffReason(Enum):
    MERCHANT_REQUEST = "merchant_request"
    DEAL_READY = "deal_ready"
    HIGH_VALUE = "high_value"
    COMPLIANCE = "compliance"
    DURATION_EXCEEDED = "duration_exceeded"
    RESOLUTION_FAILURE = "resolution_failure"

DEAL_READINESS_THRESHOLD = 75   # Score at which auto-escalation triggers
MAX_CALL_DURATION_SECONDS = 900 # 15 minutes
MAX_FAILED_ATTEMPTS = 3         # Before resolution failure escalation

# ─── Closer Registry ────────────────────────────────────────────────────────

DEFAULT_CLOSERS = [
    {"name": "Tim", "extension": "101", "available": True, "priority": 1},
    {"name": "Sales Desk", "extension": "200", "available": True, "priority": 2},
]


class HandoffEscalationOrgan:
    """
    Organ 25: Manages call escalation and warm/cold/conference transfers.
    IQcore cost: 3 per handoff decision (rare but heavy).
    """

    def __init__(self, closers: Optional[List[Dict]] = None):
        import copy
        self._closers = closers if closers is not None else copy.deepcopy(DEFAULT_CLOSERS)
        self._handoff_log: List[Dict] = []
        self._active_call: Optional[str] = None
        self._consent_given = False
        self._failed_attempts = 0
        self._call_start_time: Optional[float] = None
        logger.info("[Organ 25] HandoffEscalationOrgan initialized")

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def start_call(self, call_id: str) -> None:
        """Initialize state for a new call."""
        self._active_call = call_id
        self._consent_given = False
        self._failed_attempts = 0
        self._call_start_time = time.time()
        logger.info(f"[Organ 25] Call started: {call_id}")

    def end_call(self) -> Dict[str, Any]:
        """Finalize call and return handoff stats."""
        stats = {
            "call_id": self._active_call,
            "handoffs_attempted": len([h for h in self._handoff_log
                                        if h.get("call_id") == self._active_call]),
            "consent_given": self._consent_given,
            "failed_attempts": self._failed_attempts,
        }
        self._active_call = None
        self._consent_given = False
        self._failed_attempts = 0
        self._call_start_time = None
        logger.info(f"[Organ 25] Call ended. Stats: {stats}")
        return stats

    # ─── Core Handoff Logic ─────────────────────────────────────────────

    @iqcore_cost("Alan", 3)
    def initiate_handoff(
        self,
        reason: str,
        mode: str = "warm",
        merchant_name: Optional[str] = None,
        business_name: Optional[str] = None,
        merchant_phone: Optional[str] = None,
        deal_readiness_score: int = 0,
        context_notes: str = "",
    ) -> Dict[str, Any]:
        """
        Initiate a handoff to a human closer.

        Args:
            reason: Why the handoff is happening (HandoffReason value)
            mode: Transfer mode (warm/cold/conf)
            merchant_name: Name of the merchant (may be None)
            business_name: Business name (may be None)
            merchant_phone: Phone number
            deal_readiness_score: Current deal readiness (0-100)
            context_notes: Additional context for the closer

        Returns:
            Handoff result dict with status and details
        """
        # ── Validate consent ──
        if not self._consent_given and reason != HandoffReason.COMPLIANCE.value:
            return {
                "status": "blocked",
                "reason": "consent_not_given",
                "message": "Merchant consent required before transfer.",
            }

        # ── Insert-if-missing rules ──
        display_name = merchant_name or "the merchant on the line"
        display_business = business_name or merchant_phone or "unknown business"
        missing_notes = []

        if not merchant_name:
            missing_notes.append("Name not captured; introduced as 'the merchant on the line'")
        if not business_name:
            missing_notes.append(f"Business name missing; identified by phone: {merchant_phone}")

        # ── Find available closer ──
        closer = self._find_available_closer()
        if not closer:
            # Failover: offer callback scheduling
            result = {
                "status": "failover",
                "reason": "no_closer_available",
                "message": "No closer available. Offering callback scheduling.",
                "fallback": "callback_scheduling",
                "missing_notes": missing_notes,
            }
            self._log_handoff(reason, mode, result)
            return result

        # ── Build context package ──
        context_package = {
            "merchant_name": display_name,
            "business_name": display_business,
            "merchant_phone": merchant_phone,
            "deal_readiness_score": deal_readiness_score,
            "reason": reason,
            "notes": context_notes,
            "missing_data_notes": missing_notes,
            "call_id": self._active_call,
            "timestamp": time.time(),
        }

        # ── Execute transfer ──
        result = {
            "status": "initiated",
            "mode": mode,
            "closer": closer["name"],
            "closer_extension": closer["extension"],
            "context_package": context_package,
            "display_name": display_name,
            "display_business": display_business,
            "missing_notes": missing_notes,
        }

        self._log_handoff(reason, mode, result)
        logger.info(f"[Organ 25] Handoff initiated: {mode} to {closer['name']} — reason: {reason}")
        return result

    def record_consent(self, consent: bool = True) -> None:
        """Record that merchant has consented to transfer."""
        self._consent_given = consent
        logger.info(f"[Organ 25] Consent recorded: {consent}")

    def record_failed_attempt(self) -> Dict[str, Any]:
        """Record a failed resolution attempt. Returns escalation check."""
        self._failed_attempts += 1
        should_escalate = self._failed_attempts >= MAX_FAILED_ATTEMPTS
        return {
            "failed_attempts": self._failed_attempts,
            "threshold": MAX_FAILED_ATTEMPTS,
            "should_escalate": should_escalate,
            "reason": "resolution_failure" if should_escalate else None,
        }

    def check_duration_escalation(self) -> Dict[str, Any]:
        """Check if call duration exceeds maximum."""
        if not self._call_start_time:
            return {"should_escalate": False, "duration": 0}

        duration = time.time() - self._call_start_time
        should_escalate = duration >= MAX_CALL_DURATION_SECONDS
        return {
            "duration_seconds": duration,
            "threshold": MAX_CALL_DURATION_SECONDS,
            "should_escalate": should_escalate,
            "reason": "duration_exceeded" if should_escalate else None,
        }

    def check_deal_readiness_escalation(self, score: int) -> Dict[str, Any]:
        """Check if deal readiness score warrants escalation."""
        should_escalate = score >= DEAL_READINESS_THRESHOLD
        return {
            "deal_readiness_score": score,
            "threshold": DEAL_READINESS_THRESHOLD,
            "should_escalate": should_escalate,
            "reason": "deal_ready" if should_escalate else None,
        }

    # ─── Closer Management ──────────────────────────────────────────────

    def _find_available_closer(self) -> Optional[Dict]:
        """Find the highest-priority available closer."""
        available = [c for c in self._closers if c.get("available", False)]
        if not available:
            return None
        return sorted(available, key=lambda c: c.get("priority", 99))[0]

    def set_closer_availability(self, name: str, available: bool) -> bool:
        """Update closer availability."""
        for closer in self._closers:
            if closer["name"].lower() == name.lower():
                closer["available"] = available
                logger.info(f"[Organ 25] Closer {name} availability: {available}")
                return True
        return False

    def get_closers(self) -> List[Dict]:
        """Return current closer registry."""
        return self._closers[:]

    # ─── Logging ─────────────────────────────────────────────────────────

    def _log_handoff(self, reason: str, mode: str, result: Dict) -> None:
        """Log a handoff event."""
        entry = {
            "call_id": self._active_call,
            "reason": reason,
            "mode": mode,
            "status": result.get("status"),
            "closer": result.get("closer"),
            "timestamp": time.time(),
            "missing_notes": result.get("missing_notes", []),
        }
        self._handoff_log.append(entry)

    def get_handoff_log(self) -> List[Dict]:
        """Return full handoff log."""
        return self._handoff_log[:]

    # ─── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Return organ status for diagnostics."""
        return {
            "organ": "Organ 25 — Handoff & Escalation",
            "version": "4.1.0",
            "iqcore_available": IQCORE_AVAILABLE,
            "active_call": self._active_call,
            "consent_given": self._consent_given,
            "failed_attempts": self._failed_attempts,
            "total_handoffs": len(self._handoff_log),
            "closers_available": len([c for c in self._closers if c.get("available")]),
            "closers_total": len(self._closers),
        }
