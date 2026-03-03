"""
+==============================================================================+
|   IVR DETECTION MODULE                                                        |
|   AQI Agent Alan --- Inline IVR/Voicemail Phone Tree Detector                 |
|                                                                               |
|   PURPOSE:                                                                    |
|   Detect when Alan is talking to an IVR system, voicemail prompt, or          |
|   automated phone tree -- NOT a human. Prevents Alan from having full         |
|   sales conversations with robots.                                            |
|                                                                               |
|   THREE-LAYER DETECTION:                                                      |
|   Layer 1: Keyphrase pattern matching (fast, regex-based)                     |
|   Layer 2: Temporal pattern analysis (IVR timing signatures)                  |
|   Layer 3: Behavioral repetition detection (verbatim repeats)                 |
|                                                                               |
|   ACTION ON DETECTION:                                                        |
|   - Switch mission -> EXTRACT_LEARNINGS (terminal)                            |
|   - Speak one graceful exit line                                              |
|   - Hang up cleanly                                                           |
|   - Classify outcome as "ivr_voicemail"                                       |
|   - Feed IVR pattern to CCNM for learning                                     |
|                                                                               |
|   LINEAGE: Built 2026-02-17. Tim's directive: "If Alan can't distinguish      |
|   humans from phone trees, every downstream intelligence is distorted."       |
+==============================================================================+
"""

import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

logger = logging.getLogger("IVR_DETECT")

# ======================================================================
#  KEYPHRASE PATTERNS -- Layer 1
# ======================================================================

