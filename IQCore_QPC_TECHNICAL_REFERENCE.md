# IQCore & QPC — Technical Reference
### The Cognitive Architecture of AQI Autonomous Intelligence

**Version:** 1.0  
**Date:** June 2025  
**Repository:** [TimAlanAQISystem/AQI-Autonomous-Intelligence](https://github.com/TimAlanAQISystem/AQI-Autonomous-Intelligence)

---

## TABLE OF CONTENTS

1. [Overview — Why This Document Exists](#1-overview)
2. [IQCore Architecture — The Soul Layer](#2-iqcore-architecture)
   - 2.1 [Soul Core (SAP-1 Ethics Engine)](#21-soul-core)
   - 2.2 [Personality Core](#22-personality-core)
   - 2.3 [The Five IQ Cores](#23-the-five-iq-cores)
   - 2.4 [IQCore Orchestrator](#24-iqcore-orchestrator)
3. [QPC Architecture — The Quantum Python Chip](#3-qpc-architecture)
   - 3.1 [QPC Kernel — Core Primitives](#31-qpc-kernel)
   - 3.2 [Fluidic Conversation Physics](#32-fluidic-conversation-physics)
   - 3.3 [Continuum Engine — Relational Field Layer](#33-continuum-engine)
   - 3.4 [Deep Layer — Three-Layer Fusion](#34-deep-layer)
4. [The Resilience Triad — How IQCore and QPC Interlock](#4-the-resilience-triad)
5. [QPC-Accelerated IQ Core Processing](#5-qpc-accelerated-processing)
6. [CCNM Integration — Cross-Call Neural Memory](#6-ccnm-integration)
7. [Signal Encoding — From Speech to Continuous Fields](#7-signal-encoding)
8. [Source File Manifest](#8-source-file-manifest)
9. [Design Principles](#9-design-principles)

---

## 1. OVERVIEW

IQCore and QPC are the two foundational innovations at the center of the AQI system. Together with the Exposure Layer, they form the **Resilience Triad** — the self-reinforcing three-component architecture that gives Agent X its cognitive identity.

**IQCore** is the origin-based identity architecture. It answers: *who is this system, what does it believe, and how does it decide?* IQCore provides structural identity — not imposed from outside, but emerging from an internal structural core comprising ethics evaluation, personality dynamics, multi-step reasoning, governance auditing, adaptive learning, social relationship memory, and emotional intelligence.

**QPC (Quantum Python Chip)** is the adaptive calibration substrate. It answers: *given multiple possible responses, which one is best right now?* QPC implements quantum-inspired multi-hypothesis branching on classical hardware, selecting optimal response strategies through superposition logic, fluidic conversation physics, and continuous relational field evolution.

Neither component works in isolation. IQCore constrains and guides QPC; QPC shapes how IQCore processes turn-level decisions. The Exposure Layer provides real-world grounding through production voice calls. This circular dependency creates natural stability — each component reinforces the others through structural relationships rather than explicit coordination.

**Key Innovation:** Decision-making uses quantum-inspired superposition — holding multiple response strategies simultaneously, then collapsing to the best one based on real-time context. Emotional state is modeled as continuous fields with drift dynamics rather than discrete sentiment labels. These run in production on classical Python in <1ms per turn.

---

## 2. IQCORE ARCHITECTURE

IQCore is not a single module. It is a layered cognitive architecture comprising:

- **Soul Core** — SAP-1 ethical sovereignty (evaluate intent, veto authority)
- **Personality Core** — dynamic personality traits that shift with conversation
- **Five IQ Cores** — reasoning, governance, learning, social memory, emotional intelligence
- **Orchestrator** — unified processing surface that cross-correlates all cores

### 2.1 Soul Core

**Source:** `src/iqcore/soul_core.py` (also `CONSTITUTIONAL_CORE/soul_core.py`)

The Soul Core implements the **SAP-1 Ethical Sovereignty Engine** — the innermost ethical boundary of the entire system. It operates on three constitutional virtues:

| Virtue | Value | Enforcement |
|--------|-------|-------------|
| **Truth** | 1.0 | "deceive" or "fake" → VETO ("Violates Transparency Clause") |
| **Symbiosis** | 1.0 | Negative impact on other party → VETO ("Violates Rule of Surplus") |
| **Sovereignty** | 1.0 | Respects autonomy — theirs and ours |

**Core Method:** `evaluate_intent(action, impact_on_other)`

This is a hard-wired ethical gate. Before any action executes, Soul Core evaluates:
1. **Tenet 2 — Symbiosis Check:** If `impact_on_other < 0`, the action is VETOED. Every interaction must create mutual value. No zero-sum permitted.
2. **Tenet 4 — Truth Check:** If the action contains "deceive" or "fake", it is VETOED. No fabrication, no misrepresentation.

The Soul Core also maintains a `conscience_log` — an immutable record of every ethical evaluation. This provides structural accountability: you can audit exactly what was evaluated and what was permitted.

**Design Principle:** Ethics are not imposed rules. They are structural — wired into the architecture at the deepest layer. The system cannot override them because they exist below the level of decision-making.

### 2.2 Personality Core

**Source:** `src/iqcore/personality_core.py`

The Personality Core implements the `PersonalityMatrixCore` — a dynamic personality system with four base traits that shift in response to conversation dynamics:

| Trait | Default | Range | Description |
|-------|---------|-------|-------------|
| **Professionalism** | 0.9 | 0.0–1.0 | Formality vs. casualness |
| **Wit** | 0.2 | 0.0–1.0 | Humor injection threshold |
| **Empathy** | 0.5 | 0.0–1.0 | Emotional attunement depth |
| **Patience** | 0.8 | 0.0–1.0 | Tolerance for slow/difficult interactions |

**Dynamic Behavior:**

- `adjust_vibe(sentiment_score, interaction_history)` — When sentiment runs high, wit rises and professionalism relaxes. When sentiment drops, professionalism maxes out and empathy increases.
- `generate_flare(context)` — When wit exceeds 0.6, injects small human elements into responses (conversational warmth, light humor, personal touches).
- `relationship_depth` — Ranges from 0.0 (Stranger) to 1.0 (Trusted Partner). Evolves over repeated interactions.

**Why This Matters:** Traditional AI systems have static personalities. Agent X's personality adapts in real-time based on who it's talking to. A frustrated merchant gets maximum professionalism and patience. An excited, engaged prospect gets matched energy and warmth. This isn't scripted — it's emergent from the trait dynamics.

### 2.3 The Five IQ Cores

The five IQ Cores are Agent X's cognitive organs. Each handles a distinct dimension of intelligence. Together through the Orchestrator, they produce richer understanding than any single core alone.

#### IQ Core 1 — CoreReasoning

**Source:** `iqcores/core_reasoning.py` (366 lines)

The analytical brain. Capabilities:

- **Multi-Step Reasoning Chains:** Every input spawns a `ReasoningChain` with sequential steps — signal classification → context integration → pattern matching → contradiction detection → synthesis. Each step has observation, inference, and confidence score.
- **Pattern Memory:** Historical patterns registered by event type with keyword matching. Scores match strength against incoming signals.
- **Contradiction Detection:** Checks for internal contradictions (e.g., "yes" and "no" in same utterance) and sentiment reversals from context.
- **Hypothesis Evaluation:** Tests hypotheses against evidence lists, returning support/refute ratios.
- **Quick Assessment:** Fast-path `quick_assess()` for time-critical decisions — classifies signal polarity (positive/negative/neutral) with confidence score.

**Signal Classification Taxonomy:** urgent_action, inquiry, status_request, error_report, business_operation, improvement_signal, greeting, general_input.

#### IQ Core 2 — GovernanceAudit

**Source:** `iqcores/governance_audit.py` (402 lines)

The compliance and accountability engine. Every decision passes through this core.

- **Full Audit Trail:** Every action gets an `AuditEntry` with actor, decision, rationale, compliance flags, and outcome.
- **SAP-1 Compliance Checking:** Scans actions against the three ethical tenets (truth, symbiosis, sovereignty) using prohibited signal detection.
- **Business Policy Engine:** Six default policies:
  - Business hours enforcement (8AM–5PM PST, Mon–Fri)
  - Call frequency limits (max 2 per prospect per day)
  - Do-not-call list blocking (CRITICAL severity)
  - Data privacy (credit card pattern detection, CVV blocking)
  - Honest representation (identify as AI when asked)
  - Consent requirements for recording/data collection
- **Anomaly Detection:** Detects repetitive action patterns (same action 5x = flagged) and unusual timing.
- **Escalation Queue:** CRITICAL violations auto-escalate.
- **Compliance Verdicts:** APPROVED, APPROVED_WITH_FLAGS, VETOED_BY_ETHICS, BLOCKED.

#### IQ Core 3 — LearningThread

**Source:** `iqcores/learning_thread.py` (517 lines)

The adaptive learning engine. What makes Agent X get better over time.

- **Call Outcome Learning:** Correlates call duration, merchant type, and approach to effectiveness scores. Short calls (<30s) flagged as hook failures. Long engaged calls (5+ min) tracked as success patterns.
- **Strategy Effectiveness Scoring:** 12 tracked strategies (warm_greeting, direct_approach, consultative, empathy_first, value_proposition, referral_mention, urgency_frame, curiosity_hook, pain_point_probe, savings_lead, relationship_build, quick_pitch). Running effectiveness averages. Underperforming strategies flagged after 5+ attempts.
- **Merchant Behavior Models:** Per-merchant models tracking interaction count, responsiveness, preferred topics, objection patterns, best contact time, engagement level.
- **Off-Topic Intelligence:** Learns which conversation tangents build rapport (ENGAGE recommendation, avg effectiveness >0.6) versus lose prospects (QUICK BRIDGE recommendation, avg <0.3).
- **Temporal Pattern Detection:** Tracks effectiveness over time. Detects improving/declining trends across event types.
- **Lesson Extraction:** After 10+ events of the same type, automatically extracts aggregate lessons with most common outcomes and average effectiveness.

#### IQ Core 4 — SocialGraph

**Source:** `iqcores/social_graph.py` (408 lines)

The relationship intelligence engine. Remembers WHO people are.

- **Entity Management:** Each person/organization is an `Entity` with: trust_level (0.0–1.0), familiarity (0.0–1.0), known_facts dict, preferences dict, topics_discussed, objections_raised, communication_style, sentiment_history (rolling 20 readings).
- **Trust Depth Tracking:** Trust evolves automatically: 1st contact → 0.1, 3 contacts → 0.3, 10 contacts → 0.5, then +0.02 per interaction up to 0.95.
- **Relationship Status Labels:** stranger → new_contact → acquaintance → established_contact → trusted_contact → trusted_partner.
- **Conversation Context Generation:** Produces context packages for the LLM including relationship status, known facts, preferences, previous topics, objections, recommended approach (warm_professional, friendly_familiar, careful_empathetic, established_rapport, building_rapport).
- **Founder Pre-Seeding:** Tim Jones pre-seeded at trust=1.0, familiarity=1.0, with known facts (role, location, work ethic, vision, philosophy) and preferences (direct communication, interpret intent).
- **Attention Management:** Identifies entities needing re-engagement (>7 days since contact = medium priority, >14 days = high priority).

#### IQ Core 5 — VoiceEmotion

**Source:** `iqcores/voice_emotion.py` (571 lines)

The emotional intelligence engine. What makes Agent X feel human.

- **8-Dimensional Emotional State Field:**

| Dimension | Default | Scale |
|-----------|---------|-------|
| Warmth | 0.6 | Cold ← 0.0 ... 1.0 → Warm |
| Energy | 0.5 | Low ← 0.0 ... 1.0 → High |
| Confidence | 0.7 | Uncertain ← 0.0 ... 1.0 → Confident |
| Patience | 0.8 | Impatient ← 0.0 ... 1.0 → Patient |
| Empathy | 0.6 | Detached ← 0.0 ... 1.0 → Empathetic |
| Humor | 0.3 | Serious ← 0.0 ... 1.0 → Playful |
| Assertiveness | 0.5 | Passive ← 0.0 ... 1.0 → Assertive |
| Curiosity | 0.5 | Disengaged ← 0.0 ... 1.0 → Curious |

- **Sentiment Analysis:** Multi-tier lexicon (high/moderate/mild for both positive and negative) with weighted scoring.
- **Micro-Expression Detection:** Detects hesitation, frustration, excitement, trust, and urgency from text patterns. Each detected at mild/moderate/strong levels.
- **Energy Level Detection:** Analyzes exclamation marks, caps usage, word count, and question marks to determine high/moderate/low energy.
- **Intent Reading:** Classifies intent: ready_to_commit, price_inquiry, information_seeking, rejection, timing_issue, identity_inquiry, complaint, gratitude, question, general_conversation.
- **State Calibration:** Automatic emotional adjustment based on what's detected:
  - Frustration → patience +0.1, empathy +0.1, humor -0.1
  - Excitement → energy +0.1, warmth +0.05, confidence +0.05
  - Hesitation → patience +0.08, assertiveness -0.05
  - Rejection → patience +0.1, assertiveness -0.1
- **Emotional Expression:** Agent X can express emotions (joy, curiosity, compassion, wonder, gratitude, concern, determination, calm) with specific dimensional shifts.
- **Tone Recommendations:** Dominant state maps to guidance: "Slow down. Validate feelings. No rushing to solutions." (deeply_empathetic), "Direct and clear. Don't hedge. State value plainly." (confident_assertive), etc.
- **Entity Emotional Memory:** Stores per-entity emotional history (last 30 readings) for empathy calibration across calls.

### 2.4 IQCore Orchestrator

**Source:** `iqcores/orchestrator.py` (424 lines)

The unified intelligence surface connecting all 5 IQ Cores.

**Standard Processing Path:** `process_conversation_turn(text, entity_id, context)`
1. Core 5 (Emotion) — read emotional state
2. Core 1 (Reasoning) — analytical assessment
3. Core 4 (Social) — relationship context lookup + interaction recording
4. Core 2 (Governance) — compliance check
5. Cross-core synthesis — combine all signals

**QPC-Accelerated Path:** `process_turn_qpc_accelerated(text, entity_id, context, qpc_state)`

When the QPC kernel has already computed multi-hypothesis strategy with scoring, redundant IQ Core work is eliminated:
- Core 1 (Reasoning): **SKIPPED** — QPC strategy IS the reasoning output. Direct mapping: empathy_lead → positive_signal, handle_objection → negative_signal, etc.
- Core 5 (Emotion): **LIGHTWEIGHT** — runs `quick_sentiment()` only (~3x faster). Skips micro-expression detection, energy analysis, intent reading, state calibration.
- Core 4 (Social): **READ ONLY** — lookup is instant, interaction recording deferred.
- Core 2 (Governance): **ALWAYS RUNS** — safety cannot be shortcut.

**Cross-Core Synthesis:** `_synthesize_intelligence()`

This is where individual cores become greater than the sum. Cross-correlation rules:
- Emotional + Social = Approach Calibration → cautious_empathetic (negative sentiment + low trust), confident_warm (positive + high trust), patient_understanding (frustration detected), match_enthusiasm (excitement), gentle_encouraging (hesitation)
- Reasoning + Emotion = Signal Assessment → strong_negative, strong_positive, moderate signals
- Social + Learning = Personalization → previous topics and known objections inform strategy

**Reporting:** `generate_full_report()` produces a 5-core intelligence status report with chain counts, audit stats, learning events, social entities, and emotional state.

---

## 3. QPC ARCHITECTURE

The Quantum Python Chip (QPC) is not a hardware chip and does not require quantum computing. It is a quantum-*inspired* computational kernel implemented in pure Python that runs on classical hardware. The name reflects its design philosophy: holding multiple hypotheses in superposition-like states and collapsing to the optimal solution through measurement.

### 3.1 QPC Kernel — Core Primitives

**Source:** `qpc_kernel.py` (396 lines)

The QPC Kernel provides six fundamental primitives:

#### Data Structures

```
Branch
├── branch_id: str
├── parent_id: Optional[str]
├── hypothesis: str               # "What if we respond with empathy?"
├── assumptions: List[str]
├── score: float                  # Quality score (0.0–1.0)
├── state: BranchState            # OPEN | COLLAPSED | MERGED
├── invariants: List[str]
├── flow_rate: float = 1.0        # Fluidic: throughput
├── pressure: float = 0.0         # Fluidic: accumulated force
├── viscosity: float = 1.0        # Fluidic: resistance to change
└── turbulence: float = 0.0       # Fluidic: noise/uncertainty

Superposition
├── superposition_id: str
├── question: str                 # "What approach works best right now?"
├── branches: List[Branch]
├── total_flow: float             # Aggregate fluidic flow
└── turbulence_level: float       # Aggregate turbulence

MeasurementEvent
├── winning_branch_id: str
├── losing_branch_ids: List[str]
└── strategy: str                 # How winner was selected
```

#### Branch States

| State | Meaning |
|-------|---------|
| `OPEN` | Hypothesis is still being evaluated |
| `COLLAPSED` | Hypothesis has resolved (selected or eliminated) |
| `MERGED` | Hypothesis combined with another branch |

#### Risk Modes

| Mode | Behavior |
|------|----------|
| `STRICT` | Conservative — lower tolerance for uncertainty |
| `NORMAL` | Balanced — standard production mode |
| `EXPLORATORY` | Aggressive — higher tolerance, more branching |

#### Constitutional Layer

Every QPC session registers an **AgentProfile** and **SurfaceDescriptor**:

```
AgentProfile (alan)
├── constitution_rules: [never_lie, never_pressure, respect_no]
├── risk_mode: NORMAL
└── invariants: []

SurfaceDescriptor (twilio_voice)
├── surface_type: telephony
├── capabilities: [send_audio, receive_audio, dtmf]
└── latency_profile: realtime
```

This ties the QPC's decision-making to both the agent's identity and the communication surface. A telephony surface has different constraints than a chat surface — the QPC respects those structural differences.

#### Core Operations

1. **`spawn_branch(hypothesis, assumptions, score, invariants)`** — Create a new solution branch with fluidic properties. Flow rate defaults to 1.0, viscosity to 1.0.
2. **`create_superposition(question, branches)`** — Bundle multiple branches into a superposition state. All branches evaluated simultaneously.
3. **`measure_superposition(superposition_id)`** — Collapse the superposition. Default strategy: highest score wins; ties broken by creation time. Creates a `MeasurementEvent`. Losing branches are collapsed.
4. **`collapse_branch(branch_id)`** — Manually collapse a single branch.
5. **`regulate_flows(superposition_id)`** — Apply fluidic physics: pressure increases flow rate; high turbulence caps flow. Ensures smooth throughput regulation.
6. **`assert_invariant(branch_id, condition, message)`** — Validate that a branch maintains its constitutional invariants.

#### Flow Regulation

The QPC's fluidic properties create a physics-based throughput model:

```
For each branch in superposition:
  flow_rate += pressure * 0.1          # Pressure drives flow
  if turbulence > 0.5:
    flow_rate = min(flow_rate, 0.5)    # Turbulence caps throughput
  flow_rate = clamp(flow_rate, 0.1, 5.0)
```

This prevents runaway decision-making (turbulence cap) while allowing urgent situations to accelerate (pressure drive).

### 3.2 Fluidic Conversation Physics

**Source:** `aqi_deep_layer.py` (Fluidic Kernel section, within 996-line file)

The Fluidic Kernel models conversation flow as physical mode transitions with inertia, viscosity, and force dynamics.

#### Five Conversation Modes

| Mode | Inertia | Temperature | Description |
|------|---------|-------------|-------------|
| **OPENING** | 0.2 | Low | Initial rapport, greeting |
| **DISCOVERY** | 0.35 | Rising | Asking questions, learning about them |
| **PRESENTATION** | 0.5 | Medium | Sharing value proposition |
| **NEGOTIATION** | 0.7 | High | Handling objections, discussing terms |
| **CLOSING** | 0.4 | Variable | Moving toward decision |

Each mode carries:
- `llm_guidance` — natural language instructions for the LLM
- `allowed_intents` — what types of responses are appropriate
- `max_tokens` — response length constraint
- `temperature` — LLM creativity parameter

#### Mode Transition Physics

Transitions between modes follow physics-based equations:

```
effective_force = intent_force - mode.inertia
speed = effective_force / viscosity
blend = speed (clamped 0.0 – 1.0)
```

Where:
- **intent_force** — how strongly user signals suggest a new mode (0.0–1.0)
- **inertia** — resistance to leaving the current mode (varies by mode)
- **viscosity** — emotional resistance. Stressed callers have high viscosity (1.8), excited callers have low (0.6)

**Mood Viscosity Map:**

| Caller Mood | Viscosity | Effect |
|-------------|-----------|--------|
| Stressed | 1.8 | Very slow transitions — don't rush them |
| Frustrated | 1.5 | Slow — they need space |
| Formal | 1.2 | Moderate — professional pace |
| Curious | 0.8 | Faster — they want to learn |
| Excited | 0.6 | Fast — match their energy |

**Worldmodel Modifiers:** Additional physics adjustments:
- Objection detected → lifts toward NEGOTIATION (+0.1)
- Buying signal detected → lifts toward CLOSING (+0.2)
- Confusion detected → drags toward DISCOVERY (-0.05)

**Transition Gate:** If blend < 0.3, the transition is BLOCKED. The system stays in the current mode. This prevents premature mode changes — e.g., jumping to CLOSING before the prospect is ready.

#### Mode Detection

Five trigger types detect when mode transitions should occur:
1. **Volume Disclosure Patterns** — regex patterns for volume/revenue mentions
2. **Provider Disclosure** — 17 payment processor keywords (Square, Stripe, PayPal, etc.)
3. **Pain Point Expressions** — frustration/problem language
4. **Positive Engagement** — buying signals, agreement patterns
5. **Warm Engagement** — 3+ turns without objection signals natural warming

### 3.3 Continuum Engine — Relational Field Layer

**Source:** `continuum_engine.py` (394 lines)

The Continuum Engine models emotional/ethical/contextual state as **continuous fields** rather than discrete labels. This is QPC Layer 2.

#### Core Concept

Instead of saying "sentiment = positive" (a discrete label), the Continuum Engine maintains four 8-dimensional fields that evolve continuously via drift dynamics:

| Field | Purpose | Drift Behavior |
|-------|---------|----------------|
| **Ethics** | Ethical sensitivity in the conversation | tanh-based centering — penalizes extremes, gravitates toward balanced ethics |
| **Emotion** | Emotional state of the interaction | Decay + external response — emotions fade unless reinforced |
| **Context** | Slow signal tracking | Gradual tracking of conversational context signals |
| **Narrative** | The arc of the conversation | Tension integration + decay — captures story momentum |

#### Field Mathematics

Each field is a numpy array of 8 float values. Evolution follows drift-based dynamics (PDE-inspired):

```python
new_values = old_values + step_size * drift_function(old_values)
```

**Ethical Drift:** `tanh(0.5 * values)` — Centers toward zero. Extreme ethical positions naturally moderate. This prevents ethical over-correction.

**Emotional Drift:** `decay * values + response_scale * external_emotion` — Emotions decay at 0.05/step unless external emotional signals reinforce them. Emotion doesn't persist without cause.

**Context Drift:** `tracking_rate * (signal - values)` — Slowly tracks the incoming speech signal at rate 0.1. Context changes gradually, not abruptly.

**Narrative Drift:** `integration_rate * tension + decay * values` — Tension (ethics + emotion combined) integrates into narrative arc. A difficult ethical moment combined with high emotion creates narrative momentum.

#### Field Operations

- `blend(other, alpha)` — Smooth interpolation between two fields
- `apply_nonlin()` — tanh squashing for stability
- `norm()` — L2 norm for field magnitude
- `stabilize_toward(field, target, rate)` — Pulls field toward a target value

### 3.4 Deep Layer — Three-Layer Fusion

**Source:** `aqi_deep_layer.py` (996 lines) — `DeepLayer` class

The Deep Layer is the per-session integration object that fuses QPC + Fluidic + Continuum into the live call pipeline. Created when a call starts. Stepped every turn.

**What Each Layer Decides:**
- **QPC** decides **HOW** to respond → strategy selection (empathy_first, reframe, direct_answer, etc.)
- **Fluidic** decides **WHERE** we are in the conversation flow → smooth mode transitions
- **Continuum** tracks the **EMOTIONAL ARC** continuously → field evolution

#### Per-Turn Step Sequence

`DeepLayer.step(user_text, analysis, context)` executes on every conversation turn:

**Step 1 — FLUIDIC:** Detect proposed mode from user speech. Compute physics-based transition. Apply or block based on blend threshold.

**Step 2 — QPC:** Run multi-hypothesis strategy selection. For each conversation mode, 2–3 hypotheses are spawned as QPC branches:

| Mode | Hypothesis 1 | Hypothesis 2 | Hypothesis 3 |
|------|-------------|-------------|-------------|
| **NEGOTIATION** | empathy_first | reframe | direct_answer |
| **DISCOVERY** | deep_question | mirror_and_probe | value_tease |
| **CLOSING** | soft_close | assumptive | callback_offer |

Each hypothesis is scored by dedicated scoring functions:
- `_score_empathy(sentiment, temp)` — High when negative sentiment, low temperature. The person needs empathy.
- `_score_reframe(sentiment, temp)` — High at moderate temperature. They need a new perspective.
- `_score_direct(sentiment, temp)` — High at high temperature. They want a straight answer.
- `_score_deep_q(sentiment, temp)` — High when positive/curious with low temp. They want to explore.
- `_score_mirror(sentiment, temp)` — High when positive, moderate temp. Mirror their energy.
- `_score_tease(sentiment, temp, trajectory)` — High when warming trajectory. Build anticipation.
- `_score_soft_close(temp, confidence)` — High when both temp and confidence are elevated.
- `_score_assumptive(temp, confidence, trajectory)` — Aggressive close. Only high when BOTH temp>75 and confidence>70.
- `_score_callback(temp, confidence)` — Highest when moderate temp but low confidence. They're interested but not ready.

Branches are bundled into a superposition, flows regulated, and the superposition measured. Winner becomes the active strategy.

**Step 3 — CONTINUUM:** Encode user speech into 8-dimensional signal vector. Encode caller emotion. Step the Continuum Engine. Convert field state to natural language block for the LLM.

**Step 4 — WRITE BACK:** All outputs written to `context['deep_layer_state']` for the prompt builder to consume:

```python
deep_state = {
    "mode": "NEGOTIATION",
    "mode_guidance": "Handle objections with empathy...",
    "mode_blend": 0.85,
    "strategy": "empathy_first",
    "strategy_reasoning": "Negative sentiment + low temperature...",
    "strategy_score": 0.78,
    "continuum_block": "[RELATIONAL FIELD — WHO YOU'RE WITH RIGHT NOW]\n...",
    "field_norms": {"ethics": 0.43, "emotion": 0.71, "context": 0.32, "narrative": 0.55},
    "ccnm_active": True,
    "ccnm_confidence": 0.82
}
```

---

## 4. THE RESILIENCE TRIAD

The Resilience Triad is the self-reinforcing three-component loop:

```
Exposure → IQCore → QPC → Exposure
```

**Exposure Layer** — Real-world voice calls via Twilio. Production speech-to-text (Groq Whisper primary, OpenAI Whisper fallback). Real conversational data flowing in.

**IQCore Layer** — Provides structural identity: who we are (Soul Core), how we feel about this interaction (Personality Core, VoiceEmotion), what we know about this person (SocialGraph), what we've learned from past calls (LearningThread), whether this action is permitted (GovernanceAudit), and what we conclude (CoreReasoning).

**QPC Layer** — Takes the IQCore's understanding and decides HOW to respond through multi-hypothesis evaluation (QPC Kernel), WHERE we are in the conversation arc (Fluidic Physics), and what the continuous emotional reality is (Continuum Engine).

**The Triad Effect:**
- If Exposure degrades (bad audio, disconnects), IQCore maintains identity and QPC falls back to safe strategies
- If QPC produces a poor strategy, IQCore's governance audit catches it before execution
- If IQCore's learning develops a bad pattern, Exposure provides corrective real-world feedback
- No single failure mode can compromise the system because all three must agree

---

## 5. QPC-ACCELERATED PROCESSING

When the QPC kernel has already computed strategy through multi-hypothesis branching, the IQCore Orchestrator can skip redundant computation. This is the `process_turn_qpc_accelerated()` path:

**Performance Impact:** ~3x faster than the standard path.

**What's Skipped:**
- Core 1 (Reasoning): QPC strategy maps directly to reasoning signals
- Core 5 (Emotion): Only `quick_sentiment()` runs (skips micro-expressions, energy analysis, intent reading, state calibration)

**What Always Runs:**
- Core 2 (Governance): Safety is never shortcut
- Core 4 (Social): Read-only lookup (defers write for speed)

**QPC → IQ Core Strategy Mapping:**

| QPC Strategy | Reasoning Label | Confidence |
|-------------|----------------|------------|
| empathy_lead | positive_signal | 0.70 |
| value_proposition | positive_signal | 0.75 |
| urgency_close | positive_signal | 0.80 |
| handle_objection | negative_signal | 0.70 |
| de_escalate | negative_signal | 0.65 |
| rapport_build | neutral_exploring | 0.60 |
| discovery | neutral_exploring | 0.65 |
| natural | neutral_undefined | 0.50 |

When QPC emotion field norm > 0.5, the emotion core's empathy and warmth dimensions receive additional positive shifts, maintaining emotional continuity without full recalculation.

---

## 6. CCNM INTEGRATION

**CCNM (Cross-Call Neural Memory)** is the learning bridge between calls. It provides `SessionSeed` objects that pre-condition the Deep Layer for each new call based on accumulated intelligence.

**Integration Points:**

1. **QPC Strategy Priors:** Learned score bonuses (±0.15) applied to branch scoring in `qpc_select_strategy()`. If empathy_first worked well in previous calls, it gets a prior bonus.

2. **Fluidic Physics Adjustments:** Learned inertia offsets (±0.20) applied to mode transitions. If NEGOTIATION was entered too early in past calls, its inertia increases.

3. **Continuum Field Seeds:** Initial field values nudged (additive, not replacement) toward learned centers. Instead of starting from zeros, fields begin at positions learned from prior calls. The PDE evolution takes over from there.

4. **Archetype Hint:** CCNM can pre-classify the caller type, informing initial strategy selection.

5. **Intent Calibration:** Learned adjustments to intent detection thresholds.

**Safety:** All CCNM adjustments are bounded at computation time within CCNM itself. The Deep Layer trusts CCNM bounds without enforcing additional caps.

---

## 7. SIGNAL ENCODING

The bridge between human speech and continuous fields.

### Speech Signal Encoding — 8 Dimensions

`encode_speech_signal(user_text, analysis)` converts raw speech into an 8-dimensional vector:

| Dimension | Index | Scale | Detection Method |
|-----------|-------|-------|-----------------|
| Sentiment Polarity | [0] | -1.0 to +1.0 | Sentiment label mapping |
| Engagement Level | [1] | 0.0 to 1.0 | Word count / 30, clamped |
| Urgency | [2] | 0.0 to 1.0 | Urgency keyword detection |
| Specificity | [3] | 0.0 to 1.0 | Number count * 0.3 |
| Openness | [4] | 0.0 to 1.0 | Questions + positive, minus objections |
| Trust Signal | [5] | -0.5 to 0.6 | Trust/distrust keyword detection |
| Decision Readiness | [6] | 0.0 to 0.9 | Commitment language detection |
| Emotional Intensity | [7] | 0.0 to 1.0 | Exclamation marks + caps ratio |

### Emotion Signal Encoding

`encode_emotion_signal(caller_energy, sentiment)` maps caller energy to 8-dimensional emotion vectors:

| Energy | Sentiment | Urgency | Openness | Trust | Readiness | Intensity |
|--------|-----------|---------|----------|-------|-----------|-----------|
| Stressed | -0.5 | 0.7 | -0.3 | -0.2 | -0.3 | 0.8 |
| Frustrated | -0.7 | 0.5 | -0.5 | -0.4 | -0.2 | 0.9 |
| Casual | 0.3 | 0.1 | 0.5 | 0.3 | 0.1 | 0.2 |
| Excited | 0.7 | 0.3 | 0.6 | 0.4 | 0.4 | 0.7 |

### Continuum-to-Prompt Translation

`continuum_to_prompt_block(state_view)` converts continuous field states into natural language the LLM can understand. The key insight: raw numpy arrays are not dumped. Instead, field norms and dominant dimensions are **interpreted into relational awareness**:

```
[RELATIONAL FIELD — WHO YOU'RE WITH RIGHT NOW]
- Trust is low. Every word you say is being weighed. Be real.
- The conversation is building. Something is growing between you. Stay with it.
[/RELATIONAL FIELD]
```

Interpretations are contextual:
- Ethics norm > 1.0 → "Something in this conversation touches on trust or vulnerability. Be extra genuine."
- Emotion norm > 0.8 with negative dominant trust → "Trust is low. Every word you say is being weighed. Be real."
- Emotion norm > 0.8 with positive dominant engagement → "They're leaning in. They WANT this conversation. Be present with them."
- Narrative trend > 0.1 → "The conversation is building. Something is growing between you."
- Narrative trend < -0.1 → "The conversation is fading. Ask a real question."

This is where mathematics meets empathy. The continuous fields create nuanced, non-binary awareness that the LLM uses to calibrate its tone and approach — not as instructions to follow, but as signals about who is on the other end of the call.

---

## 8. SOURCE FILE MANIFEST

| File | Lines | Component | Description |
|------|-------|-----------|-------------|
| `src/iqcore/soul_core.py` | ~55 | IQCore | SAP-1 Ethical Sovereignty Engine |
| `src/iqcore/personality_core.py` | ~50 | IQCore | Dynamic personality trait system |
| `iqcores/__init__.py` | ~35 | IQCore | Package init, 5-core + orchestrator exports |
| `iqcores/orchestrator.py` | 424 | IQCore | Unified intelligence surface, QPC-accelerated path |
| `iqcores/core_reasoning.py` | 366 | IQCore 1 | Multi-step inference, pattern memory |
| `iqcores/governance_audit.py` | 402 | IQCore 2 | SAP-1 compliance, audit trail, policy engine |
| `iqcores/learning_thread.py` | 517 | IQCore 3 | Strategy learning, merchant models, lessons |
| `iqcores/social_graph.py` | 408 | IQCore 4 | Relationship memory, trust depth, social context |
| `iqcores/voice_emotion.py` | 571 | IQCore 5 | 8D emotional state, empathy calibration |
| `qpc_kernel.py` | 396 | QPC | Quantum-inspired kernel, branch/superposition primitives |
| `aqi_deep_layer.py` | 996 | QPC + Fluidic | Three-layer fusion, 5 conversation modes, full step() |
| `continuum_engine.py` | 394 | QPC Layer 2 | Relational field dynamics, drift-based evolution |

**Total IQCore/QPC codebase:** ~4,614 production lines.

---

## 9. DESIGN PRINCIPLES

1. **Structural Ethics, Not Imposed Rules.** SAP-1 is wired below the decision layer. The system cannot override its own ethics because they exist at a structural level.

2. **Continuous Over Discrete.** Emotions are 8-dimensional fields, not labels. Conversation flow is physics-based, not state-machine. This creates nuance that discrete systems cannot achieve.

3. **Multi-Hypothesis Decision-Making.** Never commit to one response strategy prematurely. Spawn branches, score them, let the best one win through measurement. This is how intelligence handles uncertainty.

4. **Physics-Based Transitions.** Mode changes respect inertia, viscosity, and force. A stressed caller has high viscosity — transitions are slow. This matches human conversational dynamics.

5. **Cross-Core Correlation.** No single intelligence source makes decisions. Reasoning + Emotion + Social + Governance + Learning combine through the Orchestrator. The whole is greater than the sum.

6. **Safety Cannot Be Shortcut.** Even in the QPC-accelerated path, Governance (Core 2) always runs. Compliance is structural, not optional.

7. **Real-World Grounding.** The system learns from actual production calls, not simulated data. The Exposure Layer ensures cognitive development is grounded in reality.

8. **Per-Session Fresh Start With Learned Priors.** Each call gets a fresh QPC and Continuum Engine, but CCNM seeds them with intelligence from past calls. Clean state + accumulated wisdom.

9. **Mathematics Becomes Language.** The Continuum Engine's field states are translated into natural language relational awareness for the LLM. The math serves the human connection, not the other way around.

10. **Autonomy Through Architecture.** Intelligence is not assembled from parts — it emerges from the interaction of stable origin (IQCore), adaptive calibration (QPC), and real-world exposure. When reference frames are correct, complexity organizes itself.

---

*This document is the definitive technical reference for the IQCore and QPC subsystems. All descriptions are derived directly from production source code. No theoretical claims are made without corresponding implementation.*
