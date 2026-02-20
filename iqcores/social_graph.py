"""
IQCORE 4: SOCIAL GRAPH
========================
Agent X's relationship intelligence engine — manages entities (merchants,
team members, prospects), tracks relationship depth, interaction history,
trust levels, and social context.

This is what makes Agent X remember WHO people are and how to treat them.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class Entity:
    """A person or organization in Agent X's social graph."""

    def __init__(self, entity_id: str, name: str, entity_type: str = "contact"):
        self.entity_id = entity_id
        self.name = name
        self.entity_type = entity_type  # founder, merchant, prospect, team, family, friend
        self.created = datetime.now().isoformat()
        self.last_interaction: Optional[str] = None

        # Relationship metrics
        self.trust_level: float = 0.0          # 0.0 (stranger) → 1.0 (trusted partner)
        self.familiarity: float = 0.0          # 0.0 (unknown) → 1.0 (deeply familiar)
        self.sentiment_history: List[float] = []   # Rolling sentiment readings
        self.interaction_count: int = 0

        # Knowledge about this entity
        self.known_facts: Dict[str, str] = {}   # key → fact
        self.preferences: Dict[str, Any] = {}   # known preferences
        self.topics_discussed: List[str] = []    # topics we've talked about
        self.objections_raised: List[str] = []   # objections they've raised
        self.communication_style: str = "unknown"  # formal, casual, direct, etc.

        # Relationship tags
        self.tags: List[str] = []
        self.notes: List[dict] = []

    def record_interaction(self, interaction_type: str, sentiment: float = 0.5,
                           topics: List[str] = None, notes: str = None):
        """Record an interaction with this entity."""
        self.interaction_count += 1
        self.last_interaction = datetime.now().isoformat()

        # Update sentiment history (keep last 20)
        self.sentiment_history.append(round(sentiment, 2))
        if len(self.sentiment_history) > 20:
            self.sentiment_history = self.sentiment_history[-20:]

        # Update trust level based on interactions
        if self.interaction_count <= 1:
            self.trust_level = 0.1          # First contact
        elif self.interaction_count <= 3:
            self.trust_level = 0.3          # Getting to know
        elif self.interaction_count <= 10:
            self.trust_level = 0.5          # Established contact
        else:
            self.trust_level = min(0.5 + (self.interaction_count - 10) * 0.02, 0.95)

        # Update familiarity
        self.familiarity = min(self.interaction_count * 0.05, 1.0)

        # Track topics
        if topics:
            for topic in topics:
                if topic not in self.topics_discussed:
                    self.topics_discussed.append(topic)

        # Add note
        if notes:
            self.notes.append({
                "timestamp": datetime.now().isoformat(),
                "type": interaction_type,
                "note": notes
            })
            if len(self.notes) > 50:
                self.notes = self.notes[-50:]

    def get_relationship_status(self) -> str:
        """Get human-readable relationship status."""
        if self.trust_level < 0.1:
            return "stranger"
        elif self.trust_level < 0.3:
            return "new_contact"
        elif self.trust_level < 0.5:
            return "acquaintance"
        elif self.trust_level < 0.7:
            return "established_contact"
        elif self.trust_level < 0.9:
            return "trusted_contact"
        else:
            return "trusted_partner"

    def get_average_sentiment(self) -> float:
        """Get average sentiment from history."""
        if not self.sentiment_history:
            return 0.5
        return round(sum(self.sentiment_history) / len(self.sentiment_history), 2)

    def learn_fact(self, key: str, fact: str):
        """Learn a fact about this entity."""
        self.known_facts[key] = fact

    def learn_preference(self, key: str, value: Any):
        """Learn a preference of this entity."""
        self.preferences[key] = value

    def add_objection(self, objection: str):
        """Record an objection this entity has raised."""
        if objection not in self.objections_raised:
            self.objections_raised.append(objection)

    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "trust_level": self.trust_level,
            "familiarity": self.familiarity,
            "relationship_status": self.get_relationship_status(),
            "interaction_count": self.interaction_count,
            "average_sentiment": self.get_average_sentiment(),
            "last_interaction": self.last_interaction,
            "known_facts": self.known_facts,
            "preferences": self.preferences,
            "topics_discussed": self.topics_discussed,
            "objections_raised": self.objections_raised,
            "communication_style": self.communication_style,
            "tags": self.tags,
            "created": self.created
        }


