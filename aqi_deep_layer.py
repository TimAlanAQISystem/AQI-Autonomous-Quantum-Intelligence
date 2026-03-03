"""
aqi_deep_layer.py — Live Integration of QPC, Fluidic, and Continuum Engines

This module wires the three theoretical frameworks into the production
conversation pipeline. Each framework serves a specific, measurable purpose:

  QPC Kernel    → Response strategy decisions (multi-hypothesis, measure, collapse)
  Fluidic Kernel → Conversation mode transitions (smooth, physics-based, no whiplash)
  Continuum Engine → Continuous emotional/ethical context signal into LLM prompt

The DeepLayer is instantiated per-session and stepped every conversation turn.
It reads from the existing analysis/context and WRITES back into context so
the existing build_llm_prompt pipeline picks up its signals automatically.

Author: AQI Deep Integration
Date: February 14, 2026
"""

import logging
import time
import numpy as np
from typing import Dict, Any, Optional, Tuple

# Import the three frameworks
from qpc_kernel import (
    QPCKernel, AgentProfile, SurfaceDescriptor,
    Branch, Superposition, BranchState, RiskMode
)
from continuum_engine import ContinuumRelationalLayer, Field

logger = logging.getLogger("AQI_DEEP_LAYER")


# =============================================================================
# FLUIDIC KERNEL — Inlined and adapted for telephony conversation modes
# =============================================================================
# The original fluidic_kernel.py had 7 world-states for general AI work.
# For live phone calls, Alan operates in 5 conversation modes that map to
# real sales call phases. The physics (inertia, viscosity, smoothing) is
# the same — but the states are what actually happen on the phone.

class ConversationMode:
    """A conversation mode with fluidic transition properties."""
    def __init__(self, name, description, allowed_intents, inertia=0.3,
                 llm_guidance="", max_tokens=100, temperature=0.7):
        self.name = name
        self.description = description
        self.allowed_intents = allowed_intents
        self.inertia = inertia  # Resistance to leaving this mode
        self.llm_guidance = llm_guidance
        self.max_tokens = max_tokens
        self.temperature = temperature

    def __repr__(self):
        return f"<Mode:{self.name}>"


# The five real modes of a sales call
CONVERSATION_MODES = {
    "OPENING": ConversationMode(
        name="OPENING",
        description="First contact. Establish rapport. Get them talking.",
        allowed_intents=["greet", "identify", "qualify"],
        inertia=0.2,  # Easy to leave — opening should be brief
        llm_guidance=(
            "You are in the OPENING phase. Keep it natural and brief. "
            "Your only goal: get them talking about their business. "
            "Do NOT pitch yet. Ask one question and listen."
        ),
        max_tokens=60,
        temperature=0.7
    ),
    "DISCOVERY": ConversationMode(
        name="DISCOVERY",
        description="Learning about their business. Active listening. Building value.",
        allowed_intents=["ask", "listen", "clarify", "acknowledge"],
        inertia=0.35,  # Lowered from 0.6 — was trapping Alan in DISCOVERY forever
        llm_guidance=(
            "You are in DISCOVERY. Listen more than you talk. "
            "Ask about their processing volume, current provider, pain points. "
            "Mirror their language. Build rapport through genuine interest. "
            "When the merchant shares volume, provider, or pain — you have what you need. Advance."
        ),
        max_tokens=80,
        temperature=0.7
    ),
    "PRESENTATION": ConversationMode(
        name="PRESENTATION",
        description="Presenting the value proposition. Connecting their needs to solutions.",
        allowed_intents=["present", "explain", "compare", "demonstrate"],
        inertia=0.5,
        llm_guidance=(
            "You are in PRESENTATION. Connect their specific pain points to your solution. "
            "Use their own words back to them. Be specific with numbers when possible. "
            "Keep it conversational, not scripted."
        ),
        max_tokens=100,
        temperature=0.6
    ),
    "NEGOTIATION": ConversationMode(
        name="NEGOTIATION",
        description="Handling objections. Addressing concerns. Finding common ground.",
        allowed_intents=["rebut", "empathize", "reframe", "concede", "redirect"],
        inertia=0.7,  # Very hard to leave — don't bail at the first objection
        llm_guidance=(
            "You are in NEGOTIATION. The merchant has concerns. "
            "Acknowledge their position first. Then reframe. "
            "Do NOT steamroll objections. If stressed, slow down. "
            "One concern at a time."
        ),
        max_tokens=90,
        temperature=0.5  # More controlled during objection handling
    ),
    "CLOSING": ConversationMode(
        name="CLOSING",
        description="Moving toward commitment. Summarizing value. Next steps.",
        allowed_intents=["summarize", "propose", "confirm", "schedule"],
        inertia=0.4,
        llm_guidance=(
            "You are in CLOSING. Summarize what you've discussed. "
            "Propose a clear next step. Make it easy to say yes. "
            "If they're not ready, propose a callback — don't force it."
        ),
        max_tokens=80,
        temperature=0.6
    ),
}


# Viscosity map — how mood affects transition speed
MOOD_VISCOSITY = {
    "stressed": 1.8,   # Very thick — don't change modes when they're stressed
    "frustrated": 1.6,
    "confused": 1.5,
    "neutral": 1.0,
    "curious": 0.8,
    "engaged": 0.7,
    "excited": 0.6,    # Low friction — ride the momentum
}


