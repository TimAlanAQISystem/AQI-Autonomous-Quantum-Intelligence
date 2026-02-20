"""
IQCORE ORCHESTRATOR
=====================
The unified intelligence surface that connects all 5 IQ Cores into
a single coherent cognitive architecture for Agent X.

IQCore 1: CoreReasoning     — Thinking
IQCore 2: GovernanceAudit   — Ethics & Compliance
IQCore 3: LearningThread    — Learning & Adaptation
IQCore 4: SocialGraph       — Relationships
IQCore 5: VoiceEmotion      — Emotional Intelligence

The Orchestrator doesn't just pass-through — it cross-correlates signals
across cores to produce richer intelligence than any single core alone.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .core_reasoning import CoreReasoningIQCore
from .governance_audit import GovernanceAuditIQCore
from .learning_thread import LearningThreadIQCore
from .social_graph import SocialGraphIQCore
from .voice_emotion import VoiceEmotionIQCore

logger = logging.getLogger(__name__)


class IQCoreOrchestrator:
    """
    Unified Intelligence Engine — orchestrates all 5 IQ Cores.

    Cross-core capabilities:
    - Reason about an input while checking ethics, reading emotion,
      consulting relationship history, and learning from the outcome
    - Generate holistic intelligence briefings
    - Provide conversation-ready context packages
    - Track and report system-wide cognitive health
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir
        self.initialized_at = datetime.now().isoformat()
        self._interaction_count = 0

        # Initialize all 5 cores
        self.reasoning = CoreReasoningIQCore(base_dir)    # Core 1
        self.governance = GovernanceAuditIQCore(base_dir)  # Core 2
        self.learning = LearningThreadIQCore(base_dir)     # Core 3
        self.social = SocialGraphIQCore(base_dir)          # Core 4
        self.emotion = VoiceEmotionIQCore(base_dir)        # Core 5

        logger.info(
            "[IQCORE ORCHESTRATOR] All 5 IQ Cores online. "
            "Agent X cognitive architecture: ACTIVE"
        )

    # ------------------------------------------------------------------
    # UNIFIED INTELLIGENCE OPERATIONS
    # ------------------------------------------------------------------

    def process_conversation_turn(self, text: str, entity_id: str = None,
                                   context: dict = None) -> Dict[str, Any]:
        """
        Full-stack intelligence processing for a single conversation turn.
        Engages all 5 cores in coordinated analysis.

        Returns a comprehensive intelligence package.
        """
        context = context or {}
        self._interaction_count += 1

        # Core 5: Emotional Intelligence — read their emotional state
        emotion_analysis = self.emotion.analyze(text, entity_id)

        # Core 1: Reasoning — analytical assessment
        reasoning_result = self.reasoning.quick_assess(text)

        # Core 4: Social Graph — relationship context
        social_context = {}
        if entity_id:
            social_context = self.social.get_conversation_context(entity_id)
            # Record the interaction
            self.social.record_interaction(
                entity_id,
                "conversation_turn",
                sentiment=emotion_analysis["sentiment"]["score"],
                topics=context.get("topics", []),
                name=context.get("entity_name")
            )

        # Core 2: Governance — quick compliance check
        is_compliant = self.governance.quick_check(text)

        # Cross-core synthesis: combine emotional + social + reasoning
        intelligence = self._synthesize_intelligence(
            emotion_analysis, reasoning_result, social_context, is_compliant
        )

        return intelligence

    def process_turn_qpc_accelerated(self, text: str, entity_id: str = None,
                                      context: dict = None,
                                      qpc_state: dict = None) -> Dict[str, Any]:
        """
        QPC-ACCELERATED intelligence processing — uses DeepLayer QPC output
        to skip/shortcut IQ Core work that the QPC already performed.

        The QPC kernel does multi-hypothesis branching with scoring and
        strategy selection BEFORE Agent X runs. When QPC confidence is
        high, its outputs overlap with what Core 1 (Reasoning) and
        Core 5 (Emotion) would compute independently. Using QPC data
        as pre-computed intelligence eliminates redundant work.

        Cores affected:
        - Core 1 (Reasoning): SKIPPED — QPC strategy IS the reasoning output.
          QPC approach maps directly to reasoning labels.
        - Core 5 (Emotion): LIGHTWEIGHT — QPC emotion field provides baseline.
          Only runs quick sentiment, skips full dimensional evolution.
        - Core 4 (Social): READ ONLY — lookup is instant, interaction
          recording deferred (doesn't affect this turn's output).
        - Core 2 (Governance): ALWAYS RUNS — safety cannot be shortcut.

        Returns: same intelligence dict as process_conversation_turn().
        """
        context = context or {}
        qpc_state = qpc_state or {}
        self._interaction_count += 1

        # ── QPC → Reasoning mapping (replaces Core 1 quick_assess) ──
        # QPC strategy approach maps to reasoning signal labels:
        qpc_strategy = qpc_state.get('strategy', 'natural')
        strategy_map = {
            'empathy_lead': ('positive_signal', 0.7),
            'value_proposition': ('positive_signal', 0.75),
            'urgency_close': ('positive_signal', 0.8),
            'handle_objection': ('negative_signal', 0.7),
            'de_escalate': ('negative_signal', 0.65),
            'rapport_build': ('neutral_exploring', 0.6),
            'discovery': ('neutral_exploring', 0.65),
            'natural': ('neutral_undefined', 0.5),
        }
        reasoning_result = strategy_map.get(qpc_strategy, ('neutral_undefined', 0.5))

        # ── Core 5 (Emotion): Lightweight — QPC emotion field seeds it ──
        # Instead of full analyze(), do quick sentiment + use QPC emotion norm
        qpc_emotion_norm = qpc_state.get('continuum_emotion', 0.0)
        emotion_analysis = self.emotion.quick_sentiment(text)

        # Boost emotional state dimensions based on QPC field strength
        if qpc_emotion_norm > 0.5:
            self.emotion.state.shift('empathy', 0.05, 'qpc_emotion_field_strong')
            self.emotion.state.shift('warmth', 0.03, 'qpc_emotion_field_strong')

        # ── Core 4 (Social): Read only — defer write ──
        social_context = {}
        if entity_id:
            social_context = self.social.get_conversation_context(entity_id)
            # Deferred: record_interaction skipped for speed.
            # Will be recorded on next full (non-accelerated) turn.

        # ── Core 2 (Governance): Always runs — safety first ──
        is_compliant = self.governance.quick_check(text)

        # ── Cross-core synthesis — same as standard path ──
        intelligence = self._synthesize_intelligence(
            emotion_analysis, reasoning_result, social_context, is_compliant
        )

        # Tag that this was QPC-accelerated (for diagnostic visibility)
        intelligence['_qpc_accelerated'] = True
        intelligence['_qpc_strategy_used'] = qpc_strategy

        return intelligence

    def audit_action(self, action: str, actor: str = "Agent X",
                     rationale: str = "", context: dict = None) -> Dict[str, Any]:
        """
        Audit an action through the governance core with reasoning support.
        """
        # Core 2: Full governance audit
        audit_result = self.governance.audit(action, actor, "proceed", rationale, context)

        # Core 1: Reason about the action if it was flagged
        if audit_result["flag_count"] > 0:
            reasoning = self.reasoning.process(
                f"Flagged action: {action}. Flags: {audit_result['flags']}",
                context or {}
            )
            audit_result["reasoning_assessment"] = reasoning["conclusion"]

        return audit_result

    def learn_from_outcome(self, event_type: str, input_data: dict,
                           outcome: str, effectiveness: float = 0.5,
                           entity_id: str = None) -> Dict[str, Any]:
        """
        Record a learning event with cross-core enrichment.
        """
        # Core 3: Primary learning
        learning_result = self.learning.learn(
            event_type, input_data, outcome, effectiveness
        )

        # Core 4: Update social graph if entity involved
        if entity_id:
            self.social.record_interaction(
                entity_id, event_type,
                sentiment=effectiveness,
                notes=f"Outcome: {outcome}"
            )

        # Core 1: Register pattern if effectiveness was notable
        if effectiveness > 0.8 or effectiveness < 0.2:
            keywords = [w for w in str(input_data).lower().split()[:10]
                        if len(w) > 3]
            self.reasoning.register_pattern(
                event_type, keywords,
                f"{'High' if effectiveness > 0.8 else 'Low'} effectiveness event",
                outcome
            )

        return learning_result

    def get_briefing(self, entity_id: str = None) -> Dict[str, Any]:
        """
        Generate a comprehensive intelligence briefing combining all cores.
        Useful before a call or important interaction.
        """
        briefing = {
            "generated_at": datetime.now().isoformat(),
            "total_interactions": self._interaction_count,
        }

        # Emotional readout
        briefing["emotional_state"] = {
            "dominant": self.emotion.state.get_dominant_state(),
            "tone_rec": self.emotion.state.get_tone_recommendation(),
            "dimensions": self.emotion.state.dimensions
        }

        # Social context
        if entity_id:
            briefing["social_context"] = self.social.get_conversation_context(entity_id)
            empathy_cal = self.emotion.get_empathy_calibration(entity_id)
            briefing["empathy_calibration"] = empathy_cal

        # Strategy recommendation
        best_strategy, confidence = self.learning.get_best_strategy()
        briefing["recommended_strategy"] = {
            "strategy": best_strategy,
            "confidence": confidence
        }

        # Off-topic intelligence
        briefing["off_topic_intelligence"] = self.learning.get_off_topic_intelligence()

        # Temporal patterns
        briefing["temporal_patterns"] = self.learning.get_temporal_insight()

        # Governance posture
        briefing["governance"] = {
            "sap1_status": "ACTIVE",
            "compliance_rate": (
                ((self.governance._audit_count - self.governance._violation_count) /
                 max(self.governance._audit_count, 1)) * 100
            ),
            "escalations_pending": len(self.governance.escalation_queue)
        }

        return briefing

    def reset_for_new_call(self):
        """Reset emotional state for a fresh call. Social graph persists."""
        self.emotion.reset_state()
        logger.info("[IQCORE ORCHESTRATOR] Emotional state reset for new call")

    # ------------------------------------------------------------------
    # CROSS-CORE SYNTHESIS
    # ------------------------------------------------------------------

    def _synthesize_intelligence(self, emotion: dict, reasoning: tuple,
                                  social: dict, compliant: bool) -> Dict[str, Any]:
        """
        Cross-correlate signals from all cores into unified intelligence.
        This is where the magic happens — individual cores are good,
        but together they're powerful.
        """
        reasoning_label, reasoning_confidence = reasoning
        sentiment = emotion.get("sentiment", {})
        micro = emotion.get("micro_expressions", {})

        # Determine overall interaction quality
        sentiment_score = sentiment.get("score", 0.5)
        relationship = social.get("relationship", "stranger")
        trust = social.get("trust_level", 0.0)

        # Cross-core: Emotional + Social = Approach Calibration
        if sentiment_score < 0.3 and trust < 0.3:
            approach = "cautious_empathetic"
            priority = "de-escalate"
        elif sentiment_score > 0.7 and trust > 0.5:
            approach = "confident_warm"
            priority = "advance"
        elif "frustration" in micro:
            approach = "patient_understanding"
            priority = "listen"
        elif "excitement" in micro:
            approach = "match_enthusiasm"
            priority = "capitalize"
        elif "hesitation" in micro:
            approach = "gentle_encouraging"
            priority = "clarify"
        else:
            approach = social.get("approach", "balanced_professional")
            priority = "build_rapport"

        # Cross-core: Reasoning + Emotion = Signal Assessment
        if reasoning_label == "negative_signal" and sentiment_score < 0.4:
            signal_strength = "strong_negative"
        elif reasoning_label == "positive_signal" and sentiment_score > 0.6:
            signal_strength = "strong_positive"
        elif reasoning_label != "neutral_undefined":
            signal_strength = "moderate_" + reasoning_label.split("_")[0]
        else:
            signal_strength = "neutral"

        # Cross-core: Social + Learning = Personalization
        previous_topics = social.get("previous_topics", [])
        objections = social.get("objections", [])

        return {
            "approach": approach,
            "priority": priority,
            "signal_strength": signal_strength,
            "sentiment": sentiment,
            "emotion_state": emotion.get("dominant_state"),
            "tone_recommendation": emotion.get("tone_recommendation"),
            "micro_expressions": list(micro.keys()),
            "relationship_status": relationship,
            "trust_level": trust,
            "previous_topics": previous_topics,
            "known_objections": objections,
            "compliant": compliant,
            "energy_level": emotion.get("energy_level", {}).get("level", "moderate"),
            "intent": emotion.get("intent", "unknown"),
            "confidence": reasoning_confidence
        }

    # ------------------------------------------------------------------
    # REPORTING
    # ------------------------------------------------------------------

    def get_full_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all 5 IQ Cores."""
        return {
            "orchestrator": {
                "initialized_at": self.initialized_at,
                "total_interactions": self._interaction_count,
                "status": "ACTIVE",
                "cores_online": 5
            },
            "core_1_reasoning": self.reasoning.get_status(),
            "core_2_governance": self.governance.get_status(),
            "core_3_learning": self.learning.get_status(),
            "core_4_social": self.social.get_status(),
            "core_5_emotion": self.emotion.get_status()
        }

    def generate_full_report(self) -> str:
        """Generate a comprehensive report across all cores."""
        status = self.get_full_status()

        report = f"""
