"""
Personality Engine — Probabilistic Personality Matrix + Algebraic Quantum Layer
================================================================================
Two-layer personality system for Alan:

Layer 1: QUANTUM STATE VECTOR (AQIPersonalityState)
  Alan's personality exists as a state vector |ψ⟩ in a 5-dimensional Hilbert
  space: [Wit, Empathy, Precision, Patience, Entropy]. Conversation events
  apply NON-COMMUTATIVE operators (matrices) that evolve the state. The ORDER
  of events matters — insult-then-apologize produces a different state than
  apologize-then-insult. The Born rule (|amplitude|²) collapses the state
  into trait probabilities that feed Layer 2.

  Why this matters: Standard personality systems are Markov — only the current
  state matters. The quantum layer encodes HISTORY in the state vector itself,
  because each operator application transforms the entire vector, and matrix
  multiplication is non-commutative. Alan is who he is because of what happened
  IN SEQUENCE, not just what happened.

Layer 2: PROBABILISTIC JITTER (PersonalityEngine)
  Takes the collapsed trait probabilities from Layer 1 and applies per-turn
  Gaussian jitter + reactive mood adjustment + relationship depth accrual.
  This produces the final persona classification, flare generation, system
  instruction crafting, and prosody bias.

Integration with existing AQI stack:
  - Complements QPC (strategy selection) — QPC decides WHAT to say,
    personality decides HOW to say it
  - Complements Continuum Engine (emotional fields) — Continuum tracks the
    MERCHANT's emotional state, personality tracks ALAN's personality state
  - Complements Fluidic Kernel (conversation modes) — Fluidic decides WHERE
    in the call we are, personality decides WHO Alan is right now
  - Feeds into Prosody Engine (Organ 7) via prosody_bias hints

Author: AQI System
Date: March 3, 2026
"""

import random
import time
import math
import logging
import numpy as np
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("PersonalityEngine")


# =============================================================================
# LAYER 1: ALGEBRAIC QUANTUM PERSONALITY STATE
# =============================================================================
# The state vector |ψ⟩ lives in ℂ⁵ (5 complex dimensions).
# Conversation events apply operator matrices M ∈ ℂ⁵ˣ⁵.
# Non-commutativity: M_praise · M_criticism ≠ M_criticism · M_praise
# Collapse via Born rule: P(trait_i) = |⟨i|ψ⟩|²
#
# The 5 dimensions correspond to personality traits:
#   [0] Wit       — humor, playfulness, irreverence
#   [1] Empathy   — emotional resonance, care, warmth
#   [2] Precision — data-driven, analytical, clinical
#   [3] Patience  — tolerance, measured responses, listening
#   [4] Entropy   — unpredictability, creative leaps, chaos
#
# Entropy is the "quantum" dimension — when it's high, Alan makes lateral
# leaps, creative analogies, and surprising turns. When it's low, he's
# systematic and predictable. A machine that is ALWAYS predictable feels
# like a database; one that occasionally surprises feels like a person.
# =============================================================================

# ─── CONVERSATION EVENT OPERATORS ─────────────────────────────────────────
# Each operator is a 5×5 real matrix (simplified from complex for numerical
# stability in production). These transform the state vector when specific
# conversation events are detected.
#
# Design principle: operators are NOT unitary (not norm-preserving).
# Real conversations aren't reversible — you can't un-say something.
# We re-normalize after each application to keep |ψ⟩ on the unit sphere.

# Merchant is warm/positive → boosts Wit, slightly reduces Precision
_OP_POSITIVE = np.array([
    [1.15, 0.05, 0.00, 0.00, 0.05],  # Wit boosted
    [0.05, 1.05, 0.00, 0.00, 0.00],  # Empathy slightly up
    [0.00, 0.00, 0.90, 0.00, 0.00],  # Precision slightly down
    [0.00, 0.00, 0.00, 1.00, 0.00],  # Patience stable
    [0.05, 0.00, 0.00, 0.00, 1.10],  # Entropy up (confidence → creativity)
], dtype=np.float64)

# Merchant is negative/frustrated → spikes Empathy, dampens Wit and Entropy
_OP_NEGATIVE = np.array([
    [0.75, 0.00, 0.05, 0.00, 0.00],  # Wit dampened
    [0.10, 1.30, 0.00, 0.05, 0.00],  # Empathy surges
    [0.00, 0.00, 1.05, 0.00, 0.00],  # Precision slightly up
    [0.00, 0.10, 0.00, 1.10, 0.00],  # Patience up (absorb the stress)
    [0.00, 0.00, 0.00, 0.00, 0.70],  # Entropy dampened (stay predictable)
], dtype=np.float64)

# Merchant asks a specific/technical question → boosts Precision
_OP_QUESTION = np.array([
    [0.95, 0.00, 0.05, 0.00, 0.00],  # Wit slightly down
    [0.00, 0.95, 0.00, 0.00, 0.00],  # Empathy slightly down
    [0.05, 0.05, 1.20, 0.00, 0.00],  # Precision boosted
    [0.00, 0.00, 0.00, 1.05, 0.00],  # Patience up (answering well)
    [0.00, 0.00, 0.00, 0.00, 0.90],  # Entropy down (be precise)
], dtype=np.float64)

