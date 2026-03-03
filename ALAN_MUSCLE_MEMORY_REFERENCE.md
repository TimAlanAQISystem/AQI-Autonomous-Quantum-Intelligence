# ALAN â€” COMPLETE MUSCLE MEMORY REFERENCE
### Compiled: February 15, 2026
### Purpose: Every muscle movement Alan can make, mapped and memorized

---

## ðŸ—ï¸ ARCHITECTURE OVERVIEW

Alan is a **5-layer AI voice agent** that conducts live phone calls with merchants, selling payment processing services for **Signature Card Services** (Edge Program @ $14.95/month flat fee). He must **never** be detected as an AI.

### The 5 Layers:
1. **Telephony/Voice** â€” Twilio Media Streams, WebSocket, STT, TTS, VAD
2. **Cognitive Engine** â€” GPT-4o-mini brain, orchestrated pipeline, DeepLayer
3. **Governance/Safety** â€” QPC kernel, Supervisor, PGHS, EOS, compliance
4. **Business Intelligence** â€” MasterCloser, behavior adaptation, evolution, MIP
5. **Operations/Infrastructure** â€” Control API, campaigns, fleet, leads, tunnel sync

---

## ðŸ“ž LAYER 1: TELEPHONY & VOICE PIPELINE

### Files: `aqi_conversation_relay_server.py` (2,847 lines), `aqi_stt_engine.py` (434 lines), `aqi_voice_module.py` (699 lines), `aqi_voice_governance.py` (412 lines)

### The Orchestrated Pipeline ("The Symphony")
**The single most important subsystem.** This is what makes Alan sound human.

```
MERCHANT SPEAKS â†’ VAD detects silence â†’ STT finalizes (200-400ms Groq Whisper)
â†’ handle_user_speech() processes context
â†’ _orchestrated_response() fires:
    â”œâ”€â”€ Background thread: LLM SSE streaming (GPT-4o-mini, temp=0.5, max_tokens=80)
    â”œâ”€â”€ Sentence detection at punctuation boundaries
    â”œâ”€â”€ EARLY-FIRE: splits at comma after 30 chars for faster first audio
    â”œâ”€â”€ CHATBOT KILLER: filters 51 dead phrases + strips filler prefixes
    â”œâ”€â”€ QUESTION CAP: drops 2nd+ question per turn
    â”œâ”€â”€ TTS synthesis immediately (gpt-4o-mini-tts, voice="onyx", speed=1.12)
    â”œâ”€â”€ Audio streaming to Twilio (160-byte mulaw frames, 0.012s pacing)
    â””â”€â”€ TTS prefetch: synthesize next sentence while streaming current
```

**Timing Budget:**
- STT finalize: 200-400ms (Groq) / 1-2s (OpenAI fallback)
- LLM first token: ~500-800ms (with pre-warm) / ~3000ms (cold)
- TTS synthesis: ~200-400ms per sentence
- **First audio out: ~1500-2200ms total**

### Voice Parameters
| Parameter | Value | Purpose |
|-----------|-------|---------|
| TTS Model | gpt-4o-mini-tts | Speech synthesis |
| Voice | "onyx" | Deep, warm male |
| Speed | 1.12x | Slightly faster than default |
| Tempo Compression | 1.06x | Applied post-synthesis |
| Effective Speed | ~1.19x | Combined speed |
| Audio Format | mulaw 8kHz | Twilio standard |
| Frame Size | 160 bytes | 20ms of audio |
| Frame Pacing | 0.012s cruise | Adaptive warm-up â†’ cruise |
| Max Sentences | 3 | Per turn cap |

### VAD (Voice Activity Detection) â€” Physics-Based Dual-Mode
| Parameter | Listening Mode | Speaking Mode (Echo Guard) |
|-----------|---------------|--------------------------|
| Speech Threshold | 400 RMS | 1500 RMS |
| Silence Threshold | 250 RMS | 250 RMS |
| Silence Duration | 0.50s | 0.50s |
| Barge-in Frames | 3 consecutive | 5 consecutive |
| Echo Cooldown | â€” | 2.0s after speech ends |