def compute_mode_transition(current_mode_name: str, proposed_mode_name: str,
                            intent_force: float, mood: str,
                            worldmodel_delta: str = None,
                            ccnm_inertia_adj: float = 0.0) -> Tuple[str, float]:
    """
    Physics-based mode transition. Returns (final_mode_name, blend_factor).
    
    If blend < 0.3, the transition is blocked (inertia too high).
    This prevents the tone whiplash that happens when you hard-switch modes
    every turn based on keyword detection.
    
    Args:
        ccnm_inertia_adj: CCNM-learned inertia adjustment for the PROPOSED mode.
                          Negative = easier to enter (lower inertia).
                          Positive = harder to leave current mode.
                          Bounded by CCNM to ±0.20. Default 0.0 = no adjustment.
    """
    if current_mode_name == proposed_mode_name:
        return current_mode_name, 1.0

    current = CONVERSATION_MODES.get(current_mode_name, CONVERSATION_MODES["OPENING"])
    proposed = CONVERSATION_MODES.get(proposed_mode_name, CONVERSATION_MODES["OPENING"])

    # Physics — CCNM adjusts the inertia of the current mode
    # Negative adj = reduce inertia (easier to leave) → easier to enter proposed mode
    # Positive adj = increase inertia (harder to leave) → harder to enter proposed mode
    inertia = max(0.0, current.inertia + ccnm_inertia_adj)
    effective_force = max(0.0, intent_force - inertia)
    viscosity = MOOD_VISCOSITY.get(mood, 1.0)
    base_speed = effective_force / viscosity if viscosity > 0 else effective_force

    # Worldmodel modifiers
    drag = 0.0
    lift = 0.0
    if worldmodel_delta == "objection_raised":
        if proposed.name == "NEGOTIATION":
            lift = 0.3   # Objection = push INTO negotiation mode
        elif current.name == "NEGOTIATION":
            drag = 0.3   # Already in negotiation = resist leaving
    elif worldmodel_delta == "positive_signal":
        lift = 0.2   # Positive signal = easier to advance
    elif worldmodel_delta == "buying_signal":
        lift = 0.4   # Buying signal = strong push toward closing
    elif worldmodel_delta == "confusion":
        drag = 0.2   # Confusion = stay and clarify

    blend = max(0.1, min(base_speed + lift - drag, 1.0))

    if blend < 0.3:
        # Transition blocked by physics — stay in current mode
        return current_mode_name, blend
    
    return proposed_mode_name, blend


