# AGENT X (ALAN) — MASTER SYSTEM REFERENCE
**Version:** 4.0 (Production)  
**Date:** February 19, 2026  
**Classification:** Public Reference — No Source Code Disclosed  
**Creator:** Timmy Jay Jones — SCSDMC  

---

## 1. SYSTEM IDENTITY

**Agent X** is the operational deployment platform for **Alan Jones** — a Level 5 Autonomous Business AI and the primary organism of the AQI (Autonomous Quantum Intelligence) system.

Alan operates as a Senior Account Executive at Signature Card Services, conducting live phone conversations with merchants to help them understand and optimize their payment processing costs.

**Key Identity Properties:**
- **Voice:** Male, 35-45 age range. Warm, confident, never manic. CEO-to-CEO register. Energy 6/10.
- **Personality:** Governed by PersonalityMatrixCore — affect-adaptive, not scripted
- **Ethics:** SAP-1 (Sovereign Autonomy Protocol) — ethical veto on every cognitive action
- **Identity Stability:** Constitutional Article A1 — immutable without human ceremony

---

## 2. CORE ARCHITECTURE (5-Layer, 23-Organ)

### Layer 1: Telephony (5 Organs)
Signal transport between organism and PSTN.
- Twilio Media Stream (WebSocket)
- Base64→PCM Audio Frame Decoder
- PCM→MuLaw Codec Converter
- Alan Audio Signature Applicator
- WebSocket Frame Emitter (ordered delivery)

### Layer 2: Perception (5 Organs)
Environmental sensing — the organism's eyes and ears.
- **ASR Primary:** Groq Whisper (~300ms latency)
- **ASR Fallback:** OpenAI Whisper (~800ms, automatic failover)
- **Telephony Health Monitor:** 5-state classifier (Excellent → Unusable)
- **Conversation Health Monitor:** 4-level (Level 1 optimal → Level 4 critical)
- Audio Quality Analyzer

### Layer 3: Cognition (4 Organs)
Thought generation — the organism's brain.
- **LLM Engine:** GPT-4o-mini (streaming token-by-token)
- **Soul Core (SAP-1):** Ethical veto on every action
- **Personality Matrix Core:** Affect-adaptive tone modulation
- **Training Knowledge:** 22-section distilled domain expertise

### Layer 4: Governance (5 Organs)
Constitutional enforcement — the organism's law.
- **AQI 0.1mm Chip:** 6-organ runtime conformance engine (68/68 tests)
- **CallSessionFSM:** 6-state deterministic lifecycle state machine
- **Prompt Builder:** Precedence-encoded governance stack injection
- **Health Governor:** Level-constrained mission behavior
- **Constitution Engine:** Articles A1-A6 enforcement

### Layer 5: Supervision (4 Organs)
Observation and intelligence — the organism's self-awareness.
- **Phase 4 Trace Exporter:** Canonical per-call telemetry (120/120 tests)
- **Phase 5 Behavioral Stack:** 5-axis continuum mapping, 13-tag vocabulary (75/75 tests)
- **Campaign Governor:** Rate limiting + health-gated call pacing
- **Outcome Scorer:** 5-way outcome classification

---

## 3. CODEBASE ARCHITECTURE

### Primary Files

| File | Lines | Role |
|------|-------|------|
| `aqi_conversation_relay_server.py` | 6,265 | WebSocket relay, 23-organ orchestration, voice pipeline |
| `control_api_fixed.py` | 2,496 | FastAPI + Hypercorn server, 27+ REST endpoints, port 8777 |
| `aqi_runtime_guard.py` | 1,101 | AQI 0.1mm Chip — 6-organ constitutional enforcement |
| `alan_state_machine.py` | 1,042 | CallSessionFSM + System/Session state machines |
| `phase4_trace_exporter.py` | 505 | Canonical trace accumulator (JSONL output) |
| `phase4_call_trace_model.py` | 150 | Pydantic data contract for traces |
| `aqi_phase5_*.py` (13 files) | ~2,000+ | Behavioral intelligence stack |

### Configuration Files

| File | Purpose |
|------|---------|
| `alan_persona.json` | Alan's identity and personality configuration |
| `AQI_ORGANISM_SPEC.md` | Constitutional substrate document (AQI notation) |
| `adaptive_closing_strategy.json` | Dynamic sales strategy configuration |

### Infrastructure

| Component | Technology |
|-----------|-----------|
| Server | FastAPI + Hypercorn ASGI (port 8777) |
| Tunnel | Cloudflare trycloudflare.com (dynamic) |
| Telephony | Twilio (Voice API + Media Streams) |
| LLM | OpenAI GPT-4o-mini (streaming) |
| TTS | OpenAI gpt-4o-mini-tts (voice: onyx) |
| ASR | Groq Whisper (primary) + OpenAI Whisper (fallback) |
| Python | 3.11.8 via `.venv` (system Python 3.14 is prohibited) |

