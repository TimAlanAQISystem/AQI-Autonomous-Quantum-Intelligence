"""
+==============================================================================+
|   ENVIRONMENT-AWARE FIRST-TURN BEHAVIOR SELECTION (EAB)                       |
|   AQI Agent Alan --- Call Environment Classifier                              |
|                                                                               |
|   PURPOSE:                                                                    |
|   Classify the call environment on the FIRST remote utterance and select      |
|   the correct behavioral template to continue the mission.                    |
|                                                                               |
|   ENVIRONMENT CLASSES:                                                        |
|     HUMAN, GOOGLE_CALL_SCREEN, CARRIER_SPAM_BLOCKER, BUSINESS_IVR,            |
|     PERSONAL_VOICEMAIL, CARRIER_VOICEMAIL, AI_RECEPTIONIST,                   |
|     LIVE_RECEPTIONIST, ANSWERING_SERVICE, UNKNOWN                             |
|                                                                               |
|   DETECTION LAYERS:                                                           |
|     Layer 1: Keyphrase regex matching (fast, per-class)                       |
|     Layer 2: Utterance shape analysis (length, structure)                     |
|     Layer 3: Human marker penalty (filler words, questions)                   |
|                                                                               |
|   CONSTITUTIONAL PRINCIPLE:                                                   |
|     On the first remote utterance, Alan must classify the call environment    |
|     and select a behavior template that is legal, efficient, and aligned      |
|     with the mission for that environment.                                    |
|                                                                               |
|   LINEAGE: Built 2026-02-20. Tim's directive: "Alan continues to talk to     |
|   answering machines and phone scanners."                                     |
|                                                                               |
|   SUPERSEDES: The old IVR detector's binary kill logic. The IVR detector      |
|   remains as a fallback layer; EAB runs FIRST and routes behavior.            |
+==============================================================================+
"""

import re
import time
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("EAB")


# ======================================================================
#  ENVIRONMENT CLASSES
# ======================================================================

class EnvironmentClass(Enum):
    """The 10 environment types Alan can encounter on an outbound call."""
    HUMAN = auto()
    GOOGLE_CALL_SCREEN = auto()
    CARRIER_SPAM_BLOCKER = auto()
    BUSINESS_IVR = auto()
    PERSONAL_VOICEMAIL = auto()
    CARRIER_VOICEMAIL = auto()
    AI_RECEPTIONIST = auto()
    LIVE_RECEPTIONIST = auto()
    ANSWERING_SERVICE = auto()
    UNKNOWN = auto()


# ======================================================================
#  ENVIRONMENT ACTIONS — what Alan does in each environment
# ======================================================================

class EnvironmentAction(Enum):
    """The action Alan takes based on environment classification."""
    CONTINUE_MISSION = auto()      # Human — proceed with sales pipeline
    PASS_THROUGH = auto()          # Screener — try to get connected
    NAVIGATE = auto()              # IVR — try to reach a human
    DROP_AND_ABORT = auto()        # Voicemail — short message + hang up
    DECLINE_AND_ABORT = auto()     # Answering service — decline + hang up
    FALLBACK = auto()              # Unknown — safe opener, continue


# ======================================================================
#  ENVIRONMENT PATTERN DEFINITIONS
# ======================================================================

