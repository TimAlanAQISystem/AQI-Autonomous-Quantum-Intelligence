"""
IQCORE 1: CORE REASONING
==========================
Agent X's analytical brain — multi-step inference, pattern recognition,
confidence scoring, hypothesis formation, and context synthesis.

This is the core that makes Agent X THINK, not just react.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ReasoningChain:
    """A single chain of reasoning with steps, evidence, and conclusions."""

    def __init__(self, query: str):
        self.query = query
        self.steps: List[Dict[str, Any]] = []
        self.conclusion: Optional[str] = None
        self.confidence: float = 0.0
        self.timestamp = datetime.now().isoformat()

    def add_step(self, observation: str, inference: str, confidence: float):
        step = {
            "step_number": len(self.steps) + 1,
            "observation": observation,
            "inference": inference,
            "confidence": round(min(max(confidence, 0.0), 1.0), 2),
            "timestamp": datetime.now().isoformat()
        }
        self.steps.append(step)
        # Overall confidence is the product of step confidences
        if self.steps:
            self.confidence = round(
                sum(s["confidence"] for s in self.steps) / len(self.steps), 2
            )

    def conclude(self, conclusion: str):
        self.conclusion = conclusion

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "steps": self.steps,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "step_count": len(self.steps),
            "timestamp": self.timestamp
        }


class CoreReasoningIQCore:
    """
    IQCore 1 — The Reasoning Engine.

    Capabilities:
    - Multi-step inference chains with confidence scoring
    - Pattern recognition across historical data
    - Hypothesis formation and testing
    - Context synthesis (combining signals into coherent understanding)
    - Decision support with evidence weighting
    - Contradiction detection in inputs
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir
        self.active_chains: List[ReasoningChain] = []
        self.completed_chains: List[dict] = []
        self.pattern_memory: Dict[str, List[dict]] = {}
        self.max_chain_history = 100
        self._reasoning_count = 0
        logger.info("[IQCORE-1] CoreReasoning initialized")

    # ------------------------------------------------------------------
    # PRIMARY REASONING
    # ------------------------------------------------------------------

    def process(self, input_signal: str, context: dict = None) -> Dict[str, Any]:
        """
        Primary reasoning entry point. Takes an input signal, builds a
        reasoning chain, and returns a structured analysis.
        """
        context = context or {}
        chain = ReasoningChain(input_signal)

        # Step 1: Signal Classification
        signal_type = self._classify_signal(input_signal)
        chain.add_step(
            observation=f"Input signal received: '{input_signal[:80]}...'",
            inference=f"Signal classified as: {signal_type}",
            confidence=0.85
        )

        # Step 2: Context Integration
        relevant_context = self._extract_relevant_context(input_signal, context)
        if relevant_context:
            chain.add_step(
                observation=f"Found {len(relevant_context)} relevant context signals",
                inference=f"Context enrichment: {', '.join(relevant_context[:3])}",
                confidence=0.75
            )

        # Step 3: Pattern Matching
        patterns = self._match_patterns(input_signal, signal_type)
        if patterns:
            chain.add_step(
                observation=f"Matched {len(patterns)} historical patterns",
                inference=f"Best pattern match: {patterns[0]['description']}",
                confidence=patterns[0].get('match_strength', 0.7)
            )

        # Step 4: Contradiction Check
        contradictions = self._detect_contradictions(input_signal, context)
        if contradictions:
            chain.add_step(
                observation=f"Detected {len(contradictions)} contradictions",
                inference=f"Contradiction: {contradictions[0]}",
                confidence=0.6
            )

        # Step 5: Synthesize Conclusion
        conclusion = self._synthesize(chain, signal_type, context)
        chain.conclude(conclusion)

        # Archive
        self._archive_chain(chain)
        self._reasoning_count += 1

        return {
            "conclusion": conclusion,
            "confidence": chain.confidence,
            "signal_type": signal_type,
            "steps": len(chain.steps),
            "contradictions_found": len(contradictions),
            "patterns_matched": len(patterns),
            "chain": chain.to_dict()
        }

    def quick_assess(self, input_signal: str) -> Tuple[str, float]:
        """
        Fast assessment without full chain — for time-critical decisions.
        Returns (assessment, confidence).
        """
        signal_type = self._classify_signal(input_signal)
        text_lower = input_signal.lower()

        # Quick sentiment read
        positive_markers = ['great', 'good', 'love', 'perfect', 'awesome', 'sure',
                            'yes', 'absolutely', 'definitely', 'sounds good', 'interested']
        negative_markers = ['no', 'not interested', 'busy', 'stop', 'don\'t',
                            'can\'t', 'won\'t', 'never', 'remove', 'terrible']
        neutral_markers = ['maybe', 'depends', 'tell me more', 'what', 'how',
                           'when', 'hmm', 'ok', 'I see', 'go on']

        pos_score = sum(1 for m in positive_markers if m in text_lower)
        neg_score = sum(1 for m in negative_markers if m in text_lower)
        neu_score = sum(1 for m in neutral_markers if m in text_lower)

        total = pos_score + neg_score + neu_score
        if total == 0:
            return "neutral_undefined", 0.5

        if pos_score > neg_score and pos_score > neu_score:
            return "positive_signal", min(0.5 + (pos_score * 0.1), 0.95)
        elif neg_score > pos_score:
            return "negative_signal", min(0.5 + (neg_score * 0.1), 0.95)
        else:
            return "neutral_exploring", 0.6

    def evaluate_hypothesis(self, hypothesis: str, evidence: List[str]) -> Dict[str, Any]:
        """
        Test a hypothesis against evidence. Returns support/refute assessment.
        """
        hyp_lower = hypothesis.lower()
        supporting = []
        refuting = []
        neutral = []

        for item in evidence:
            item_lower = item.lower()
            # Simple overlap scoring
            hyp_words = set(hyp_lower.split())
            evidence_words = set(item_lower.split())
            overlap = len(hyp_words & evidence_words)

            if overlap >= 3:
                supporting.append(item)
            elif any(neg in item_lower for neg in ['not', 'no', 'never', 'wrong', 'false']):
                refuting.append(item)
            else:
                neutral.append(item)

        total = len(evidence)
        if total == 0:
            return {"verdict": "insufficient_evidence", "confidence": 0.1}

        support_ratio = len(supporting) / total
        refute_ratio = len(refuting) / total

        if support_ratio > 0.6:
            verdict = "strongly_supported"
        elif support_ratio > 0.3:
            verdict = "partially_supported"
        elif refute_ratio > 0.5:
            verdict = "refuted"
        else:
            verdict = "inconclusive"

        return {
            "hypothesis": hypothesis,
            "verdict": verdict,
            "support_count": len(supporting),
            "refute_count": len(refuting),
            "neutral_count": len(neutral),
            "confidence": round(support_ratio, 2),
            "supporting_evidence": supporting[:3],
            "refuting_evidence": refuting[:3]
        }

    # ------------------------------------------------------------------
    # INTERNAL METHODS
    # ------------------------------------------------------------------

    def _classify_signal(self, text: str) -> str:
        """Classify input signal type."""
        text_lower = text.lower()

        if any(w in text_lower for w in ['urgent', 'critical', 'emergency', 'asap', 'now']):
            return 'urgent_action'
        if any(w in text_lower for w in ['question', 'how', 'what', 'why', 'when', '?']):
            return 'inquiry'
        if any(w in text_lower for w in ['report', 'status', 'update', 'summary']):
            return 'status_request'
        if any(w in text_lower for w in ['error', 'fail', 'broken', 'crash', 'bug', 'issue']):
            return 'error_report'
        if any(w in text_lower for w in ['call', 'phone', 'merchant', 'prospect', 'lead']):
            return 'business_operation'
        if any(w in text_lower for w in ['learn', 'improve', 'optimize', 'better', 'pattern']):
            return 'improvement_signal'
        if any(w in text_lower for w in ['hi', 'hello', 'hey', 'good morning', 'what\'s up']):
            return 'greeting'
        return 'general_input'

    def _extract_relevant_context(self, text: str, context: dict) -> List[str]:
        """Extract elements from context that are relevant to the input."""
        relevant = []
        text_lower = text.lower()

        for key, value in context.items():
            if isinstance(value, str) and any(
                word in value.lower() for word in text_lower.split()[:5]
            ):
                relevant.append(f"{key}={str(value)[:50]}")
            elif isinstance(value, (int, float)):
                relevant.append(f"{key}={value}")
            elif isinstance(value, dict):
                for sub_key in value:
                    if sub_key.lower() in text_lower:
                        relevant.append(f"{key}.{sub_key}")

        return relevant[:10]

    def _match_patterns(self, text: str, signal_type: str) -> List[dict]:
        """Match against pattern memory for historical precedents."""
        patterns = self.pattern_memory.get(signal_type, [])
        matches = []

        text_lower = text.lower()
        for pattern in patterns:
            keywords = pattern.get('keywords', [])
            matched_keywords = sum(1 for kw in keywords if kw in text_lower)
            if matched_keywords > 0:
                match_strength = min(matched_keywords / max(len(keywords), 1), 1.0)
                matches.append({
                    "description": pattern.get('description', 'Unknown pattern'),
                    "match_strength": round(match_strength, 2),
                    "historical_outcome": pattern.get('outcome', 'unknown')
                })

        return sorted(matches, key=lambda x: x['match_strength'], reverse=True)[:5]

    def _detect_contradictions(self, text: str, context: dict) -> List[str]:
        """Detect logical contradictions in the input vs context."""
        contradictions = []
        text_lower = text.lower()

        # Check for internal contradictions
        contradiction_pairs = [
            ('yes', 'no'), ('always', 'never'), ('all', 'none'),
            ('love', 'hate'), ('agree', 'disagree'), ('true', 'false'),
            ('interested', 'not interested'), ('good', 'bad')
        ]
        for pos, neg in contradiction_pairs:
            if pos in text_lower and neg in text_lower:
                contradictions.append(
                    f"Internal contradiction: '{pos}' and '{neg}' in same input"
                )

        # Check context contradictions
        if context.get('previous_sentiment') and context.get('current_sentiment'):
            prev = context['previous_sentiment']
            curr = context['current_sentiment']
            if (prev == 'positive' and curr == 'negative') or \
               (prev == 'negative' and curr == 'positive'):
                contradictions.append(
                    f"Sentiment reversal: {prev} → {curr}"
                )

        return contradictions

    def _synthesize(self, chain: ReasoningChain, signal_type: str,
                    context: dict) -> str:
        """Synthesize a conclusion from the reasoning chain."""
        step_count = len(chain.steps)
        avg_confidence = chain.confidence

        if signal_type == 'urgent_action':
            return f"Urgent signal detected. Priority processing required. Confidence: {avg_confidence}"
        elif signal_type == 'error_report':
            return f"Error condition reported. Diagnostic chain complete ({step_count} steps). Confidence: {avg_confidence}"
        elif signal_type == 'business_operation':
            return f"Business operation signal. Analyzed through {step_count} reasoning steps. Confidence: {avg_confidence}"
        elif signal_type == 'inquiry':
            return f"Inquiry processed through {step_count} analytical steps. Confidence: {avg_confidence}"
        elif signal_type == 'improvement_signal':
            return f"Improvement opportunity identified. Chain depth: {step_count}. Confidence: {avg_confidence}"
        else:
            return f"Signal processed: {signal_type}. Analysis depth: {step_count} steps. Confidence: {avg_confidence}"

    def _archive_chain(self, chain: ReasoningChain):
        """Archive completed reasoning chain."""
        self.completed_chains.append(chain.to_dict())
        if len(self.completed_chains) > self.max_chain_history:
            self.completed_chains = self.completed_chains[-self.max_chain_history:]

    def register_pattern(self, signal_type: str, keywords: List[str],
                         description: str, outcome: str = "unknown"):
        """Register a new pattern for future matching."""
        if signal_type not in self.pattern_memory:
            self.pattern_memory[signal_type] = []

        self.pattern_memory[signal_type].append({
            "keywords": keywords,
            "description": description,
            "outcome": outcome,
            "registered": datetime.now().isoformat()
        })

    def get_status(self) -> dict:
        return {
            "core": "CoreReasoning",
            "core_number": 1,
            "total_reasoning_chains": self._reasoning_count,
            "archived_chains": len(self.completed_chains),
            "registered_patterns": sum(
                len(v) for v in self.pattern_memory.values()
            ),
            "status": "ACTIVE"
        }
