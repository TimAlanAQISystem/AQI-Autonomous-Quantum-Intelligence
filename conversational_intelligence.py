"""
+==============================================================================+
|   CONVERSATIONAL INTELLIGENCE MODULE                                          |
|   AQI Agent Alan — Behavioral Intelligence Fixes                              |
|                                                                               |
|   PURPOSE:                                                                    |
|   Seven critical conversational intelligence systems that make Alan behave    |
|   like a human operator with judgment, awareness, and adaptive reasoning.     |
|                                                                               |
|   SYSTEMS:                                                                    |
|   1. COMPLIANCE INTERRUPT (DNC) — instant termination on DNC request          |
|   2. VOICEMAIL DETECTOR — recognize voicemail prompts, leave clean message    |
|   3. ENTITY CLASSIFIER — identify government/non-merchant entities            |
|   4. REPETITION BREAKER — Alan-side response dedup + hard bail               |
|   5. LATENCY BRIDGE — sub-1.5s bridging utterances during slow LLM           |
|   6. DEAD-END DETECTOR — recognize stalled conversations, exit gracefully    |
|   7. SHORT-CALL OUTCOME FALLBACK — eliminate "unknown" outcomes              |
|                                                                               |
|   WIRING:                                                                    |
|   All systems expose simple check functions called from                       |
|   handle_user_speech() in aqi_conversation_relay_server.py                    |
|                                                                               |
|   LINEAGE: Built 2026-02-17. Tim's directive: "These are the difference      |
|   between a machine that talks and a representative who sells."              |
+==============================================================================+
"""

import re
import time
import random
import logging
from difflib import SequenceMatcher
from typing import Optional, Dict, Tuple, List

logger = logging.getLogger("CONV_INTEL")


# ======================================================================
#  1. COMPLIANCE INTERRUPT — DNC Hard Stop
# ======================================================================
# Rule: DNC = instant termination. No exceptions.
# If merchant says "do not call", "remove me", "stop calling", or variant:
#   → Confirm removal
#   → Say goodbye
#   → Hang up
#   → Log outcome as "dnc_request"
# ======================================================================

DNC_PATTERNS = [
    re.compile(r"\b(?:do\s+not\s+call|don'?t\s+call)\b", re.IGNORECASE),
    re.compile(r"\b(?:remove\s+(?:me|us|my\s+number|this\s+number))\b", re.IGNORECASE),
    re.compile(r"\b(?:stop\s+calling|quit\s+calling|no\s+more\s+calls)\b", re.IGNORECASE),
    re.compile(r"\b(?:take\s+(?:me|us|my\s+number)\s+off)\b", re.IGNORECASE),
    re.compile(r"\b(?:put\s+(?:me|us)\s+on\s+(?:your|the)\s+(?:do\s+not\s+call|dnc))\b", re.IGNORECASE),
    re.compile(r"\b(?:unsubscribe|opt\s*out)\b", re.IGNORECASE),
    re.compile(r"\b(?:not\s+interested\s+(?:ever|at\s+all|in\s+any))\b", re.IGNORECASE),
    re.compile(r"\b(?:never\s+call\s+(?:me|us|here|again|this\s+number))\b", re.IGNORECASE),
    re.compile(r"\b(?:add\s+(?:me|us|this)\s+to\s+(?:your|the)\s+(?:do\s+not|no)\s+call)\b", re.IGNORECASE),
    re.compile(r"\bdn(?:c|cl)\s*list\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+call\s+list\b", re.IGNORECASE),
]

DNC_GOODBYE_LINES = [
    "Absolutely, I'll remove your number right away. Sorry for the interruption. Have a great day.",
    "Done — your number's been removed. Apologies for the call. Take care.",
    "Got it, removing you now. Won't happen again. Have a good one.",
]


class ComplianceInterrupt:
    """Detects DNC/removal requests and forces immediate call termination."""
    
    def __init__(self):
        self.triggered = False
        self.trigger_text = None
    
    def check(self, user_text: str) -> Optional[Dict]:
        """
        Check if user_text contains a DNC request.
        
        Returns:
            None if no DNC detected.
            Dict with keys: 'is_dnc', 'goodbye_line', 'outcome' if DNC triggered.
        """
        if self.triggered:
            # Already triggered — don't re-fire
            return None
        
        text_lower = user_text.lower().strip()
        
        for pattern in DNC_PATTERNS:
            if pattern.search(text_lower):
                self.triggered = True
                self.trigger_text = user_text
                goodbye = random.choice(DNC_GOODBYE_LINES)
                logger.warning(f"[DNC] COMPLIANCE INTERRUPT — trigger: '{user_text[:80]}' — CALL MUST END NOW")
                return {
                    'is_dnc': True,
                    'goodbye_line': goodbye,
                    'outcome': 'dnc_request',
                    'trigger': user_text[:100],
                }
        
        return None


# ======================================================================
#  2. VOICEMAIL DETECTOR
# ======================================================================
# Detects voicemail system prompts that IVR detector might miss.
# Separate from IVR because voicemail requires a DIFFERENT action:
#   IVR → hang up immediately (no audience)
#   Voicemail → leave a clean 7-10 second message → hang up
# ======================================================================

VOICEMAIL_PATTERNS = [
    re.compile(r"(?:at|after)\s+the\s+(?:tone|beep)", re.IGNORECASE),
    re.compile(r"(?:please\s+)?(?:leave|record)\s+(?:a\s+)?(?:message|voicemail)", re.IGNORECASE),
    re.compile(r"(?:no\s+one|nobody)\s+is\s+(?:available|here)", re.IGNORECASE),
    re.compile(r"(?:mailbox|voicemail\s+box)\s+is\s+full", re.IGNORECASE),
    re.compile(r"(?:you(?:'ve| have)\s+reached|this is)\s+the\s+(?:voicemail|mailbox|answering)", re.IGNORECASE),
    re.compile(r"to\s+(?:send|cancel|delete|re-?record)\s+(?:this|your)\s+message", re.IGNORECASE),
    re.compile(r"(?:press|hit)\s+(?:pound|hash|star)\s+(?:to\s+send|when\s+done|or\s+hang\s+up)", re.IGNORECASE),
    re.compile(r"person\s+(?:you\s+(?:are|have)\s+)?(?:called|dialed|reached)\s+is\s+(?:unavailable|not\s+available)", re.IGNORECASE),
    re.compile(r"hang\s+up\s+(?:or\s+)?press\s+(?:pound|star|hash)", re.IGNORECASE),
    re.compile(r"to\s+page\s+this\s+person", re.IGNORECASE),
    re.compile(r"when\s+you(?:'ve| have)\s+finished\s+recording", re.IGNORECASE),
    re.compile(r"(?:begin|start)\s+(?:speaking|recording)\s+(?:at|after)\s+the", re.IGNORECASE),
    re.compile(r"press\s+(?:pound|hash|star)\s+or\s+hang\s+up", re.IGNORECASE),
]

# Voicemail messages — short, professional, leave callback hook
VOICEMAIL_MESSAGES = [
    "Hey, this is Alan from Signature Card Services. I was looking at your processing setup and had a quick idea to save you some money. Give me a call back when you get a sec. Thanks!",
    "Hi, it's Alan with Signature Card Services. Just wanted to touch base about your card processing rates — might have some savings for you. Call me back when you have a minute. Thanks!",
    "Hey, Alan here from Signature Card Services. Quick call about your processing fees — I think we can help. Give me a ring back when you're free. Have a good one!",
]