_ENV_PATTERNS: Dict[EnvironmentClass, Dict[str, Any]] = {

    EnvironmentClass.GOOGLE_CALL_SCREEN: {
        "regex": [
            re.compile(r"screen(ing)?\s+service", re.IGNORECASE),
            re.compile(r"the\s+person\s+you(?:'re|\s+are)\s+(?:calling|trying\s+to\s+reach)", re.IGNORECASE),
            re.compile(r"state\s+your\s+name", re.IGNORECASE),
            re.compile(r"why\s+you(?:'re|\s+are)\s+calling", re.IGNORECASE),
            re.compile(r"please\s+say\s+your\s+name", re.IGNORECASE),
            re.compile(r"\bgoogle\b", re.IGNORECASE),
            re.compile(r"call\s+screen", re.IGNORECASE),
            re.compile(r"please\s+(?:stay|remain)\s+on\s+the\s+line", re.IGNORECASE),
            re.compile(r"what\s+company\s+did\s+you\s+say", re.IGNORECASE),
            re.compile(r"screening\s+(?:this|your)\s+call", re.IGNORECASE),
            re.compile(r"describe\s+(?:why|the\s+reason)\s+you(?:'re|\s+are)\s+calling", re.IGNORECASE),
            re.compile(r"I(?:'ll|\s+will)\s+let\s+them\s+know", re.IGNORECASE),
            re.compile(r"I(?:'ll|\s+will)\s+pass\s+(?:that|it)\s+(?:along|on)", re.IGNORECASE),
            re.compile(r"is\s+(?:this|the)\s+call\s+(?:important|urgent)", re.IGNORECASE),
            re.compile(r"are\s+you\s+(?:a\s+)?(?:real\s+person|robot|human)", re.IGNORECASE),
        ],
        "threshold": 0.30,
        "min_hits": 1,
        "action": EnvironmentAction.PASS_THROUGH,
        "max_cycles": 2,
    },

    EnvironmentClass.CARRIER_SPAM_BLOCKER: {
        "regex": [
            re.compile(r"press\s+1\s+to\s+(?:continue|connect)", re.IGNORECASE),
            re.compile(r"this\s+call\s+is\s+being\s+screened", re.IGNORECASE),
            re.compile(r"spam\s+(?:blocker|filter|protection)", re.IGNORECASE),
            re.compile(r"to\s+continue,?\s+press", re.IGNORECASE),
            re.compile(r"verify\s+(?:you(?:'re|\s+are)|you\s+are)\s+(?:a\s+)?(?:real|human|not\s+a\s+robot)", re.IGNORECASE),
            re.compile(r"(?:if\s+you(?:'re|\s+are)|are\s+you)\s+(?:selling|soliciting)", re.IGNORECASE),
            re.compile(r"robocall\s+(?:blocker|filter)", re.IGNORECASE),
            # [FIX 2026-02-20] Catch screener phrases like "you may hang up"
            re.compile(r"(?:you\s+)?(?:may|can)\s+hang\s+up", re.IGNORECASE),
            re.compile(r"if\s+you\s+(?:have\s+)?(?:a\s+)?record(?:ing)?", re.IGNORECASE),
            # [FIX R5b 2026-02-20] Telemarketer screener variants
            re.compile(r"if\s+you\s+are\s+a\s+telemarketer", re.IGNORECASE),
            re.compile(r"(?:this|it)\s+is\s+a\s+recording", re.IGNORECASE),
        ],
        "threshold": 0.35,
        "min_hits": 1,
        "action": EnvironmentAction.PASS_THROUGH,
        "max_cycles": 2,
    },

    EnvironmentClass.BUSINESS_IVR: {
        "regex": [
            re.compile(r"for\s+(?:sales|support|billing|service|customer),?\s*press", re.IGNORECASE),
            re.compile(r"your\s+call\s+(?:may|is)\s+(?:being\s+)?(?:recorded|monitored)", re.IGNORECASE),
            re.compile(r"please\s+listen\s+carefully", re.IGNORECASE),
            re.compile(r"menu\s+options?\s+(?:have|has)\s+changed", re.IGNORECASE),
            re.compile(r"press\s+(?:one|two|three|four|five|six|seven|eight|nine|zero|\d)\s+(?:for|to)", re.IGNORECASE),
            re.compile(r"main\s+menu", re.IGNORECASE),
            # [FIX R5b 2026-02-20] Curly apostrophe support — STT uses both straight and curly
            re.compile(r"if\s+you\s+know\s+your\s+party['’]?s?\s+extension", re.IGNORECASE),
            re.compile(r"dial\s+(?:one|two|three|four|five|six|seven|eight|nine|zero|\d)", re.IGNORECASE),
            re.compile(r"to\s+speak\s+(?:to|with)\s+(?:a\s+)?(?:representative|operator|agent)", re.IGNORECASE),
            re.compile(r"para\s+espa[nñ]ol", re.IGNORECASE),
            re.compile(r"press\s+(?:the\s+)?(?:star|pound|hash)", re.IGNORECASE),
            # [FIX 2026-02-20] Catch reversed IVR pattern "for X, press N" (with optional "please", multi-comma)
            re.compile(r"for\s+[\w\s,]+[,\s]+(?:please\s+)?press\s+(?:one|two|three|four|five|six|seven|eight|nine|zero|\d)", re.IGNORECASE),
            # [NEG PROOF FIX] "if you schedule/want/need... press N" — conditional IVR syntax
            # [FIX R5 2026-02-20] Added (?:please\s+)? — A-Plus Auto: "If you have any calls, please press two"
            # [FIX R5b 2026-02-20] Added apostrophe to char class — "party's extension" etc.
            # Includes curly apostrophe (’) for STT compatibility
            re.compile(r"if\s+you\s+[\w\s'’]+,?\s*(?:please\s+)?press\s+(?:one|two|three|four|five|six|seven|eight|nine|zero|\d)", re.IGNORECASE),
            # [FIX 2026-02-20] "hear these options again" / "hear our menu"
            re.compile(r"(?:hear|repeat)\s+(?:these|the|our)\s+(?:options|menu)", re.IGNORECASE),
            # [FIX R5 2026-02-20] Handle "thank you again for calling" + optional trailing business name
            re.compile(r"thank\s+you\s+(?:(?:so\s+much|again)\s+)?for\s+calling(?:\s+\w+)?", re.IGNORECASE),
            re.compile(r"select\s+from\s+the\s+following", re.IGNORECASE),
            re.compile(r"all\s+(?:of\s+our\s+)?(?:agents|representatives|operators)\s+are\s+(?:busy|currently)", re.IGNORECASE),
            re.compile(r"your\s+call\s+is\s+important", re.IGNORECASE),
            re.compile(r"estimated\s+wait\s+time", re.IGNORECASE),
            re.compile(r"please\s+hold", re.IGNORECASE),
        ],
        "threshold": 0.35,
        "min_hits": 1,
        "action": EnvironmentAction.NAVIGATE,
        "max_cycles": 2,
    },

    EnvironmentClass.PERSONAL_VOICEMAIL: {
        "regex": [
            re.compile(r"leave\s+(?:me\s+)?(?:a\s+)?message", re.IGNORECASE),
            re.compile(r"(?:at|after)\s+the\s+(?:tone|beep)", re.IGNORECASE),
            re.compile(r"(?:not\s+available|unavailable)\s+(?:right\s+now|to\s+take)", re.IGNORECASE),
            re.compile(r"mailbox\s+is\s+full", re.IGNORECASE),
            re.compile(r"record\s+your\s+message", re.IGNORECASE),
            re.compile(r"(?:re-?record|delete|send)\s+(?:this|your)\s+message", re.IGNORECASE),
            re.compile(r"(?:can'?t|cannot)\s+(?:take|answer|come\s+to)", re.IGNORECASE),
            re.compile(r"leave\s+your\s+(?:name|number|message)", re.IGNORECASE),
            re.compile(r"(?:stepped|away)\s+(?:from|out)", re.IGNORECASE),
            re.compile(r"(?:get|come)\s+to\s+the\s+phone", re.IGNORECASE),
            # [FIX 2026-02-20] Catch standalone "beep" in STT (voicemail beep transcribed)
            re.compile(r"^\s*beep\.?\s*$", re.IGNORECASE),
            re.compile(r"\bbeep\b.*\bbeep\b", re.IGNORECASE),
            # [FIX R5b 2026-02-20] "Beep. roofing." — STT transcribes beep + business name fragment
            re.compile(r"\bbeep\.?\s+\w+ing\b", re.IGNORECASE),
            # [FIX R5b 2026-02-20] "your call has been forwarded" — carrier voicemail redirect
            re.compile(r"your\s+call\s+has\s+been\s+forwarded", re.IGNORECASE),
            # [FIX 2026-02-20] "finished recording" voicemail cues — requires voicemail context to avoid false positives
            # NEG PROOF: "We finished recording our inventory" was false-positive without context guard
            # [FIX R5b 2026-02-20] Added \s+are — "when you are done recording, press pound"
            re.compile(r"when\s+you(?:'ve|\s+are)?\s+(?:finished|done)\s+record(?:ing)?", re.IGNORECASE),
            re.compile(r"(?:finished|done)\s+record(?:ing)?[,.]?\s*(?:hang\s+up|press|you\s+may)", re.IGNORECASE),
            # [FIX R5 2026-02-20] Explicit voicemail keyword — Heating & Cooling: "We have a non-emergency voicemail."
            re.compile(r"(?:have|reached|this\s+is)\s+(?:a\s+)?(?:[\w-]+\s+)*voicemail", re.IGNORECASE),
            # [FIX 2026-02-24] Phone number recitation — VMs recite digits as words
            # "three three four two seven two seven three three four" = phone number
            re.compile(r"(?:(?:zero|one|two|three|four|five|six|seven|eight|nine|oh)\s+){3,}", re.IGNORECASE),
            # [FIX 2026-02-24] "if you have reached this message/number/recording"
            re.compile(r"if\s+you\s+(?:have\s+)?reached\s+this\s+(?:message|number|recording)", re.IGNORECASE),
            # [FIX 2026-02-24] "to send this message press pound" — post-recording VM menu
            re.compile(r"to\s+(?:send|cancel|delete|re-?record)\s+(?:this|your)\s+message", re.IGNORECASE),
        ],
        "threshold": 0.30,
        "min_hits": 1,
        "action": EnvironmentAction.DROP_AND_ABORT,
        "max_cycles": 0,
    },

    EnvironmentClass.CARRIER_VOICEMAIL: {
        "regex": [
            re.compile(r"the\s+(?:wireless|mobile|cellular)\s+(?:customer|subscriber)", re.IGNORECASE),
            re.compile(r"(?:is\s+)?not\s+(?:available|in\s+service)", re.IGNORECASE),
            re.compile(r"cannot\s+take\s+your\s+call", re.IGNORECASE),
            re.compile(r"has\s+not\s+set\s+up\s+(?:their\s+)?voicemail", re.IGNORECASE),
            re.compile(r"(?:has\s+been|is)\s+disconnected", re.IGNORECASE),
            re.compile(r"you\s+have\s+reached", re.IGNORECASE),
            re.compile(r"no\s+one\s+is\s+available", re.IGNORECASE),
            re.compile(r"reached\s+the\s+voicemail", re.IGNORECASE),
        ],
        "threshold": 0.30,
        "min_hits": 1,
        "action": EnvironmentAction.DROP_AND_ABORT,
        "max_cycles": 0,
    },

    EnvironmentClass.AI_RECEPTIONIST: {
        "regex": [
            re.compile(r"how\s+(?:can|may)\s+I\s+(?:direct|help|assist)", re.IGNORECASE),
            re.compile(r"who\s+(?:may|can|shall)\s+I\s+say\s+is\s+calling", re.IGNORECASE),
            re.compile(r"what\s+is\s+this\s+(?:regarding|about|in\s+reference)", re.IGNORECASE),
            re.compile(r"virtual\s+(?:receptionist|assistant|agent)", re.IGNORECASE),
            re.compile(r"how\s+(?:can|may)\s+I\s+(?:direct|route)\s+your\s+call", re.IGNORECASE),
            re.compile(r"who\s+(?:are\s+you|is\s+calling)", re.IGNORECASE),
            re.compile(r"(?:can|could)\s+you\s+(?:tell\s+me|say)\s+(?:what|why)", re.IGNORECASE),
        ],
        "threshold": 0.40,
        "min_hits": 1,
        "action": EnvironmentAction.PASS_THROUGH,
        "max_cycles": 2,
    },

    EnvironmentClass.ANSWERING_SERVICE: {
        "regex": [
            re.compile(r"answering\s+service", re.IGNORECASE),
            re.compile(r"taking\s+(?:calls|messages)\s+for", re.IGNORECASE),
            re.compile(r"(?:may|can)\s+I\s+take\s+(?:a\s+)?message", re.IGNORECASE),
            re.compile(r"after\s+hours?\s+(?:service|answering)", re.IGNORECASE),
        ],
        "threshold": 0.40,
        "min_hits": 1,
        "action": EnvironmentAction.DECLINE_AND_ABORT,
        "max_cycles": 0,
    },
}

