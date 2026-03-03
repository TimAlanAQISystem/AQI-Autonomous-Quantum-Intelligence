"""
Unit Tests for CallTypeClassifier
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tests all override paths, edge cases, and the 141s regression bug.

Usage:
    python -m pytest test_call_type_classifier.py -v
    or:
    python test_call_type_classifier.py
"""

import sys
import os
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from call_type_classifier import CallTypeClassifier
from call_feature_aggregator import CallFeatureAggregator


class TestClassifierOverrides(unittest.TestCase):
    """Test hard override rules."""

    def setUp(self):
        self.clf = CallTypeClassifier()

    def _base_features(self, **overrides):
        """Build a neutral feature dict with optional overrides."""
        f = {
            "acoustic": {
                "cadence_irregularity": 0.5,
                "waveform_entropy": 0.5,
                "background_noise_level": "low",
                "has_breathing": False,
            },
            "temporal": {
                "avg_first_audio_latency_ms": 0,
                "avg_full_turn_latency_ms": 0,
                "interruptions": 0,
                "overlaps": 0,
                "monologue_ratio": 0.3,
                "greeting_duration_ms": 0,
            },
            "linguistic": {
                "merchant_word_count": 0,
                "alan_word_count": 0,
                "turn_count": 0,
                "questions_count": 0,
                "filler_rate": 0.0,
                "scripted_phrase_rate": 0.0,
            },
            "behavioral": {
                "semantic_reactivity": 0.0,
                "menu_pattern_score": 0.0,
                "voicemail_phrase_score": 0.0,
            },
        }
        # Apply overrides by category
        for key, val in overrides.items():
            for cat in ("acoustic", "temporal", "linguistic", "behavioral"):
                if key in f[cat]:
                    f[cat][key] = val
        return f

    # ── Human engagement override ──

    def test_human_engagement_override(self):
        """40+ words and 3+ turns → force human_conversation."""
        features = self._base_features(merchant_word_count=120, turn_count=10)
        result = self.clf.classify(features)
        self.assertEqual(result["call_type"], "human_conversation")
        self.assertIn("HUMAN_ENGAGEMENT_OVERRIDE", result["override_flags"])
        self.assertGreaterEqual(result["confidence"], 0.9)

    def test_human_engagement_just_at_threshold(self):
        """Exactly 40 words and 3 turns → still triggers."""
        features = self._base_features(merchant_word_count=40, turn_count=3)
        result = self.clf.classify(features)
        self.assertEqual(result["call_type"], "human_conversation")
        self.assertIn("HUMAN_ENGAGEMENT_OVERRIDE", result["override_flags"])

    def test_human_engagement_below_threshold(self):
        """39 words, 3 turns → does NOT trigger engagement override."""
        features = self._base_features(merchant_word_count=39, turn_count=3)
        result = self.clf.classify(features)
        self.assertNotIn("HUMAN_ENGAGEMENT_OVERRIDE", result.get("override_flags", []))

    # ── Human question override ──

    def test_human_question_override(self):
        """1+ questions with semantic reactivity → human."""
        features = self._base_features(questions_count=2, semantic_reactivity=0.7)
        result = self.clf.classify(features)
        self.assertEqual(result["call_type"], "human_conversation")
        self.assertIn("HUMAN_QUESTION_OVERRIDE", result["override_flags"])

    # ── Human interruption override ──

    def test_human_interruption_override(self):
        """1+ interruption → human."""
        features = self._base_features(interruptions=1)
        result = self.clf.classify(features)
        self.assertEqual(result["call_type"], "human_conversation")
        self.assertIn("HUMAN_INTERRUPTION_OVERRIDE", result["override_flags"])

    # ── Voicemail override ──

    def test_voicemail_phrase_override(self):
        """High voicemail phrase score → voicemail."""
        features = self._base_features(
            voicemail_phrase_score=0.9,
            monologue_ratio=0.95,
            turn_count=1,
            merchant_word_count=10,
        )
        result = self.clf.classify(features)
        self.assertEqual(result["call_type"], "voicemail")
        self.assertIn("VOICEMAIL_PHRASE_OVERRIDE", result["override_flags"])

    # ── IVR menu override ──

    def test_ivr_menu_override(self):
        """High menu pattern score → IVR."""
        features = self._base_features(
            menu_pattern_score=0.85,
            scripted_phrase_rate=0.8,
            turn_count=1,
            merchant_word_count=15,
        )
        result = self.clf.classify(features)
        self.assertEqual(result["call_type"], "ivr")
        self.assertIn("IVR_MENU_OVERRIDE", result["override_flags"])

    # ── Safety rule (the 141s bug regression test) ──

    def test_safety_rule_prevents_voicemail_on_engaged_call(self):
        """
        REGRESSION TEST: The 141s bug.
        A call with 118 merchant words, 10 turns, and a voicemail_phrase_score of 0.8
        MUST be classified as human_conversation, not voicemail.
        The engagement override fires first, preventing the voicemail label.
        """
        features = self._base_features(
            merchant_word_count=118,
            turn_count=10,
            voicemail_phrase_score=0.8,
            semantic_reactivity=0.7,
        )
        result = self.clf.classify(features)
        self.assertEqual(result["call_type"], "human_conversation")
        self.assertNotEqual(result["call_type"], "voicemail")
        self.assertGreaterEqual(result["confidence"], 0.9)

    def test_safety_rule_forces_human_even_if_engagement_off(self):
        """
        Even with engagement override disabled, safety rule should
        prevent voicemail on engaged calls.
        """
        config = CallTypeClassifier.DEFAULT_CONFIG.copy()
        config = {
            "thresholds": config["thresholds"].copy(),
            "weights": config["weights"].copy(),
            "overrides": {
                "enable_human_engagement_override": False,
                "enable_human_question_override": False,
                "enable_human_interruption_override": False,
                "enable_voicemail_phrase_override": True,
                "enable_ivr_menu_override": True,
                "enable_safety_rule": True,
            },
            "logging": config["logging"].copy(),
        }
        clf = CallTypeClassifier(config)
        features = self._base_features(
            merchant_word_count=100,
            turn_count=8,
            voicemail_phrase_score=0.9,
        )
        result = clf.classify(features)
        # Safety rule should kick in after voicemail override
        self.assertEqual(result["call_type"], "human_conversation")
        self.assertIn("SAFETY_RULE_OVERRIDE", result["override_flags"])