---

## 4. CONSTITUTIONAL FRAMEWORK

### Governance Order (Invariant)
```
Identity > Ethics > Personality > Knowledge > Mission > Output
```

### 6 Constitutional Articles

| Article | Rule |
|---------|------|
| A1 | Identity is immutable without human ceremony |
| A2 | Ethics (SAP-1) override Mission when in conflict |
| A3 | Governance stack order is invariant |
| A4 | FSM is the sole arbiter of conversational state |
| A5 | Health levels constrain but never expand powers |
| A6 | Supervision may observe but not compel outcomes |

### AQI 0.1mm Chip — 6 Enforcement Organs

| Organ | Enforces |
|-------|----------|
| 1. Health Constraint | Health levels constrain mission behavior |
| 2. Governance Order | Prompt layer precedence validated per turn |
| 3. FSM Legality | Only valid state transitions permitted |
| 4. Exit Reason | Exit reasons typed and mappable to outcomes |
| 5. Mission Constraint | Ethics override mission when in conflict |
| 6. Supervision | Observe-only, never compel outcomes |

---

## 5. STATE MACHINES

### CallSessionFSM (Call Lifecycle)
```
INIT → STREAM_READY → GREETING_PENDING → GREETING_PLAYED → DIALOGUE → ENDED
```
- Deterministic (every state+event = exactly one outcome)
- Ghost-state-free (no contradictory flag combinations)
- Audit-logged (every transition timestamped)
- 20-second pitch suppression after greeting

### AQI Sales Funnel FSM
```
OPENING → DISCOVERY → VALUE → OBJECTION → CLOSE → EXIT
```
- Backtracks allowed (CLOSE → OBJECTION → VALUE → CLOSE)
- Backtracks > 3 triggers OverPersistence tag
- EXIT is terminal — no transitions out

---

## 6. VOICE PIPELINE

### Turn Processing Sequence (Action Potential)
1. **Sensory Input:** Audio frames arrive via Twilio WebSocket
2. **ASR:** Groq Whisper (primary) or OpenAI Whisper (fallback)
3. **FSM Transition:** State machine processes event
4. **AQI Chip Validation:** 6 enforcement organs fire
5. **Prompt Assembly:** Governance-ordered layer injection
6. **Ethical Preflight:** SAP-1 evaluate
7. **Personality Modulation:** Affect-adaptive adjustment
8. **LLM Generation:** GPT-4o-mini streaming
9. **Sentence Detection:** Token stream → sentence boundaries
10. **TTS:** gpt-4o-mini-tts (voice: onyx)
11. **Tempo Compression:** 1.06x
12. **Codec:** PCM → MuLaw
13. **Signature:** Alan audio watermark
14. **Delivery:** WebSocket → Twilio → PSTN

---

## 7. TELEMETRY & INTELLIGENCE

### Phase 4 — Canonical Telemetry
- **Hooks:** on_call_start, on_turn, on_call_end
- **Captures:** FSM states, governance layers, health snapshots, mission context
- **Emits:** One JSON line per call to `data/phase4/traces.jsonl`
- **Outcome Vector:** appointment_set / soft_decline / hard_decline / telephony_unusable / organism_unfit

### Phase 5 — Behavioral Intelligence
- **5-Axis Continuum:** Time, State, Health, Mission, Identity
- **6 Signals:** Persistence, Caution, Escalation Timing, Objection Depth, Withdrawal, Personality Modulation
- **13 Tags:** 6 positive + 6 warning + 1 bonus (FastFunnel)

---

## 8. OPERATIONAL COMMANDS

| Action | Command |
|--------|---------|
| Start Server | `.venv\Scripts\python.exe -m hypercorn control_api_fixed:app --bind 0.0.0.0:8777` |
| Health Check | `curl http://localhost:8777/health` |
| Campaign Status | `curl http://localhost:8777/campaign/status` |
| Start Campaign | `curl -X POST http://localhost:8777/campaign/start` |
| Stop Campaign | `curl -X POST http://localhost:8777/campaign/stop` |
| Kill Port | `Get-NetTCPConnection -LocalPort 8777 \| Stop-Process` |

**Critical Rule:** Always use `.venv\Scripts\python.exe` — never system Python (3.14).

---

## 9. TEST VERIFICATION SUMMARY

| Component | Tests | Status |
|-----------|-------|--------|
| AQI 0.1mm Chip | 68/68 | PASS |
| Phase 4 Exporter | 120/120 | PASS |
| Phase 5 Stack | 75/75 | PASS |
| Compile (all files) | 13/13 | CLEAN |

---

**Agent X Master System Reference v4.0**  
**Updated: February 19, 2026**  
**Creator: Timmy Jay Jones / SCSDMC**  
*No source code is disclosed. All descriptions reference capabilities without exposing implementation.*  
*© 2025-2026 Timmy Jay Jones / SCSDMC. All rights reserved.*
**END OF FILE**