class VoicemailDetector:
    """Detects voicemail prompts and triggers clean message delivery."""
    
    def __init__(self):
        self.confidence = 0.0
        self.pattern_hits: List[str] = []
        self.triggered = False
        self._utterance_count = 0
        # Track if we see beep/tone timing patterns
        self._silence_after_prompt = False
    
    def check(self, user_text: str, elapsed_seconds: float = 0) -> Optional[Dict]:
        """
        Check if user_text indicates a voicemail system.
        
        Args:
            user_text: STT transcription of what was heard.
            elapsed_seconds: Seconds since call started.
            
        Returns:
            None if no voicemail detected.
            Dict with 'is_voicemail', 'voicemail_message', 'confidence' if detected.
        """
        if self.triggered:
            return None
        
        self._utterance_count += 1
        text_lower = user_text.lower().strip()
        
        # Check patterns
        hits_this_turn = 0
        for pattern in VOICEMAIL_PATTERNS:
            if pattern.search(text_lower):
                hits_this_turn += 1
                self.pattern_hits.append(pattern.pattern[:50])
        
        # Score voicemail confidence
        if hits_this_turn > 0:
            # Each hit adds 0.35, and multiple hits in one utterance are very strong
            self.confidence += 0.35 * hits_this_turn
            # Bonus for multiple distinct patterns
            if len(set(self.pattern_hits)) >= 2:
                self.confidence += 0.15
        
        # Long monologue without questions → voicemail greeting
        words = text_lower.split()
        if len(words) > 20 and '?' not in text_lower and self._utterance_count <= 3:
            # 20+ word monologue at the start of the call with no questions = likely voicemail
            self.confidence += 0.10
        
        # Trigger at threshold
        if self.confidence >= 0.60:
            self.triggered = True
            message = random.choice(VOICEMAIL_MESSAGES)
            logger.warning(f"[VOICEMAIL] DETECTED (confidence={self.confidence:.2f}) — leaving message")
            return {
                'is_voicemail': True,
                'voicemail_message': message,
                'confidence': self.confidence,
                'outcome': 'voicemail_message_left',
                'pattern_hits': self.pattern_hits[:5],
            }
        
        return None


# ======================================================================
#  3. ENTITY CLASSIFIER — Government/Non-Merchant Detection
# ======================================================================
# Rule: If entity is government or non-merchant → immediate polite exit.
# Checks both the merchant name (from lead data) and the speech content.
# ======================================================================

# Government/non-merchant keywords in business names
GOVERNMENT_NAME_PATTERNS = [
    re.compile(r"\b(?:department\s+of|dept\s+of|office\s+of)\b", re.IGNORECASE),
    re.compile(r"\b(?:state\s+(?:of|department)|federal|government|gov(?:t)?)\b", re.IGNORECASE),
    re.compile(r"\b(?:county\s+(?:of|clerk|court)|city\s+(?:of|hall|council))\b", re.IGNORECASE),
    re.compile(r"\b(?:secretary\s+of\s+state|attorney\s+general)\b", re.IGNORECASE),
    re.compile(r"\b(?:IRS|FBI|CIA|NSA|DOD|DOJ|EPA|FDA|USDA|HHS|HUD|DHS)\b"),
    re.compile(r"\b(?:DMV|SSA|VA\b|SBA)\b"),
    re.compile(r"\b(?:civil\s+service|public\s+(?:works|safety|health|defender))\b", re.IGNORECASE),
    re.compile(r"\b(?:board\s+of\s+(?:education|supervisors|elections))\b", re.IGNORECASE),
    re.compile(r"\b(?:municipal|township|borough|parish)\b", re.IGNORECASE),
    re.compile(r"\b(?:U\.?S\.?\s+(?:Army|Navy|Air\s+Force|Marines|Coast\s+Guard))\b", re.IGNORECASE),
    re.compile(r"\b(?:police|sheriff|fire\s+department|EMS)\b", re.IGNORECASE),
    re.compile(r"\b(?:school\s+district|public\s+school|university\s+of)\b", re.IGNORECASE),
    re.compile(r"\b(?:national\s+(?:guard|park|forest|lab))\b", re.IGNORECASE),
    re.compile(r"\b(?:defense\s+(?:contract|logistics|information))\b", re.IGNORECASE),
]

# Speech-based government indicators (what IVR menus say)
GOVERNMENT_SPEECH_PATTERNS = [
    re.compile(r"(?:state|federal|county|city)\s+(?:agency|department|office|bureau)", re.IGNORECASE),
    re.compile(r"(?:tax\s+board|franchise\s+tax|revenue\s+service|tax\s+commission)", re.IGNORECASE),
    re.compile(r"(?:driver.s?\s+license|vehicle\s+registration|vital\s+records)", re.IGNORECASE),
    re.compile(r"(?:file\s+(?:your|a)\s+(?:tax|return|claim|complaint))", re.IGNORECASE),
    re.compile(r"(?:government\s+(?:service|program|assistance|benefit))", re.IGNORECASE),
    re.compile(r"(?:social\s+security|medicaid|medicare)\b", re.IGNORECASE),
    re.compile(r"(?:statements?\s+of\s+information)\b", re.IGNORECASE),
    re.compile(r"(?:biz\s*file|business\s+registration\s+(?:portal|system))", re.IGNORECASE),
]

GOVERNMENT_EXIT_LINES = [
    "I think I may have reached the wrong number — this sounds like a government office. My apologies for the interruption. Have a great day!",
    "Sorry about that, sounds like I've reached a government agency. Wrong number on my end. Take care!",
    "Ah, this is a government line — my mistake. Sorry to bother you. Have a good one!",
]


class EntityClassifier:
    """Classifies call target as government/non-merchant and triggers polite exit."""
    
    def __init__(self):
        self.government_score = 0.0
        self.entity_type = 'unknown'  # unknown, retail, government, non_profit
        self.triggered = False
        self._checks_run = 0
    
    def check_name(self, merchant_name: str) -> Optional[Dict]:
        """
        Check merchant name for government/non-merchant indicators.
        Called ONCE at call start from lead data.
        
        Returns Dict if government detected, None otherwise.
        """
        if not merchant_name or self.triggered:
            return None
        
        name_lower = merchant_name.lower()
        hits = 0
        for pattern in GOVERNMENT_NAME_PATTERNS:
            if pattern.search(name_lower):
                hits += 1
        
        if hits >= 1:
            self.government_score += 0.4 * hits
            logger.info(f"[ENTITY] Government indicators in name '{merchant_name}': +{hits} hits (score={self.government_score:.2f})")
        
        # Strong single-hit names (department of, secretary of state, etc.)
        if hits >= 2 or self.government_score >= 0.75:
            return self._trigger_exit(merchant_name)
        
        return None
    
    def check_speech(self, user_text: str) -> Optional[Dict]:
        """
        Check speech content for government indicators.
        Called each turn from speech processing.
        
        Returns Dict if government detected with enough evidence, None otherwise.
        """
        if self.triggered:
            return None
        
        self._checks_run += 1
        text_lower = user_text.lower()
        
        hits = 0
        for pattern in GOVERNMENT_SPEECH_PATTERNS:
            if pattern.search(text_lower):
                hits += 1
        
        if hits > 0:
            self.government_score += 0.30 * hits
            logger.info(f"[ENTITY] Government speech detected (hits={hits}, total_score={self.government_score:.2f})")
        
        # Need strong evidence from speech (multiple indicators)
        if self.government_score >= 0.85:
            return self._trigger_exit(user_text[:80])
        
        return None
    
    def _trigger_exit(self, context_hint: str) -> Dict:
        self.triggered = True
        self.entity_type = 'government'
        exit_line = random.choice(GOVERNMENT_EXIT_LINES)
        logger.warning(f"[ENTITY] GOVERNMENT ENTITY CONFIRMED — exiting call. Hint: '{context_hint}'")
        return {
            'is_government': True,
            'exit_line': exit_line,
            'government_score': self.government_score,
            'outcome': 'government_entity',
            'entity_type': 'government',
        }