# Human speech markers — presence reduces non-human confidence
HUMAN_MARKERS = [
    re.compile(r"\b(?:um|uh|hmm|hm|ah)\b", re.IGNORECASE),
    # [FIX R5b 2026-02-20] "like" as filler only — exclude verb usage ("would like to", "I'd like to")
    re.compile(r"\blike\b(?!\s+to\b)", re.IGNORECASE),
    re.compile(r"\b(?:you know|I mean|well)\b", re.IGNORECASE),
    re.compile(r"\b(?:yeah|yep|nah|nope|yea)\b", re.IGNORECASE),
    re.compile(r"\?$"),
    re.compile(r"\b(?:who|what|why|how)\s+(?:is|are|do|did|can|would)\b", re.IGNORECASE),
    re.compile(r"\b(?:I'm|I am|we're|we are|my\s+name|my\s+business)\b", re.IGNORECASE),
    # [FIX R5b 2026-02-20] Split "wait" out — exclude "wait time" (IVR phrase, not human filler)
    re.compile(r"\b(?:hold on|one second|let me|hang on|gimme)\b", re.IGNORECASE),
    re.compile(r"\bwait\b(?!\s+time)", re.IGNORECASE),
    re.compile(r"\b(?:actually|honestly|basically|seriously)\b", re.IGNORECASE),
    # [FIX 2026-02-24] "go ahead" — conversational directive, VMs don't use this
    re.compile(r"\bgo\s+ahead\b", re.IGNORECASE),
    # [FIX 2026-02-24] "tell me" — human conversational request
    re.compile(r"\btell\s+me\b", re.IGNORECASE),
]


