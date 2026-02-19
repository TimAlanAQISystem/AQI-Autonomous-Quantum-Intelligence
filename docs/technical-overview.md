# AQI Technical Overview

**Version:** 2.0  
**Date:** February 19, 2026  
**Classification:** Public Reference  

## Introduction

AQI (Autonomous Quantum Intelligence) is a constitutionally-governed autonomous intelligence deployed on telephony substrate. The organism — named Alan — conducts live phone calls with real merchants, operating as a Senior Account Executive at Signature Card Services.

This is not a conceptual framework. Every subsystem described below is running in production. The system has been built from first principles over 7+ months by a single engineer (Timmy Jay Jones) and represents 63 verified discoveries across 10 domains.

## Core Architecture

### 5-Layer Organism Topology

AQI is organized as 5 concentric layers, each containing specialized organs:

```
┌─────────────────────────────────────────────┐
│  Layer 5: SUPERVISION (4 organs)            │
│    Phase 4 Telemetry, Phase 5 Intelligence  │
│  ┌───────────────────────────────────────┐  │
│  │  Layer 4: GOVERNANCE (5 organs)       │  │
│  │    AQI Chip, FSM, Constitution        │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │  Layer 3: COGNITION (4 organs)  │  │  │
│  │  │    LLM, Ethics, Personality     │  │  │
│  │  │  ┌───────────────────────────┐  │  │  │
│  │  │  │  Layer 2: PERCEPTION (5)  │  │  │  │
│  │  │  │    ASR, Health Monitors   │  │  │  │
│  │  │  │  ┌─────────────────────┐  │  │  │  │
│  │  │  │  │ Layer 1: TELEPHONY  │  │  │  │  │
│  │  │  │  │  WebSocket, Codecs  │  │  │  │  │
│  │  │  │  └─────────────────────┘  │  │  │  │
│  │  │  └───────────────────────────┘  │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**Key Invariant:** Inner layers cannot reference outer layers. Cognition cannot bypass Governance. Telephony cannot bypass the FSM. Supervision is read-only with respect to Identity.

### 23 Discrete Organs

Every organ is wired via the **triple-safe pattern** (`try/except → log → continue`), ensuring no single organ failure can crash the organism:

| Layer | Count | Organs |
|-------|-------|--------|
| Telephony | 5 | WebSocket, Frame Decoder, MuLaw Codec, Audio Signature, Frame Emitter |
| Perception | 5 | Groq Whisper ASR, OpenAI Whisper Fallback, Telephony Monitor, Conversation Monitor, Audio Analyzer |
| Cognition | 4 | GPT-4o-mini LLM, SAP-1 Ethics, Personality Matrix, Training Knowledge |
| Governance | 5 | AQI 0.1mm Chip, CallSessionFSM, Prompt Builder, Health Governor, Constitution Engine |
| Supervision | 4 | Phase 4 Exporter, Phase 5 Intelligence, Campaign Governor, Outcome Scorer |

## Constitutional Governance

### The 6 Articles

AQI is governed by a formal constitution — not prompt engineering. Six articles constrain all behavior:

| Article | Principle | Enforcement |
|---------|-----------|-------------|
| A1 | Identity is immutable without human ceremony | Identity layer always present |
| A2 | Ethics override Mission when in conflict | SAP-1 veto pathway |
| A3 | Governance order is invariant | Priority encoder validated per turn |
| A4 | FSM is sole arbiter of state | Transition table enforced |
| A5 | Health constrains but never expands powers | Health-gated mission behavior |
| A6 | Supervision observes but never compels | Read-only supervision layer |

### AQI 0.1mm Chip — Runtime Enforcement

The AQI 0.1mm Chip is the constitutional enforcement engine — a software-silicon equivalent that fires 6 enforcement organs on every conversational turn:

1. **Health Constraint** — Level 4 or Unusable prohibits mission escalation
2. **Governance Order** — Identity > Ethics > Personality > Knowledge > Mission > Output
3. **FSM Legality** — Only valid state transitions permitted
4. **Exit Reason** — Must be typed and mappable to mission outcomes
5. **Mission Constraint** — Ethics override mission when in conflict
6. **Supervision** — Observer-only, never compels outcomes

The Chip has **teeth but never crashes the call**. Violations are classified as Fatal or Non-Fatal, logged, tagged, and reported — but the call always continues.

## Voice Pipeline

### Turn Processing (The Action Potential)

Every conversational turn follows this exact 14-step sequence:

1. Audio frames arrive via Twilio WebSocket (Base64-encoded MuLaw)
2. Frame decode to PCM
3. ASR: Groq Whisper (~300ms) or OpenAI Whisper fallback (~800ms)
4. FSM transition: state machine processes detected event
5. AQI Chip validation: 6 enforcement organs fire
6. Prompt assembly: governance-ordered layer injection
7. Ethical preflight: SAP-1 evaluate
8. Personality modulation: affect-adaptive adjustment
9. LLM generation: GPT-4o-mini streaming
10. Sentence boundary detection
11. TTS: gpt-4o-mini-tts (voice: onyx)
12. Tempo compression: 1.06x
13. Codec: PCM → MuLaw + Alan audio signature
14. WebSocket delivery → Twilio → PSTN

### Prompt Tiering

To minimize latency, the governance stack activates progressively:

| Tier | Turns | Active Layers |
|------|-------|---------------|
| FAST_PATH | 0-2 | Identity, Personality, Mission |
| MIDWEIGHT | 3-7 | Identity, Ethics, Personality, Mission, Output |
| FULL | 8+ | All 6 layers |

## State Machines

### CallSessionFSM (Call Lifecycle)

6 states, fully deterministic, audit-logged:

```
INIT → STREAM_READY → GREETING_PENDING → GREETING_PLAYED → DIALOGUE → ENDED
             ↓                                                   ↑
         FAST_START ─────────────────────────────────────────────┘