# ======================================================================
#  4. REPETITION BREAKER — Alan's Own Response Dedup + Hard Bail
# ======================================================================
# The existing repetition escalation detects MERCHANT repeating.
# This detects ALAN repeating himself — the "I'm Listening" loop.
#
# Escalation Ladder:
#   1. Normal response
#   2. Same intent → force different phrasing
#   3. Still same → "I think we might have a connection issue"
#   4. Still same → bail: "Let me try you back another time"
#   5. Hard kill — hang up
# ======================================================================

# Short responses that Alan tends to loop on
ALAN_LOOP_PHRASES = {
    "i'm listening", "im listening", "i am listening",
    "can you hear me", "hello", "yeah", "i'm right here",
    "i'm here", "i hear you", "go ahead",
}


class RepetitionBreaker:
    """Detects when Alan is repeating himself and forces escalation or bail."""
    
    def __init__(self):
        self.alan_response_history: List[str] = []
        self.consecutive_similar = 0
        self.bail_triggered = False
    
    def record_response(self, alan_text: str):
        """Record what Alan said for loop detection."""
        if alan_text:
            self.alan_response_history.append(alan_text.lower().strip())
            if len(self.alan_response_history) > 12:
                self.alan_response_history = self.alan_response_history[-12:]
    
    def check_before_response(self, proposed_response: str = None) -> Optional[Dict]:
        """
        Called AFTER LLM generates response but BEFORE TTS.
        Checks if Alan is repeating himself.
        
        Returns:
            None if OK.
            Dict with 'action' (force_rephrase|bail|hard_kill) and guidance.
        """
        if self.bail_triggered:
            return {'action': 'hard_kill', 'line': "Take care. Goodbye."}
        
        if not self.alan_response_history or not proposed_response:
            return None
        
        proposed_lower = proposed_response.lower().strip()
        
        # Check for exact loop phrases
        is_loop_phrase = any(proposed_lower.startswith(lp) or proposed_lower == lp 
                           for lp in ALAN_LOOP_PHRASES)
        
        # Count consecutive similar responses
        similar_count = 0
        for prev in reversed(self.alan_response_history[-6:]):
            sim = SequenceMatcher(None, proposed_lower, prev).ratio()
            if sim > 0.60 or (is_loop_phrase and any(prev.startswith(lp) for lp in ALAN_LOOP_PHRASES)):
                similar_count += 1
            else:
                break
        
        self.consecutive_similar = similar_count
        
        if similar_count >= 4:
            # Hard bail — 5th time saying the same thing
            self.bail_triggered = True
            logger.warning(f"[REP BREAKER] HARD BAIL — Alan repeated himself {similar_count}+ times")
            return {
                'action': 'bail',
                'line': "I think we might have a bad connection. Let me try you back another time. Take care!",
                'outcome': 'repetition_bail',
            }
        elif similar_count >= 2:
            # Connection check — 3rd+ time
            logger.warning(f"[REP BREAKER] Connection check — {similar_count} consecutive similar responses")
            return {
                'action': 'force_rephrase',
                'directive': (
                    "[CRITICAL] You have said nearly the same thing multiple times in a row. "
                    "The call may be stuck. Say something COMPLETELY DIFFERENT. Options:\n"
                    "- 'I think we might have a connection issue — can you hear me clearly?'\n"
                    "- 'Let me try a different approach — what's the best way to reach you?'\n"
                    "- 'Sounds like the line is breaking up. I'll try calling back later.'\n"
                    "DO NOT say 'I'm listening' again."
                ),
            }
        elif similar_count >= 1:
            # Light nudge — 2nd time
            return {
                'action': 'nudge',
                'directive': (
                    "[NOTICE] Your last response was very similar to this one. "
                    "Change your approach. Ask a NEW question or make a DIFFERENT observation."
                ),
            }
        
        return None


# ======================================================================
#  5. LATENCY BRIDGE — Sub-1.5s Bridging Utterances
# ======================================================================
# Rule: Alan must respond within 1.2-1.5 seconds, even if LLM is slow.
# These are pre-computed filler utterances that buy time while the full
# response generates. Sent as TTS-ready text.
#
# IMPORTANT: Bridging only triggers if LLM is taking >1200ms.
# Normal fast responses skip this entirely.
# ======================================================================

# Context-aware bridging utterances — varies by call state
BRIDGE_UTTERANCES = {
    'default': [
        "So...",
        "Right, so...",
        "Sure, so...",
        "Of course...",
    ],
    'after_question': [
        "Good question...",
        "Sure, so...",
        "Right...",
    ],
    'after_info': [
        "Got it...",
        "Okay...",
        "Right...",
    ],
    'after_objection': [
        "I hear you...",
        "Fair enough...",
        "I get that...",
    ],
}


class LatencyBridge:
    """
    Provides bridging utterances when LLM response exceeds latency threshold.
    
    Usage:
        bridge = LatencyBridge()
        
        # When turn starts:
        bridge.mark_turn_start()
        
        # After pre-processing, before LLM call:
        if bridge.should_bridge(preprocess_ms):
            bridging_text = bridge.get_bridge(context_type='default')
            # Send bridging_text to TTS immediately
        
        # LLM response arrives normally after bridge plays
    """
    
    THRESHOLD_MS = 1200  # Bridge if pre-processing already took this long
    LLM_EXPECTED_MS = 800  # Expected additional LLM time
    
    def __init__(self):
        self._turn_start = None
        self._last_bridge = None
        self._bridge_count = 0
        self._used_bridges: List[str] = []
    
    def mark_turn_start(self):
        """Call when user speech is received."""
        self._turn_start = time.time()
    
    def should_bridge(self, preprocess_elapsed_ms: float) -> bool:
        """
        Should we send a bridging utterance?
        True if pre-processing has already consumed enough time that
        the full pipeline will exceed 1.5s.
        """
        # If pre-processing + expected LLM time > threshold, bridge
        estimated_total = preprocess_elapsed_ms + self.LLM_EXPECTED_MS
        should = estimated_total > self.THRESHOLD_MS
        
        if should:
            logger.info(f"[BRIDGE] Triggering — preprocess={preprocess_elapsed_ms:.0f}ms, "
                       f"estimated_total={estimated_total:.0f}ms > {self.THRESHOLD_MS}ms")
        
        return should
    
    def get_bridge(self, context_type: str = 'default') -> str:
        """
        Get a bridging utterance. Avoids repeating the same bridge.
        
        Args:
            context_type: 'default', 'after_question', 'after_info', 'after_objection'
        """
        options = BRIDGE_UTTERANCES.get(context_type, BRIDGE_UTTERANCES['default'])
        
        # Filter out recently used bridges
        available = [b for b in options if b not in self._used_bridges[-3:]]
        if not available:
            available = options
        
        bridge = random.choice(available)
        self._used_bridges.append(bridge)
        self._bridge_count += 1
        self._last_bridge = bridge
        
        if len(self._used_bridges) > 10:
            self._used_bridges = self._used_bridges[-10:]
        
        logger.info(f"[BRIDGE] Sending: '{bridge}' (count={self._bridge_count})")
        return bridge