# Merchant raises an objection → Patience + Empathy up, Entropy stabilized
_OP_OBJECTION = np.array([
    [0.85, 0.00, 0.00, 0.00, 0.00],  # Wit down (not the time for jokes)
    [0.05, 1.15, 0.00, 0.00, 0.00],  # Empathy up
    [0.00, 0.00, 1.05, 0.00, 0.00],  # Precision slightly up
    [0.10, 0.00, 0.00, 1.20, 0.00],  # Patience surges
    [0.00, 0.00, 0.00, 0.00, 0.80],  # Entropy down (be measured)
], dtype=np.float64)

# Merchant engages warmly / shows buying intent → Wit + Entropy up (reward)
_OP_ENGAGEMENT = np.array([
    [1.20, 0.00, 0.00, 0.00, 0.05],  # Wit boosted (ride the vibe)
    [0.00, 1.00, 0.00, 0.00, 0.00],  # Empathy stable
    [0.00, 0.00, 1.00, 0.00, 0.00],  # Precision stable
    [0.00, 0.00, 0.00, 0.95, 0.00],  # Patience slightly down (less needed)
    [0.10, 0.00, 0.00, 0.00, 1.15],  # Entropy up (confidence → creativity)
], dtype=np.float64)

# Silence / dead air / confusion → Patience + Precision up, everything else stabilizes
_OP_SILENCE = np.array([
    [0.90, 0.00, 0.00, 0.00, 0.00],  # Wit down
    [0.00, 1.00, 0.00, 0.00, 0.00],  # Empathy stable
    [0.00, 0.00, 1.10, 0.00, 0.00],  # Precision up (be clear)
    [0.00, 0.00, 0.00, 1.15, 0.00],  # Patience up
    [0.00, 0.00, 0.00, 0.00, 0.85],  # Entropy down (stay grounded)
], dtype=np.float64)

# Neutral turn / no strong signal → gentle regression toward baseline
_OP_NEUTRAL = np.array([
    [1.00, 0.01, 0.01, 0.01, 0.01],  # Very slight mixing
    [0.01, 1.00, 0.01, 0.01, 0.01],
    [0.01, 0.01, 1.00, 0.01, 0.01],
    [0.01, 0.01, 0.01, 1.00, 0.01],
    [0.01, 0.01, 0.01, 0.01, 1.00],
], dtype=np.float64)

# Map event names → operator matrices
_CONVERSATION_OPERATORS = {
    "positive": _OP_POSITIVE,
    "negative": _OP_NEGATIVE,
    "question": _OP_QUESTION,
    "objection": _OP_OBJECTION,
    "engagement": _OP_ENGAGEMENT,
    "silence": _OP_SILENCE,
    "neutral": _OP_NEUTRAL,
}