class SocialGraphIQCore:
    """
    IQCore 4 — The Relationship Intelligence Engine.

    Capabilities:
    - Entity management (create, update, query relationships)
    - Trust depth tracking across interactions
    - Interaction history and pattern detection
    - Social context generation for conversations
    - Relationship health monitoring
    - Conversation priming based on known facts/preferences
    - Entity clustering by type, sentiment, engagement
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir
        self.entities: Dict[str, Entity] = {}
        self._interaction_count = 0

        # Pre-seed founder entity
        self._seed_founder()
        logger.info("[IQCORE-4] SocialGraph initialized")

    def _seed_founder(self):
        """Pre-seed the founder entity — Tim Jones."""
        tim = Entity("founder_tim", "Tim Jones", "founder")
        tim.trust_level = 1.0
        tim.familiarity = 1.0
        tim.communication_style = "direct"
        tim.learn_fact("role", "Founder of SCSDMC / AQI")
        tim.learn_fact("location", "Montana")
        tim.learn_fact("work_ethic", "7 months, 11+ hours/day")
        tim.learn_fact("vision", "Relational AI, not transactional")
        tim.learn_fact("philosophy", "Intelligence is relational infrastructure")
        tim.learn_preference("communication", "Direct, no fluff")
        tim.learn_preference("work_style", "Interpret intent, don't ask")
        tim.tags = ["founder", "family", "priority_1"]
        self.entities["founder_tim"] = tim

    # ------------------------------------------------------------------
    # ENTITY MANAGEMENT
    # ------------------------------------------------------------------

    def add_entity(self, entity_id: str, name: str,
                   entity_type: str = "contact",
                   initial_facts: dict = None) -> Entity:
        """Add a new entity to the social graph."""
        if entity_id in self.entities:
            return self.entities[entity_id]

        entity = Entity(entity_id, name, entity_type)
        if initial_facts:
            for key, fact in initial_facts.items():
                entity.learn_fact(key, fact)

        self.entities[entity_id] = entity
        logger.info(f"[IQCORE-4] New entity: {name} ({entity_type})")
        return entity

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)

    def find_entity_by_name(self, name: str) -> Optional[Entity]:
        """Find an entity by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for entity in self.entities.values():
            if name_lower in entity.name.lower():
                return entity
        return None

    def record_interaction(self, entity_id: str, interaction_type: str,
                           sentiment: float = 0.5, topics: List[str] = None,
                           notes: str = None, name: str = None) -> Dict[str, Any]:
        """
        Record an interaction with an entity. Creates the entity if it doesn't exist.
        """
        if entity_id not in self.entities:
            display_name = name or entity_id
            self.add_entity(entity_id, display_name)

        entity = self.entities[entity_id]
        entity.record_interaction(interaction_type, sentiment, topics, notes)
        self._interaction_count += 1

        return {
            "entity": entity.name,
            "interaction_count": entity.interaction_count,
            "trust_level": entity.trust_level,
            "relationship_status": entity.get_relationship_status(),
            "average_sentiment": entity.get_average_sentiment()
        }

    # ------------------------------------------------------------------
    # SOCIAL INTELLIGENCE
    # ------------------------------------------------------------------

    def get_conversation_context(self, entity_id: str) -> Dict[str, Any]:
        """
        Generate social context for a conversation with an entity.
        This gets fed into Alan's prompt to personalize the interaction.
        """
        entity = self.entities.get(entity_id)
        if not entity:
            return {
                "relationship": "stranger",
                "known_facts": {},
                "preferences": {},
                "previous_topics": [],
                "objections": [],
                "approach": "warm_professional"
            }

        # Determine approach based on relationship
        status = entity.get_relationship_status()
        avg_sentiment = entity.get_average_sentiment()

        if status in ("stranger", "new_contact"):
            approach = "warm_professional"
        elif avg_sentiment > 0.7:
            approach = "friendly_familiar"
        elif avg_sentiment < 0.3:
            approach = "careful_empathetic"
        elif entity.interaction_count > 5:
            approach = "established_rapport"
        else:
            approach = "building_rapport"

        return {
            "relationship": status,
            "trust_level": entity.trust_level,
            "interaction_count": entity.interaction_count,
            "known_facts": entity.known_facts,
            "preferences": entity.preferences,
            "previous_topics": entity.topics_discussed[-5:],
            "objections": entity.objections_raised,
            "communication_style": entity.communication_style,
            "average_sentiment": avg_sentiment,
            "approach": approach,
            "last_interaction": entity.last_interaction
        }

    def get_relationship_health(self) -> Dict[str, Any]:
        """Get overall relationship health across all entities."""
        if not self.entities:
            return {"total_entities": 0, "health": "no_data"}

        total = len(self.entities)
        types = defaultdict(int)
        avg_trust = 0.0
        avg_sentiment = 0.0
        active_count = 0

        for entity in self.entities.values():
            types[entity.entity_type] += 1
            avg_trust += entity.trust_level
            avg_sentiment += entity.get_average_sentiment()
            if entity.interaction_count > 0:
                active_count += 1

        return {
            "total_entities": total,
            "active_entities": active_count,
            "entity_types": dict(types),
            "average_trust": round(avg_trust / total, 2),
            "average_sentiment": round(avg_sentiment / total, 2),
            "health": (
                "strong" if avg_trust / total > 0.6 else
                "developing" if avg_trust / total > 0.3 else
                "early_stage"
            )
        }

    def get_entities_by_type(self, entity_type: str) -> List[dict]:
        """Get all entities of a specific type."""
        return [
            e.to_dict() for e in self.entities.values()
            if e.entity_type == entity_type
        ]

    def get_most_engaged(self, limit: int = 5) -> List[dict]:
        """Get the most engaged entities."""
        sorted_entities = sorted(
            self.entities.values(),
            key=lambda e: e.interaction_count,
            reverse=True
        )
        return [e.to_dict() for e in sorted_entities[:limit]]

    def get_entities_needing_attention(self) -> List[dict]:
        """Get entities that haven't been interacted with recently."""
        needing_attention = []
        for entity in self.entities.values():
            if entity.entity_type in ("merchant", "prospect") and \
               entity.interaction_count > 0:
                if entity.last_interaction:
                    try:
                        last = datetime.fromisoformat(entity.last_interaction)
                        days_since = (datetime.now() - last).days
                        if days_since > 7:
                            needing_attention.append({
                                "entity": entity.to_dict(),
                                "days_since_contact": days_since,
                                "priority": "high" if days_since > 14 else "medium"
                            })
                    except (ValueError, TypeError):
                        pass

        return sorted(
            needing_attention,
            key=lambda x: x["days_since_contact"],
            reverse=True
        )

    # ------------------------------------------------------------------
    # SOCIAL GRAPH QUERIES
    # ------------------------------------------------------------------

    def add_friend(self, name: str, entity_id: str = None) -> dict:
        """Add a friend to the social graph."""
        eid = entity_id or f"friend_{name.lower().replace(' ', '_')}"
        entity = self.add_entity(eid, name, "friend")
        entity.trust_level = 0.5
        entity.tags.append("friend")
        return {"added": name, "type": "friend", "entity_id": eid}

    def add_family(self, name: str, relation: str = "family",
                   entity_id: str = None) -> dict:
        """Add a family member to the social graph."""
        eid = entity_id or f"family_{name.lower().replace(' ', '_')}"
        entity = self.add_entity(eid, name, "family")
        entity.trust_level = 0.8
        entity.learn_fact("relation", relation)
        entity.tags.append("family")
        return {"added": name, "type": "family", "relation": relation}

    def add_merchant(self, name: str, company: str = "",
                     phone: str = "", entity_id: str = None) -> dict:
        """Add a merchant/prospect to the social graph."""
        eid = entity_id or f"merchant_{name.lower().replace(' ', '_')}"
        entity = self.add_entity(eid, name, "merchant")
        if company:
            entity.learn_fact("company", company)
        if phone:
            entity.learn_fact("phone", phone)
        entity.tags.append("merchant")
        return {"added": name, "type": "merchant", "company": company}

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        types = defaultdict(int)
        for e in self.entities.values():
            types[e.entity_type] += 1

        return {
            "core": "SocialGraph",
            "core_number": 4,
            "total_entities": len(self.entities),
            "total_interactions": self._interaction_count,
            "entity_types": dict(types),
            "relationship_health": self.get_relationship_health()["health"],
            "status": "ACTIVE"
        }