# ======================================================================
#  6. DEAD-END DETECTOR — Stalled Conversation Exit
# ======================================================================
# Rule: If conversation makes no progress for N turns, bail gracefully.
# "Progress" = new information, new intent, advancement toward goal.
# "No progress" = repeated objections, silence, circular talk.
# ======================================================================

# Phrases indicating no progress (merchant wants to end but isn't explicit)
NO_PROGRESS_PHRASES = [
    re.compile(r"\b(?:we(?:'re| are)\s+(?:fine|good|all\s+set|happy|okay))\b", re.IGNORECASE),
    re.compile(r"\b(?:not\s+(?:interested|looking|in\s+the\s+market))\b", re.IGNORECASE),
    re.compile(r"\b(?:no\s+(?:thanks?|thank\s+you))\b", re.IGNORECASE),
    re.compile(r"\b(?:we\s+don'?t\s+need|don'?t\s+want)\b", re.IGNORECASE),
    re.compile(r"\b(?:i'?m?\s+busy|bad\s+time|call\s+(?:back|later|another))\b", re.IGNORECASE),
    re.compile(r"\b(?:already\s+have|happy\s+with)\b", re.IGNORECASE),
]

DEAD_END_EXIT_LINES = [
    "I don't want to keep you — thanks for your time. Have a great day!",
    "Sounds like this isn't the right time. I appreciate your time — take care!",
    "I hear you. Thanks for giving me a minute. Have a good one!",
]


# [2026-02-24 FIX] ACKNOWLEDGMENT WHITELIST
# These phrases indicate passive listening — the merchant is still there,
# just not actively engaging yet. They should NOT count as dead turns
# (which would trigger dead_end_exit and kill the call).
# Tim: "What my concern would be, is if it may interfere with an actual human caller?"
ACKNOWLEDGMENT_PHRASES = re.compile(
    r"^(?:"
    r"(?:uh|u)\s*h(?:uh|m+)|"           # uh huh, uhm, uh hm
    r"(?:m+h*m+)|"                       # mm, mmhm, mhm
    r"(?:okay|ok|o\.?k\.?)|"            # okay, ok, o.k.
    r"(?:yeah|yea|yep|yup|ya)|"          # yeah, yep, yup
    r"(?:sure)|"                         # sure
    r"(?:right)|"                        # right
    r"(?:go\s+(?:on|ahead))|"           # go on, go ahead
    r"(?:i\s+see)|"                     # i see
    r"(?:got\s+it)|"                    # got it
    r"(?:alright|all\s+right)|"         # alright, all right
    r"(?:i'?m\s+listening)|"            # i'm listening
    r"(?:tell\s+me\s+more)|"            # tell me more
    r"(?:continue)|"                     # continue
    r"(?:and\??)|"                       # and? and
    r"(?:so\??)"                         # so? so
    r")[.\?!,]*$",                       # optional trailing punctuation
    re.IGNORECASE
)


class DeadEndDetector:
    """Detects stalled conversations and triggers graceful exit."""
    
    def __init__(self, max_dead_turns: int = 3):
        self.max_dead_turns = max_dead_turns
        self.dead_turn_count = 0
        self.rejection_count = 0
        self.triggered = False
        self._turn_count = 0
        self._last_had_progress = False
        self._ack_count = 0  # Track consecutive acknowledgments
    
    def check(self, user_text: str, analysis: dict = None) -> Optional[Dict]:
        """
        Check if conversation is going nowhere.
        
        Args:
            user_text: What the merchant said
            analysis: Analysis dict from pipeline (optional, for interest_level/sentiment)
            
        Returns:
            None if conversation still has life.
            Dict with 'should_exit', 'exit_line', 'outcome' if dead-end.
        """
        if self.triggered:
            return None
        
        self._turn_count += 1
        text_lower = user_text.lower().strip()
        
        # [2026-02-24 FIX] Check for acknowledgments FIRST.
        # Acknowledgments ("uh huh", "okay", "go on") indicate passive listening.
        # They should HOLD the dead_turn_count (not increment), giving the merchant
        # more runway to engage. A merchant who is listening is NOT a dead end.
        # However, 5+ consecutive acknowledgments with zero progress is still dead.
        is_acknowledgment = bool(ACKNOWLEDGMENT_PHRASES.match(text_lower))
        if is_acknowledgment:
            self._ack_count += 1
            if self._ack_count < 5:  # Up to 4 acks in a row → hold, don't increment
                logger.debug(f"[DEAD-END] Acknowledgment detected: '{text_lower}' — holding counter (ack #{self._ack_count})")
                return None  # Don't increment, don't reset — just hold
            # 5+ acks: fall through to normal logic (will count as no-progress)
        else:
            self._ack_count = 0  # Reset ack streak on any non-ack response
        
        # Check for rejection/no-progress phrases
        is_rejection = False
        for pattern in NO_PROGRESS_PHRASES:
            if pattern.search(text_lower):
                is_rejection = True
                break
        
        # Also check analysis signals
        if analysis:
            interest = analysis.get('interest_level', 'medium')
            sentiment = analysis.get('sentiment', 'neutral')
            if interest == 'low' and sentiment == 'negative':
                is_rejection = True
        
        if is_rejection:
            self.rejection_count += 1
            self.dead_turn_count += 1
            self._last_had_progress = False
        else:
            # Check for actual progress indicators
            has_progress = False
            # New info: user provided details, asked questions, showed engagement
            if '?' in text_lower and len(text_lower) > 15:
                has_progress = True  # They're asking questions = engaged
            if len(text_lower.split()) > 10 and not is_rejection:
                has_progress = True  # Substantive response = engaged
            if analysis and analysis.get('interest_level') in ('medium', 'high'):
                has_progress = True
            
            if has_progress:
                self.dead_turn_count = 0  # Reset on progress
                self._last_had_progress = True
            else:
                # Short, non-rejection but non-progress (e.g., "hm", "what")
                self.dead_turn_count += 1
                self._last_had_progress = False
        
        # Trigger exit if too many dead turns
        if self.dead_turn_count >= self.max_dead_turns and self._turn_count >= 4:
            self.triggered = True
            exit_line = random.choice(DEAD_END_EXIT_LINES)
            logger.warning(f"[DEAD-END] Triggered after {self.dead_turn_count} dead turns, "
                          f"{self.rejection_count} rejections in {self._turn_count} total turns")
            return {
                'should_exit': True,
                'exit_line': exit_line,
                'outcome': 'dead_end_exit',
                'dead_turns': self.dead_turn_count,
                'rejection_count': self.rejection_count,
            }
        
        return None


# ======================================================================
#  7. SHORT-CALL OUTCOME FALLBACK — Eliminate "Unknown" Outcomes
# ======================================================================
# Rule: No more "unknown" outcomes. Every call gets a classification.
# If the primary ODL classifier returns "unknown", apply these fallbacks:
#   < 1 human turn → "no_answer"
#   1-2 turns, no intent → "no_engagement"
#   Voicemail → "voicemail_message_left"
#   IVR → "ivr_detected"
#   DNC → "dnc_request"
#   Government → "government_entity"
#   Dead-end exit → "clear_rejection"
# ======================================================================

