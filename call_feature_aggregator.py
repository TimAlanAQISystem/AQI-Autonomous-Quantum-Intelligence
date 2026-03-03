"""
CallFeatureAggregator — Per-Turn CDC Logs → Per-Call Feature Dict
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Aggregates per-turn CDC data into the per-call feature dict
consumed by CallTypeClassifier.classify().

Can work with:
  1. Full per-turn feature dicts (future — when per-turn features are captured)
  2. CDC turns table rows (current — extracts what's available)

Author: Claude Opus 4.6 — AQI System Expert
Date: February 18, 2026
"""

import re
import logging
from collections import defaultdict
from statistics import mean
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ── Filler words for rate computation ──
FILLER_WORDS = {"uh", "um", "like", "hmm", "huh", "yeah", "yep", "mhm",
                "you know", "i mean", "sort of", "kind of"}

# ── Voicemail marker phrases ──
VOICEMAIL_MARKERS = [
    "leave a message", "after the tone", "after the beep",
    "leave your name", "leave your number", "not available",
    "reached the voicemail", "mailbox is full", "at the tone",
    "record your message", "leave a brief message",
    "personal greeting", "please leave",
]

# ── IVR / menu patterns ──
MENU_PATTERNS = [
    r"press\s+\d", r"for\s+(?:sales|billing|hours|directions|reservations)",
    r"option\s+\d", r"dial\s+\d", r"extension\s+\d",
    r"para\s+español", r"for\s+english",
    r"your\s+call\s+is\s+(?:important|being\s+recorded)",
    r"please\s+hold", r"transferring",
]
_menu_compiled = [re.compile(p, re.I) for p in MENU_PATTERNS]