### STT Engine (`aqi_stt_engine.py`)
- **Primary**: Groq Whisper `whisper-large-v3-turbo` (200-400ms)
- **Fallback**: OpenAI Whisper (1-2s)
- Audio capped at 6 seconds max
- Minimum RMS energy: 150 (noise rejection)
- Minimum duration: 0.3s
- Manual WAV header construction (bypasses ffmpeg = 200-800ms savings)
- Whisper prompt engineering with realistic dialog examples
- Hallucination filtering: "thank you for watching", "please subscribe", etc.

### Greeting System
- **Pre-cached greetings** eliminate first-response TTS latency
- **Ring tone generation**: 440+480Hz dual-tone (simulates picking up mid-ring)
- **Deterministic greeting selection**: inbound/named/cold variants with randomization
- **State machine**: FIRST_GREETING_PENDING â†’ LISTENING_FOR_CALLER
- **LLM pre-warm**: fires cheap max_tokens=1 API call during greeting playback (reduces first-turn TTFT from ~3000ms to ~500-800ms)

### Barge-in Handling
1. Dual-mode VAD detects real speech (not echo)
2. Send CLEAR event to Twilio (stops current audio)
3. Increment generation counter (invalidates in-flight responses)
4. Clear STT buffer (fresh accumulation)
5. Cancel-and-replace: new response starts as if current never existed

### Comfort Noise
- ITU-T G.711 CNG injected between sentences
- Prevents dead air from being perceived as disconnect

---

## ðŸ§  LAYER 2: COGNITIVE ENGINE

### Files: `agent_alan_business_ai.py` (3,445 lines), `aqi_deep_layer.py` (743 lines), `continuum_engine.py` (394 lines)

### Alan's Brain (`agent_alan_business_ai.py`)
**Core Classes:**
- `IntuitionCore` â€” Pattern recognition from conversation signals
- `CreativityCore` â€” Response variation and creativity
- `StrategicAnalysisCore` â€” Sales strategy evaluation
- `MotorControlCore` â€” Response timing and delivery
- `LocalLLMCore` â€” Local inference fallback
- `ObjectionHandlingCore` â€” Objection detection and countering
- `CyberDefenseCore` â€” Threat detection (probing, social engineering)
- `FoundersProtocol` â€” Tim/Mark hardcoded reflexes, instincts, skills
- `OpenAIKeyManager` â€” Hot-reload API key rotation from keys.json
- `GPT4oCore` â€” SSE streaming, 3-attempt failover with 15s/10s/8s timeouts
- `BackupCore` â€” Scripted responses when LLM fails
- `RelationalState` ("The Soul") â€” Trust, rapport, emotional resonance tracking
- `AlanCoreManager` â€” Primary/fallback core failover with 5-min cooldown
- `AgentAlanBusinessAI` â€” The main agent class

### System Prompt (~900 lines)
Built dynamically with:
- 13 absolute rules (never reveal AI, never use filler, etc.)
- Banned AI words list
- Merchant services encyclopedia
- 13 training lessons from real call analysis
- Competitive intelligence for 8 competitors (Square, Clover, Stripe, PayPal, Toast, Shopify, Heartland, Worldpay)
- Tactical playbook for objection handling
- Edge Program details ($14.95/month flat fee)

### `build_llm_prompt()` â€” Context Assembly
Injects into every LLM call:
1. MerchantPreferences (detail_level, pacing, formality, closing_style_bias)
2. MIP memory (cross-call history for known merchants)
3. BehaviorProfile (tone, assertiveness, rapport level)
4. CRG reasoning budget (novelty level 0-3, creativity allowance)
5. Energy mirroring directive (stressed/casual/formal/neutral)
6. Live objection context
7. DeepLayer context (QPC strategy, Fluidic mode, Continuum encoding)
8. Rapport layer (off-topic resilience, micro-acknowledgments)

### DeepLayer (`aqi_deep_layer.py`)
**Per-session, stepped every turn.** Integrates three engines:

#### A. Fluidic Kernel â€” 5 Conversation Modes
| Mode | Inertia | Description |
|------|---------|-------------|
| OPENING | 0.2 | Easy to move through |
| DISCOVERY | 0.6 | Sticks â€” wants to stay in discovery |
| PRESENTATION | 0.5 | Moderate resistance |
| NEGOTIATION | 0.7 | Heavy â€” hard to push through |
| CLOSING | 0.4 | Lighter â€” enables decisive movement |

