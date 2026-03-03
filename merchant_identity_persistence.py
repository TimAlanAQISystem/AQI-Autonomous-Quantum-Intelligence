"""
Merchant Identity Persistence (MIP)
Alan's social memory - cross-call relationship continuity
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MerchantProfile(BaseModel):
    merchant_id: str
    business_name: Optional[str] = None
    phone_number: str
    last_contact: Optional[datetime] = None

    # Behavioral memory
    archetype_history: List[Dict[str, Any]] = []
    objection_history: List[str] = []
    trajectory_patterns: List[Dict[str, Any]] = []
    rapport_level: float = 0.5  # 0.0-1.0

    # Risk & compliance
    risk_flags: List[str] = []

    # Preferences (legacy — simple fields)
    preferred_pacing: Optional[str] = None
    preferred_tone: Optional[str] = None

    # [PERSISTENCE PILLAR] Detected Preferences — full communication style learned per-call
    # Persisted from MerchantPreferences at call end, restored at call start.
    # Decays toward defaults if not reinforced within 90 days.
    detected_preferences: Dict[str, Any] = {}

    # [PERSISTENCE PILLAR] Call Memories — tactical memory from MasterCloser
    # Last N call snapshots: key_points, objections (with strength), agreements, goals.
    # Bounded to MAX_CALL_MEMORIES (3) — oldest evicted on overflow.
    call_memories: List[Dict[str, Any]] = []

    # [PERSISTENCE PILLAR] Conversation Summaries — per-merchant turn history
    # Last N conversations (agent/user turns) so Alan never cross-contaminates merchants.
    # Bounded to MAX_CONVERSATION_SUMMARIES (2) — oldest evicted on overflow.
    conversation_summaries: List[Dict[str, Any]] = []

    # Outcomes
    call_outcomes: List[Dict[str, Any]] = []

    # Follow-up logic
    callback_commitments: List[Dict[str, Any]] = []

    # Flags
    do_not_contact: bool = False
    do_not_store_profile: bool = False


class MerchantIdentityPersistence:
    """
    Cross-call memory system for merchant relationships.
    NOT transcript storage - tendency and pattern storage.
    """

    # Constants
    MAX_CALL_MEMORIES = 3
    MAX_CONVERSATION_SUMMARIES = 2
    MAX_CONVERSATION_TURNS = 20  # Per summary
    PREFERENCE_DECAY_DAYS = 90

    def __init__(self, db_path: str = "merchant_profiles.json"):
        self.db_path = db_path
        self.logger = logging.getLogger("MIP")
        self.profiles = self._load_profiles()

    def _load_profiles(self) -> Dict[str, MerchantProfile]:
        """Load profiles from disk"""
        try:
            with open(self.db_path, "r") as f:
                data = json.load(f)
                return {k: MerchantProfile(**v) for k, v in data.items()}
        except FileNotFoundError:
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load profiles: {e}")
            return {}

    def _save_profiles(self):
        """Persist profiles to disk"""
        try:
            data = {k: v.dict() for k, v in self.profiles.items()}
            with open(self.db_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save profiles: {e}")

    def resolve_merchant_id(self, phone_number: str, business_name: Optional[str] = None) -> str:
        """
        Deterministic merchant identification.
        Priority: phone number (simple for now)
        """
        # In production, would do fuzzy matching on business name
        return phone_number

    def load_profile(self, merchant_id: str) -> MerchantProfile:
        """Load or create merchant profile"""
        if merchant_id in self.profiles:
            return self.profiles[merchant_id]

        # Create new profile
        profile = MerchantProfile(
            merchant_id=merchant_id,
            phone_number=merchant_id  # Simple mapping for now
        )
        self.profiles[merchant_id] = profile
        return profile

    def update_profile_from_call(self, merchant_id: str, call_data: Dict[str, Any]):
        """Update profile with call results — full persistence of all memory systems."""
        profile = self.load_profile(merchant_id)

        # Check flags
        if profile.do_not_store_profile:
            self.logger.info(f"Skipping profile update for {merchant_id} (do_not_store_profile)")
            return

        profile.last_contact = datetime.utcnow()

        # Archetype
        if call_data.get("archetype"):
            profile.archetype_history.append({
                "type": call_data["archetype"],
                "confidence": call_data.get("archetype_confidence", 0.5),
                "timestamp": datetime.utcnow().isoformat()
            })
            # Keep bounded
            profile.archetype_history = profile.archetype_history[-10:]

        # Objections (keep last 5)
        if call_data.get("objection"):
            profile.objection_history.append(call_data["objection"])
            profile.objection_history = profile.objection_history[-5:]

        # Trajectory patterns
        if call_data.get("trajectory"):
            profile.trajectory_patterns.append({
                "trajectory": call_data["trajectory"],
                "success": call_data.get("outcome") in ["statement_obtained", "kept_engaged"],
                "timestamp": datetime.utcnow().isoformat()
            })
            profile.trajectory_patterns = profile.trajectory_patterns[-10:]

        # Rapport
        if "rapport_delta" in call_data:
            profile.rapport_level = max(0.0, min(1.0, profile.rapport_level + call_data["rapport_delta"]))

        # Risk flags
        if call_data.get("risk_flag"):
            if call_data["risk_flag"] not in profile.risk_flags:
                profile.risk_flags.append(call_data["risk_flag"])

        # Outcomes
        if call_data.get("outcome"):
            profile.call_outcomes.append({
                "outcome": call_data["outcome"],
                "confidence": call_data.get("confidence", 0.5),
                "timestamp": datetime.utcnow().isoformat()
            })
            profile.call_outcomes = profile.call_outcomes[-10:]

        # Callbacks
        if call_data.get("callback"):
            profile.callback_commitments.append(call_data["callback"])

        # [PERSISTENCE PILLAR] CallMemory snapshot
        if call_data.get("call_memory"):
            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                **call_data["call_memory"]
            }
            profile.call_memories.append(snapshot)
            profile.call_memories = profile.call_memories[-self.MAX_CALL_MEMORIES:]
            self.logger.info(f"[MIP] Persisted CallMemory for {merchant_id} ({len(profile.call_memories)} stored)")

        # [PERSISTENCE PILLAR] MerchantPreferences
        if call_data.get("preferences"):
            profile.detected_preferences = call_data["preferences"]
            # Also update legacy fields for backward compat
            profile.preferred_pacing = call_data["preferences"].get("pacing")
            profile.preferred_tone = call_data["preferences"].get("formality")
            self.logger.info(f"[MIP] Persisted preferences for {merchant_id}")

        # [PERSISTENCE PILLAR] Conversation summary (last N turns of this call)
        if call_data.get("conversation_turns"):
            turns = call_data["conversation_turns"][-self.MAX_CONVERSATION_TURNS:]
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "turn_count": len(turns),
                "turns": turns
            }
            profile.conversation_summaries.append(summary)
            profile.conversation_summaries = profile.conversation_summaries[-self.MAX_CONVERSATION_SUMMARIES:]
            self.logger.info(f"[MIP] Persisted {len(turns)} conversation turns for {merchant_id}")

        # Save
        self._save_profiles()

    def seed_context_from_profile(self, profile: MerchantProfile) -> Dict[str, Any]:
        """Generate context dict for BAL/MTSP/etc from profile — full memory restoration."""
        context = {
            "is_returning": len(profile.call_outcomes) > 0,
            "rapport_level": profile.rapport_level,
            "risk_flags": profile.risk_flags,
            "preferred_pacing": profile.preferred_pacing,
            "preferred_tone": profile.preferred_tone,
            "last_objections": profile.objection_history[-3:] if profile.objection_history else [],
            "archetype_hint": profile.archetype_history[-1]["type"] if profile.archetype_history else None,
        }

        # [PERSISTENCE PILLAR] Restore detected preferences
        if profile.detected_preferences:
            # Check for staleness (decay after PREFERENCE_DECAY_DAYS)
            if profile.last_contact:
                try:
                    last_contact = profile.last_contact
                    if isinstance(last_contact, str):
                        last_contact = datetime.fromisoformat(last_contact)
                    days_since = (datetime.utcnow() - last_contact).days
                    if days_since <= self.PREFERENCE_DECAY_DAYS:
                        context["restored_preferences"] = profile.detected_preferences
                        self.logger.info(f"[MIP] Restored preferences (last contact {days_since}d ago)")
                    else:
                        self.logger.info(f"[MIP] Preferences decayed ({days_since}d > {self.PREFERENCE_DECAY_DAYS}d) — starting fresh")
                except Exception:
                    context["restored_preferences"] = profile.detected_preferences
            else:
                context["restored_preferences"] = profile.detected_preferences

        # [PERSISTENCE PILLAR] Restore last CallMemory for continuity
        if profile.call_memories:
            context["previous_call_memories"] = profile.call_memories
            self.logger.info(f"[MIP] Restored {len(profile.call_memories)} previous call memories")

        # [PERSISTENCE PILLAR] Restore conversation history (per-merchant)
        if profile.conversation_summaries:
            context["previous_conversations"] = profile.conversation_summaries
            self.logger.info(f"[MIP] Restored {len(profile.conversation_summaries)} previous conversations")

        return context

    def purge_merchant_data(self, merchant_id: str, reason: str):
        """GDPR/compliance purge"""
        if merchant_id in self.profiles:
            del self.profiles[merchant_id]
            self._save_profiles()
            self.logger.info(f"Purged merchant {merchant_id}: {reason}")