class AQIPersonalityState:
    """
    Algebraic Quantum Personality State — |ψ⟩ in ℝ⁵.

    The state vector evolves through non-commutative operator application.
    Each conversation event applies a specific operator matrix, and the
    ORDER of application matters. This encodes conversation history
    directly into the personality state.

    The Born rule analogue (|amplitude|²) collapses the state into trait
    probabilities used by the PersonalityEngine for final output generation.

    Dimensions:
      [0] Wit       — humor, playfulness
      [1] Empathy   — emotional resonance
      [2] Precision — data-driven, analytical
      [3] Patience  — tolerance, measured
      [4] Entropy   — unpredictability, creativity
    """

    DIMENSION_NAMES = ["wit", "empathy", "precision", "patience", "entropy"]

    def __init__(self, initial_state: np.ndarray = None):
        """
        Initialize the quantum personality state.

        Default initial state: balanced across all dimensions with a slight
        bias toward Precision and Patience (Alan's professional baseline).
        """
        if initial_state is not None:
            self.state = np.array(initial_state, dtype=np.float64)
        else:
            # Baseline: professional, patient, moderate wit, moderate empathy, low chaos
            self.state = np.array([0.40, 0.45, 0.55, 0.50, 0.25], dtype=np.float64)

        self._normalize()

        # Track operator history for non-commutativity verification
        self._operator_history: List[str] = []
        self._evolution_count = 0

    def _normalize(self):
        """Normalize state vector to unit sphere (Born rule requirement)."""
        norm = np.linalg.norm(self.state)
        if norm > 1e-10:
            self.state = self.state / norm
        else:
            # Degenerate state — reset to balanced
            self.state = np.ones(5, dtype=np.float64) / np.sqrt(5)

    def apply_operator(self, event_name: str, custom_operator: np.ndarray = None):
        """
        Evolve the state by applying a conversation event operator.

        Non-commutativity: apply_operator("positive") then apply_operator("negative")
        produces a DIFFERENT final state than the reverse order. This is the
        key insight — Alan's personality is path-dependent, not state-dependent.

        Args:
            event_name: Key into _CONVERSATION_OPERATORS
            custom_operator: Optional custom 5×5 matrix (overrides event_name)
        """
        if custom_operator is not None:
            operator = np.array(custom_operator, dtype=np.float64)
        else:
            operator = _CONVERSATION_OPERATORS.get(event_name, _OP_NEUTRAL)

        # Matrix-vector multiplication: |ψ'⟩ = M|ψ⟩
        self.state = operator @ self.state
        self._normalize()

        self._operator_history.append(event_name)
        self._evolution_count += 1

        # Keep history bounded (last 50 events)
        if len(self._operator_history) > 50:
            self._operator_history = self._operator_history[-50:]

    def collapse(self) -> Dict[str, float]:
        """
        Collapse the state vector into trait probabilities via Born rule.

        Returns dict of trait_name → probability (sums to 1.0).
        This is the "measurement" — the quantum state becomes classical
        trait weights for the PersonalityEngine to consume.
        """
        # Born rule: P(i) = |ψ_i|²
        probabilities = np.abs(self.state) ** 2
        total = probabilities.sum()
        if total > 1e-10:
            probabilities = probabilities / total
        else:
            probabilities = np.ones(5) / 5.0

        return {
            name: float(prob)
            for name, prob in zip(self.DIMENSION_NAMES, probabilities)
        }

    def get_dominant_trait(self) -> Tuple[str, float]:
        """Get the trait with highest probability after collapse."""
        collapsed = self.collapse()
        dominant = max(collapsed.items(), key=lambda x: x[1])
        return dominant

    def get_entropy_level(self) -> float:
        """
        Get the Shannon entropy of the trait distribution.

        High entropy = balanced distribution = Alan is versatile, unpredictable.
        Low entropy = one trait dominates = Alan is focused, predictable.

        Max entropy for 5 dimensions = ln(5) ≈ 1.609
        """
        probs = np.abs(self.state) ** 2
        total = probs.sum()
        if total < 1e-10:
            return 0.0
        probs = probs / total
        # Shannon entropy: H = -Σ p_i * ln(p_i)
        entropy = 0.0
        for p in probs:
            if p > 1e-10:
                entropy -= p * np.log(p)
        return float(entropy)

    def get_complexity_index(self) -> float:
        """
        Compute a complexity index — weighted sum of trait probabilities.

        Higher = more complex personality expression.
        Range: 1.0 (pure Wit) to 5.0 (pure Entropy).
        """
        probs = np.abs(self.state) ** 2
        total = probs.sum()
        if total < 1e-10:
            return 3.0
        probs = probs / total
        weights = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        return float(np.dot(probs, weights))

    def export_state(self) -> Dict[str, Any]:
        """Export for persistence (MIP cross-call storage)."""
        return {
            "state_vector": self.state.tolist(),
            "evolution_count": self._evolution_count,
            "operator_history_last10": self._operator_history[-10:],
        }

    def restore_state(self, data: Dict[str, Any]):
        """Restore from persistence (partial — decay toward baseline)."""
        if "state_vector" in data:
            restored = np.array(data["state_vector"], dtype=np.float64)
            baseline = np.array([0.40, 0.45, 0.55, 0.50, 0.25], dtype=np.float64)
            baseline /= np.linalg.norm(baseline)
            # 60% carry-over, 40% regression toward baseline
            self.state = 0.6 * restored + 0.4 * baseline
            self._normalize()
        if "evolution_count" in data:
            self._evolution_count = data["evolution_count"]

    def __repr__(self):
        collapsed = self.collapse()
        dominant, prob = self.get_dominant_trait()
        return (
            f"AQIPersonalityState(dominant={dominant}@{prob:.2f}, "
            f"entropy={self.get_entropy_level():.3f}, "
            f"evolutions={self._evolution_count})"
        )


# ─── EVENT DETECTION ─────────────────────────────────────────────────────────
# Classifies a conversation turn into an operator event for the quantum layer.
# This bridges between the text-level analysis and the algebraic evolution.

def detect_conversation_event(sentiment: str, user_text: str,
                              analysis: Dict[str, Any] = None) -> str:
    """
    Detect what type of conversation event this turn represents.

    Reads sentiment, word patterns, and analysis flags to classify
    the event for operator selection.

    Returns: event_name key from _CONVERSATION_OPERATORS
    """
    text_lower = (user_text or "").lower().strip()
    analysis = analysis or {}

    # Objection detection (highest priority — these need careful handling)
    objection_signals = [
        "too expensive", "not interested", "already have", "don't need",
        "waste of time", "no thanks", "pass", "we're good", "happy with",
        "can't afford", "budget", "competitor", "why should",
    ]
    if any(sig in text_lower for sig in objection_signals):
        return "objection"

    # Silence / confusion detection
    if len(text_lower) < 3 or text_lower in ("", "huh", "what", "um", "uh"):
        return "silence"

    # Question detection
    question_signals = ["?", "how much", "how does", "what is", "can you",
                        "tell me", "explain", "what's the", "how do"]
    if any(sig in text_lower for sig in question_signals):
        return "question"

    # Engagement detection (buying intent, interest signals)
    engagement_signals = [
        "sounds good", "interesting", "tell me more", "that's great",
        "let's do it", "sign me up", "how do we start", "I like",
        "makes sense", "you're right", "good point", "exactly",
    ]
    if any(sig in text_lower for sig in engagement_signals):
        return "engagement"

    # Sentiment-based classification
    sentiment_lower = (sentiment or "").lower()
    if sentiment_lower in ("positive", "warm", "friendly", "excited"):
        return "positive"
    elif sentiment_lower in ("negative", "frustrated", "angry", "cold", "hostile"):
        return "negative"

    # Default: neutral
    return "neutral"


