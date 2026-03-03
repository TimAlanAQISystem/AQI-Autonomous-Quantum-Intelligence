"""
+==============================================================================+
|   ORGAN 37 — IVR NAVIGATOR                                                   |
|                                                                               |
|   PURPOSE:                                                                    |
|   Parse IVR menu prompts from STT transcripts and navigate them              |
|   deterministically to reach a live human. Uses Organ 36 (DTMF Reflex)       |
|   to send button presses and speech to navigate phone trees.                  |
|                                                                               |
|   STATE MACHINE:                                                              |
|     LISTENING_MENU  → Collecting IVR prompt text                              |
|     PARSING_OPTIONS → Extracting menu options from transcript                 |
|     DECIDING        → Selecting best option to reach human                    |
|     ACTING          → Sending DTMF or speaking response                      |
|     WAITING         → Waiting for next prompt after action                    |
|     REACHED_HUMAN   → Human detected, hand back to Alan                      |
|     FAILED          → Dead end / loop — abort call                           |
|                                                                               |
|   NAVIGATION STRATEGY:                                                        |
|   1. Parse menu options from STT (e.g., "press 1 for sales")                 |
|   2. Score each option for "leads to a human" probability                     |
|   3. Send DTMF for best option, OR speak "representative" / "operator"       |
|   4. If stuck in loop (3+ cycles), try '0' then '#' then abort               |
|                                                                               |
|   CONSTITUTIONAL CONSTRAINTS:                                                 |
|   - Only send DTMF digits that were explicitly parsed from the menu          |
|   - Or from the HUMAN_ESCAPE_SEQUENCE (0, #, "representative")              |
|   - Never guess or hallucinate menu options                                   |
|   - Maximum 5 navigation attempts before abort                               |
|   - Full lineage logging of every decision                                    |
|                                                                               |
|   LINEAGE: Organ 37. Created 2026-02-26.                                      |
|   DIRECTIVE: "Finding a way for Alan to reach these businesses" — Tim         |
+==============================================================================+
"""

import re
import time
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger("IVR_NAVIGATOR")


# ======================================================================
#  IVR NAVIGATOR STATE MACHINE
# ======================================================================

class IVRNavState(Enum):
    """IVR Navigator internal states."""
    LISTENING_MENU = auto()    # Collecting prompt text
    PARSING_OPTIONS = auto()   # Extracting options
    DECIDING = auto()          # Choosing best option
    ACTING = auto()            # Sending DTMF or speech
    WAITING = auto()           # Waiting for response after action
    REACHED_HUMAN = auto()     # Human detected — hand back
    FAILED = auto()            # Dead end — abort


class IVRAction(Enum):
    """What the navigator decided to do."""
    SEND_DTMF = auto()         # Press a button
    SPEAK = auto()             # Say something (e.g., "representative")
    WAIT = auto()              # Wait for more prompt
    ABORT = auto()             # Give up
    HANDOFF = auto()           # Human detected — return control


# ======================================================================
#  MENU OPTION PARSER
# ======================================================================

# Patterns to extract "press X for Y" style options
_MENU_PATTERNS = [
    # "press 1 for sales" / "press one for sales"
    re.compile(
        r"(?:press|dial|hit|push|enter)\s+"
        r"(?:the\s+)?"
        r"(one|two|three|four|five|six|seven|eight|nine|zero|star|pound|hash|\d|\*|#)"
        r"\s+(?:for|to\s+(?:reach|speak|talk|connect|get))\s+"
        r"(.+?)(?:\.|,|$)",
        re.IGNORECASE
    ),
    # "for sales, press 1" / "for sales press one"
    re.compile(
        r"for\s+(.+?),?\s*(?:please\s+)?(?:press|dial|hit|push|enter)\s+"
        r"(?:the\s+)?"
        r"(one|two|three|four|five|six|seven|eight|nine|zero|star|pound|hash|\d|\*|#)",
        re.IGNORECASE
    ),
    # "select 1 for..." / "option 1 for..."
    re.compile(
        r"(?:select|option|choice)\s+"
        r"(one|two|three|four|five|six|seven|eight|nine|zero|\d)"
        r"\s+(?:for|to)\s+"
        r"(.+?)(?:\.|,|$)",
        re.IGNORECASE
    ),
]

# Word-to-digit mapping (used in regex capture groups)
_WORD_TO_DIGIT = {
    'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
    'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'zero': '0',
    'star': '*', 'pound': '#', 'hash': '#',
}