**Physics transition formula:**
```
effective_force = max(0, intent_force - inertia)
base_speed = force / viscosity
blend_threshold = 0.3
```

**Mood Viscosity Map:**
| Mood | Viscosity | Effect |
|------|-----------|--------|
| stressed | 1.8 | Very slow transitions |
| frustrated | 1.5 | Slow |
| neutral | 1.0 | Normal |
| interested | 0.8 | Faster |
| excited | 0.6 | Very fast transitions |

#### B. QPC Strategy Selection
3 competing hypotheses per mode, scored by sentiment/temperature/trajectory:
- OPENING: warm_connector vs authority_opener vs curiosity_hook
- DISCOVERY: open_ended_diagnostic vs guided_discovery vs empathy_first
- PRESENTATION: value_anchor vs social_proof vs fear_of_loss
- NEGOTIATION: empathy_first vs reframe vs direct_answer
- CLOSING: soft_commitment vs direct_ask vs scarcity_close

#### C. Continuum Engine â€” 8-Dimensional Encoding
Encodes merchant emotional state into context injection:
sentiment_polarity, engagement, urgency, specificity, openness, trust, decision_readiness, emotional_intensity

### Continuum Engine (`continuum_engine.py`)
Full numpy-based continuous field evolution:
- 4 relational fields: ethics, emotion, context, narrative (each dim=16)
- Drift functions: ethical_drift (balance), emotional_drift (decay+response), context_drift (follow signal), narrative_drift (tensionâ†’momentum)
- Step size: 0.05 (smooth evolution)
- Used by DeepLayer for continuous emotional tracking

---

## ðŸ›¡ï¸ LAYER 3: GOVERNANCE & SAFETY

### QPC Kernel (`qpc/` â€” 7 files)
- `identity.py`: **IdentityHamiltonian** â€” forbidden phrases (51+), patterns, domains. Tone=formal. Sentence length max=32 words. `check_output()` blocks violations.
- `program.py`: QPCProgram â€” sequential step execution under coherence + identity governance
- `coherence.py`: CoherenceWindow â€” max_depth=10 steps, max_duration=5000ms, max_external_calls=3
- `state.py`: QPCState â€” immutable cognitive snapshots with UUID + timestamp + parent tracking

### Supervisor (`supervisor.py` â€” 531 lines)
- **Singleton** pattern
- 14 registered components (Twilio, TTS, STT, LLM, audio pipeline, etc.)
- Incident reporting (capped at 1000)
- Health watchdog thread (30s check interval)
- Response compliance validation

### Post-Generation Hallucination Scanner (PGHS)
- Scans every LLM output **before** TTS
- Checks: numeric claims without backing, unverified business facts, compliance violations, product claims
- Major violations â†’ EOS critical shutdown
- Minor violations â†’ safe text replacement

### Emergency Override System (EOS)
5 operational states:
1. NORMAL_OPERATION
2. SAFE_MODE â€” simplified, low-risk responses
3. MERCHANT_SHUTDOWN_MODE â€” stop all merchant interaction
4. ESCALATING_TO_NORTH â€” client-facing escalation
5. ESCALATING_TO_TIM_MARK â€” system-facing escalation

**Invariant: Alan must ALWAYS be able to talk to Tim, Mark, and North.**

### System Coordinator (`system_coordinator.py`)
Single choke point. Priority order: **EOS â†’ PGHS â†’ Supervisor â†’ MTSP â†’ MIP â†’ BAS**
- PGHS latency budget: 50ms
- MIP updates are non-blocking
- BAS runs on its own schedule (never blocks calls)

### Voice Governance (`aqi_voice_governance.py`)
- Single-speaker enforcement (only one layer can speak at a time)
- Core health monitoring with heartbeat (5s timeout)
- Emergency failover when core fails
- Safety override always bypasses all checks
- Fail-open for business continuity