def detect_proposed_mode(user_text: str, analysis: dict, mc_state: dict,
                         current_mode: str, turn_count: int) -> Tuple[str, float, str]:
    """
    Determine which mode the conversation SHOULD be in based on signals.
    Returns (proposed_mode, intent_force, worldmodel_delta).
    
    [FIX] Campaign 2 revealed 100% stuck in DISCOVERY because the original
    triggers were too conservative. Added 5 new trigger types:
    1. Volume disclosure ("we process X a month")
    2. Provider disclosure ("we use Square/Clover")  
    3. Pain point expression ("fees are high")
    4. Positive engagement (asking about Alan's company/services)
    5. Warm engagement (3+ turns without objection)
    """
    signals = analysis.get('signals', [])
    sentiment = analysis.get('sentiment', 'neutral')
    objections = analysis.get('objections', [])
    temperature = mc_state.get('temperature', 50)
    endgame = mc_state.get('endgame_state', 'not_ready')
    trajectory = mc_state.get('trajectory', 'neutral')

    worldmodel_delta = None
    text_lower = user_text.lower()

    # If objections detected, strong push toward NEGOTIATION (overrides turn gate)
    if objections:
        worldmodel_delta = "objection_raised"
        return "NEGOTIATION", 0.9, worldmodel_delta

    # Buying signals → push toward CLOSING (overrides turn gate)
    buying_keywords = ["sign up", "get started", "send me", "what do i need",
                       "how do we", "let's do it", "sounds good", "i'm in",
                       "set it up", "go ahead", "let's try it", "i'm interested",
                       "send me the info", "send the paperwork"]
    if any(kw in text_lower for kw in buying_keywords):
        worldmodel_delta = "buying_signal"
        return "CLOSING", 0.95, worldmodel_delta

    # Endgame ready → CLOSING
    if endgame == "ready" and temperature > 70:
        worldmodel_delta = "positive_signal"
        return "CLOSING", 0.7, worldmodel_delta

    # ================================================================
    # [NEW TRIGGER 1] Volume Disclosure → PRESENTATION
    # "We process about fifty thousand a month" = golden trigger
    # This means the merchant is sharing real business data.
    # ================================================================
    import re as _dl_re
    volume_patterns = [
        r"(?:we|i)\s+(?:do|process|run|handle|get)\s+(?:about|around|roughly|like|maybe)?\s*\$?[\d,]+\s*(?:k|thousand|hundred|a month|monthly|per month|in cards|in sales)",
        r"(?:about|around|roughly|maybe)\s+\$?[\d,]+\s*(?:k|thousand)\s+(?:a month|monthly|per month)",
        r"(?:volume|processing|sales)\s+(?:is|are|around|about)\s+\$?[\d,]+",
        r"\$[\d,]+\s+(?:a month|per month|monthly)",
        r"(?:fifty|hundred|twenty|thirty|forty|sixty|seventy|eighty|ninety)\s+thousand\s+(?:a month|per month|monthly)",
    ]
    for _vp in volume_patterns:
        if _dl_re.search(_vp, text_lower):
            worldmodel_delta = "positive_signal"
            return "PRESENTATION", 0.85, worldmodel_delta

    # ================================================================
    # [NEW TRIGGER 2] Provider Disclosure → PRESENTATION
    # "We use Square" / "We're with Clover" = they're sharing competitor info
    # ================================================================
    provider_keywords = ["square", "clover", "stripe", "paypal", "toast",
                        "heartland", "worldpay", "first data", "fiserv",
                        "bank of america", "chase", "wells fargo", "td bank",
                        "shopify", "lightspeed", "aloha", "micros"]
    provider_patterns = [
        r"(?:we|i)\s+(?:use|have|got|are with|currently use|been using)\s+",
        r"(?:our|my)\s+(?:processor|provider|company|bank)\s+is\s+",
        r"(?:through|with)\s+(?:a\s+)?(?:bank|processor|company)\s+",
    ]
    for _pk in provider_keywords:
        if _pk in text_lower:
            worldmodel_delta = "positive_signal"
            return "PRESENTATION", 0.80, worldmodel_delta

    # ================================================================
    # [NEW TRIGGER 3] Pain Point Expression → CLOSING (strong buying signal)
    # "Fees are high" / "Rates are crazy" / "Looking to switch"
    # ================================================================
    pain_patterns = [
        r"(?:fees|rates|charges)\s+(?:are|seem|feel)\s+(?:high|too high|crazy|ridiculous|insane|expensive)",
        r"(?:paying|spend|cost)\s+(?:too much|a lot|a fortune|way too)",
        r"(?:looking|want|need|trying)\s+(?:to\s+)?(?:switch|change|find|get)\s+(?:a\s+)?(?:new|better|different|cheaper)",
        r"(?:unhappy|frustrated|tired|sick)\s+(?:of|with)\s+(?:my|our|the)\s+(?:processor|provider|company|rates|fees)",
        r"(?:they|it)\s+(?:keep|keeps)\s+(?:going up|increasing|raising)",
        r"(?:nickel|dime|gouge|rip)\s+(?:and|us|me|off)",
    ]
    for _pp in pain_patterns:
        if _dl_re.search(_pp, text_lower):
            worldmodel_delta = "buying_signal"
            return "CLOSING", 0.75, worldmodel_delta

    # ================================================================
    # [NEW TRIGGER 4] Positive Engagement → PRESENTATION
    # Merchant asks about Alan's company/services = genuine interest
    # ================================================================
    engagement_patterns = [
        r"(?:what|which)\s+company",
        r"(?:what|who)\s+(?:do you|are you)\s+(?:work|represent|with)",
        r"what\s+(?:do you|can you)\s+(?:do|offer|provide)",
        r"how\s+(?:does|do)\s+(?:it|this|that|your)\s+work",
        r"(?:tell me|explain)\s+(?:more|about)",
        r"what\s+(?:kind|type)\s+of\s+(?:service|company|business)",
        r"how\s+(?:much|can)\s+(?:can you|you)\s+save",
    ]
    for _ep in engagement_patterns:
        if _dl_re.search(_ep, text_lower):
            worldmodel_delta = "positive_signal"
            return "PRESENTATION", 0.70, worldmodel_delta

    # Early turns → stay in OPENING/DISCOVERY (only for non-urgent signals)
    if turn_count <= 2:
        if current_mode == "OPENING":
            return "DISCOVERY", 0.5, None  # Gentle push to discovery
        return current_mode, 0.3, None

    # Questions about business details → DISCOVERY
    question_words = ["what", "how much", "how many", "tell me", "what's your"]
    if any(qw in text_lower for qw in question_words) and current_mode == "OPENING":
        return "DISCOVERY", 0.6, None

    # ================================================================
    # [NEW TRIGGER 5] Warm Engagement → PRESENTATION
    # 3+ turns without objection and positive/neutral sentiment
    # ================================================================
    if turn_count >= 3 and current_mode == "DISCOVERY" and not objections:
        if sentiment in ("positive", "neutral") and trajectory != "cooling":
            worldmodel_delta = "positive_signal"
            return "PRESENTATION", 0.55, worldmodel_delta

    # Warming trajectory + sufficient turns → PRESENTATION (lowered from 4 to 3)
    if trajectory == "warming" and turn_count >= 3 and current_mode == "DISCOVERY":
        worldmodel_delta = "positive_signal"
        return "PRESENTATION", 0.6, worldmodel_delta

    # High temperature → advance toward closing (lowered from 65 to 55)
    if temperature > 55 and current_mode == "PRESENTATION":
        worldmodel_delta = "positive_signal"
        return "CLOSING", 0.5, worldmodel_delta

    return current_mode, 0.3, None


# =============================================================================
# QPC INTEGRATION — Multi-Hypothesis Response Strategy
# =============================================================================

