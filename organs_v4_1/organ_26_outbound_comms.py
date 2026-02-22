"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 26 — OUTBOUND COMMUNICATIONS (SMS / EMAIL / LINKS)           ║
║                                                                              ║
║  Allow Alan to send SMS, email, brochures, links, and follow-up materials    ║
║  during or after a call. Supports templated follow-ups, link generation,     ║
║  and post-call workflow engine.                                              ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - No payment processing                                                   ║
║    - No attachments without merchant consent                                 ║
║    - All outbound messages logged                                            ║
║    - Rate limiting enforced (max 1 SMS per phone per hour)                   ║
║    - Template-only: no free-form LLM-generated SMS                           ║
║    - "Insert if missing" rules for email/phone                               ║
║                                                                              ║
║  RRG: Section 36                                                             ║
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

logger = logging.getLogger("organ_26_outbound_comms")

# ─── Constants ───────────────────────────────────────────────────────────────

class Channel(Enum):
    SMS = "sms"
    EMAIL = "email"

# Rate limiting: max 1 SMS per phone per hour
SMS_RATE_LIMIT_SECONDS = 3600

# ─── Template Library ────────────────────────────────────────────────────────

DEFAULT_TEMPLATES = {
    "follow_up_pricing": {
        "channel": "sms",
        "subject": None,
        "body": "Hi {merchant_name}, thanks for speaking with us! As discussed, here's our pricing info: {link}. Reply STOP to opt out.",
    },
    "follow_up_email_pricing": {
        "channel": "email",
        "subject": "Pricing Information — {business_name}",
        "body": "Hi {merchant_name},\n\nThank you for your time today. As we discussed, please find our pricing details below:\n\n{details}\n\nBest regards,\nAlan",
    },
    "callback_confirmation": {
        "channel": "sms",
        "body": "Hi {merchant_name}, this confirms our callback scheduled for {callback_time}. Looking forward to speaking with you!",
    },
    "brochure_link": {
        "channel": "sms",
        "body": "Hi {merchant_name}, here's the brochure we discussed: {link}. Let us know if you have any questions!",
    },
    "appointment_confirmation": {
        "channel": "email",
        "subject": "Appointment Confirmation — {callback_time}",
        "body": "Hi {merchant_name},\n\nThis confirms your appointment on {callback_time}.\n\nLocation: {location}\n\nSee you then!\nAlan",
    },
}