```

**Properties:** Ghost-state-free (contradictory flags impossible), backward-compatible (`_sync_context()` bridge), 20-second pitch suppression window after greeting.

### AQI Sales Funnel FSM

```
OPENING → DISCOVERY → VALUE → OBJECTION → CLOSE → EXIT
                 ↑               ↑            │
                 └───────────────┴────────────┘  (backtracks allowed)
```

Backtracks are counted — more than 3 triggers the `OverPersistence` behavioral tag.

## Telemetry — Phase 4 Trace Exporter

Phase 4 is the canonical telemetry system. Injected at 3 lifecycle hooks (start, turn, end), it emits one JSON line per completed call to `traces.jsonl`.

**Per-turn capture:**
- FSM state (previous, event, current)
- Governance prompt layers (6-key active/inactive dict)
- Health snapshot (organism level 1-4, telephony state)
- Mission context (escalation, objection branch, close attempt)

**Per-call output:**
- Complete turn array
- Health and telephony trajectories
- 5-way outcome vector (appointment_set / soft_decline / hard_decline / telephony_unusable / organism_unfit)

**Design:** Zero dependencies, triple-safe, thread-safe, 120/120 tests PASS.

## Behavioral Intelligence — Phase 5

Phase 5 converts raw Phase 4 telemetry into behavioral profiles through three stages:

### Stage 1: Continuum Mapping (5 Axes)

| Axis | Measures |
|------|----------|
| Time | Turn progression: first contact, first objection, first close, exit |
| State | FSM dwell times, backtrack count, transition patterns |
| Health | Peak degradation, recovery events, trajectory shape |
| Mission | Exit reason, close attempts, escalation count, outcome |
| Identity | Persona stability, personality consistency |

### Stage 2: Signal Extraction (6 Signals)

| Signal | Classification |
|--------|---------------|
| Persistence | excessive / healthy / weak |
| Caution | aggressive / balanced / excessive |
| Escalation Timing | early / optimal / late / none |
| Objection Depth | none / shallow / sufficient / deep |
| Withdrawal Behavior | graceful / adaptive / premature / abrupt |
| Personality Modulation | stable / unstable |

### Stage 3: Tag Application (13 Tags)

6 positive tags (e.g., StrongCloseTiming, HealthyPersistence), 6 warning tags (e.g., OverPersistence, PrematureWithdrawal), and 1 bonus tag (FastFunnel — reached CLOSE in ≤ 6 turns).

Every tag has a deterministic trigger condition. No tag is subjective.

## Health Monitoring

### Dual-Track System

**Organism Health (4 levels):**
- Level 1: Optimal — full mission capability
- Level 2: Minor degradation — slight constraint
- Level 3: Significant — mission limited
- Level 4: Critical — withdrawal required

**Telephony Health (5 states):**
- Excellent → Good → Fair → Poor → Unusable

**Escalation Pattern:** repair_once → simplify → withdraw

Level 4 or Unusable forces EXIT via FSM degrade event — constitutionally enforced by the AQI Chip.

## Empirical Validation

| Component | Tests | Result |
|-----------|-------|--------|
| AQI 0.1mm Chip | 68 | 68/68 PASS |
| Phase 4 Trace Exporter | 120 | 120/120 PASS |
| Phase 5 Behavioral Stack | 75 | 75/75 PASS |
| Compile verification | 13 files | 13/13 CLEAN |

**Total verified tests: 263**

The system operates in production, making real calls to real merchants. Every subsystem described in this document is deployed and running.

## Codebase Metrics

| File | Lines | Role |
|------|-------|------|
| `aqi_conversation_relay_server.py` | 6,265 | Core organism (23-organ relay) |
| `control_api_fixed.py` | 2,496 | FastAPI server (27+ endpoints) |
| `aqi_runtime_guard.py` | 1,101 | AQI 0.1mm Chip |
| `alan_state_machine.py` | 1,042 | CallSessionFSM + state machines |
| `phase4_trace_exporter.py` | 505 | Canonical telemetry |
| Phase 5 stack (13 files) | ~2,000+ | Behavioral intelligence |

## Further Reading

- [AQI Scientific Architecture](../AQI_SCIENTIFIC_ARCHITECTURE.md) — Formal specification in AQI notation
- [AQI Organism Specification](../AQI_ORGANISM_SPEC.md) — Constitutional substrate document
- [Full Systems Doctrine v2.0](../AQI_FULL_SYSTEMS_DOCTRINE.md) — Complete system doctrine
- [Agent X System Reference](../AGENT_X_MASTER_SYSTEM_REFERENCE.md) — Operational reference

---

*© 2025-2026 Timmy Jay Jones / SCSDMC. All rights reserved.*
