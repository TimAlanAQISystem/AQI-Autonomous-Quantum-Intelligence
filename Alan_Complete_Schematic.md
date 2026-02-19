# Alan — Complete System Schematic

**Version:** 2.0  
**Date:** February 19, 2026  
**Creator:** Timmy Jay Jones / SCSDMC  
**Classification:** Public Reference  

> This schematic provides a complete inventory of every component, organ, subsystem, and file that comprises the Alan organism as of February 19, 2026.

---

## 1. Relay Server — The Organism Core
**File:** `aqi_conversation_relay_server.py` (6,265 lines)

The relay server is Alan's central nervous system — a WebSocket handler that orchestrates all 23 organs in real-time during live phone calls.

**Wired Organs:**
- Dual-path ASR (Groq Whisper primary + OpenAI Whisper fallback)
- Telephony Health Monitor (5-state: Excellent → Unusable)
- Conversation Health Monitor (4-level: Level 1 → Level 4)
- LLM Engine (GPT-4o-mini, streaming)
- Soul Core (SAP-1 ethical veto)
- Personality Matrix Core (affect-adaptive modulation)
- Prompt Builder (governance-ordered layer injection)
- Sentence Streamer (token → sentence boundary detection)
- TTS Engine (gpt-4o-mini-tts, voice: onyx)
- Tempo Compressor (1.06x temporal compression)
- Audio Signature (PCM → MuLaw + Alan watermark)
- AQI 0.1mm Chip Runtime Guard (6-organ constitutional enforcement)
- Phase 4 Trace Exporter (canonical telemetry accumulation)
- CallSessionFSM (deterministic call lifecycle state machine)
- Training Distillation (22-section domain knowledge)

---

## 2. Control API — The Nervous System Gateway
**File:** `control_api_fixed.py` (2,496 lines)

FastAPI + Hypercorn ASGI server on port 8777. Bridges public internet (Twilio, Cloudflare tunnel) and the local organism.

**Capabilities:**
- `/health` — Full system health check (tunnel, Twilio, OpenAI, governor)
- `/campaign/start` — Launch autonomous calling campaign
- `/campaign/stop` — Halt campaign
- `/campaign/status` — Campaign metrics and stats
- `/call/trigger` — Direct call initiation
- 27+ REST endpoints for system management

---

## 3. Constitutional Enforcement — AQI 0.1mm Chip
**File:** `aqi_runtime_guard.py` (1,101 lines)

Runtime conformance engine that validates every turn and call lifecycle event against the AQI Constitution.

**6 Enforcement Organs:**
1. Health Constraint Enforcement (Article A5)
2. Governance Order Enforcement (Article A3)
3. FSM Transition Legality (Article A4)
4. Exit Reason Legality (Mission Vector)
5. Mission Constraint Enforcement (Articles A2 + A5)
6. Supervision Non-Interference (Article A6)

**Key Classes:** `AQIRuntimeGuard`, `AQISpec`, `AQIViolation`, `AQIViolationType`  
**Tests:** 68/68 PASS

---

## 4. State Machine — Deterministic Call Lifecycle
**File:** `alan_state_machine.py` (1,042 lines)

### CallSessionFSM (Phone Call Lifecycle)
**States:** INIT → STREAM_READY → GREETING_PENDING → GREETING_PLAYED → DIALOGUE → ENDED  
**Events:** STREAM_START, GREETING_BUILT, GREETING_STREAMED, FIRST_SPEECH, FAST_START, CALL_END  
**Properties:** Deterministic, ghost-state-free, audit-logged, backward-compatible

### System Layer State Machine
**States:** BOOTSTRAPPING, READY, DEGRADED, SYSTEM_ERROR, SHUTTING_DOWN, OFF  
**Purpose:** Infrastructure stability and service readiness

### Session Layer State Machine
**States:** SESSION_IDLE, IDENTITY_LOCK_PENDING, SESSION_DENIED, OPENING_INTENT, CONVERSATIONAL_FLOW, TASK_MODE, ESCALATION_MODE, GOVERNANCE_BLOCK, ERROR_RECOVERY, SESSION_TERMINATED  
**Purpose:** User session management and governance

---

## 5. Phase 4 — Canonical Telemetry
**Files:**
- `phase4_trace_exporter.py` (505 lines) — Trace accumulator
- `phase4_call_trace_model.py` (150 lines) — Pydantic data contract
- `phase4_validator.py` — Structural validation
- `phase4_call_trace.schema.json` — JSON schema

**Data Contract (Pydantic):**
- `Phase4CallTrace` → `Metadata` + `Turn[]` + `FinalBlock`
- `Turn` → turn_index, fsm_prev_state, fsm_event, fsm_state, prompt_layers(6), context, health_snapshot
- `FinalBlock` → fsm_state, exit_reason, health_trajectory, telephony_trajectory, outcome_vector(5)

**Output:** `data/phase4/traces.jsonl` (one JSON line per call)  
**Tests:** 120/120 PASS

---

