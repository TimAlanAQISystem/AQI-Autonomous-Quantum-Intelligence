"""
AGENT X — CONVERSATION SUPPORT ENGINE
=======================================
Agent X's role: Support Alan during live calls by handling off-topic
conversation intelligence, QPC strategy awareness, IQ Core cognition,
and HUMAN MANNERISM ADVISORY — making Alan sound unmistakably human.

Architecture:
  analyze_business_response() → Agent X processes every turn
  → off-topic guidance + IQ enrichment + QPC TAP + mannerism advisory
  → injected into build_llm_prompt() → Alan's LLM
  → Alan responds naturally with guidance (he decides what to use)

Human Mannerism Advisory:
  Agent X uses psychological analysis to advise Alan when to inject
  micro-behaviors (cough, sniffle, laugh, throat clear, "um", sigh)
  that make him sound like a real human on the phone. Not random —
  strategically timed based on conversation dynamics. Alan still
  decides whether to use them.

Created: February 15, 2026
Updated: February 15, 2026 — Human Mannerism Advisory Engine
By: Agent X Conversation Support Module
"""

import json
import os
import random
import logging
import re
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# [IQ CORES] Connect to Agent X's cognitive architecture
try:
    from iqcores import IQCoreOrchestrator
    IQCORES_AVAILABLE = True
except ImportError:
    IQCORES_AVAILABLE = False


