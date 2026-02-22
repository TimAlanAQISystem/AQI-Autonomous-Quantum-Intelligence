"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 29 — INBOUND CONTEXT INJECTION (CALLBACK MEMORY)             ║
║                                                                              ║
║  Give Alan memory for inbound calls. When a callback arrives, looks up       ║
║  caller by phone number and injects prior context: last call summary,        ║
║  callback reason, merchant profile, and scheduled callback info.             ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - No hallucinated context — only stored data may be injected              ║
║    - All context injections logged                                           ║
║    - Unknown callers get generic context gracefully                          ║
║    - Partial context acknowledged with uncertainty                           ║
║    - "Insert if missing" rules for name/business/context                     ║
║                                                                              ║
║  RRG: Section 39                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import sqlite3
import sys
import time
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

logger = logging.getLogger("organ_29_inbound_context")

# ─── Constants ───────────────────────────────────────────────────────────────

CDC_DB_PATH = "data/call_capture.db"
LEAD_QUEUE_PATH = "merchant_queue.json"
CALL_LOG_PATH = "call_log.json"
MAX_PRIOR_CALLS = 5  # Max prior call records to inject

# Inbound-specific scripts
INBOUND_SCRIPTS = {
    "returning_caller": (
        "Welcome back! I see we spoke on {last_call_date}. "
        "Last time we discussed {last_topic}. "
        "How can I help you today?"
    ),
    "scheduled_callback": (
        "Hi {merchant_name}, thanks for calling back! "
        "We had scheduled this follow-up to discuss {callback_reason}. "
        "Shall we pick up where we left off?"
    ),
    "unknown_caller": (
        "Hi, this is Alan. Thanks for calling! "
        "Did we speak earlier about your payment processing?"
    ),
    "partial_context": (
        "Hi, I believe we've spoken before. "
        "I have some notes from our previous conversation. "
        "How can I help you today?"
    ),
}