# Extended word-to-digit for full-text normalization (Whisper transcribes digits as words)
# Includes ordinals, informal variants, and common Whisper mishearings
_TEXT_NORMALIZE_MAP = {
    # Standard number words
    'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
    'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
    # Common Whisper mishearings / homophones
    'won': '1', 'to': None, 'too': None, 'for': None,  # Skip ambiguous ones
    'ate': None,  # ambiguous
    # Explicit "number X" patterns handled separately
    'star': '*', 'pound': '#', 'hash': '#', 'asterisk': '*',
}

def _normalize_transcript_digits(text: str) -> str:
    """Pre-process transcript to convert number words to digits.
    
    Whisper often transcribes "press one" instead of "press 1".
    This normalizes the text so regex patterns can use simpler matching.
    Only converts unambiguous number words that appear in IVR context.
    """
    # Only convert when preceded by IVR action words (avoids false positives)
    # Pattern: (press|dial|hit|push|enter|option|select|choice) + word-number
    _IVR_DIGIT_PATTERN = re.compile(
        r'\b(press|dial|hit|push|enter|option|select|choice|number)\s+'
        r'(zero|one|two|three|four|five|six|seven|eight|nine|star|pound|hash|asterisk)\b',
        re.IGNORECASE
    )
    
    def _replace_match(m):
        action = m.group(1)
        word = m.group(2).lower()
        digit = _WORD_TO_DIGIT.get(word, word)
        return f"{action} {digit}"
    
    result = _IVR_DIGIT_PATTERN.sub(_replace_match, text)
    
    # Also normalize "for X press/dial Y" pattern where X is a description
    # and Y is a word-digit
    _FOR_PATTERN = re.compile(
        r'\b(for\s+.+?)\s+(press|dial)\s+'
        r'(zero|one|two|three|four|five|six|seven|eight|nine|star|pound|hash|asterisk)\b',
        re.IGNORECASE
    )
    
    def _replace_for_match(m):
        prefix = m.group(1)
        action = m.group(2)
        word = m.group(3).lower()
        digit = _WORD_TO_DIGIT.get(word, word)
        return f"{prefix} {action} {digit}"
    
    result = _FOR_PATTERN.sub(_replace_for_match, result)
    
    return result

# Keywords that suggest an option leads to a human
_HUMAN_KEYWORDS = [
    'representative', 'operator', 'agent', 'person', 'human',
    'receptionist', 'front desk', 'someone', 'speak to', 'talk to',
    'sales', 'service', 'support', 'customer', 'general',
    'owner', 'manager', 'billing', 'accounts',
    'main', 'office', 'store', 'shop',
    'appointments', 'scheduling', 'booking',
]

# Keywords that suggest a dead end (NOT a human)
_DEAD_END_KEYWORDS = [
    'voicemail', 'leave a message', 'directory', 'dial by name',
    'hours', 'location', 'address', 'website', 'fax', 'hearing impaired',
    'español', 'espanol', 'spanish', 'language',
    'pay', 'payment', 'balance', 'automated',
]

# Escape sequences to try when menu parsing fails
_ESCAPE_SEQUENCES = [
    ('0', "press 0 — universal operator shortcut"),
    ('#', "press # — common escape key"),
    ('0w0', "press 0 twice — aggressive operator request"),
]


# ======================================================================
#  MENU OPTION DATA STRUCTURE
# ======================================================================

@dataclass
class MenuOption:
    """A single parsed menu option."""
    digit: str               # The DTMF digit ('1', '2', '*', etc.)
    description: str         # What this option does ("sales", "representative")
    human_score: float       # 0-1 probability this leads to a human
    raw_text: str            # The original text this was parsed from


@dataclass
class IVRDecision:
    """A navigation decision — what to do and why."""
    action: IVRAction
    digit: Optional[str] = None      # For SEND_DTMF
    speech: Optional[str] = None     # For SPEAK
    reason: str = ""                 # Why this decision was made
    confidence: float = 0.0          # How confident (0-1)
    options_parsed: List[MenuOption] = field(default_factory=list)


# ======================================================================
#  IVR NAVIGATOR ENGINE (per-call instance)
# ======================================================================

