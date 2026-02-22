"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           ORGAN 32 — CALL SUMMARIZATION ENGINE                               ║
║                                                                              ║
║  Turn every call into a structured, machine- and human-readable record.      ║
║  Runs once per call at call_end. Produces canonical JSON summary with        ║
║  deal readiness scoring, objection inventory, key quotes, and                ║
║  follow-up recommendations.                                                  ║
║                                                                              ║
║  Constitutional Guarantees:                                                  ║
║    - Summaries must be factual (grounded in transcript)                      ║
║    - No hallucinated quotes or data                                          ║
║    - "Insert if missing" rules for name/email/business                       ║
║    - All summaries persisted to CDC                                          ║
║    - Deal readiness score is algorithmic, not LLM-guessed                    ║
║                                                                              ║
║  RRG: Section 42                                                             ║
║  Author: Agent X / v4.1                                                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import re
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

logger = logging.getLogger("organ_32_summarization")

# ─── Constants ───────────────────────────────────────────────────────────────

INTEREST_LEVELS = ["none", "low", "medium", "high"]

# Keywords for interest level detection
INTEREST_SIGNALS = {
    "high": ["yes", "let's do it", "sign me up", "sounds great", "I'm interested",
             "let's move forward", "when can we start", "send me the paperwork",
             "I'm ready", "absolutely"],
    "medium": ["maybe", "could work", "tell me more", "what's the price",
               "how does it work", "I might be", "possibly", "not bad"],
    "low": ["I don't know", "not sure", "I'll think about it", "not right now",
            "maybe later", "send info", "I'll call you back"],
    "none": ["not interested", "no thanks", "don't call", "remove me",
             "stop calling", "I already have", "no"],
}

# Objection keyword patterns
OBJECTION_PATTERNS = [
    "too expensive", "too much", "can't afford", "not in the budget",
    "already have", "under contract", "happy with", "don't need",
    "not interested", "bad timing", "too busy", "need to think",
    "talk to partner", "talk to my", "let me check", "call back later",
]

# Deal readiness scoring weights
READINESS_WEIGHTS = {
    "interest_high": 30,
    "interest_medium": 15,
    "interest_low": 5,
    "no_objections": 20,
    "few_objections": 10,
    "callback_requested": 15,
    "asked_pricing": 10,
    "long_call": 10,  # > 3 minutes
}

SUMMARY_STORE = "data/call_summaries.json"