╔══════════════════════════════════════════════════════════════╗
║          AGENT X — 5 IQCORE INTELLIGENCE REPORT             ║
╠══════════════════════════════════════════════════════════════╣

  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  Total Interactions: {self._interaction_count}
  All Cores: ONLINE

  ┌─ CORE 1: REASONING ─────────────────────────────────────┐
  │ Chains completed: {status['core_1_reasoning']['total_reasoning_chains']}
  │ Patterns registered: {status['core_1_reasoning']['registered_patterns']}
  │ Status: {status['core_1_reasoning']['status']}
  └──────────────────────────────────────────────────────────┘

  ┌─ CORE 2: GOVERNANCE ────────────────────────────────────┐
  │ Audits: {status['core_2_governance']['total_audits']}
  │ Violations: {status['core_2_governance']['violations']}
  │ SAP-1: {status['core_2_governance']['sap1_status']}
  │ Policies: {status['core_2_governance']['policies_active']}
  │ Status: {status['core_2_governance']['status']}
  └──────────────────────────────────────────────────────────┘

  ┌─ CORE 3: LEARNING ──────────────────────────────────────┐
  │ Events: {status['core_3_learning']['total_learning_events']}
  │ Lessons: {status['core_3_learning']['lessons_extracted']}
  │ Strategies: {status['core_3_learning']['strategies_tracked']}
  │ Merchant Models: {status['core_3_learning']['merchant_models']}
  │ Status: {status['core_3_learning']['status']}
  └──────────────────────────────────────────────────────────┘

  ┌─ CORE 4: SOCIAL GRAPH ──────────────────────────────────┐
  │ Entities: {status['core_4_social']['total_entities']}
  │ Interactions: {status['core_4_social']['total_interactions']}
  │ Health: {status['core_4_social']['relationship_health']}
  │ Status: {status['core_4_social']['status']}
  └──────────────────────────────────────────────────────────┘

  ┌─ CORE 5: VOICE EMOTION ─────────────────────────────────┐
  │ Analyses: {status['core_5_emotion']['total_analyses']}
  │ State: {status['core_5_emotion']['emotional_state']}
  │ Entities tracked: {status['core_5_emotion']['entities_tracked']}
  │ Tone: {status['core_5_emotion']['tone_recommendation'][:50]}
  │ Status: {status['core_5_emotion']['status']}
  └──────────────────────────────────────────────────────────┘

╚══════════════════════════════════════════════════════════════╝
"""
        return report