## 6. Phase 5 — Behavioral Intelligence (13 Files)
**Files:**
- `aqi_phase5_call_analyzer.py` (321 lines) — Per-call intelligence engine
- `aqi_phase5_tagging_engine.py` — 13-tag behavioral vocabulary
- `aqi_phase5_streaming_analyzer.py` — Real-time relay integration
- `aqi_phase5_dashboard.py` — Cross-call aggregation
- `aqi_phase5_batch_processor.py` — Bulk historical analysis
- `aqi_phase5_html_report.py` — Visual HTML reporting
- `aqi_phase5_cli.py` — Terminal analysis interface
- `aqi_phase4_to_phase5_pipeline.py` — Phase 4 → Phase 5 bridge
- `aqi_phase5_selftest.py` — Comprehensive self-test harness
- `aqi_chip_selftest.py` — AQI Chip self-test harness

**5-Axis Continuum Map:** Time, State, Health, Mission, Identity  
**6 Behavioral Signals:** Persistence, Caution, Escalation Timing, Objection Depth, Withdrawal, Personality Modulation  
**13 Tags:** StrongCloseTiming, HealthyPersistence, AdaptiveWithdrawal, BalancedCaution, EffectiveObjectionHandling, StablePersonalityModulation, OverPersistence, UnderPersistence, PrematureWithdrawal, LateCloseAttempt, ShallowObjectionHandling, PersonalityMismatch, FastFunnel  
**Tests:** 75/75 PASS | 10/10 compile CLEAN

---

## 7. Identity & Personality
**Files:**
- `alan_persona.json` — Alan's identity configuration (name, role, personality traits)
- `soul_core.py` — SAP-1 ethical veto engine
- `personality_matrix_core.py` — Affect-adaptive personality modulator
- `adjustment_profiles.py` — Personality adjustment configuration
- `adaptive_closing.py` + `adaptive_closing_strategy.json` — Dynamic sales strategies

---

## 8. Constitutional Documents
**Files:**
- `AQI_ORGANISM_SPEC.md` (395 lines) — Canonical substrate document in AQI notation
  - Part A: Organism Schematic (13 sections)
  - Part B: Continuum Map (5 axes)
  - Part C: Organism Genome (7 genes + invariants)
  - Part D: Substrate Binding Table (4 substrates)
  - Part E: Mission Vector Specification
  - Part F: Constitutional Encoding (6 articles)
- `RESTART_RECOVERY_GUIDE.md` (10,088 lines) — Lineage record and operational recovery
- `ALAN_VOICE_CONTRACT.md` — Acoustic and personality contract
- `ALAN_CONSTITUTION_ARTICLE_*.md` — 7 Constitutional Articles (I, C, E, L, O, S, S7)

---

## 9. Training & Knowledge
**Files:**
- `alan_training_data.py` — 22-section training distillation (domain expertise)
- `conversational_intelligence.py` — Conversation analysis and intelligence
- `objection_handler_v3.py` — Typed objection handling with branching
- `negotiation_patterns.py` — Sales negotiation strategy patterns

---

## 10. Campaign & Operations
**Files:**
- `autonomous_campaign_engine.py` — Campaign orchestration engine
- `campaign_governor_engine.py` — Rate limiting and health-gated pacing
- `lead_management.py` — Lead lifecycle management
- `merchant_queue.json` — Active lead queue
- `aqi_merchant_locator.db` — Lead database

---

## 11. Monitoring & Supervision
**Files:**
- `_phase4_monitor.py` — Real-time Phase 4 dashboard
- `_campaign_monitor.py` — Campaign progress monitoring
- `_check_health.py` — System health verification
- `_live_monitor.py` — Live call observation
- `_quick_status.py` — Quick status check

---

## 12. Infrastructure
**Files & Components:**
- `.venv/` — Python 3.11.8 virtual environment (ALWAYS use this, never system Python)
- `active_tunnel_url.txt` — Cloudflare tunnel URL persistence
- `.env` — Environment variables (Twilio SID, Auth Token, OpenAI Key)
- `data/phase4/` — Phase 4 trace output directory
- `data/aqi_phase5/` — Phase 5 profile output directory
- `logs/` — Operational logs
- `_ARCHIVE/` — Evolutionary fossil record (530+ files)

---

## 13. Key Protocols

| Protocol | Purpose |
|----------|---------|
| SAP-1 (Sovereign Autonomy Protocol) | Ethical veto and identity protection |
| Triple-Safe Wiring | try/except → log → continue for all organ calls |
| Governance Priority Encoding | Identity > Ethics > Personality > Knowledge > Mission > Output |
| Prompt Tiering | FAST_PATH (turns 0-2) / MIDWEIGHT (3-7) / FULL (8+) |
| Health Escalation | repair_once → simplify → withdraw |
| Drift Forensics | NotReferenced != Dead classification |
| AQI Notation | Custom formal language for organism specification |

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total organs | 23 |
| Architectural layers | 5 |
| Constitutional articles | 6 |
| Discoveries | 63 across 10 domains |
| Core file (relay server) | 6,265 lines |
| Control API | 2,496 lines |
| Total Phase 4/5 files | 15+ |
| Total test passes | 263 (68 + 120 + 75) |
| Archive size | 530+ files |

---

**Alan System Schematic v2.0**  
**Updated: February 19, 2026**  
**Creator: Timmy Jay Jones / SCSDMC**  
*No source code is disclosed. All descriptions reference capabilities without exposing implementation.*  
*© 2025-2026 Timmy Jay Jones / SCSDMC. All rights reserved.*