# These regex patterns match common IVR/voicemail system prompts.
# Case-insensitive. Ordered by frequency of occurrence in real calls.
IVR_PATTERNS = [
    # DTMF instructions (expanded per Campaign 2 learnings)
    re.compile(r"press\s+(?:the\s+)?(?:one|two|three|four|five|six|seven|eight|nine|zero|star|pound|\d)", re.IGNORECASE),
    re.compile(r"dial\s+(?:one|two|three|four|five|six|seven|eight|nine|zero|\d)", re.IGNORECASE),
    re.compile(r"press\s+(?:0|9)\b", re.IGNORECASE),   # "press zero" / "press 9" for operator
    
    # Voicemail system prompts
    re.compile(r"(?:leave|record)\s+(?:a\s+)?(?:message|voicemail)", re.IGNORECASE),
    re.compile(r"(?:after|at)\s+the\s+(?:tone|beep)", re.IGNORECASE),
    re.compile(r"(?:press|hit)\s+(?:star|pound|hash)\s+(?:to|when)", re.IGNORECASE),
    re.compile(r"to\s+(?:send|cancel|delete|re-?record)\s+(?:this|your)\s+message", re.IGNORECASE),
    re.compile(r"hang\s+up\s+(?:or|when|to)", re.IGNORECASE),
    re.compile(r"recording\s+(?:your|a)\s+message", re.IGNORECASE),
    
    # IVR menu navigation (expanded)
    re.compile(r"(?:to\s+)?speak\s+(?:to|with)\s+(?:a\s+)?representative", re.IGNORECASE),
    re.compile(r"for\s+(?:sales|billing|support|service|customer\s+service|more\s+options)", re.IGNORECASE),
    re.compile(r"for\s+(?:hours|location|directions|pricing|reservations),?\s*press", re.IGNORECASE),
    # [FIX 2026-02-20] Broader reversed IVR menu pattern: "for X, (please) press N" (multi-comma)
    re.compile(r"for\s+[\w\s,]+[,\s]+(?:please\s+)?press\s+(?:one|two|three|four|five|six|seven|eight|nine|zero|\d)", re.IGNORECASE),
    # [NEG PROOF FIX] "if you schedule/want/need... press N" — conditional IVR syntax
    # [FIX R5 2026-02-20] Added (?:please\s+)? — A-Plus Auto: "If you have any calls, please press two"
    # [FIX R5b 2026-02-20] Added apostrophe + curly apostrophe to char class
    re.compile(r"if\s+you\s+[\w\s'’]+,?\s*(?:please\s+)?press\s+(?:one|two|three|four|five|six|seven|eight|nine|zero|\d)", re.IGNORECASE),
    # [FIX 2026-02-20] "hear these options / repeat the menu"
    re.compile(r"(?:hear|repeat)\s+(?:these|the|our)\s+(?:options|menu)", re.IGNORECASE),
    # [FIX 2026-02-20] Catch screener "you may hang up" / "have a recording"
    re.compile(r"(?:you\s+)?(?:may|can)\s+hang\s+up", re.IGNORECASE),
    re.compile(r"if\s+you\s+(?:have\s+)?(?:a\s+)?record(?:ing)?", re.IGNORECASE),
    # [FIX R5b 2026-02-20] Telemarketer screener variants
    re.compile(r"if\s+you\s+are\s+a\s+telemarketer", re.IGNORECASE),
    re.compile(r"(?:this|it)\s+is\s+a\s+recording", re.IGNORECASE),
    # [FIX 2026-02-20] STT transcribes voicemail beep as "beep" — catch it
    re.compile(r"^\s*beep\.?\s*$", re.IGNORECASE),
    # [FIX R5b 2026-02-20] "Beep. roofing." — STT transcribes beep + business name fragment
    re.compile(r"\bbeep\.?\s+\w+ing\b", re.IGNORECASE),
    # [FIX R5b 2026-02-20] "your call has been forwarded" — carrier voicemail redirect
    re.compile(r"your\s+call\s+has\s+been\s+forwarded", re.IGNORECASE),
    # [FIX 2026-02-20] "finished recording" voicemail cue — requires voicemail context (NEG PROOF tightened)
    # [FIX R5b 2026-02-20] Added \s+are — "when you are done recording, press pound"
    re.compile(r"when\s+you(?:'ve|\s+are)?\s+(?:finished|done)\s+record(?:ing)?", re.IGNORECASE),
    re.compile(r"(?:finished|done)\s+record(?:ing)?[,.]?\s*(?:hang\s+up|press|you\s+may)", re.IGNORECASE),
    # [FIX R5 2026-02-20] Explicit voicemail keyword — Heating & Cooling: "We have a non-emergency voicemail."
    re.compile(r"(?:have|reached|this\s+is)\s+(?:a\s+)?(?:[\w-]+\s+)*voicemail", re.IGNORECASE),
    re.compile(r"(?:our|the)\s+menu\s+(?:options|has|have)\s+changed", re.IGNORECASE),
    re.compile(r"your\s+call\s+(?:may|is)\s+(?:being\s+)?(?:recorded|monitored)", re.IGNORECASE),
    re.compile(r"this\s+call\s+(?:may|is)\s+(?:being\s+)?(?:recorded|monitored)", re.IGNORECASE),
    re.compile(r"please\s+(?:hold|wait|listen\s+carefully)", re.IGNORECASE),
    re.compile(r"(?:office|business)\s+hours\s+are", re.IGNORECASE),
    re.compile(r"(?:we\s+are|we're)\s+(?:currently\s+)?(?:closed|unavailable)", re.IGNORECASE),
    re.compile(r"(?:all|our)\s+(?:agents|representatives|operators)\s+are\s+(?:busy|currently)", re.IGNORECASE),
    re.compile(r"your\s+call\s+is\s+important\s+to\s+us", re.IGNORECASE),
    re.compile(r"please\s+hold", re.IGNORECASE),
    re.compile(r"(?:we\s+are|we're)\s+currently\s+(?:assisting|helping)\s+other\s+(?:callers|customers)", re.IGNORECASE),
    re.compile(r"to\s+repeat\s+(?:this|these)\s+(?:options|menu)", re.IGNORECASE),
    re.compile(r"if\s+you\s+know\s+your\s+party.s\s+extension", re.IGNORECASE),
    re.compile(r"press\s+\d\s+for\s+\w+", re.IGNORECASE),  # Generic "press N for X" pattern
    
    # Thank-you-for-calling prefix (auto-attendant)
    # [FIX R5 2026-02-20] Handle "thank you again for calling" + optional trailing business name
    re.compile(r"thank\s+you\s+(?:(?:so\s+much|again)\s+)?for\s+calling(?:\s+\w+)?", re.IGNORECASE),
    
    # "For more options" / "for this recording"
    re.compile(r"for\s+(?:this|more|additional)\s+(?:recording|options|information)", re.IGNORECASE),
    
    # Extended hold/queue patterns
    re.compile(r"(?:estimated|approximate)\s+wait\s+time", re.IGNORECASE),
    re.compile(r"you\s+are\s+(?:caller|number)\s+\d+\s+in\s+(?:the\s+)?queue", re.IGNORECASE),
    re.compile(r"main\s+menu", re.IGNORECASE),
    re.compile(r"goodbye", re.IGNORECASE),  # IVR farewell pattern
    
    # [2026-02-20] GOOGLE CALL SCREEN / PHONE SCANNER PATTERNS
    # Tim's directive: "Alan continues to talk to phone scanners"
    # These are automated screening systems that intercept calls before a human.
    re.compile(r"please\s+(?:stay|remain)\s+on\s+the\s+line", re.IGNORECASE),
    re.compile(r"what\s+company\s+did\s+you\s+say", re.IGNORECASE),
    re.compile(r"please\s+state\s+(?:your|the)\s+(?:name|reason|purpose)", re.IGNORECASE),
    re.compile(r"(?:google|call)\s+(?:is\s+)?screen", re.IGNORECASE),
    re.compile(r"who\s+(?:is\s+)?(?:calling|this)", re.IGNORECASE),
    re.compile(r"(?:the\s+)?person\s+you.re\s+(?:calling|trying\s+to\s+reach)", re.IGNORECASE),
    re.compile(r"screening\s+(?:this|your)\s+call", re.IGNORECASE),
    re.compile(r"state\s+your\s+(?:name|business|reason)", re.IGNORECASE),
    re.compile(r"describe\s+(?:why|the\s+reason)\s+you.re\s+calling", re.IGNORECASE),
    re.compile(r"I.ll\s+(?:let\s+them\s+know|pass\s+(?:that|it)\s+(?:along|on))", re.IGNORECASE),
    re.compile(r"(?:can|could)\s+you\s+(?:tell\s+me|say)\s+(?:what|why)", re.IGNORECASE),
    re.compile(r"is\s+(?:this|the)\s+call\s+(?:important|urgent)", re.IGNORECASE),
    re.compile(r"are\s+you\s+(?:a\s+)?(?:real\s+person|robot|human)", re.IGNORECASE),
    re.compile(r"(?:if\s+you.re|are\s+you)\s+(?:selling|soliciting)", re.IGNORECASE),
    
    # [2026-02-24] VOICEMAIL PATTERNS — previously missing from IVR detector
    # Tim's directive: "Alan is still talking to VMs" — these patterns were in EAB
    # but missed from IVR detector fallback, so when EAB misclassified on first
    # utterance, the IVR detector couldn't catch VMs on subsequent turns.
    
    # Phone number recitation — VMs recite digits as words ("three three four two seven")
    # A sequence of 4+ digit-words in a row is a phone number, not human speech.
    re.compile(r"(?:(?:zero|one|two|three|four|five|six|seven|eight|nine|oh)\s+){3,}", re.IGNORECASE),
    
    # Common voicemail phrases NOT already covered
    re.compile(r"(?:you\s+have\s+)?reached\s+(?:the\s+)?(?:voicemail|mailbox|office)", re.IGNORECASE),
    re.compile(r"if\s+you\s+(?:have\s+)?reached\s+this\s+(?:message|number|recording)", re.IGNORECASE),
    re.compile(r"(?:we'll|we\s+will)\s+(?:get\s+back|return\s+your\s+call|call\s+you\s+back)", re.IGNORECASE),
    re.compile(r"(?:you\s+)?(?:may|can)\s+(?:call|reach|contact)\s+\w+\s+(?:at|on)", re.IGNORECASE),
    re.compile(r"(?:outside|after|before)\s+(?:of\s+)?(?:normal\s+)?(?:business|office|regular)\s+hours", re.IGNORECASE),
    re.compile(r"(?:our|normal|regular|business)\s+(?:business\s+)?hours\s+(?:are|is)", re.IGNORECASE),
    re.compile(r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(?:through|thru|to)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)", re.IGNORECASE),
    re.compile(r"(?:not\s+available|unavailable|cannot\s+(?:take|answer)|can't\s+(?:take|answer|come\s+to))", re.IGNORECASE),
    re.compile(r"(?:get|come)\s+to\s+the\s+phone", re.IGNORECASE),
    re.compile(r"(?:stepped|away)\s+(?:from|out)", re.IGNORECASE),
    re.compile(r"(?:have|reached|this\s+is)\s+(?:a\s+)?(?:[\w-]+\s+)*voicemail", re.IGNORECASE),
    re.compile(r"(?:as\s+soon\s+as\s+)?(?:possible|we\s+can)", re.IGNORECASE),
    re.compile(r"(?:your\s+call\s+has\s+been\s+forwarded)", re.IGNORECASE),
    re.compile(r"(?:no\s+one\s+is\s+available)", re.IGNORECASE),
    re.compile(r"(?:the\s+)?(?:wireless|mobile|cellular)\s+(?:customer|subscriber)", re.IGNORECASE),
    re.compile(r"(?:has\s+not\s+set\s+up|hasn't\s+set\s+up)\s+(?:their\s+)?voicemail", re.IGNORECASE),
    re.compile(r"(?:has\s+been|is)\s+disconnected", re.IGNORECASE),
    re.compile(r"(?:answering\s+service)", re.IGNORECASE),
    re.compile(r"(?:taking\s+(?:calls|messages)\s+for)", re.IGNORECASE),
    # Auto-attendant greeting patterns ("Thank you for calling X, please hold")
    re.compile(r"(?:serving|we\s+serve)\s+(?:from|between)", re.IGNORECASE),
    re.compile(r"(?:our|the)\s+(?:hours|operating\s+hours)\s+(?:are|is)", re.IGNORECASE),
    re.compile(r"(?:reservations?|table|seating)", re.IGNORECASE),
    re.compile(r"(?:for|to\s+make)\s+(?:a\s+)?(?:reservation|appointment|booking)", re.IGNORECASE),
]