class ShortCallOutcomeFallback:
    """
    Reclassifies "unknown" outcomes using simple heuristics.
    Called at call end, AFTER primary ODL classification.
    """
    
    @staticmethod
    def reclassify(current_outcome: str, context: dict) -> str:
        """
        If outcome is 'unknown', apply fallback rules.
        Also applies human override: if merchant spoke 40+ words across 3+ turns,
        force human classification regardless of IVR/voicemail markers.
        
        Args:
            current_outcome: The ODL-classified outcome (may be 'unknown')
            context: conversation_context dict with messages, guard results, etc.
            
        Returns:
            Reclassified outcome string.
        """
        messages = context.get('messages', [])
        human_turns = len([m for m in messages if m.get('user', '').strip()])
        total_merchant_words = sum(len((m.get('user', '') or '').split()) for m in messages)
        
        # [PHASE 1] Human override — prevent IVR/voicemail misclassification
        # Enough words + turns = real conversation, block sentinel outcomes
        _sentinel_outcomes = {'voicemail_ivr', 'ivr_transcript_kill', 'ivr_timeout_kill',
                              'silence_kill', 'air_call_kill'}
        if (total_merchant_words >= 40 and human_turns >= 3 
                and current_outcome in _sentinel_outcomes):
            logger.info(f"[OUTCOME FALLBACK] Human override: {current_outcome} → kept_engaged "
                       f"(words={total_merchant_words}, turns={human_turns})")
            return 'kept_engaged'
        
        if current_outcome and current_outcome.lower() not in ('unknown', ''):
            return current_outcome  # ODL already classified — trust it
        
        messages = context.get('messages', [])
        human_turns = len([m for m in messages if m.get('user', '').strip()])
        
        # Check guard results first (most specific)
        guard_outcome = context.get('_guard_outcome')
        if guard_outcome:
            logger.info(f"[OUTCOME FALLBACK] Guard outcome: {guard_outcome}")
            return guard_outcome
        
        # IVR quarantine
        if context.get('_ccnm_ignore'):
            return context.get('_evolution_outcome', 'ivr_detected')
        
        # Turn-count based fallbacks
        if human_turns == 0:
            logger.info("[OUTCOME FALLBACK] 0 human turns → no_answer")
            return 'no_answer'
        
        if human_turns <= 2:
            # Very short call — check for any signal
            all_user_text = ' '.join(m.get('user', '') for m in messages).lower()
            if len(all_user_text.strip()) < 10:
                logger.info("[OUTCOME FALLBACK] ≤2 turns, minimal text → no_engagement")
                return 'no_engagement'
            
            # Check for quick rejection
            rejection_words = ['not interested', 'no thanks', 'no thank you', 'busy', 'wrong number']
            if any(r in all_user_text for r in rejection_words):
                logger.info("[OUTCOME FALLBACK] ≤2 turns + rejection → quick_rejection")
                return 'quick_rejection'
            
            logger.info("[OUTCOME FALLBACK] ≤2 turns, some text → no_engagement")
            return 'no_engagement'
        
        # Enough turns but unknown — likely soft decline
        duration = 0
        if context.get('start_time'):
            try:
                from datetime import datetime as _dt
                if hasattr(context['start_time'], 'timestamp'):
                    duration = time.time() - context['start_time'].timestamp()
                else:
                    duration = (datetime.now() - context['start_time']).total_seconds() if hasattr(context['start_time'], 'total_seconds') else 0
            except Exception:
                pass
        
        if duration < 30:
            logger.info(f"[OUTCOME FALLBACK] {human_turns} turns but <30s → short_interaction")
            return 'short_interaction'
        
        logger.info(f"[OUTCOME FALLBACK] {human_turns} turns, {duration:.0f}s → soft_decline (default)")
        return 'soft_decline'


# ======================================================================
#  COACHING ENGINE — Per-Turn Quality Scoring
# ======================================================================
# The endocrine system. Hormones that tell the organism what happened.
# Scores each turn on human-like behavior, identifies issues, and
# aggregates into per-call coaching reports.
#
# This is the INPUT to evolution. Without coaching scores, evolution
# has nothing to learn from.
# ======================================================================