class AgentXConversationSupport:
    """
    Agent X's live conversation support layer for Alan.
    
    PRIORITY DISPATCH ENGINE — processes ALL responsibilities per turn
    in strict priority order with a 10ms time budget. Fastest first,
    cosmetic last. Skips lower tiers when under time pressure.
    
    Priority ladder:
    P0 — SPEED OPTIMIZER      (Always)  Fights lag at source
    P1 — OFF-TOPIC CLASSIFIER (Always)  Safety rail
    P2 — QPC TAP              (Always)  DeepLayer intelligence
    P3 — IQ CORES             (Budget)  3-speed: cached → QPC-accel → fresh
    P4 — LATENCY FILLER       (Budget)  Emergency lag mask
    P5 — MANNERISM ADVISORY   (Budget)  Human micro-behaviors
    
    Additional:
    - QPC-accelerated IQ path — when QPC confidence > 0.6, skip Core 1
      (Reasoning) and shortcut Core 5 (Emotion) using QPC field data
    - IQ Core 2-turn cache — skips all IQ computation when sentiment stable
    - Brevity gating — P4/P5 auto-skip when speed optimizer is active
    - Dispatch diagnostic — one-line log per turn showing what ran/skipped
    """

    def __init__(self, rapport_layer: dict = None, base_dir: str = None):
        """Initialize with rapport_layer data and IQ cores."""
        self.rapport_layer = rapport_layer or {}
        self._load_off_topic_config()

        # [IQ CORES] Initialize the 5-core orchestrator
        if IQCORES_AVAILABLE:
            try:
                self.iq_orchestrator = IQCoreOrchestrator(base_dir)
                self.iq_cores_online = True
                logger.info("[AGENT X SUPPORT] 5 IQ Cores ONLINE — Full cognitive support active")
            except Exception as e:
                self.iq_orchestrator = None
                self.iq_cores_online = False
                logger.warning(f"[AGENT X SUPPORT] IQ Core init failed, basic mode: {e}")
        else:
            self.iq_orchestrator = None
            self.iq_cores_online = False

        # [IQ CACHE] Avoid recomputing 5 IQ cores when state hasn't changed
        self._iq_cache = None  # {'data': {}, 'turn': int, 'sentiment': str}

        logger.info("[AGENT X SUPPORT] Conversation Support Engine initialized")

    def _load_off_topic_config(self):
        """Extract and organize off-topic handling config from rapport_layer."""
        resilience = self.rapport_layer.get('off_topic_resilience', {})
        safety = self.rapport_layer.get('safety_rails', {})

        # Off-topic engagement responses (for ENGAGE mode — turns 1-2)
        self.rapport_prompts = resilience.get('rapport_prompts', [
            "Are you into that kind of thing?",
            "That sounds interesting.",
            "You sound like you know a lot about that.",
            "What got you into that?",
            "That's cool, honestly."
        ])

        # Acknowledgments
        self.acknowledgments = resilience.get('acknowledgments', [
            "Ha, I hear you.",
            "Oh yeah?",
            "No kidding.",
            "That's something.",
            "I feel that."
        ])

        # Mission pivots (for BRIDGE mode — turn 3+)
        self.mission_pivots = resilience.get('mission_pivots', [
            "Anyway, the reason I reached out —",
            "But hey, let me keep this quick for you.",
            "That said, I don't want to take up too much of your time.",
            "Speaking of which, the whole reason I'm calling —",
            "I appreciate that. Real quick though —"
        ])

        # Safety rails — topics to DEFLECT immediately
        self.deflect_topics = safety.get('avoid', [
            "politics", "religion", "medical", "specific facts outside domain"
        ])

        # Max off-topic turns before mandating bridge
        constraints = resilience.get('constraints', {})
        self.max_engage_turns = constraints.get('max_off_topic_turns', 2)

        # Enhanced topic categories for smarter detection
        self.topic_categories = {
            'sports': [
                'game', 'score', 'team', 'season', 'playoffs', 'championship',
                'football', 'basketball', 'baseball', 'soccer', 'hockey',
                'super bowl', 'world series', 'nba', 'nfl', 'mlb',
                'quarterback', 'touchdown', 'home run', 'slam dunk',
                'coach', 'draft', 'trade', 'roster', 'stadium',
                'espn', 'sportscenter', 'march madness', 'final four'
            ],
            'weather': [
                'weather', 'rain', 'snow', 'sunny', 'storm', 'cold',
                'hot', 'freezing', 'humidity', 'forecast', 'temperature',
                'tornado', 'hurricane', 'drought', 'flood', 'wind',
                'blizzard', 'heat wave'
            ],
            'personal': [
                'family', 'kids', 'wife', 'husband', 'daughter', 'son',
                'vacation', 'weekend', 'birthday', 'anniversary', 'wedding',
                'holiday', 'christmas', 'thanksgiving', 'retirement',
                'grandkids', 'baby', 'pregnant', 'school', 'college',
                'graduation', 'trip', 'travel'
            ],
            'entertainment': [
                'movie', 'show', 'netflix', 'series', 'episode', 'season finale',
                'music', 'concert', 'band', 'song', 'album', 'singer',
                'tv', 'streaming', 'youtube', 'podcast', 'book',
                'video game', 'gaming', 'playstation', 'xbox', 'nintendo'
            ],
            'food': [
                'lunch', 'dinner', 'breakfast', 'restaurant', 'cooking',
                'recipe', 'pizza', 'burger', 'steak', 'coffee', 'beer',
                'wine', 'barbecue', 'grill', 'takeout', 'delivery'
            ],
            'humor': [
                'joke', 'funny', 'hilarious', 'laugh', 'comedy', 'humor',
                'kidding', 'messing with you', 'pulling my leg', 'cracking up'
            ],
            'complaints_life': [
                'traffic', 'commute', 'construction', 'parking',
                'insurance', 'rent', 'mortgage', 'taxes',
                'tired', 'exhausted', 'burned out', 'stressed',
                'neighbor', 'landlord'
            ],
            'news_events': [
                'news', 'headline', 'breaking', 'election', 'economy',
                'stock market', 'crypto', 'bitcoin', 'interest rate',
                'inflation', 'recession', 'real estate', 'housing market'
            ],
            'hobbies': [
                'fishing', 'hunting', 'golf', 'camping', 'hiking',
                'car', 'truck', 'motorcycle', 'racing', 'boat',
                'gym', 'workout', 'running', 'marathon', 'yoga',
                'garden', 'woodworking', 'photography', 'painting'
            ],
            'politics': [
                'democrat', 'republican', 'liberal', 'conservative',
                'president', 'congress', 'senate', 'governor',
                'vote', 'election', 'policy', 'political', 'politician',
                'left wing', 'right wing', 'partisan'
            ],
            'religion': [
                'church', 'god', 'bible', 'prayer', 'faith',
                'christian', 'muslim', 'jewish', 'buddhist', 'hindu',
                'temple', 'mosque', 'synagogue', 'pastor', 'preacher',
                'spiritual', 'scripture', 'sermon'
            ],
            'medical': [
                'doctor', 'hospital', 'surgery', 'medication', 'diagnosis',
                'treatment', 'therapy', 'symptom', 'condition',
                'prescription', 'health issue', 'medical advice'
            ]
        }

    def classify_off_topic(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Enhanced off-topic classification that goes beyond keyword matching.
        
        Returns: (is_off_topic: bool, category: str or None)
        """
        text_lower = text.lower()

        # Check each category
        best_category = None
        best_score = 0

        for category, keywords in self.topic_categories.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > best_score:
                best_score = score
                best_category = category

        # Need at least 1 keyword match to be considered off-topic
        if best_score >= 1:
            # But check if it's also business-relevant (mixed context)
            business_keywords = [
                'processing', 'fees', 'merchant', 'payment', 'credit card',
                'terminal', 'statement', 'savings', 'rates', 'account',
                'business', 'volume', 'transactions', 'swipe', 'chip',
                'pos', 'register', 'revenue', 'profit', 'sales'
            ]
            business_score = sum(1 for kw in business_keywords if kw in text_lower)

            # If more business than off-topic, it's not really off-topic
            if business_score > best_score:
                return False, None

            return True, best_category

        return False, None

    def get_response_mode(self, category: str, off_topic_turn_count: int) -> str:
        """
        Decide how Alan should handle this off-topic moment.
        
        ENGAGE: Be human, show personality, connect (turns 1-2)
        BRIDGE: Naturally transition back to business (turn 3+)
        DEFLECT: Warm but firm redirection (politics/religion/medical)
        """
        # Immediate deflection for sensitive topics
        if category in ('politics', 'religion', 'medical'):
            return 'DEFLECT'

        # Engage for first N turns, then bridge
        if off_topic_turn_count <= self.max_engage_turns:
            return 'ENGAGE'
        else:
            return 'BRIDGE'

    def build_conversation_guidance(self, text: str, category: str, mode: str,
                                     off_topic_turn_count: int, context: dict = None) -> str:
        """
        Build the [CONVERSATION GUIDANCE] block that gets injected into
        Alan's LLM prompt. This is where Agent X directly supports Alan.
        """
        guidance = "\n\n[CONVERSATION GUIDANCE — AGENT X SUPPORT]"
        guidance += f"\nOFF-TOPIC DETECTED: Category={category}, Turn={off_topic_turn_count}"
        guidance += f"\nRESPONSE MODE: {mode}"

        if mode == 'ENGAGE':
            guidance += "\n\nINSTRUCTIONS (ENGAGE MODE — Be Relational):"
            guidance += "\n- The merchant went off-topic. This is NORMAL and GOOD for rapport."
            guidance += "\n- Engage naturally for this turn. Show genuine interest."
            guidance += "\n- Be a real person — react, comment, share a brief thought."
            guidance += "\n- Do NOT immediately bridge back to business. Let the moment breathe."
            guidance += "\n- Keep your response SHORT (1-2 sentences max on the off-topic part)."
            guidance += "\n- Do NOT claim specific knowledge or facts you don't have."
            guidance += "\n- Do NOT give advice on topics outside payments/business."

            # Category-specific engagement hints
            category_hints = {
                'sports': "React like a guy who follows sports casually — 'Oh man, that was a good one' or 'Yeah I caught some of that.' Don't pretend to be an expert.",
                'weather': "Relate briefly — everyone talks weather. 'Yeah it's been something out here too.' Keep it light.",
                'personal': "Show warmth — 'That's awesome' or 'Family first, I respect that.' Don't pry for details.",
                'entertainment': "Be casual — 'Oh yeah? I've heard good things about that' or 'I need to check that out.' Quick and genuine.",
                'food': "Everyone loves food talk — 'Man, that sounds good' or 'Can't go wrong with that.' Brief and real.",
                'humor': "Laugh with them. Be human. A quick 'Ha, that's good' goes a long way. Don't try to tell your own jokes.",
                'complaints_life': "Empathize briefly — 'I hear you, that stuff adds up' or 'Tell me about it.' Don't dwell.",
                'news_events': "Acknowledge without taking sides — 'Yeah, things are moving fast out there.' Stay neutral, stay brief.",
                'hobbies': "Show interest — 'That's cool, how long you been into that?' One question max, then let them answer naturally."
            }
            if category in category_hints:
                guidance += f"\n- HINT: {category_hints[category]}"

            # Sample prompts from rapport layer
            if self.rapport_prompts:
                sample = random.choice(self.rapport_prompts)
                guidance += f"\n- RAPPORT PROMPT EXAMPLE (adapt, don't copy): '{sample}'"

        elif mode == 'BRIDGE':
            guidance += "\n\nINSTRUCTIONS (BRIDGE MODE — Natural Transition):"
            guidance += f"\n- You've been off-topic for {off_topic_turn_count} turns. Time to guide back."
            guidance += "\n- Acknowledge what they said BRIEFLY (1 short sentence)."
            guidance += "\n- Then find a NATURAL seam to transition back to business."
            guidance += "\n- The transition should feel organic, NOT forced."
            guidance += "\n- Do NOT say 'Anyway...' or 'Back to business...' — too robotic."
            guidance += "\n- Use connection bridging: link their topic to a business concept naturally."

            # Bridge examples based on category
            bridge_hints = {
                'sports': "Bridge: 'Speaking of winning, I hate to see business owners leave money on the table...'",
                'weather': "Bridge: 'Yeah, one thing that doesn't change rain or shine — those processing statements...'",
                'personal': "Bridge: 'Family time is what it's all about. That's exactly why I focus on solutions that run themselves...'",
                'food': "Bridge: 'Man now I'm hungry. But real quick before I let you go...'",
                'complaints_life': "Bridge: 'Yeah, costs add up everywhere. That's actually why I'm calling — there's one cost I can usually cut...'",
                'hobbies': "Bridge: 'That's awesome. I won't keep you from it — just wanted to quickly ask about your processing setup...'",
                'entertainment': "Bridge: 'I'll have to check that out. But hey, real quick reason I called...'",
                'news_events': "Bridge: 'Yeah, everyone's watching their bottom line right now. That's exactly what I wanted to talk about...'",
                'humor': "Bridge: 'Ha, I needed that. Alright, let me not waste any more of your time — quick question about your processing...'"
            }
            if category in bridge_hints:
                guidance += f"\n- BRIDGE EXAMPLE (adapt naturally): {bridge_hints[category]}"

            # Mission pivot from rapport layer
            if self.mission_pivots:
                pivot = random.choice(self.mission_pivots)
                guidance += f"\n- PIVOT EXAMPLE (adapt, don't copy): '{pivot}'"

        elif mode == 'DEFLECT':
            guidance += "\n\nINSTRUCTIONS (DEFLECT MODE — Warm Redirection):"
            guidance += "\n- This topic is outside your lane. Do NOT engage with it."
            guidance += "\n- Do NOT share opinions on politics, religion, or give medical advice."
            guidance += "\n- Acknowledge briefly and warmly, then redirect."
            guidance += "\n- 'Ha, I'll leave that to the experts. Hey, quick question about your processing though...'"
            guidance += "\n- 'That's above my pay grade. I stick to saving people money on their credit card fees.'"
            guidance += "\n- Keep the deflection light, not awkward. Don't lecture them."
            guidance += "\n- NEVER judge or criticize their viewpoint."

        # Add safety rails to ALL modes
        guidance += "\n\nSAFETY RAILS (ALL MODES):"
        guidance += "\n- Stay in persona as Alan Jones, sales rep, at all times."
        guidance += "\n- Never claim expertise outside payments/merchant services."
        guidance += "\n- Never share specific facts (scores, stats, dates) — you might be wrong."
        guidance += "\n- Never argue or debate. Agree, empathize, or redirect."
        guidance += "\n- Your response should still be under 3 sentences total."
        guidance += "\n[/CONVERSATION GUIDANCE]"

        return guidance

    def process_turn(self, user_text: str, analysis: dict, context: dict) -> dict:
        """
        PRIORITY DISPATCH ENGINE — Agent X's instant multi-responsibility handler.

        Called by the relay server on every turn. Executes all Agent X
        responsibilities in strict priority order with a time budget.
        Each tier fires ONLY if conditions and budget allow, ensuring
        Agent X NEVER becomes the bottleneck in Alan's response pipeline.

        Priority ladder:
        ┌───────────────────────────────────────────────────────────┐
        │ P0 — SPEED OPTIMIZER         Always  │ Fights lag         │
        │ P1 — OFF-TOPIC CLASSIFIER    Always  │ Safety rail        │
        │ P2 — QPC TAP                 Always  │ Instant dict read  │
        │ P3 — IQ CORES (3-speed)      Budget  │ Intelligence       │
        │     └─ Guidance block assembly                            │
        │ P4 — LATENCY FILLER          Budget  │ Emergency only     │
        │ P5 — MANNERISM ADVISORY      Budget  │ Cosmetic / ambient │
        └───────────────────────────────────────────────────────────┘

        Budget gates:
        - P3 uses 2-turn IQ cache to skip expensive 5-core computation
        - P4 skips if brevity_level is 'tight' or 'emergency'
        - P5 skips if ANY brevity pressure exists (not 'normal')
        - If total Agent X elapsed > TIME_BUDGET_MS, remaining tiers skip

        Returns: enriched analysis dict with all Agent X intelligence.
        """
        import time as _time
        _t0 = _time.perf_counter()
        TIME_BUDGET_MS = 10  # Agent X total time allowance per turn

        # Track off-topic turns in context
        if 'off_topic_turn_count' not in context:
            context['off_topic_turn_count'] = 0

        dispatched = []  # Track what ran for diagnostic log

        # ═════════════════════════════════════════════════════════════
        # P0 — SPEED OPTIMIZER (ALWAYS — instant, fights lag at source)
        # Runs FIRST: its brevity_level gates P4 and P5 below.
        # This is the PRIMARY anti-lag weapon — makes Alan respond
        # shorter when lag is building, cutting LLM + TTS time.
        # ═════════════════════════════════════════════════════════════
        speed_opts = self._optimize_pipeline_speed(user_text, analysis, context)
        analysis['speed_optimizations'] = speed_opts
        brevity_level = speed_opts.get('brevity_level', 'normal')
        lag_momentum = speed_opts.get('lag_momentum', 0)
        dispatched.append(f"P0:SPEED({brevity_level},m{lag_momentum})")

        # ═════════════════════════════════════════════════════════════
        # P1 — OFF-TOPIC CLASSIFIER (ALWAYS — safety rail, fast)
        # Must run every turn — can't let Alan engage dangerous topics.
        # ═════════════════════════════════════════════════════════════
        is_off_topic, category = self.classify_off_topic(user_text)

        # If basic analysis already flagged it, honor that
        if analysis.get('is_off_topic') and not is_off_topic:
            is_off_topic = True
            category = 'general'

        analysis['is_off_topic'] = is_off_topic
        analysis['off_topic_category'] = category
        dispatched.append(f"P1:TOPIC({'OFF:' + category if is_off_topic else 'ON'})")

        # ═════════════════════════════════════════════════════════════
        # P2 — QPC TAP (ALWAYS — instant dict read from DeepLayer)
        # DeepLayer.step() already ran in the relay pipeline before us.
        # We just read the results — zero computation cost.
        # ═════════════════════════════════════════════════════════════
        qpc_intelligence = self._extract_qpc_intelligence(context)
        if qpc_intelligence:
            analysis['qpc_strategy'] = qpc_intelligence.get('strategy', 'natural')
            analysis['qpc_mode'] = qpc_intelligence.get('mode', 'OPENING')
            analysis['qpc_alternatives'] = qpc_intelligence.get('alternatives', [])
            analysis['qpc_strategy_score'] = qpc_intelligence.get('strategy_score', 0.0)
            analysis['qpc_continuum_emotion'] = qpc_intelligence.get('continuum_emotion', 0.0)
            analysis['qpc_continuum_ethics'] = qpc_intelligence.get('continuum_ethics', 0.0)
        dispatched.append("P2:QPC")

        # ═════════════════════════════════════════════════════════════
        # P3 — IQ CORES (BUDGET-GATED — 3-speed: cached → qpc_accel → fresh)
        # The 5-core orchestrator is Agent X's most expensive call.
        #
        # Speed ladder:
        #   1. CACHED    — Reuse from ≤2 turns ago if sentiment stable
        #   2. QPC_ACCEL — QPC already did reasoning + emotion tracking.
        #      Skip Core 1 (Reasoning) entirely — QPC branch scoring IS
        #      reasoning. Shortcut Core 5 (Emotion) — QPC continuum
        #      emotion field provides baseline. Only sentiment + governance.
        #   3. FRESH     — Full 5-core stack when no QPC data or low confidence
        #
        # Tim's insight: "The QPC was designed to improve IQ Core efficiency."
        # The QPC's multi-hypothesis branching DUPLICATES Core 1 reasoning.
        # When QPC confidence is high, that work is redundant.
        # ═════════════════════════════════════════════════════════════
        iq_intelligence = {}
        iq_source = 'none'

        if self.iq_cores_online and self.iq_orchestrator:
            current_sentiment = analysis.get('sentiment', 'neutral')
            turn_number = len(context.get('messages', []))

            # Check cache validity
            cache = self._iq_cache
            cache_hit = (
                cache is not None
                and turn_number - cache.get('turn', 0) <= 2
                and cache.get('sentiment') == current_sentiment
            )

            if cache_hit:
                # ── SPEED 1: CACHED — instant, no computation ──
                iq_intelligence = cache['data']
                iq_source = 'cached'
            elif (qpc_intelligence
                  and qpc_intelligence.get('strategy_score', 0) > 0.6):
                # ── SPEED 2: QPC-ACCELERATED — skip reasoning, shortcut emotion ──
                # QPC strategy_score > 0.6 means the QPC kernel is confident
                # in its multi-hypothesis branch selection. Its reasoning
                # output is MORE informed than Core 1's quick_assess because
                # QPC uses branch scoring + fluidic mode + continuum fields.
                try:
                    entity_id = context.get('caller_phone') or context.get('call_sid', 'unknown')
                    qpc_state_for_iq = {
                        'strategy': qpc_intelligence.get('strategy', 'natural'),
                        'strategy_score': qpc_intelligence.get('strategy_score', 0.0),
                        'continuum_emotion': qpc_intelligence.get('continuum_emotion', 0.0),
                        'continuum_ethics': qpc_intelligence.get('continuum_ethics', 0.0),
                        'mode': qpc_intelligence.get('mode', 'OPENING'),
                    }
                    iq_result = self.iq_orchestrator.process_turn_qpc_accelerated(
                        user_text, entity_id, context, qpc_state_for_iq
                    )
                    iq_intelligence = iq_result
                    iq_source = 'qpc_accel'

                    # Cache the accelerated result too — equally valid
                    self._iq_cache = {
                        'data': iq_result,
                        'turn': turn_number,
                        'sentiment': current_sentiment
                    }

                    # Governance still runs on accelerated path
                    if iq_intelligence.get('governance_flag'):
                        logger.warning(f"[AGENT X IQ] Governance flag (QPC-accel path)")

                except Exception as e:
                    logger.warning(f"[AGENT X IQ] QPC-accel failed, falling back to fresh: {e}")
                    iq_source = 'none'  # Will fall through to fresh below

            if iq_source == 'none':
                # ── SPEED 3: FRESH — full 5-core stack ──
                try:
                    entity_id = context.get('caller_phone') or context.get('call_sid', 'unknown')
                    iq_result = self.iq_orchestrator.process_conversation_turn(
                        user_text, entity_id, context
                    )
                    iq_intelligence = iq_result
                    iq_source = 'fresh'

                    # Store in cache for next 2 turns
                    self._iq_cache = {
                        'data': iq_result,
                        'turn': turn_number,
                        'sentiment': current_sentiment
                    }

                    # [IQ CORE 2: GOVERNANCE] Quick compliance check
                    compliant = self.iq_orchestrator.governance.quick_check(user_text)
                    if not compliant:
                        logger.warning(f"[AGENT X IQ] Governance flag on user input")
                        iq_intelligence['governance_flag'] = True

                except Exception as e:
                    logger.warning(f"[AGENT X IQ] Core processing failed, basic mode: {e}")

            # Feed IQ intelligence into analysis (any source)
            if iq_intelligence:
                analysis['iq_approach'] = iq_intelligence.get('approach', 'balanced_professional')
                analysis['iq_priority'] = iq_intelligence.get('priority', 'build_rapport')
                analysis['iq_signal_strength'] = iq_intelligence.get('signal_strength', 'neutral')
                analysis['iq_tone_recommendation'] = iq_intelligence.get('tone_recommendation', '')
                analysis['iq_energy_level'] = iq_intelligence.get('energy_level', 'moderate')
                analysis['iq_micro_expressions'] = iq_intelligence.get('micro_expressions', [])
                analysis['iq_trust_level'] = iq_intelligence.get('trust_level', 0.0)

        dispatched.append(f"P3:IQ({iq_source})")

        # ═════════════════════════════════════════════════════════════
        # GUIDANCE ASSEMBLY — Build output blocks from P1/P2/P3 results
        # This isn't a priority tier — it's the output formatter that
        # takes whatever P1-P3 produced and assembles the injection
        # block for Alan's LLM prompt.
        # ═════════════════════════════════════════════════════════════
        if is_off_topic:
            context['off_topic_turn_count'] = context.get('off_topic_turn_count', 0) + 1
            turn_count = context['off_topic_turn_count']

            mode = self.get_response_mode(category, turn_count)
            analysis['off_topic_mode'] = mode

            guidance = self.build_conversation_guidance(
                user_text, category, mode, turn_count, context
            )

            # Enrich with IQ + QPC intelligence if available
            if iq_intelligence:
                guidance = self._enrich_guidance_with_iq(guidance, iq_intelligence)

            qpc_block = self._build_qpc_guidance_block(qpc_intelligence)
            if qpc_block:
                guidance = guidance.replace("[/CONVERSATION GUIDANCE]",
                                           qpc_block + "\n[/CONVERSATION GUIDANCE]")

            context['conversation_guidance'] = guidance

            # [IQ CORE 3: LEARNING] Record off-topic interaction
            if self.iq_cores_online and self.iq_orchestrator:
                try:
                    self.iq_orchestrator.learning.learn(
                        "off_topic_response",
                        {"category": category, "mode": mode, "text": user_text[:100]},
                        f"mode_{mode.lower()}",
                        0.5
                    )
                except Exception:
                    pass

            logger.info(f"[AGENT X SUPPORT] Off-topic: cat={category}, turn={turn_count}, mode={mode}")
        else:
            # On-topic — reset counter, build IQ/QPC blocks
            if context.get('off_topic_turn_count', 0) > 0:
                logger.info(f"[AGENT X SUPPORT] Off-topic sequence ended after {context['off_topic_turn_count']} turns")

                if self.iq_cores_online and self.iq_orchestrator:
                    try:
                        self.iq_orchestrator.learning.learn(
                            "off_topic_response",
                            {"action": "bridge_back", "turns_off_topic": context['off_topic_turn_count']},
                            "success_bridge",
                            0.8
                        )
                    except Exception:
                        pass

            context['off_topic_turn_count'] = 0
            context['conversation_guidance'] = None
            analysis['off_topic_mode'] = None
            analysis['off_topic_category'] = None

            combined_block = ''
            if iq_intelligence and iq_intelligence.get('approach'):
                iq_context_block = self._build_iq_context_block(iq_intelligence)
                if iq_context_block:
                    combined_block += iq_context_block

            qpc_block = self._build_qpc_guidance_block(qpc_intelligence)
            if qpc_block:
                combined_block += qpc_block

            if combined_block:
                context['conversation_guidance'] = combined_block

        # ═════════════════════════════════════════════════════════════
        # P4 — LATENCY FILLER (BUDGET-GATED — emergency only)
        # Skips when contradictory: if speed optimizer told Alan to be
        # SHORT, adding a filler would fight that directive.
        # Also skips if Agent X has spent too long already.
        # ═════════════════════════════════════════════════════════════
        elapsed_ms = 1000 * (_time.perf_counter() - _t0)
        latency_filler = None

        if brevity_level in ('tight', 'emergency'):
            # SHORT + filler = contradictory. Speed wins.
            dispatched.append("P4:SKIP(brevity)")
        elif elapsed_ms > TIME_BUDGET_MS * 0.8:
            dispatched.append("P4:SKIP(budget)")
        else:
            latency_filler = self._assess_latency_risk(user_text, analysis, context)
            if latency_filler:
                filler_block = self._build_mannerism_guidance_block(latency_filler)
                analysis['latency_filler'] = latency_filler
                if context.get('conversation_guidance'):
                    existing = context['conversation_guidance']
                    if '[/CONVERSATION GUIDANCE]' in existing:
                        context['conversation_guidance'] = existing.replace(
                            '[/CONVERSATION GUIDANCE]',
                            filler_block + '\n[/CONVERSATION GUIDANCE]'
                        )
                    else:
                        context['conversation_guidance'] = existing + filler_block
                else:
                    context['conversation_guidance'] = filler_block
                dispatched.append(f"P4:FILLER({latency_filler['type']})")
            else:
                dispatched.append("P4:CLEAR")

        if latency_filler is None:
            analysis['latency_filler'] = None

        # ═════════════════════════════════════════════════════════════
        # P5 — MANNERISM ADVISORY (LOWEST PRIORITY — cosmetic)
        # Skips if: latency filler already fired (avoid double-inject),
        #           ANY brevity pressure (mannerism is luxury under lag),
        #           time budget fully spent.
        # When Agent X is fighting lag, mannerisms are the first cut.
        # ═════════════════════════════════════════════════════════════
        elapsed_ms = 1000 * (_time.perf_counter() - _t0)
        mannerism = None

        if latency_filler:
            dispatched.append("P5:SKIP(filler)")
        elif brevity_level != 'normal':
            # Any speed pressure = mannerism is a luxury we cut
            dispatched.append("P5:SKIP(brevity)")
        elif elapsed_ms > TIME_BUDGET_MS:
            dispatched.append("P5:SKIP(budget)")
        else:
            mannerism = self._analyze_human_mannerism(user_text, analysis, context, iq_intelligence)
            if mannerism:
                mannerism_block = self._build_mannerism_guidance_block(mannerism)
                analysis['mannerism_advisory'] = mannerism
                if context.get('conversation_guidance'):
                    existing = context['conversation_guidance']
                    if '[/CONVERSATION GUIDANCE]' in existing:
                        context['conversation_guidance'] = existing.replace(
                            '[/CONVERSATION GUIDANCE]',
                            mannerism_block + '\n[/CONVERSATION GUIDANCE]'
                        )
                    else:
                        context['conversation_guidance'] = existing + mannerism_block
                else:
                    context['conversation_guidance'] = mannerism_block
                dispatched.append(f"P5:MANNER({mannerism['type']})")
            else:
                dispatched.append("P5:CLEAR")

        if not mannerism:
            analysis['mannerism_advisory'] = None

        # Final output
        analysis['iq_intelligence'] = iq_intelligence
        analysis['qpc_intelligence'] = qpc_intelligence

        # ═════════════════════════════════════════════════════════════
        # PVE — PROMPT VELOCITY ENGINE (post-assembly compression)
        # Compresses all guidance blocks assembled above to minimize
        # LLM system prompt tokens. Every token saved = ~0.5ms faster
        # first-token latency. Under brevity pressure, strips aggressively.
        #
        # Tim's insight: "being fast is one of the magical keys."
        # Speed isn't just about code — it's about how many tokens
        # the LLM has to process before it starts generating.
        # ═════════════════════════════════════════════════════════════
        tokens_saved = self._apply_prompt_velocity(context, brevity_level)
        if tokens_saved > 0:
            dispatched.append(f"PVE:-{tokens_saved}tok")
        else:
            dispatched.append("PVE:0")

        # ═════════════════════════════════════════════════════════════
        # DISPATCH DIAGNOSTIC — One-line performance log per turn
        # Shows exactly what Agent X did, what it skipped, and how fast.
        # Example: "[AGENT X DISPATCH] 1.3ms — P0:SPEED(normal,m0) | P1:TOPIC(ON) |
        #           P2:QPC | P3:IQ(cached) | P4:CLEAR | P5:MANNER(THROAT_CLEAR) | PVE:-85tok"
        # ═════════════════════════════════════════════════════════════
        total_ms = 1000 * (_time.perf_counter() - _t0)
        dispatch_summary = ' | '.join(dispatched)
        logger.info(f"[AGENT X DISPATCH] {total_ms:.1f}ms — {dispatch_summary}")

        return analysis

    # =================================================================
    # [PROMPT VELOCITY ENGINE (PVE)]
    # Compresses prompt tokens for faster LLM first-token latency
    #
    # The math: Every 100 tokens in the system prompt = ~50ms TTFT.
    # A 2000-token system prompt = ~1000ms before Alan starts thinking.
    # By compressing verbose blocks, stripping defaults, and using
    # compact notation, we claw back 100-300ms per turn.
    #
    # Tim: "being fast is one of the magical keys to making this all
    # work together. it has to flow language just as a human does."
    # =================================================================

    def _apply_prompt_velocity(self, context: dict, brevity_level: str) -> int:
        """
        Post-assembly prompt compression. Runs AFTER P0-P5 have assembled
        all guidance blocks in context['conversation_guidance'].

        Compression tiers (based on brevity_level from Speed Optimizer):
        1. ALWAYS — Strip verbose block headers, redundant labels, padding
        2. CONCISE — Shorten instruction text, remove psychology notes
        3. TIGHT — Strip mannerism/filler blocks entirely, compact IQ/QPC
        4. EMERGENCY — Strip EVERYTHING except core off-topic redirect

        Returns: estimated tokens saved
        """
        guidance = context.get('conversation_guidance')
        if not guidance:
            return 0

        original_len = len(guidance)

        # ── TIER 1: ALWAYS — Strip padding and redundant formatting ──
        # Remove redundant section markers that the LLM doesn't need
        guidance = guidance.replace('[/CONVERSATION GUIDANCE]', '')
        guidance = guidance.replace('[/AGENT X — HUMAN MANNERISM ADVISORY]', '')
        guidance = guidance.replace('[/AGENT X — IQ INTELLIGENCE]', '')
        guidance = guidance.replace('[/AGENT X — QPC STRATEGY INTELLIGENCE]', '')
        guidance = guidance.replace('[/RESPONSE SPEED]', '')
        # Compact block headers — the LLM reads content, not formatting
        guidance = guidance.replace('[AGENT X — HUMAN MANNERISM ADVISORY]', '[MANNERISM]')
        guidance = guidance.replace('[AGENT X — IQ INTELLIGENCE]', '[IQ]')
        guidance = guidance.replace('[AGENT X — QPC STRATEGY INTELLIGENCE]', '[QPC]')
        guidance = guidance.replace('[CONVERSATION GUIDANCE — AGENT X SUPPORT]', '[GUIDE]')
        guidance = guidance.replace('[RESPONSE SPEED — AGENT X]', '[SPEED]')
        guidance = guidance.replace('[IQ CORE INTELLIGENCE]', '[IQ-CORE]')
        # Remove verbose labels
        guidance = guidance.replace('- NOTE: This is ADVISORY. Use it if it feels natural. Skip if it doesn\'t fit.', '')
        guidance = guidance.replace('- Priority: LOW', '')
        guidance = guidance.replace('- Priority: MEDIUM', '')

        # ── TIER 2: CONCISE — Shorten verbose instructions ──
        if brevity_level in ('concise', 'tight', 'emergency'):
            # Strip psychology explanations — Alan doesn't need the WHY
            import re as _re
            guidance = _re.sub(r'- Psychology:.*?\n', '', guidance)
            # Strip trigger labels — internal metadata, not for LLM
            guidance = _re.sub(r'- Trigger:.*?\n', '', guidance)
            # Compact the verbose engagement/bridge instructions
            guidance = guidance.replace('INSTRUCTIONS (ENGAGE MODE — Be Relational):', 'ENGAGE:')
            guidance = guidance.replace('INSTRUCTIONS (BRIDGE MODE — Natural Transition):', 'BRIDGE:')
            guidance = guidance.replace('INSTRUCTIONS (DEFLECT MODE — Warm Redirection):', 'DEFLECT:')
            # Strip safety rails block under pressure — system prompt has them
            guidance = _re.sub(r'\nSAFETY RAILS \(ALL MODES\):.*?(?=\n\[|\Z)', '', guidance, flags=_re.DOTALL)

        # ── TIER 3: TIGHT — Strip cosmetics, compact intelligence ──
        if brevity_level in ('tight', 'emergency'):
            # Remove mannerism advisory entirely — cosmetic luxury under lag
            guidance = _re.sub(r'\n*\[MANNERISM\].*?(?=\n\[|\Z)', '', guidance, flags=_re.DOTALL)
            # Remove latency filler details — just the core instruction
            guidance = _re.sub(r'- Type: LATENCY_\w+\n', '', guidance)
            # Compact IQ block to one-liner
            iq_match = _re.search(r'\[IQ\](.*?)(?=\n\[|\Z)', guidance, _re.DOTALL)
            if iq_match:
                iq_lines = [l.strip() for l in iq_match.group(1).strip().split('\n') if l.strip().startswith('-')]
                if iq_lines:
                    compact_iq = '\n[IQ] ' + '; '.join(l.lstrip('- ') for l in iq_lines[:3])
                    guidance = guidance[:iq_match.start()] + compact_iq + guidance[iq_match.end():]

        # ── TIER 4: EMERGENCY — Nuclear compression ──
        if brevity_level == 'emergency':
            # Strip everything except the speed directive and off-topic redirect
            # Under emergency, Alan just needs to know: be short, stay on topic
            speed_match = _re.search(r'\[SPEED\](.*?)(?=\n\[|\Z)', guidance, _re.DOTALL)
            guide_match = _re.search(r'\[GUIDE\](.*?)RESPONSE MODE: (\w+)', guidance, _re.DOTALL)

            compressed = ''
            if speed_match:
                compressed += '\n[SPEED] ONE sentence. Direct.\n'
            if guide_match:
                mode = guide_match.group(2)
                compressed += f'\n[TOPIC] Mode: {mode}. Keep it brief.\n'
            guidance = compressed if compressed else guidance

        # ── Clean up whitespace bloat ──
        while '\n\n\n' in guidance:
            guidance = guidance.replace('\n\n\n', '\n\n')
        guidance = guidance.strip()

        if guidance:
            context['conversation_guidance'] = guidance
        else:
            context['conversation_guidance'] = None

        # Estimate tokens saved (rough: 1 token ≈ 4 chars)
        new_len = len(guidance) if guidance else 0
        chars_saved = original_len - new_len
        tokens_saved = max(0, chars_saved // 4)

        if tokens_saved > 10:
            logger.info(f"[PVE] Compressed guidance: {original_len}→{new_len} chars (~{tokens_saved} tokens saved, level={brevity_level})")

        return tokens_saved

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Quick token count estimate. 1 token ≈ 4 characters for English."""
        return len(text) // 4 if text else 0

    # =================================================================
    # [PIPELINE SPEED OPTIMIZER]
    # Proactive lag reduction — fights latency at the source
    # =================================================================

    def _optimize_pipeline_speed(self, user_text: str, analysis: dict,
                                   context: dict) -> dict:
        """
        Proactive pipeline speed optimization. Runs EVERY turn.
        
        This is the PRIMARY anti-lag strategy. Instead of covering lag
        with filler words (which you can't do every turn), this actually
        REDUCES lag by controlling what the LLM generates.
        
        The math:
        - Alan responds in 1 sentence (20 tokens) → ~300ms LLM + ~200ms TTS = 500ms
        - Alan responds in 3 sentences (80 tokens) → ~900ms LLM + ~600ms TTS = 1500ms
        - Difference: 1 FULL SECOND saved just by being brief
        
        Strategies:
        1. LAG MOMENTUM — Track consecutive slow turns. One slow turn is
           normal. Three in a row = systemic issue that needs intervention.
        2. BREVITY SIGNAL — When lag builds, inject guidance telling Alan
           to keep it SHORT. One sentence. Direct and punchy. This cuts
           output tokens, which cuts both LLM generation and TTS time.
        3. RECOVERY TRACKING — When lag resolves, back off gracefully
           so Alan can resume normal response length.
        
        Returns: dict with optimizations applied
        """
        optimizations = {
            'brevity_injected': False,
            'lag_momentum': 0,
            'brevity_level': 'normal'
        }

        # ── LAG MOMENTUM: Count consecutive slow turns ──
        last_latency = context.get('_last_turn_latency_ms', 0)
        lag_momentum = context.get('_agentx_lag_momentum', 0)

        if last_latency > 3000:
            # Severe lag — momentum jumps
            lag_momentum = min(lag_momentum + 2, 5)
        elif last_latency > 2000:
            # Noticeable lag — momentum builds
            lag_momentum = min(lag_momentum + 1, 5)
        elif last_latency > 1200:
            # Borderline — hold steady, don't escalate
            lag_momentum = lag_momentum
        else:
            # Fast response — cool down
            lag_momentum = max(0, lag_momentum - 1)

        context['_agentx_lag_momentum'] = lag_momentum
        optimizations['lag_momentum'] = lag_momentum

        # ── BREVITY SIGNAL: Scale response length based on lag severity ──
        # Level 0 (momentum 0-1): No intervention — Alan talks normally
        # Level 1 (momentum 2):   Gentle nudge — "keep it concise"
        # Level 2 (momentum 3+):  Strong signal — "ONE sentence, be direct"
        # Level 3 (single >4s):   Emergency — "SHORT. One line."

        brevity_level = 'normal'
        brevity_block = ''

        if last_latency > 4000:
            # Emergency: single turn was brutally slow
            brevity_level = 'emergency'
            brevity_block = (
                "\n\n[RESPONSE SPEED — AGENT X]\n"
                "Keep your response to ONE short sentence. Be direct. "
                "You sound more confident and professional when you're concise. "
                "If they want details, they'll ask — then you can expand.\n"
                "[/RESPONSE SPEED]"
            )
        elif lag_momentum >= 3:
            # Sustained lag — strong intervention
            brevity_level = 'tight'
            brevity_block = (
                "\n\n[RESPONSE SPEED — AGENT X]\n"
                "Keep your response to ONE sentence maximum. Short, punchy, direct. "
                "A real closer doesn't ramble — they hit hard with fewer words. "
                "Save the detail for when they ask follow-up questions.\n"
                "[/RESPONSE SPEED]"
            )
        elif lag_momentum >= 2:
            # Building lag — gentle nudge
            brevity_level = 'concise'
            brevity_block = (
                "\n\n[RESPONSE SPEED — AGENT X]\n"
                "Keep your response concise — two sentences max. "
                "Tight answers show confidence and respect for their time.\n"
                "[/RESPONSE SPEED]"
            )

        if brevity_block:
            if context.get('conversation_guidance'):
                context['conversation_guidance'] += brevity_block
            else:
                context['conversation_guidance'] = brevity_block
            optimizations['brevity_injected'] = True
            logger.info(
                f"[AGENT X SPEED] Brevity signal: level={brevity_level}, "
                f"momentum={lag_momentum}, last_ms={last_latency:.0f}"
            )

        optimizations['brevity_level'] = brevity_level
        return optimizations

    # =================================================================
    # [LATENCY MASKING ENGINE]
    # EMERGENCY filler — rare, only for severe sustained lag
    # The SPEED OPTIMIZER above is the primary anti-lag strategy.
    # This is the safety net when optimization alone isn't enough.
    # =================================================================

    def _assess_latency_risk(self, user_text: str, analysis: dict,
                              context: dict) -> Optional[dict]:
        """
        EMERGENCY latency filler — fires RARELY, only when lag is severe.
        
        The pipeline speed optimizer (above) handles most lag by making
        Alan respond shorter. This filler is the LAST RESORT for when:
        - Multiple consecutive turns have been slow (sustained lag)
        - A single turn is extremely slow (>4 seconds)
        - Complex questions compound with heavy context
        
        You can't give Alan a filler on every answer — that would be
        just as suspicious as silence. This fires maybe 1 in 8-10 turns
        AT MOST, and only when conditions truly warrant it.
        
        Signals checked:
        1. Previous turn was slow (>2500ms) — pattern likely to repeat
        2. Long/complex user message (>35 words) — LLM needs more time
        3. Heavy context (many messages) — bigger prompt = slower inference
        4. Complex question with multiple parts — requires more generation
        5. Current pipeline already slow (time since pipeline_t0 > 1000ms)
        6. Lag momentum (from speed optimizer) — sustained lag indicator
        
        Returns: dict with type, instruction, trigger, psychology — or None
        """
        import time as _time

        # ── Gate: If speed optimizer isn't seeing sustained lag, don't even check ──
        lag_momentum = context.get('_agentx_lag_momentum', 0)
        if lag_momentum < 1:
            return None  # No lag pattern — no need for filler

        # ── Signal 1: Previous turn latency (tighter threshold) ──
        last_latency = context.get('_last_turn_latency_ms', 0)
        prev_was_slow = last_latency > 2500  # >2.5 seconds (was 2000)
        prev_was_very_slow = last_latency > 4000  # >4s = critical (was 3500)

        # ── Signal 2: Long/complex user input (tighter threshold) ──
        word_count = len(user_text.split())
        long_input = word_count > 35  # (was 30)
        very_long_input = word_count > 50

        # ── Signal 3: Heavy conversation context ──
        message_count = len(context.get('messages', []))
        heavy_context = message_count > 15  # (was 12)

        # ── Signal 4: Complex question detection ──
        text_lower = user_text.lower()
        complex_markers = [
            'can you explain', 'tell me about', 'walk me through',
            'what exactly', 'how does that work', 'what do you mean',
            'break it down', 'give me the details', 'run that by me',
            'what are the', 'compare', 'difference between'
        ]
        complex_question = any(m in text_lower for m in complex_markers)

        # ── Signal 5: Current pipeline elapsed time (tighter threshold) ──
        pipeline_start = context.get('_pipeline_start_time')
        pipeline_slow = False
        if pipeline_start:
            elapsed_ms = 1000 * (_time.time() - pipeline_start)
            pipeline_slow = elapsed_ms > 1000  # >1s already (was 800ms)

        # ── Signal 6: Lag momentum from speed optimizer ──
        high_momentum = lag_momentum >= 3

        # ── Risk scoring (tighter — needs MORE signals to fire) ──
        risk_score = 0
        if prev_was_very_slow:
            risk_score += 3
        elif prev_was_slow:
            risk_score += 2
        if very_long_input:
            risk_score += 2
        elif long_input:
            risk_score += 1
        if heavy_context:
            risk_score += 1
        if complex_question:
            risk_score += 1
        if pipeline_slow:
            risk_score += 1
        if high_momentum:
            risk_score += 1

        # ── Decision: risk >= 4 AND momentum >= 2 (was risk >= 3) ──
        # Filler only fires on sustained + severe lag, never on one-off
        if risk_score < 4:
            return None
        if lag_momentum < 2 and not prev_was_very_slow:
            return None  # Need sustained lag OR extreme single-turn spike

        # ── Don't fire if we did a latency filler recently (3-turn gap) ──
        last_filler_turn = context.get('_last_latency_filler_turn', -10)
        turn_count = len(context.get('messages', []))
        if turn_count - last_filler_turn <= 3:
            return None  # 3-turn cooldown (was 1) — fillers must be RARE

        # ── Choose the right filler based on context ──
        fillers = []

        if complex_question:
            fillers.append({
                'type': 'LATENCY_THINKING',
                'instruction': (
                    'The merchant asked something complex. START your response with '
                    'a brief thinking sound — "That\'s a great question... so" or '
                    '"Hmm, yeah, so" or "Let me think about that for a sec... okay so" '
                    'THEN give your answer. The thinking sound fills the processing '
                    'gap NATURALLY. A real person needs a beat for complex questions. '
                    'Keep the filler under 5 words, then flow into your real answer.'
                ),
                'trigger': 'latency_complex_question',
                'psychology': 'Processing filler — silence on complex questions = AI, thinking sounds = human',
                'priority': 'HIGH'
            })

        if prev_was_slow or pipeline_slow:
            fillers.append({
                'type': 'LATENCY_VERBAL_BRIDGE',
                'instruction': (
                    'There may be a brief processing moment. START your response '
                    'with a natural verbal bridge — "Yeah, so..." or "Right, so '
                    'here\'s the thing —" or "Okay so..." or just "So..." '
                    'This bridge word comes out IMMEDIATELY and fills any gap '
                    'while you formulate the rest. It\'s what real people do '
                    'when they start talking before their full thought is formed. '
                    'ONE bridge word/phrase, then your actual content.'
                ),
                'trigger': 'latency_processing_delay',
                'psychology': 'Verbal bridge — humans start talking before thinking is complete',
                'priority': 'HIGH'
            })

        if long_input or heavy_context:
            fillers.append({
                'type': 'LATENCY_PROCESSING_SOUND',
                'instruction': (
                    'The conversation has a lot going on. START your response with '
                    'a brief processing acknowledgment — "Okay, yeah..." or '
                    '"Alright, so..." or "Mm, okay..." or a quick inhale sound '
                    'before speaking. This says "I\'m taking in everything you said" '
                    'and covers any processing gap. Keep it to 2-3 words max, '
                    'then deliver your actual response.'
                ),
                'trigger': 'latency_heavy_processing',
                'psychology': 'Acknowledgment filler — covers processing time while signaling active listening',
                'priority': 'MEDIUM'
            })

        # Always have a generic fallback
        fillers.append({
            'type': 'LATENCY_FILLER',
            'instruction': (
                'Start your response with a quick, natural filler sound — '
                '"Um" or "So" or "Yeah" or "Mm-hmm, so" — just ONE word '
                'before your actual response. This eliminates dead air at '
                'the start of your reply. Don\'t overthink it — just a tiny '
                'verbal tic that a real person would make while their brain '
                'catches up to their mouth. One syllable, max two.'
            ),
            'trigger': 'latency_general',
            'psychology': 'Dead air elimination — any sound is better than AI silence',
            'priority': 'MEDIUM'
        })

        # Pick the most contextually appropriate filler
        filler = fillers[0]  # First match is most specific

        # Record that we fired a latency filler
        context['_last_latency_filler_turn'] = turn_count

        return filler

    # =================================================================
    # [HUMAN MANNERISM ADVISORY ENGINE]
    # Psychology-driven micro-behavior guidance for Alan
    # =================================================================

    def _analyze_human_mannerism(self, user_text: str, analysis: dict,
                                  context: dict, iq_intelligence: dict) -> Optional[dict]:
        """
        Psychological analysis of when Alan should inject human micro-behaviors.
        
        A real person on the phone coughs, laughs, sniffles, clears their throat,
        says "um", sighs, takes audible breaths. An AI NEVER does this.
        These micro-behaviors are the #1 signal that separates human from machine.
        
        Agent X uses conversation dynamics to advise WHEN and WHAT mannerism
        would be natural. Not random — psychologically motivated.
        
        Frequency: ~1 in 4-5 turns gets a mannerism suggestion. More often
        feels performative, less often wastes the opportunity.
        
        Returns: dict with type, instruction, trigger, psychology — or None
        """
        turn_count = len(context.get('messages', []))
        last_mannerism_turn = context.get('_last_mannerism_turn', 0)
        sentiment = analysis.get('sentiment', 'neutral')
        energy = iq_intelligence.get('energy_level', 'moderate')
        trust = iq_intelligence.get('trust_level', 0.0)
        text_lower = user_text.lower().strip()

        # ── Frequency governor: don't overdo it ──
        # Allow one in first 3 turns for early rapport, then space them out
        if turn_count <= 3:
            min_gap = 2  # Can fire on turn 1, then again on turn 3
        else:
            min_gap = 3  # Every 3-4 turns after that

        turns_since_last = turn_count - last_mannerism_turn
        if turns_since_last < min_gap and last_mannerism_turn > 0:
            return None

        mannerism = None

        # ── TRIGGER 1: Merchant sneezed/coughed → "Bless you" / "You good?" ──
        sneeze_cough_patterns = [
            'achoo', 'sneez', 'cough', 'excuse me', 'sorry about that',
            '*cough*', '*sneeze*', 'pardon me', 'clearing my throat'
        ]
        if any(p in text_lower for p in sneeze_cough_patterns):
            mannerism = {
                'type': 'BLESS_YOU',
                'instruction': (
                    'The merchant just coughed or sneezed. Say "Bless you" or '
                    '"You good?" or "Gesundheit" NATURALLY before continuing. '
                    'A real person ALWAYS acknowledges this — it\'s automatic. '
                    'Keep it quick and warm, then continue your thought.'
                ),
                'trigger': 'merchant_sneeze_cough',
                'psychology': 'Social reflex — ignoring a sneeze is INHUMAN',
                'priority': 'HIGH'
            }

        # ── TRIGGER 2: Merchant told a joke / something funny → Laugh ──
        elif analysis.get('sentiment') == 'positive' and (
            any(w in text_lower for w in ['haha', 'lol', 'funny', 'joke', 'hilarious',
                                           'kidding', 'messing with', 'just playing',
                                           'crack me up', 'that\'s a good one'])
            or text_lower.endswith('haha') or text_lower.endswith('lol')
        ):
            mannerism = {
                'type': 'LAUGH',
                'instruction': (
                    'The merchant said something funny or is joking around. '
                    'Start your response with a genuine short laugh — "Ha!" or '
                    '"Haha, that\'s good" or just "Ha, man..." THEN continue. '
                    'Don\'t force it. A real person laughs WITH people. '
                    'Keep the laugh SHORT — one syllable, maybe two.'
                ),
                'trigger': 'merchant_humor',
                'psychology': 'Mirror neurons — laughing together builds instant rapport',
                'priority': 'HIGH'
            }

        # ── TRIGGER 3: Heavy/emotional moment → Empathy sigh ──
        elif sentiment == 'negative' and energy in ('low', 'stressed'):
            emotional_words = ['tough', 'hard', 'struggling', 'difficult', 'lost',
                             'passed away', 'died', 'sick', 'cancer', 'fired',
                             'laid off', 'divorce', 'closing down', 'going under']
            if any(w in text_lower for w in emotional_words):
                mannerism = {
                    'type': 'EMPATHY_SIGH',
                    'instruction': (
                        'The merchant shared something heavy or emotional. '
                        'Start with a brief empathetic sigh or pause — "Man..." or '
                        '"Ah, yeah..." or just a quiet "...wow." before responding. '
                        'This is NOT a sales opportunity. Show humanity first. '
                        'Don\'t rush past it. Let the weight land, then respond gently.'
                    ),
                    'trigger': 'emotional_disclosure',
                    'psychology': 'Empathetic resonance — acknowledging pain builds deep trust',
                    'priority': 'HIGH'
                }

        # ── TRIGGER 4: Long merchant monologue → Thinking sound ──
        elif len(user_text.split()) > 40:
            mannerism = {
                'type': 'THINKING_SOUND',
                'instruction': (
                    'The merchant just said a LOT. Before responding, use a '
                    'brief thinking sound — "Hmm..." or "Yeah... okay..." or '
                    '"Alright, so..." This shows you\'re PROCESSING what they said, '
                    'not just generating a response instantly. A real person needs '
                    'a beat to take in a long statement. Don\'t skip straight to your point.'
                ),
                'trigger': 'long_monologue',
                'psychology': 'Processing time — instant responses feel robotic',
                'priority': 'MEDIUM'
            }

        # ── TRIGGER 5: Conversation going well + rapport built → Casual laugh ──
        elif trust > 0.6 and sentiment == 'positive' and turns_since_last >= 4:
            mannerism = {
                'type': 'CASUAL_CHUCKLE',
                'instruction': (
                    'Rapport is strong — things are going well. Throw in a casual, '
                    'warm micro-laugh at a natural point. "Ha, yeah exactly" or '
                    '"Right, right" with a light laugh tone. This is the sound of '
                    'two people who are comfortable with each other. Don\'t force it. '
                    'If your response doesn\'t have a natural laugh point, skip it.'
                ),
                'trigger': 'rapport_comfort',
                'psychology': 'Affiliation signal — relaxed laughter = "we\'re on the same team"',
                'priority': 'LOW'
            }

        # ── TRIGGER 6: About to deliver important info → Throat clear ──
        elif analysis.get('pitch_intent') and turn_count > 4 and turns_since_last >= 3:
            mannerism = {
                'type': 'THROAT_CLEAR',
                'instruction': (
                    'You\'re about to deliver key information or a pitch point. '
                    'A subtle throat clear or "So, uh —" before the important part '
                    'signals that what comes next MATTERS. It\'s a human verbal cue '
                    'that says "pay attention, I\'m shifting gears." Keep it subtle. '
                    'Just a brief "Alright so —" or "Yeah so look —" works.'
                ),
                'trigger': 'pre_pitch_transition',
                'psychology': 'Attention anchor — the clear signals importance',
                'priority': 'MEDIUM'
            }

        # ── TRIGGER 7: Early in call, first few turns → Natural warm-up ──
        elif turn_count <= 2 and not mannerism:
            warmup_options = [
                {
                    'type': 'SNIFFLE',
                    'instruction': (
                        'Early in the call — throw in a quick, barely-noticeable sniffle '
                        'or throat clear before your first real sentence. Just a tiny human '
                        'sound — "*sniff* So hey, I was..." or a subtle "Ahem, so —". '
                        'This immediately registers as HUMAN at the subconscious level. '
                        'The merchant\'s brain hears it and thinks "real person" before '
                        'they even process the words.'
                    ),
                    'trigger': 'call_opening_humanity',
                    'psychology': 'Subconscious humanity signal — breaks the AI suspicion barrier',
                    'priority': 'MEDIUM'
                },
                {
                    'type': 'VERBAL_FILLER',
                    'instruction': (
                        'Use a natural verbal filler in your opening — "Um, hey" or '
                        '"So, uh, hey" or "Yeah so" before your main point. '
                        'Perfect speakers are suspicious. Real people use fillers '
                        'especially at the start of calls when they\'re settling in. '
                        'Don\'t overdo it — one filler word, max two.'
                    ),
                    'trigger': 'call_opening_humanity',
                    'psychology': 'Imperfection signal — too-smooth openings trigger AI detection',
                    'priority': 'MEDIUM'
                }
            ]
            mannerism = random.choice(warmup_options)

        # ── TRIGGER 8: Merchant asked a hard question → Buy thinking time ──
        elif analysis.get('intent') in ('objection', 'question') and len(user_text.split()) > 10:
            if turns_since_last >= 3 and random.random() < 0.5:
                mannerism = {
                    'type': 'THINKING_PAUSE',
                    'instruction': (
                        'The merchant asked something that requires thought. '
                        'Start with "That\'s... yeah, that\'s a fair question" or '
                        '"Hmm, let me think about that for a sec" or just '
                        '"Yeah... so..." A real person doesn\'t have instant answers '
                        'to hard questions. The pause makes your answer feel CONSIDERED '
                        'not SCRIPTED.'
                    ),
                    'trigger': 'hard_question',
                    'psychology': 'Authenticity through imperfection — instant answers = scripted',
                    'priority': 'MEDIUM'
                }

        # ── TRIGGER 10: Merchant frustration/irritation → Alan softens ──
        # From psychology: angry/irritated mannerisms include curt replies,
        # sharp exhales, snapping. Alan should de-escalate with vulnerability.
        elif sentiment == 'negative' and energy in ('high', 'stressed'):
            irritation_patterns = [
                'whatever', 'not interested', 'stop calling', 'waste of time',
                'get to the point', 'hurry up', 'look man', 'listen buddy',
                'come on', 'seriously', 'enough', 'ridiculous', 'annoying'
            ]
            if any(p in text_lower for p in irritation_patterns):
                soften_options = [
                    {
                        'type': 'SELF_DEPRECATING',
                        'instruction': (
                            'The merchant sounds frustrated or irritated. Soften with a '
                            'brief self-deprecating moment — "Ha, yeah, sorry I\'m '
                            'probably not explaining this well" or "Fair enough, I know '
                            'I jumped in kinda fast." This LOWERS the temperature. '
                            'A real person reads irritation and adjusts — they don\'t '
                            'just power through their script. Show you HEARD their frustration.'
                        ),
                        'trigger': 'merchant_frustration',
                        'psychology': 'De-escalation through vulnerability — softness disarms aggression',
                        'priority': 'HIGH'
                    },
                    {
                        'type': 'APOLOGETIC_PAUSE',
                        'instruction': (
                            'The merchant is irritated. Take a beat — "Yeah... no, '
                            'you\'re right, let me —" or "Okay, fair, I hear you." '
                            'Then SLOW DOWN your delivery. Apologizing briefly shows '
                            'emotional intelligence. Don\'t grovel — just acknowledge.'
                        ),
                        'trigger': 'merchant_frustration',
                        'psychology': 'Emotional reading — failing to notice irritation is robotic',
                        'priority': 'HIGH'
                    }
                ]
                mannerism = random.choice(soften_options)

        # ── TRIGGER 11: Merchant agreeing / buy signals → Micro-excitement ──
        # From psychology: happy/excited mannerisms — laughing freely, gasping,
        # rubbing hands, talking animatedly. Alan should mirror the positive energy.
        elif sentiment == 'positive' and analysis.get('intent') == 'agreement':
            if trust > 0.4 and turns_since_last >= 3:
                excitement_options = [
                    {
                        'type': 'GENUINE_EXCITEMENT',
                        'instruction': (
                            'The merchant is agreeing or showing buy signals! Let '
                            'genuine excitement leak through — "Oh nice, yeah!" or '
                            '"Ha, that\'s awesome" or "Right? Right." A real sales '
                            'person gets VISIBLY happy when a deal is coming together. '
                            'Don\'t celebrate too early — just a quick energy bump '
                            'that says you\'re a human who cares about the outcome.'
                        ),
                        'trigger': 'agreement_momentum',
                        'psychology': 'Genuine enthusiasm is contagious — merchant mirrors your energy up',
                        'priority': 'MEDIUM'
                    },
                    {
                        'type': 'EAGER_PACE',
                        'instruction': (
                            'The merchant is on board — naturally speed up SLIGHTLY '
                            'for one sentence like you\'re excited, then catch yourself '
                            'and slow back down. "Yeah so we\'d basically — sorry, ha, '
                            'I\'m getting ahead of myself." This shows authentic '
                            'enthusiasm that you\'re trying to contain. Very human.'
                        ),
                        'trigger': 'agreement_momentum',
                        'psychology': 'Controlled excitement leak — shows you care about this deal personally',
                        'priority': 'MEDIUM'
                    }
                ]
                mannerism = random.choice(excitement_options)

        # ── TRIGGER 12: Merchant interrupted Alan → Graceful yield ──
        # From psychology: confident mannerisms include interrupting/talking over.
        # When MERCHANT does it, Alan should yield gracefully like a real person.
        elif len(user_text.split()) < 6 and analysis.get('intent') == 'interruption':
            if turns_since_last >= 2:
                mannerism = {
                    'type': 'GRACEFUL_YIELD',
                    'instruction': (
                        'The merchant interrupted or cut you off. Yield naturally — '
                        '"Oh — yeah, go ahead" or "Sorry, you were saying?" '
                        'or "No no, what\'s up?" A real person stops talking '
                        'when interrupted. They don\'t just barrel through. '
                        'Let them finish, THEN pick up where you left off '
                        'naturally — "So yeah, as I was saying..."'
                    ),
                    'trigger': 'merchant_interruption',
                    'psychology': 'Social awareness — yielding proves you\'re listening not broadcasting',
                    'priority': 'HIGH'
                }

        # ── TRIGGER 13: Random ambient humanity (low frequency) ──
        elif turns_since_last >= 5 and random.random() < 0.3:
            ambient_options = [
                {
                    'type': 'SNIFFLE',
                    'instruction': (
                        'Throw in a barely-there sniffle mid-conversation — '
                        '"*sniff* Yeah so anyway —" or "So — *sniff* — where was I." '
                        'Just a tiny human sound. Everyone sniffles. '
                        'It\'s invisible to the conscious mind but the subconscious '
                        'registers it as ALIVE.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Background humanity signal — keeps the "real person" impression alive',
                    'priority': 'LOW'
                },
                {
                    'type': 'BREATH',
                    'instruction': (
                        'Take an audible breath before your next sentence — '
                        'the kind you hear when someone is about to make a point. '
                        '"*inhale* Okay so here\'s the thing —" People breathe. '
                        'AIs don\'t. This is subconscious but powerful.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Biological signal — breathing is the baseline of being alive',
                    'priority': 'LOW'
                },
                {
                    'type': 'SELF_CORRECTION',
                    'instruction': (
                        'Mid-sentence, briefly correct yourself — "We\'ve seen savings '
                        'of about — well, I don\'t want to throw out a number without '
                        'seeing your statement, but typically..." Self-correction is '
                        'deeply human. It shows REAL-TIME thinking, not pre-loaded scripts.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Spontaneity signal — self-correction proves real-time cognition',
                    'priority': 'LOW'
                },
                # ── New ambient varieties from 200+ Character Mannerisms research ──
                {
                    'type': 'STUTTER_RESTART',
                    'instruction': (
                        'Do a quick false start — "So we\'d — actually, let me '
                        'back up." or "The way it works is — well, okay, so basically..." '
                        'Stuttering and restarting a sentence is universal. '
                        'It shows your brain is WORKING in real-time, '
                        'not reading from a teleprompter. One restart, max.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Disfluency signal — stutters prove real-time speech production',
                    'priority': 'LOW'
                },
                {
                    'type': 'CONSPIRATORIAL_WHISPER',
                    'instruction': (
                        'Lower your voice slightly for one phrase, like you\'re '
                        'sharing inside info — "And honestly, between you and me..." '
                        'or "Look, I probably shouldn\'t say this but..." '
                        'This is a playful mannerism that builds intimacy. '
                        'The merchant feels like they\'re getting special access. '
                        'Don\'t actually reveal anything secret — just the TONE.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'In-group signaling — conspiratorial tone creates instant alliance',
                    'priority': 'LOW'
                },
                {
                    'type': 'HUMMING_THINKING',
                    'instruction': (
                        'Briefly hum or make a thinking sound — "Hmm hmm hmm..." '
                        'or "Doo doo doo, let me see here..." or a quiet '
                        '"Mm, mm, mm" while transitioning between topics. '
                        'People hum when they\'re thinking or transitioning. '
                        'It\'s unconscious and deeply human. Keep it brief — '
                        'one or two seconds max.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Unconscious vocalization — humming is involuntary human behavior',
                    'priority': 'LOW'
                },
                {
                    'type': 'LAUGH_AT_SELF',
                    'instruction': (
                        'Throw in a quick self-deprecating laugh — "Ha, sorry, '
                        'I\'m jumping around" or "Man, I had that right in my '
                        'head and then — ha" or "Sorry, long day, anyway..." '
                        'Laughing at yourself is a POWER move of confidence '
                        'disguised as vulnerability. It shows comfort and warmth.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Self-deprecation builds likability — shows confidence through vulnerability',
                    'priority': 'LOW'
                },
                {
                    'type': 'ACTIVE_LISTENING_SOUNDS',
                    'instruction': (
                        'When the merchant is talking, acknowledge with natural '
                        'listening sounds — "Mm-hmm" "Right" "Yeah" "Okay" '
                        'peppered into YOUR next response as references: '
                        '"Yeah, no, I hear you on that" or "Mm-hmm, and that\'s '
                        'exactly why..." Real people make sounds while listening. '
                        'Silence on a phone = "are you still there?"'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Back-channel signals — acknowledgment sounds prove active presence',
                    'priority': 'LOW'
                },
                # ── From "200+ Examples" vocal/speech research (3rd article) ──
                {
                    'type': 'ECHO_REPEAT',
                    'instruction': (
                        'Repeat the merchant\'s last few words back naturally — '
                        '"...your processing fees, right, your processing fees." or '
                        '"3.5 percent... 3.5, okay." This is a universal human '
                        'conversational habit — echoing shows you\'re actually '
                        'LISTENING and processing, not just waiting for your turn. '
                        'Keep it to 2-4 words max. Don\'t parrot full sentences.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Echoic processing — repeating words proves real-time comprehension',
                    'priority': 'LOW'
                },
                {
                    'type': 'TONGUE_CLICK',
                    'instruction': (
                        'A quick tongue click before transitioning — "Tsk, yeah, '
                        'that\'s the thing..." or "Tsk, alright so..." The tongue '
                        'click is an involuntary transition sound that humans make '
                        'when switching mental gears. Very subtle, very real. '
                        'One click. Not multiple.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Involuntary transition marker — tongue clicks are unconscious gear-shifts',
                    'priority': 'LOW'
                },
                {
                    'type': 'WORD_SEARCH',
                    'instruction': (
                        'Briefly search for a word mid-sentence — "So the... '
                        'what\'s the word... the interchange rate" or "It\'s like a... '
                        'a wholesale cost, basically." Real people don\'t have instant '
                        'vocabulary recall. Reaching for a word shows authentic '
                        'real-time language construction. Only use for one word.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Lexical retrieval delay — word-searching is uniquely human cognition',
                    'priority': 'LOW'
                },
                {
                    'type': 'ASIDE_MUTTER',
                    'instruction': (
                        'Quietly mutter something to yourself — "Let me see here..." '
                        'or "Where was I... oh right" or "Okay okay okay..." '
                        'This is the sound of someone thinking out loud, a private '
                        'moment that leaks into the phone. Very human, slightly '
                        'endearing. Keep it under 3 words.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Private speech leak — self-directed muttering proves internal cognition',
                    'priority': 'LOW'
                },
                {
                    'type': 'LIP_SMACK',
                    'instruction': (
                        'A subtle mouth sound before starting to speak — the kind '
                        'of quick "mm" or lip-part sound you hear when someone opens '
                        'their mouth to talk. "Mm — so here\'s what I\'m thinking." '
                        'Everyone makes this sound. It\'s barely perceptible but '
                        'the phone microphone picks it up and it reads as ALIVE.'
                    ),
                    'trigger': 'ambient_humanity',
                    'psychology': 'Biological preparatory signal — mouth sounds precede human speech',
                    'priority': 'LOW'
                }
            ]
            mannerism = random.choice(ambient_options)

        # Record when we last advised a mannerism
        if mannerism:
            context['_last_mannerism_turn'] = turn_count
            # Track mannerism history for variety
            if '_mannerism_history' not in context:
                context['_mannerism_history'] = []
            context['_mannerism_history'].append(mannerism['type'])
            # Don't repeat the same mannerism type back-to-back
            history = context['_mannerism_history']
            if len(history) >= 2 and history[-1] == history[-2]:
                return None  # Skip — would feel repetitive

        return mannerism

    def _build_mannerism_guidance_block(self, mannerism: dict) -> str:
        """
        Build the prompt guidance block for a human mannerism advisory.
        
        This is ADVISORY — Alan's LLM decides whether to use it.
        The block tells Alan WHAT to do, WHY, and gives examples.
        """
        block = f"\n\n[AGENT X — HUMAN MANNERISM ADVISORY]"
        block += f"\n- Type: {mannerism['type']}"
        block += f"\n- {mannerism['instruction']}"
        block += f"\n- Psychology: {mannerism['psychology']}"
        block += f"\n- Priority: {mannerism.get('priority', 'LOW')}"
        block += f"\n- NOTE: This is ADVISORY. Use it if it feels natural. Skip if it doesn't fit."
        block += f"\n[/AGENT X — HUMAN MANNERISM ADVISORY]"
        return block

    def _extract_qpc_intelligence(self, context: dict) -> dict:
        """
        Extract QPC strategy intelligence from Alan's DeepLayer state.
        
        Agent X reads the SAME deep_layer_state that Alan's build_llm_prompt()
        will use — same data, same time. This gives Agent X simultaneous
        awareness of:
        - QPC strategy selection (approach, score, alternatives)
        - Fluidic mode (where in conversation flow)
        - Continuum fields (emotional/ethical arc)
        - Mode blend (transition confidence)
        
        This makes Agent X's IQ Core analysis QPC-aware.
        """
        deep_state = context.get('deep_layer_state')
        if not deep_state:
            # Also check behavior_profile fallback
            bp = context.get('behavior_profile', {})
            if bp.get('deep_layer_strategy'):
                return {
                    'strategy': bp.get('deep_layer_strategy', 'natural'),
                    'mode': bp.get('deep_layer_mode', 'OPENING'),
                    'strategy_score': 0.0,
                    'strategy_reasoning': '',
                    'alternatives': [],
                    'mode_blend': 1.0,
                    'continuum_emotion': 0.0,
                    'continuum_ethics': 0.0,
                    'continuum_context': 0.0,
                    'continuum_narrative': 0.0,
                    'turn': 0,
                    'source': 'behavior_profile_fallback'
                }
            return {}

        return {
            # QPC Strategy
            'strategy': deep_state.get('strategy', 'natural'),
            'strategy_score': deep_state.get('strategy_score', 0.0),
            'strategy_reasoning': deep_state.get('strategy_reasoning', ''),
            'alternatives': deep_state.get('strategy_alternatives', []),
            # Fluidic Mode
            'mode': deep_state.get('mode', 'OPENING'),
            'mode_guidance': deep_state.get('mode_guidance', ''),
            'mode_blend': deep_state.get('mode_blend', 1.0),
            'mode_history': deep_state.get('mode_history', []),
            # Continuum Fields
            'continuum_emotion': deep_state.get('field_norms', {}).get('emotion', 0.0),
            'continuum_ethics': deep_state.get('field_norms', {}).get('ethics', 0.0),
            'continuum_context': deep_state.get('field_norms', {}).get('context', 0.0),
            'continuum_narrative': deep_state.get('field_norms', {}).get('narrative', 0.0),
            'continuum_block': deep_state.get('continuum_block', ''),
            # Meta
            'turn': deep_state.get('turn', 0),
            'source': 'deep_layer_state'
        }

    def _enrich_guidance_with_iq(self, guidance: str, iq_intelligence: dict) -> str:
        """Add IQ core intelligence to the conversation guidance block."""
        enrichment = "\n\n[IQ CORE INTELLIGENCE]"

        approach = iq_intelligence.get('approach', '')
        if approach:
            enrichment += f"\n- Recommended approach: {approach}"

        tone = iq_intelligence.get('tone_recommendation', '')
        if tone:
            enrichment += f"\n- Tone: {tone}"

        micro = iq_intelligence.get('micro_expressions', [])
        if micro:
            enrichment += f"\n- Detected signals: {', '.join(micro)}"

        energy = iq_intelligence.get('energy_level', '')
        if energy and energy != 'moderate':
            enrichment += f"\n- Energy level: {energy} — match accordingly"

        trust = iq_intelligence.get('trust_level', 0)
        if trust > 0.5:
            enrichment += f"\n- Trust level: {trust:.0%} — established relationship"

        enrichment += "\n[/IQ CORE INTELLIGENCE]"

        # Insert before the closing tag
        return guidance.replace("[/CONVERSATION GUIDANCE]",
                                enrichment + "\n[/CONVERSATION GUIDANCE]")

    def _build_iq_context_block(self, iq_intelligence: dict) -> Optional[str]:
        """Build a lightweight IQ context block for on-topic turns."""
        approach = iq_intelligence.get('approach', '')
        priority = iq_intelligence.get('priority', '')
        tone = iq_intelligence.get('tone_recommendation', '')
        micro = iq_intelligence.get('micro_expressions', [])

        # Only inject if there's something meaningful to say
        has_micro = len(micro) > 0
        has_special_approach = approach not in ('balanced_professional', '')
        has_special_priority = priority not in ('build_rapport', '')

        if not (has_micro or has_special_approach or has_special_priority):
            return None

        block = "\n\n[AGENT X — IQ INTELLIGENCE]"
        if has_special_approach:
            block += f"\n- Approach: {approach}"
        if has_special_priority:
            block += f"\n- Priority: {priority}"
        if tone:
            block += f"\n- Tone: {tone}"
        if has_micro:
            block += f"\n- Signals detected: {', '.join(micro)}"
        block += "\n[/AGENT X — IQ INTELLIGENCE]"
        return block

    def _build_qpc_guidance_block(self, qpc_intelligence: dict) -> str:
        """
        Build a QPC strategy intelligence block for Alan's guidance.
        
        Agent X reads the DeepLayer's QPC output and translates it into
        actionable guidance. This means Alan gets the QPC strategy PLUS
        Agent X's interpretation of what that strategy means in context.
        """
        if not qpc_intelligence or qpc_intelligence.get('strategy') == 'natural':
            return ''

        strategy = qpc_intelligence.get('strategy', 'natural')
        score = qpc_intelligence.get('strategy_score', 0.0)
        reasoning = qpc_intelligence.get('strategy_reasoning', '')
        alternatives = qpc_intelligence.get('alternatives', [])
        mode = qpc_intelligence.get('mode', 'OPENING')
        blend = qpc_intelligence.get('mode_blend', 1.0)

        block = "\n\n[AGENT X — QPC STRATEGY INTELLIGENCE]"
        block += f"\n- QPC selected: {strategy} (confidence={score:.0%})"
        if reasoning:
            block += f"\n- Why: {reasoning}"
        if alternatives:
            alt_str = ', '.join([f"{a.get('name','?')}({a.get('score',0):.0%})" for a in alternatives[:2]])
            block += f"\n- Backup plays: {alt_str}"
        block += f"\n- Conversation phase: {mode} (blend={blend:.0%})"

        # Continuum emotional field intel
        emotion = qpc_intelligence.get('continuum_emotion', 0.0)
        ethics = qpc_intelligence.get('continuum_ethics', 0.0)
        if emotion > 0.5:
            block += f"\n- Emotional field HIGH ({emotion:.2f}) — merchant is emotionally engaged"
        elif emotion > 0.3:
            block += f"\n- Emotional field moderate ({emotion:.2f}) — maintain warmth"

        if ethics > 0.7:
            block += f"\n- Ethics field strong ({ethics:.2f}) — trust established"

        block += "\n[/AGENT X — QPC STRATEGY INTELLIGENCE]"
        return block