class CallFeatureAggregator:
    """
    Aggregates per-turn data into per-call features for the classifier.
    """

    def aggregate_from_cdc_turns(self, call_id: str, turns: List[Dict],
                                  call_meta: Dict = None) -> Dict[str, Any]:
        """
        Build per-call feature dict from CDC turns table rows.

        Args:
            call_id: Call SID
            turns: List of dicts from CDC turns table
            call_meta: Optional call-level metadata (duration, outcome, etc.)

        Returns:
            Per-call feature dict suitable for CallTypeClassifier.classify()
        """
        if not turns:
            return self._empty_features(call_id)

        call_meta = call_meta or {}

        # ── Aggregate linguistic features ──
        merchant_word_counts = []
        alan_word_counts = []
        questions_count = 0
        filler_count = 0
        total_merchant_words = 0
        total_alan_words = 0
        scripted_phrases_found = 0

        # ── Aggregate temporal features ──
        first_audio_latencies = []
        full_turn_latencies = []
        interruptions = 0
        overlaps = 0

        # ── Behavioral ──
        voicemail_score = 0.0
        menu_score = 0.0
        semantic_turns = 0  # turns where merchant text seems responsive

        for t in turns:
            user_text = (t.get("user_text", "") or "").strip()
            alan_text = (t.get("alan_text", "") or "").strip()
            user_wc = t.get("user_word_count", 0) or len(user_text.split())
            alan_wc = t.get("alan_word_count", 0) or len(alan_text.split())

            merchant_word_counts.append(user_wc)
            alan_word_counts.append(alan_wc)
            total_merchant_words += user_wc
            total_alan_words += alan_wc

            user_lower = user_text.lower()

            # Questions
            if "?" in user_text:
                questions_count += 1

            # Fillers
            for filler in FILLER_WORDS:
                if filler in user_lower:
                    filler_count += 1

            # Voicemail markers
            for marker in VOICEMAIL_MARKERS:
                if marker in user_lower:
                    voicemail_score = max(voicemail_score, 0.8)

            # Menu / IVR patterns
            for pat in _menu_compiled:
                if pat.search(user_lower):
                    menu_score = max(menu_score, 0.7)
                    scripted_phrases_found += 1
                    break

            # Semantic reactivity (rough): user text contains 3+ unique words
            # and doesn't look like a script
            if user_wc >= 3 and "press" not in user_lower and "option" not in user_lower:
                semantic_turns += 1

            # Temporal from turn-level timing
            if t.get("total_turn_ms"):
                full_turn_latencies.append(t["total_turn_ms"])
            # We don't have per-turn first_audio yet, but if it's there, use it
            if t.get("first_audio_latency_ms"):
                first_audio_latencies.append(t["first_audio_latency_ms"])

        turn_count = len(turns)
        filler_rate = filler_count / max(total_merchant_words, 1)
        scripted_rate = scripted_phrases_found / max(turn_count, 1)

        # Semantic reactivity = fraction of turns with real content
        semantic_reactivity = semantic_turns / max(turn_count, 1)

        # Monologue ratio: high if merchant talks a lot but few turns
        if turn_count <= 1:
            monologue_ratio = 0.95
        elif turn_count <= 2:
            monologue_ratio = 0.6
        else:
            # More turns = less monologue
            monologue_ratio = max(0.0, 1.0 - (turn_count / 10.0))

        # Cadence irregularity: proxy from word count variance
        if len(merchant_word_counts) >= 2:
            avg_wc = mean(merchant_word_counts)
            if avg_wc > 0:
                variance = mean([(w - avg_wc) ** 2 for w in merchant_word_counts])
                cv = (variance ** 0.5) / avg_wc  # coefficient of variation
                cadence_irregularity = min(1.0, cv / 2.0)  # normalize
            else:
                cadence_irregularity = 0.1
        else:
            cadence_irregularity = 0.3  # default for single-turn

        return {
            "call_id": call_id,
            "acoustic": {
                "cadence_irregularity": round(cadence_irregularity, 3),
                "waveform_entropy": 0.5,  # placeholder — no raw audio analysis yet
                "background_noise_level": "low",  # placeholder
                "has_breathing": False,  # placeholder
            },
            "temporal": {
                "avg_first_audio_latency_ms": round(mean(first_audio_latencies), 1)
                    if first_audio_latencies else 0,
                "avg_full_turn_latency_ms": round(mean(full_turn_latencies), 1)
                    if full_turn_latencies else 0,
                "interruptions": interruptions,
                "overlaps": overlaps,
                "monologue_ratio": round(monologue_ratio, 3),
                "greeting_duration_ms": 0,  # could derive from first turn timing
            },
            "linguistic": {
                "merchant_word_count": total_merchant_words,
                "alan_word_count": total_alan_words,
                "turn_count": turn_count,
                "questions_count": questions_count,
                "filler_rate": round(filler_rate, 4),
                "scripted_phrase_rate": round(scripted_rate, 4),
            },
            "behavioral": {
                "semantic_reactivity": round(semantic_reactivity, 3),
                "menu_pattern_score": round(menu_score, 3),
                "voicemail_phrase_score": round(voicemail_score, 3),
            },
        }

    def aggregate_from_full_features(self, call_id: str,
                                      turns: List[Dict]) -> Dict[str, Any]:
        """
        Build per-call feature dict from FULL per-turn feature dicts.
        This is the future path — when per-turn features are fully captured.

        Args:
            call_id: Call SID
            turns: List of full per-turn feature dicts (with acoustic, temporal, etc.)
        """
        if not turns:
            return self._empty_features(call_id)

        # Linguistic
        merchant_word_counts = [t["merchant"]["word_count"] for t in turns]
        alan_word_counts = [t["alan"]["word_count"] for t in turns]
        questions_counts = [t["merchant"]["questions_count"] for t in turns]
        filler_rates = [t["merchant"]["filler_rate"] for t in turns]

        # Acoustic
        cadence_irregularities = [t["acoustic"]["cadence_irregularity"] for t in turns]
        waveform_entropies = [t["acoustic"]["waveform_entropy"] for t in turns]
        background_levels = [t["acoustic"]["background_noise_level"] for t in turns]

        # Temporal
        first_audio_latencies = [t["temporal"]["first_audio_latency_ms"] for t in turns]
        full_turn_latencies = [t["temporal"]["full_turn_latency_ms"] for t in turns]
        interruptions_list = [t["temporal"]["interruptions"] for t in turns]
        overlaps_list = [t["temporal"]["overlaps"] for t in turns]
        monologue_ratios = [t["behavioral"]["monologue_ratio"] for t in turns]

        # Behavioral
        menu_scores = [t["behavioral"]["menu_pattern_score"] for t in turns]
        voicemail_scores = [t["behavioral"]["voicemail_phrase_score"] for t in turns]
        semantic_scores = [t["merchant"]["semantic_reactivity_score"] for t in turns]

        bg_level = self._mode(background_levels)

        return {
            "call_id": call_id,
            "acoustic": {
                "cadence_irregularity": round(mean(cadence_irregularities), 3),
                "waveform_entropy": round(mean(waveform_entropies), 3),
                "background_noise_level": bg_level,
                "has_breathing": any(t.get("acoustic", {}).get("has_breathing") for t in turns),
            },
            "temporal": {
                "avg_first_audio_latency_ms": round(mean(first_audio_latencies), 1),
                "avg_full_turn_latency_ms": round(mean(full_turn_latencies), 1),
                "interruptions": sum(interruptions_list),
                "overlaps": sum(overlaps_list),
                "monologue_ratio": round(mean(monologue_ratios), 3),
                "greeting_duration_ms": first_audio_latencies[0] if first_audio_latencies else 0,
            },
            "linguistic": {
                "merchant_word_count": sum(merchant_word_counts),
                "alan_word_count": sum(alan_word_counts),
                "turn_count": len(turns),
                "questions_count": sum(questions_counts),
                "filler_rate": round(mean(filler_rates), 4),
                "scripted_phrase_rate": round(mean(menu_scores), 4),
            },
            "behavioral": {
                "semantic_reactivity": round(mean(semantic_scores), 3),
                "menu_pattern_score": round(mean(menu_scores), 3),
                "voicemail_phrase_score": round(mean(voicemail_scores), 3),
            },
        }

    def _empty_features(self, call_id: str) -> Dict[str, Any]:
        """Return empty features for calls with no turns."""
        return {
            "call_id": call_id,
            "acoustic": {
                "cadence_irregularity": 0.0,
                "waveform_entropy": 0.0,
                "background_noise_level": "low",
                "has_breathing": False,
            },
            "temporal": {
                "avg_first_audio_latency_ms": 0,
                "avg_full_turn_latency_ms": 0,
                "interruptions": 0,
                "overlaps": 0,
                "monologue_ratio": 1.0,
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

    @staticmethod
    def _mode(values):
        """Return the most common value in a list."""
        counter = defaultdict(int)
        for v in values:
            counter[v] += 1
        return max(counter, key=counter.get) if counter else "low"