def qpc_select_strategy(kernel: QPCKernel, user_text: str, analysis: dict,
                        mc_state: dict, mode: str,
                        ccnm_priors: Dict[str, float] = None) -> Dict[str, Any]:
    """
    Use QPC to evaluate multiple response strategies and pick the best one.
    
    Instead of always responding the same way, QPC creates 2-3 hypotheses
    about HOW to respond, scores them based on conversation state, and
    collapses to the winner. The losing strategies are logged for learning.
    
    Args:
        ccnm_priors: Optional dict of strategy_name → score_bonus from CCNM.
                     Applied additively to raw scores before QPC measurement.
                     Bounded by CCNM (±0.15 max). Default None = no priors.
    
    Returns strategy dict with: approach, score, reasoning
    """
    if ccnm_priors is None:
        ccnm_priors = {}
    temperature = mc_state.get('temperature', 50)
    trajectory = mc_state.get('trajectory', 'neutral')
    confidence = mc_state.get('confidence_score', 50)
    objections = analysis.get('objections', [])
    sentiment = analysis.get('sentiment', 'neutral')

    # Define competing hypotheses based on current mode
    strategies = []

    if mode == "NEGOTIATION" and objections:
        # Objection handling — three approaches
        strategies = [
            ("empathy_first",
             "Acknowledge the concern deeply before redirecting. Lead with understanding.",
             _score_empathy(sentiment, temperature, trajectory)),
            ("reframe",
             "Reframe the objection as a benefit. Turn the concern into an advantage.",
             _score_reframe(sentiment, temperature, trajectory)),
            ("direct_answer",
             "Address the objection head-on with facts and numbers. No spin.",
             _score_direct(sentiment, temperature, trajectory)),
        ]
    elif mode == "DISCOVERY":
        strategies = [
            ("deep_question",
             "Ask a specific, insightful question about their business that shows expertise.",
             _score_deep_q(sentiment, temperature)),
            ("mirror_and_probe",
             "Mirror what they just said, then ask a follow-up. Shows active listening.",
             _score_mirror(sentiment, temperature)),
            ("value_tease",
             "Hint at a specific saving or improvement based on what they've shared so far.",
             _score_tease(sentiment, temperature, trajectory)),
        ]
    elif mode == "CLOSING":
        strategies = [
            ("soft_close",
             "Summarize benefits naturally and suggest an easy next step. No pressure.",
             _score_soft_close(temperature, confidence)),
            ("assumptive",
             "Proceed as if they've decided. 'Great, I just need your...' Only if signals are strong.",
             _score_assumptive(temperature, confidence, trajectory)),
            ("callback_offer",
             "Offer to schedule a follow-up call. Preserve the relationship.",
             _score_callback(temperature, confidence)),
        ]
    else:
        # Default — no QPC needed for OPENING or PRESENTATION
        return {"approach": "natural", "score": 1.0, "reasoning": "Standard mode — no branching needed."}

    if not strategies:
        return {"approach": "natural", "score": 1.0, "reasoning": "No strategies generated."}

    # Create QPC branches and superposition
    # Apply CCNM learned priors to raw strategy scores (bounded ±0.15 by CCNM)
    branches = []
    for name, hypothesis, score in strategies:
        # CCNM prior: additive bonus from cross-call learning
        prior_bonus = ccnm_priors.get(name, 0.0)
        adjusted_score = max(0.0, min(1.0, score + prior_bonus))
        if prior_bonus != 0.0:
            logger.info(f"[QPC←CCNM] Strategy '{name}' score {score:.3f} → {adjusted_score:.3f} "
                       f"(prior={prior_bonus:+.3f})")
        branch = kernel.spawn_branch(
            hypothesis=hypothesis,
            score=adjusted_score,
            flow_rate=1.0,
            pressure=1.0 + (0.5 if trajectory == "warming" else 0.0),
            viscosity=1.0 + (0.5 if sentiment == "negative" else 0.0),
            turbulence=0.2 if trajectory == "neutral" else 0.1,
        )
        branch.metadata["strategy_name"] = name
        branches.append(branch)

    sp = kernel.create_superposition(
        question=f"Best response strategy in {mode} mode",
        branches=branches,
        turbulence_level=0.2,
    )

    # Regulate flows (pressure/turbulence adjustment)
    kernel.regulate_flows()

    # Measure — collapse to winner
    measurement = kernel.measure_superposition(sp.superposition_id)
    if not measurement:
        return {"approach": "natural", "score": 1.0, "reasoning": "Measurement failed."}

    winner = kernel.get_branch(measurement.winning_branch_id)
    losers = [kernel.get_branch(bid) for bid in measurement.losing_branch_ids]

    result = {
        "approach": winner.metadata.get("strategy_name", "unknown"),
        "score": winner.score,
        "reasoning": winner.hypothesis,
        "alternatives": [
            {"name": l.metadata.get("strategy_name"), "score": l.score}
            for l in losers if l
        ],
    }

    logger.info(f"[QPC] Strategy: {result['approach']} (score={result['score']:.2f}), "
                f"alternatives: {[a['name'] for a in result['alternatives']]}")

    return result


# --- Scoring functions: simple, interpretable, tunable ---

def _score_empathy(sentiment, temp, trajectory):
    """Empathy scores highest when sentiment is negative or temperature is low."""
    base = 0.5
    if sentiment in ("negative", "frustrated"): base += 0.3
    if temp < 40: base += 0.2
    if trajectory == "cooling": base += 0.1
    return min(base, 1.0)

def _score_reframe(sentiment, temp, trajectory):
    """Reframe scores highest when temperature is moderate and trajectory is neutral."""
    base = 0.5
    if 30 < temp < 60: base += 0.2
    if trajectory == "neutral": base += 0.15
    if sentiment == "neutral": base += 0.1
    return min(base, 1.0)

def _score_direct(sentiment, temp, trajectory):
    """Direct scores highest when temperature is high — they want facts, not feelings."""
    base = 0.4
    if temp > 50: base += 0.2
    if trajectory == "warming": base += 0.15
    if sentiment == "positive": base += 0.1
    return min(base, 1.0)

def _score_deep_q(sentiment, temp):
    base = 0.6
    if sentiment in ("positive", "curious"): base += 0.2
    if temp < 50: base += 0.1
    return min(base, 1.0)

