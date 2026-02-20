"""
IQCORE 3: LEARNING THREAD
============================
Agent X's adaptive learning engine — learns from call outcomes, merchant
interactions, strategy effectiveness, and temporal patterns. Feeds
intelligence back to improve future performance.

This is what makes Agent X get BETTER over time, not just repeat.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class LearningRecord:
    """A single learning record from an observed interaction."""

    def __init__(self, event_type: str, input_data: dict,
                 outcome: str, effectiveness: float):
        self.timestamp = datetime.now().isoformat()
        self.event_type = event_type
        self.input_data = input_data
        self.outcome = outcome
        self.effectiveness = round(min(max(effectiveness, 0.0), 1.0), 2)
        self.tags: List[str] = []

    def tag(self, label: str):
        if label not in self.tags:
            self.tags.append(label)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "input_data": self.input_data,
            "outcome": self.outcome,
            "effectiveness": self.effectiveness,
            "tags": self.tags
        }


class LearningThreadIQCore:
    """
    IQCore 3 — The Learning Engine.

    Capabilities:
    - Call outcome learning (what words/approaches lead to success)
    - Merchant behavior model building over time
    - Strategy effectiveness scoring and ranking
    - Temporal pattern detection (best times, days, seasons)
    - Off-topic engagement learning (which topics build rapport vs lose them)
    - Feedback loop integration for continuous improvement
    - Lesson extraction from failures
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir
        self.learning_records: List[LearningRecord] = []
        self.strategy_scores: Dict[str, Dict[str, Any]] = {}
        self.behavior_models: Dict[str, Dict[str, Any]] = {}
        self.temporal_patterns: Dict[str, List[float]] = defaultdict(list)
        self.lessons_learned: List[dict] = []
        self.off_topic_effectiveness: Dict[str, Dict[str, float]] = {}
        self._learn_count = 0
        self._max_records = 1000

        # Initialize strategy tracking
        self._init_strategy_tracking()
        logger.info("[IQCORE-3] LearningThread initialized")

    def _init_strategy_tracking(self):
        """Initialize known strategy tracking."""
        strategies = [
            "warm_greeting", "direct_approach", "consultative",
            "empathy_first", "value_proposition", "referral_mention",
            "urgency_frame", "curiosity_hook", "pain_point_probe",
            "savings_lead", "relationship_build", "quick_pitch"
        ]
        for strategy in strategies:
            if strategy not in self.strategy_scores:
                self.strategy_scores[strategy] = {
                    "attempts": 0,
                    "successes": 0,
                    "effectiveness": 0.5,  # Start neutral
                    "last_used": None,
                    "best_context": None
                }

    # ------------------------------------------------------------------
    # PRIMARY LEARNING INTERFACE
    # ------------------------------------------------------------------

    def learn(self, event_type: str, input_data: dict, outcome: str,
              effectiveness: float = 0.5, tags: List[str] = None) -> Dict[str, Any]:
        """
        Primary learning entry point. Records an observation and extracts patterns.

        Args:
            event_type: Type of event (call_outcome, off_topic_response, strategy_used, etc.)
            input_data: The input conditions/context
            outcome: What happened (success, failure, partial, etc.)
            effectiveness: 0.0 to 1.0 score
            tags: Optional labels for categorization

        Returns:
            Learning result with extracted insights
        """
        record = LearningRecord(event_type, input_data, outcome, effectiveness)
        if tags:
            for tag in tags:
                record.tag(tag)

        self.learning_records.append(record)
        self._learn_count += 1
        self._trim_records()

        # Extract insights based on event type
        insights = []

        if event_type == "call_outcome":
            insights.extend(self._learn_from_call(input_data, outcome, effectiveness))
        elif event_type == "strategy_used":
            insights.extend(self._learn_strategy(input_data, outcome, effectiveness))
        elif event_type == "off_topic_response":
            insights.extend(self._learn_off_topic(input_data, outcome, effectiveness))
        elif event_type == "merchant_behavior":
            insights.extend(self._learn_merchant_behavior(input_data, outcome, effectiveness))

        # Temporal learning for all events
        self._learn_temporal(event_type, effectiveness)

        # Check if we've learned enough to extract a lesson
        lesson = self._check_for_lesson(event_type)
        if lesson:
            insights.append(f"NEW LESSON: {lesson['lesson']}")

        logger.info(f"[IQCORE-3] Learned from {event_type}: {outcome} (eff={effectiveness})")

        return {
            "learned": True,
            "event_type": event_type,
            "record_id": self._learn_count,
            "insights": insights,
            "total_records": len(self.learning_records)
        }

    def get_best_strategy(self, context: dict = None) -> Tuple[str, float]:
        """
        Returns the highest-performing strategy based on historical data.
        Optionally considers context for better recommendations.
        """
        if not self.strategy_scores:
            return "warm_greeting", 0.5

        # Score strategies
        scores = {}
        for strategy, data in self.strategy_scores.items():
            if data["attempts"] == 0:
                scores[strategy] = 0.5  # No data, neutral
                continue

            base_score = data["effectiveness"]

            # Recency bonus — strategies used recently get slight boost
            if data["last_used"]:
                try:
                    last = datetime.fromisoformat(data["last_used"])
                    days_ago = (datetime.now() - last).days
                    if days_ago < 7:
                        base_score += 0.05
                except (ValueError, TypeError):
                    pass

            # Context matching bonus
            if context and data.get("best_context"):
                context_match = sum(
                    1 for k, v in data["best_context"].items()
                    if context.get(k) == v
                )
                if context_match > 0:
                    base_score += 0.1 * context_match

            scores[strategy] = min(base_score, 1.0)

        best = max(scores, key=scores.get)
        return best, round(scores[best], 2)

    def get_merchant_model(self, merchant_id: str) -> Dict[str, Any]:
        """Get the behavioral model for a specific merchant."""
        return self.behavior_models.get(merchant_id, {
            "interaction_count": 0,
            "responsiveness": "unknown",
            "preferred_topics": [],
            "objection_patterns": [],
            "best_time": None,
            "sentiment_trend": "neutral",
            "engagement_level": 0.5
        })

    def get_temporal_insight(self) -> Dict[str, Any]:
        """Get timing-related insights from learning data."""
        result = {}

        for event_type, scores in self.temporal_patterns.items():
            if len(scores) < 3:
                continue

            avg = sum(scores) / len(scores)
            trend = "stable"
            if len(scores) >= 5:
                recent = sum(scores[-3:]) / 3
                older = sum(scores[:3]) / 3
                if recent > older + 0.1:
                    trend = "improving"
                elif recent < older - 0.1:
                    trend = "declining"

            result[event_type] = {
                "average_effectiveness": round(avg, 2),
                "trend": trend,
                "sample_size": len(scores)
            }

        return result

    def get_off_topic_intelligence(self) -> Dict[str, Any]:
        """
        Returns learned intelligence about off-topic handling.
        Which categories build rapport vs which ones lose prospects.
        """
        intelligence = {}

        for category, data in self.off_topic_effectiveness.items():
            attempts = data.get("attempts", 0)
            if attempts == 0:
                continue

            avg_eff = data.get("total_effectiveness", 0) / attempts
            intelligence[category] = {
                "attempts": attempts,
                "average_effectiveness": round(avg_eff, 2),
                "recommendation": (
                    "ENGAGE — builds rapport"
                    if avg_eff > 0.6
                    else "BRIEF ENGAGE — neutral impact"
                    if avg_eff > 0.4
                    else "QUICK BRIDGE — tends to lose them"
                )
            }

        return intelligence

    # ------------------------------------------------------------------
    # INTERNAL LEARNING METHODS
    # ------------------------------------------------------------------

    def _learn_from_call(self, input_data: dict, outcome: str,
                         effectiveness: float) -> List[str]:
        """Extract insights from a call outcome."""
        insights = []

        # Duration insight
        duration = input_data.get("call_duration_seconds", 0)
        if duration > 300 and effectiveness > 0.7:
            insights.append("Longer calls (5+ min) correlate with higher effectiveness")
        elif duration < 30 and effectiveness < 0.3:
            insights.append("Very short calls (<30s) rarely succeed — improve hook")

        # Merchant type insight
        merchant_type = input_data.get("merchant_type", "unknown")
        if merchant_type != "unknown":
            key = f"merchant_type_{merchant_type}"
            if key not in self.behavior_models:
                self.behavior_models[key] = {
                    "total_calls": 0,
                    "avg_effectiveness": 0.5,
                    "outcomes": []
                }
            model = self.behavior_models[key]
            model["total_calls"] += 1
            total = model["total_calls"]
            model["avg_effectiveness"] = (
                (model["avg_effectiveness"] * (total - 1) + effectiveness) / total
            )
            model["outcomes"].append(outcome)
            if len(model["outcomes"]) > 50:
                model["outcomes"] = model["outcomes"][-50:]

        return insights

    def _learn_strategy(self, input_data: dict, outcome: str,
                        effectiveness: float) -> List[str]:
        """Learn from a strategy application."""
        insights = []
        strategy_name = input_data.get("strategy", "unknown")

        if strategy_name in self.strategy_scores:
            data = self.strategy_scores[strategy_name]
            data["attempts"] += 1

            # Running average
            total = data["attempts"]
            data["effectiveness"] = round(
                (data["effectiveness"] * (total - 1) + effectiveness) / total, 2
            )
            data["last_used"] = datetime.now().isoformat()

            if effectiveness > 0.7:
                data["successes"] += 1
                data["best_context"] = input_data.get("context", {})
                insights.append(
                    f"Strategy '{strategy_name}' succeeded (eff={effectiveness}) — "
                    f"overall rate: {data['effectiveness']}"
                )

            if data["attempts"] >= 5 and data["effectiveness"] < 0.3:
                insights.append(
                    f"WARNING: Strategy '{strategy_name}' consistently underperforming "
                    f"({data['effectiveness']} avg over {data['attempts']} attempts)"
                )

        return insights

    def _learn_off_topic(self, input_data: dict, outcome: str,
                         effectiveness: float) -> List[str]:
        """Learn from off-topic conversation handling."""
        insights = []
        category = input_data.get("category", "unknown")

        if category not in self.off_topic_effectiveness:
            self.off_topic_effectiveness[category] = {
                "attempts": 0,
                "total_effectiveness": 0.0
            }

        data = self.off_topic_effectiveness[category]
        data["attempts"] += 1
        data["total_effectiveness"] += effectiveness

        avg = data["total_effectiveness"] / data["attempts"]

        if data["attempts"] >= 3:
            if avg > 0.7:
                insights.append(
                    f"Off-topic '{category}' is a RAPPORT BUILDER — "
                    f"avg effectiveness {avg:.2f}"
                )
            elif avg < 0.3:
                insights.append(
                    f"Off-topic '{category}' LOSES prospects — "
                    f"avg effectiveness {avg:.2f}. Bridge faster."
                )

        return insights

    def _learn_merchant_behavior(self, input_data: dict, outcome: str,
                                  effectiveness: float) -> List[str]:
        """Build behavioral model for a specific merchant."""
        insights = []
        merchant_id = input_data.get("merchant_id", "unknown")

        if merchant_id not in self.behavior_models:
            self.behavior_models[merchant_id] = {
                "interaction_count": 0,
                "responsiveness": "unknown",
                "preferred_topics": [],
                "objection_patterns": [],
                "best_time": None,
                "sentiment_trend": "neutral",
                "engagement_level": 0.5
            }

        model = self.behavior_models[merchant_id]
        model["interaction_count"] += 1

        # Update engagement level
        count = model["interaction_count"]
        model["engagement_level"] = round(
            (model["engagement_level"] * (count - 1) + effectiveness) / count, 2
        )

        # Track objection patterns
        objections = input_data.get("objections", [])
        for obj in objections:
            if obj not in model["objection_patterns"]:
                model["objection_patterns"].append(obj)

        # Track preferred topics
        topics = input_data.get("engaged_topics", [])
        for topic in topics:
            if topic not in model["preferred_topics"]:
                model["preferred_topics"].append(topic)

        if count >= 3 and model["engagement_level"] > 0.7:
            insights.append(
                f"Merchant '{merchant_id}' is highly engaged "
                f"(level={model['engagement_level']})"
            )

        return insights

    def _learn_temporal(self, event_type: str, effectiveness: float):
        """Track temporal patterns."""
        self.temporal_patterns[event_type].append(effectiveness)
        if len(self.temporal_patterns[event_type]) > 200:
            self.temporal_patterns[event_type] = \
                self.temporal_patterns[event_type][-200:]

    def _check_for_lesson(self, event_type: str) -> Optional[dict]:
        """Check if accumulated data yields a new lesson."""
        # Need at least 10 records of same type to extract a lesson
        type_records = [
            r for r in self.learning_records if r.event_type == event_type
        ]
        if len(type_records) < 10:
            return None

        # Check if we already have a lesson for this count threshold
        threshold = (len(type_records) // 10) * 10
        existing = [
            l for l in self.lessons_learned
            if l.get("event_type") == event_type and l.get("threshold") == threshold
        ]
        if existing:
            return None

        # Extract lesson
        recent = type_records[-10:]
        avg_eff = sum(r.effectiveness for r in recent) / 10
        outcomes = [r.outcome for r in recent]
        most_common_outcome = max(set(outcomes), key=outcomes.count)

        lesson = {
            "event_type": event_type,
            "threshold": threshold,
            "lesson": (
                f"After {threshold} '{event_type}' events: "
                f"avg effectiveness={avg_eff:.2f}, "
                f"most common outcome='{most_common_outcome}'"
            ),
            "average_effectiveness": round(avg_eff, 2),
            "sample_size": threshold,
            "extracted_at": datetime.now().isoformat()
        }
        self.lessons_learned.append(lesson)
        return lesson

    def _trim_records(self):
        """Keep learning records bounded."""
        if len(self.learning_records) > self._max_records:
            self.learning_records = self.learning_records[-self._max_records:]

    # ------------------------------------------------------------------
    # REPORTING
    # ------------------------------------------------------------------

    def generate_learning_report(self) -> str:
        """Generate a comprehensive learning report."""
        report = f"""
LEARNING & INTELLIGENCE REPORT
=================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERVIEW:
- Total learning events: {self._learn_count}
- Active records: {len(self.learning_records)}
- Lessons extracted: {len(self.lessons_learned)}
- Strategies tracked: {len(self.strategy_scores)}
- Merchant models: {len(self.behavior_models)}

TOP STRATEGIES:
"""
        # Sort strategies by effectiveness
        ranked = sorted(
            self.strategy_scores.items(),
            key=lambda x: x[1]["effectiveness"],
            reverse=True
        )
        for name, data in ranked[:5]:
            if data["attempts"] > 0:
                report += (
                    f"- {name}: {data['effectiveness']:.0%} effective "
                    f"({data['successes']}/{data['attempts']} successes)\n"
                )

        if self.lessons_learned:
            report += "\nLESSONS LEARNED:\n"
            for lesson in self.lessons_learned[-5:]:
                report += f"- {lesson['lesson']}\n"

        off_topic = self.get_off_topic_intelligence()
        if off_topic:
            report += "\nOFF-TOPIC INTELLIGENCE:\n"
            for cat, data in off_topic.items():
                report += f"- {cat}: {data['recommendation']}\n"

        report += "\nEND OF LEARNING REPORT"
        return report

    def get_status(self) -> dict:
        return {
            "core": "LearningThread",
            "core_number": 3,
            "total_learning_events": self._learn_count,
            "active_records": len(self.learning_records),
            "lessons_extracted": len(self.lessons_learned),
            "strategies_tracked": len(self.strategy_scores),
            "merchant_models": len(self.behavior_models),
            "status": "ACTIVE"
        }