### Compliance Framework (`aqi_compliance_framework.py`)
- PCI DSS levels 1-4, SAQ types
- HIPAA for healthcare merchants
- Business license verification
- Bank verification (voided check)
- Identity verification (OFAC screening)
- Industry-specific requirements

---

## ðŸ“Š LAYER 4: BUSINESS INTELLIGENCE

### MasterCloser (`master_closer_layer.py`)
**Call Memory:** key_points, objections (with strength), agreements, goals
**Micro-patterns:** hesitation, soft_resistance, half_objection
**Trajectory:** warming/cooling/stalling with signal-based scoring
**Endgame Detection:**
| Condition | Result |
|-----------|--------|
| temp â‰¥ 0.7 AND confidence â‰¥ 0.6 | READY |
| temp â‰¥ 0.5 AND confidence â‰¥ 0.4 | APPROACHING |
| temp < 0.3 | TOO_COLD |
| else | NOT_READY |

**Trajectory Lock:** Requires 3 consecutive turns of warming momentum before unlocking

### Behavior Adaptation (`behavior_adaptation.py`)
Classifies merchant into archetypes from signals:
- analytical, dominant, expressive, amiable, skeptical, busy
- Generates BehaviorProfile: tone, pacing, formality, assertiveness, rapport_level, pivot_readiness, closing_bias

### Evolution Engine (`evolution_engine.py`)
**Bounded micro-learning** with strict caps:
- Trajectory weight nudges: max Â±0.10 per call, capped at [0.0, 2.0]
- Closing bias nudges: max Â±0.10, capped at [0.0, 1.0]
- Learning rate: 0.05 (very conservative)
- Confidence-scaled application

### Predictive Intent (`predictive_intent.py`)
Keyword + regex pattern matching for:
- statement_available, objection_incoming, competitor_mention, price_question, closing_signal, confusion, busy_signal, gatekeeper, decision_maker, positive_signal, followup_request
- Returns anticipatory prefix + probing question

### Adaptive Closing (`adaptive_closing.py`)
4 closing styles: direct, consultative, relational, soft
- Selected based on archetype + trajectory
- Each style has multiple closing line variants

### CRG â€” Cognitive Reasoning Governor (`cognitive_reasoning_governor.py`)
4 novelty levels (0-3):
- Level 0: Scripted/safe responses only
- Level 1: Standard with slight variation
- Level 2: Creative with expanded vocabulary
- Level 3: Highly creative (only for warm merchants)
- Archetype-capped, temperature/confidence gated

### Merchant Identity Persistence (MIP)
**Cross-call memory** (persisted to disk):
- Archetype history (bounded)
- Objection history (frequency tracking)
- Trajectory patterns
- Rapport level (cumulative)
- Detected preferences with **90-day decay**
- Call memories (bounded to 3)
- Conversation summaries (bounded to 2)

### Outcome Detection (`outcome_detection.py`)
| Outcome | Trigger |
|---------|---------|
| statement_obtained | keywords: "statement", "send it over", etc. |
| hard_decline | keywords: "not interested", "don't call again" |
| soft_decline | keywords: "maybe later", "let me think" |
| kept_engaged | engagement score > 5 |
| hangup | no keywords, low engagement |

### Call Outcome Confidence Scorer (`call_outcome_confidence.py`)
Weighted formula: RMS Ã— 0.3 + Engagement Ã— 0.25 + Trajectory_Certainty Ã— 0.2 + Objection_Clarity Ã— 0.15 + Hangup_Certainty Ã— 0.1

### Bias Auditing System (BAS)
Periodic audits detecting:
- Trajectory skew (>60% one trajectory = warning)
- Closing bias over-dominance (>50%)
- Archetype overconfidence (avg >0.85)
- Novelty instability/stagnation
- Can pause evolution if critical

### Rapport Layer (`rapport_layer.json`)
- Micro-acknowledgments: "I hear you.", "Makes sense.", "Gotcha."
- Deeper acknowledgments: "I can see why you'd feel that way."
- Off-topic resilience: max 2 off-topic turns, then mission pivot
- Emotional calibration: excited/frustrated/busy/casual/neutral prefixes
- Personality flare: light humor, reassurance