class CoachingEngine:
    """
    Per-turn and per-call coaching scorer.
    
    Scores each conversational turn on a 0.0-1.0 scale and records
    coaching flags (issues detected and strengths observed).
    
    Scoring dimensions:
      - Response proportionality (word count ratio)
      - Latency quality (total_turn_ms)
      - AI language detection (robotic phrases)
      - Conversational acknowledgment (does Alan reference what was said?)
      - Dead-end language detection
      - Question quality (does Alan ask good business questions?)
    
    Usage:
        engine = CoachingEngine()
        score, flags = engine.score_turn(user_text, alan_text, turn_data)
        # score: 0.0-1.0, flags: ['over_response', 'ai_language']
        
        # At call end:
        report = engine.generate_call_report()
        # report: {score, strengths, weaknesses, action_item}
    """
    
    # AI language patterns — robotic phrases that betray non-human origin
    AI_PHRASES = {
        "i'm right here",
        "i am right here", 
        "absolutely",
        "i appreciate you sharing that",
        "i appreciate that",
        "that's a great question",
        "great question",
        "i understand your concern",
        "i completely understand",
        "that's wonderful",
        "i'd be happy to help",
        "i'd love to help",
        "no worries at all",
        "thanks for sharing that",
        "perfect",
        "excellent question",
        "that makes total sense",
    }
    
    # Positive question indicators — signs of good business conversation
    GOOD_QUESTION_PATTERNS = [
        re.compile(r'\b(?:what|how much|how many|what kind|what type)\b.*\?', re.I),
        re.compile(r'\b(?:processing|volume|fees|rates|terminals?|pos)\b.*\?', re.I),
        re.compile(r'\b(?:currently|right now|at the moment)\b.*\?', re.I),
    ]
    
    # Dead-end response patterns from Alan (signs he's stuck)
    ALAN_DEAD_PHRASES = [
        re.compile(r"^(?:i see|okay|alright|got it|i understand)[.,!]?\s*$", re.I),
        re.compile(r"^(?:hmm|mhm|uh huh|right)[.,!]?\s*$", re.I),
    ]
    
    # Acknowledgment patterns — Alan referencing what merchant said
    ACKNOWLEDGMENT_PATTERNS = [
        re.compile(r'\b(?:you mentioned|you said|you\'re saying|as you noted|like you said)\b', re.I),
        re.compile(r'\b(?:i hear you|makes sense|that\'s|sounds like)\b', re.I),
    ]
    
    def __init__(self):
        self.turn_scores: List[float] = []
        self.turn_flags: List[List[str]] = []
        self.turn_count = 0
    
    def score_turn(self, user_text: str, alan_text: str, 
                   turn_data: dict = None) -> tuple:
        """
        Score a single conversational turn.
        
        Args:
            user_text: What the merchant said
            alan_text: What Alan said
            turn_data: Optional dict with timing data:
                - total_turn_ms: end-to-end latency
                - llm_ms: LLM latency
                - preprocess_ms: preprocessing latency
                
        Returns:
            (score: float, flags: list[str])
            score is 0.0-1.0, flags is list of issue/strength labels
        """
        if turn_data is None:
            turn_data = {}
        
        self.turn_count += 1
        score = 1.0
        flags = []
        
        user_words = len(user_text.split()) if user_text.strip() else 0
        alan_words = len(alan_text.split()) if alan_text.strip() else 0
        
        # ---- PENALTIES ----
        
        # 1. Response proportionality
        if user_words > 0 and alan_words > 0:
            ratio = alan_words / max(user_words, 1)
            if ratio > 4.0:
                # Heavy over-response: merchant said 3 words, Alan said 15+
                score -= 0.20
                flags.append('over_response')
            elif ratio > 3.0:
                # Moderate over-response
                score -= 0.10
                flags.append('mild_over_response')
            elif user_words > 20 and alan_words < 5:
                # Under-response to detailed input
                score -= 0.10
                flags.append('under_response')
        
        # 2. Latency quality — use first_audio_latency_ms (perceived latency)
        #    Falls back to total_turn_ms if first_audio not available
        first_audio_ms = turn_data.get('first_audio_latency_ms')
        latency_ms = first_audio_ms if first_audio_ms is not None else turn_data.get('total_turn_ms')
        if latency_ms is not None:
            if first_audio_ms is not None:
                # Scoring based on perceived first-audio latency (Phase 2 spec)
                if latency_ms > 2500:
                    score -= 0.15
                    flags.append('high_latency')
                elif latency_ms > 1500:
                    score -= 0.05
                    flags.append('elevated_latency')
                # <= 1500ms: full credit (no penalty)
            else:
                # Fallback: total_turn_ms (legacy)
                if latency_ms > 4000:
                    score -= 0.15
                    flags.append('high_latency')
                elif latency_ms > 3000:
                    score -= 0.08
                    flags.append('elevated_latency')
        
        # 3. AI language detection
        alan_lower = alan_text.lower().strip()
        for phrase in self.AI_PHRASES:
            if phrase in alan_lower:
                score -= 0.20
                flags.append('ai_language')
                break  # One penalty per turn, but flag it
        
        # 4. Dead-end response (Alan gave a non-response)
        for pattern in self.ALAN_DEAD_PHRASES:
            if pattern.match(alan_text.strip()):
                score -= 0.15
                flags.append('dead_end_response')
                break
        
        # 5. No acknowledgment when merchant gave substantial input
        if user_words >= 10:
            has_ack = any(p.search(alan_text) for p in self.ACKNOWLEDGMENT_PATTERNS)
            if not has_ack:
                score -= 0.08
                flags.append('no_acknowledgment')
        
        # ---- BONUSES ----
        
        # 6. Good business question asked
        for pattern in self.GOOD_QUESTION_PATTERNS:
            if pattern.search(alan_text):
                score += 0.05
                flags.append('good_question')
                break
        
        # 7. Natural acknowledgment present (only bonus if not already penalized)
        if 'no_acknowledgment' not in flags and user_words >= 5:
            has_ack = any(p.search(alan_text) for p in self.ACKNOWLEDGMENT_PATTERNS)
            if has_ack:
                score += 0.03
                flags.append('natural_ack')
        
        # Clamp to [0.0, 1.0]
        score = max(0.0, min(1.0, score))
        
        self.turn_scores.append(score)
        self.turn_flags.append(flags)
        
        return score, flags
    
    def generate_call_report(self) -> dict:
        """
        Generate an aggregate coaching report for the entire call.
        
        Returns:
            {
                'coaching_score': float (0.0-1.0),
                'coaching_strengths': str (comma-separated),
                'coaching_weaknesses': str (comma-separated), 
                'coaching_action_item': str
            }
        """
        if not self.turn_scores:
            return {
                'coaching_score': None,
                'coaching_strengths': '',
                'coaching_weaknesses': '',
                'coaching_action_item': 'No turns to evaluate',
            }
        
        avg_score = sum(self.turn_scores) / len(self.turn_scores)
        
        # Count all flags across all turns
        flag_counts = {}
        for flags in self.turn_flags:
            for f in flags:
                flag_counts[f] = flag_counts.get(f, 0) + 1
        
        # Separate strengths from weaknesses
        strength_flags = {'good_question', 'natural_ack'}
        weakness_flags = {'over_response', 'mild_over_response', 'under_response',
                         'high_latency', 'elevated_latency', 'ai_language',
                         'dead_end_response', 'no_acknowledgment'}
        
        strengths = []
        weaknesses = []
        
        for flag, count in sorted(flag_counts.items(), key=lambda x: -x[1]):
            label = f"{flag}({count}x)" if count > 1 else flag
            if flag in strength_flags:
                strengths.append(label)
            elif flag in weakness_flags:
                weaknesses.append(label)
        
        # Generate action item — focus on the worst issue
        action_item = self._generate_action_item(flag_counts, avg_score)
        
        return {
            'coaching_score': round(avg_score, 3),
            'coaching_strengths': ', '.join(strengths) if strengths else 'none_detected',
            'coaching_weaknesses': ', '.join(weaknesses) if weaknesses else 'none_detected',
            'coaching_action_item': action_item,
        }
    
    def _generate_action_item(self, flag_counts: dict, avg_score: float) -> str:
        """Generate a prioritized action item based on worst issues."""
        # Priority order for action items
        if flag_counts.get('ai_language', 0) >= 2:
            return "CRITICAL: Eliminate robotic AI phrases. Use natural human language."
        if flag_counts.get('over_response', 0) >= 2:
            return "Reduce response length. Match merchant energy — short question = short answer."
        if flag_counts.get('high_latency', 0) >= 2:
            return "Address latency bottleneck. Multiple turns exceeded 4s response time."
        if flag_counts.get('dead_end_response', 0) >= 2:
            return "Break dead-end pattern. Avoid filler responses — ask a specific question instead."
        if flag_counts.get('no_acknowledgment', 0) >= 2:
            return "Improve active listening. Reference what the merchant said before responding."
        if flag_counts.get('under_response', 0) >= 1:
            return "Give fuller answers when merchant provides detailed information."
        if avg_score >= 0.85:
            return "Maintain current performance. Focus on closing technique."
        if avg_score >= 0.70:
            return "Good performance. Minor improvements in natural conversation flow."
        return "Review conversation patterns. Multiple issues detected across turns."


# ======================================================================
#  UNIFIED CONVERSATION GUARD — Single Entry Point
# ======================================================================
# Wraps all eight systems into one object per call session.
# Created once per call, checked each turn.
# ======================================================================