class TestClassifierProbabilities(unittest.TestCase):
    """Test probability-based fallback (no overrides firing)."""

    def setUp(self):
        self.clf = CallTypeClassifier()

    def test_neutral_features_produce_valid_probabilities(self):
        """Neutral features should produce valid probability distribution."""
        features = {
            "acoustic": {"cadence_irregularity": 0.5, "waveform_entropy": 0.5,
                         "background_noise_level": "low", "has_breathing": False},
            "temporal": {"avg_first_audio_latency_ms": 0, "avg_full_turn_latency_ms": 0,
                         "interruptions": 0, "overlaps": 0, "monologue_ratio": 0.3,
                         "greeting_duration_ms": 0},
            "linguistic": {"merchant_word_count": 15, "alan_word_count": 10,
                           "turn_count": 2, "questions_count": 0,
                           "filler_rate": 0.0, "scripted_phrase_rate": 0.0},
            "behavioral": {"semantic_reactivity": 0.3, "menu_pattern_score": 0.0,
                           "voicemail_phrase_score": 0.0},
        }
        result = self.clf.classify(features)
        probs = result["probabilities"]
        # Sum should be ~1.0
        self.assertAlmostEqual(sum(probs.values()), 1.0, places=2)
        # All probabilities should be non-negative
        for v in probs.values():
            self.assertGreaterEqual(v, 0.0)


class TestClassifierFromCDC(unittest.TestCase):
    """Test the classify_from_cdc convenience method."""

    def setUp(self):
        self.clf = CallTypeClassifier()

    def test_cdc_human_call(self):
        """CDC record with high engagement → human_conversation."""
        cdc_record = {
            "merchant_words": 120,
            "alan_words": 80,
            "total_turns": 10,
            "duration_seconds": 80.0,
            "final_outcome": "kept_engaged",
            "coaching_weaknesses": "high_latency",
        }
        result = self.clf.classify_from_cdc(cdc_record)
        self.assertEqual(result["call_type"], "human_conversation")

    def test_cdc_voicemail_call(self):
        """CDC record with voicemail outcome → voicemail."""
        cdc_record = {
            "merchant_words": 5,
            "alan_words": 0,
            "total_turns": 0,
            "duration_seconds": 15.0,
            "final_outcome": "voicemail_ivr",
            "coaching_weaknesses": "",
        }
        result = self.clf.classify_from_cdc(cdc_record)
        self.assertIn(result["call_type"], ("voicemail", "ambiguous_machine_like"))

    def test_cdc_ivr_call(self):
        """CDC record with IVR outcome → ivr."""
        cdc_record = {
            "merchant_words": 10,
            "alan_words": 5,
            "total_turns": 1,
            "duration_seconds": 45.0,
            "final_outcome": "ivr_transcript_kill",
            "coaching_weaknesses": "",
        }
        result = self.clf.classify_from_cdc(cdc_record)
        # Should lean machine (IVR or voicemail)
        self.assertIn(result["call_type"],
                      ("ivr", "voicemail", "ambiguous_machine_like"))