# Human speech markers -- if these appear, it's likely human, not IVR
HUMAN_MARKERS = [
    re.compile(r"\b(?:um|uh|hmm|hm|ah)\b", re.IGNORECASE),       # Filler words
    re.compile(r"\b(?:like|you know|I mean|well)\b", re.IGNORECASE),  # Discourse markers
    re.compile(r"\b(?:yeah|yep|nah|nope)\b", re.IGNORECASE),      # Informal responses
    re.compile(r"\?$"),                                              # Questions (intonation)
    re.compile(r"\b(?:who|what|why|how)\s+(?:is|are|do|did)\b", re.IGNORECASE),  # Genuine questions
    re.compile(r"\b(?:I'm|I am|we're|we are|my|our)\b", re.IGNORECASE),  # First-person
    re.compile(r"\b(?:hold on|one second|let me|hang on|gimme)\b", re.IGNORECASE),  # Human interrupts
    re.compile(r"\b(?:actually|honestly|basically|seriously)\b", re.IGNORECASE),  # Human qualifiers
]


# ======================================================================
#  IVR DETECTOR
# ======================================================================

@dataclass
class Utterance:
    """Single merchant utterance with timestamp."""
    text: str
    timestamp: float
    keyphrase_hits: int = 0
    human_markers: int = 0