class ConversationGuard:
    """
    Unified controller for all conversational intelligence systems.
    One instance per active call.
    
    Usage in handle_user_speech:
        guard = context.get('_conversation_guard')
        if not guard:
            guard = ConversationGuard(merchant_name)
            context['_conversation_guard'] = guard
        
        # Pre-checks (before LLM):
        result = guard.pre_check(user_text, context)
        if result and result.get('abort'):
            # Handle abort (DNC, government, voicemail)
        
        # Post-check (after LLM, before TTS):
        post_result = guard.post_check(proposed_response)
        if post_result:
            # Handle repetition breaker
    """
    
    def __init__(self, merchant_name: str = ''):
        self.compliance = ComplianceInterrupt()
        self.voicemail = VoicemailDetector()
        self.entity = EntityClassifier()
        self.repetition = RepetitionBreaker()
        self.bridge = LatencyBridge()
        self.dead_end = DeadEndDetector()
        self.outcome_fallback = ShortCallOutcomeFallback()
        self.coaching = CoachingEngine()
        
        # Track stream state
        self.stream_ended = False
        self._guard_outcome = None
        
        # Check merchant name at init
        self._name_check_result = None
        if merchant_name:
            self._name_check_result = self.entity.check_name(merchant_name)
    
    @property
    def name_check_abort(self) -> Optional[Dict]:
        """Returns entity classification result from name check, if any."""
        return self._name_check_result
    
    def pre_check(self, user_text: str, context: dict = None) -> Optional[Dict]:
        """
        Run all pre-LLM checks on user speech.
        Returns the FIRST abort-worthy result, or None if clear.
        
        Priority order:
        1. DNC (legally mandatory)
        2. Government entity (from speech)
        3. Voicemail (from speech patterns)
        4. Dead-end (stalled conversation)
        """
        # 1. DNC check — highest priority, legally mandatory
        dnc_result = self.compliance.check(user_text)
        if dnc_result:
            return {**dnc_result, 'abort': True, 'system': 'compliance'}
        
        # 2. Government entity check (speech-based)
        gov_result = self.entity.check_speech(user_text)
        if gov_result:
            return {**gov_result, 'abort': True, 'system': 'entity'}
        
        # 3. Voicemail detection
        elapsed = 0
        if context and context.get('start_time'):
            try:
                if hasattr(context['start_time'], 'timestamp'):
                    elapsed = time.time() - context['start_time'].timestamp()
                else:
                    elapsed = time.time() - float(context['start_time'])
            except Exception:
                pass
        
        vm_result = self.voicemail.check(user_text, elapsed)
        if vm_result:
            return {**vm_result, 'abort': True, 'system': 'voicemail'}
        
        # 4. Dead-end detection
        # [2026-03-02 FIX] Early-turn guard: NEVER fire dead-end exit on the first
        # 3 real messages. Noise/echo fragments from STT can rack up invisible
        # _turn_count increments before real merchant speech arrives, causing
        # farewell exit lines ("Thanks for your time. Have a great day!") to play
        # as Alan's FIRST audible response. This guard prevents that.
        _msg_count = len(context.get('messages', [])) if context else 0
        if _msg_count >= 3:
            analysis = context.get('_last_analysis') if context else None
            dead_result = self.dead_end.check(user_text, analysis)
            if dead_result:
                return {**dead_result, 'abort': True, 'system': 'dead_end'}
        else:
            logger.debug(f"[CONV GUARD] Skipping dead-end check — only {_msg_count} messages (need 3+)")
        
        return None
    
    def post_check(self, proposed_response: str) -> Optional[Dict]:
        """
        Run post-LLM checks on Alan's proposed response.
        Currently: repetition breaker.
        """
        result = self.repetition.check_before_response(proposed_response)
        if result:
            return result
        return None
    
    def record_alan_response(self, alan_text: str):
        """Record what Alan said for future repetition detection."""
        self.repetition.record_response(alan_text)
    
    def score_turn(self, user_text: str, alan_text: str, 
                   turn_data: dict = None) -> tuple:
        """Score a conversational turn via coaching engine. Returns (score, flags)."""
        return self.coaching.score_turn(user_text, alan_text, turn_data)
    
    def generate_coaching_report(self) -> dict:
        """Generate aggregate coaching report for this call."""
        return self.coaching.generate_call_report()


