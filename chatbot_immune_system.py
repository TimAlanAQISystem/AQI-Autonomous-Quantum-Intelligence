#!/usr/bin/env python3
"""
CHATBOT IMMUNE SYSTEM
======================
Extracted from aqi_conversation_relay_server.py (was lines ~7043-7313).

This module is Alan's defense against sounding like a chatbot.
It strips markdown formatting, kills filler phrases, blocks premature
goodbyes, and detects repetition — all before sentences reach TTS.

The name reflects what it actually does: it's an immune system that
identifies and destroys chatbot-pattern "pathogens" in LLM output.

Integration:
    from chatbot_immune_system import clean_sentence
    
    # In _orchestrated_response:
    cleaned = clean_sentence(raw_sentence, context, logger)
    if not cleaned:
        continue  # Sentence was killed

Design Principles:
    - EVERY kill is logged (transparency for debugging)
    - Returns "" for killed sentences (never None)
    - Filler prefix stripping preserves the substance after the filler
    - Early-turn exit guard prevents LLM panic-goodbye on turns 0-3
    - Repetition detector has two modes: short-phrase exact + long-phrase overlap
    - All patterns are lowercase-normalized for matching

Neg-Proofed: Yes
    - No external state mutation (reads context, doesn't write)
    - No exceptions can escape (all matching is regex/string, no IO)
    - Returns original string if no patterns match (safe passthrough)
    - Empty string input returns empty string (no crash on edge case)

Author: Extracted by Claude Opus 4.6 — AQI Relay Decomposition Phase 1
Date: March 3, 2026
"""

import re
import logging
from typing import Optional

# Module logger — used when no external logger is passed
_module_logger = logging.getLogger("chatbot_immune_system")


# =============================================================================
# KILL LISTS — Chatbot patterns that must never reach the merchant's ear
# =============================================================================

# Exact-match kills: if the sentence IS this phrase (after lowering + stripping), kill it
CHATBOT_KILLS = [
    "that sounds great",
    "that sounds exciting",
    "looking forward to our chat",
    "looking forward to it",
    "in the meantime",
    "that's exciting",
    "that's great to hear",
    "that's wonderful",
    "absolutely",
    "of course",
    "great question",
    "got it",
    "okay, got it",
    "okay got it",
    "okay, sure",
    "right, got it",
    "that's a solid setup",
    "that's really solid",
    "nice setup",
    "yeah absolutely",
    "yeah, absolutely",
    "yeah",
    "yeah, sure",
    "sure thing",
    "i'm listening",
    "i'm right here",
    "i hear you",
    "i hear you, tell me more about that",
    "tell me more about that",
    "i appreciate that",
    "i appreciate your patience",
    "thanks for that",
    "i'm glad you're still with me",
    "i'm here to help",
    "i'm here to chat",
    "no problem at all",
    "no problem",
    "no worries at all",
    "thanks for giving me a minute",
    "thanks for your time",
    "i appreciate you mentioning that",
    "i appreciate you letting me know",
    "i appreciate you sharing that",
    "i appreciate you taking the time",
    "i understand completely",
    "totally understand",
    "i completely understand",
    "that makes total sense",
    "that makes sense",
    "fair enough",
    "have a good one",
    "have a great day",
    "have a great one",
    "take care",
    "i'll try again later",
    "i'll try back later",
    "i'll call back another time",
    "i'll reach out another time",
    "sounds like you're busy",
    "sounds like this isn't the right time",
    "sounds like i caught you at a bad time",
    "i don't want to take up your time",
    "i won't take up any more of your time",
]

# Partial-match kills: if the sentence CONTAINS this phrase, kill it
CHATBOT_CONTAINS_KILLS = [
    "i can help with that",
    "i can definitely help",
    "we can definitely help",
    "i'm here to help",
    "i'd love to help",
    "sounds great",
    "sounds exciting",
    "sounds wonderful",
    "sounds fantastic",
    "sounds like a great",
    "sounds like a valuable",
    "i appreciate you sharing",
    "i appreciate you mentioning",
    "i appreciate you letting me know",
    "i appreciate you taking",
    "thanks for sharing",
    "thanks for giving me",
    "thanks for letting me know",
    "that's really exciting",
    "how can i assist",
    "how may i help",
    "looking forward to",
    "solid setup",
    "great setup",
    "have a good one",
    "have a great day",
    "have a great one",
    "take care",
    "i'll try again later",
    "i'll try back",
    "i'll call back",
    "i'll reach out another",
    "i won't take up",
    "i don't want to take up",
    "caught you at a bad time",
    "sounds like you're busy",
    "isn't the right time",
    "i appreciate you picking up",
    "sounds like you're in a good",
    "sounds like you're having",
    "sounds like you're doing",
    "i don't want to keep you",
    "don't want to keep you",
    "that's totally understandable",
    "that's completely understandable",
    "i totally understand",
    "i completely understand",
    "of course",
]