class SummarizationOrgan:
    """
    Organ 32: Generates structured call summaries.
    IQcore cost: 2 at call end.
    """

    def __init__(self, store_path: Optional[str] = None):
        self._store_path = store_path or SUMMARY_STORE
        self._summaries: List[Dict] = []
        self._active_call: Optional[str] = None
        self._transcript_buffer: List[Dict] = []
        self._objection_events: List[str] = []
        self._tone_timeline: List[Dict] = []
        self._retrieval_hits: List[Dict] = []
        self._competitive_intel_used: List[str] = []
        self._call_metadata: Dict = {}
        self._load_summaries()
        logger.info("[Organ 32] SummarizationOrgan initialized")

    # ─── Lifecycle ───────────────────────────────────────────────────────

    def start_call(self, call_id: str, metadata: Optional[Dict] = None) -> None:
        self._active_call = call_id
        self._transcript_buffer = []
        self._objection_events = []
        self._tone_timeline = []
        self._retrieval_hits = []
        self._competitive_intel_used = []
        self._call_metadata = metadata or {}
        self._call_metadata["call_start"] = time.time()
        logger.info(f"[Organ 32] Call started: {call_id}")

    def end_call(self) -> Dict[str, Any]:
        stats = {
            "call_id": self._active_call,
            "transcript_turns": len(self._transcript_buffer),
            "summary_generated": False,
        }
        self._active_call = None
        return stats

    # ─── Data Collection (mid-call feeds) ────────────────────────────────

    def add_transcript_turn(self, speaker: str, text: str) -> None:
        """Add a transcript turn (called during the call)."""
        self._transcript_buffer.append({
            "speaker": speaker,
            "text": text,
            "timestamp": time.time(),
        })

    def add_objection_event(self, objection: str) -> None:
        """Record an objection event from Organ 06 or Organ 31."""
        self._objection_events.append(objection)

    def add_tone_event(self, tone_data: Dict) -> None:
        """Record a tone analysis result from Organ 30."""
        self._tone_timeline.append(tone_data)

    def add_retrieval_hit(self, retrieval_data: Dict) -> None:
        """Record a RAG retrieval hit from Organ 24."""
        self._retrieval_hits.append(retrieval_data)

    def add_competitive_intel(self, competitor: str) -> None:
        """Record competitive intel usage from Organ 34."""
        if competitor not in self._competitive_intel_used:
            self._competitive_intel_used.append(competitor)

    # ─── Core Summarization ──────────────────────────────────────────────

    @iqcore_cost("Alan", 2)
    def generate_summary(
        self,
        merchant_name: Optional[str] = None,
        merchant_email: Optional[str] = None,
        merchant_phone: Optional[str] = None,
        business_name: Optional[str] = None,
        current_processor: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate the canonical call summary JSON.

        Insert-if-missing rules:
        - merchant_name not confident → "Unknown", flagged in notes
        - merchant_email missing + follow-up requested → null, flagged
        - business_name inferred from greeting → included with confidence note
        """
        call_duration = time.time() - self._call_metadata.get("call_start", time.time())
        full_transcript = " ".join(t["text"] for t in self._transcript_buffer)

        # ── Insert-if-missing rules ──
        notes_parts = []

        if not merchant_name:
            merchant_name = "Unknown"
            notes_parts.append("Name not captured; set to 'Unknown'.")

        if not merchant_email:
            # Check if follow-up was requested
            callback_requested = self._detect_callback_request(full_transcript)
            if callback_requested:
                notes_parts.append(
                    "Missing email; follow-up impossible without manual enrichment."
                )

        if not business_name:
            # Try to infer from transcript
            inferred = self._infer_business_name(full_transcript)
            if inferred:
                business_name = inferred
                notes_parts.append(
                    f"Business name inferred from greeting: '{inferred}' (low confidence)."
                )

        # ── Extract data from transcript ──
        interest_level = self._detect_interest_level(full_transcript)
        primary_objection, secondary_objections = self._extract_objections(full_transcript)
        callback_requested = self._detect_callback_request(full_transcript)
        callback_time = self._extract_callback_time(full_transcript)
        key_quotes = self._extract_key_quotes(full_transcript)
        deal_readiness = self._compute_deal_readiness(
            interest_level, len(secondary_objections) + (1 if primary_objection else 0),
            callback_requested, call_duration, full_transcript
        )

        # ── Build canonical summary ──
        summary = {
            "call_id": self._active_call or self._call_metadata.get("call_id"),
            "merchant_name": merchant_name,
            "merchant_email": merchant_email,
            "merchant_phone": merchant_phone,
            "business_name": business_name,
            "current_processor": current_processor,
            "expressed_interest_level": interest_level,
            "primary_objection": primary_objection,
            "secondary_objections": secondary_objections,
            "callback_requested": callback_requested,
            "callback_time": callback_time,
            "deal_readiness_score": deal_readiness,
            "key_quotes": key_quotes,
            "used_competitor": self._competitive_intel_used[0] if self._competitive_intel_used else None,
            "used_retrieval": len(self._retrieval_hits) > 0,
            "notes": " ".join(notes_parts) if notes_parts else "",
            "duration_seconds": round(call_duration, 1),
            "transcript_turns": len(self._transcript_buffer),
            "objection_events": len(self._objection_events),
            "tone_frames": len(self._tone_timeline),
            "outcome": outcome,
            "generated_at": time.time(),
        }

        # ── Persist ──
        self._summaries.append(summary)
        self._save_summaries()

        logger.info(f"[Organ 32] Summary generated: readiness={deal_readiness}, interest={interest_level}")
        return summary

    # ─── Extraction Helpers ──────────────────────────────────────────────

    def _detect_interest_level(self, transcript: str) -> str:
        """Detect interest level from transcript keywords."""
        transcript_lower = transcript.lower()
        scores = {level: 0 for level in INTEREST_LEVELS}

        for level, keywords in INTEREST_SIGNALS.items():
            for kw in keywords:
                if kw in transcript_lower:
                    scores[level] += 1

        # Highest score wins
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "low"  # Default to low if nothing detected
        return best

    def _extract_objections(self, transcript: str) -> tuple:
        """Extract primary and secondary objections."""
        transcript_lower = transcript.lower()
        found = []
        for pattern in OBJECTION_PATTERNS:
            if pattern in transcript_lower:
                found.append(pattern)

        # Also include Organ 06/31 events
        for obj in self._objection_events:
            if obj not in found:
                found.append(obj)

        primary = found[0] if found else None
        secondary = found[1:] if len(found) > 1 else []
        return primary, secondary

    def _detect_callback_request(self, transcript: str) -> bool:
        """Detect if merchant requested a callback."""
        callback_phrases = [
            "call me back", "call back", "try again", "call later",
            "tomorrow", "next week", "another time",
        ]
        transcript_lower = transcript.lower()
        return any(phrase in transcript_lower for phrase in callback_phrases)

    def _extract_callback_time(self, transcript: str) -> Optional[str]:
        """Try to extract callback time from transcript."""
        time_patterns = [
            r"(?:call|back|tomorrow|next)\s+(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))",
            r"(tomorrow|next week|monday|tuesday|wednesday|thursday|friday)",
        ]
        for pattern in time_patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _extract_key_quotes(self, transcript: str, max_quotes: int = 3) -> List[str]:
        """Extract notable direct quotes from merchant speech."""
        quotes = []
        for turn in self._transcript_buffer:
            if turn["speaker"].lower() in ("merchant", "caller", "customer"):
                text = turn["text"].strip()
                # Keep meaningful quotes (>20 chars, <200 chars)
                if 20 < len(text) < 200:
                    quotes.append(text)

        return quotes[:max_quotes]

    def _infer_business_name(self, transcript: str) -> Optional[str]:
        """Try to infer business name from greeting patterns."""
        patterns = [
            r"(?:this is|you've reached|welcome to|calling from)\s+([A-Z][a-z]+(?:'s)?\s+[A-Z][a-z]+)",
            r"([A-Z][a-z]+(?:'s)?\s+(?:Pizza|Deli|Market|Shop|Store|Restaurant|Salon|Auto|Bar|Grill|Cafe))",
        ]
        for pattern in patterns:
            match = re.search(pattern, transcript)
            if match:
                return match.group(1)
        return None

    def _compute_deal_readiness(
        self, interest: str, objection_count: int,
        callback: bool, duration: float, transcript: str,
    ) -> int:
        """Compute deal readiness score (0-100)."""
        score = 0

        if interest == "high":
            score += READINESS_WEIGHTS["interest_high"]
        elif interest == "medium":
            score += READINESS_WEIGHTS["interest_medium"]
        elif interest == "low":
            score += READINESS_WEIGHTS["interest_low"]

        if objection_count == 0:
            score += READINESS_WEIGHTS["no_objections"]
        elif objection_count <= 2:
            score += READINESS_WEIGHTS["few_objections"]

        if callback:
            score += READINESS_WEIGHTS["callback_requested"]

        if "price" in transcript.lower() or "cost" in transcript.lower():
            score += READINESS_WEIGHTS["asked_pricing"]

        if duration > 180:  # > 3 minutes
            score += READINESS_WEIGHTS["long_call"]

        return min(score, 100)

    # ─── Access ──────────────────────────────────────────────────────────

    def get_summary(self, call_id: str) -> Optional[Dict]:
        """Get summary for a specific call."""
        for s in reversed(self._summaries):
            if s.get("call_id") == call_id:
                return s
        return None

    def get_recent_summaries(self, count: int = 10) -> List[Dict]:
        """Get most recent summaries."""
        return self._summaries[-count:]

    # ─── Persistence ─────────────────────────────────────────────────────

    def _load_summaries(self) -> None:
        try:
            path = Path(self._store_path)
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._summaries = json.load(f)
        except Exception as e:
            logger.warning(f"[Organ 32] Failed to load summaries: {e}")
            self._summaries = []

    def _save_summaries(self) -> None:
        try:
            path = Path(self._store_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._summaries, f, indent=2)
        except Exception as e:
            logger.warning(f"[Organ 32] Failed to save summaries: {e}")

    # ─── Status ──────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "organ": "Organ 32 — Call Summarization",
            "version": "4.1.0",
            "iqcore_available": IQCORE_AVAILABLE,
            "active_call": self._active_call,
            "total_summaries": len(self._summaries),
            "transcript_turns_buffered": len(self._transcript_buffer),
            "objection_events_buffered": len(self._objection_events),
            "tone_frames_buffered": len(self._tone_timeline),
        }
