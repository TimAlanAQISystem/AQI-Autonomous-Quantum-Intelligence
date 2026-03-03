# AGENT X / ALAN AI — AUTONOMOUS CAPABILITIES AUDIT
### Generated: February 23, 2026
### Workspace: `c:\Users\signa\OneDrive\Desktop\Agent X`

---

## TABLE OF CONTENTS
1. [Background Workers (Boot-Time Tasks)](#1-background-workers-boot-time-tasks)
2. [Numbered Organs (v4.1 ARMS-LEGS-REACH)](#2-numbered-organs-v41-arms-legs-reach)
3. [Unnumbered Organs (Core Subsystems)](#3-unnumbered-organs-core-subsystems)
4. [Agent Capabilities (agent_1, agent_2, agent_3, Agent X)](#4-agent-capabilities)
5. [IQ Cores (5-Core Cognitive Architecture)](#5-iq-cores-5-core-cognitive-architecture)
6. [Campaign / Dialing Automation](#6-campaign--dialing-automation)
7. [Learning / Self-Improvement Systems](#7-learning--self-improvement-systems)
8. [Monitoring / Self-Healing Systems](#8-monitoring--self-healing-systems)
9. [Deep Cognitive Engines](#9-deep-cognitive-engines)
10. [Telephony Resilience & Governance](#10-telephony-resilience--governance)

---

## 1. BACKGROUND WORKERS (Boot-Time Tasks)

All launched in `control_api_fixed.py` → `lifespan()` function (lines 320–400).

| # | Worker | File | Line | Interval | What It Does |
|---|--------|------|------|----------|--------------|
| 1 | **Background Tunnel Monitor** | `control_api_fixed.py` | L332 | 30s | Monitors `active_tunnel_url.txt` for Cloudflare tunnel URL changes. When the tunnel rotates, auto-syncs the new URL to all Twilio phone number webhooks (voice URL, status callback URL). Prevents broken inbound/outbound calls after tunnel restart. Uses `tunnel_sync.py`. |
| 2 | **Governor Watchdog** | `control_api_fixed.py` | L342 | 30s check, 120s max lock | Auto-unlocks the call governor (`CALL_IN_PROGRESS` flag) if a Twilio status callback never arrives. Prevents permanent call lock-out where no new outbound calls can fire. Uses `telephony_resilience.py → governor_watchdog_loop()`. |
| 3 | **FSM Watchdog** | `control_api_fixed.py` | L358 | 10s (shadow mode) | Monitors the Call Lifecycle FSM (`call_lifecycle_fsm.py`) for stuck states. If a call gets stuck in a non-terminal state beyond its timeout, the FSM auto-transitions to IDLE. Currently runs in "shadow mode" (observes, doesn't override governor). |
| 4 | **Self-Health Monitor** | `control_api_fixed.py` | L366 | 300s (5 min) | Periodically checks tunnel reachability (HTTP GET to tunnel/health), Twilio credential presence, OpenAI API key presence. Logs warnings if anything is wrong. Reports results to Supervisor. Defined at L2186. |
| 5 | **ARDE (Autonomous Repair & Diagnostics Engine)** | `control_api_fixed.py` | L372 | 60s cycle | Full self-healing subsystem. Monitors 7 subsystems (Alan, Agent X, TTS, greeting cache, tunnel, Twilio, OpenAI). Detects degradation, attempts autonomous repair, logs all actions. Has VIP Launch Mode with tightened thresholds. Uses `autonomous_repair_engine.py`. |
| 6 | **System Health Guardian** | `control_api_fixed.py` | L378 | 30s fast, deep every 5th pass | Infrastructure-level watchdog filling ARDE's blind spots: tunnel staleness, tunnel expiration, credential liveness (actual API calls), disk space, memory pressure, log rotation, database integrity, WebSocket staleness, webhook reachability. Uses `system_health_guardian.py` (1036 lines). |
| 7 | **Follow-Up Execution Worker** | `control_api_fixed.py` | L382 | 300s (5 min) | Checks SQLite `follow_ups` table for due callback/follow-up tasks. Automatically triggers outbound calls via internal `/call` endpoint during business hours (8am-5pm Mon-Sat). Honors email/nurture tasks (logged for manual review until SMTP configured). Defined at L2022. Uses `src/follow_up.py`. |
| 8 | **Education Learning Cycle** | `control_api_fixed.py` | L386 | Daily at 6 AM | Runs Alan's self-education module: scrapes fintech news from TechCrunch, Payments Dive, Retail Dive. Stores insights in knowledge_base DB table. Also runs coaching analysis on the most recent conversation via AgentCoach (LLM-based). Defined at L2103. Uses `src/education.py` and `src/agent_coach.py`. |

---

## 2. NUMBERED ORGANS (v4.1 ARMS-LEGS-REACH)

All wired in `aqi_conversation_relay_server.py` (8996 lines), imported at the top.

| Organ # | Name | File | Line (import) | What It Does |
|---------|------|------|---------------|--------------|
| **24** | **Retrieval Cortex** | `organs_v4_1/organ_24_retrieval_cortex.py` | L313-320 | Mid-call RAG knowledge retrieval. When the merchant asks a question Alan doesn't have context for, this organ queries a knowledge store in real-time and injects the answer into the LLM prompt. |
| **25** | **Warm Handoff & Escalation** | `organs_v4_1/organ_25_handoff_escalation.py` | L357-364 | Human closer transfer system. When merchant says "talk to a person" / "speak to a manager", detects the escalation request, gets consent, and transfers the call to a human closer. Has `HandoffReason` enum and consent confirmation patterns. |
| **26** | **Outbound Comms** | `organs_v4_1/organ_26_outbound_comms.py` | L476-480 | Mid-call SMS/email/link follow-up pipeline. When merchant says "text me the details" or "email me", queues an outbound SMS or email with relevant info. Supports `Channel` enum (SMS, email, link). |
| **27** | **Language Switching** | `organs_v4_1/organ_27_language_switch.py` | L435-440 | Multilingual STT/TTS/prompt pipeline. Detects when merchant wants to speak Spanish, French, or Portuguese. Switches the entire pipeline (speech recognition, text-to-speech, system prompt) to the detected language. |
| **28** | **Calendar & Scheduling** | `organs_v4_1/organ_28_calendar_scheduling.py` | L407-412 | Real-time appointment booking engine. Detects scheduling requests ("set up a meeting", "book an appointment"), proposes time slots, handles confirmation/decline flows. |
| **29** | **Inbound Context Injection** | `organs_v4_1/organ_29_inbound_context.py` | L398-403 | Callback memory system. When a merchant calls BACK (inbound), this organ looks up the previous conversation context and injects it into Alan's prompt so he remembers what was discussed. Has `INBOUND_SCRIPTS` for different callback scenarios. |
| **30** | **Prosody Analysis** | `organs_v4_1/organ_30_prosody_analysis.py` | L334-341 | Emotional perception layer with 7-emotion tone detection. Analyzes text-based emotional cues in merchant speech to detect frustration, excitement, hesitation, confidence, anger, confusion, warmth. Feeds emotional state into NFC for behavioral adaptation. |
| **31** | **Objection Learning** | `organs_v4_1/organ_31_objection_learning.py` | L343-355 | Adaptive objection learning loop. Learns from uncaptured objection phrases that the main objection handler (Organ 6) misses. Maintains candidate → promoted pipeline: new objection phrases start as candidates, get promoted after 3+ occurrences. Persists learning to disk across sessions. |
| **32** | **Call Summarization** | `organs_v4_1/organ_32_summarization.py` | L366-373 | Structured call intelligence summary pipeline. At call end, generates a structured summary (outcome, key topics, merchant sentiment, next steps, objections encountered). Stores in `SUMMARY_STORE`. |
| **33** | **CRM Integration** | `organs_v4_1/organ_33_crm_integration.py` | L375-382 | Pipeline-aware CRM push system. After call completion, pushes call results into CRM with durable queue (`CRM_QUEUE_PATH`). Tracks `SyncStatus` (pending, synced, failed). |
| **34** | **Competitive Intel** | `organs_v4_1/organ_34_competitive_intel.py` | L322-332 | Competitor data store and positioning engine. Tracks competitor information (names, pricing, weaknesses). When merchant mentions a competitor, provides Alan with real-time positioning data and talking points. Module-level singleton shared across all sessions. |
| **35** | **In-Call IQ Budgeting** | `organs_v4_1/organ_35_incall_budget.py` | L384-393 | Cognitive governance and burn accounting. Tracks per-call LLM token/cost usage. Assigns `CallTier` and `BurnState`. Enforces `THROTTLE_RULES` when budget is exceeded (reduce organ calls, use fallback strategies). Has `ORGAN_COST_MAP` and `BUDGET_TIERS`. |

---

## 3. UNNUMBERED ORGANS (Core Subsystems)

Wired in `aqi_conversation_relay_server.py` at the top-level imports.

| Organ | File | Line | What It Does |
|-------|------|------|--------------|
| **Agent X Conversation Support** | `agent_x_conversation_support.py` | L60-65 | Off-topic conversation intelligence. When the merchant goes off-script, this organ provides Alan with contextual responses for non-sales topics. |
| **IQ Core Orchestrator** | `iqcores/orchestrator.py` | L69-74 | 5-core cognitive architecture (Reasoning, Governance, Learning, Social Graph, Voice Emotion). See Section 5 for details. |
| **Replication Engine** | `alan_replication.py` | L86-92 | Fleet replication — manages concurrent Alan instances (calls). Tracks capacity, enforces max_instances, provides batch dialing, and experience sharing (Hive Mind). |
| **Call Monitor Integration** | `alan_call_monitor_integration.py` | L94-110 | Live call visibility — 8 monitoring hooks (call_start, greeting_sent, agent_wired, merchant_speech, alan_response, call_error, call_warning, call_end). |
| **Call Data Capture** | `call_data_capture.py` | L113-128 | Non-intrusive capture system (1155 lines). Records full transcripts, per-turn timing, Deep Layer state, Master Closer state, evolution adjustments, coaching scores. Zero latency impact (background thread writes). |
| **Call-Type Classifier** | `call_type_classifier.py` + `call_feature_aggregator.py` | L131-145 | Fusion classifier that categorizes calls (sales, retention, support, spam, IVR, voicemail). Uses aggregated features from the call to classify in real-time. |
| **Voice Sensitizer** | `voice_sensitizer.py` | L148-157 | Real-time voice identity integrity monitor. Detects voice drift, speaker changes, and audio anomalies within sliding windows. |
| **Inbound Silence Sensitizer** | `inbound_silence_sensitizer.py` | L160-174 | Detects dead air and connection loss on the inbound audio stream. Triggers escalation or graceful exit when sustained silence is detected. |
| **Live Call Monitor** | `live_call_monitor.py` | L177-185 | Real-time call state tracking + human voice frequency detection. Determines whether a human is actually on the line (vs. IVR / voicemail / dead air). |
| **IVR Detector** | `ivr_detector.py` | L188-194 | Inline IVR/voicemail phone tree detection. Identifies when Alan is talking to an automated system and triggers appropriate behavior (hang up, leave message, or navigate menu). |
| **Environment-Aware Behavior (EAB)** | `call_environment_classifier.py` | L197-206 | First-utterance call environment classifier with 10 environment classes (quiet office, noisy restaurant, car, warehouse, etc.). Adapts Alan's speaking style (volume emphasis, pacing, vocabulary) to the detected environment. |
| **Conversational Intelligence** | `conversational_intelligence.py` | L209-215 | 7 behavioral intelligence systems: (1) DNC Compliance Interrupt, (2) Voicemail Detector, (3) Entity Classifier, (4) Repetition Breaker, (5) Latency Bridge, (6) Dead-End Detector, (7) Short-Call Outcome Fallback. |
| **DNC Manager** | `dnc_manager.py` | L218-226 | Auto-suppression system. When merchant requests removal, persists DNC flag in database. Pre-dial DNC check prevents calling blacklisted numbers. |
| **Inbound Spam Filter** | `inbound_filter.py` | L229-235 | Filters inbound spam calls (robo-callbacks, "there" callbacks). Classifies inbound calls and rejects spam. |
| **Operational Maintenance Scheduler** | `operational_maintenance.py` | L238-246 | Periodic health checks: garbage collection (every 5 min), memory monitoring (warning at 75%, critical at 85%, emergency at 92%), log rotation (every hour, max 50MB per file), cache cleanup. |
| **Deep Layer (QPC + Fluidic + Continuum)** | `aqi_deep_layer.py` | L249-255 | Unified integration of 3 cognitive frameworks: QPC Kernel (multi-hypothesis response strategy), Fluidic Kernel (physics-based mode transitions), Continuum Engine (continuous emotional/ethical context fields). Per-session instantiation, stepped every turn. |
| **Behavioral Fusion Layer** | `behavioral_fusion_engine.py` | L258-267 | Fuses Fluidic Kernel state, Continuum metrics, objection physics, and Perception Fusion into a single behavioral state vector. Outputs `BehavioralSnapshot` with health (optimal/stable/fragile/failed) and mode (normal/high_friction/stalled/recovering/collapsed). |
| **Neural Flow Cortex (NFC)** | `neural_flow_cortex.py` | L277-284 | Alan's central nervous system (2132 lines). Gathers all organ outputs, synthesizes unified 12D behavioral state, applies physics-based smoothing across ALL behavioral dimensions (warmth, assertiveness, patience, momentum, rapport). Emits natural-language guidance. Implements Mission Switch Doctrine (MISSION_CLOSE → MISSION_PRESERVE_RELATIONSHIP → MISSION_EXTRACT_LEARNINGS). |
| **Cross-Call Neural Memory (CCNM)** | `cross_call_intelligence.py` | L287-293 | Accumulated intelligence feedback loop (981 lines). Reads from call_capture.db, produces SessionSeed that pre-conditions the DeepLayer. Adjusts QPC priors (±0.15), Fluidic physics (±0.20), Continuum fields (±0.30). Requires minimum 3 calls before seeding. Cold-start safe. |
| **AQI 0.1mm Chip Runtime Guard** | `aqi_runtime_guard.py` | L296-302 | Constitutional conformance engine (1101 lines). Enforces 6 rules per turn: Health Constraint, Governance Order, FSM Transition Legality, Exit Reason Legality, Mission Constraint, Supervision Non-Interference. Defines `AQIViolationType` enum. |
| **Phase 4 Trace Exporter** | `phase4_trace_exporter.py` | L305-311 | Canonical telemetry export to `data/phase4/traces.jsonl`. Wired at 3 hooks (call_start, on_turn, call_end). Accumulates per-turn health and telephony snapshots for Phase 5 ingestion. |
| **Perception Fusion Engine** | `perception_fusion_engine.py` | (config loaded L270) | Fuses inbound silence, outbound drift, classifier scores, and transport health into single perception state. Outputs `PerceptionSnapshot` with mode (normal/IVR/voicemail/dead_air/connection_loss/audio_drift). |
| **Coaching Tags Engine** | `coaching_tags_engine.py` | (import L52) | Derives per-turn coaching tags from behavioral and perception vectors. Tags: STALL_DISCOVERY, STALL_OPENING, COLLAPSE_NEGOTIATION, COLLAPSE_CLOSING, HIGH_FRICTION_OBJECTIONS, HIGH_VISCOSITY_USER_STATE, DEAD_AIR_STT_FAILURE, IVR_LATE_DETECTION, AUDIO_DRIFT_OR_LATENCY. |

---

## 4. AGENT CAPABILITIES

| Agent | File | Lines | What It Does |
|-------|------|-------|--------------|
| **Agent 1 — Onboarding Specialist** | `agent_1.py` | 112 lines | Handles merchant onboarding calls. Uses `onboarding.py` and `compliance.py` IQcores. Shares experiences via `AgentCommunicationHub`. Learns from previous onboarding experiences. |
| **Agent 2 — Retention Specialist** | `agent_2.py` | 107 lines | Handles merchant retention calls. Uses `retention.py` and `analytics.py` IQcores. Learns from shared retention experiences. |
| **Agent 3 — Sales Specialist** | `agent_3.py` | 107 lines | Handles merchant sales calls. Uses `sales.py` and `negotiation.py` IQcores. Learns from shared sales experiences. |
| **Agent X Avatar** | `agent_x_avatar.py` | 1083 lines | Desktop GUI avatar (Tkinter) with TTS worker, speech recognition, and `AutonomyEngine`. The avatar is the interactive desktop interface for Agent X. |
| **Agent Communication Hub** | `agent_communication.py` | 143 lines | Inter-agent learning and coordination system. SQLite-backed shared experience database with two tables: `shared_experiences` (cross-agent learning) and `agent_coordination` (inter-agent messaging with priority). |
| **Autonomy Engine** | `src/autonomy.py` | 101 lines | Background thread for autonomous desktop behavior. Checks every 30 seconds. When user is idle, performs autonomous actions (check-ins, surface suggestions). Manages avatar visibility (surface/hide). |
| **Agentic Loop** | `src/agentic.py` | 91 lines | Rule-based tool planning with optional LLM backing. Maps user messages to available tools (time_awareness, greeting, wisdom). Observe → Think/Plan → Act loop. |

---

## 5. IQ CORES (5-Core Cognitive Architecture)

Located in `iqcores/` directory, orchestrated by `iqcores/orchestrator.py` (424 lines).

| Core # | Name | File | Lines | What It Does |
|--------|------|------|-------|--------------|
| **1** | **Core Reasoning** | `iqcores/core_reasoning.py` | 366 lines | Analytical brain — multi-step inference, pattern recognition, confidence scoring, hypothesis formation, context synthesis. Builds `ReasoningChain` with steps, evidence, and conclusions. |
| **2** | **Governance Audit** | `iqcores/governance_audit.py` | 402 lines | Compliance and accountability — decision audit trails, ethical compliance checks, anomaly detection, transparency reporting. Every decision Agent X makes is logged as an `AuditEntry` with compliance flags. |
| **3** | **Learning Thread** | `iqcores/learning_thread.py` | 517 lines | Adaptive learning engine — learns from call outcomes, merchant interactions, strategy effectiveness, temporal patterns. Produces `LearningRecord` entries with effectiveness scores. **This is what makes Agent X get BETTER over time.** |
| **4** | **Social Graph** | `iqcores/social_graph.py` | 408 lines | Relationship intelligence — manages entities (merchants, team, prospects), tracks trust levels, interaction history, familiarity, known facts, preferences, topics discussed, objections raised. |
| **5** | **Voice Emotion** | `iqcores/voice_emotion.py` | 571 lines | Emotional intelligence — reads emotional signals from text, tracks 8 emotional dimensions (warmth, energy, confidence, patience, empathy, humor, assertiveness, curiosity), calibrates empathy, manages tone recommendations. |

---

## 6. CAMPAIGN / DIALING AUTOMATION

| System | File | Line | What It Does |
|--------|------|------|--------------|
| **Campaign Runner** | `control_api_fixed.py` | L1578 (`_run_campaign`) | Automated sequential dialer. Pulls leads from SQLite DB, checks governor readiness, fires outbound calls with Twilio, records outcomes. Honors Regime Engine skip-checks. Triggered via `POST /campaign/start`. |
| **Campaign Start API** | `control_api_fixed.py` | L1429 | `POST /campaign/start` — starts automated campaign with configurable `max_calls` and `delay_seconds` (minimum 240s between calls). Blocked in instructor mode. |
| **Campaign Stop API** | `control_api_fixed.py` | L1462 | `POST /campaign/stop` — gracefully stops the active campaign. |
| **Batch Dialer** | `control_api_fixed.py` | L1777 (`_fire_batch_calls`) | Fires multiple calls concurrently with staggered timing (avoids Twilio rate limits). Used by the replication engine's batch dial endpoint. |
| **Regime Engine** | `regime_engine.py` | 1088 lines | Meta-organ that detects when the market changes and rewrites the dialing strategy. 5 detection classes: Timing Regime (by hour/DOW/holiday), Cultural Shift (state-level patterns), Script Performance (A/B degradation), Objection Mutation (cluster drift), Cost Explosion (per-call cost spikes). 4 faculties: Uncertainty, Anomaly, Value, Model-of-Models. |
| **Campaign Optimization Engine** | `campaign_optimization_engine.py` | 128 lines | Consumes behavioral audit summaries and produces: pattern analysis, threshold recommendations, Fluidic Kernel tuning hints, classifier/STT/TTS flags, next campaign readiness score. |
| **Auto-Dialer (DISABLED)** | `control_api_fixed.py` | L392 | Previously auto-resumed campaigns 30s after boot. **Now DISABLED** to prevent race conditions with mode switching. Campaigns require explicit `POST /campaign/start`. |

---

## 7. LEARNING / SELF-IMPROVEMENT SYSTEMS

| System | File | What It Does |
|--------|------|--------------|
| **Education Module** | `src/education.py` (184 lines) | Live web scraping of fintech news (TechCrunch, Payments Dive, Retail Dive). Parses articles, scores relevance, stores in `knowledge_base` SQLite table. Insights are injected into Alan's system prompt. Runs daily at 6 AM via the Education Learning Cycle background worker. |
| **Agent Coach** | `src/agent_coach.py` (136 lines) | LLM-based call coaching. Reads conversation history, sends to GPT for analysis, produces scores, strengths, weaknesses, and a specific action item for the next call. Coaching results stored in `coaching_logs` table. Runs daily after education cycle. |
| **Evolution Engine** | `evolution_engine.py` (306 lines) | Bounded micro-learning on Alan's performance weights. Takes call Outcome + Engagement Score → produces trajectory weight nudges, closing bias nudges, and archetype nudges. All adjustments are bounded to prevent identity drift. |
| **Cross-Call Neural Memory (CCNM)** | `cross_call_intelligence.py` (981 lines) | Accumulated intelligence feedback loop. Reads from call_capture.db, produces SessionSeed that pre-conditions DeepLayer. QPC priors ±0.15, Fluidic physics ±0.20, Continuum fields ±0.30 norm. Requires minimum 3 calls. Alan gets smarter with every call. |
| **Objection Learning (Organ 31)** | `organs_v4_1/organ_31_objection_learning.py` | Adaptive objection learning loop. New objection phrases start as candidates → promoted after 3+ occurrences. Persists to disk. Module-level singleton. |
| **Learning Thread (IQCore 3)** | `iqcores/learning_thread.py` (517 lines) | Agent X's adaptive learning — learns from call outcomes, merchant interactions, strategy effectiveness, temporal patterns. Produces `LearningRecord` entries. |
| **Phase 5 Tagging Engine** | `aqi_phase5_tagging_engine.py` (133 lines) | Classifies call behavior using Phase 5 vocabulary: 6 positive tags (StrongCloseTiming, HealthyPersistence, AdaptiveWithdrawal, BalancedCaution, EffectiveObjectionHandling, StablePersonalityModulation) and 6 warning tags (OverPersistence, UnderPersistence, PrematureWithdrawal, LateCloseAttempt, ShallowObjectionHandling, PersonalityMismatch). |
| **Coaching Tags Engine** | `coaching_tags_engine.py` | Derives per-turn coaching tags from behavioral/perception vectors for real-time performance analysis. |

---

## 8. MONITORING / SELF-HEALING SYSTEMS

| System | File | Lines | What It Does |
|--------|------|-------|--------------|
| **ARDE** | `autonomous_repair_engine.py` | 738 lines | Core self-healing engine. Monitors 7 subsystems (Alan, Agent X, TTS, greeting cache, tunnel, Twilio, OpenAI). Repair actions: REINIT_ALAN, REINIT_AGENT_X, REBUILD_GREETING_CACHE, RECONNECT_TTS, RESYNC_TUNNEL, FULL_RELAY_RESTART. Max 3 repair attempts before CRITICAL. Has VIP Launch Mode (20s cycles, 2 max attempts, traffic halt on CRITICAL). |
| **System Health Guardian** | `system_health_guardian.py` | 1036 lines | Infrastructure-level watchdog. 10 check categories: (1) Tunnel staleness, (2) Tunnel expiration, (3) Credential liveness, (4) Disk space (<500MB warn, <100MB critical), (5) Memory pressure (>85% warn, >95% critical), (6) Log rotation (>10MB), (7) Database integrity, (8) WebSocket staleness, (9) Process heartbeat, (10) Upstream/downstream cascade checks. Self-repairs where possible, escalates what it can't. Writes `guardian_heartbeat.json`. |
| **Alan Guardian Engine** | `alan_guardian_engine.py` | 248 lines | Process-level auto-recovery. Monitors control API at localhost:8777. If service goes down, attempts restart (max 3 attempts). Tracks restart count and last restart time. |
| **Governor Watchdog** | `telephony_resilience.py` | 570 lines | Auto-unlocks call governor after 120s timeout (reduced from 300s). Prevents permanent lockout if Twilio callback never arrives. 30s post-call cooldown for reflection. |
| **FSM Watchdog** | `call_lifecycle_fsm.py` | 568 lines | Monitors Call Lifecycle FSM for stuck states. Every state has a bounded timeout leading to terminal state → IDLE. No path can permanently block outbound calls. Includes COOLDOWN state for behavioral circuit-breaking. |
| **Conversation Health Monitor** | `conversation_health_monitor.py` | 340 lines | Per-turn self-awareness. 4 health levels: OPTIMAL → STRAINED (latency >3s) → COMPROMISED (repeated fallbacks, repetition) → UNFIT (persistent failure). UNFIT triggers graceful exit via FSM. |
| **Telephony Health Monitor** | imported at L56 | — | Telephony perception: tracks transport-level health (packet gaps, audio quality, connection stability). |
| **Self-Health Monitor** | `control_api_fixed.py` | L2186 | 5-minute cycle: checks tunnel reachability, Twilio creds, OpenAI key. Reports to Supervisor. |
| **Operational Maintenance** | `operational_maintenance.py` | 409 lines | Periodic GC (5 min), health checks (60s), log rotation (1 hr), memory reports (5 min). Emergency GC + cache clear at 92% memory. |
| **Supervisor** | `supervisor.py` | 850 lines | Central incident tracking system. Singleton. Records incidents with severity (info/warning/error/critical), component metadata, dependency chains. All monitoring systems report here. |
| **AQI Runtime Guard** | `aqi_runtime_guard.py` | 1101 lines | Constitutional conformance enforcement. 6 rules checked per turn and per call. Raises `AQIViolation` on breach. |

---

## 9. DEEP COGNITIVE ENGINES

| Engine | File | Lines | What It Does |
|--------|------|-------|--------------|
| **QPC-2 Chamber** | `qpc2_engine.py` | 692 lines | Unified Quantum–Continuum creativity engine. Relational worldsheet with history. Governance-grade shell with epistemic layers (ethics, boundaries, creativity, flow). |
| **Deep Layer** | `aqi_deep_layer.py` | 996 lines | Live integration of QPC Kernel (multi-hypothesis branching), Fluidic Kernel (physics-based mode transitions with inertia/viscosity), and Continuum Engine (PDE field evolution). Per-session, stepped every turn. |
| **Continuum Engine** | `continuum_engine.py` | 394 lines | Continuous field evolution (QPC Layer 2). Ethics, emotion, context, narrative fields as numpy arrays. Smooth interpolation, drift functions, no hard jumps. |
| **Neural Flow Cortex** | `neural_flow_cortex.py` | 2132 lines | Central nervous system. 12D behavioral flow harmonizer. Physics-based smoothing across all dimensions. Mission Switch Doctrine (3-state machine: CLOSE → PRESERVE_RELATIONSHIP → EXTRACT_LEARNINGS). Natural-language emission to LLM. |
| **Behavioral Fusion Engine** | `behavioral_fusion_engine.py` | 184 lines | Fuses all behavioral signals into single state vector. 5 modes: normal, high_friction, stalled, recovering, collapsed. 4 health levels. |
| **Perception Fusion Engine** | `perception_fusion_engine.py` | 154 lines | Fuses all perceptual signals. 6 modes: normal, IVR, voicemail, dead_air, connection_loss, audio_drift. |

---

## 10. TELEPHONY RESILIENCE & GOVERNANCE

| System | File | What It Does |
|--------|------|--------------|
| **Telephony Resilience Layer** | `telephony_resilience.py` (570 lines) | Atomic tunnel URL reading, centralized call creation (DRY), governor watchdog, Twilio client health validation, port pre-check, request origin validation. |
| **Tunnel Sync** | `tunnel_sync.py` (195 lines) | Auto-detects tunnel URL changes, updates Twilio webhooks, updates .env. Used standalone or by control_api. |
| **Call Lifecycle FSM** | `call_lifecycle_fsm.py` (568 lines) | Replaces boolean CALL_IN_PROGRESS with explicit state machine. States with bounded timeouts. Includes COOLDOWN state for high-friction circuit breaking. |
| **Governor Behavior Bridge** | `governor_behavior_bridge.py` | Decides governor actions (continue, soft_kill, hard_kill) based on behavioral state. |
| **Alan State Machine** | `alan_state_machine.py` | Call session FSM with flow states (OPENING, DISCOVERY, VALUE, OBJECTION, CLOSE, EXIT) and events. |
| **Voicemail Block** | `control_api_fixed.py` L2259+ | Tim's Directive: No voicemails. AMD detection → immediate call termination for machine_start/machine_end/fax (unless merchant has prior successful conversation). |

---

## SUMMARY STATISTICS

| Category | Count |
|----------|-------|
| Background Workers (boot-time) | **8** |
| Numbered Organs (v4.1) | **12** (Organs 24–35) |
| Unnumbered Organs (core) | **18** |
| Agent Modules | **7** (3 specialists + Avatar + CommHub + Autonomy + Agentic) |
| IQ Cores | **5** |
| Campaign/Dialing Systems | **6** (+ 1 disabled) |
| Learning/Self-Improvement | **7** |
| Monitoring/Self-Healing | **11** |
| Deep Cognitive Engines | **6** |
| Telephony Resilience | **6** |
| **TOTAL AUTONOMOUS CAPABILITIES** | **~86 distinct systems** |

---

## KEY AUTONOMOUS BEHAVIORS (What Runs Without Human Intervention)

1. **Tunnel failover** — tunnel URL changes are auto-synced to Twilio every 30s
2. **Call governor auto-unlock** — stuck locks auto-release after 120s
3. **Self-healing** — ARDE repairs 7 subsystems autonomously (60s cycles)
4. **Infrastructure monitoring** — Guardian checks 10 infrastructure categories (30s cycles)
5. **Follow-up callbacks** — promised callbacks auto-execute during business hours (5-min checks)
6. **Daily education** — Alan scrapes fintech news and learns at 6 AM daily
7. **Daily coaching** — LLM analyzes last conversation and produces coaching for next call
8. **Cross-call learning** — CCNM seeds each new call with intelligence from all previous calls
9. **Objection learning** — Organ 31 learns new objection phrases automatically (disk-persistent)
10. **Campaign dialing** — automated lead-by-lead dialing with Regime Engine skip checks
11. **DNC auto-suppression** — merchant removal requests auto-persisted and enforced
12. **Memory management** — GC, log rotation, cache cleanup on automated schedules
13. **Behavioral adaptation** — NFC harmonizes all organ outputs into unified behavioral flow in real-time
14. **Constitutional enforcement** — AQI Guard checks 6 rules every turn without human oversight