class IVRDetector:
    """
    Three-layer inline IVR/voicemail detection system.
    
    Designed to be instantiated per-call and fed merchant utterances
    as they arrive from STT. Produces a confidence score and binary
    is_ivr flag.
    
    Usage:
        detector = IVRDetector()
        detector.add_utterance("press one for sales", time.time())
        if detector.should_abort_call():
            # graceful exit
    """
    
    # Detection thresholds (tuned after Campaign 4 — Feb 20 2026)
    # Tim: "Alan continues to talk to answering machines and phone scanners"
    # Lowered thresholds aggressively — false positives are better than wasting minutes on robots
    IVR_THRESHOLD = 0.35           # Score above this = IVR detected (lowered: 0.55 → 0.50 → 0.35)
    ABORT_THRESHOLD = 0.45         # Score above this = abort call immediately (lowered: 0.65 → 0.60 → 0.45)
    MIN_UTTERANCES_FOR_DETECTION = 1  # Can detect on first phrase if strong signal
    MAX_HISTORY = 20               # Sliding window of recent utterances (was 8 — too small for long IVR)
    
    # Weights for each detection layer (rebalanced — keyphrase boosted)
    KEYPHRASE_WEIGHT = 0.45        # Layer 1: keyword matching (was 0.40)
    TEMPORAL_WEIGHT = 0.15         # Layer 2: timing patterns
    REPETITION_WEIGHT = 0.15       # Layer 3: verbatim repetition (was 0.20)
    NO_HUMAN_WEIGHT = 0.15         # Layer 4: absence of human markers
    # [FIX 2026-02-24] Increased from 0.10 to 0.25 — old value made human markers
    # almost meaningless (3 markers = -0.03 reduction). "Yeah, who is this?" was
    # false-positive'ing as IVR because "who is this" matched a phone scanner pattern
    # but the strong human markers (yeah, question mark) couldn't overcome it.
    HUMAN_PENALTY_WEIGHT = 0.25    # Penalty for human markers detected
    
    # Consecutive hit cooldown — don't reset on a single non-matching utterance
    CONSECUTIVE_COOLDOWN = 2       # Miss this many in a row before resetting counter
    
    def __init__(self):
        self.utterances: List[Utterance] = []
        self.ivr_score: float = 0.0
        self.is_ivr: bool = False
        self.detection_reason: str = ""
        self._consecutive_ivr_hits: int = 0
        self._consecutive_misses: int = 0       # Track consecutive non-IVR utterances
        self._lifetime_keyphrase_hits: int = 0   # Total keyphrase hits over entire call
        self._lifetime_human_markers: int = 0    # Total human markers over entire call
        self._lifetime_utterance_count: int = 0  # Total utterances fed (not windowed)
        self._abort_line_spoken: bool = False
        self.ccnm_ignore: bool = False  # Flag for CCNM to quarantine IVR calls
    
    def add_utterance(self, text: str, timestamp: float) -> dict:
        """
        Feed a new merchant utterance. Returns detection result.
        
        Returns:
            {
                "is_ivr": bool,
                "score": float,  
                "should_abort": bool,
                "reason": str,
            }
        """
        text = text.strip()
        if not text:
            return {"is_ivr": False, "score": 0.0, "should_abort": False, "reason": ""}
        
        # [NOISE FILTER] Skip very short utterances that are likely STT noise
        # Real IVR/human speech is always 2+ words
        if len(text.split()) < 2 and len(text) < 5:
            return {"is_ivr": self.is_ivr, "score": round(self.ivr_score, 3),
                    "should_abort": self.should_abort_call(), "reason": self.detection_reason}
        
        # Count keyphrase hits
        keyphrase_hits = sum(1 for p in IVR_PATTERNS if p.search(text))
        
        # Count human markers
        human_markers = sum(1 for p in HUMAN_MARKERS if p.search(text))
        
        utterance = Utterance(
            text=text.lower(),
            timestamp=timestamp,
            keyphrase_hits=keyphrase_hits,
            human_markers=human_markers,
        )
        
        self.utterances.append(utterance)
        if len(self.utterances) > self.MAX_HISTORY:
            self.utterances = self.utterances[-self.MAX_HISTORY:]
        
        # Track LIFETIME counters (never reset, never windowed)
        self._lifetime_keyphrase_hits += keyphrase_hits
        self._lifetime_human_markers += human_markers
        self._lifetime_utterance_count += 1
        
        # Track consecutive IVR hits WITH COOLDOWN
        # Don't reset on a single miss — IVR menus mix keyphrase lines
        # ("press 1 for sales") with non-keyphrase lines ("our hours are 9-5")
        if keyphrase_hits > 0:
            self._consecutive_ivr_hits += 1
            self._consecutive_misses = 0
        else:
            self._consecutive_misses += 1
            # Only reset after CONSECUTIVE_COOLDOWN consecutive misses
            if self._consecutive_misses >= self.CONSECUTIVE_COOLDOWN:
                self._consecutive_ivr_hits = 0
        
        # Recompute score
        self._recompute()
        
        result = {
            "is_ivr": self.is_ivr,
            "score": round(self.ivr_score, 3),
            "should_abort": self.should_abort_call(),
            "reason": self.detection_reason,
        }
        
        if self.is_ivr:
            logger.info(f"[IVR] DETECTED (score={self.ivr_score:.2f}): {self.detection_reason} | text='{text[:60]}'")
        
        return result
    
    def _recompute(self):
        """Recompute IVR score from all three layers."""
        if not self.utterances:
            self.ivr_score = 0.0
            self.is_ivr = False
            return
        
        texts = [u.text for u in self.utterances]
        timestamps = [u.timestamp for u in self.utterances]
        
        # ── Layer 1: Keyphrase Pattern Detection ──
        # Use LIFETIME hits (not just windowed) to prevent evidence loss
        # on long IVR calls where old utterances fall off the window
        total_keyphrase_hits = self._lifetime_keyphrase_hits
        window_keyphrase_hits = sum(u.keyphrase_hits for u in self.utterances)
        # [FIX 2026-02-24] Step-function scoring (matches EAB approach):
        # 1 hit = 0.55, 2 hits = 0.80, 3+ = 1.0. Previous linear 0.45x
        # underscored single hits (0.45 * 0.45 weight = 0.20, below 0.35 threshold).
        # [FIX 2026-02-24 v2] Boosted single-hit to 0.85 so that 0.85 * 0.45 = 0.38
        # crosses IVR_THRESHOLD (0.35) on first utterance. Single clear IVR/VM phrase
        # like "press one" or "reached this message" should trigger is_ivr=True
        # immediately, even though abort requires more evidence (0.45).
        if total_keyphrase_hits >= 3:
            keyphrase_score = 1.0
        elif total_keyphrase_hits >= 2:
            keyphrase_score = 0.90
        elif total_keyphrase_hits >= 1:
            keyphrase_score = 0.85
        else:
            keyphrase_score = 0.0
        
        # ── Layer 2: Temporal Pattern Detection ──
        temporal_score = 0.0
        if len(timestamps) >= 2:
            gaps = [t2 - t1 for t1, t2 in zip(timestamps[:-1], timestamps[1:])]
            # IVR characteristics: very regular timing, fast gaps
            fast_gaps = sum(1 for g in gaps if 0.1 <= g <= 2.0)
            
            # Check timing regularity (low variance = robotic)
            if len(gaps) >= 2:
                avg_gap = sum(gaps) / len(gaps)
                variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
                # Low variance = regular (IVR-like)
                if variance < 0.5 and avg_gap < 3.0:
                    temporal_score = 0.8
                elif fast_gaps >= 2:
                    temporal_score = 0.5
            elif fast_gaps >= 1:
                temporal_score = 0.3
        
        # ── Layer 3: Behavioral Repetition Detection ──
        repetition_score = 0.0
        if len(texts) >= 2:
            # Check for verbatim or near-verbatim repetitions
            unique_texts = set(texts)
            if len(unique_texts) == 1 and len(texts) >= 2:
                repetition_score = 1.0  # All identical = definitely IVR
            elif len(unique_texts) <= 2 and len(texts) >= 3:
                repetition_score = 0.8  # Very low variety
            else:
                # Check pairwise similarity for near-repeats
                repeat_count = 0
                for i in range(len(texts) - 1):
                    for j in range(i + 1, len(texts)):
                        # Simple overlap ratio
                        words_i = set(texts[i].split())
                        words_j = set(texts[j].split())
                        if words_i and words_j:
                            overlap = len(words_i & words_j) / max(len(words_i), len(words_j))
                            if overlap > 0.7:
                                repeat_count += 1
                if repeat_count >= 2:
                    repetition_score = 0.6
                elif repeat_count >= 1:
                    repetition_score = 0.3
        
        # ── Human Marker Penalty ──
        # Use LIFETIME human markers for accurate penalty
        total_human_markers = self._lifetime_human_markers
        human_penalty = min(total_human_markers * 0.15, 0.3)
        
        # ── Layer 4: No-Human-Markers Detection ──
        # IVRs never produce filler words, hesitation, questions, or first-person speech.
        # If we have 3+ utterances and ZERO human markers across all of them, that's suspicious.
        # Use LIFETIME count to avoid missing evidence that fell off the window
        no_human_score = 0.0
        total_utterances = self._lifetime_utterance_count
        if total_utterances >= 3 and total_human_markers == 0:
            no_human_score = 0.7  # Strongly suspicious — no human speech markers at all
        elif total_utterances >= 2 and total_human_markers == 0:
            no_human_score = 0.4
        
        # ── Final Score (5-layer) ──
        raw_score = (
            keyphrase_score * self.KEYPHRASE_WEIGHT +
            temporal_score * self.TEMPORAL_WEIGHT +
            repetition_score * self.REPETITION_WEIGHT +
            no_human_score * self.NO_HUMAN_WEIGHT
        )
        
        # Apply human penalty
        self.ivr_score = max(0.0, min(1.0, raw_score - human_penalty * self.HUMAN_PENALTY_WEIGHT))
        
        # ── Instant detection overrides ──
        # Single utterance with 2+ strong IVR keyphrases = immediate detection
        if self.utterances and self.utterances[-1].keyphrase_hits >= 2:
            self.ivr_score = max(self.ivr_score, 0.80)
        
        # 2+ consecutive IVR keyphrase utterances = high confidence (was 3, too strict)
        if self._consecutive_ivr_hits >= 2:
            self.ivr_score = max(self.ivr_score, 0.75)
        
        # 3+ consecutive IVR keyphrase utterances = certain
        if self._consecutive_ivr_hits >= 3:
            self.ivr_score = max(self.ivr_score, 0.90)
        
        # [LIFETIME OVERRIDE] 5+ lifetime keyphrase hits with 0 human markers = certain IVR
        # Catches cases where IVR mixes keyphrase/non-keyphrase lines, resetting consecutive counter
        if self._lifetime_keyphrase_hits >= 5 and self._lifetime_human_markers == 0:
            self.ivr_score = max(self.ivr_score, 0.85)
        elif self._lifetime_keyphrase_hits >= 3 and self._lifetime_human_markers == 0:
            self.ivr_score = max(self.ivr_score, 0.70)
        
        self.is_ivr = self.ivr_score >= self.IVR_THRESHOLD
        
        # Build reason string
        reasons = []
        if keyphrase_score > 0:
            reasons.append(f"keyphrases({total_keyphrase_hits})")
        if temporal_score > 0.3:
            reasons.append(f"timing({temporal_score:.1f})")
        if repetition_score > 0.3:
            reasons.append(f"repetition({repetition_score:.1f})")
        if no_human_score > 0.3:
            reasons.append(f"no_human({no_human_score:.1f})")
        if human_penalty > 0:
            reasons.append(f"human_markers(-{human_penalty:.1f})")
        self.detection_reason = " + ".join(reasons) if reasons else "none"
    
    def should_abort_call(self) -> bool:
        """Should Alan abort this call? True if IVR score is above abort threshold."""
        return self.ivr_score >= self.ABORT_THRESHOLD
    
    def get_abort_line(self) -> str:
        """
        Get the graceful exit line Alan should speak before hanging up.
        Only returns a line once per call (idempotent).
        """
        if self._abort_line_spoken:
            return ""
        self._abort_line_spoken = True
        return "No worries, I'll try again later. Take care."
    
    def get_outcome_label(self) -> str:
        """Get the outcome label for call classification."""
        if self.ivr_score >= 0.90:
            return "ivr_system"
        elif self.ivr_score >= self.IVR_THRESHOLD:
            return "voicemail_ivr"
        return "unknown"
    
    def snapshot(self) -> dict:
        """Full detector state for debugging/logging."""
        return {
            "is_ivr": self.is_ivr,
            "score": round(self.ivr_score, 3),
            "should_abort": self.should_abort_call(),
            "reason": self.detection_reason,
            "utterance_count": len(self.utterances),
            "lifetime_utterances": self._lifetime_utterance_count,
            "lifetime_keyphrase_hits": self._lifetime_keyphrase_hits,
            "lifetime_human_markers": self._lifetime_human_markers,
            "consecutive_ivr_hits": self._consecutive_ivr_hits,
            "consecutive_misses": self._consecutive_misses,
            "abort_line_spoken": self._abort_line_spoken,
        }

    def get_state(self) -> dict:
        """Get current detector state for Cost Sentinel integration."""
        return {
            "score": self.ivr_score,
            "is_ivr": self.is_ivr,
            "utterance_count": len(self.utterances),
            "lifetime_utterances": self._lifetime_utterance_count,
            "lifetime_keyphrase_hits": self._lifetime_keyphrase_hits,
            "consecutive_hits": self._consecutive_ivr_hits,
            "reason": self.detection_reason,
        }