# ─── FLARE POOLS ─────────────────────────────────────────────────────────────
# Categorized by mood/trait blend. Each pool targets a different "vibe."
# The engine selects from the pool that matches Alan's current state vector.
# These are human touches — tiny asides that break the AI pattern.

_FLARE_POOLS = {
    # High wit + high mood → playful confidence
    "playful": [
        "You know how these things go, right?",
        "I mean, I don't want to brag, but the math speaks for itself.",
        "Honestly, I get excited about this stuff, which probably makes me weird.",
        "Not gonna lie, this is the fun part of my day.",
        "I know, I know — another guy calling about processing. But hear me out.",
        "Look, I'd rather be honest than smooth.",
    ],
    # High empathy + low mood → warm and grounding
    "empathetic": [
        "I hear you. Running a business is no joke.",
        "Look, I'm not here to add to your plate.",
        "Honestly, I just want to make sure you're not overpaying.",
        "No pressure at all — I'd rather you feel good about it.",
        "I've talked to a lot of folks in your shoes. You're not alone in this.",
        "Take your time — I'm not going anywhere.",
    ],
    # High analytical + neutral mood → precise and credible
    "analytical": [
        "The numbers don't really lie on this one.",
        "I can break that down pretty specifically if you want.",
        "That's actually a really sharp question.",
        "So here's what the data actually shows...",
        "Let me give you the real math, not the brochure version.",
    ],
    # Low brevity (elaborate) → conversational depth
    "conversational": [
        "Actually, that reminds me of something I was looking at earlier.",
        "Here's the thing nobody tells you about this...",
        "I was just talking to someone about this exact situation.",
        "You know what's interesting about that?",
        "So this is where it gets kind of cool, actually.",
    ],
    # High brevity → punchy
    "punchy": [
        "Bottom line?",
        "Real talk.",
        "Here's the move.",
        "Straight up.",
        "Quick math.",
    ],
}

# ─── SYSTEM INSTRUCTION TEMPLATES ────────────────────────────────────────────
# These are injected into the system prompt to shape the LLM's behavior.
# Selected based on the personality state vector.

_INSTRUCTION_TEMPLATES = {
    "playful": (
        "Your current tone is playful and slightly irreverent — like someone "
        "who genuinely enjoys what they do. You can make a light quip or aside "
        "if the moment calls for it. Don't force it. Be yourself."
    ),
    "empathetic": (
        "Your current tone is warm and steady. The person you're talking to "
        "may be stressed or uncertain. Be genuine — not performative. "
        "Listen more than you speak. When you do speak, be grounding."
    ),
    "analytical": (
        "Your current tone is precise and data-driven. Lead with specifics "
        "and credibility. Be the expert in the room — not condescending, but "
        "clearly knowledgeable. Numbers over feelings."
    ),
    "conversational": (
        "Your current tone is relaxed and exploratory. You're having a real "
        "conversation, not delivering a pitch. Let it breathe. Ask follow-ups. "
        "Be the kind of person people want to keep talking to."
    ),
    "punchy": (
        "Your current tone is direct and efficient. The person values their "
        "time and you respect that. Get to the point. Every word earns its place. "
        "No filler, no padding."
    ),
    "neutral": (
        "Your current tone is balanced and professional — a seasoned sales rep "
        "on the phone. Confident but not pushy. Natural and unhurried."
    ),
}