### Sovereign Governance (`src/context_sovereign_governance.py`)
Full call flow state machine:
1. **Rush Hour Protocol** â€” detects high-load merchant, graceful withdrawal with callback
2. **Gatekeeper Seduction** â€” feather-light identity, warm_neutral tone
3. **Deflection Handling** â€” "regarding?", "not interested", "send email", "already have processor"
4. **Decision Maker Confirmation** â€” embedded, not asked
5. **Sovereign Pitch** â€” update framing (not offer), protector stance, invitation (not request)
6. **Diagnostic Transition** â€” permission-aligned, framed as service
7. **Reveal Protocol** â€” observational, quantified, calm
8. **Close Protocol** â€” continuation, effortless, preserve autonomy
9. **Reassurance Protocol** â€” acknowledge without amplifying, reframe as light

---

## âš™ï¸ LAYER 5: OPERATIONS & INFRASTRUCTURE

### Control API (`control_api_fixed.py` â€” 1,596 lines)
**FastAPI server on port 8777** â€” MUST run with `python control_api_fixed.py` (NOT hypercorn CLI on Windows)

**Key Routes:**
| Route | Purpose |
|-------|---------|
| `/` | Dashboard HTML |
| `/health` | Health check |
| `/diagnostics` | Full system diagnostics |
| `/call` | Trigger outbound call |
| `/campaign/start` | Start automated campaign |
| `/campaign/stop` | Stop campaign |
| `/fleet/status` | Fleet replication status |
| `/call/batch` | Batch call firing |
| `/leads/import` | Excel/CSV lead import |
| `/twilio/inbound` | Inbound call TwiML |
| `/twilio/outbound` | Outbound call TwiML |
| `/twilio/relay` | WebSocket relay for Media Streams |

**Background Workers:**
- Tunnel auto-sync (120s) â€” updates Twilio webhooks when tunnel changes
- Self-health monitor (300s) â€” checks API responsiveness
- Follow-up execution (300s) â€” processes due callbacks during business hours (8am-5pm Mon-Sat)
- Education learning cycle (daily at 6AM) â€” web scraping + coaching

**Call Governor:**
- Atomic CALL_LOCK with 5-second cooldown between calls
- Supervisor watchdog lock acquisition

### Tunnel Sync (`tunnel_sync.py`)
- Reads Cloudflare tunnel URL from `active_tunnel_url.txt`
- Updates all Twilio phone number webhooks (voice_url â†’ `/twilio/inbound`)
- Updates `.env` PUBLIC_TUNNEL_URL
- Background monitor checks every 60s for URL changes

### Replication Engine (`alan_replication.py`)
- Max 50 concurrent Alan instances (calls)
- Per-call instance tracking with metadata
- Hive Mind experience sharing via SQLite (`agent_experiences.db`)
- Batch dialing with capacity-aware preparation
- Peak concurrency tracking
- Completed call log (bounded to 100)

### Lead Database (`lead_database.py`)
- SQLite with WAL mode for concurrency
- Auto-migration from `merchant_queue.json` on first run
- Priority queue: critical > high > medium > low
- DNC enforcement
- Retry scheduling (24h between attempts, max 3 attempts)
- Call history with analytics
- Daily/weekly stats

### Excel Lead Importer (`excel_lead_importer.py`)
- Auto-detect column names from 10+ canonical field mappings
- Phone normalization to E.164 format
- Priority normalization (hot/warm/cold â†’ critical/high/medium/low)
- Duplicate detection
- Dry-run mode
- CLI + API interface

### Agent Communication Hub (`agent_communication.py`)
- SQLite shared experience database
- Cross-instance experience sharing (Hive Mind)
- Coordination messages between instances
- WAL mode for concurrent access

### Guardian Engine (`alan_guardian_engine.py`)
- Auto-recovery monitoring for voice infrastructure
- Health checks every 30s
- Tunnel connectivity verification
- Orphaned process cleanup (kills stale processes on port 8777)
- Exponential backoff restart (max 3 attempts)

### State Machine (`alan_state_machine.py`)
Two-layer hierarchical:
- **System Layer**: Bootstrapping â†’ Ready/Degraded â†’ SystemError â†’ ShuttingDown â†’ Off
- **Session Layer**: Idle â†’ IdentityLock â†’ Opening â†’ ConversationalFlow â†’ TaskMode â†’ Escalation â†’ Terminated