# Filler prefixes: chatbot openers stripped from the START, preserving substance after
FILLER_PREFIXES = [
    "got it, ", "got it — ", "got it - ",
    "sure, ", "sure — ", "sure - ",
    "yeah, absolutely, ", "yeah absolutely, ",
    "yeah, so, ", "yeah so, ",
    "yeah, ", "yeah — ", "yeah - ",
    "absolutely, ",
    "perfect, ",
    "great, ",
    "of course, ", "of course — ", "of course! ",
    "right, got it, ",
    "okay, so, ", "okay so, ",
    "okay, ", "okay — ", "okay - ",
    "i'm listening, ", "i'm listening — ", "i'm listening. ",
    "i'm right here, ", "i'm right here — ", "i'm right here. ",
    "i hear you, ", "i hear you — ", "i hear you. ",
    "i appreciate that, ", "i appreciate that — ", "i appreciate that. ",
    "i appreciate you picking up, ", "i appreciate you picking up — ", "i appreciate you picking up. ",
    "thanks for that, ", "thanks for that — ", "thanks for that! ",
    "no problem, ", "no problem — ", "no problem. ",
    "no problem at all, ", "no problem at all — ", "no problem at all. ",
    "no worries, ", "no worries — ", "no worries. ",
    "totally, ", "totally — ",
    "totally understand, ", "totally understand — ",
    "i understand, ", "i understand — ",
    "fair enough, ", "fair enough — ",
    "that makes sense, ", "that makes sense — ", "that makes sense. ",
]

# Goodbye patterns blocked on turns 0-3 (early-turn exit guard)
GOODBYE_PATTERNS = [
    "goodbye", "good bye", "bye bye", "bye for now",
    "have a good", "have a great", "have a nice",
    "take care", "talk to you later", "talk soon",
    "i'll let you go", "i'll try again", "i'll try back",
    "i'll call back", "i'll reach out", "catch you later",
    "thanks for your time", "thank you for your time",
    "i won't take up", "i don't want to bother",
    "i don't want to keep you", "don't want to keep you",
    "sounds like you're busy", "caught you at a bad time",
    "isn't the right time", "not the right time",
    "maybe another time", "perhaps another time",
]


# =============================================================================
# CORE FUNCTION — The single chatbot killer + exit guard for all output paths
# =============================================================================