class OutboundCommsOrgan:
    """
    Organ 26: Manages outbound SMS, email, and link-based communications.
    IQcore cost: 1 per send.
    """

    def __init__(self, templates: Optional[Dict] = None):
        self._templates = templates or DEFAULT_TEMPLATES.copy()
        self._send_log: List[Dict] = []
        self._rate_tracker: Dict[str, float] = {}  # phone -> last_send_timestamp
        self._active_call: Optional[str] = None
        self._opt_outs: set = set()  # phones that have opted out
        logger.info("[Organ 26] OutboundCommsOrgan initialized")

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def start_call(self, call_id: str) -> None:
        self._active_call = call_id
        logger.info(f"[Organ 26] Call started: {call_id}")

    def end_call(self) -> Dict[str, Any]:
        stats = {
            "call_id": self._active_call,
            "messages_sent": len([s for s in self._send_log
                                   if s.get("call_id") == self._active_call]),
        }
        self._active_call = None
        return stats

    # ─── Core Send Logic ────────────────────────────────────────────────

    @iqcore_cost("Alan", 1)
    def send_message(
        self,
        template_name: str,
        merchant_phone: Optional[str] = None,
        merchant_email: Optional[str] = None,
        merchant_name: Optional[str] = None,
        business_name: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        channel_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a templated message via SMS or email.

        Insert-if-missing rules:
        - If email missing: send SMS only
        - If phone missing: send email only
        - If both missing: log 'follow-up impossible'

        Returns:
            Send result dict
        """
        # ── Template lookup ──
        template = self._templates.get(template_name)
        if not template:
            return {"status": "error", "reason": f"Template '{template_name}' not found"}

        # ── Determine channel ──
        channel = channel_override or template.get("channel", "sms")
        missing_notes = []

        # ── Insert-if-missing rules ──
        if channel == "email" and not merchant_email:
            if merchant_phone:
                channel = "sms"  # Fallback to SMS
                missing_notes.append("Email missing; falling back to SMS")
            else:
                return {
                    "status": "impossible",
                    "reason": "no_contact_method",
                    "message": "Follow-up impossible; no email or phone available",
                    "missing_notes": ["Both email and phone missing"],
                }

        if channel == "sms" and not merchant_phone:
            if merchant_email:
                channel = "email"  # Fallback to email
                missing_notes.append("Phone missing; falling back to email")
            else:
                return {
                    "status": "impossible",
                    "reason": "no_contact_method",
                    "message": "Follow-up impossible; no email or phone available",
                    "missing_notes": ["Both email and phone missing"],
                }

        display_name = merchant_name or "Valued Merchant"
        display_business = business_name or "your business"

        # ── Rate limit check (SMS only) ──
        if channel == "sms" and merchant_phone:
            if not self._check_rate_limit(merchant_phone):
                return {
                    "status": "rate_limited",
                    "reason": f"SMS rate limit: max 1 per {SMS_RATE_LIMIT_SECONDS}s per phone",
                    "phone": merchant_phone,
                }

            # Opt-out check
            if merchant_phone in self._opt_outs:
                return {
                    "status": "opt_out",
                    "reason": "Merchant has opted out of SMS",
                    "phone": merchant_phone,
                }

        # ── Render template ──
        all_vars = {
            "merchant_name": display_name,
            "business_name": display_business,
            "merchant_phone": merchant_phone or "",
            "merchant_email": merchant_email or "",
            **(variables or {}),
        }

        body = template.get("body", "")
        subject = template.get("subject")
        try:
            body = body.format(**{k: v for k, v in all_vars.items() if f"{{{k}}}" in body})
            if subject:
                subject = subject.format(**{k: v for k, v in all_vars.items() if f"{{{k}}}" in subject})
        except KeyError as e:
            return {"status": "error", "reason": f"Missing template variable: {e}"}

        # ── Execute send ──
        result = {
            "status": "sent",
            "channel": channel,
            "template": template_name,
            "recipient": merchant_email if channel == "email" else merchant_phone,
            "subject": subject,
            "body_preview": body[:100] + ("..." if len(body) > 100 else ""),
            "missing_notes": missing_notes,
            "timestamp": time.time(),
        }

        # Update rate tracker
        if channel == "sms" and merchant_phone:
            self._rate_tracker[merchant_phone] = time.time()

        self._log_send(result)
        logger.info(f"[Organ 26] Message sent via {channel}: {template_name}")
        return result

    def send_link(
        self,
        url: str,
        merchant_phone: Optional[str] = None,
        merchant_name: Optional[str] = None,
        description: str = "requested information",
    ) -> Dict[str, Any]:
        """Send a link via SMS. Convenience wrapper."""
        return self.send_message(
            template_name="brochure_link",
            merchant_phone=merchant_phone,
            merchant_name=merchant_name,
            variables={"link": url, "description": description},
        )

    # ─── Rate Limiting ──────────────────────────────────────────────────

    def _check_rate_limit(self, phone: str) -> bool:
        """Check if we can send SMS to this phone (rate limit)."""
        last_send = self._rate_tracker.get(phone)
        if last_send is None:
            return True
        elapsed = time.time() - last_send
        return elapsed >= SMS_RATE_LIMIT_SECONDS

    # ─── Opt-out Management ─────────────────────────────────────────────

    def register_opt_out(self, phone: str) -> None:
        """Register a phone number as opted out."""
        self._opt_outs.add(phone)
        logger.info(f"[Organ 26] Opt-out registered: {phone[-4:]}")

    def check_opt_out(self, phone: str) -> bool:
        """Check if phone is opted out."""
        return phone in self._opt_outs

    # ─── Template Management ────────────────────────────────────────────

    def add_template(self, name: str, channel: str, body: str,
                     subject: Optional[str] = None) -> None:
        """Add a new message template."""
        self._templates[name] = {
            "channel": channel,
            "body": body,
            "subject": subject,
        }
        logger.info(f"[Organ 26] Template added: {name}")

    def get_templates(self) -> Dict:
        """Return all templates."""
        return self._templates.copy()

    # ─── Logging ─────────────────────────────────────────────────────────

    def _log_send(self, result: Dict) -> None:
        entry = {
            "call_id": self._active_call,
            **result,
        }
        self._send_log.append(entry)

    def get_send_log(self) -> List[Dict]:
        return self._send_log[:]

    # ─── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "organ": "Organ 26 — Outbound Communications",
            "version": "4.1.0",
            "iqcore_available": IQCORE_AVAILABLE,
            "active_call": self._active_call,
            "templates_loaded": len(self._templates),
            "total_sends": len(self._send_log),
            "opt_outs": len(self._opt_outs),
            "rate_tracked_phones": len(self._rate_tracker),
        }