class IVRNavigator:
    """Per-call IVR navigation engine.
    
    Tracks IVR state, parses menus, decides actions, and coordinates
    with the DTMF Reflex (Organ 36) to send tones.
    
    Usage:
        nav = IVRNavigator()
        
        # Feed each IVR transcript
        decision = nav.process_utterance(text)
        
        # Execute the decision
        if decision.action == IVRAction.SEND_DTMF:
            await dtmf_reflex.send_digit(ws, sid, decision.digit, context=decision.reason)
        elif decision.action == IVRAction.SPEAK:
            # Synthesize and stream decision.speech
            pass
        elif decision.action == IVRAction.HANDOFF:
            # Human reached — return control to Alan
            pass
        elif decision.action == IVRAction.ABORT:
            # Dead end — hang up
            pass
    """
    
    MAX_NAVIGATION_ATTEMPTS = 5    # Maximum menu levels before giving up
    MAX_SAME_MENU_REPEATS = 2     # Same menu heard this many times = stuck
    HUMAN_SCORE_THRESHOLD = 0.3   # Minimum score to consider an option
    
    def __init__(self):
        self.state: IVRNavState = IVRNavState.LISTENING_MENU
        self.attempts: int = 0
        self.decisions: List[IVRDecision] = []
        self.menu_history: List[str] = []  # Normalized menu prompts
        self.escape_index: int = 0         # Which escape sequence to try next
        self._last_prompt: str = ""
        self._active: bool = True
    
    def process_utterance(self, text: str) -> IVRDecision:
        """Process an IVR utterance and decide what to do.
        
        This is the main entry point — called each time STT produces
        a transcript while in IVR navigation mode.
        
        Returns:
            IVRDecision with the action to take.
        """
        if not self._active or self.state == IVRNavState.FAILED:
            return IVRDecision(action=IVRAction.ABORT, reason="Navigator deactivated or failed")
        
        if self.state == IVRNavState.REACHED_HUMAN:
            return IVRDecision(action=IVRAction.HANDOFF, reason="Human already reached")
        
        self.attempts += 1
        self._last_prompt = text
        
        # Safety: too many attempts
        if self.attempts > self.MAX_NAVIGATION_ATTEMPTS:
            self.state = IVRNavState.FAILED
            logger.warning(f"[ORGAN 37] MAX ATTEMPTS ({self.MAX_NAVIGATION_ATTEMPTS}) exceeded — aborting")
            return IVRDecision(
                action=IVRAction.ABORT,
                reason=f"Exceeded {self.MAX_NAVIGATION_ATTEMPTS} navigation attempts",
            )
        
        # Check for human indicators
        if self._is_human_speaking(text):
            self.state = IVRNavState.REACHED_HUMAN
            logger.info(f"[ORGAN 37] HUMAN DETECTED in IVR — handing back to Alan")
            return IVRDecision(
                action=IVRAction.HANDOFF,
                reason="Human speech pattern detected during IVR navigation",
                confidence=0.8,
            )
        
        # Check for stuck-in-loop (same menu repeating)
        normalized = self._normalize_prompt(text)
        if self._is_repeated_menu(normalized):
            logger.warning(f"[ORGAN 37] REPEATED MENU detected — trying escape sequence")
            return self._try_escape()
        self.menu_history.append(normalized)
        
        # Parse menu options
        options = self._parse_menu_options(text)
        
        if options:
            # Score and select best option
            return self._select_best_option(options, text)
        else:
            # No parseable menu — try speech or generic escape
            return self._handle_unparseable_prompt(text)
    
    def _parse_menu_options(self, text: str) -> List[MenuOption]:
        """Extract menu options from IVR transcript text."""
        # Pre-process: convert word-numbers to digits (Whisper transcribes "one" not "1")
        text = _normalize_transcript_digits(text)
        logger.debug(f"[ORGAN 37] Normalized transcript: '{text[:120]}'")
        
        options = []
        
        for pattern in _MENU_PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groups()
                if len(groups) >= 2:
                    # Determine which group is digit and which is description
                    # Pattern 1 & 3: (digit, description)
                    # Pattern 2: (description, digit)
                    g1, g2 = groups[0].strip(), groups[1].strip()
                    
                    # Check if g1 is a digit/word-digit
                    g1_lower = g1.lower()
                    if g1_lower in _WORD_TO_DIGIT or (len(g1) == 1 and g1 in '0123456789*#'):
                        digit_raw = g1_lower
                        description = g2
                    else:
                        digit_raw = g2.lower()
                        description = g1
                    
                    # Convert word to digit
                    digit = _WORD_TO_DIGIT.get(digit_raw, digit_raw)
                    
                    # Validate digit
                    if digit not in '0123456789*#ABCD':
                        continue
                    
                    # Score for human-reachability
                    human_score = self._score_option(description)
                    
                    options.append(MenuOption(
                        digit=digit,
                        description=description.strip(),
                        human_score=human_score,
                        raw_text=match.group(0),
                    ))
        
        # Deduplicate by digit (keep highest score)
        seen = {}
        for opt in options:
            if opt.digit not in seen or opt.human_score > seen[opt.digit].human_score:
                seen[opt.digit] = opt
        
        return list(seen.values())
    
    def _score_option(self, description: str) -> float:
        """Score an IVR menu option for likelihood of reaching a human.
        
        Higher score = more likely to reach a human.
        """
        desc_lower = description.lower()
        score = 0.0
        
        # Positive signals — this option likely leads to a human
        for kw in _HUMAN_KEYWORDS:
            if kw in desc_lower:
                score += 0.3
        
        # Negative signals — this option likely leads to a dead end
        for kw in _DEAD_END_KEYWORDS:
            if kw in desc_lower:
                score -= 0.4
        
        # Special boost for operator/representative
        if any(w in desc_lower for w in ('representative', 'operator', 'person', 'human', 'agent')):
            score += 0.5
        
        # Special boost for "sales" (Alan IS calling about sales)
        if 'sales' in desc_lower:
            score += 0.3
        
        # Special boost for "general" / "main" / "front desk"
        if any(w in desc_lower for w in ('general', 'main', 'front desk')):
            score += 0.2
        
        # Clamp to 0-1
        return max(0.0, min(1.0, score))
    
    def _select_best_option(self, options: List[MenuOption], raw_text: str) -> IVRDecision:
        """Select the best menu option to navigate toward a human."""
        # Sort by human_score descending
        sorted_opts = sorted(options, key=lambda o: o.human_score, reverse=True)
        
        best = sorted_opts[0]
        
        # If best score is below threshold, try escape instead
        if best.human_score < self.HUMAN_SCORE_THRESHOLD:
            logger.info(f"[ORGAN 37] No high-confidence option (best={best.human_score:.2f} for '{best.description}') — trying escape")
            return self._try_escape()
        
        self.state = IVRNavState.ACTING
        decision = IVRDecision(
            action=IVRAction.SEND_DTMF,
            digit=best.digit,
            reason=f"Menu option: press {best.digit} for '{best.description}' (score={best.human_score:.2f})",
            confidence=best.human_score,
            options_parsed=sorted_opts,
        )
        self.decisions.append(decision)
        logger.info(f"[ORGAN 37] DECISION: Press '{best.digit}' for '{best.description}' "
                    f"(score={best.human_score:.2f}, {len(options)} options parsed)")
        
        return decision
    
    def _handle_unparseable_prompt(self, text: str) -> IVRDecision:
        """Handle an IVR prompt where we couldn't parse menu options.
        
        Strategy: try speaking "representative" first, then DTMF escapes.
        """
        text_lower = text.lower()
        
        # If prompt says "say" something → speech-responsive IVR
        if any(w in text_lower for w in ('say ', 'speak ', 'state ')):
            logger.info(f"[ORGAN 37] Speech-responsive IVR detected — saying 'representative'")
            decision = IVRDecision(
                action=IVRAction.SPEAK,
                speech="representative",
                reason="Speech-responsive IVR — requesting representative",
                confidence=0.5,
            )
            self.decisions.append(decision)
            return decision
        
        # If it mentions "operator" or "representative" → say the word
        if any(w in text_lower for w in ('operator', 'representative', 'press zero')):
            logger.info(f"[ORGAN 37] Operator/representative mentioned — pressing 0")
            decision = IVRDecision(
                action=IVRAction.SEND_DTMF,
                digit='0',
                reason="IVR mentions operator — pressing 0",
                confidence=0.5,
            )
            self.decisions.append(decision)
            return decision
        
        # If prompt mentions "hold" or "stay on the line" → just wait
        if any(w in text_lower for w in ('please hold', 'stay on the line', 'remain on the line',
                                          'transferring', 'connecting')):
            logger.info(f"[ORGAN 37] Hold/transfer detected — waiting")
            decision = IVRDecision(
                action=IVRAction.WAIT,
                reason="IVR says hold/transfer — waiting for human",
                confidence=0.6,
            )
            self.decisions.append(decision)
            return decision
        
        # No clues — try escape sequence
        return self._try_escape()
    
    def _try_escape(self) -> IVRDecision:
        """Try the next escape sequence to break out of an IVR loop."""
        if self.escape_index < len(_ESCAPE_SEQUENCES):
            seq, reason = _ESCAPE_SEQUENCES[self.escape_index]
            self.escape_index += 1
            
            decision = IVRDecision(
                action=IVRAction.SEND_DTMF,
                digit=seq,
                reason=f"Escape attempt {self.escape_index}: {reason}",
                confidence=0.3,
            )
            self.decisions.append(decision)
            logger.info(f"[ORGAN 37] ESCAPE ATTEMPT {self.escape_index}: sending '{seq}' — {reason}")
            return decision
        
        # All escapes exhausted — try speaking "representative" as last resort
        if self.escape_index == len(_ESCAPE_SEQUENCES):
            self.escape_index += 1
            decision = IVRDecision(
                action=IVRAction.SPEAK,
                speech="representative",
                reason="All DTMF escapes exhausted — speaking 'representative'",
                confidence=0.2,
            )
            self.decisions.append(decision)
            logger.info(f"[ORGAN 37] LAST RESORT: speaking 'representative'")
            return decision
        
        # Truly exhausted — abort
        self.state = IVRNavState.FAILED
        decision = IVRDecision(
            action=IVRAction.ABORT,
            reason="All navigation strategies exhausted — aborting IVR",
            confidence=0.0,
        )
        self.decisions.append(decision)
        logger.warning(f"[ORGAN 37] ALL STRATEGIES EXHAUSTED — aborting")
        return decision
    
    def _is_human_speaking(self, text: str) -> bool:
        """Detect if a real human has picked up during IVR navigation.
        
        Looks for natural speech patterns that IVR systems don't produce:
        - Questions directed at the caller
        - Informal greetings
        - Reactive language ("hello?", "who's calling?")
        """
        text_lower = text.lower().strip()
        
        # Short reactive utterances = human
        human_markers = [
            'hello?', "who's calling", 'who is this', 'how can i help',
            'what can i do for you', 'may i help you', 'this is ',
            'speaking', "who's this", 'can i help', 'good morning',
            'good afternoon', 'thanks for calling',
        ]
        
        for marker in human_markers:
            if marker in text_lower:
                # But filter out IVR phrases that contain these words
                if any(ivr in text_lower for ivr in ('press', 'dial', 'menu', 'option',
                                                       'extension', 'leave a message')):
                    continue
                return True
        
        # Very short text (under 30 chars) without IVR keywords = probably human
        if len(text_lower) < 30:
            ivr_words = ('press', 'dial', 'menu', 'option', 'extension',
                        'voicemail', 'leave', 'message', 'hours', 'directory')
            if not any(w in text_lower for w in ivr_words):
                # Short, no IVR words = likely human
                # But require at least some content (not just silence/noise)
                if len(text_lower) > 3:
                    return True
        
        return False
    
    def _normalize_prompt(self, text: str) -> str:
        """Normalize menu prompt for loop detection."""
        # Strip numbers, punctuation, excess whitespace
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        # Truncate to first 100 chars for comparison
        return normalized[:100]
    
    def _is_repeated_menu(self, normalized: str) -> bool:
        """Check if we've heard this menu before (stuck in loop)."""
        if not self.menu_history:
            return False
        
        repeat_count = 0
        for prev in self.menu_history:
            # Fuzzy match: 70%+ overlap = same menu
            if self._text_similarity(normalized, prev) > 0.70:
                repeat_count += 1
        
        return repeat_count >= self.MAX_SAME_MENU_REPEATS
    
    @staticmethod
    def _text_similarity(a: str, b: str) -> float:
        """Simple word-overlap similarity between two strings."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0
    
    def get_state_summary(self) -> dict:
        """Get current navigator state for debugging/logging."""
        return {
            'state': self.state.name,
            'attempts': self.attempts,
            'decisions': len(self.decisions),
            'escape_index': self.escape_index,
            'menu_history_count': len(self.menu_history),
            'last_prompt': self._last_prompt[:80] if self._last_prompt else '',
            'last_decision': self.decisions[-1].reason if self.decisions else '',
        }
    
    def get_decision_log(self) -> List[dict]:
        """Get full decision history for audit trail."""
        return [
            {
                'action': d.action.name,
                'digit': d.digit,
                'speech': d.speech,
                'reason': d.reason,
                'confidence': d.confidence,
                'options_count': len(d.options_parsed),
            }
            for d in self.decisions
        ]


# ======================================================================
#  MODULE-LEVEL FACTORY
# ======================================================================

def create_ivr_navigator() -> IVRNavigator:
    """Factory: create a new per-call IVRNavigator instance."""
    return IVRNavigator()