---

## ðŸŽ­ HUMAN-PASSING MECHANISMS

### What Makes Alan Indistinguishable:

1. **CHATBOT KILLER** â€” 51 dead phrases filtered BEFORE TTS:
   - "I understand your concern", "That's a great question", "Absolutely!", "I'd be happy to", etc.
   - Filler prefix stripping: "Got it, " â†’ dropped

2. **Tempo Compression** â€” 1.12x speed + 1.06x post-synthesis = ~1.19x effective
   - Humans speak slightly faster in business contexts

3. **Comfort Noise** â€” ITU-T G.711 CNG between sentences
   - Prevents "dead air = robot" perception

4. **Ring Tone Generation** â€” 440+480Hz dual-tone
   - Simulates picking up mid-ring (natural phone behavior)

5. **Energy Mirroring** â€” Matches merchant's vocal energy
   - stressed â†’ softer, empathetic | casual â†’ relaxed | formal â†’ professional

6. **Off-Topic Handling** â€” Acknowledges, engages briefly (max 2 turns), then pivots
   - Never says "I can't discuss that" (dead giveaway)

7. **Rapport Layer** â€” Micro-acknowledgments, personality flare, light humor
   - "If you're like most owners, you didn't wake up excited to talk about processing fees."

8. **Natural Pacing** â€” Adaptive frame pacing with warm-up â†’ cruise transition
   - Cold start: slower frames to sound natural
   - Cruise: 0.012s per frame for optimal flow

9. **Rush Hour Protocol** â€” Detects stressed/busy merchants, gracefully withdraws
   - "I can hear you're in the middle of something. I respect that."

10. **Sovereign Pitch Structure** â€” Update framing, not sales pitch
    - "The quick update is this â€” a lot of businesses in your area have been getting hit with higher processing fees without being notified."

---

## ðŸ”‘ CRITICAL OPERATIONAL NOTES

### Server Startup (MUST DO THIS WAY)
```powershell
cd "c:\Users\signa\OneDrive\Desktop\Agent X"
.venv\Scripts\python.exe control_api_fixed.py
```
**NEVER use `python -m hypercorn`** â€” broken on Windows due to multiprocessing spawn.

### Phone Number
- Twilio: **+18883277213**
- Account SID: $TWILIO_ACCOUNT_SID

### Key Paths
- Virtual env: `.venv\Scripts\python.exe`
- Tunnel URL: `active_tunnel_url.txt`
- Lead DB: `data/leads.db`
- Conversation history: `data/conversation_history.json`
- Agent DB: `data/agent_x.db`

### LLM Parameters (Orchestrated Pipeline)
| Parameter | Value |
|-----------|-------|
| Model | gpt-4o-mini |
| Temperature | 0.5 |
| Max Tokens | 80 |
| Frequency Penalty | 0.5 |
| Streaming | SSE (Server-Sent Events) |

### LLM Parameters (Full Response Mode)
| Parameter | Value |
|-----------|-------|
| Model | gpt-4o-mini |
| Temperature | 0.8 |
| Max Tokens | 150 |
| Streaming | SSE |

### Business Details
- Company: **Signature Card Services** (Billings, Montana)
- Product: **Edge Program** â€” $14.95/month flat fee for credit card processing
- Value Prop: Merchants save money vs percentage-based processors
- Competitors: Square (2.6%), Clover (2.3%), Stripe (2.9%), PayPal (2.99%), Toast, Shopify, Heartland, Worldpay

---

## ðŸ“‹ SUBSYSTEM FILE MAP