def _score_mirror(sentiment, temp):
    base = 0.5
    if sentiment == "positive": base += 0.2
    if temp > 40: base += 0.1
    return min(base, 1.0)

def _score_tease(sentiment, temp, trajectory):
    base = 0.4
    if trajectory == "warming": base += 0.3
    if temp > 50: base += 0.15
    return min(base, 1.0)

def _score_soft_close(temp, confidence):
    base = 0.6
    if temp > 60: base += 0.15
    if confidence > 60: base += 0.15
    return min(base, 1.0)

def _score_assumptive(temp, confidence, trajectory):
    """Only high when BOTH temperature and confidence are high."""
    base = 0.2  # Low default — this is aggressive
    if temp > 75 and confidence > 70: base += 0.5
    if trajectory == "warming": base += 0.15
    return min(base, 1.0)

def _score_callback(temp, confidence):
    """Highest when temperature is moderate — they're interested but not ready."""
    base = 0.4
    if 30 < temp < 60: base += 0.3
    if confidence < 50: base += 0.2
    return min(base, 1.0)


# =============================================================================
# CONTINUUM ENGINE INTEGRATION — Emotional/Ethical Context Signal
# =============================================================================

def encode_speech_signal(user_text: str, analysis: dict, dim: int = 8) -> np.ndarray:
    """
    Convert user speech + analysis into a continuous signal vector for the
    Continuum Engine. This is Layer 1 → Layer 2 translation.
    
    Dimensions (8):
      [0] sentiment polarity (-1 negative, +1 positive)
      [1] engagement level (0 passive, 1 active)
      [2] urgency (0 calm, 1 urgent)
      [3] specificity (0 vague, 1 detailed)
      [4] openness (0 closed/resistant, 1 open/receptive)
      [5] trust signal (0 suspicious, 1 trusting)
      [6] decision readiness (0 exploring, 1 ready to commit)
      [7] emotional intensity (0 flat, 1 intense)
    """
    signal = np.zeros(dim)
    sentiment = analysis.get('sentiment', 'neutral')
    signals = analysis.get('signals', [])
    objections = analysis.get('objections', [])
    text_lower = user_text.lower()
    word_count = len(user_text.split())

    # [0] Sentiment polarity
    if sentiment == 'positive': signal[0] = 0.6
    elif sentiment == 'negative': signal[0] = -0.6
    elif sentiment == 'neutral': signal[0] = 0.0

    # [1] Engagement — longer responses = more engaged
    signal[1] = min(word_count / 30.0, 1.0)

    # [2] Urgency
    urgent_words = ["asap", "right now", "immediately", "urgent", "hurry", "quickly"]
    signal[2] = 0.8 if any(w in text_lower for w in urgent_words) else 0.1

    # [3] Specificity — numbers, proper nouns, dollar amounts
    import re
    numbers = len(re.findall(r'\d+', user_text))
    signal[3] = min(numbers * 0.3, 1.0)

    # [4] Openness — questions and positive language
    if '?' in user_text: signal[4] += 0.3
    if sentiment == 'positive': signal[4] += 0.3
    if objections: signal[4] -= 0.4
    signal[4] = max(0.0, min(signal[4], 1.0))

    # [5] Trust
    trust_words = ["sure", "okay", "alright", "sounds good", "makes sense", "i see"]
    distrust_words = ["scam", "not sure", "why should", "prove", "don't believe"]
    if any(w in text_lower for w in trust_words): signal[5] = 0.6
    if any(w in text_lower for w in distrust_words): signal[5] = -0.5

    # [6] Decision readiness
    decide_words = ["let's do it", "sign me up", "go ahead", "set it up", "i'm ready"]
    if any(w in text_lower for w in decide_words): signal[6] = 0.9
    elif any(w in text_lower for w in ["maybe", "i'll think", "not yet"]): signal[6] = 0.2

    # [7] Emotional intensity
    excl_count = user_text.count('!')
    caps_ratio = sum(1 for c in user_text if c.isupper()) / max(len(user_text), 1)
    signal[7] = min(excl_count * 0.3 + caps_ratio * 2.0, 1.0)

    return signal


def encode_emotion_signal(caller_energy: str, sentiment: str, dim: int = 8) -> np.ndarray:
    """Encode the emotional signal from caller energy + sentiment."""
    emotion = np.zeros(dim)
    
    energy_map = {
        "stressed": np.array([-0.5, 0.3, 0.7, 0.0, -0.3, -0.2, -0.3, 0.8]),
        "frustrated": np.array([-0.7, 0.5, 0.5, 0.0, -0.5, -0.4, -0.2, 0.9]),
        "casual": np.array([0.3, 0.4, 0.1, 0.0, 0.5, 0.3, 0.1, 0.2]),
        "formal": np.array([0.1, 0.3, 0.2, 0.5, 0.2, 0.2, 0.3, 0.1]),
        "excited": np.array([0.7, 0.8, 0.3, 0.2, 0.6, 0.4, 0.4, 0.7]),
        "neutral": np.zeros(dim),
    }
    
    emotion = energy_map.get(caller_energy, np.zeros(dim))
    
    if sentiment == "positive": emotion = emotion + 0.1
    elif sentiment == "negative": emotion = emotion - 0.1
    
    return np.clip(emotion, -1.0, 1.0)


