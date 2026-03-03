"""
CallTypeClassifier — Fusion Call-Type Classification Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Distinguishes:
  - human_conversation
  - ivr
  - voicemail
  - ambiguous_human_like
  - ambiguous_machine_like

Architecture:
  Layer 1 — Raw feature extraction (acoustic, temporal, linguistic, behavioral)
  Layer 2 — Per-class score computation with configurable weights
  Layer 3 — Softmax normalization to probabilities
  Layer 4 — Decision head with hard overrides

The classifier is STATELESS and consumes a per-call aggregated feature dict.
All thresholds are governed by classifier_config.yaml for live tuning.

Author: Claude Opus 4.6 — AQI System Expert
Date: February 18, 2026
"""

import math
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CallTypeClassifier:
    """
    Fusion classifier for call-type determination.

    Consumes per-call aggregated features and produces:
      - call_type (str)
      - confidence (float 0-1)
      - raw_scores (dict)
      - probabilities (dict)
      - override_flags (list[str])
      - reasoning (str)
    """

    # ── Default config (used when no YAML loaded) ────────────────────────
    DEFAULT_CONFIG = {
        "thresholds": {
            "human_word_threshold": 40,
            "human_turn_threshold": 3,
            "human_question_threshold": 1,
            "human_semantic_reactivity_threshold": 0.4,
            "ivr_menu_threshold": 0.7,
            "voicemail_phrase_threshold": 0.7,
            "monologue_ratio_threshold": 0.8,
            "monologue_turn_cap": 2,
            "cadence_machine_threshold": 0.2,
            "probability_confidence_threshold": 0.7,
            "ambiguous_confidence_floor": 0.5,
        },
        "weights": {
            "human": {
                "cadence_irregularity": 1.0,
                "semantic_reactivity": 1.0,
                "filler_rate": 0.8,
                "interruptions": 1.2,
                "background_noise_bonus": 0.3,
                "breathing_bonus": 0.4,
            },
            "ivr": {
                "scripted_phrase_rate": 1.0,
                "menu_pattern_score": 1.2,
                "cadence_regular": 0.8,
                "no_interruptions_bonus": 0.3,
            },
            "voicemail": {
                "voicemail_phrase_score": 1.4,
                "monologue_ratio": 0.8,
                "short_greeting_bonus": 0.3,
            },
        },
        "overrides": {
            "enable_human_engagement_override": True,
            "enable_human_question_override": True,
            "enable_human_interruption_override": True,
            "enable_voicemail_phrase_override": True,
            "enable_ivr_menu_override": True,
            "enable_safety_rule": True,
        },
        "logging": {
            "log_raw_scores": True,
            "log_probabilities": True,
            "log_overrides": True,
        },
    }

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize with config dict (from YAML or default).

        Args:
            config: Full config dict with 'thresholds', 'weights', 'overrides' keys.
                    If None, uses DEFAULT_CONFIG.
        """
        self._raw_config = config or self.DEFAULT_CONFIG
        self.thresholds = self._raw_config.get("thresholds", self.DEFAULT_CONFIG["thresholds"])
        self.weights = self._raw_config.get("weights", self.DEFAULT_CONFIG["weights"])
        self.overrides_enabled = self._raw_config.get("overrides", self.DEFAULT_CONFIG["overrides"])
        self.log_config = self._raw_config.get("logging", self.DEFAULT_CONFIG["logging"])

    def reload_config(self, config: Dict[str, Any]):
        """Hot-reload config without reinstantiating."""
        self._raw_config = config
        self.thresholds = config.get("thresholds", self.DEFAULT_CONFIG["thresholds"])
        self.weights = config.get("weights", self.DEFAULT_CONFIG["weights"])
        self.overrides_enabled = config.get("overrides", self.DEFAULT_CONFIG["overrides"])
        self.log_config = config.get("logging", self.DEFAULT_CONFIG["logging"])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN ENTRY POINT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def classify(self, call_features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify a call based on aggregated per-call features.

        Args:
            call_features: {
                "acoustic": { "cadence_irregularity": float, "waveform_entropy": float,
                              "background_noise_level": str, "has_breathing": bool },
                "temporal": { "avg_first_audio_latency_ms": float, "avg_full_turn_latency_ms": float,
                              "interruptions": int, "overlaps": int, "monologue_ratio": float,
                              "greeting_duration_ms": float },
                "linguistic": { "merchant_word_count": int, "alan_word_count": int,
                                "turn_count": int, "questions_count": int,
                                "filler_rate": float, "scripted_phrase_rate": float },
                "behavioral": { "semantic_reactivity": float, "menu_pattern_score": float,
                                "voicemail_phrase_score": float },
            }

        Returns:
            {
                "call_type": str,
                "confidence": float,
                "raw_scores": {"human": float, "ivr": float, "voicemail": float},
                "probabilities": {"human": float, "ivr": float, "voicemail": float},
                "override_flags": [str],
                "reasoning": str,
            }
        """
        acoustic = call_features.get("acoustic", {})
        temporal = call_features.get("temporal", {})
        linguistic = call_features.get("linguistic", {})
        behavioral = call_features.get("behavioral", {})

        # 1. Compute raw scores
        scores = self._compute_raw_scores(acoustic, temporal, linguistic, behavioral)

        # 2. Normalize to probabilities
        probs = self._softmax(scores)

        # 3. Apply overrides (hard rules before probability fallback)
        final_label, override_flags, reasoning = self._apply_overrides(
            probs, acoustic, temporal, linguistic, behavioral
        )

        # 4. Compute confidence
        confidence = self._compute_confidence(probs, override_flags)

        # 5. Apply safety rule — engaged calls CANNOT be voicemail
        if self.overrides_enabled.get("enable_safety_rule", True):
            if (linguistic.get("merchant_word_count", 0) >= self.thresholds.get("human_word_threshold", 40)
                    and linguistic.get("turn_count", 0) >= self.thresholds.get("human_turn_threshold", 3)
                    and final_label in ("voicemail", "ivr")):
                old_label = final_label
                final_label = "human_conversation"
                override_flags.append("SAFETY_RULE_OVERRIDE")
                reasoning += f" | Safety override: {old_label} → human (words={linguistic.get('merchant_word_count')}, turns={linguistic.get('turn_count')})"
                confidence = max(confidence, 0.9)

        # 6. Ambiguity bucketing
        if not override_flags and confidence < self.thresholds.get("ambiguous_confidence_floor", 0.5):
            if probs.get("human", 0) > probs.get("ivr", 0) + probs.get("voicemail", 0):
                final_label = "ambiguous_human_like"
            else:
                final_label = "ambiguous_machine_like"
            reasoning += f" | Low confidence ({confidence:.2f}) → ambiguous"

        result = {
            "call_type": final_label,
            "confidence": round(confidence, 4),
            "raw_scores": {k: round(v, 4) for k, v in scores.items()},
            "probabilities": {k: round(v, 4) for k, v in probs.items()},
            "override_flags": override_flags,
            "reasoning": reasoning.strip(" |"),
        }

        if self.log_config.get("log_raw_scores"):
            logger.info(f"[CLASSIFIER] Scores: {result['raw_scores']}")
        if self.log_config.get("log_probabilities"):
            logger.info(f"[CLASSIFIER] Probabilities: {result['probabilities']}")
        if self.log_config.get("log_overrides") and override_flags:
            logger.info(f"[CLASSIFIER] Overrides: {override_flags}")
        logger.info(f"[CLASSIFIER] Result: {final_label} (conf={confidence:.3f}) — {reasoning.strip(' |')}")

        return result

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LAYER 2: Raw Score Computation
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _compute_raw_scores(self, acoustic, temporal, linguistic, behavioral):
        hw = self.weights.get("human", {})
        iw = self.weights.get("ivr", {})
        vw = self.weights.get("voicemail", {})

        # ── Human score ──
        human_score = (
            acoustic.get("cadence_irregularity", 0.5) * hw.get("cadence_irregularity", 1.0)
            + behavioral.get("semantic_reactivity", 0.0) * hw.get("semantic_reactivity", 1.0)
            + linguistic.get("filler_rate", 0.0) * hw.get("filler_rate", 0.8)
            + min(temporal.get("interruptions", 0), 5) * 0.2 * hw.get("interruptions", 1.2)
        )
        # Bonus for background noise (humans exist in noisy environments)
        if acoustic.get("background_noise_level", "low") in ("medium", "high"):
            human_score += hw.get("background_noise_bonus", 0.3)
        # Bonus for breathing detection
        if acoustic.get("has_breathing", False):
            human_score += hw.get("breathing_bonus", 0.4)

        # ── IVR score ──
        ivr_score = (
            linguistic.get("scripted_phrase_rate", 0.0) * iw.get("scripted_phrase_rate", 1.0)
            + behavioral.get("menu_pattern_score", 0.0) * iw.get("menu_pattern_score", 1.2)
            + (1 - acoustic.get("cadence_irregularity", 0.5)) * iw.get("cadence_regular", 0.8)
        )
        # Bonus for no interruptions (machines never interrupt)
        if temporal.get("interruptions", 0) == 0 and temporal.get("overlaps", 0) == 0:
            ivr_score += iw.get("no_interruptions_bonus", 0.3)

        # ── Voicemail score ──
        voicemail_score = (
            behavioral.get("voicemail_phrase_score", 0.0) * vw.get("voicemail_phrase_score", 1.4)
            + temporal.get("monologue_ratio", 0.0) * vw.get("monologue_ratio", 0.8)
        )
        # Bonus for short greeting with single monologue
        if (temporal.get("greeting_duration_ms", 0) > 0
                and temporal.get("greeting_duration_ms", 0) < 10000
                and linguistic.get("turn_count", 0) <= 2):
            voicemail_score += vw.get("short_greeting_bonus", 0.3)

        return {
            "human": human_score,
            "ivr": ivr_score,
            "voicemail": voicemail_score,
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LAYER 3: Softmax Normalization
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _softmax(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Normalize raw scores to probabilities via softmax."""
        # Clamp to prevent overflow
        max_score = max(scores.values()) if scores else 0
        exps = {k: math.exp(v - max_score) for k, v in scores.items()}
        total = sum(exps.values())
        if total == 0:
            n = len(scores)
            return {k: 1.0 / n for k in scores}
        return {k: v / total for k, v in exps.items()}

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LAYER 4: Overrides + Decision Head
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _apply_overrides(self, probs, acoustic, temporal, linguistic, behavioral
                         ) -> Tuple[str, List[str], str]:
        """
        Apply hard override rules before falling back to probability argmax.

        Returns:
            (final_label, override_flags, reasoning)
        """
        flags = []
        reasoning = ""
        th = self.thresholds
        ov = self.overrides_enabled

        # ── HUMAN OVERRIDES (checked first — protect real conversations) ──

        # 1. Engagement override — most important
        if ov.get("enable_human_engagement_override", True):
            mw = linguistic.get("merchant_word_count", 0)
            tc = linguistic.get("turn_count", 0)
            if mw >= th.get("human_word_threshold", 40) and tc >= th.get("human_turn_threshold", 3):
                flags.append("HUMAN_ENGAGEMENT_OVERRIDE")
                reasoning = f"Engagement: {mw} words, {tc} turns"
                return "human_conversation", flags, reasoning

        # 2. Question override
        if ov.get("enable_human_question_override", True):
            qc = linguistic.get("questions_count", 0)
            sr = behavioral.get("semantic_reactivity", 0.0)
            if (qc >= th.get("human_question_threshold", 1)
                    and sr >= th.get("human_semantic_reactivity_threshold", 0.4)):
                flags.append("HUMAN_QUESTION_OVERRIDE")
                reasoning = f"Questions: {qc}, reactivity: {sr:.2f}"
                return "human_conversation", flags, reasoning

        # 3. Interruption override
        if ov.get("enable_human_interruption_override", True):
            interruptions = temporal.get("interruptions", 0)
            overlaps = temporal.get("overlaps", 0)
            if interruptions >= 1 or overlaps >= 1:
                flags.append("HUMAN_INTERRUPTION_OVERRIDE")
                reasoning = f"Interruptions: {interruptions}, overlaps: {overlaps}"
                return "human_conversation", flags, reasoning

        # ── MACHINE OVERRIDES ──

        # 4. Voicemail phrase override
        if ov.get("enable_voicemail_phrase_override", True):
            vps = behavioral.get("voicemail_phrase_score", 0.0)
            if vps >= th.get("voicemail_phrase_threshold", 0.7):
                flags.append("VOICEMAIL_PHRASE_OVERRIDE")
                reasoning = f"Voicemail phrases: {vps:.2f}"
                return "voicemail", flags, reasoning

        # 5. IVR menu override
        if ov.get("enable_ivr_menu_override", True):
            mps = behavioral.get("menu_pattern_score", 0.0)
            if mps >= th.get("ivr_menu_threshold", 0.7):
                flags.append("IVR_MENU_OVERRIDE")
                reasoning = f"Menu patterns: {mps:.2f}"
                return "ivr", flags, reasoning

        # 6. Monologue + low turns = machine
        monologue = temporal.get("monologue_ratio", 0.0)
        turns = linguistic.get("turn_count", 0)
        if (monologue >= th.get("monologue_ratio_threshold", 0.8)
                and turns <= th.get("monologue_turn_cap", 2)):
            cadence = acoustic.get("cadence_irregularity", 0.5)
            if cadence <= th.get("cadence_machine_threshold", 0.2):
                flags.append("MONOLOGUE_MACHINE_PATTERN")
                reasoning = f"Monologue: {monologue:.2f}, turns: {turns}, cadence: {cadence:.2f}"
                return "voicemail", flags, reasoning

        # ── FALLBACK TO PROBABILITIES ──
        max_label = max(probs, key=probs.get)
        max_prob = probs[max_label]
        reasoning = f"Probability argmax: {max_label}={max_prob:.3f}"

        return max_label, flags, reasoning

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONFIDENCE COMPUTATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _compute_confidence(self, probs: Dict[str, float], flags: List[str]) -> float:
        """Compute final confidence from probabilities and override flags."""
        base_conf = max(probs.values()) if probs else 0.5
        if flags:
            return max(base_conf, 0.9)
        return base_conf

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONVENIENCE: Classify from raw CDC data
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def classify_from_cdc(self, call_record: Dict, turns: List[Dict] = None) -> Dict[str, Any]:
        """
        Convenience method: classify directly from CDC call record + turns.
        Builds features from available CDC data without requiring the full
        per-turn feature schema.

        This is the pragmatic path — we extract what we CAN from existing CDC data
        and fill reasonable defaults for features we don't yet capture (acoustic, etc.).

        Args:
            call_record: Row from CDC calls table (dict)
            turns: List of rows from CDC turns table (optional)

        Returns:
            Classification result dict
        """
        merchant_words = call_record.get("merchant_words", 0) or 0
        alan_words = call_record.get("alan_words", 0) or 0
        total_turns = call_record.get("total_turns", 0) or 0
        duration = call_record.get("duration_seconds", 0) or 0
        outcome = call_record.get("final_outcome", "unknown") or "unknown"
        coaching_weaknesses = call_record.get("coaching_weaknesses", "") or ""

        # ── Extract features from turns if available ──
        questions_count = 0
        filler_count = 0
        total_merchant_words_from_turns = 0
        interruptions = 0

        if turns:
            for t in turns:
                user_text = (t.get("user_text", "") or "").lower()
                total_merchant_words_from_turns += t.get("user_word_count", 0) or 0
                # Count questions
                if "?" in user_text:
                    questions_count += 1
                # Count fillers
                for filler in ("uh ", "um ", "like ", "you know ", "hmm"):
                    filler_count += user_text.count(filler)

        effective_words = max(merchant_words, total_merchant_words_from_turns)
        filler_rate = filler_count / max(effective_words, 1) if effective_words > 0 else 0.0

        # ── Derive behavioral scores from outcome/transcript ──
        voicemail_phrases = any(kw in outcome.lower() for kw in
                                ("voicemail", "vm_", "voicemail_ivr"))
        menu_detected = "ivr" in outcome.lower() or "menu" in coaching_weaknesses.lower()

        # Semantic reactivity: rough proxy from turn count and word count
        if total_turns >= 3 and effective_words >= 20:
            semantic_reactivity = min(1.0, effective_words / (total_turns * 30))
        else:
            semantic_reactivity = 0.0

        # Monologue ratio: if very few turns but many words, likely monologue
        if total_turns <= 1 and effective_words > 5:
            monologue_ratio = 0.9
        elif total_turns <= 2:
            monologue_ratio = 0.6
        else:
            monologue_ratio = max(0.0, 1.0 - (total_turns / 10.0))

        # Scripted phrase detection from existing IVR scoring
        scripted_rate = 0.0
        if "ivr_transcript" in outcome or menu_detected:
            scripted_rate = 0.5

        features = {
            "acoustic": {
                "cadence_irregularity": 0.5,  # Default — we don't have acoustic features yet
                "waveform_entropy": 0.5,
                "background_noise_level": "low",
                "has_breathing": False,
            },
            "temporal": {
                "avg_first_audio_latency_ms": 0,
                "avg_full_turn_latency_ms": 0,
                "interruptions": interruptions,
                "overlaps": 0,
                "monologue_ratio": monologue_ratio,
                "greeting_duration_ms": 0,
            },
            "linguistic": {
                "merchant_word_count": effective_words,
                "alan_word_count": alan_words,
                "turn_count": total_turns,
                "questions_count": questions_count,
                "filler_rate": filler_rate,
                "scripted_phrase_rate": scripted_rate,
            },
            "behavioral": {
                "semantic_reactivity": semantic_reactivity,
                "menu_pattern_score": 0.7 if menu_detected else 0.0,
                "voicemail_phrase_score": 0.8 if voicemail_phrases else 0.0,
            },
        }

        return self.classify(features)