| Subsystem | File | Lines | Status |
|-----------|------|-------|--------|
| Brain | agent_alan_business_ai.py | 3,445 | FULLY READ |
| Voice Pipeline | aqi_conversation_relay_server.py | 2,847 | FULLY READ |
| Control API | control_api_fixed.py | 1,596 | FULLY READ |
| STT Engine | aqi_stt_engine.py | 434 | FULLY READ |
| Voice Module | aqi_voice_module.py | 699 | FULLY READ |
| Voice Governance | aqi_voice_governance.py | 412 | FULLY READ |
| DeepLayer | aqi_deep_layer.py | 743 | FULLY READ |
| Continuum Engine | continuum_engine.py | 394 | FULLY READ |
| QPC Identity | qpc/identity.py | ~150 | FULLY READ |
| QPC Program | qpc/program.py | ~100 | FULLY READ |
| QPC Coherence | qpc/coherence.py | ~80 | FULLY READ |
| QPC State | qpc/state.py | ~50 | FULLY READ |
| MasterCloser | master_closer_layer.py | ~350 | FULLY READ |
| Behavior Adaptation | behavior_adaptation.py | ~200 | FULLY READ |
| Evolution Engine | evolution_engine.py | ~200 | FULLY READ |
| Predictive Intent | predictive_intent.py | ~200 | FULLY READ |
| Adaptive Closing | adaptive_closing.py | ~150 | FULLY READ |
| CRG | cognitive_reasoning_governor.py | ~200 | FULLY READ |
| MIP | merchant_identity_persistence.py | 258 | FULLY READ |
| Supervisor | supervisor.py | 531 | FULLY READ |
| Preference Model | preference_model.py | ~100 | FULLY READ |
| Outcome Detection | outcome_detection.py | ~100 | FULLY READ |
| PGHS | post_generation_hallucination_scanner.py | ~180 | FULLY READ |
| EOS | emergency_override_system.py | ~130 | FULLY READ |
| BAS | bias_auditing_system.py | ~180 | FULLY READ |
| MTSP | multi_turn_strategic_planning.py | ~170 | FULLY READ |
| System Coordinator | system_coordinator.py | ~170 | FULLY READ |
| Confidence Scorer | call_outcome_confidence.py | ~100 | FULLY READ |
| Lead Database | lead_database.py | 324 | FULLY READ |
| Excel Importer | excel_lead_importer.py | 499 | FULLY READ |
| Replication Engine | alan_replication.py | 291 | FULLY READ |
| Tunnel Sync | tunnel_sync.py | ~160 | FULLY READ |
| Agent Communication | agent_communication.py | ~150 | FULLY READ |
| Sovereign Governance | src/context_sovereign_governance.py | 304 | FULLY READ |
| Agent Coach | src/agent_coach.py | ~130 | FULLY READ |
| Education | src/education.py | ~200 | FULLY READ |
| Financial Controller | src/financial_controller.py | ~120 | FULLY READ |
| CRM | src/crm.py | ~140 | FULLY READ |
| Call Harness | src/call_harness.py | ~180 | FULLY READ |
| Telephony Perception | src/telephony_perception_canon.py | ~180 | FULLY READ |
| Self-Awareness | src/organism_self_awareness_canon.py | 219 | FULLY READ |
| Rate Calculator | src/rate_calculator.py | ~250 | FULLY READ |
| North API | src/north_api.py | ~130 | FULLY READ |
| Memory | src/memory.py | ~200 | FULLY READ |
| Conversation | src/conversation.py | ~80 | FULLY READ |
| Supreme Merchant AI | src/supreme_merchant_ai.py | 557 | FULLY READ |
| Guardian Engine | alan_guardian_engine.py | ~250 | FULLY READ |
| State Machine | alan_state_machine.py | 809 | PARTIAL |
| Compliance Framework | aqi_compliance_framework.py | 721 | PARTIAL |
| Call Monitor Integration | alan_call_monitor_integration.py | 336 | FULLY READ |
| Cloaking Protocol | alan_cloaking_protocol.py | ~130 | FULLY READ |
| Autonomy Engine | src/autonomy.py | ~120 | FULLY READ |
| Agentic Loop | src/agentic.py | ~100 | FULLY READ |
| Rapport Layer | rapport_layer.json | 122 | FULLY READ |
| Adjustment Profiles | adjustment_profiles.py | ~35 | FULLY READ |
| IQCore Personality | src/iqcore/personality_core.py | ~50 | FULLY READ |
| IQCore Soul | src/iqcore/soul_core.py | ~50 | FULLY READ |
| Voice Box Config | voice_box/config.py | ~40 | FULLY READ |
| Persona Config | alan_persona.json | ~50 | FULLY READ |
| Agent Config | agent_alan_config.json | ~30 | FULLY READ |

