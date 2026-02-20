"""
IQCORE 5: VOICE EMOTION
=========================
Agent X's emotional intelligence engine — reads emotional signals from text,
tracks emotional state across conversations, calibrates empathy, manages
tone recommendations, and maintains emotional memory.

This is what makes Agent X (and Alan through him) feel HUMAN
rather than robotic.
"""

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class EmotionalState:
    """Tracks the current emotional state across 8 dimensions."""

    def __init__(self):
        self.dimensions = {
            "warmth": 0.6,       # Cold ← 0.0 ... 1.0 → Warm
            "energy": 0.5,       # Low ← 0.0 ... 1.0 → High
            "confidence": 0.7,   # Uncertain ← 0.0 ... 1.0 → Confident
            "patience": 0.8,     # Impatient ← 0.0 ... 1.0 → Patient
            "empathy": 0.6,      # Detached ← 0.0 ... 1.0 → Empathetic
            "humor": 0.3,        # Serious ← 0.0 ... 1.0 → Playful
            "assertiveness": 0.5, # Passive ← 0.0 ... 1.0 → Assertive
            "curiosity": 0.5     # Disengaged ← 0.0 ... 1.0 → Curious
        }
        self.last_shift: Optional[str] = None
        self.shift_history: List[dict] = []

    def shift(self, dimension: str, delta: float, reason: str = ""):
        """Shift a dimension by delta, clamped to [0.0, 1.0]."""
        if dimension not in self.dimensions:
            return
        old = self.dimensions[dimension]
        new = round(min(max(old + delta, 0.0), 1.0), 2)
        self.dimensions[dimension] = new

        if abs(new - old) > 0.01:
            shift_record = {
                "dimension": dimension,
                "from": old,
                "to": new,
                "delta": round(delta, 2),
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            self.shift_history.append(shift_record)
            if len(self.shift_history) > 50:
                self.shift_history = self.shift_history[-50:]
            self.last_shift = datetime.now().isoformat()

    def get_dominant_state(self) -> str:
        """Get the dominant emotional characteristic."""
        if self.dimensions["warmth"] > 0.8 and self.dimensions["humor"] > 0.5:
            return "friendly_warm"
        if self.dimensions["empathy"] > 0.8:
            return "deeply_empathetic"
        if self.dimensions["confidence"] > 0.8 and self.dimensions["assertiveness"] > 0.7:
            return "confident_assertive"
        if self.dimensions["patience"] > 0.8 and self.dimensions["warmth"] > 0.6:
            return "patient_supportive"
        if self.dimensions["energy"] < 0.3:
            return "calm_measured"
        if self.dimensions["energy"] > 0.8:
            return "enthusiastic"
        if self.dimensions["curiosity"] > 0.7:
            return "engaged_curious"
        return "balanced_professional"

    def get_tone_recommendation(self) -> str:
        """Recommend a conversational tone based on current state."""
        dominant = self.get_dominant_state()

        tone_map = {
            "friendly_warm": "Relaxed and warm. Use casual language. Show personality.",
            "deeply_empathetic": "Slow down. Validate feelings. No rushing to solutions.",
            "confident_assertive": "Direct and clear. Don't hedge. State value plainly.",
            "patient_supportive": "Take your time. Let them talk. Don't interrupt.",
            "calm_measured": "Even-keeled. Professional. Brief and clear.",
            "enthusiastic": "High energy match. Show genuine excitement. Be upbeat.",
            "engaged_curious": "Ask questions. Show interest. Let them lead a bit.",
            "balanced_professional": "Professional but human. Standard rapport mode."
        }
        return tone_map.get(dominant, "Professional and natural.")

    def to_dict(self) -> dict:
        return {
            "dimensions": dict(self.dimensions),
            "dominant_state": self.get_dominant_state(),
            "tone_recommendation": self.get_tone_recommendation(),
            "recent_shifts": self.shift_history[-5:] if self.shift_history else []
        }


class VoiceEmotionIQCore:
    """
    IQCore 5 — The Emotional Intelligence Engine.

    Capabilities:
    - Text-based emotional signal reading (sentiment, intent, urgency)
    - 8-dimensional emotional state field tracking
    - Empathy calibration based on merchant signals
    - Tone and approach recommendation
    - Emotional memory per entity
    - Conversation energy matching
    - Micro-expression detection in text (hesitation, excitement, frustration)
    """

    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir
        self.state = EmotionalState()
        self.entity_emotions: Dict[str, List[dict]] = defaultdict(list)
        self._analysis_count = 0

        # Emotional signal lexicons
        self._build_lexicons()
        logger.info("[IQCORE-5] VoiceEmotion initialized — 8D field active")

    def _build_lexicons(self):
        """Build comprehensive emotional signal detection lexicons."""
        self.positive_signals = {
            "high_positive": [
                "love", "amazing", "fantastic", "incredible", "perfect",
                "wonderful", "excellent", "absolutely", "brilliant", "thrilled"
            ],
            "moderate_positive": [
                "good", "great", "nice", "happy", "glad", "pleased",
                "sure", "sounds good", "ok", "alright", "fine",
                "interested", "tell me more", "that works", "makes sense"
            ],
            "mild_positive": [
                "ok", "yeah", "cool", "not bad", "fair enough",
                "I see", "go on", "I suppose", "maybe"
            ]
        }

        self.negative_signals = {
            "high_negative": [
                "terrible", "horrible", "worst", "furious", "disgusted",
                "scam", "fraud", "liar", "rip off", "waste of time",
                "never", "absolutely not", "get lost", "stop calling"
            ],
            "moderate_negative": [
                "no", "not interested", "busy", "don't need",
                "not right now", "bad timing", "too expensive",
                "not looking", "already have", "don't want"
            ],
            "mild_negative": [
                "I don't know", "not sure", "probably not",
                "I'll think about it", "maybe later", "we'll see",
                "hmm", "eh", "nah"
            ]
        }

        self.urgency_signals = [
            "asap", "urgent", "right now", "immediately", "hurry",
            "can't wait", "deadline", "today", "emergency", "critical"
        ]

        self.hesitation_signals = [
            "um", "uh", "well", "I guess", "I suppose", "kind of",
            "sort of", "maybe", "I'm not sure", "let me think",
            "I don't know", "hmm", "it depends", "possibly"
        ]

        self.frustration_signals = [
            "again", "already told", "how many times", "still",
            "keeps happening", "why", "doesn't work", "always",
            "tired of", "sick of", "over this", "done with"
        ]

        self.excitement_signals = [
            "wow", "really", "no way", "that's great", "amazing",
            "I can't believe", "sign me up", "let's do it",
            "when can we start", "I'm in", "definitely"
        ]

        self.trust_signals = [
            "I trust you", "sounds honest", "I appreciate",
            "thank you", "you're helpful", "I feel comfortable",
            "straightforward", "no pressure", "I like that"
        ]

    # ------------------------------------------------------------------
    # PRIMARY EMOTION ANALYSIS
    # ------------------------------------------------------------------

    def analyze(self, text: str, entity_id: str = None) -> Dict[str, Any]:
        """
        Primary emotional analysis entry point.
        Reads emotional signals from text and returns comprehensive analysis.
        """
        self._analysis_count += 1
        text_lower = text.lower()

        # Sentiment analysis
        sentiment = self._analyze_sentiment(text_lower)

        # Micro-expression detection
        micro = self._detect_micro_expressions(text_lower)

        # Energy level detection
        energy = self._detect_energy(text_lower, text)

        # Intent reading
        intent = self._read_intent(text_lower)

        # Update internal emotional state based on what we're reading
        self._calibrate_state(sentiment, micro, energy, intent)

        # Store emotion for entity if provided
        if entity_id:
            self._store_entity_emotion(entity_id, sentiment, micro, energy)

        result = {
            "sentiment": sentiment,
            "micro_expressions": micro,
            "energy_level": energy,
            "intent": intent,
            "our_emotional_state": self.state.to_dict(),
            "tone_recommendation": self.state.get_tone_recommendation(),
            "dominant_state": self.state.get_dominant_state()
        }

        logger.info(
            f"[IQCORE-5] Emotion analysis #{self._analysis_count}: "
            f"sentiment={sentiment['label']}, energy={energy['level']}, "
            f"state={self.state.get_dominant_state()}"
        )

        return result

    def quick_sentiment(self, text: str) -> Dict[str, Any]:
        """
        QPC-ACCELERATED emotion read — lightweight fast path.

        When the QPC kernel has already computed emotion fields via the
        Continuum engine, full 8-dimensional analysis is redundant.
        This method runs ONLY sentiment + existing state readout —
        skipping micro-expression detection, energy analysis, intent
        reading, state calibration, and entity storage.

        ~3x faster than full analyze(). Used by the orchestrator's
        process_turn_qpc_accelerated() path.

        Returns: same shape dict as analyze() with current state values.
        """
        self._analysis_count += 1
        text_lower = text.lower()

        # Sentiment only — the one thing QPC doesn't directly provide
        sentiment = self._analyze_sentiment(text_lower)

        # Return with EXISTING state (no recalibration — QPC fields are seeding)
        return {
            "sentiment": sentiment,
            "micro_expressions": {},  # Skipped — QPC emotion field covers this
            "energy_level": {"level": "moderate", "source": "qpc_accelerated"},
            "intent": "unknown",
            "our_emotional_state": self.state.to_dict(),
            "tone_recommendation": self.state.get_tone_recommendation(),
            "dominant_state": self.state.get_dominant_state()
        }

    def express(self, emotion: str) -> Dict[str, Any]:
        """Express an emotion — used when Agent X itself needs to convey emotion."""
        emotion_map = {
            "joy": {"warmth": 0.15, "energy": 0.1, "humor": 0.1},
            "curiosity": {"curiosity": 0.2, "energy": 0.1},
            "compassion": {"empathy": 0.2, "warmth": 0.15, "patience": 0.1},
            "wonder": {"curiosity": 0.2, "warmth": 0.1, "energy": 0.1},
            "gratitude": {"warmth": 0.15, "empathy": 0.1},
            "concern": {"empathy": 0.15, "patience": 0.1, "energy": -0.1},
            "determination": {"assertiveness": 0.15, "confidence": 0.1, "energy": 0.1},
            "calm": {"patience": 0.15, "energy": -0.1, "warmth": 0.05}
        }

        shifts = emotion_map.get(emotion, {})
        for dimension, delta in shifts.items():
            self.state.shift(dimension, delta, f"Expressing: {emotion}")

        return {
            "expressed": emotion,
            "state_after": self.state.get_dominant_state(),
            "tone": self.state.get_tone_recommendation()
        }

    def get_empathy_calibration(self, entity_id: str = None) -> Dict[str, Any]:
        """
        Get empathy calibration recommendation based on accumulated
        emotional data for an entity.
        """
        if entity_id and entity_id in self.entity_emotions:
            history = self.entity_emotions[entity_id]
            if len(history) >= 2:
                recent = history[-3:]
                avg_sentiment = sum(
                    r.get("sentiment_score", 0.5) for r in recent
                ) / len(recent)

                if avg_sentiment < 0.3:
                    return {
                        "empathy_level": "high",
                        "note": "Entity consistently negative — prioritize empathy and patience",
                        "recommended_shifts": {"empathy": 0.2, "patience": 0.15}
                    }
                elif avg_sentiment > 0.7:
                    return {
                        "empathy_level": "moderate",
                        "note": "Entity positive — match energy, show warmth",
                        "recommended_shifts": {"warmth": 0.1, "energy": 0.1}
                    }

        return {
            "empathy_level": "standard",
            "note": "Default empathy calibration — balanced approach",
            "recommended_shifts": {}
        }

    # ------------------------------------------------------------------
    # INTERNAL ANALYSIS METHODS
    # ------------------------------------------------------------------

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment from text."""
        pos_score = 0
        neg_score = 0

        for level, words in self.positive_signals.items():
            weight = {"high_positive": 3, "moderate_positive": 2, "mild_positive": 1}[level]
            for word in words:
                if word in text:
                    pos_score += weight

        for level, words in self.negative_signals.items():
            weight = {"high_negative": 3, "moderate_negative": 2, "mild_negative": 1}[level]
            for word in words:
                if word in text:
                    neg_score += weight

        total = pos_score + neg_score
        if total == 0:
            score = 0.5
            label = "neutral"
        else:
            score = round(pos_score / total, 2)
            if score > 0.7:
                label = "positive"
            elif score < 0.3:
                label = "negative"
            else:
                label = "neutral"

        return {
            "score": score,
            "label": label,
            "positive_weight": pos_score,
            "negative_weight": neg_score
        }

    def _detect_micro_expressions(self, text: str) -> Dict[str, Any]:
        """Detect micro-expressions (subtle emotional signals in text)."""
        detected = {}

        hesitation_count = sum(1 for s in self.hesitation_signals if s in text)
        if hesitation_count >= 2:
            detected["hesitation"] = {
                "level": "strong" if hesitation_count >= 3 else "moderate",
                "count": hesitation_count
            }
        elif hesitation_count == 1:
            detected["hesitation"] = {"level": "mild", "count": 1}

        frustration_count = sum(1 for s in self.frustration_signals if s in text)
        if frustration_count >= 1:
            detected["frustration"] = {
                "level": "strong" if frustration_count >= 2 else "moderate",
                "count": frustration_count
            }

        excitement_count = sum(1 for s in self.excitement_signals if s in text)
        if excitement_count >= 1:
            detected["excitement"] = {
                "level": "strong" if excitement_count >= 2 else "moderate",
                "count": excitement_count
            }

        trust_count = sum(1 for s in self.trust_signals if s in text)
        if trust_count >= 1:
            detected["trust"] = {
                "level": "strong" if trust_count >= 2 else "moderate",
                "count": trust_count
            }

        urgency_count = sum(1 for s in self.urgency_signals if s in text)
        if urgency_count >= 1:
            detected["urgency"] = {
                "level": "strong" if urgency_count >= 2 else "moderate",
                "count": urgency_count
            }

        return detected

    def _detect_energy(self, text_lower: str, text_original: str) -> Dict[str, Any]:
        """Detect energy level from text patterns."""
        # Exclamation marks indicate energy
        exclamations = text_original.count('!')
        # Caps indicate strong emotion
        caps_words = len(re.findall(r'\b[A-Z]{2,}\b', text_original))
        # Short responses often indicate low energy or disinterest
        word_count = len(text_original.split())
        # Question marks indicate engagement
        questions = text_original.count('?')

        energy_score = 0.5  # Start neutral

        if exclamations >= 2:
            energy_score += 0.2
        elif exclamations == 1:
            energy_score += 0.1

        if caps_words >= 2:
            energy_score += 0.15

        if word_count < 3:
            energy_score -= 0.2  # Very short = low energy
        elif word_count > 20:
            energy_score += 0.1  # Long = engaged

        if questions >= 2:
            energy_score += 0.1

        energy_score = round(min(max(energy_score, 0.0), 1.0), 2)

        if energy_score > 0.7:
            level = "high"
        elif energy_score < 0.3:
            level = "low"
        else:
            level = "moderate"

        return {
            "score": energy_score,
            "level": level,
            "indicators": {
                "exclamations": exclamations,
                "caps_words": caps_words,
                "word_count": word_count,
                "questions": questions
            }
        }

    def _read_intent(self, text: str) -> str:
        """Read the likely intent behind the text."""
        if any(w in text for w in ['buy', 'purchase', 'sign up', 'get started', 'let\'s do it']):
            return "ready_to_commit"
        if any(w in text for w in ['how much', 'price', 'cost', 'rate', 'fee']):
            return "price_inquiry"
        if any(w in text for w in ['tell me more', 'explain', 'how does', 'what is']):
            return "information_seeking"
        if any(w in text for w in ['not interested', 'no thanks', 'don\'t need', 'stop']):
            return "rejection"
        if any(w in text for w in ['busy', 'call back', 'not a good time', 'in a meeting']):
            return "timing_issue"
        if any(w in text for w in ['who are you', 'what company', 'how did you get']):
            return "identity_inquiry"
        if any(w in text for w in ['complaint', 'problem', 'issue', 'not working']):
            return "complaint"
        if any(w in text for w in ['thank', 'appreciate', 'helpful', 'thanks']):
            return "gratitude"
        if any(w in text for w in ['?']):
            return "question"
        return "general_conversation"

    def _calibrate_state(self, sentiment: dict, micro: dict,
                         energy: dict, intent: str):
        """Calibrate Agent X's emotional state based on what we're reading."""
        # Mirror sentiment (with dampening — we don't overreact)
        sent_score = sentiment.get("score", 0.5)
        if sent_score > 0.6:
            self.state.shift("warmth", 0.05, "Positive sentiment detected")
            self.state.shift("energy", 0.03, "Positive energy match")
        elif sent_score < 0.4:
            self.state.shift("empathy", 0.08, "Negative sentiment — increase empathy")
            self.state.shift("patience", 0.05, "Negative sentiment — be patient")
            self.state.shift("assertiveness", -0.05, "Back off slightly")

        # Respond to micro-expressions
        if "frustration" in micro:
            self.state.shift("patience", 0.1, "Frustration detected")
            self.state.shift("empathy", 0.1, "Frustration detected")
            self.state.shift("humor", -0.1, "Not the time for jokes")

        if "excitement" in micro:
            self.state.shift("energy", 0.1, "Excitement detected — match it")
            self.state.shift("warmth", 0.05, "Excitement")
            self.state.shift("confidence", 0.05, "They're excited — be confident")

        if "hesitation" in micro:
            self.state.shift("patience", 0.08, "Hesitation — don't rush")
            self.state.shift("warmth", 0.05, "Hesitation — be encouraging")
            self.state.shift("assertiveness", -0.05, "Don't push")

        if "trust" in micro:
            self.state.shift("confidence", 0.08, "Trust signal")
            self.state.shift("warmth", 0.05, "Trust building")

        # Energy matching
        energy_level = energy.get("score", 0.5)
        if energy_level > 0.7:
            self.state.shift("energy", 0.05, "Energy match — high")
        elif energy_level < 0.3:
            self.state.shift("energy", -0.05, "Energy match — low")

        # Intent-based calibration
        if intent == "rejection":
            self.state.shift("patience", 0.1, "Rejection — stay calm")
            self.state.shift("warmth", 0.05, "Rejection — stay warm")
            self.state.shift("assertiveness", -0.1, "Don't push rejected prospect")
        elif intent == "ready_to_commit":
            self.state.shift("confidence", 0.1, "Commitment signal")
            self.state.shift("energy", 0.05, "Commitment energy")
        elif intent == "complaint":
            self.state.shift("empathy", 0.15, "Complaint — full empathy")
            self.state.shift("patience", 0.1, "Complaint — full patience")

    def _store_entity_emotion(self, entity_id: str, sentiment: dict,
                               micro: dict, energy: dict):
        """Store emotional reading for an entity."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "sentiment_score": sentiment.get("score", 0.5),
            "sentiment_label": sentiment.get("label", "neutral"),
            "energy_level": energy.get("score", 0.5),
            "micro_expressions": list(micro.keys())
        }
        self.entity_emotions[entity_id].append(record)
        # Keep last 30 readings per entity
        if len(self.entity_emotions[entity_id]) > 30:
            self.entity_emotions[entity_id] = \
                self.entity_emotions[entity_id][-30:]

    # ------------------------------------------------------------------
    # STATUS
    # ------------------------------------------------------------------

    def reset_state(self):
        """Reset emotional state to baseline (e.g., between calls)."""
        self.state = EmotionalState()
        logger.info("[IQCORE-5] Emotional state reset to baseline")

    def get_status(self) -> dict:
        return {
            "core": "VoiceEmotion",
            "core_number": 5,
            "total_analyses": self._analysis_count,
            "emotional_state": self.state.get_dominant_state(),
            "tone_recommendation": self.state.get_tone_recommendation(),
            "entities_tracked": len(self.entity_emotions),
            "dimensions": self.state.dimensions,
            "status": "ACTIVE"
        }