class InboundContextOrgan:
    """
    Organ 29: Enriches inbound calls with prior context from lead DB and CDC.
    IQcore cost: 1 per lookup.
    """

    def __init__(
        self,
        cdc_db_path: Optional[str] = None,
        lead_queue_path: Optional[str] = None,
        call_log_path: Optional[str] = None,
    ):
        self._cdc_db_path = cdc_db_path or CDC_DB_PATH
        self._lead_queue_path = lead_queue_path or LEAD_QUEUE_PATH
        self._call_log_path = call_log_path or CALL_LOG_PATH
        self._active_call: Optional[str] = None
        self._injection_log: List[Dict] = []
        self._last_context: Optional[Dict] = None
        logger.info("[Organ 29] InboundContextOrgan initialized")

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def start_call(self, call_id: str) -> None:
        self._active_call = call_id
        self._last_context = None
        logger.info(f"[Organ 29] Call started: {call_id}")

    def end_call(self) -> Dict[str, Any]:
        stats = {
            "call_id": self._active_call,
            "context_injected": self._last_context is not None,
            "context_type": self._last_context.get("context_type") if self._last_context else None,
        }
        self._active_call = None
        self._last_context = None
        return stats

    # ─── Core Context Lookup ─────────────────────────────────────────────

    @iqcore_cost("Alan", 1)
    def lookup_caller(self, phone: str) -> Dict[str, Any]:
        """
        Look up a caller by phone number across all data sources.

        Insert-if-missing rules:
        - No prior context → treat as cold, ask "Did we speak earlier?"
        - Partial context (e.g., callback time but no name) → use what's available
        - Name missing → use business name or phone

        Returns:
            Context package for system prompt injection
        """
        context = {
            "phone": phone,
            "context_type": "unknown",
            "merchant_name": None,
            "business_name": None,
            "lead_status": None,
            "prior_calls": [],
            "last_call_summary": None,
            "callback_reason": None,
            "scheduled_callback": None,
            "script_template": "unknown_caller",
            "missing_notes": [],
            "injection_text": "",
        }

        # ── Source 1: Lead Queue ──
        lead_data = self._lookup_lead(phone)
        if lead_data:
            context["merchant_name"] = lead_data.get("name") or lead_data.get("contact_name")
            context["business_name"] = lead_data.get("business_name") or lead_data.get("company")
            context["lead_status"] = lead_data.get("status")
            context["context_type"] = "known_lead"

        # ── Source 2: Call History (CDC) ──
        prior_calls = self._lookup_call_history(phone)
        if prior_calls:
            context["prior_calls"] = prior_calls[:MAX_PRIOR_CALLS]
            context["last_call_summary"] = prior_calls[0].get("summary", "")
            context["context_type"] = "returning_caller"

        # ── Source 3: Call Log (for callback info) ──
        callback_info = self._lookup_callback(phone)
        if callback_info:
            context["callback_reason"] = callback_info.get("reason")
            context["scheduled_callback"] = callback_info.get("scheduled_time")
            context["context_type"] = "scheduled_callback"

        # ── Insert-if-missing rules ──
        if not context["merchant_name"]:
            if context["business_name"]:
                context["missing_notes"].append(
                    f"Name missing; using business name: {context['business_name']}"
                )
            else:
                context["missing_notes"].append(
                    "Name and business both missing; identified only by phone"
                )

        # ── Build injection text ──
        context["injection_text"] = self._build_injection_text(context)

        # ── Select script template ──
        if context["context_type"] == "scheduled_callback":
            context["script_template"] = "scheduled_callback"
        elif context["context_type"] == "returning_caller":
            context["script_template"] = "returning_caller"
        elif context["context_type"] == "known_lead":
            context["script_template"] = "partial_context"
        else:
            context["script_template"] = "unknown_caller"

        # ── Log injection ──
        self._injection_log.append({
            "call_id": self._active_call,
            "phone": phone[-4:],  # Last 4 digits only for privacy
            "context_type": context["context_type"],
            "has_name": context["merchant_name"] is not None,
            "has_business": context["business_name"] is not None,
            "prior_calls": len(context["prior_calls"]),
            "timestamp": time.time(),
        })

        self._last_context = context
        logger.info(f"[Organ 29] Context lookup: {context['context_type']} — {len(context['prior_calls'])} prior calls")
        return context

    def get_greeting_script(self, context: Optional[Dict] = None) -> str:
        """Get the appropriate greeting script based on context."""
        ctx = context or self._last_context or {}
        template_key = ctx.get("script_template", "unknown_caller")
        template = INBOUND_SCRIPTS.get(template_key, INBOUND_SCRIPTS["unknown_caller"])

        # Fill template variables
        variables = {
            "merchant_name": ctx.get("merchant_name") or "there",
            "business_name": ctx.get("business_name") or "your business",
            "last_call_date": "",
            "last_topic": "your payment processing",
            "callback_reason": ctx.get("callback_reason") or "your account",
        }

        # Extract date from prior calls
        prior = ctx.get("prior_calls", [])
        if prior:
            variables["last_call_date"] = prior[0].get("date", "recently")
            variables["last_topic"] = prior[0].get("topic", "your account")

        try:
            return template.format(**variables)
        except KeyError:
            return INBOUND_SCRIPTS["unknown_caller"]

    # ─── Data Source Lookups ─────────────────────────────────────────────

    def _lookup_lead(self, phone: str) -> Optional[Dict]:
        """Look up lead by phone in merchant_queue.json."""
        try:
            path = Path(self._lead_queue_path)
            if not path.exists():
                return None

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Handle both list and dict formats
            leads = data if isinstance(data, list) else data.get("leads", [])

            for lead in leads:
                lead_phone = lead.get("phone", "")
                # Normalize: compare last 10 digits
                if lead_phone[-10:] == phone[-10:]:
                    return lead

        except Exception as e:
            logger.warning(f"[Organ 29] Lead lookup failed: {e}")
        return None

    def _lookup_call_history(self, phone: str) -> List[Dict]:
        """Look up prior calls from CDC database."""
        try:
            db_path = Path(self._cdc_db_path)
            if not db_path.exists():
                return []

            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Try to query — table structure may vary
            try:
                cursor.execute(
                    "SELECT * FROM calls WHERE phone LIKE ? ORDER BY timestamp DESC LIMIT ?",
                    (f"%{phone[-10:]}%", MAX_PRIOR_CALLS),
                )
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
            except sqlite3.OperationalError:
                results = []

            conn.close()
            return results

        except Exception as e:
            logger.warning(f"[Organ 29] CDC lookup failed: {e}")
            return []

    def _lookup_callback(self, phone: str) -> Optional[Dict]:
        """Look up scheduled callback from call_log.json."""
        try:
            path = Path(self._call_log_path)
            if not path.exists():
                return None

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            logs = data if isinstance(data, list) else data.get("calls", [])

            for entry in reversed(logs):
                entry_phone = entry.get("phone", "")
                if entry_phone[-10:] == phone[-10:]:
                    if entry.get("callback_requested") or entry.get("scheduled_callback"):
                        return {
                            "reason": entry.get("callback_reason", "follow-up"),
                            "scheduled_time": entry.get("callback_time") or entry.get("scheduled_callback"),
                        }

        except Exception as e:
            logger.warning(f"[Organ 29] Callback lookup failed: {e}")
        return None

    # ─── Context Building ────────────────────────────────────────────────

    def _build_injection_text(self, context: Dict) -> str:
        """Build system prompt injection text from context."""
        parts = []

        if context.get("merchant_name"):
            parts.append(f"Caller name: {context['merchant_name']}")
        if context.get("business_name"):
            parts.append(f"Business: {context['business_name']}")
        if context.get("lead_status"):
            parts.append(f"Lead status: {context['lead_status']}")
        if context.get("callback_reason"):
            parts.append(f"Callback reason: {context['callback_reason']}")
        if context.get("scheduled_callback"):
            parts.append(f"Scheduled callback: {context['scheduled_callback']}")

        prior = context.get("prior_calls", [])
        if prior:
            parts.append(f"Prior calls: {len(prior)}")
            last = prior[0]
            if last.get("summary"):
                parts.append(f"Last call summary: {last['summary']}")

        if context.get("missing_notes"):
            parts.append("Notes: " + "; ".join(context["missing_notes"]))

        if not parts:
            return "No prior context available for this caller."

        return "\n".join(parts)

    # ─── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "organ": "Organ 29 — Inbound Context Injection",
            "version": "4.1.0",
            "iqcore_available": IQCORE_AVAILABLE,
            "active_call": self._active_call,
            "total_lookups": len(self._injection_log),
            "last_context_type": self._last_context.get("context_type") if self._last_context else None,
            "cdc_db_exists": Path(self._cdc_db_path).exists(),
            "lead_queue_exists": Path(self._lead_queue_path).exists(),
        }