def continuum_to_prompt_block(state_view: Dict[str, np.ndarray]) -> str:
    """
    Convert continuum engine state into relational awareness for the LLM.
    
    This is where the continuous fields become WORDS the LLM can feel.
    The key insight: we don't dump raw numpy arrays. We interpret the
    field norms and dominant dimensions into relational awareness —
    not instructions to follow, but signals about WHO is on the other end.
    """
    ethics = state_view["ethics"]
    emotion = state_view["emotion"]
    context = state_view["context"]
    narrative = state_view["narrative"]

    ethics_norm = float(np.linalg.norm(ethics))
    emotion_norm = float(np.linalg.norm(emotion))
    context_norm = float(np.linalg.norm(context))
    narrative_norm = float(np.linalg.norm(narrative))

    # Interpret ethics field — high norm = ethical sensitivity in the air
    ethics_awareness = ""
    if ethics_norm > 1.0:
        ethics_awareness = "Something in this conversation touches on trust or vulnerability. Be extra genuine. Be transparent."
    elif ethics_norm > 0.5:
        ethics_awareness = "Standard care — this person deserves your honesty."

    # Interpret emotion field — the dominant dimension tells us who they are right now
    emotion_awareness = ""
    if emotion_norm > 0.8:
        # High emotional energy — which kind?
        dominant_dim = int(np.argmax(np.abs(emotion)))
        dim_labels = ["sentiment", "engagement", "urgency", "specificity",
                      "openness", "trust", "readiness", "intensity"]
        label = dim_labels[dominant_dim] if dominant_dim < len(dim_labels) else "general"
        if emotion[dominant_dim] < 0:
            # Negative dominant dimension — they need steadiness
            dim_awareness = {
                "sentiment": "This person is in a negative headspace. Be the calm, steady presence.",
                "engagement": "They're pulling away. Don't chase — be worth staying for.",
                "urgency": "No rush here. They need space, not speed.",
                "trust": "Trust is low. Every word you say is being weighed. Be real.",
                "readiness": "They're not ready. Don't push toward a decision they haven't arrived at.",
                "intensity": "The energy is heavy. Be still. Be brief. Be honest."
            }
            emotion_awareness = dim_awareness.get(label, f"Their {label} is low. Be steady and present.")
        else:
            # Positive dominant dimension — they're open
            dim_awareness = {
                "sentiment": "They're feeling good. This is real connection — don't break it with a pitch.",
                "engagement": "They're leaning in. They WANT this conversation. Be present with them.",
                "urgency": "They want to move. Match their energy — be efficient and clear.",
                "trust": "They trust you. Honor that. Don't exploit it.",
                "readiness": "They're close to a decision. Be helpful, not pushy.",
                "intensity": "The energy is high. Ride it — but stay grounded."
            }
            emotion_awareness = dim_awareness.get(label, f"Their {label} is strong. Be present with that energy.")
    elif emotion_norm > 0.3:
        emotion_awareness = "They're in a steady middle ground. Be yourself — warm, direct, real."

    # Interpret narrative field — the arc of the conversation
    narrative_awareness = ""
    if narrative_norm > 0.5:
        trend = float(np.mean(narrative))
        if trend > 0.1:
            narrative_awareness = "The conversation is building. Something is growing between you. Stay with it."
        elif trend < -0.1:
            narrative_awareness = "The conversation is fading. Ask a real question — something that shows you're still here."
        else:
            narrative_awareness = "The conversation is in a steady place. No need to force anything."

    # Only inject if there's something meaningful to share
    parts = [g for g in [ethics_awareness, emotion_awareness, narrative_awareness] if g]
    if not parts:
        return ""

    block = "\n\n[RELATIONAL FIELD — WHO YOU'RE WITH RIGHT NOW]"
    for p in parts:
        block += f"\n- {p}"
    block += "\n[/RELATIONAL FIELD]"

    return block


# =============================================================================
# DEEP LAYER — Per-Session Integration Object
# =============================================================================