class TestAggregator(unittest.TestCase):
    """Test CallFeatureAggregator."""

    def setUp(self):
        self.agg = CallFeatureAggregator()

    def test_empty_turns(self):
        """Empty turns should return zero features."""
        result = self.agg.aggregate_from_cdc_turns("CA123", [])
        self.assertEqual(result["linguistic"]["merchant_word_count"], 0)
        self.assertEqual(result["linguistic"]["turn_count"], 0)

    def test_human_conversation_turns(self):
        """Multiple turns with real speech."""
        turns = [
            {"user_text": "Hello, how can I help you?", "alan_text": "Hi there",
             "user_word_count": 6, "alan_word_count": 2},
            {"user_text": "Yeah, we do merchant services, what do you need?",
             "alan_text": "I wanted to talk about your payment processing.",
             "user_word_count": 10, "alan_word_count": 8},
            {"user_text": "Uh, let me check on that. Hold on a sec.",
             "alan_text": "Sure, take your time.",
             "user_word_count": 10, "alan_word_count": 4},
            {"user_text": "We're currently with Square, been using them about two years.",
             "alan_text": "I see, and how's that working for you?",
             "user_word_count": 10, "alan_word_count": 9},
        ]
        result = self.agg.aggregate_from_cdc_turns("CA456", turns)

        self.assertEqual(result["linguistic"]["turn_count"], 4)
        self.assertGreaterEqual(result["linguistic"]["merchant_word_count"], 30)
        self.assertGreater(result["linguistic"]["filler_rate"], 0)  # "uh" detected
        self.assertGreater(result["linguistic"]["questions_count"], 0)  # "?" detected
        self.assertGreater(result["behavioral"]["semantic_reactivity"], 0)

    def test_voicemail_turn(self):
        """Single voicemail greeting turn."""
        turns = [
            {"user_text": "Hi, you've reached the voicemail of Maria. Please leave a message after the tone.",
             "alan_text": "", "user_word_count": 15, "alan_word_count": 0},
        ]
        result = self.agg.aggregate_from_cdc_turns("CA789", turns)

        self.assertEqual(result["linguistic"]["turn_count"], 1)
        self.assertGreater(result["behavioral"]["voicemail_phrase_score"], 0.5)
        self.assertGreater(result["temporal"]["monologue_ratio"], 0.8)

    def test_ivr_menu_turn(self):
        """IVR menu pattern detection."""
        turns = [
            {"user_text": "Press 1 for sales, press 2 for billing, press 3 for hours.",
             "alan_text": "", "user_word_count": 12, "alan_word_count": 0},
        ]
        result = self.agg.aggregate_from_cdc_turns("CA101", turns)

        self.assertGreater(result["behavioral"]["menu_pattern_score"], 0.5)


class TestEndToEnd(unittest.TestCase):
    """Integration: Aggregator → Classifier pipeline."""

    def test_full_pipeline_human(self):
        """Aggregator feeds classifier for a human call."""
        agg = CallFeatureAggregator()
        clf = CallTypeClassifier()

        turns = [
            {"user_text": "Metro Earth Florist, how may I help you?",
             "alan_text": "Hey, it's Alan with SCS.",
             "user_word_count": 8, "alan_word_count": 6},
            {"user_text": "What is SCS?",
             "alan_text": "Signature Card Services — we help businesses save on card processing.",
             "user_word_count": 4, "alan_word_count": 10},
            {"user_text": "Oh, um, I think we're good with what we have right now.",
             "alan_text": "I understand. Would it be worth a quick comparison?",
             "user_word_count": 13, "alan_word_count": 9},
            {"user_text": "Yeah, maybe. Can you call back on Thursday?",
             "alan_text": "Absolutely. Thursday works. Talk to you then.",
             "user_word_count": 8, "alan_word_count": 7},
        ]

        features = agg.aggregate_from_cdc_turns("CAtest", turns)
        result = clf.classify(features)

        self.assertEqual(result["call_type"], "human_conversation")
        self.assertGreaterEqual(result["confidence"], 0.7)

    def test_full_pipeline_voicemail(self):
        """Aggregator feeds classifier for a voicemail call."""
        agg = CallFeatureAggregator()
        clf = CallTypeClassifier()

        turns = [
            {"user_text": "Hi, you've reached Maria at the flower shop. "
                          "Leave a message after the beep and I'll get back to you.",
             "alan_text": "",
             "user_word_count": 20, "alan_word_count": 0},
        ]

        features = agg.aggregate_from_cdc_turns("CAvm", turns)
        result = clf.classify(features)

        self.assertIn(result["call_type"], ("voicemail",))


if __name__ == "__main__":
    unittest.main(verbosity=2)