def clean_sentence(s: str, context: dict, log: Optional[logging.Logger] = None) -> str:
    """
    Strip markdown/list formatting AND chatbot patterns from LLM output.
    
    This is the SINGLE chatbot killer + exit guard function for all output paths.
    Extracted from aqi_conversation_relay_server.py for modularity.
    
    Args:
        s: Raw sentence from LLM
        context: Conversation context dict (needs 'messages' for repetition detection)
        log: Logger instance (falls back to module logger if None)
    
    Returns:
        Cleaned sentence string, or "" if the sentence was killed.
    """
    if not s or not s.strip():
        return ""
    
    logger = log or _module_logger
    
    # =========================================================================
    # PHASE 1: Markdown / formatting cleanup
    # =========================================================================
    
    # Remove **bold** markers
    s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)
    # Remove __bold__ markers
    s = re.sub(r'__([^_]+)__', r'\1', s)
    # Remove leading numbered list prefixes ("1. ", "2. ", etc.)
    s = re.sub(r'^\d+\.\s*', '', s)
    # Remove leading bullet markers
    s = re.sub(r'^[-*]\s+', '', s)
    # Remove markdown headers
    s = re.sub(r'^#+\s*', '', s)
    # Strip "Label: Description" format — e.g. "Business Information: Your name"
    # Only strip if the label part is 1-4 words followed by colon
    s = re.sub(r'^[A-Z][a-zA-Z]*(?:\s[A-Z][a-zA-Z]*){0,3}:\s*', '', s)
    
    # =========================================================================
    # PHASE 2: Filler prefix stripping
    # =========================================================================
    # "Got it, three different businesses" → "Three different businesses"
    # The filler adds nothing. The substance after it is what matters.
    
    s_lower_check = s.strip().lower()
    for prefix in FILLER_PREFIXES:
        if s_lower_check.startswith(prefix):
            stripped = s.strip()[len(prefix):]
            if stripped and len(stripped) > 3:
                # Capitalize the first letter of what remains
                stripped = stripped[0].upper() + stripped[1:]
                logger.info(f"[CHATBOT KILLER] Stripped filler prefix '{prefix.strip()}' → '{stripped[:50]}'")
                s = stripped
                break
    
    # =========================================================================
    # PHASE 3: Exact-match chatbot kills
    # =========================================================================
    
    s_lower = s.strip().lower().rstrip('!.')
    for kill in CHATBOT_KILLS:
        if s_lower == kill or s_lower.startswith(kill):
            logger.info(f"[CHATBOT KILLER] Stripped dead phrase: '{s[:50]}'")
            return ""
    
    # =========================================================================
    # PHASE 4: Contains-match chatbot kills
    # =========================================================================
    
    for kill in CHATBOT_CONTAINS_KILLS:
        if kill in s_lower:
            logger.info(f"[CHATBOT KILLER] Stripped (contains): '{s[:50]}'")
            return ""
    
    # =========================================================================
    # PHASE 5: Early-turn exit guard (turns 0-3)
    # =========================================================================
    # On turns 0-3, Alan MUST NOT say goodbye.
    # The LLM sometimes panics on ambiguous audio and tries to bail.
    
    _etg_turn = len(context.get('messages', [])) // 2
    if _etg_turn <= 3:
        for _gp in GOODBYE_PATTERNS:
            if _gp in s_lower:
                logger.warning(f"[EXIT GUARD] Blocked goodbye on turn {_etg_turn}: '{s[:60]}'")
                return ""
    
    # =========================================================================
    # PHASE 6: Repetition detector (two modes)
    # =========================================================================
    
    _rep_turn = len(context.get('messages', []))
    _prev_msgs = context.get('messages', [])
    _s_stripped = s.strip()
    _s_word_count = len(_s_stripped.split())
    
    # MODE A: SHORT-PHRASE exact-match (1-4 words)
    # If Alan has said this exact phrase 2+ times recently, block it.
    if _rep_turn >= 3 and 1 <= _s_word_count <= 4:
        _s_norm = _s_stripped.lower().rstrip('!.?,')
        _short_repeat_count = 0
        for _pm in _prev_msgs:
            _prev_alan = (_pm.get('alan', '') or '').strip()
            if not _prev_alan:
                continue
            # Check each sentence in previous Alan response
            for _prev_sent in re.split(r'[.!?]+', _prev_alan):
                _prev_norm = _prev_sent.strip().lower().rstrip('!.?,')
                if _prev_norm == _s_norm:
                    _short_repeat_count += 1
        if _short_repeat_count >= 2:
            logger.warning(
                f"[REPETITION DETECTOR] Blocked short repeated phrase "
                f"(turn {_rep_turn}, {_short_repeat_count}x): '{_s_stripped[:60]}'"
            )
            return ""
    
    # MODE B: LONG-PHRASE word-overlap (5+ words)
    if _rep_turn >= 3 and _s_word_count >= 5:
        _s_words = set(_s_stripped.lower().split())
        for _pm in _prev_msgs:
            _prev_alan = (_pm.get('alan', '') or '').strip()
            if not _prev_alan or len(_prev_alan.split()) < 5:
                continue
            # Check each previous Alan sentence individually
            for _prev_sent in re.split(r'[.!?]+', _prev_alan):
                _prev_sent = _prev_sent.strip()
                if len(_prev_sent.split()) < 5:
                    continue
                _prev_words = set(_prev_sent.lower().split())
                _overlap = len(_s_words & _prev_words)
                _ratio = _overlap / min(len(_s_words), len(_prev_words))
                if _ratio > 0.70:
                    logger.warning(
                        f"[REPETITION DETECTOR] Blocked repeated phrase (turn {_rep_turn}, "
                        f"overlap={_ratio:.0%}): '{_s_stripped[:60]}'"
                    )
                    return ""
    
    return _s_stripped