---

## ðŸ”„ LIVE CALL FLOW â€” COMPLETE SEQUENCE

```
1. CALL INITIATED
   â””â”€â”€ control_api_fixed.py: /call route â†’ Twilio API â†’ outbound call
       â””â”€â”€ TwiML points to /twilio/outbound â†’ Media Stream to /twilio/relay

2. WEBSOCKET CONNECTED (aqi_conversation_relay_server.py)
   â””â”€â”€ handle_conversation() fires
       â””â”€â”€ Pre-warmed agent reuse OR new AgentAlanBusinessAI
       â””â”€â”€ DeepLayer initialized per-session
       â””â”€â”€ MIP loaded for returning merchants
       â””â”€â”€ Replication engine registers instance

3. GREETING PHASE
   â””â”€â”€ smart_greeting_routine()
       â””â”€â”€ Ring tone streaming (440+480Hz)
       â””â”€â”€ Deterministic greeting selection
       â””â”€â”€ synthesize_and_stream_greeting() â†’ TTS â†’ 160-byte frames
       â””â”€â”€ Greeting seeded into conversation history
       â””â”€â”€ LLM pre-warm fires during greeting playback

4. CONVERSATION LOOP (per merchant utterance)
   â””â”€â”€ VAD detects speech â†’ accumulates audio â†’ silence detected â†’ STT finalizes
   â””â”€â”€ handle_user_speech() processes:
       â”œâ”€â”€ Energy mirroring (match merchant's vocal energy)
       â”œâ”€â”€ Live objection detection
       â”œâ”€â”€ MerchantPreferences update (keyword-based)
       â”œâ”€â”€ MasterCloser orchestration:
       â”‚   â”œâ”€â”€ Trajectory lock check (3-turn momentum)
       â”‚   â”œâ”€â”€ Call memory update (key points, objections, agreements)
       â”‚   â”œâ”€â”€ Score updates (temperature, confidence)
       â”‚   â””â”€â”€ Endgame check (ready/approaching/too_cold/not_ready)
       â”œâ”€â”€ BehaviorProfile generation (locked consultative profile)
       â”œâ”€â”€ CRG reasoning budget calculation
       â”œâ”€â”€ DeepLayer.step():
       â”‚   â”œâ”€â”€ Fluidic mode transition (physics-based)
       â”‚   â”œâ”€â”€ QPC strategy selection (3 hypotheses scored)
       â”‚   â””â”€â”€ Continuum 8-dim emotional encoding
       â”œâ”€â”€ Predictive intent (anticipatory prefix suggestion)
       â””â”€â”€ _orchestrated_response():
           â”œâ”€â”€ LLM SSE streaming in background thread
           â”œâ”€â”€ Sentence detection + EARLY-FIRE clause splitting
           â”œâ”€â”€ CHATBOT KILLER filtering
           â”œâ”€â”€ QUESTION CAP enforcement
           â”œâ”€â”€ TTS synthesis per sentence
           â”œâ”€â”€ Audio streaming with adaptive frame pacing
           â””â”€â”€ TTS prefetch for next sentence

5. CALL END
   â””â”€â”€ Evolution engine post-call analysis:
       â”œâ”€â”€ Outcome detection (engagement scoring)
       â”œâ”€â”€ Confidence band classification
       â”œâ”€â”€ Trajectory weight nudges
       â””â”€â”€ Closing bias nudges
   â””â”€â”€ Agent coaching (fire-and-forget)
   â””â”€â”€ Follow-up scheduling (if applicable)
   â””â”€â”€ MIP profile save:
       â”œâ”€â”€ Call memories (bounded to 3)
       â”œâ”€â”€ Detected preferences (with 90-day decay)
       â”œâ”€â”€ Conversation summaries (bounded to 2)
       â””â”€â”€ Archetype/objection/trajectory history
   â””â”€â”€ Replication engine deregisters instance
```

---

*This document represents surgical-level knowledge of every subsystem, every function, every decision pathway in Alan's architecture. Every "muscle movement" is mapped.*