# ======================================================================
#  CLASSIFICATION RESULT
# ======================================================================

@dataclass
class ClassificationResult:
    """Result of environment classification."""
    env_class: EnvironmentClass
    confidence: float
    action: EnvironmentAction
    max_cycles: int
    reason: str
    hits: int
    human_markers: int
    utterance: str
    timestamp_ms: float


# ======================================================================
#  CALL ENVIRONMENT CLASSIFIER
# ======================================================================

class CallEnvironmentClassifier:
    """
    Classifies the call environment from the first remote utterance.
    
    Architecture:
      1. Run all pattern sets against the transcript
      2. Score each environment class: (hits / patterns) * stt_confidence
      3. Apply human marker penalty to non-human classes
      4. Select highest-scoring class above threshold
      5. Default to UNKNOWN → HUMAN fallback
    
    Integration:
      Called from the relay server STT pipeline, BEFORE cognition.
      Result determines which behavior template Alan uses.
    """

    def __init__(self, patterns: Dict[EnvironmentClass, Dict[str, Any]] = None):
        self.patterns = patterns or _ENV_PATTERNS
        self.last_result: Optional[ClassificationResult] = None
        self._cycle_count: int = 0
        self._classification_locked: bool = False

    def classify(
        self,
        transcript: str,
        stt_confidence: float = 0.90,
        turn_number: int = 0,
    ) -> ClassificationResult:
        """
        Classify environment from transcript.
        
        Args:
            transcript: STT text from remote side
            stt_confidence: STT confidence score (0.0-1.0)
            turn_number: Which merchant turn this is (0-based)
            
        Returns:
            ClassificationResult with environment class, action, and metadata
        """
        text = transcript.lower().strip()
        now_ms = time.time() * 1000

        if not text or len(text) < 3:
            result = ClassificationResult(
                env_class=EnvironmentClass.UNKNOWN,
                confidence=0.0,
                action=EnvironmentAction.FALLBACK,
                max_cycles=0,
                reason="empty_transcript",
                hits=0,
                human_markers=0,
                utterance=transcript,
                timestamp_ms=now_ms,
            )
            self.last_result = result
            return result

        # Count human markers
        human_marker_count = sum(1 for p in HUMAN_MARKERS if p.search(text))

        # Score each environment class
        scores: Dict[EnvironmentClass, Tuple[float, int]] = {}
        for env_class, cfg in self.patterns.items():
            hits = sum(1 for rx in cfg["regex"] if rx.search(text))
            if hits == 0:
                continue
            
            # Score: step function based on hit count (not normalized by pattern count)
            # This prevents environments with many patterns from being unfairly diluted.
            # 1 hit = 0.45, 2 hits = 0.70, 3 hits = 0.85, 4+ hits = 0.95
            if hits >= 4:
                base_score = 0.95
            elif hits >= 3:
                base_score = 0.85
            elif hits >= 2:
                base_score = 0.70
            else:
                base_score = 0.45
            
            score = base_score * stt_confidence
            
            # Apply human marker penalty for non-human classes
            # [FIX 2026-02-24 NEG-PROOF] Increased penalty from 0.08 to 0.15 per
            # marker. Old 0.08 was too low — phrases like "we'll get back to you"
            # and "not available right now" are common in both VM and human speech.
            # With human markers present, we need stronger suppression of single-hit
            # VM matches to prevent false-killing human calls.
            if human_marker_count > 0:
                penalty = min(human_marker_count * 0.15, 0.30)
                score = max(0.0, score - penalty)
            
            scores[env_class] = (score, hits)

        # Select best class above threshold
        best_env = EnvironmentClass.UNKNOWN
        best_score = 0.0
        best_hits = 0
        best_action = EnvironmentAction.FALLBACK
        best_max_cycles = 0
        reason_parts = []

        for env_class, (score, hits) in sorted(scores.items(), key=lambda x: x[1][0], reverse=True):
            cfg = self.patterns[env_class]
            if hits >= cfg.get("min_hits", 1) and score >= cfg["threshold"]:
                # [FIX 2026-02-24] Prefer DROP_AND_ABORT (voicemail) over NAVIGATE (IVR)
                # when scores are tied. False-positive on VM is cheaper than continuing
                # a conversation with a VM classified as IVR (NAVIGATE tries to talk to it).
                if best_env != EnvironmentClass.UNKNOWN:
                    # Already found a match — only override if new match is DROP/DECLINE_AND_ABORT
                    # and current match was NAVIGATE/PASS_THROUGH with same or lower score.
                    if (cfg["action"] in (EnvironmentAction.DROP_AND_ABORT, EnvironmentAction.DECLINE_AND_ABORT)
                        and best_action not in (EnvironmentAction.DROP_AND_ABORT, EnvironmentAction.DECLINE_AND_ABORT)
                        and score >= best_score - 0.05):
                        best_env = env_class
                        best_score = score
                        best_hits = hits
                        best_action = cfg["action"]
                        best_max_cycles = cfg.get("max_cycles", 0)
                        reason_parts.append(f"{env_class.name}(hits={hits},score={score:.2f},abort_priority)")
                    # else keep current match
                else:
                    best_env = env_class
                    best_score = score
                    best_hits = hits
                    best_action = cfg["action"]
                    best_max_cycles = cfg.get("max_cycles", 0)
                    reason_parts.append(f"{env_class.name}(hits={hits},score={score:.2f})")
                if cfg["action"] in (EnvironmentAction.DROP_AND_ABORT, EnvironmentAction.DECLINE_AND_ABORT):
                    break  # Found an abort class — stop looking

        # If nothing matched AND we have human markers → classify as HUMAN
        if best_env == EnvironmentClass.UNKNOWN and human_marker_count > 0:
            best_env = EnvironmentClass.HUMAN
            best_score = min(0.5 + human_marker_count * 0.1, 0.9)
            best_action = EnvironmentAction.CONTINUE_MISSION
            best_max_cycles = 0
            reason_parts.append(f"HUMAN(markers={human_marker_count})")

        # If truly unknown and utterance is short natural speech → assume HUMAN
        # (Quick " hello?" / "Yeah?" / "This is Mike" type responses)
        # [FIX 2026-02-24] Tightened: exclude garbled fragments that contain
        # no recognizable conversational words. Require at least one common
        # human greeting/response word OR a question mark to qualify.
        if best_env == EnvironmentClass.UNKNOWN:
            word_count = len(text.split())
            _has_conversational_signal = bool(
                re.search(r"\b(?:hello|hey|hi|yes|yeah|yep|no|nah|nope|what|who|why|"
                          r"how|this\s+is|speaking|can\s+I|may\s+I|I'm|I\s+am|"
                          r"we're|we\s+are|sure|okay|ok|good)\b", text, re.IGNORECASE)
                or text.rstrip().endswith("?")
            )
            if word_count <= 8 and _has_conversational_signal:
                best_env = EnvironmentClass.HUMAN
                best_score = 0.40
                best_action = EnvironmentAction.CONTINUE_MISSION
                reason_parts.append(f"HUMAN(short_natural,words={word_count})")
            else:
                reason_parts.append("UNKNOWN(no_match)")

        # Build reason string
        reason = " | ".join(reason_parts) if reason_parts else "no_match"
        if human_marker_count > 0:
            reason += f" | human_markers={human_marker_count}"

        result = ClassificationResult(
            env_class=best_env,
            confidence=round(best_score, 3),
            action=best_action,
            max_cycles=best_max_cycles,
            reason=reason,
            hits=best_hits,
            human_markers=human_marker_count,
            utterance=transcript,
            timestamp_ms=now_ms,
        )

        self.last_result = result
        self._cycle_count += 1

        logger.info(
            f"[EAB] CLASSIFIED: {best_env.name} (conf={best_score:.2f}, hits={best_hits}, "
            f"human_markers={human_marker_count}) | action={best_action.name} | "
            f"text='{transcript[:80]}'"
        )

        return result

    def reclassify(self, transcript: str, stt_confidence: float = 0.90) -> ClassificationResult:
        """
        Re-classify on subsequent utterances (e.g., second screener prompt).
        Same logic, but increments cycle counter for loop detection.
        """
        result = self.classify(transcript, stt_confidence, turn_number=self._cycle_count)
        return result

    def should_abort_loop(self) -> bool:
        """Check if we've exceeded max cycles for the current environment."""
        if not self.last_result:
            return False
        if self.last_result.max_cycles == 0:
            return False
        return self._cycle_count > self.last_result.max_cycles

    def get_cycle_count(self) -> int:
        return self._cycle_count

    def reset(self):
        """Reset for a new call."""
        self.last_result = None
        self._cycle_count = 0
        self._classification_locked = False