# ======================================================================
#  SELF-TEST
# ======================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("CONVERSATIONAL INTELLIGENCE — SELF-TEST")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    def test(name, condition):
        global passed, failed
        if condition:
            print(f"  PASS: {name}")
            passed += 1
        else:
            print(f"  FAIL: {name}")
            failed += 1
    
    # --- DNC Tests ---
    print("\n[1] COMPLIANCE INTERRUPT (DNC)")
    ci = ComplianceInterrupt()
    test("Normal speech → no trigger", ci.check("Hi, how are you?") is None)
    test("'do not call list' → DNC", ci.check("Put me on your do not call list")['is_dnc'] == True)
    
    ci2 = ComplianceInterrupt()
    test("'remove me' → DNC", ci2.check("Please remove me from your list")['is_dnc'] == True)
    
    ci3 = ComplianceInterrupt()
    test("'stop calling' → DNC", ci3.check("Stop calling us please")['is_dnc'] == True)
    
    ci4 = ComplianceInterrupt()
    test("'never call again' → DNC", ci4.check("Never call me again")['is_dnc'] == True)
    
    ci5 = ComplianceInterrupt()
    test("'not interested' alone → no trigger", ci5.check("I'm not interested") is None)
    test("'take me off' → DNC", ci5.check("Take me off your list")['is_dnc'] == True)
    
    # --- Voicemail Tests ---
    print("\n[2] VOICEMAIL DETECTOR")
    vm = VoicemailDetector()
    test("Normal speech → no trigger", vm.check("Hi, how can I help you?") is None)
    test("'leave a message' → builds confidence", vm.check("Please leave a message after the beep") is not None or vm.confidence > 0)
    
    vm2 = VoicemailDetector()
    r = vm2.check("At the tone, please record your message. When you're done, press pound or hang up.")
    test("Full voicemail prompt → trigger", r is not None and r.get('is_voicemail') == True)
    
    vm3 = VoicemailDetector()
    vm3.check("The person you have called is unavailable.")
    r3 = vm3.check("Please leave a message after the tone.")
    test("Two voicemail indicators → trigger", r3 is not None and r3.get('is_voicemail') == True)
    
    # --- Entity Classifier Tests ---
    print("\n[3] ENTITY CLASSIFIER")
    ec = EntityClassifier()
    test("Normal business name → no trigger", ec.check_name("Joe's Pizza") is None)
    
    ec2 = EntityClassifier()
    r2 = ec2.check_name("New York State Department of Civil Service")
    test("Government dept name → trigger", r2 is not None and r2.get('is_government') == True)
    
    ec3 = EntityClassifier()
    test("Defense contractor name → score increase", ec3.check_name("CACI, INC. - FEDERAL") is None or ec3.government_score > 0)
    
    ec4 = EntityClassifier()
    ec4.check_name("Business Entities")  # Ambiguous name
    r4 = ec4.check_speech("All limited liability companies can now file their statements of information online by visiting our California portal")
    test("Government speech + ambiguous name → accumulate", ec4.government_score > 0)
    
    ec5 = EntityClassifier()
    ec5.check_speech("Tax board suspension fees or other tax related questions")
    r5 = ec5.check_speech("Contact the franchise tax board at ftb.ca.gov for faster service")
    test("Tax board references → accumulate", ec5.government_score > 0.5)
    
    # --- Repetition Breaker Tests ---
    print("\n[4] REPETITION BREAKER")
    rb = RepetitionBreaker()
    rb.record_response("I'm listening.")
    rb.record_response("I'm listening.")
    r_rep = rb.check_before_response("I'm listening.")
    test("3x 'I'm listening' → force rephrase", r_rep is not None and r_rep['action'] in ('force_rephrase', 'nudge'))
    
    rb2 = RepetitionBreaker()
    for _ in range(5):
        rb2.record_response("I'm listening.")
    r_rep2 = rb2.check_before_response("I'm listening.")
    test("6x 'I'm listening' → bail", r_rep2 is not None and r_rep2['action'] == 'bail')
    
    rb3 = RepetitionBreaker()
    rb3.record_response("How's your processing setup?")
    rb3.record_response("Just curious about your processing fees.")
    test("2 different responses → no trigger", rb3.check_before_response("What's your monthly volume?") is None)
    
    # --- Latency Bridge Tests ---
    print("\n[5] LATENCY BRIDGE")
    lb = LatencyBridge()
    lb.mark_turn_start()
    test("Fast preprocess → no bridge", lb.should_bridge(200) == False)
    test("Slow preprocess → bridge", lb.should_bridge(1500) == True)
    bridge_text = lb.get_bridge('default')
    test("Bridge text is non-empty", len(bridge_text) > 0)
    test("Bridge text ends with ...", bridge_text.endswith("..."))
    
    # --- Dead-End Detector Tests ---
    print("\n[6] DEAD-END DETECTOR")
    de = DeadEndDetector(max_dead_turns=3)
    test("First turn → no trigger", de.check("Hi, how can I help you?") is None)
    test("Normal engagement → no trigger", de.check("Tell me more about your rates") is None)
    de2 = DeadEndDetector(max_dead_turns=3)
    de2.check("Normal first turn with enough words to be real")
    de2.check("We're fine, thanks")
    de2.check("No thanks")
    r_de = de2.check("Not interested")  # 3rd rejection at turn 4 → triggers
    test("3 rejections at turn 4 → dead-end exit", r_de is not None and r_de.get('should_exit') == True)
    
    de3 = DeadEndDetector(max_dead_turns=3)
    de3.check("Hello there how can I help you today")
    de3.check("We're good")
    de3.check("Tell me more actually, what do you offer?")  # Progress! Long + question
    de3.check("We're good")
    test("Progress resets dead count", de3.dead_turn_count <= 2)
    
    # --- Short-Call Outcome Fallback Tests ---
    print("\n[7] SHORT-CALL OUTCOME FALLBACK")
    scof = ShortCallOutcomeFallback()
    test("Known outcome → pass through", scof.reclassify("kept_engaged", {}) == "kept_engaged")
    test("0 turns → no_answer", scof.reclassify("unknown", {'messages': []}) == "no_answer")
    test("1 turn minimal → no_engagement",
         scof.reclassify("unknown", {'messages': [{'user': 'hi'}]}) == "no_engagement")
    test("Quick rejection → quick_rejection",
         scof.reclassify("unknown", {'messages': [{'user': 'not interested'}, {'user': 'no thanks'}]}) == "quick_rejection")
    test("Guard outcome → uses guard",
         scof.reclassify("unknown", {'messages': [{'user': 'test'}], '_guard_outcome': 'dnc_request'}) == "dnc_request")
    
    # --- ConversationGuard Integration ---
    print("\n[8] CONVERSATION GUARD (Integration)")
    guard = ConversationGuard("Joe's Pizza")
    test("Normal merchant → no name abort", guard.name_check_abort is None)
    
    guard2 = ConversationGuard("New York State Department of State")
    test("Government name → name abort", guard2.name_check_abort is not None)
    
    guard3 = ConversationGuard("Lake Auto")
    test("Normal name, normal speech → no abort", guard3.pre_check("Hi, how can I help you?") is None)
    test("Normal name, DNC speech → abort", guard3.pre_check("Put me on your do not call list") is not None)
    
    # Dead-end through guard
    guard4 = ConversationGuard("Some Business")
    guard4.pre_check("Hello welcome to some business")
    guard4.pre_check("We're fine")
    guard4.pre_check("No thanks")
    r_g4 = guard4.pre_check("Not interested")  # 3rd rejection at turn 4 → triggers
    test("Dead-end through guard → abort", r_g4 is not None and r_g4.get('system') == 'dead_end')
    
    # --- Coaching Engine Tests ---
    print("\n[9] COACHING ENGINE")
    ce = CoachingEngine()
    
    # Perfect turn: proportional response, no AI language
    s1, f1 = ce.score_turn("How much do you charge per transaction?", 
                           "Our rates start at 1.5% for card-present transactions. What kind of volume are you doing?")
    test("Good turn → score > 0.8", s1 > 0.8)
    test("Good turn → good_question flag", 'good_question' in f1)
    
    # Over-response: 3 words in, 40 words out
    ce2 = CoachingEngine()
    s2, f2 = ce2.score_turn("Not interested",
                            "Oh I completely understand that you might not be interested right now but I wanted to let you know that we have some really amazing rates and we work with businesses just like yours to save them thousands of dollars every single month on their processing fees")
    test("Over-response → score < 0.85", s2 < 0.85)
    test("Over-response → over_response flag", 'over_response' in f2)
    
    # AI language: robotic phrase
    ce3 = CoachingEngine()
    s3, f3 = ce3.score_turn("What do you do?", 
                            "That's a great question! I'd be happy to help you with that.")
    test("AI language → score < 0.85", s3 < 0.85)
    test("AI language → ai_language flag", 'ai_language' in f3)
    
    # High latency
    ce4 = CoachingEngine()
    s4, f4 = ce4.score_turn("Tell me about your rates",
                            "Sure, our rates are very competitive.",
                            {'total_turn_ms': 5000})
    test("High latency → high_latency flag", 'high_latency' in f4)
    test("High latency → score penalty", s4 < 0.9)
    
    # Dead-end response
    ce5 = CoachingEngine()
    s5, f5 = ce5.score_turn("We process about fifty thousand a month",
                            "I see.")
    test("Dead-end response → dead_end_response flag", 'dead_end_response' in f5)
    
    # No acknowledgment on substantial input
    ce6 = CoachingEngine()
    s6, f6 = ce6.score_turn("We've been with our processor for ten years and they give us great rates and we're really happy with them",
                            "Let me tell you about our competitive rates and how we can save you money.")
    test("No acknowledgment → no_acknowledgment flag", 'no_acknowledgment' in f6)
    
    # Call report generation
    ce7 = CoachingEngine()
    ce7.score_turn("Hi", "That's a great question! I'm right here for you!", {'total_turn_ms': 5000})
    ce7.score_turn("What?", "Absolutely! I'd be happy to help you with that great question!")
    ce7.score_turn("Bye", "Thanks for your time. Have a good day.")
    report = ce7.generate_call_report()
    test("Report has coaching_score", report['coaching_score'] is not None)
    test("Report has weaknesses", len(report['coaching_weaknesses']) > 0)
    test("Report has action_item", len(report['coaching_action_item']) > 0)
    test("Report score < 0.8 (bad turns)", report['coaching_score'] < 0.8)
    
    # Perfect call report
    ce8 = CoachingEngine()
    ce8.score_turn("How much do you charge?", "Our rates start at 1.5%. What kind of volume are you processing?")
    ce8.score_turn("About fifty thousand a month", "That's solid volume. Sounds like you're doing well. Are you seeing any issues with chargebacks?")
    ce8.score_turn("Not really", "Good to hear. What about your terminal setup — are you using countertop or mobile?")
    report2 = ce8.generate_call_report()
    test("Perfect call → score > 0.85", report2['coaching_score'] > 0.85)
    
    # Guard integration with coaching
    guard5 = ConversationGuard("Test Biz")
    gs, gf = guard5.score_turn("Hello", "Hi there, how are you doing today?")
    test("Guard.score_turn works", gs > 0.5)
    greport = guard5.generate_coaching_report()
    test("Guard.generate_coaching_report works", greport['coaching_score'] is not None)
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed} tests")
    if failed == 0:
        print("ALL TESTS PASSED")
    print(f"{'='*60}")