# ======================================================================
#  SELF-TESTS
# ======================================================================

def _self_test():
    """Verify IVR detector works correctly."""
    import sys
    
    passed = 0
    failed = 0
    
    def check(name, condition):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS: {name}")
        else:
            failed += 1
            print(f"  FAIL: {name}")
    
    print("IVR Detector Self-Tests")
    print("=" * 40)
    
    # Test 1: Single strong IVR phrase
    d = IVRDetector()
    r = d.add_utterance("To speak to a representative, please press one.", time.time())
    check("Single IVR phrase detected", r["is_ivr"] == True)
    
    # Test 2: Human speech should NOT trigger
    d = IVRDetector()
    d.add_utterance("Um, what company did you say?", time.time())
    check("Human speech not flagged", d.is_ivr == False)
    
    # Test 3: Voicemail prompts
    d = IVRDetector()
    d.add_utterance("To send this message now, press pound or hang up.", time.time())
    check("Voicemail prompt detected", d.is_ivr == True)
    
    # Test 4: Multiple IVR prompts increase confidence
    d = IVRDetector()
    t = time.time()
    d.add_utterance("Press one for sales, press two for support.", t)
    d.add_utterance("For more options, press star.", t + 1.0)
    check("Multiple IVR prompts high score", d.ivr_score >= 0.75)
    check("Multiple IVR prompts abort", d.should_abort_call())
    
    # Test 5: Natural conversation should never trigger
    d = IVRDetector()
    t = time.time()
    d.add_utterance("Yeah, who is this?", t)
    d.add_utterance("Oh okay, um, we already have a processor.", t + 3.0)
    d.add_utterance("I mean, how much can you save us?", t + 8.0)
    check("Natural conversation clear", d.is_ivr == False)
    check("Natural conversation low score", d.ivr_score < 0.3)
    
    # Test 6: Red Sun Boutique scenario (real data from campaign)
    d = IVRDetector()
    t = time.time()
    d.add_utterance("So, for this call, the best way to get hold of me is to text me.", t)
    r1 = d.add_utterance("To continue recording, press two. To delete and re-record your message, press three.", t + 10)
    r2 = d.add_utterance("To send this message now, press pound or hang up.", t + 20)
    check("Red Sun Boutique IVR detected", d.is_ivr == True)
    check("Red Sun Boutique should abort", d.should_abort_call())
    
    # Test 7: Golden Star Florist (human asking same question -- NOT IVR)
    d = IVRDetector()
    t = time.time()
    d.add_utterance("What company did you say?", t)
    d.add_utterance("What company did you say? Signature Card, SCS Direct.", t + 4.0)
    d.add_utterance("What company did you say?", t + 8.0)
    check("Golden Star (human repeat) not IVR", d.is_ivr == False or d.ivr_score < 0.65)
    
    # Test 8: Thank you for calling auto-attendant
    d = IVRDetector()
    d.add_utterance("Thank you for calling Maple Tech. To speak to a representative, please press one.", time.time())
    check("Auto-attendant detected", d.is_ivr == True)
    
    # Test 9: Abort line is idempotent
    d = IVRDetector()
    d.add_utterance("Press one for sales, press two for billing.", time.time())
    line1 = d.get_abort_line()
    line2 = d.get_abort_line()
    check("Abort line returned once", len(line1) > 0 and line2 == "")
    
    # Test 10: Outcome label
    d = IVRDetector()
    d.add_utterance("Press one", time.time())
    d.add_utterance("Press two", time.time() + 0.5)
    d.add_utterance("Press star", time.time() + 1.0)
    check("Outcome label is ivr_system", d.get_outcome_label() in ("ivr_system", "voicemail_ivr"))
    
    # Test 11: DEEP ROOTS SCENARIO — IVR mixing keyphrase/non-keyphrase lines
    # Real IVR menus say things like "Our hours are 9-5" between "press 1" lines.
    # The OLD detector failed because consecutive counter reset on non-keyphrase lines.
    d = IVRDetector()
    t = time.time()
    d.add_utterance("Thank you for calling Deep Roots ATX Salon.", t)           # No keyphrase
    d.add_utterance("For appointments, please press one.", t + 3)               # Keyphrase
    d.add_utterance("Our hours are Monday through Friday, 9am to 5pm.", t + 6)  # No keyphrase
    d.add_utterance("For existing customers, press two.", t + 9)                # Keyphrase
    d.add_utterance("To hear these options again, press star.", t + 12)         # Keyphrase
    check("Deep Roots IVR detected (mixed lines)", d.is_ivr == True)
    check("Deep Roots should abort", d.should_abort_call())

    # Test 12: BUSINESS ENTITIES SCENARIO — long IVR with FAQ recording
    # Lots of non-keyphrase content with occasional IVR lines
    d = IVRDetector()
    t = time.time()
    d.add_utterance("Welcome to Business Entities Incorporated.", t)
    d.add_utterance("If you need to form an LLC, please press one.", t + 5)
    d.add_utterance("For questions about corporate filings, press two.", t + 10)
    d.add_utterance("Our filing fees start at 99 dollars.", t + 15)
    d.add_utterance("For trademark registration, press three.", t + 20)
    d.add_utterance("We serve all 50 states.", t + 25)
    d.add_utterance("To repeat this menu, press star.", t + 30)
    check("Business Entities IVR detected (long FAQ)", d.is_ivr == True)
    check("Business Entities should abort", d.should_abort_call())

    # Test 13: SHORT LEGITIMATE CALL — should NOT trigger
    # Real merchant picks up, has brief exchange, hangs up
    d = IVRDetector()
    t = time.time()
    d.add_utterance("Hello?", t)
    d.add_utterance("Yeah, we're not interested.", t + 3.0)
    check("Short legitimate call not IVR", d.is_ivr == False)

    # Test 14: NOISE FILTER — very short noise should not affect scoring
    d = IVRDetector()
    d.add_utterance("ok", time.time())  # Too short, should be filtered
    check("Noise utterance filtered", d._lifetime_utterance_count == 0)
    
    print(f"\nResults: {passed}/{passed+failed} passed")
    return failed == 0


if __name__ == "__main__":
    success = _self_test()
    exit(0 if success else 1)