# ======================================================================
#  BEHAVIOR TEMPLATES — what Alan says in each environment
# ======================================================================

class EnvironmentBehaviorTemplates:
    """
    Behavior templates for each environment class.
    
    Each template returns the TTS text Alan should speak.
    Templates use merchant context from the call.
    """

    @staticmethod
    def human_opener(merchant_name: str, **kwargs) -> str:
        """Direct opener for confirmed human."""
        # Return empty — let the normal cognition pipeline handle the greeting.
        # The EAB system just confirms this is a human and lets the existing
        # smart_greeting_routine / pipeline continue as designed.
        return ""

    @staticmethod
    def screen_pass_through(merchant_name: str, cycle: int = 0, **kwargs) -> str:
        """Google Call Screen / carrier screener — attempt pass-through."""
        if cycle == 0:
            if merchant_name:
                return f"Hi, this is Alan calling for {merchant_name}. It's about their merchant account. Please connect me."
            return "Hi, this is Alan calling about a merchant account. Please connect me."
        else:
            return "Alan, merchant services. Please connect me."

    @staticmethod
    def spam_pass_through(merchant_name: str, cycle: int = 0, **kwargs) -> str:
        """Carrier spam blocker — brief identification."""
        return "Alan, merchant services. Connect."

    @staticmethod
    def ivr_navigation(merchant_name: str, **kwargs) -> str:
        """Business IVR — attempt to reach a human."""
        return "Hi, I'm calling for the business owner."

    @staticmethod
    def voicemail_drop(merchant_name: str, **kwargs) -> str:
        """Voicemail — drop short message and abort."""
        return "Hey, this is Alan — I'll try you again later."

    @staticmethod
    def ai_receptionist_opener(merchant_name: str, cycle: int = 0, **kwargs) -> str:
        """AI receptionist — clearly state purpose."""
        if merchant_name:
            return f"Alan calling for {merchant_name} about their merchant account. Please connect me."
        return "Alan calling about a merchant account. Please connect me."

    @staticmethod
    def live_receptionist_opener(merchant_name: str, **kwargs) -> str:
        """Live receptionist — warm handoff."""
        if merchant_name:
            return f"Hi there — Alan calling for {merchant_name} about their merchant account."
        return "Hi there — Alan calling about a merchant account."

    @staticmethod
    def answering_service_decline(merchant_name: str, **kwargs) -> str:
        """Answering service — decline to leave message."""
        if merchant_name:
            return f"Alan calling for {merchant_name}. I'll try them back directly."
        return "No worries, I'll try back directly."

    @staticmethod
    def fallback_opener(merchant_name: str, **kwargs) -> str:
        """Unknown environment — safe neutral opener."""
        # Return empty — let normal pipeline handle it.
        return ""

    @classmethod
    def get_template(cls, env_class: EnvironmentClass, merchant_name: str, cycle: int = 0) -> str:
        """
        Get the behavior template text for an environment class.
        
        Returns:
            TTS text for Alan to speak, or "" if normal pipeline should handle it.
        """
        TEMPLATE_MAP = {
            EnvironmentClass.HUMAN: cls.human_opener,
            EnvironmentClass.GOOGLE_CALL_SCREEN: cls.screen_pass_through,
            EnvironmentClass.CARRIER_SPAM_BLOCKER: cls.spam_pass_through,
            EnvironmentClass.BUSINESS_IVR: cls.ivr_navigation,
            EnvironmentClass.PERSONAL_VOICEMAIL: cls.voicemail_drop,
            EnvironmentClass.CARRIER_VOICEMAIL: cls.voicemail_drop,
            EnvironmentClass.AI_RECEPTIONIST: cls.ai_receptionist_opener,
            EnvironmentClass.LIVE_RECEPTIONIST: cls.live_receptionist_opener,
            EnvironmentClass.ANSWERING_SERVICE: cls.answering_service_decline,
            EnvironmentClass.UNKNOWN: cls.fallback_opener,
        }
        fn = TEMPLATE_MAP.get(env_class, cls.fallback_opener)
        return fn(merchant_name=merchant_name, cycle=cycle)


# ======================================================================
#  CONVENIENCE EXPORTS
# ======================================================================

def create_classifier() -> CallEnvironmentClassifier:
    """Factory: create a new CallEnvironmentClassifier with default patterns."""
    return CallEnvironmentClassifier(_ENV_PATTERNS)