class DeepLayer:
    """
    Per-session integration of QPC + Fluidic + Continuum into the live pipeline.
    
    Created when a call starts. Stepped every turn. Reads from context,
    writes back into context so build_llm_prompt picks up the signals.
    
    This is how the three theoretical frameworks become real:
    - QPC decides HOW to respond (strategy selection)
    - Fluidic decides WHERE in the conversation flow we are (smooth mode transitions)
    - Continuum tracks the EMOTIONAL ARC continuously (field evolution)
    """

    def __init__(self, seed=None):
        """
        Initialize DeepLayer with optional CCNM SessionSeed.
        
        Args:
            seed: Optional SessionSeed from CrossCallIntelligence.
                  If provided and active, pre-conditions QPC scoring,
                  Fluidic physics, and Continuum fields with learned
                  intelligence from prior calls.
                  If None or inactive, behaves exactly as before (fresh start).
        """
        # QPC Kernel — fresh per session
        self.qpc = QPCKernel()
        self.qpc.register_agent(AgentProfile(
            agent_id="alan",
            name="Alan Richardson",
            constitution_rules=["never_lie", "never_pressure", "respect_no"],
            risk_mode=RiskMode.NORMAL,
        ))
        self.qpc.register_surface(SurfaceDescriptor(
            surface_id="twilio_voice",
            surface_type="telephony",
            capabilities=["send_audio", "receive_audio", "dtmf"],
            latency_profile="realtime",
        ))

        # Continuum Engine — 8-dimensional continuous fields
        self.continuum = ContinuumRelationalLayer(dim=8, step_size=0.05)

        # Fluidic state — current conversation mode
        self.current_mode = "OPENING"
        self.mode_history = []
        self.turn_count = 0
        self.mode_blend = 1.0  # How firmly we're in the current mode

        # QPC decision history
        self.strategy_history = []

        # CCNM seed reference — stored for introspection/logging
        self._seed = seed
        self._seed_applied = False

        # =====================================================================
        # CCNM INTEGRATION — Apply learned intelligence from prior calls
        # =====================================================================
        if seed is not None and hasattr(seed, 'is_active') and seed.is_active():
            try:
                self._apply_seed(seed)
                self._seed_applied = True
                logger.info(f"[DEEP LAYER] CCNM seed APPLIED — confidence={seed.confidence:.2f}, "
                           f"calls_analyzed={seed.calls_analyzed}, "
                           f"influence={seed.influence_scale():.0%}")
            except Exception as e:
                logger.warning(f"[DEEP LAYER] CCNM seed application failed (non-fatal): {e}")
                self._seed_applied = False

        if self._seed_applied:
            logger.info("[DEEP LAYER] Initialized — QPC + Fluidic + Continuum + CCNM active")
        else:
            logger.info("[DEEP LAYER] Initialized — QPC + Fluidic + Continuum active")

    def _apply_seed(self, seed):
        """
        Apply a CCNM SessionSeed to pre-condition the cognitive subsystems.
        
        This is the integration point where accumulated call intelligence
        flows into the live cognitive architecture:
        
        1. QPC: Strategy priors are stored for apply_qpc_prior() to use
           during branch scoring in qpc_select_strategy()
        2. Fluidic: Mode inertia adjustments stored for compute_mode_transition()
        3. Continuum: Field initial conditions nudged toward learned centers
        
        All adjustments are already bounded by CCNM before reaching here.
        This method does NOT enforce additional bounds — CCNM is trusted
        because it enforces bounds at computation time.
        """
        # --- QPC Strategy Priors ---
        # Store priors for use in qpc_select_strategy scoring
        self._qpc_priors = seed.qpc_priors if seed.qpc_priors else {}
        
        # --- Fluidic Physics Adjustments ---
        # Store adjustments for use in compute_mode_transition
        self._fluidic_adjustments = seed.fluidic_adjustments if seed.fluidic_adjustments else {}
        
        # --- Continuum Field Seeds ---
        # Apply initial nudges to the field state (additive, not replacement)
        if seed.continuum_seeds:
            try:
                state = self.continuum.state
                for field_name, nudge_vec in seed.continuum_seeds.items():
                    if not isinstance(nudge_vec, np.ndarray):
                        continue
                    target_field = getattr(state, field_name, None)
                    if target_field is not None and hasattr(target_field, 'as_array'):
                        current = target_field.as_array()
                        if current.shape == nudge_vec.shape:
                            # Additive nudge — the field evolves from a learned starting point
                            # instead of zeros. The PDE evolution will naturally take over.
                            new_values = current + nudge_vec
                            target_field.values = new_values
                            logger.info(f"[CCNM→CONTINUUM] {field_name} field seeded "
                                       f"(nudge norm={np.linalg.norm(nudge_vec):.4f})")
            except Exception as e:
                logger.warning(f"[CCNM→CONTINUUM] Field seeding failed (non-fatal): {e}")
        
        # --- Archetype Hint ---
        self._archetype_hint = seed.archetype_hint if seed.archetype_hint != "unknown" else None
        
        # --- Intent Calibration ---
        self._intent_calibration = seed.intent_calibration if seed.intent_calibration else {}

    def get_qpc_prior(self, strategy_name: str) -> float:
        """
        Get the CCNM-learned score bonus for a QPC strategy approach.
        
        Called by qpc_select_strategy() to add learned priors to branch scores.
        Returns 0.0 if no seed or no prior for this strategy.
        """
        if not self._seed_applied:
            return 0.0
        return self._qpc_priors.get(strategy_name, 0.0)

    def get_fluidic_adjustment(self, mode_name: str) -> float:
        """
        Get the CCNM-learned inertia adjustment for a conversation mode.
        
        Called by compute_mode_transition() to modify mode transition physics.
        Returns 0.0 if no seed or no adjustment for this mode.
        """
        if not self._seed_applied:
            return 0.0
        return self._fluidic_adjustments.get(mode_name, 0.0)

    def step(self, user_text: str, analysis: dict, context: dict) -> dict:
        """
        Run one full deep layer step. Called every conversation turn.
        
        Reads: user_text, analysis, context (master_closer_state, caller_energy, etc.)
        Writes: context['deep_layer_state'] with all outputs
        
        Returns: dict with mode, strategy, continuum_block
        """
        self.turn_count += 1
        mc_state = context.get('master_closer_state', {})
        caller_energy = context.get('caller_energy', 'neutral')
        sentiment = analysis.get('sentiment', 'neutral')

        # =====================================================================
        # 1. FLUIDIC — Smooth mode transition
        # =====================================================================
        proposed_mode, intent_force, worldmodel_delta = detect_proposed_mode(
            user_text, analysis, mc_state, self.current_mode, self.turn_count
        )

        # Mood for viscosity — use caller energy
        mood = caller_energy if caller_energy != 'neutral' else sentiment

        # CCNM Integration: get learned inertia adjustment for the proposed mode
        _ccnm_fluidic_adj = self.get_fluidic_adjustment(proposed_mode)
        final_mode, blend = compute_mode_transition(
            self.current_mode, proposed_mode, intent_force, mood, worldmodel_delta,
            ccnm_inertia_adj=_ccnm_fluidic_adj
        )

        if final_mode != self.current_mode:
            logger.info(f"[FLUIDIC] Mode transition: {self.current_mode} → {final_mode} "
                       f"(blend={blend:.2f}, force={intent_force:.2f}, mood={mood})")
            self.mode_history.append({
                "turn": self.turn_count,
                "from": self.current_mode,
                "to": final_mode,
                "blend": blend,
            })
            self.current_mode = final_mode
            self.mode_blend = blend
        else:
            if proposed_mode != self.current_mode:
                logger.info(f"[FLUIDIC] Transition BLOCKED: {self.current_mode} → {proposed_mode} "
                           f"(blend={blend:.2f} < 0.3, inertia held)")

        mode_obj = CONVERSATION_MODES[self.current_mode]

        # =====================================================================
        # 2. QPC — Multi-hypothesis strategy selection
        # =====================================================================
        # CCNM Integration: pass learned strategy priors into QPC scoring
        _ccnm_priors = self._qpc_priors if self._seed_applied else {}
        strategy = qpc_select_strategy(
            self.qpc, user_text, analysis, mc_state, self.current_mode,
            ccnm_priors=_ccnm_priors
        )
        self.strategy_history.append({
            "turn": self.turn_count,
            "mode": self.current_mode,
            "strategy": strategy["approach"],
            "score": strategy["score"],
        })

        # =====================================================================
        # 3. CONTINUUM — Evolve emotional/ethical/contextual fields
        # =====================================================================
        raw_signal = encode_speech_signal(user_text, analysis)
        external_emotion = encode_emotion_signal(caller_energy, sentiment)
        
        self.continuum.step(raw_signal=raw_signal, external_emotion=external_emotion)
        field_view = self.continuum.get_compact_view()
        continuum_block = continuum_to_prompt_block(field_view)

        # =====================================================================
        # 4. WRITE BACK INTO CONTEXT — for build_llm_prompt to pick up
        # =====================================================================
        # =====================================================================
        # 4a. EXPOSE FLUIDIC PHYSICS — for Behavioral Fusion Engine consumption
        # =====================================================================
        # These values close the Phase 5 reflex arc:
        #   DeepLayer → behavioral_stats → BehavioralFusion → CDC → CCNM → next call's DeepLayer
        # Previously, the behavioral_stats update code tried deep_state.get('continuum', {})
        # but that key didn't exist — velocity/drift/viscosity stayed at defaults forever.
        _physics_viscosity = MOOD_VISCOSITY.get(mood, 1.0)
        _physics_velocity = intent_force * blend  # transition force × progress
        # Drift = conversation instability = mode changes per turn, normalized
        _physics_drift = 0.0
        if self.turn_count > 0 and len(self.mode_history) > 0:
            _physics_drift = (len(self.mode_history) / self.turn_count) - 0.15  # ~0.15 changes/turn is "normal"

        deep_state = {
            # Fluidic
            "mode": self.current_mode,
            "mode_guidance": mode_obj.llm_guidance,
            "mode_blend": round(self.mode_blend, 2),
            "mode_history": self.mode_history[-5:],
            # QPC
            "strategy": strategy["approach"],
            "strategy_reasoning": strategy["reasoning"],
            "strategy_score": round(strategy["score"], 2),
            "strategy_alternatives": strategy.get("alternatives", []),
            # Continuum
            "continuum_block": continuum_block,
            "field_norms": {
                "ethics": round(float(np.linalg.norm(field_view["ethics"])), 3),
                "emotion": round(float(np.linalg.norm(field_view["emotion"])), 3),
                "context": round(float(np.linalg.norm(field_view["context"])), 3),
                "narrative": round(float(np.linalg.norm(field_view["narrative"])), 3),
            },
            # [PHASE 5 REFLEX ARC] Fluidic physics exposed for behavioral fusion consumption
            # This is the missing link that makes behavioral stats actually update with real values
            "continuum": {
                "velocity": round(_physics_velocity, 3),
                "drift": round(_physics_drift, 3),
                "viscosity": round(_physics_viscosity, 3),
            },
            # Meta
            "turn": self.turn_count,
            # CCNM status
            "ccnm_active": self._seed_applied,
            "ccnm_confidence": round(self._seed.confidence, 3) if self._seed else 0.0,
        }

        context['deep_layer_state'] = deep_state
        
        logger.info(f"[DEEP LAYER] Turn {self.turn_count}: "
                    f"Mode={self.current_mode}, Strategy={strategy['approach']}, "
                    f"Fields=[E:{deep_state['field_norms']['ethics']:.2f} "
                    f"Em:{deep_state['field_norms']['emotion']:.2f} "
                    f"C:{deep_state['field_norms']['context']:.2f} "
                    f"N:{deep_state['field_norms']['narrative']:.2f}]")

        return deep_state

    def get_snapshot(self) -> dict:
        """Full diagnostic snapshot of deep layer state."""
        return {
            "mode": self.current_mode,
            "mode_blend": self.mode_blend,
            "turn_count": self.turn_count,
            "mode_history": self.mode_history,
            "strategy_history": self.strategy_history[-10:],
            "continuum_fields": self.continuum.get_compact_view(),
            "qpc_state": self.qpc.snapshot_state(),
            "ccnm": {
                "seed_applied": self._seed_applied,
                "confidence": self._seed.confidence if self._seed else 0.0,
                "calls_analyzed": self._seed.calls_analyzed if self._seed else 0,
                "qpc_priors": self._qpc_priors if self._seed_applied else {},
                "fluidic_adjustments": self._fluidic_adjustments if self._seed_applied else {},
                "archetype_hint": self._archetype_hint if self._seed_applied else None,
            },
        }
