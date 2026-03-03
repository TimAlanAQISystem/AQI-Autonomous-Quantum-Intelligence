"""
Zero-Turn Diagnostics Module
=============================
Classifies 0-turn calls into actionable categories so we can distinguish
carrier-level problems from system problems.

Tim's directive: "a human hang up is the worst possible outcome... never by
timing or issues of any kind associated to the telephone, Twilio or coding or
anything that we have control over."

This module answers: for each 0-turn call, WHY did it have 0 turns?

Categories:
  - INSTANT_HANGUP:    Duration < 2s, no ASR frames — caller hung up immediately
  - NO_AUDIO:          Audio bytes below threshold, no ASR — carrier/network dead air
  - INBOUND_SPAM:      Inbound callback with merchant_name="there" — telephony garbage
  - CARRIER_FILTER:    EAB classified as CARRIER_SPAM_BLOCKER or GOOGLE_CALL_SCREEN
  - VOICEMAIL_ABORT:   EAB classified as voicemail with DROP_AND_ABORT
  - IVR_SILENT:        EAB classified as IVR but no turns captured
  - SENTINEL_KILL:     killed_by=sentinel — watchdog timeout
  - UNKNOWN_ZERO_TURN: None of the above — needs investigation
"""

from dataclasses import dataclass, field
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class ZeroTurnEvent:
    """All available context for a 0-turn call."""
    call_sid: str
    merchant_name: str
    duration_sec: float
    env_class: Optional[str] = None
    eab_action: Optional[str] = None
    killed_by: Optional[str] = None
    asr_frames: int = 0
    audio_bytes: int = 0
    inbound: bool = False
    call_type: Optional[str] = None
    final_outcome: Optional[str] = None


class ZeroTurnDiagnostics:
    """Classifies 0-turn calls into diagnostic categories."""

    MIN_AUDIO_BYTES = 2000   # Below this = effectively no audio
    MIN_ASR_FRAMES = 3       # Below this = no meaningful speech detected

    # Categories ordered by priority (first match wins)
    CATEGORIES = [
        "INSTANT_HANGUP",
        "INBOUND_SPAM",
        "CARRIER_FILTER",
        "VOICEMAIL_ABORT",
        "IVR_SILENT",
        "SENTINEL_KILL",
        "NO_AUDIO",
        "UNKNOWN_ZERO_TURN",
    ]

    @classmethod
    def classify(cls, evt: ZeroTurnEvent) -> str:
        """
        Classify a 0-turn call into a diagnostic category.
        Returns one of the CATEGORIES strings.
        """
        # 1. Instant hangup — caller hung up before anything could happen
        if evt.duration_sec < 2.0 and evt.asr_frames < cls.MIN_ASR_FRAMES:
            return "INSTANT_HANGUP"

        # 2. Inbound "there" spam — telephony garbage callbacks
        if evt.inbound and (evt.merchant_name or '').strip().lower() == "there":
            return "INBOUND_SPAM"

        # 3. Carrier filter — spam blocker or Google Call Screen
        if evt.env_class in ("CARRIER_SPAM_BLOCKER", "GOOGLE_CALL_SCREEN"):
            return "CARRIER_FILTER"
        if evt.call_type and 'spam' in evt.call_type.lower():
            return "CARRIER_FILTER"

        # 4. Voicemail correctly aborted (EAB did the right thing)
        if evt.eab_action == "DROP_AND_ABORT":
            return "VOICEMAIL_ABORT"
        if evt.env_class and 'voicemail' in evt.env_class.lower():
            return "VOICEMAIL_ABORT"

        # 5. IVR with no turns — IVR system but Alan couldn't interact
        if evt.env_class and 'ivr' in evt.env_class.lower():
            return "IVR_SILENT"

        # 6. Sentinel kill — watchdog timeout
        if evt.killed_by == 'sentinel':
            return "SENTINEL_KILL"

        # 7. No audio — dead air / network issue
        if evt.audio_bytes < cls.MIN_AUDIO_BYTES and evt.asr_frames < cls.MIN_ASR_FRAMES:
            return "NO_AUDIO"

        # 8. Unknown — needs investigation
        return "UNKNOWN_ZERO_TURN"

    @classmethod
    def to_dict(cls, evt: ZeroTurnEvent) -> dict:
        """Convert event + classification to a loggable dict."""
        return {
            "call_sid": evt.call_sid,
            "merchant_name": evt.merchant_name,
            "duration_sec": evt.duration_sec,
            "env_class": evt.env_class,
            "eab_action": evt.eab_action,
            "killed_by": evt.killed_by,
            "asr_frames": evt.asr_frames,
            "audio_bytes": evt.audio_bytes,
            "inbound": evt.inbound,
            "call_type": evt.call_type,
            "final_outcome": evt.final_outcome,
            "zero_turn_class": cls.classify(evt),
        }

    @classmethod
    def classify_from_cdc(cls, call_row: dict) -> str:
        """
        Convenience: classify directly from a CDC calls row dict.
        Fills in reasonable defaults for fields not in the calls table.
        """
        evt = ZeroTurnEvent(
            call_sid=call_row.get('call_sid', ''),
            merchant_name=call_row.get('merchant_name', ''),
            duration_sec=call_row.get('duration_seconds', 0) or 0,
            env_class=call_row.get('env_class'),
            eab_action=call_row.get('eab_action'),
            killed_by=call_row.get('killed_by'),
            asr_frames=call_row.get('asr_frames', 0) or 0,
            audio_bytes=call_row.get('audio_bytes', 0) or 0,
            inbound=call_row.get('inbound', False),
            call_type=call_row.get('call_type'),
            final_outcome=call_row.get('final_outcome'),
        )
        return cls.classify(evt)

    @classmethod
    def summarize(cls, events: List[ZeroTurnEvent]) -> dict:
        """
        Summarize a list of zero-turn events into category counts.
        Returns dict like {"INSTANT_HANGUP": 12, "CARRIER_FILTER": 5, ...}
        """
        counts = {cat: 0 for cat in cls.CATEGORIES}
        for evt in events:
            category = cls.classify(evt)
            counts[category] = counts.get(category, 0) + 1
        return {k: v for k, v in counts.items() if v > 0}