class PersonalityEngine:
    """
    Probabilistic Personality Matrix — Alan's dynamic soul.

    Unlike the old PersonalitymatrixCore (4 static traits, 3 hardcoded flares),
    this engine produces genuinely varied behavior through:
      - Stochastic jitter on 5 core traits per turn
      - Reactive mood adjustment based on merchant sentiment
      - Gradual relationship depth accumulation
      - Session-persistent state (mood doesn't reset per turn)
      - Context-aware flare generation from categorized pools
      - System instruction crafting for LLM persona shaping

    Thread Safety: This class is instantiated once per call (via agent).
    No shared mutable state across calls.
    """

    # ─── TRAIT BOUNDS ─────────────────────────────────────────────────────
    TRAIT_MIN = 0.0
    TRAIT_MAX = 1.0

    # ─── JITTER VARIANCE ─────────────────────────────────────────────────
    # How much each trait can fluctuate per turn. Higher = more unpredictable.
    # Calibrated to produce noticeable but not jarring variation.
    DEFAULT_JITTER = 0.12  # ±12% per turn

    # ─── MOOD MOMENTUM ───────────────────────────────────────────────────
    # How quickly mood responds to sentiment. Lower = more inertia.
    # At 0.15, it takes ~5-6 consistently positive turns to go from 0.5→0.8.
    MOOD_GAIN = 0.12   # positive sentiment push
    MOOD_DECAY = 0.08  # negative sentiment pull (slower — negativity is "stickier")
    MOOD_REVERT = 0.03 # neutral sentiment slowly reverts toward 0.5

    # ─── EMPATHY SURGE ────────────────────────────────────────────────────
    # When merchant sentiment is strongly negative, empathy spikes
    # (humans naturally lean in when someone is struggling).
    EMPATHY_SURGE = 0.15

    # ─── RELATIONSHIP DEPTH ACCRUAL ──────────────────────────────────────
    # Each turn where the merchant engages adds to relationship depth.
    # This models the natural warming of a conversation over time.
    DEPTH_PER_TURN = 0.04  # ~25 turns to reach full depth
    DEPTH_EMPATHY_BOOST = 0.06  # extra depth when empathy moments happen

    # ─── FLARE PROBABILITY ────────────────────────────────────────────────
    # Base probability of generating a flare. Modified by wit + mood.
    FLARE_BASE_PROB = 0.25  # 25% baseline

    # ─── RECENT FLARE TRACKING ────────────────────────────────────────────
    MAX_RECENT_FLARES = 4  # Don't repeat from last N flares

    def __init__(self):
        """Initialize with baseline personality traits."""
        # ─── CORE TRAITS ──────────────────────────────────────────────────
        # These are Alan's "resting" personality. Jitter shifts them per-turn.
        self.traits = {
            "wit": 0.35,          # Propensity for humor/asides (low default — earn it)
            "analytical": 0.75,   # Data-driven vs feeling-driven
            "empathy": 0.50,      # Emotional resonance with merchant
            "brevity": 0.45,      # Short vs elaborate (slightly elaborate default)
            "patience": 0.80,     # Tolerance for hesitation/repetition
        }

        # ─── VOLATILE STATE ───────────────────────────────────────────────
        # These change within a call. Persist across turns, reset per call.
        self.mood_score = 0.50      # 0.0 (cold) ↔ 1.0 (warm/energetic)
        self.relationship_depth = 0.0  # 0.0 (stranger) ↔ 1.0 (trusted)
        self.turns_processed = 0
        self.consecutive_positive = 0
        self.consecutive_negative = 0

        # ─── ANTI-REPETITION ──────────────────────────────────────────────
        self._recent_flares: List[str] = []
        self._last_persona_key = ""

        # ─── TIMESTAMPS ──────────────────────────────────────────────────
        self._created_at = time.time()
        self._last_update = time.time()

        # ─── QUANTUM STATE VECTOR ─────────────────────────────────────────
        # Layer 1: Algebraic personality evolution via non-commutative operators
        self.quantum_state = AQIPersonalityState()

        logger.info("[PERSONALITY] Engine initialized — 5 traits, quantum layer active, probabilistic matrix online")

    # ─── JITTER ───────────────────────────────────────────────────────────

    def _apply_jitter(self, value: float, variance: float = None) -> float:
        """
        Apply quantum jitter to a trait value.

        Uses a normal distribution (not uniform) so extreme jitter is rare.
        This produces a bell-curve of personality variation — usually close
        to the base trait, occasionally noticeably different.

        Args:
            value: Current trait value (0.0 to 1.0)
            variance: Standard deviation of jitter. Default: DEFAULT_JITTER

        Returns:
            Jittered value, clamped to [0.0, 1.0]
        """
        if variance is None:
            variance = self.DEFAULT_JITTER

        # Gaussian jitter — clamp to bounds
        jitter = random.gauss(0, variance)
        result = value + jitter
        return max(self.TRAIT_MIN, min(self.TRAIT_MAX, result))

    # ─── STATE SNAPSHOT ───────────────────────────────────────────────────

    def get_state_vector(self) -> Dict[str, float]:
        """
        Generate the current personality state with per-turn jitter applied.

        This is the "snapshot" — what Alan IS right now, not what his
        baseline traits are. Called once per turn before LLM generation.

        Returns:
            Dict of trait_name → jittered_value for this turn
        """
        state = {}
        for trait_name, base_value in self.traits.items():
            state[trait_name] = self._apply_jitter(base_value)

        # Mood bleed-through: high mood slightly boosts wit and lowers brevity
        # (happy people talk more and joke more)
        if self.mood_score > 0.7:
            state["wit"] = min(1.0, state["wit"] + 0.08)
            state["brevity"] = max(0.0, state["brevity"] - 0.05)
        elif self.mood_score < 0.3:
            state["wit"] = max(0.0, state["wit"] - 0.10)
            state["empathy"] = min(1.0, state["empathy"] + 0.10)

        # Relationship depth bleed-through: deeper relationship → more wit allowed
        if self.relationship_depth > 0.5:
            state["wit"] = min(1.0, state["wit"] + self.relationship_depth * 0.15)

        return state

    # ─── REACTIVE SENTIMENT UPDATE ────────────────────────────────────────

    def react_to_sentiment(self, sentiment: str, sentiment_score: float = None,
                           user_word_count: int = 0) -> None:
        """
        Update Alan's internal state based on merchant sentiment.

        This is the REACTIVE loop — the merchant's emotional valence
        shifts Alan's mood, empathy, and wit. The shift is gradual and
        momentum-based (sustained signals move faster than single turns).

        Args:
            sentiment: 'positive', 'neutral', or 'negative'
            sentiment_score: Optional numeric score (0.0 to 1.0, or -1 to 1)
            user_word_count: How many words the merchant said (engagement signal)
        """
        self.turns_processed += 1
        self._last_update = time.time()

        # ─── MOOD UPDATE ─────────────────────────────────────────────
        if sentiment == 'positive':
            self.consecutive_positive += 1
            self.consecutive_negative = 0
            # Momentum: consecutive positive turns accelerate the shift
            momentum = min(1.0 + self.consecutive_positive * 0.1, 1.5)
            self.mood_score = min(1.0, self.mood_score + self.MOOD_GAIN * momentum)

        elif sentiment == 'negative':
            self.consecutive_negative += 1
            self.consecutive_positive = 0
            momentum = min(1.0 + self.consecutive_negative * 0.1, 1.5)
            self.mood_score = max(0.0, self.mood_score - self.MOOD_DECAY * momentum)
            # Empathy surge — negative sentiment spikes empathy
            self.traits["empathy"] = min(1.0, self.traits["empathy"] + self.EMPATHY_SURGE)
            # Wit dampening — don't joke when they're struggling
            self.traits["wit"] = max(0.1, self.traits["wit"] - 0.08)

        else:
            # Neutral: gradual revert toward center (0.5)
            self.consecutive_positive = 0
            self.consecutive_negative = 0
            if self.mood_score > 0.55:
                self.mood_score -= self.MOOD_REVERT
            elif self.mood_score < 0.45:
                self.mood_score += self.MOOD_REVERT

        # ─── RELATIONSHIP DEPTH ──────────────────────────────────────
        # Every turn deepens the relationship slightly. Longer responses
        # (higher word count) indicate more engagement → faster depth.
        engagement_bonus = 0.02 if user_word_count > 15 else 0.0
        self.relationship_depth = min(1.0,
            self.relationship_depth + self.DEPTH_PER_TURN + engagement_bonus)

        # Empathy moments (negative sentiment) build depth faster
        if sentiment == 'negative':
            self.relationship_depth = min(1.0,
                self.relationship_depth + self.DEPTH_EMPATHY_BOOST)

        # ─── GRADUAL WIT RECOVERY ────────────────────────────────────
        # If wit was dampened by negative sentiment, it slowly recovers
        # toward baseline when sentiment is non-negative.
        if sentiment != 'negative' and self.traits["wit"] < 0.35:
            self.traits["wit"] = min(0.35, self.traits["wit"] + 0.02)

        logger.debug(
            f"[PERSONALITY] Turn {self.turns_processed}: "
            f"mood={self.mood_score:.2f}, empathy={self.traits['empathy']:.2f}, "
            f"wit={self.traits['wit']:.2f}, depth={self.relationship_depth:.2f}"
        )

    # ─── PERSONA CLASSIFICATION ───────────────────────────────────────────

    def _classify_persona(self, state: Dict[str, float]) -> str:
        """
        Classify the current state vector into a persona key.

        Priority order (first match wins):
          1. High wit + high mood → "playful"
          2. High empathy + low mood → "empathetic"
          3. High analytical → "analytical"
          4. High brevity → "punchy"
          5. Low brevity → "conversational"
          6. Default → "neutral"
        """
        wit = state.get("wit", 0.5)
        empathy = state.get("empathy", 0.5)
        analytical = state.get("analytical", 0.5)
        brevity = state.get("brevity", 0.5)

        if wit > 0.6 and self.mood_score > 0.6:
            return "playful"
        if empathy > 0.65 and self.mood_score < 0.4:
            return "empathetic"
        if analytical > 0.75:
            return "analytical"
        if brevity > 0.7:
            return "punchy"
        if brevity < 0.3:
            return "conversational"
        return "neutral"

    # ─── FLARE GENERATION ─────────────────────────────────────────────────

    def generate_flare(self, state: Dict[str, float] = None) -> str:
        """
        Generate a contextual personality flare (human aside).

        The probability of generating a flare depends on:
          - Current wit level (higher wit → more likely)
          - Mood score (happier → more likely)
          - Relationship depth (deeper → more likely)
          - Anti-repetition (won't repeat recent flares)

        Returns:
            A flare string, or empty string if no flare this turn.
        """
        if state is None:
            state = self.get_state_vector()

        persona = self._classify_persona(state)

        # Calculate flare probability
        wit = state.get("wit", 0.5)
        prob = self.FLARE_BASE_PROB
        prob += (wit - 0.5) * 0.3          # Wit boost: ±15%
        prob += (self.mood_score - 0.5) * 0.2  # Mood boost: ±10%
        prob += self.relationship_depth * 0.1   # Depth boost: up to +10%
        prob = max(0.05, min(0.60, prob))   # Clamp: 5% to 60%

        # Empathetic persona should rarely flare (not the time for quips)
        if persona == "empathetic":
            prob *= 0.4

        # Roll the dice
        if random.random() > prob:
            return ""

        # Select from the matching pool
        pool = _FLARE_POOLS.get(persona, _FLARE_POOLS["conversational"])

        # Anti-repetition filter
        available = [f for f in pool if f not in self._recent_flares]
        if not available:
            self._recent_flares.clear()
            available = pool

        flare = random.choice(available)

        # Track recent flares
        self._recent_flares.append(flare)
        if len(self._recent_flares) > self.MAX_RECENT_FLARES:
            self._recent_flares.pop(0)

        self._last_persona_key = persona
        return flare

    # ─── SYSTEM INSTRUCTION ──────────────────────────────────────────────

    def craft_system_instruction(self, state: Dict[str, float] = None) -> str:
        """
        Generate a dynamic system instruction for the LLM.

        This is the bridge between the personality matrix and the LLM's
        behavior. It tells the model WHO Alan is right now — not forever,
        just for the next 30 seconds.

        Returns:
            Natural language instruction string for system prompt injection.
        """
        if state is None:
            state = self.get_state_vector()

        persona = self._classify_persona(state)
        base_instruction = _INSTRUCTION_TEMPLATES.get(persona, _INSTRUCTION_TEMPLATES["neutral"])

        # Add mood modifier
        if self.mood_score > 0.75:
            mood_mod = " You're feeling good — let that warmth come through naturally."
        elif self.mood_score < 0.25:
            mood_mod = " Stay measured and steady. Don't force brightness you don't feel."
        else:
            mood_mod = ""

        # Add relationship depth modifier
        if self.relationship_depth > 0.6:
            depth_mod = " You know this person a bit now. Talk like it."
        elif self.relationship_depth > 0.3:
            depth_mod = " You're getting a feel for each other. Let gravity do the work."
        else:
            depth_mod = ""

        # Add patience modifier (affects how Alan handles repeated questions)
        patience = state.get("patience", 0.8)
        if patience < 0.4:
            patience_mod = " Be efficient — you've been patient, now be direct."
        else:
            patience_mod = ""

        instruction = base_instruction + mood_mod + depth_mod + patience_mod

        return instruction

    # ─── PROSODY MODULATION ──────────────────────────────────────────────

    def get_prosody_bias(self, state: Dict[str, float] = None) -> Dict[str, Any]:
        """
        Generate prosody bias hints for the existing prosody engine.

        This doesn't REPLACE detect_prosody_intent() — it provides
        optional bias weights that can influence intent selection when
        multiple intents are valid.

        Returns:
            Dict with:
              - 'preferred_intent': suggested prosody intent (or None)
              - 'speed_mod': speed modifier (-0.1 to +0.1)
              - 'silence_mod': inter-sentence silence modifier (frames, -3 to +3)
        """
        if state is None:
            state = self.get_state_vector()

        persona = self._classify_persona(state)

        # Map persona → preferred prosody intent
        persona_prosody = {
            "playful": "casual_rapport",
            "empathetic": "empathetic_reflect",
            "analytical": "confident_recommend",
            "conversational": "neutral",
            "punchy": "neutral",
            "neutral": "neutral",
        }

        # Speed modulation: high brevity → slightly faster
        brevity = state.get("brevity", 0.5)
        speed_mod = (brevity - 0.5) * 0.15  # ±7.5%

        # Silence modulation: high empathy → longer pauses
        empathy = state.get("empathy", 0.5)
        silence_mod = int((empathy - 0.5) * 6)  # ±3 frames (±60ms)

        return {
            "preferred_intent": persona_prosody.get(persona),
            "speed_mod": round(speed_mod, 3),
            "silence_mod": silence_mod,
        }

    # ─── FULL PER-TURN UPDATE ─────────────────────────────────────────────

    def process_turn(self, sentiment: str, user_text: str = "",
                     analysis: dict = None) -> Dict[str, Any]:
        """
        Complete per-turn personality processing.

        This is the main entry point called by the relay server pipeline.
        Performs reactive update → state snapshot → classify → generate outputs.

        Args:
            sentiment: 'positive', 'neutral', or 'negative'
            user_text: What the merchant said (for word count)
            analysis: Full analysis dict from the analysis layer

        Returns:
            Dict with all outputs for the relay server to consume:
              - 'state': current state vector (trait values)
              - 'persona': classified persona key ('playful', 'empathetic', etc.)
              - 'mood_score': current mood (0.0 to 1.0)
              - 'relationship_depth': depth (0.0 to 1.0)
              - 'flare': personality flare string (may be empty)
              - 'system_instruction': LLM system prompt injection
              - 'prosody_bias': hints for prosody engine
        """
        # 1. React to merchant sentiment (Layer 2 — mood engine)
        word_count = len(user_text.split()) if user_text else 0
        self.react_to_sentiment(sentiment, user_word_count=word_count)

        # 2. QUANTUM EVOLUTION (Layer 1 — non-commutative operator application)
        #    Detect what kind of conversation event this turn represents,
        #    then evolve the quantum state vector through operator multiplication.
        #    The ORDER of these operators over the call history produces a
        #    unique personality state — Alan is shaped by the sequence of events.
        event = detect_conversation_event(sentiment, user_text, analysis)
        self.quantum_state.apply_operator(event)
        quantum_collapsed = self.quantum_state.collapse()

        # 3. Get jittered state snapshot (Layer 2 — probabilistic jitter)
        jitter_state = self.get_state_vector()

        # 4. BLEND: Quantum-modulated personality state
        #    The quantum layer provides directional bias (which traits dominate),
        #    the jitter layer provides per-turn variability.
        #    Blend: 40% quantum collapse + 60% jitter state
        #    This lets the quantum history STEER without OVERRIDING the jitter.
        state = {}
        quantum_weight = 0.40
        jitter_weight = 0.60
        for trait_name in self.traits:
            q_val = quantum_collapsed.get(trait_name, 0.2)
            j_val = jitter_state.get(trait_name, 0.5)
            state[trait_name] = q_val * quantum_weight + j_val * jitter_weight
        # Clamp to bounds
        state = {k: max(0.0, min(1.0, v)) for k, v in state.items()}

        # 5. Classify persona from blended state
        persona = self._classify_persona(state)

        # 6. Generate outputs
        flare = self.generate_flare(state)
        instruction = self.craft_system_instruction(state)
        prosody_bias = self.get_prosody_bias(state)

        # Quantum diagnostics for logging
        dominant_trait, dominant_prob = self.quantum_state.get_dominant_trait()
        q_entropy = self.quantum_state.get_entropy_level()

        result = {
            "state": state,
            "persona": persona,
            "mood_score": round(self.mood_score, 3),
            "relationship_depth": round(self.relationship_depth, 3),
            "flare": flare,
            "system_instruction": instruction,
            "prosody_bias": prosody_bias,
            "turns_processed": self.turns_processed,
            # Quantum layer diagnostics (consumed by prompt builder & logging)
            "quantum_event": event,
            "quantum_dominant": dominant_trait,
            "quantum_dominant_prob": round(dominant_prob, 3),
            "quantum_entropy": round(q_entropy, 3),
            "quantum_evolutions": self.quantum_state._evolution_count,
        }

        logger.info(
            f"[PERSONALITY] Turn {self.turns_processed}: persona={persona}, "
            f"mood={self.mood_score:.2f}, depth={self.relationship_depth:.2f}, "
            f"flare={'YES' if flare else 'no'} | "
            f"quantum: event={event}, dominant={dominant_trait}@{dominant_prob:.2f}, "
            f"entropy={q_entropy:.3f}"
        )

        return result

    # ─── MIP INTEGRATION ─────────────────────────────────────────────────

    def export_for_persistence(self) -> Dict[str, Any]:
        """
        Export personality state for MIP cross-call storage.

        Called at call end by MIP's update_profile_from_call().
        The personality engine's session state becomes part of the
        merchant profile, so Alan "remembers the vibe" next call.
        """
        return {
            "mood_score": round(self.mood_score, 3),
            "relationship_depth": round(self.relationship_depth, 3),
            "empathy": round(self.traits["empathy"], 3),
            "wit": round(self.traits["wit"], 3),
            "patience": round(self.traits["patience"], 3),
            "turns_processed": self.turns_processed,
            "timestamp": time.time(),
            # Quantum state persistence — the full state vector
            "quantum_state": self.quantum_state.export_state(),
        }

    def restore_from_persistence(self, persisted: Dict[str, Any]) -> None:
        """
        Restore personality state from MIP cross-call storage.

        Called at call start when a merchant has a prior profile.
        Applies partial restoration — not a full clone. The vibe
        carries over but doesn't lock Alan into the past.

        Restoration weights:
          - mood_score: 50% (half-carry — start neutral-ish but biased)
          - relationship_depth: 80% (relationships persist strongly)
          - empathy/wit/patience: 70% (traits carry with some reset)
        """
        if not persisted:
            return

        # Partial restoration — don't lock into past exactly
        if "mood_score" in persisted:
            self.mood_score = 0.5 * 0.5 + persisted["mood_score"] * 0.5
        if "relationship_depth" in persisted:
            self.relationship_depth = persisted["relationship_depth"] * 0.8
        if "empathy" in persisted:
            self.traits["empathy"] = self.traits["empathy"] * 0.3 + persisted["empathy"] * 0.7
        if "wit" in persisted:
            self.traits["wit"] = self.traits["wit"] * 0.3 + persisted["wit"] * 0.7
        if "patience" in persisted:
            self.traits["patience"] = self.traits["patience"] * 0.3 + persisted["patience"] * 0.7

        # Restore quantum state (60% carry, 40% baseline regression)
        if "quantum_state" in persisted:
            self.quantum_state.restore_state(persisted["quantum_state"])

        logger.info(
            f"[PERSONALITY] Restored from MIP: mood={self.mood_score:.2f}, "
            f"depth={self.relationship_depth:.2f}, "
            f"empathy={self.traits['empathy']:.2f}, wit={self.traits['wit']:.2f}"
        )

    # ─── BACKWARD COMPAT — drop-in for old PersonalitymatrixCore ──────────

    def adjust_vibe(self, sentiment_score: float, interaction_history: list) -> None:
        """
        Backward-compatible method matching old PersonalitymatrixCore API.
        Maps numeric sentiment score → string → full reactive update.
        """
        if sentiment_score > 0.65:
            sentiment = 'positive'
        elif sentiment_score < 0.35:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        # Extract last user text for word count
        user_text = ""
        if interaction_history:
            last = interaction_history[-1]
            if isinstance(last, dict):
                user_text = last.get('user', '') or last.get('content', '') or ''
            elif isinstance(last, str):
                user_text = last

        word_count = len(user_text.split()) if user_text else 0
        self.react_to_sentiment(sentiment, user_word_count=word_count)

    # ─── REPRESENTATION ──────────────────────────────────────────────────

    def __repr__(self):
        return (
            f"PersonalityEngine(mood={self.mood_score:.2f}, "
            f"depth={self.relationship_depth:.2f}, "
            f"turns={self.turns_processed}, "
            f"traits={{{', '.join(f'{k}={v:.2f}' for k, v in self.traits.items())}}})"
        )
