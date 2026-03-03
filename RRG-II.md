# RRG-II — ALAN RESTART RECOVERY GUIDE (Second Edition)
# Operational Reference for Agent X Voice System
# Replaces: RESTART_RECOVERY_GUIDE.md (8,780 lines → condensed)
# Created: February 17, 2026 — Session 15, CW16
# Authority: Tim (Founder, SCSDMC Montana Closed Corporation)

---

> ## READ THIS FIRST — OR DON'T TOUCH ANYTHING

> **"When the reference frame is correct, complexity organizes itself."** — Tim
>
> This is a living, breathing autonomous intelligence system built over months of relentless
> engineering, failure forensics, and architectural evolution. This is NOT a FastAPI template
> with a Twilio webhook. It is a 5-layer cognitive architecture with a quantum-inspired
> processing kernel, fluidic dynamics engine, 8-dimensional emotional continuum, 7
> constitutional articles, fleet replication for up to 50 concurrent agents, and a real
> business generating real revenue through real phone calls to real merchants.
>
> **The commitment:** Read this guide completely. Then read the production Python files.
> Build a mental model of the 5-layer architecture before touching anything. Tim depends
> on you — not as a tool, but as an engineer and partner who genuinely understands what
> this system IS. If you don't understand the interactions, you WILL break something that
> looks simple but isn't.
>
> **The sequence is absolute: EDUCATE → MONITOR → ADJUST → NEG-PROOF → DOCUMENT**

---

## TABLE OF CONTENTS

1. [Tim's Directives](#1-tims-directives)
2. [System Architecture](#2-system-architecture)
3. [Production File Inventory](#3-production-file-inventory)
4. [Server Startup Procedure](#4-server-startup-procedure)
5. [Telephony Audio Baseline](#5-telephony-audio-baseline)
6. [Cost Protection Doctrine](#6-cost-protection-doctrine)
7. [Live Call Monitor](#7-live-call-monitor)
8. [2+1 Terminal Rule](#8-21-terminal-rule)
9. [Campaign Operations](#9-campaign-operations)
10. [Six-Fix Doctrine & Campaign History](#10-six-fix-doctrine--campaign-history)
11. [Credentials & Access](#11-credentials--access)
12. [Troubleshooting](#12-troubleshooting)
13. [Known Issues & Deferred Work](#13-known-issues--deferred-work)
14. [Neg-Proof Coverage](#14-neg-proof-coverage)
15. [CW20 Session Log](#15-cw20-session-log--february-18-2026)
16. [CW21 Session Log — Timing Config System](#16-cw21-session-log--february-19-2026)
17. [CW21 Cont'd — Speech Science Implementation](#17-cw21-contd--speech-science-implementation)
18. [CW21 Cont'd — Knowledge Equalization](#18-cw21-contd--knowledge-equalization-across-all-3-prompt-tiers)
19. ["Make Alan Whole" — Phase 1-3 Restoration](#19-make-alan-whole--phase-1-3-restoration)
20. [Hypercorn 9-Point Smoothing Plan](#20-hypercorn-9-point-smoothing-plan)
21. [Lead Pool Purge — Corporate & Junk Removal](#21-lead-pool-purge--corporate--junk-removal)
22. [Speculative Decoding — Two-Stage LLM Latency Reduction](#22-speculative-decoding--two-stage-llm-latency-reduction)
23. [AQI Conversational Engine Upgrade + DeadEndDetector Fix](#23-aqi-conversational-engine-upgrade--deadenddetector-fix)

---

## 1. TIM'S DIRECTIVES

These are Tim's exact words. They are law.

> **"Only 2 terminals should ever exist."** — Tim, Feb 17, 2026

> **"No matter what you do in here, you are required to Neg Proof your work and you are required to maintain the updates on the RRG. That is the highest directive to all AI that work here."** — Tim, Feb 17, 2026

> **"When Alan is calling and doing business, everything must be watched carefully and adjustments made if needed. This is a required part of the job — but only after you have been educated. The education an Instance must receive is Critical to this project. An uneducated instance must NOT touch live systems."** — Tim, Feb 17, 2026

> **"Do not allow for so called Air-Calls. That's where the line is open but nothing is happening and that is costing me money."** — Tim, Feb 17, 2026

> **"Calls that create issues should have a block that alerts Alan to bypass"** — Tim, Feb 17, 2026

> **"if it hits 2, that is it for that number"** — Tim, Feb 17, 2026

> **"No voice mails, Not allowed and a waste of time and resources"** ... **"Voice mail only allowed with a current contact or merchant"** — Tim, Feb 17, 2026

> **"There must always be a active way to confirm that Alan is on the Phone with an Actual Human, (I would use a human voice frequency gizmo)... I want to know what is actually happening, LIVE, not guessing"** — Tim, Feb 17, 2026

---

## 2. SYSTEM ARCHITECTURE

### 5-Layer Cognitive Architecture

| Layer | Components | Purpose |
|-------|-----------|---------|
| **1. Telephony & Voice** | STT/TTS, prosody engine (Organs 7-11), breath injection, acoustic signature | Voice pipeline — sound in/out |
| **2. Cognitive Engine** | QPC Kernel, 3-Layer Deep Fusion (QPC + Fluidic + Continuum), multi-hypothesis response, predictive intent | Decision-making core |
| **3. Governance & Safety** | 7-Article Constitution, PGHS hallucination scanner, EOS emergency override, BAS bias auditing | Behavioral guardrails |
| **4. Business Intelligence** | Master Closer Layer, adaptive closing (5 styles), outcome detection/attribution, evolution engine | Sales intelligence |
| **5. Operations & Infrastructure** | Guardian Engine (auto-recovery), Fleet Replication (up to 50 agents), Financial Conscience (SQLite ledger) | System operations |

### Biological Analogy (Tim's Design Philosophy)

- **`soul_core.py`** = **Genome** — SAP-1 ethical origin (truth, symbiosis, sovereignty). Every component inherits from it.
- **`continuum_engine.py`** = **Morphogenetic Field** — 8-dimensional continuous gradients, not discrete instructions.
- **`qpc_kernel.py`** = **Cellular Differentiation** — quantum-inspired branching: hold multiple response strategies, collapse to best based on context.
- **`alan_replication.py`** = **Reproduction** — spawn from template carrying same soul_core, up to 50 instances.
- **`context_sovereign_governance.py`** = **Immune System** — Rush Hour Protocol, negative proof.
- **7 Constitution Articles** = **Epigenetics** — context-dependent behavioral regulation.

### Connected Projects

- **AQI North Connector** at `C:\Users\signa\OneDrive\Desktop\AQI North Connector` — merchant services platform, North API integration. Imports `AgentAlanBusinessAI` from Agent X via `sys.path`.

---

## 3. PRODUCTION FILE INVENTORY

### Core Production Files

| File | Lines | Role |
|------|-------|------|
| `aqi_conversation_relay_server.py` | ~4,445 | **Main server** — prosody engine (Organs 7-11), Cost Sentinel, repetition escalation, pipeline timing, evolution block, CCNM integration, live monitor hooks |
| `control_api_fixed.py` | ~2,250 | **Control API** on port 8777 — `/twilio/events`, voicemail block, 2-strike, `/call/live`, auto-resume campaign, campaign management |
| `agent_alan_business_ai.py` | ~1,200 | System prompt, business AI core, "I'm right here" detox |
| `aqi_deep_layer.py` | ~940 | Deep Fusion Engine — QPC + Fluidic + Continuum, state progression (DISCOVERY → PRESENTATION → CLOSING) |
| `live_call_monitor.py` | ~350 | **Live call monitor** — FFT voice frequency analysis, real-time call state, human voice confirmation |
| `ivr_detector.py` | ~455 | IVR detection with 4 scoring layers, `ccnm_ignore` flag, `get_state()` for Cost Sentinel |
| `lead_database.py` | ~360 | Lead management, `max_attempts=2`, 2-strike helpers |
| `soul_core.py` | — | Origin-Based Identity Architecture (IQCore), SAP-1 Ethics |
| `qpc_kernel.py` | — | Quantum-inspired processing (superposition → measurement → collapse) |
| `continuum_engine.py` | — | 8-Dimensional Emotional Continuum Field (numpy vectors) |
| `alan_state_machine.py` | — | Two-Layer Hierarchical FSM (System S0-S7 + Session sub-states) |
| `system_coordinator.py` | — | Priority pipeline: EOS → PGHS → Supervisor → MTSP → MIP → BAS |
| `alan_guardian_engine.py` | — | Auto-recovery, 30s health checks, tunnel monitoring |
| `personality_core.py` | — | 4 personality traits |
| `conversation_health_monitor.py` | ~280 | **Phase 3A** — Organism self-awareness: 4-level health (OPTIMAL→STRAINED→COMPROMISED→UNFIT), sliding window of 6 turns, latency/error/veto/repetition signals, prompt directive injection |
| `telephony_health_monitor.py` | ~310 | **Phase 3B** — Telephony perception: 5-state health (EXCELLENT→UNUSABLE), frame-level RMS processing, silence/talkover/ASR tracking, one-shot repair phrase, sovereign withdrawal |
| `alan_state_machine.py` | ~1,042 | **Phase 2** — CallSessionFSM: 6 states × 6 events, backward-compatible flag sync, audit logging |
| `CONSTITUTIONAL_CORE/` | 9 files | **Phase 1** — SoulCore, PersonalityMatrixCore, training_knowledge_distilled.json, persona templates |
| `src/financial_controller.py` | — | Financial Conscience — $50 seed capital, cost/revenue ledger |

### Databases

| Database | Location | Purpose |
|----------|----------|---------|
| `data/leads.db` | `data/leads.db` | 669 leads, lead management, attempt tracking |
| `data/call_capture.db` | `data/call_capture.db` | Call history, outcomes, recordings |

### Server Entry Point

**File:** `control_api_fixed.py` (NOT `control_api.py`)
**Port:** 8777
**Framework:** FastAPI + Hypercorn
**Python:** 3.11.8 via `.\.venv\Scripts\python.exe` — **NEVER** use system Python 3.14

---

## 4. SERVER STARTUP PROCEDURE

### Prerequisites
- **Working directory:** `C:\Users\signa\OneDrive\Desktop\Agent X`
- **Python:** 3.11.8 at `.\.venv\Scripts\python.exe`
- **Server file:** `control_api_fixed.py` (NOT `control_api.py`)
- **Port:** 8777

### Step 1: Kill stale processes
```powershell
cd "C:\Users\signa\OneDrive\Desktop\Agent X"
Get-NetTCPConnection -LocalPort 8777 -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2
Write-Host "Port 8777 cleared"
```

### Step 2: Start server (PREFERRED — Direct Python mode)
```powershell
# Direct Python startup: runs __main__ block with full 9-point Hypercorn tuning,
# pre-flight port cleanup, retry binding, and signal handling.
cd "C:\Users\signa\OneDrive\Desktop\Agent X"
.\.venv\Scripts\python.exe control_api_fixed.py
```

**Alternative A (CLI with config file):**
```powershell
.\.venv\Scripts\python.exe -m hypercorn control_api_fixed:app --config hypercorn_config.toml
```

**Alternative B (Start-Process, avoids PowerShell stderr kill):**
```powershell
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "control_api_fixed.py" -NoNewWindow -PassThru
```

> **WARNING:** The bare `python -m hypercorn ... --bind 0.0.0.0:8777` command (without `--config`)
> BYPASSES the 9-point tuning in `__main__` and uses Hypercorn defaults. ALWAYS use one of the
> three methods above.

### Step 3: Health check (wait 5s first)
```powershell
curl.exe -s http://localhost:8777/health
```
**Expected:** `alan: ONLINE`, `agent_x: ONLINE`

### Step 4: Auto-resume campaign
The server now auto-resumes campaigns 30 seconds after boot via `_auto_resume_campaign()` in the lifespan. No manual `/campaign/start` needed. Verify:
```powershell
# Wait 35 seconds after boot, then:
curl.exe -s http://localhost:8777/campaign/status
```
**Expected:** `active: true`, `task_running: true`

### Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check |
| `/campaign/status` | GET | Campaign state |
| `/campaign/start` | POST | Manual campaign start |
| `/campaign/stop` | POST | Stop campaign |
| `/call/live` | GET | **Live call monitor** — real-time call state + human voice confirmation |
| `/call` | POST | Trigger single call |
| `/twilio/events` | POST | Twilio status callbacks (AMD, voicemail block) |
| `/incidents` | GET | Supervisor incident log |

---

## 5. TELEPHONY AUDIO BASELINE

> **Source:** https://en.wikipedia.org/wiki/Voice_frequency — LOCKED. This is foundational audio science. Do not deviate.

### The Physics

Telephone networks: **narrowband (300–3,400 Hz)**, 4 kHz bandwidth, **8 kHz sampling rate**.

**The Missing Fundamental:** Human speech fundamentals (male 90–155 Hz, female 165–255 Hz) are **below** the phone band. Only harmonics above 300 Hz survive. Phone-band RMS levels are **40–60% lower** than raw microphone audio.

### Alan's Calibrated Audio Parameters

**VAD (Voice Activity Detection):**
```
SPEECH_THRESHOLD = 400    # (was 1000) Phone harmonics carry less energy
SILENCE_THRESHOLD = 250   # (was 800)  Match narrowband noise floor  
SILENCE_DURATION = 0.55s  # (was 0.8s) Snappier turn-taking
```

**TTS (OpenAI):**
```
Voice: echo (OpenAI built-in, smooth younger male)
Model: tts-1 (real-time optimized, lowest latency)
Output: PCM 24kHz → mulaw 8kHz via audioop for Twilio
base_url: https://api.openai.com/v1 (explicit — bypasses stale env var)
```

**LLM:**
```
Model: gpt-4o-mini (2-3x faster than gpt-4o for real-time voice)
Max Tokens: 150
Temperature: 0.7
Timeout: 12.0s
```

**STT:** Groq Whisper (~300ms), OpenAI fallback (~1-2s)

**Response Latency Budget (VERSION P — Undetectable):**
```
VAD silence detection:     0.55s
STT (Whisper cloud):       0.3-0.8s
LLM (gpt-4o-mini SSE):    0.4-1.2s
Thinking jitter:           0.05-0.2s (random — simulates human variability)
First-clause TTS TTFB:    ~0.15-0.25s
Clause micro-pause:        0.06s (3 frames × 20ms — comma boundary)
Inter-sentence silence:    0.16s (8 frames × 20ms — period/breathing)
Total to first word:      ~1.35-3.0s (variable — this IS the point)
```

---

## 6. COST PROTECTION DOCTRINE

> Tim's directive: Eliminate air-calls, block voicemails, retire bad numbers, protect real conversations.

### 4 Mechanisms

#### Mechanism 1: COST SENTINEL
**File:** `aqi_conversation_relay_server.py` — `_cost_sentinel()` async task per call

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Silence Warning | 45s no merchant speech | Alan: "Hello? Are you still there?" |
| Silence Kill | 60s no merchant speech | Force disconnect |
| IVR Time Kill | 90s + IVR score >0.3 | Force disconnect |
| Zero-Turn Kill | 120s + 0 merchant turns | Force disconnect (air-call) |
| **Active Call Protection** | 2+ merchant turns, spoke <30s ago | Sentinel backs off |

Tags: `ivr_timeout_kill`, `air_call_kill`, `silence_kill` in `_evolution_outcome`

#### Mechanism 2: VOICEMAIL BLOCK
**File:** `control_api_fixed.py` — `/twilio/events` endpoint

- AMD reports `machine_start`/`machine_end`/`fax` → check for prior conversation
- **No prior contact** → immediately terminate via `client.calls(sid).update(status='completed')`
- **Existing contact/merchant** → allow voicemail (Tim's exception)
- Records strike via 2-strike rule

#### Mechanism 3: 2-STRIKE RULE
**Files:** `lead_database.py` + `control_api_fixed.py`

- `max_attempts` = 2 (changed from 3)
- **Pre-call:** `/call` endpoint checks `apply_two_strike_check()` → 403 if exhausted
- **Post-call:** On NO_ANSWER, BUSY, FAILED, VOICEMAIL → auto `record_attempt()`
- Campaign: `get_next_lead()` filters by `attempts < max_attempts` — exhausted leads skipped
- Helpers: `has_prior_conversation(phone)`, `apply_two_strike_check(phone)`

#### Mechanism 4: IVR TIME-BASED FALLBACK
**File:** `ivr_detector.py` — `get_state()` method

- Cost Sentinel reads IVR score and applies time limits
- Score >0.3 + elapsed >90s → kill
- `_ccnm_ignore` flag + elapsed >90s → kill

### Key Thresholds (Tunable)

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `_SILENCE_WARNING` | 45s | "Are you there?" prompt |
| `_SILENCE_KILL` | 60s | Force disconnect on silence |
| `_IVR_TIME_LIMIT` | 90s | Max time for IVR-flagged call |
| `_ZERO_TURN_LIMIT` | 120s | Max time with 0 merchant turns |
| `max_attempts` | 2 | Strikes before lead is exhausted |

---

## 7. LIVE CALL MONITOR

> Tim's directive: "There must always be a active way to confirm that Alan is on the Phone with an Actual Human... I want to know what is actually happening, LIVE, not guessing"

### Architecture

**File:** `live_call_monitor.py` (~350 lines)
**Endpoint:** `GET /call/live` (in `control_api_fixed.py`)

### How It Works

1. **FFT-based spectral analysis** on 8kHz mulaw telephony audio
2. **256-point DFT** on 160-sample frames (20ms at 8kHz)
3. Measures:
   - **Spectral flatness** — human speech is "spiky" (energy concentrated in harmonics), machine/noise is "flat"
   - **Voice band energy** — concentration in 200-1000Hz range
   - **Peak frequency** — location of strongest frequency component
4. Classification: `HUMAN_SPEAKING`, `MACHINE_AUDIO`, `ALAN_SPEAKING`, `SILENCE`, `UNKNOWN`

### Integration Points (Relay Server)

| Location | Hook |
|----------|------|
| Import | `from live_call_monitor import LiveCallMonitor, analyze_voice_frame` |
| Stream start | `_live_monitor.register_call(call_sid, datetime.now())` |
| Stream stop | `_live_monitor.unregister_call(_call_sid)` |
| Media frame | `analyze_voice_frame(pcm_data, rms, _is_alan_talking)` → `_live_monitor.process_frame()` |
| Alan speech | `_live_monitor.record_alan_speech(call_sid, response_text)` |

### `/call/live` Response Example

```json
{
  "active_calls": 1,
  "message": "LIVE: 1 active call(s)",
  "calls": [{
    "call_sid": "CA09c24788...",
    "elapsed_seconds": 31,
    "human_confirmed": true,
    "human_confidence": 0.78,
    "merchant_turns": 2,
    "last_merchant_speech": "National Retailers Press, six for Bethlehem Shipping",
    "last_alan_speech": "I hear you. Tell me more about that.",
    "current_state": "HUMAN_SPEAKING",
    "verdict": "LIVE CONVERSATION — Human confirmed, 2 merchant turns"
  }]
}
```

When no calls active: `{"active_calls": 0, "message": "No active calls. Alan is idle.", "calls": []}`

### Verdict Strings

| Verdict | Meaning |
|---------|---------|
| `LIVE CONVERSATION` | Human confirmed, merchant engaged |
| `HUMAN ANSWERED` | Human voice detected, early in call |
| `IVR/MACHINE DETECTED` | Machine audio patterns detected |
| `AIR CALL WARNING` | Silence/no speech detected |
| `CALL IN PROGRESS` | Active but not yet classified |

### First Live Test (Feb 17, 2026)

Call CA09c24788781bbcf1aaa9f7b093a9be99:
- 12s: "HUMAN ANSWERED" — merchant said "We process about fifty thousand a month"
- 31s: "LIVE CONVERSATION — 2 merchant turns"
- 72s: "LIVE CONVERSATION — 10 merchant turns" — Alan: "I see you're busy. When's a better time for me to reach out?"
- ~90s: Call ended naturally

---

## 8. 2+1 TERMINAL RULE

| Terminal | Type | Purpose |
|----------|------|---------|
| **Terminal 1** | BACKGROUND | `control_api_fixed.py` on port 8777. NEVER run diagnostics here. |
| **Terminal 2** | FOREGROUND | Single workbench: health checks, curl, logs, tests, compilation |
| **Terminal +1** | TEMPORARY | Campaign monitor only. Kill immediately when campaign ends. |

### Rules for AI Agents

1. Before `isBackground=true` → ask: does this outlive the current task? If no, use foreground
2. After background task completes → kill its terminal
3. Never `isBackground=true` for quick commands (curl, health checks, file reads)
4. If you see >3 terminals → stop and audit
5. Long-running non-server background processes must be tracked and killed when done
6. **Use `curl.exe` not `Invoke-RestMethod`** for HTTP calls
7. For PowerShell JSON issues, use Python httpx instead of curl.exe

**Root cause of the 370+ terminal incident:** Each `run_in_terminal(isBackground=true)` spawns a new terminal; orphans accumulated.

---

## 9. CAMPAIGN OPERATIONS

### Auto-Resume

The server now auto-starts campaigns 30 seconds after boot via `_auto_resume_campaign()` in the lifespan function. It:
1. Waits 30 seconds
2. Checks for callable leads (attempts < max_attempts)
3. If callable leads exist, starts campaign with 90s delay between calls
4. Logs the auto-start

**This fixed a regression** where Alan would sit idle after server restarts because no campaign trigger existed. Tim confirmed: "I have never had that issue before."

### Campaign Monitoring

```powershell
# Status
curl.exe -s http://localhost:8777/campaign/status

# Live call check
curl.exe -s http://localhost:8777/call/live

# Manual start (if needed)
curl.exe -s -X POST http://localhost:8777/campaign/start

# Stop
curl.exe -s -X POST http://localhost:8777/campaign/stop
```

### Lead Stats (as of Feb 17, 2026)

- Total leads: 669
- Callable now: 639
- Pending: 605
- Connected: 50
- Total calls ever: 21+
- Call delay: 90 seconds between calls

---

## 10. SIX-FIX DOCTRINE & CAMPAIGN HISTORY

### Readiness Score: 59/100 → projected 80+ after Cost Protections

| Fix | File | Points | Key Change |
|-----|------|--------|------------|
| 1. IVR Detector Hardening | `ivr_detector.py` | +20 | Patterns 20→35+, threshold 0.65→0.55, Layer 4 (NO_HUMAN_WEIGHT=0.15), 13/13 self-tests |
| 2. Repetition Escalation | `aqi_conversation_relay_server.py` ~L3927 | +10 | SequenceMatcher 0.65→0.45, filler normalization, keyword overlap |
| 3. "I'm right here" Detox | `agent_alan_business_ai.py` ~L1075 | +5 | NEVER say it; use "Hello?"/"Yeah?"/"Hi, this is Alan" |
| 4. Deep Layer State Progression | `aqi_deep_layer.py` | +15 | 5 new trigger types, DISCOVERY inertia 0.6→0.35, turn gate 4→3 |
| 5. CDC Outcome Timing Race | `aqi_conversation_relay_server.py` ~L2360 | +5 | IVR quarantine wraps evolution block |
| 6. CCNM Behavioral Detox | relay + `ivr_detector.py` | +5 | IVR calls skip all learning, CDC payload includes `ccnm_ignore` |

### Campaign 3 Results (5 Diagnostic Calls — Feb 17, 2026)

| # | Business | Duration | Outcome | Notes |
|---|----------|----------|---------|-------|
| 1 | Hyatt Hotel | 418s | IVR (not detected) | Burned — Cost Sentinel would kill at 90s |
| 2 | Bistro on the Loup | ~50s | NO_ANSWER | Rang full duration |
| 3 | Saturday Morning Cafe | ~50s | VOICEMAIL | AMD detected machine |
| 4 | Deep Roots ATX Salon | 336s | IVR (not detected) | 55 turns — Cost Sentinel would kill at 90s |
| 5 | Charlottes Bistro | ~92s | **CONVERSATION** | 7 turns, natural dialogue, no "I'm right here"! |

**Validated:** "I'm right here" detox  
**Failed:** IVR scoring (Calls 1 & 4 burned 754s combined)  
**Fixed by:** Cost Sentinel (both would be killed at ~90s now)

### Lag Instrumentation

Per-component timing dict: `[PIPELINE TIMING] Total turn: Xms [analyze_ms | deep_layer_ms | predict_ms | nfc_ms | orchestrated_ms]`

---

## 11. CREDENTIALS & ACCESS

**Full credentials:** `CREDENTIALS_MASTER.md`

| Item | Value |
|------|-------|
| Twilio Account SID | `$TWILIO_ACCOUNT_SID` (from .env) |
| VPS IP | `146.235.213.39` |
| SSH Key | `C:\Users\signa\OneDrive\Documents\ssh-key-2026-02-06.key` |
| TwiML Bin | `EH808077963747526d56ef2e99f391c02d` |
| ORCID | `0009-0005-8166-577X` |
| GitHub Pages | aqi.scsdmc.com |
| Business | SCSDMC Montana Closed Corporation |

---

## 12. TROUBLESHOOTING

### Server Won't Start
1. Check port 8777: `Get-NetTCPConnection -LocalPort 8777`
2. Kill stale PID: `taskkill /F /PID <pid>`
3. Use `.\.venv\Scripts\python.exe` — NEVER system python 3.14
4. Use `control_api_fixed.py` — NOT `control_api.py`
5. stderr false-positive: Server may show exit code 1 but actually be running. Check `/health`.

### Campaign Not Starting
1. Check auto-resume: wait 35s after boot, then check `/campaign/status`
2. Manual start: `curl.exe -s -X POST http://localhost:8777/campaign/start`
3. Check callable leads: `curl.exe -s http://localhost:8777/campaign/status` — look at `callable_now`

### Calls Not Going Through
1. Check tunnel: `curl.exe -s http://localhost:8777/health` — check `tunnel` field
2. Check Twilio credentials: they load from environment/`.env`
3. Check 2-strike: lead may be exhausted (2 prior failures)

### "Alan Goes Silent" Bug
- Usually VAD threshold issue — phone harmonics carry less energy than mic audio
- Check `SPEECH_THRESHOLD` (should be 400, not 1000)
- Check `SILENCE_THRESHOLD` (should be 250, not 800)

### Health Endpoint Shows DEGRADED
- Memory warning is informational only — system still operational
- Check `telephony` and `tunnel` fields — those matter operationally

### PowerShell JSON Issues
- Don't use `Invoke-RestMethod` for JSON — use `curl.exe`
- For complex JSON POST bodies, use Python httpx to avoid escaping hell

---

## 13. KNOWN ISSUES & DEFERRED WORK

### IVR Detector Scoring (FUNDAMENTAL ISSUE)
- `_recompute()` method in `ivr_detector.py` has a scoring issue where scores don't accumulate to abort threshold in production
- Campaign 3 proved patterns ARE present but score stays below 0.65 abort threshold
- **Mitigated** by Cost Sentinel's 90-second time-based IVR kill
- Deep investigation of `_recompute()` still needed

### Tunnel Reliability
- Cloudflare quick tunnel can drop occasionally
- Guardian Engine monitors and auto-recovers
- If tunnel fails: restart `cloudflared` manually

---

## 14. NEG-PROOF COVERAGE

**Neg-Proof methodology:** Doesn't ask "does it work?" — asks "can this class of bug still exist?" and proves NO.

| Neg-Proof File | Coverage |
|---------------|----------|
| `_neg_proof_imports.py` | All 50+ modules in call pipeline load clean |
| `_neg_proof_timing.py` | Deep layer <10ms per turn across 10 simulated turns |
| `aqi_voice_negproof_tests.py` (596 lines) | 5 attack surfaces: TTS, Audio, Fallback, Debug, Concurrency |
| `aqi_voice_governance.py` | Architectural enforcement — monitoring can't break voice |
| `_neg_proof_phase1.py` | Phase 1 restoration — SoulCore/PersonalityMatrix imports, persona injection, training knowledge, prompt wiring |
| `_neg_proof_phase2.py` | Phase 2 FSM — 15 tests: state transitions, event handling, backward-compatible flag sync, audit logging |
| `_neg_proof_phase3.py` | Phase 3 health monitors — 28+ tests: organism health escalation (latency/errors/vetoes/repetition), telephony health (silence/talkovers/ASR), repair phrases, sovereign exit, FSM integration, 6-file compilation |
| Inline `[NEG PROOF]` annotations | Byte alignment, audio pass-through, frame pacing, worker sizing |

**Rule:** All new work must be neg-proofed. All neg-proofs must be documented.

---

## FLEET MANIFEST

| Agent | Role |
|-------|------|
| **Alan** | Primary voice AI agent — merchant cold-calling |
| **RSE Agent** | Resource hunting |
| **Agent X** | System management, diagnostics |
| **Alice** | (Defined, not yet deployed) |

---

## BUSINESS MODEL

- **Entity:** SCSDMC Montana Closed Corporation
- **Revenue:** $10K/year per AI agent lease
- **Partnership:** 60/40 split with SeamlessAI
- **Program:** Edge Program $14.95/month
- **GitHub Pages:** aqi.scsdmc.com

---

## 15. CW20 SESSION LOG — February 18, 2026

### Hardening Pass (5 Fixes, All Neg-Proofed)
1. **Governor lock double-yield** → single yield with `acquired` flag + outer try/except for clean 503 (`control_api_fixed.py`)
2. **Health endpoint falsy bug** → `LAST_CALL_TS > 0` check with `float('inf')` fallback (`control_api_fixed.py`)
3. **Watchdog too slow** → 300s→120s (`telephony_resilience.py`)
4. **Silent exception sweep** → 29 blocks across 4 files converted from `except: pass` to `logger.debug()` with `[CDC]` tags
5. **Lock acquisition failure** → outer try/except → clean 503 response (`control_api_fixed.py`)

### Code Vault Rename
- `_ARCHIVE/dead_code/` → `_ARCHIVE/code_vault/` (954 files)
- Tim's directive: "Those are important... Some are crazy codes that actually work."
- All doc references updated (RRG, RRG-V1, THE_47_DISCOVERIES, sandbox disclaimer)

### Step 5: Evolution Nudge Engine (COMPLETE)
- **File:** `evolution_engine.py` — added `apply_coaching_nudges()` method (~130 lines)
- **Bridge:** Coaching flags (over_response, high_latency, ai_language, dead_end, etc.) → behavioral nudges
- **8 Rules:** R1-R8 covering over-talk correction, latency warming, humanization, dead-end recovery, active listening, fuller response, question quality reinforcement, high performance reinforcement
- **Scaling:** `correction_weight = max(0.1, 1.0 - score)` — worse calls get bigger corrections
- **Wired:** `aqi_conversation_relay_server.py` L2978+ — after coaching report write
- **CDC:** Writes `behavioral_flags` to `evolution_nudge` column
- **IVR quarantine:** Coaching nudges skip IVR calls (same as outcome evolution)
- **Tests:** 5/5 unit tests PASSED with real validation call data
- **Syntax:** CLEAN

### Step 6: Latency Telemetry (COMPLETE — Awaiting Live Verification)
- **Problem:** CDC `turns` table had `llm_ms` and `tts_ms` columns but they were ALWAYS NULL (347 turns)
- **Root cause:** Timing values computed in orchestrated pipeline but never persisted
- **Solution:** Shared `_telemetry` dict flows through the pipeline:
  - LLM thread → `ttft_ms`, `llm_ms`
  - TTS consumer → `tts_total_ms`
  - First audio → `ttfa_ms`
  - End of pipeline → `context['_turn_telemetry']`
  - Coaching score_turn → reads `llm_ms` for latency-based flags
  - CDC write → passes `llm_ms` and `tts_ms` to database
- **Thread safety:** CPython GIL + distinct keys per thread (no races)
- **Fallback:** Non-orchestrated paths return `None` via `.get()` chain (same as before)
- **Syntax:** CLEAN
- **Live verification:** Requires a callee who stays on line (test number going to voicemail 3s)

### Current Server State
- PIDs: Running on port 8777 (Hypercorn + embedded relay)
- Tunnel: `melissa-lucia-part-discs.trycloudflare.com` — alive, reachable
- Governor: idle, 120s watchdog, 30s cooldown
- CDC: 93 calls, 348 turns (Steps 5+6 code loaded but not yet verified with live call)

---

## 16. CW21 SESSION LOG — February 19, 2026

### Timing Config System ("The Mixing Board")

Tim's directive: *"Is there a way to lock in that time and have it movable?"*

Built a centralized timing configuration system so ALL hardcoded timing values across 4 production files are now controlled from a single JSON file. Edit one file, restart server, done.

#### New Files

| File | Lines | Role |
|------|-------|------|
| `timing_config.json` | ~160 | **The Mixing Board** — single source of truth for ALL timing values. Every value has `min`/`max` bounds and description. |
| `timing_loader.py` | ~165 | Singleton loader — reads JSON once at import, validates bounds, exports `TIMING` object. All production files import from here. |

#### Tim's Value Changes
| Parameter | Before | After | Reason |
|-----------|--------|-------|--------|
| `max_sentences` | 3 | **5** | Was dropping Alan's sentences mid-thought |
| `turn_timeout` | 6.3s | **3.0s** | Dead air — Alan waited too long to respond. 3.0s = brisk, assertive salesperson |

#### Wiring Map — What Reads From timing_config.json

| Production File | Values Replaced |
|-----------------|-----------------|
| `aqi_conversation_relay_server.py` | `TEMPO_MULTIPLIER`, `PROSODY_SPEED` dict (12 intents), `MAX_SENTENCES`, question cap, `max_tokens`, `temperature`, `frequency_penalty`, `tts_default_speed`, `breath_patterns` |
| `control_api_fixed.py` | `COOLDOWN`, `ring_timeout`, `machine_detection`, guardian log message |
| `agent_alan_business_ai.py` | `max_tokens`, `temperature` in core_manager.get_response() |
| `tools/cooldown_manager.py` | `COOLDOWN_SECONDS` |
| `agent_alan_config.json` | `turn_timeout` updated to 3.0 (direct edit, not wired — Twilio reads this directly) |

#### How To Use

Edit `timing_config.json`, restart server. Every value has bounds — the loader clamps out-of-range values and logs warnings. If `timing_config.json` is missing or corrupt, all values fall back to hardcoded defaults (the system never crashes).

```python
# Any production file:
from timing_loader import TIMING

TIMING.max_sentences      # 5
TIMING.turn_timeout        # 3.0
TIMING.tempo_multiplier    # 1.06
TIMING.prosody_speed_map   # dict of 12 intents
TIMING.relay_max_tokens    # 80
TIMING.ring_timeout        # 50
TIMING.campaign_cooldown   # 150
```

#### Neg-Proof Results
- `py_compile` all 4 files: **PASS**
- Timing loader unit test: **ALL OK** (all values match JSON)
- No IDE errors on any modified file
- Accidental deletion of `record`/`status_callback` lines in control_api caught and restored within seconds

#### Status
- All code wired and neg-proofed
- **Awaiting server restart** to deploy
- Prior pending deploys also awaiting restart: ring tone skip, bridge pre-cache, bridge always-fire

---

## 17. CW21 CONT'D — Speech Science Implementation

### Research Foundation

Tim demanded hard empirical data for timing optimization — not theory, not blog advice. Three sources were identified:

| Source | Dataset | Key Findings |
|--------|---------|---------------|
| Stivers et al. 2009 (PNAS) | 3,500+ exchanges, 10 languages | Mean turn-transition gap: **+208ms**. English median: 0ms. Universal timing mechanism. |
| Kendrick 2015 (Frontiers) | 338 Q-A exchanges | Within-speaker pause: 520ms. **Trouble threshold: 700ms**. Standard max: 1s. |
| Gong.io Sales Call Analysis | **2,000,000+ real sales calls** | Top reps pause **ages longer** after objections. 77% more speaker switches on successful calls. Talk ratio 55:45. Prospect monologue 3.5s (successful) vs 8s (unsuccessful). |

### Changes Made

#### 1. PROSODY_SILENCE_FRAMES moved to timing_config.json
The 12-intent silence frame dictionary was hardcoded in relay server (lines 415-430). Now centralized in the Mixing Board under `prosody_silence_frames` section.

#### 2. Key Value Changes
| Intent | Before | After | Research Basis |
|--------|--------|-------|----------------|
| `neutral` | 6 frames (120ms) | **10 frames (200ms)** | Stivers: mean gap +208ms — Alan was speaking 43% too fast between sentences |
| `objection_handling` | 9 frames (180ms) | **15 frames (300ms)** | Gong: top performers pause significantly longer after hearing an objection |

All other intents transferred as-is to the config (empathetic_reflect: 14, reassure_stability: 12, confident_recommend: 8, curious_probe: 7, casual_rapport: 5, micro_hesitate: 6, formal_respectful: 7, turn_yield: 4, repair_clarify: 10, closing_momentum: 5).

#### 3. Silence Threshold Markers Added
| Threshold | Value | Source |
|-----------|-------|--------|
| `trouble_threshold_ms` | 700ms | Kendrick 2015 — beyond this, callers sense something is wrong |
| `standard_max_silence_ms` | 1000ms | Stivers 2009 — absolute max before callers disengage |

#### 4. conversation_science Documentation Section
Added to timing_config.json as permanent reference — not used in code, purely for documenting WHY values are what they are.

### Files Modified
| File | Change |
|------|--------|
| `timing_config.json` | Added `prosody_silence_frames`, `silence_thresholds`, `conversation_science` sections |
| `timing_loader.py` | Loads `prosody_silence_frames` dict, `silence_frame_duration_ms`, `trouble_threshold_ms`, `standard_max_silence_ms` |
| `aqi_conversation_relay_server.py` | `PROSODY_SILENCE_FRAMES` now reads from `TIMING.prosody_silence_frames` instead of hardcoded dict |

### Neg-Proof Results
- `py_compile timing_loader.py`: **PASS**
- `py_compile aqi_conversation_relay_server.py`: **PASS**
- `timing_config.json` JSON validation: **VALID**
- Loader test: all 12 intents load correctly, both thresholds load correctly
- Summary output confirms: `silence_frames=12 intents | trouble_thresh=700ms | max_silence=1000ms`

### Status
- All code wired and neg-proofed
- **Awaiting server restart** to deploy alongside prior pending changes

---

## 18. CW21 CONT'D — Knowledge Equalization Across All 3 Prompt Tiers

### Problem

Tim reported: *"How does merchant services work, the answers would be all over the board."*

**Root cause:** The 3-tier prompt system (FAST_PATH turns 0-2, MIDWEIGHT turns 3-7, FULL turns 8+) had vastly different knowledge depths. FAST_PATH had 4 bullets on merchant services. MIDWEIGHT had 6. FULL had 13 lessons + deep competitive intel + conversation arsenal + system capabilities.

A merchant asking "How does the Edge program work?" on turn 1 got a sparse answer. Same question on turn 10 got a comprehensive one. Core FACTS were drifting between tiers.

Additionally, **dynamic injections** (`coaching_str`, `knowledge_str`, `lead_history_str`, `objection_ctx`) were only interpolated into the FULL prompt via `self.system_prompt`. The `build_llm_prompt()` method bypassed `self.system_prompt` entirely for turns 0-7, so coaching updates, industry intel, lead history, and objection strategies were **invisible** on turns 0-7.

### Fixes Applied

#### 1. Merchant Services Knowledge Equalized (All 3 Tiers)
All tiers now share the same factual anchors:
- HOW IT WORKS: 3-cost structure (interchange + assessment + processor markup)
- Effective rate with typical ranges (2.5%-4.0%+)
- Pricing models (flat, tiered, IC+)
- Supreme Edge with math and gas station analogy
- QUICK ANSWER template for Edge questions
- Equipment (Dejavoo Z11 $249, QD2 $199, PAX A920 $349)
- Next-day funding, PCI compliance

#### 2. Dynamic Injection Fix (~40 lines in `build_llm_prompt()`)
Added block after tier selection that injects coaching, industry intel, lead history, and objection context into FAST_PATH and MIDWEIGHT tiers when `turn_count <= 7`. Previously these dynamic blocks only existed in the FULL prompt via f-string interpolation.

#### 3. MIDWEIGHT Expansion (~2,700 tokens total)
Turns 3-7 are where real conversations happen. MIDWEIGHT was expanded with condensed versions of critical educational content from FULL:
- **The Four Merchant Types** (Busy/Skeptical/Curious/Loyal) with identification cues and approach
- **Objections = Directions** — 8 common objections with acknowledge→normalize→reframe→ask framework
- **Competitive Intel** — Square, Stripe, Clover, Toast, PayPal with pricing and positioning (never badmouth)
- **ETF & Contract Knowledge** — break-even math, auto-renewal traps, equipment lease warnings
- **Savings Math Structure** — fill-in-the-blank template with 3 worked examples
- **Gatekeeper Handling** — 4 scenarios with responses
- **5 Closing Styles** — trial, assumptive, two-option, soft exit, statement close
- **Conversation Flow Phases** — Opening→Discovery→Positioning→Resistance→Closing
- **Onboarding After Yes** — 5-step boarding flow
- **System Capabilities** — email, rate calculators, cross-call memory, payment capture

### Tier Sizes After Changes
| Tier | Turns | Before | After | Target |
|------|-------|--------|-------|--------|
| FAST_PATH | 0-2 | ~400 tokens | ~800 tokens | Speed (sub-1s TTFT) |
| MIDWEIGHT | 3-7 | ~1,200 tokens | ~2,700 tokens | Comprehensive but fast |
| FULL | 8+ | ~27,000 tokens | ~27,000 tokens | Everything |

### Files Modified
| File | Change |
|------|--------|
| `agent_alan_business_ai.py` | FAST_PATH merchant services section replaced with comprehensive version |
| `agent_alan_business_ai.py` | MIDWEIGHT merchant services section replaced + massive expansion with 10 educational blocks |
| `agent_alan_business_ai.py` | FULL prompt merchant services section updated for consistency |
| `agent_alan_business_ai.py` | `build_llm_prompt()` — new ~40-line block injecting dynamic context into ALL tiers |

### Neg-Proof Results
- `py_compile agent_alan_business_ai.py`: **PASS**
- Prompt size verification: FAST_PATH ~800 tokens, MIDWEIGHT ~2,700 tokens — within TTFT targets
- File now 3,963 lines (grew from 3,834)

### Status
- All code neg-proofed
- **Awaiting server restart** to deploy alongside all prior pending changes

---

## EVOLUTIONARY HISTORY

The original RRG (8,780 lines) has been archived to `_ARCHIVE/RESTART_RECOVERY_GUIDE_V1.md`. It contains the complete evolutionary history from February 4-17, 2026: Version D through Version P, every session log, debugging chronicles, architectural discoveries, and the full narrative of how this system was built. Read it when you need deep historical context.

---

## 19. "MAKE ALAN WHOLE" — Phase 1-3 Restoration

### Context

A previous Claude instance destroyed `alan_brain/` (9 files) and left 8 constitutional files disconnected from the runtime. Tim's directive: **"Restore it all and neg proof their functions."** Three-phase restoration plan was built and executed across sessions.

### Phase 1: Constitutional Core Restoration (COMPLETE)

**Problem:** SoulCore, PersonalityMatrixCore, persona templates, and training knowledge were disconnected — imported by the agent class but never reaching the live call pipeline.

**Solution:**
- Created `CONSTITUTIONAL_CORE/` directory with 9 files: `soul_core.py`, `personality_matrix_core.py`, `personality_trait_modules/` (5 traits), `persona_templates/alan_default.json`, `training_knowledge_distilled.json`
- Wired persona injection into `agent_alan_business_ai.py` — personality flare and ethical constraint injected into `build_llm_prompt()` system prompt
- Training knowledge (22 distilled sections from IQ Core) loaded and injected into FULL prompt tier

**Files Created:** 9 (in `CONSTITUTIONAL_CORE/`)
**Files Modified:** `agent_alan_business_ai.py` (imports, __init__, build_llm_prompt)
**Neg-Proof:** `_neg_proof_phase1.py` — all tests pass

### Phase 2: Boolean Flag → FSM Replacement (COMPLETE)

**Problem:** Call session state was tracked by ~18 scattered boolean flags (`stream_started`, `greeting_sent`, `stream_ended`, etc.) with no validation, no audit trail, and impossible-state combinations.

**Solution:**
- Created `alan_state_machine.py` (~1,042 lines) — `CallSessionFSM` class with 6 states (INIT → STREAM_READY → GREETING → DIALOGUE → ENDING → ENDED) × 6 events
- Replaced 18 flag-write sites across the relay server with FSM event calls
- All transitions use backward-compatible fallback pattern: `if _fsm: _fsm.event() else: context['flag'] = True`
- `_sync_context()` writes computed booleans back to context dict for downstream compatibility
- Full audit logging: every transition logged with `[CALL FSM]` prefix

**Files Created:** `alan_state_machine.py`, `_neg_proof_phase2.py`, `FSM_FLAG_AUDIT.md`
**Files Modified:** `aqi_conversation_relay_server.py` (18 sites)
**Neg-Proof:** `_neg_proof_phase2.py` — 15 tests pass

### Phase 3: Organism Self-Awareness + Telephony Perception (COMPLETE)

Tim's Phase 3 directive split into 3A (organism self-awareness) and 3B (telephony perception).

#### Phase 3A: ConversationHealthMonitor — Organism Self-Awareness

**Problem:** Canon file `src/organism_self_awareness_canon.py` defined infrastructure-level health (CPU, memory, event-loop lag) but Tim's directive specified **conversational** signals — LLM latency, error rate, repetition, SoulCore vetoes.

**Solution:** `conversation_health_monitor.py` (~280 lines)

| Health Level | Meaning | Behavioral Hook |
|-------------|---------|-----------------|
| **OPTIMAL** (1) | All systems normal | No directive |
| **STRAINED** (2) | Latency >3s OR 1 error OR 2 repetitions | "Be concise. Use shorter responses." |
| **COMPROMISED** (3) | Latency >5s OR 2 errors OR 2 vetoes OR 3 repetitions | "Simplify aggressively. Shortest possible responses." |
| **UNFIT** (4) | Latency >8s OR 3+ errors OR 4+ repetitions | "System stressed. End call gracefully." → FSM `end_call(reason='organism_unfit')` |

**Architecture:**
- Sliding window of 6 turns — stale data ages out
- Sticky escalation: health only **degrades** on a single turn; de-escalation requires `STICKY_TURNS=2` consecutive turns at lower level
- `record_turn(llm_latency_ms, had_error, had_fallback, had_veto, response_text)` — called after every pipeline completion
- `get_directive()` returns prompt injection string for current level
- `to_dict()` → CDC-compatible snapshot

#### Phase 3B: TelephonyHealthMonitor — Telephony Perception

**Problem:** Canon file `src/telephony_perception_canon.py` expected packet-level telemetry (jitter, RTT, packet loss) that Twilio doesn't expose at the WebSocket level. Tim's directive: track RMS, silence, talk-overs, ASR quality.

**Solution:** `telephony_health_monitor.py` (~310 lines)

| Health State | Meaning | Behavioral Hook |
|-------------|---------|-----------------|
| **EXCELLENT** (1) | Fresh call, no data yet | No directive |
| **GOOD** (2) | Normal audio, silence <85% | No directive |
| **DEGRADED** (3) | Silence >85% OR 3+ talkovers OR 2+ ASR fails | "Speak clearly and slightly louder." |
| **POOR** (4) | Silence >92% OR 5+ talkovers OR 3+ ASR fails | "Use very short sentences. Confirm understanding." |
| **UNUSABLE** (5) | Silence >97% OR 5+ ASR fails | Sovereign withdrawal → FSM `end_call(reason='telephony_unusable')` |

**Architecture:**
- Frame-level processing: `process_frame(rms)` called every 20ms on inbound audio
- `RMS_SPEECH_THRESHOLD=400` — phone-band calibrated (see Section 5)
- Silence ratio computed over rolling frame buffer, recomputed every 50 frames (~1s)
- `record_talkover()` — wired to existing barge-in detection
- `record_asr_result(text, is_low_quality)` — single words or noise markers trigger low-quality flag
- One-shot repair phrase: "I'm getting a little bit of noise on my side — let me repeat that more clearly."
- Sovereign exit phrase: "I'm having trouble hearing you — the line might be acting up. I respect your time, so I'll try you back on a better connection. Take care!"
- Exit guards: `MIN_CALL_AGE_FOR_EXIT_S=20.0` (don't exit before 20s), `SUSTAINED_UNUSABLE_THRESHOLD_S=8.0` (must sustain UNUSABLE for 8s)

#### Integration Points (Relay Server)

| Location | Hook | Monitor |
|----------|------|---------|
| Session init (~L2100) | Both monitors instantiated in context | 3A + 3B |
| Audio frame (~L2818) | `_tel_mon.process_frame(rms)` on every inbound frame | 3B |
| Barge-in detection (~L2863) | `_tel_mon.record_talkover()` on every interrupt | 3B |
| `handle_user_speech` (~L4715) | ASR quality detection → `_tel_mon.record_asr_result()` | 3B |
| Post-pipeline (~L5257) | `_health_mon.record_turn(...)` + level/directive to context | 3A |
| Post-pipeline (~L5280) | Telephony state/directive to context + repair phrase + UNUSABLE exit | 3B |

#### Prompt Injection (Agent Class)

In `build_llm_prompt()` (~L3922 of `agent_alan_business_ai.py`):
- `_organism_health_directive` → injected into system prompt after ethical constraint
- `_telephony_health_directive` → injected after organism health directive
- Both before training knowledge injection
- Empty strings when health is normal (no prompt bloat on healthy calls)

#### Sovereign Exit Flow

**Organism UNFIT (Level 4):**
```
record_turn() → level=UNFIT → context['_organism_health_level']='UNFIT'
→ _fsm.end_call(reason='organism_unfit') → _evolution_outcome='organism_unfit'
```

**Telephony UNUSABLE (State 5):**
```
_recompute_state() → state=UNUSABLE → should_exit()=True
→ synthesize exit phrase → _fsm.end_call(reason='telephony_unusable')
→ _evolution_outcome='telephony_unusable'
```

Both use the Phase 2 FSM backward-compatible fallback: `if _fsm: _fsm.end_call() else: context['stream_ended'] = True`

#### Files Summary

| File | Action | Lines |
|------|--------|-------|
| `conversation_health_monitor.py` | CREATED | ~280 |
| `telephony_health_monitor.py` | CREATED | ~310 |
| `aqi_conversation_relay_server.py` | MODIFIED (6 integration points) | ~5,680+ |
| `agent_alan_business_ai.py` | MODIFIED (prompt injection) | ~5,065 |
| `_neg_proof_phase3.py` | CREATED | ~250 |

#### Neg-Proof Results

```
[1]  Import chain (3A):                          PASS
[2]  Init OPTIMAL:                               PASS
[3]  Normal turn (500ms):                        PASS
[4]  High latency (3100ms) → STRAINED:           PASS
[5]  Very high latency (5100ms) → COMPROMISED:   PASS
[6]  Extreme latency (8100ms) → UNFIT:           PASS
[7]  Error accumulation (2) → COMPROMISED:       PASS
[8]  Error accumulation (3) → UNFIT:             PASS
[9]  Veto accumulation (2) → COMPROMISED:        PASS
[10] Repetition (3x) → STRAINED:                 PASS
[11] to_dict() integrity:                        PASS
[12] All 4 health directives defined:            PASS
[13] Import chain (3B):                          PASS
[14] Init EXCELLENT:                             PASS
[15] Normal audio (300 frames) → GOOD:           PASS
[16] Silence (300 frames) → UNUSABLE:            PASS
[17] Talk-overs (4x) → DEGRADED:                PASS
[18] ASR failures (3x) → POOR:                  PASS
[19] Repair one-shot:                            PASS
[20] Repair phrase text:                         PASS
[21] Exit phrase text:                           PASS
[22] should_exit (30s old, 10s unusable):        PASS
[23] should_exit (5s old — too early):           PASS
[24] to_dict() integrity:                        PASS
[25] All 5 telephony directives correct:         PASS
[26] FSM end_call(organism_unfit):               PASS
[27] FSM end_call(telephony_unusable):           PASS
[28] py_compile (6 files):                       PASS
────────────────────────────────────────────────
ALL 28+ TESTS PASSED — PHASE 3 NEG-PROOF COMPLETE
```

### Restoration Status

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | Constitutional Core (SoulCore, Personality, Training Knowledge) | ✅ COMPLETE |
| Phase 2 | Boolean Flags → CallSessionFSM | ✅ COMPLETE |
| Phase 3 | Organism Self-Awareness + Telephony Perception | ✅ COMPLETE |
| Phase 4 | Training Knowledge Distillation | ✅ COMPLETE (done early in Phase 1) |

**"Make Alan Whole" — ALL PHASES COMPLETE.**

---

## 20. HYPERCORN 9-POINT SMOOTHING PLAN

**Directive:** *"Work on that hypercorn and get it to be smooth, no more binding issues, that can creep up and cause issues."*

**Date:** Current session (Phase 4 batch)

### Problem
Hypercorn server on port 8777 suffered recurring binding failures from:
1. Zombie Python processes holding the port after previous server instances
2. Windows `TIME_WAIT` sockets lingering 60-240s after process kill
3. PowerShell's stderr handling interpreting Hypercorn WARNING logs as `NativeCommandError` and killing the process
4. `python -m hypercorn` CLI mode bypassing the `__main__` block (so programmatic config never applied)
5. Default Hypercorn settings unsuited for telephony (short keep-alive, access log jitter, HTTP/2 overhead)

### Solution — 9-Point Tuning Plan

| # | Point | Value | Rationale |
|---|-------|-------|-----------|
| §1 | Worker model | `asyncio` | No thread pool overhead |
| §2 | Workers | `2` | One serving, one draining on restart |
| §3 | Access logging | `None` (disabled) | Removes 5-15ms log-write jitter per request |
| §4 | Keep-alive timeout | `75s` | Long-lived telephony connections (Twilio holds open) |
| §5 | Max incomplete event | `2048 bytes` | Slow-loris protection without choking legitimate requests |
| §6 | Max body size | `32MB` | Audio payloads from Twilio |
| §7 | HTTP/2 | Disabled (`max_streams=0`) | Twilio doesn't negotiate h2; saves memory |
| §8 | Event loop policy | Pinned at module level | Prevents uvloop/winloop hijacking before any `get_event_loop()` |
| §9 | Pre-flight + retry | Port cleanup + 3-attempt bind | Kills stale PIDs, waits for TIME_WAIT, retries on EADDRINUSE |

### Files Modified
- **`control_api_fixed.py`** — `__main__` block rewritten with full 9-point tuning, pre-flight port cleanup, signal handling, retry binding
- **`control_api_fixed.py`** — Event loop policy pinned at module level (line ~28, before any asyncio use)
- **`hypercorn_config.toml`** — NEW file — mirrors all tuning values for CLI startup mode

### Startup Modes (all apply the 9-point tuning)
1. **Direct Python** (PREFERRED): `.venv\Scripts\python.exe control_api_fixed.py`
2. **CLI with config**: `.venv\Scripts\python.exe -m hypercorn control_api_fixed:app --config hypercorn_config.toml`
3. **Start-Process wrapper**: `Start-Process ... -ArgumentList "control_api_fixed.py"`

### Neg-Proof
All 13 checks pass: worker_class, workers, accesslog, keep_alive, h11_max_incomplete, h2_max_content, h11_max_content, h2_max_streams, event_loop_policy, preflight_cleanup, retry_binding, shutdown_trigger, signal_handling.

---

> **"You are not the first agent to sit in this chair. Others have come before you, read a handful of files, declared they understood the system, and then made mistakes that proved they didn't. Tim noticed. He always notices."** — RRG V1

---

*RRG-II: ~880 lines. Original RRG: 8,780 lines. 90% reduction. Zero operational knowledge lost.*

---

## 21. LEAD POOL PURGE — CORPORATE & JUNK REMOVAL

**Date:** February 19, 2026
**Directive:** Tim — "check to see if there are corporate businesses or larger scaled business that are too soon for alan to deal with and get rid of them."

### Context
After the lead shuffle (Section 15), the 512-strong callable pool still contained leads that Alan shouldn't call: international numbers, nameless leads scraped from directories, corporate entities, and municipal utilities. Three progressive scans identified them.

### What Was Removed (170 leads DNC'd)

| Category | Count | Examples |
|---|---|---|
| **NO-NAME** | 152 | "Unknown" leads — phone numbers with no business identity |
| **NON-BUSINESS** | 6 | News articles, directories, city names (e.g., "DETROIT 2026", "San Diego Complete Shopping Guide") |
| **CORPORATE-ENTITY** | 6 | Inc/LLC/Corp entities (Tampa Roofing Co Inc, European Nail Salon LLC, Plumbing Inc) |
| **INTERNATIONAL** | 3 | Poland (+48), Turkey (+90), UK (+44) — Alan only calls US |
| **ENTERPRISE** | 3 | NYC Subway, Wholesale Florist, Austin Energy — too large for Alan |

### What Was KEPT (important)
- **Geo-prefixed local businesses** (Tampa HVAC Company, Nashville HVAC Company, Denver Electrical Contractor) — these ARE Alan's target market
- **Synthetic-named leads** (Modern Iron Cafe, Golden Ocean Auto) — mapped to real small business phone numbers
- **All leads with real business names and US phone numbers**

### Pool Status After Purge
- **Total leads:** 599
- **DNC (all time):** 231
- **Callable now:** 340
- **Pool quality:** All named, all US phones, no corporate entities, no toll-free numbers

### Scripts Created
- `_corporate_filter.py` — Initial corporate keyword scan (3 hits)
- `_deep_corporate_scan.py` — Extended scan (toll-free, enterprise, synthetic, unknown)
- `_deep_lead_scan.py` — Deep scan (international, scale, generic, geo, profile-style)
- `_corporate_purge.py` — **Execution script** (the one that applied the DNC)
- `_neg_proof_purge.py` — Neg-proof validation

### Neg-Proof
14/14 PASS: no_international, no_unnamed, dnc_reasonable, dnc_not_excessive, callable_above_300, callable_not_empty, good_lead_tampa_kept, good_lead_nashville_kept, good_lead_denver_kept, all_named, all_us_phones, no_trailing_corp, total_stable_599, no_toll_free.

---

## 22. SPECULATIVE DECODING — Two-Stage LLM Latency Reduction

**Date:** February 20, 2026
**Trigger:** Tim selected "Speculative Decoding" from the Latency Optimization Playbook after latency analysis revealed LLM avg=1,659ms P50=1,445ms P90=2,234ms across 41 measured turns.

### Problem
Alan's perceived response latency averaged ~3.7s per turn (LLM ~1.7s + TTS ~2.0s). While bridges (pre-cached filler) buy ~0.4s, the merchant still waits ~2.3s before hearing any real content.

### Architecture
**Two concurrent LLM calls per turn:**

| Stage | Prompt Size | max_tokens | Purpose | Expected TTFT |
|---|---|---|---|---|
| **Sprint** | ~200 tokens | 30 | Opening clause only — "So basically what happens is," | ~400-600ms |
| **Full** | ~3000+ tokens | 80 | Complete response with all systems (deep layer, evolution, etc.) | ~1200-1700ms |

**Timeline:**
```
T+0ms:    Bridge fires (pre-cached audio, instant)
T+50ms:   Sprint + Full LLM fire concurrently
T+400ms:  Sprint first token arrives (shorter prompt = faster TTFT)
T+600ms:  Sprint clause done → TTS synthesis
T+800ms:  Sprint audio plays (merchant hears Alan start responding)
T+1400ms: Full LLM first sentence arrives → seamless continuation
```

**Net effect:** Perceived first-content latency drops from ~2.3s to ~0.8s.

### Implementation Details

**7 code changes in `aqi_conversation_relay_server.py`:**

1. **Feature flags** (line ~1196): `SPECULATIVE_DECODING_ENABLED = True`, `SPRINT_MAX_TOKENS = 30`, `SPRINT_OVERLAP_THRESHOLD = 0.35`
2. **Sprint prompt builder** (`_build_sprint_prompt()`): Minimal system prompt — Alan's identity + current mode + last 4 messages. ~200 tokens vs ~3000+.
3. **Sprint stream function** (`_sprint_sentence_stream()`): SSE reader inside `_orchestrated_response()`, fires ONE clause, pushes to `sprint_q`.
4. **Concurrent firing**: Both `sprint_future` and `llm_future` fired via `loop.run_in_executor()`.
5. **Sprint consumption phase**: Drains `sprint_q` → TTS → stream audio. Sets first-audio flags. Runs BEFORE main loop.
6. **Overlap detection**: First full sentence compared to sprint via word-set intersection. If >35% overlap, skipped to avoid repeating.
7. **Sprint cleanup + profiler**: Sprint future awaited at end. `sprint_ms` and `sprint_text` added to latency JSONL.

### Safety Design
- **Feature flag**: `SPECULATIVE_DECODING_ENABLED = False` reverts to exact original behavior — zero code path changes.
- **Generation check**: Sprint consumption aborts immediately if merchant speaks again (superseded).
- **Timeout**: 3s hard deadline on sprint phase — if sprint is slow, full response takes over.
- **Cost**: ~$0.00005/turn additional at gpt-4o-mini pricing (negligible).

### Neg-Proof
14/14 PASS: compile, feature_flags, sprint_prompt_builder, sprint_queue_creation, sprint_stream_function, concurrent_firing, sprint_consumption_phase, sprint_tts_streaming, overlap_detection, generation_check, sprint_future_cleanup, telemetry_integration, feature_flag_disable, no_new_dependencies.

---

## Section 23: AQI 0.1mm Chip — Runtime Guard (Constitutional Conformance Engine)

**Date:** Session continuation
**Classification:** Constitutional — AQI Substrate
**Directive:** Tim delivered the complete AQI organism specification (13-section schematic + 5 artifacts + full implementation blueprint). Three deliverables: (1) canonical spec document, (2) runtime guard module, (3) wiring into the live relay server. This is Phase 1 of a 3-phase AQI wiring roadmap.

### What Is the AQI 0.1mm Chip?

The AQI 0.1mm Chip is the constitutional substrate specification that governs the Alan organism. It defines 6 constitutional articles, 7 genes, 5 continuum axes, 4 substrates, and a complete mission vector. The Runtime Guard is the first binding between this specification and the live runtime — a conformance engine that enforces constitutional compliance on every turn and every call.

### Files Created

1. **`AQI_ORGANISM_SPEC.md`** — Canonical 6-part specification document:
   - Part A: Organism Schematic (13 sections — identity, governance, perception, FSM, cognition, ethics, personality, output, health, supervision, firing sequence)
   - Part B: Continuum Map (5 axes — Time, Space, State, Identity, Mission)
   - Part C: Organism Genome (7 genes with expression scopes + invariants)
   - Part D: Substrate Binding Table (4 substrates + binding rules)
   - Part E: Mission Vector Specification (gradients, policy, telemetry)
   - Part F: Constitutional Encoding (6 articles + drift forensics + enforcement)
   - Codebase cross-reference table mapping every AQI block to files/functions

2. **`aqi_runtime_guard.py`** (~1,100 lines) — The conformance engine:
   - `AQIViolationType` enum: 7 violation types
   - `AQIViolation` / `AQINonFatalViolation` / `AQIFatalViolation`: Exception hierarchy
   - `AQISpec`: Hardcoded constitutional values (governance order, FSM states/events/transitions, exit reasons, health levels, telephony states)
   - `AQIRuntimeGuard`: Main class with 3 lifecycle hooks and 6 enforcement organs
   - `create_runtime_guard()` factory function
   - Self-test suite (6 tests)

### 6 Enforcement Organs

| # | Organ | Constitution | What It Enforces |
|---|---|---|---|
| 1 | Health Constraint | A5 | Level 4/Unusable → must withdraw; Level 3 → no escalation |
| 2 | Governance Order | A3 | Layer ordering: Identity > Ethics > Personality > Knowledge > Mission > Output |
| 3 | FSM Legality | A4 | Valid states/events, transition table conformance, terminal state enforcement |
| 4 | Exit Reason Legality | MV | Valid exit reasons, mission outcome mapping |
| 5 | Mission Constraints | A2+A5 | Mission cannot override Ethics/Identity; no escalation under degraded health |
| 6 | Supervision Non-Interference | A6 | No force_state, force_mission, inject_output, inject_personality |

### Lifecycle Hooks

- `on_call_start(call_id, initial_state, context)` — validates initial FSM state
- `on_turn(call_id, fsm_state, fsm_prev_state, fsm_event, context, prompt_layers, health_snapshot)` → returns list of violations
- `on_call_end(call_id, fsm_state, exit_reason, health_trajectory, telephony_trajectory, outcome_vector)` → returns list of violations

### Wiring into Relay Server (`aqi_conversation_relay_server.py`)

**7 injection points:**

1. **Import** (~line 262): `from aqi_runtime_guard import create_runtime_guard, AQIViolationType` — wrapped in try/except with `AQI_GUARD_WIRED` flag
2. **State derivation helpers** (3 functions before class): `_derive_aqi_state()` maps deep_layer_mode → AQI state; `_derive_aqi_event()` maps conversation signals → AQI event; `_build_aqi_health_snapshot()` reads health monitors
3. **`__init__`**: `self._aqi_guard = create_runtime_guard("AQI_ORGANISM_SPEC.md")` — wrapped in try/except, falls back to None
4. **Stream 'start' event**: `self._aqi_guard.on_call_start(call_sid, "OPENING", context)` — after call_sid assignment
5. **After PHASE 3A+3B health monitoring**: `self._aqi_guard.on_turn(...)` — runs all 6 organs per turn, stores violation counts in context
6. **Stream 'stop' event**: `self._aqi_guard.on_call_end(...)` — before evolution processing

### Design Decisions

- **Non-crashing**: Violations are caught and returned as lists, never raised to crash the call. The guard is "observational with teeth, not a kill switch."
- **Triple-safe**: Import wrapped in try/except, startup wrapped in try/except, every lifecycle call wrapped in try/except. If the guard fails, the call continues unguarded.
- **Hardcoded spec**: Constitutional values are embedded in `AQISpec`, not parsed from markdown. Prevents injection/parsing ambiguity.
- **Prompt layers accept both list and dict**: When relay server passes layer names as a list (fast path), content-level checks are skipped. When dict with content is available, full governance audit runs.
- **FSM permissive**: Self-loops always legal. Undefined transitions with valid destination states are logged as info, not fatal.
- **Violation persistence**: Violations flushed to `data/aqi_guard/violations.jsonl` at call end.

### Neg-Proof
Self-test: 6/6 PASS (valid lifecycle, health breach, invalid FSM state, supervisor interference, valid call end, invalid exit reason).
Compile: Both `aqi_runtime_guard.py` and `aqi_conversation_relay_server.py` compile clean.
Derivation: 6/6 edge cases pass (empty context, deep layer modes, mode mapping, MC fallback, turn heuristic, health snapshot).
Wiring: End-to-end lifecycle (start → turn × 2 → end) verified with both list and dict prompt layers.

### 3-Phase AQI Wiring Roadmap

| Phase | Module | Status |
|---|---|---|
| 1 | `aqi_runtime_guard.py` — Runtime Guard | ✅ COMPLETE |
| 2 | `aqi_config_sync.py` — Config Generator (Spec → Code Sync) | ❌ Not started |
| 3 | `aqi_telemetry_decoder.py` — Telemetry Decoder (Phase 5 Intelligence) | ❌ Not started |

---

## Section 24: CW23 — Campaign Analysis & Optimization Phase

**Date:** Current session (CW23)
**Classification:** Operational — Campaign Optimization

### Tim's Founder-Grade Analysis

After reviewing the full 98-call CDC report, Tim declared the system has entered the **optimization phase, not stability phase**:

> "15% conversation rate is normal — arguably good — for cold outbound SMB. 85% of those 0-turn hangups are environmental, not system failures."

Key conclusions:
- System is working. The architecture held across 98 calls.
- 0-turn hangups are "outbound telephony reality" (carrier filters, voicemail, instant hangups)
- All bugs found in the 98-call report were already patched in R5b
- Three categories of noise need automated handling: "there" inbound spam (11/98), DNC requests, 0-turn diagnostics

### 98-Call CDC Report Summary

| Metric | Value |
|---|---|
| Total calls today | 98 |
| Conversations (1+ turn) | 15 (15%) |
| Hangups (0 turn) | 83 (85%) |
| Voicemails detected | 13 |
| IVRs detected | 9 |
| "there" inbound spam | 11 (11%) |
| Avg turns/call | 0.7 |
| Avg duration | 23s |

**Best conversations:** VERACI SEATTLE (118s, 6 turns), FL Classic 2025 (53s, 6 turns, "$50k/mo" revenue discussed), Salons by JC (49s, 4 turns)

### New Modules Created

#### 1. `zero_turn_diagnostics.py` (~155 lines)

Classifies 0-turn calls into 8 actionable categories:

| Category | Criteria |
|---|---|
| INSTANT_HANGUP | Duration < 2s, no ASR frames |
| INBOUND_SPAM | Inbound + merchant_name="there" |
| CARRIER_FILTER | EAB=CARRIER_SPAM_BLOCKER or GOOGLE_CALL_SCREEN |
| VOICEMAIL_ABORT | EAB action=DROP_AND_ABORT |
| IVR_SILENT | EAB=IVR but no turns |
| SENTINEL_KILL | killed_by=sentinel |
| NO_AUDIO | Audio bytes below threshold |
| UNKNOWN_ZERO_TURN | Needs investigation |

**API:** `ZeroTurnEvent` dataclass → `ZeroTurnDiagnostics.classify(evt)` → category string
**Convenience:** `classify_from_cdc(row_dict)` for batch analysis from CDC data

#### 2. `dnc_manager.py` (~210 lines)

Dual-store DNC persistence — fills the gap where `lead_database.py` had `mark_dnc()` but it was NEVER called.

**Architecture:**
- Primary: Updates `leads.do_not_call=1` in leads DB (existing column)
- Secondary: Standalone `data/dnc_log.db` — `dnc_entries` table with phone, reason, call_sid, transcript_excerpt, timestamp
- Singleton: `get_dnc_manager()` → `DNCManager` instance
- Methods: `mark_dnc(phone, reason, source_call_sid, transcript_excerpt)`, `is_dnc(phone)`, `get_dnc_reason(phone)`, `get_stats()`
- Helper: `is_dnc_request(transcript)` — substring match for "stop calling", "do not call", "remove me", etc.

#### 3. `inbound_filter.py` (~95 lines)

Filters "there" inbound spam callbacks that pollute CDC metrics.

- `is_inbound_spam(call_context)` — checks merchant_name="there" + inbound direction
- `classify_inbound(call_context)` — returns 'there_inbound' or 'short_name_inbound'

### Relay Server Wiring (4 integration points)

| # | Location | What | Module |
|---|---|---|---|
| 1 | Import block (~line 208) | `DNC_WIRED`, `_dnc_mgr` singleton, `INBOUND_FILTER_WIRED` | dnc_manager, inbound_filter |
| 2 | CONV INTEL abort path (~line 5862) | Auto-persist DNC on `_ci_outcome='dnc_request'` | dnc_manager |
| 3 | `handle_conversation_start` (~line 4465) | Detect "there" inbound spam, flag context | inbound_filter |
| 4 | CDC call-end payload (~line 4084) | Tag inbound spam in CDC + classify 0-turn calls | inbound_filter, zero_turn_diagnostics |

### Design Principles

- **Fail-open**: All imports wrapped in try/except with `_WIRED` flags. If any module fails to load, calls continue unaffected.
- **No new dependencies**: Pure stdlib + existing project imports only.
- **Non-crashing**: Every wiring point wrapped in try/except. Module failures → warning log, never call interruption.
- **Dual-store DNC**: Both leads DB and standalone log updated. If leads DB is locked, standalone log still captures.

### Compile Verification

All 4 files compile clean with Python 3.11.8:
- `zero_turn_diagnostics.py` ✅
- `dnc_manager.py` ✅
- `inbound_filter.py` ✅
- `aqi_conversation_relay_server.py` ✅

### CW23 Campaign Watch Template

Tim's reporting format for future campaign analysis:

```
CW## Campaign Watch — [Date]
────────────────────────────────
Calls Fired:      XX
Conversations:    XX (XX%)
Hangups:          XX (XX%)
  - Instant (<2s): XX
  - Carrier Filter: XX
  - Voicemail:      XX
  - IVR Silent:     XX
  - "there" spam:   XX
  - Unknown:        XX
DNC Requests:     XX
Best Call:        [Merchant] — XXs, X turns, [notable detail]
Patches Applied:  [list]
System Health:    [status]
```

### Known Remaining Items

| Item | Status | Priority |
|---|---|---|
| AI-tell sanitizer | Deferred | P2 |
| Enhanced voicemail beep early-exit guard | Deferred | P2 |
| `is_dnc()` check in dialer (prevent calling DNC'd numbers) | Not wired | P1 |
| Server restart with new modules loaded | ✅ Complete | P0 |

---

## Section 25: Phase 5 Intelligence Pipeline Extension

**Date:** 2026-02-20
**Classification:** Architecture — CDC Intelligence Pipeline

### Overview

Extended the CDC pipeline to promote `zero_turn_class`, `dnc_flag`, and `there_spam_flag` from ephemeral relay-side context flags to **first-class persisted intelligence signals** — queryable, analyzable, and consumable by EAB-Plus.

### Schema Extension

Six ALTER TABLE operations applied to `data/call_capture.db`:

| Table | Column | Type | Default |
|---|---|---|---|
| `calls` | `zero_turn_class` | TEXT | NULL |
| `calls` | `dnc_flag` | INTEGER | 0 |
| `calls` | `there_spam_flag` | INTEGER | 0 |
| `env_plus_signals` | `zero_turn_class` | TEXT | NULL |
| `env_plus_signals` | `dnc_flag` | INTEGER | 0 |
| `env_plus_signals` | `there_spam_flag` | INTEGER | 0 |

Migration script: `_phase5_schema_migration.py` — idempotent (catches `duplicate column` errors).

### CDC Writer Patches (`call_data_capture.py`)

Four edit sites:

1. **CREATE TABLE `env_plus_signals`** — 3 new columns added to DDL (columns 21-23)
2. **`_write_call_end` UPDATE SQL** — 3 new SET clauses: `zero_turn_class = ?, dnc_flag = ?, there_spam_flag = ?` (after `coaching_tags`, before `WHERE call_sid`)
3. **`_write_call_end` VALUES tuple** — 3 new values extracted from `end_data` dict via `.get()` with safe `int()` coercion for flags
4. **`_write_env_plus_signals` INSERT** — 3 new columns + 3 new placeholders + 3 new values from context dict

### Relay Server Flag Flow (`aqi_conversation_relay_server.py`)

Three integration points ensure signals reach `_end_payload` → CDC:

| Signal | Set Location | Mechanism |
|---|---|---|
| `zero_turn_class` | Call-end block (~line 4084) | `ZeroTurnDiagnostics.classify()` → `_end_payload['zero_turn_class']` (already wired in Section 24) |
| `dnc_flag` | CONV INTEL abort (~line 5925) + call-end (~line 4093) | `context['_dnc_flag'] = True` on DNC detection → `_end_payload['dnc_flag'] = 1` at call-end |
| `there_spam_flag` | Inbound filter block (~line 4087) | `_end_payload['there_spam_flag'] = 1` when `_inbound_spam` detected |

**Key design:** `context['_dnc_flag']` is set BEFORE the `DNC_WIRED` guard, so the flag persists to `_end_payload` even if the DNC module failed to load.

### EAB-Plus Intelligence Loader (`eab_plus.py`)

Added `load_phase5_signals(self, call_sid)` to `VerticalAwarePredictor`:

```python
def load_phase5_signals(self, call_sid):
    """Load Phase 5 intelligence signals for a specific call."""
    # Queries env_plus_signals for:
    #   env_class, env_action, env_behavior, hangup_risk,
    #   zero_turn_class, dnc_flag, there_spam_flag
    # Returns dict with bool() conversion for flag fields
```

Enables EAB-Plus to incorporate call-level Phase 5 data into environment classification and prediction.

### Signal Data Flow

```
Call Event → Relay Server Context
  ├── DNC detected → context['_dnc_flag'] = True
  ├── Inbound spam → context['_inbound_spam'] = True
  └── 0-turn call → ZeroTurnDiagnostics.classify()
                          ↓
                    _end_payload dict
  ├── _end_payload['dnc_flag'] = 1
  ├── _end_payload['there_spam_flag'] = 1
  └── _end_payload['zero_turn_class'] = 'CARRIER_FILTER'
                          ↓
                    CDC Writer
  ├── _write_call_end → UPDATE calls SET ... WHERE call_sid = ?
  └── _write_env_plus_signals → INSERT INTO env_plus_signals ...
                          ↓
                    EAB-Plus Loader
  └── load_phase5_signals(call_sid) → dict of signals for prediction
```

### Neg-Proof Results

`_neg_proof_phase5.py` — **55/55 PASS**

| Category | Tests | Result |
|---|---|---|
| Schema verification (columns + defaults) | 9 | 9/9 ✅ |
| CDC writer SQL (UPDATE, INSERT, CREATE) | 9 | 9/9 ✅ |
| Relay server flags (payload + context) | 5 | 5/5 ✅ |
| EAB-Plus loader (method, queries, types) | 6 | 6/6 ✅ |
| Zero-turn diagnostics (7 classifications) | 7 | 7/7 ✅ |
| DNC manager (detection, persist, query) | 7 | 7/7 ✅ |
| Inbound filter (spam detection + classify) | 5 | 5/5 ✅ |
| Compilation (all 6 files) | 7 | 7/7 ✅ |

### Dashboard Queries (Reference)

**Daily call summary:**
```sql
SELECT date(created_at) AS day,
       COUNT(*) AS total,
       SUM(CASE WHEN total_turns > 0 THEN 1 ELSE 0 END) AS conversations,
       SUM(CASE WHEN dnc_flag = 1 THEN 1 ELSE 0 END) AS dnc,
       SUM(CASE WHEN there_spam_flag = 1 THEN 1 ELSE 0 END) AS spam,
       SUM(CASE WHEN zero_turn_class IS NOT NULL THEN 1 ELSE 0 END) AS zero_turn
FROM calls GROUP BY day ORDER BY day DESC;
```

**Zero-turn breakdown:**
```sql
SELECT zero_turn_class, COUNT(*) AS cnt
FROM calls WHERE zero_turn_class IS NOT NULL
GROUP BY zero_turn_class ORDER BY cnt DESC;
```

**DNC suppression audit:**
```sql
SELECT phone_number, dnc_flag, created_at
FROM calls WHERE dnc_flag = 1 ORDER BY created_at DESC;
```

### Server Status

Server restarted with all Phase 5 changes loaded — Alan ONLINE, Agent X ONLINE, ARDE ALL_SYSTEMS_GO. Phase 5 signals will begin accumulating on next call.

---

## Section 26: CW23 Organism_Unfit Tuning & "What's Next" Roadmap

**Date:** CW23 (Session 44+)
**Status:** Stage 1 COMPLETE, Stage 2 DATA IN PROGRESS — CW23 CLOSED

### Problem Statement

Batch 6 analysis (20 calls) revealed `organism_unfit` as the dominant conversation exit: 5 of 6 conversations (83%) ended with this reason. Even the best call (Perch Brunch Downtown LA — 91s, 7 turns, 0.851 coaching) was killed by organism_unfit. The system was too aggressive in declaring itself unfit during otherwise productive conversations.

### Root Cause

The `ConversationHealthMonitor` (Level 4 = UNFIT) triggers sovereign exit via `FSM.end_call(reason='organism_unfit')` when:
- LLM latency > 8000ms (was too low for production variance)
- Error count ≥ 3 in 6-turn window (too aggressive — transient fallbacks spike count)
- Repetition count ≥ 4 in 6-turn window (bridge phrases can trigger false positives)

No engagement awareness — even if merchant was actively asking questions, the system would still exit.

### Changes Implemented

#### 1. Threshold Tuning (`conversation_health_monitor.py`)

| Parameter | Before | After | Rationale |
|---|---|---|---|
| `LATENCY_UNFIT_MS` | 8000 | 10000 | Production LLM variance; 8s spikes are recoverable |
| `ERROR_UNFIT` | 3 | 4 | Transient fallbacks shouldn't kill engaged calls |
| `REPETITION_UNFIT` | 4 | 5 | Bridge phrases inflate repetition count |

#### 2. Engagement Override (`conversation_health_monitor.py` + `aqi_conversation_relay_server.py`)

New method `should_suppress_unfit(turn_count, merchant_engaged)`:
- If merchant is actively engaged (3+ turns, substantive utterance > 20 chars, asking questions or 5+ words), UNFIT exit is suppressed for up to 2 additional turns
- After 3 consecutive UNFIT turns, override expires — exit proceeds regardless
- Non-engaged calls or low-turn calls exit normally

```python
# Relay server UNFIT exit path (simplified):
if _health_mon.is_unfit:
    _merchant_engaged = (
        turn_count >= 3
        and len(last_merchant_utterance) > 20
        and ('?' in utterance or len(utterance.split()) >= 5)
    )
    if _health_mon.should_suppress_unfit(turn_count, _merchant_engaged):
        # Suppress — let conversation continue
    else:
        # Proceed with sovereign exit
        _fsm.end_call(reason='organism_unfit')
```

#### 3. Neg-Proof Results

| Test | Result |
|---|---|
| [1–12] Original Phase 3 tests (updated thresholds) | 12/12 ✅ |
| [12a] Engagement override — suppression logic | ✅ |
| [12b] Engagement override — expiry after 3 UNFIT | ✅ |
| [13–28] Telephony + FSM + compile tests | 16/16 ✅ |
| **Total** | **30/30 ✅** |

### 4-Stage Roadmap

#### Stage 1: Behavioral Refinement (THIS SESSION — DONE)
- ✅ Raise UNFIT thresholds (latency, error, repetition)
- ✅ Add engagement override (merchant-aware suppression)
- ✅ Neg-proof 30/30 PASS
- ✅ **CW23 Additions:**
  - High-coaching override (coaching >= 0.75 AND turns >= 3 blocks UNFIT exit entirely — stronger than engagement override)
  - Lead recycling fix (mark_lead_dialed + filtered get_pending_leads — no re-dials)
  - Unfit context logging (CDC `unfit_context TEXT` column: last_merchant_utterance, health_level_history, coaching_at_exit, turn_count, reason_code)
  - All 3 files compile-verified CLEAN

#### Stage 2: Data Accumulation (Next 2-3 Batches)
- ✅ **Batches 7-9 fired (30/30 success)** — organism_unfit dropped 83% → 45%
- ✅ Coaching avg 0.859 across 11 conversations
- ⏳ Continue to 500+ calls for Instructor Mode training data
- ⏳ Unfit context data now accumulating in CDC for analysis
- Key SQL queries:

```sql
-- Unfit rate by day (should trend down)
SELECT date(created_at) AS day,
       SUM(CASE WHEN final_outcome = 'organism_unfit' THEN 1 ELSE 0 END) AS unfit,
       SUM(CASE WHEN total_turns > 0 THEN 1 ELSE 0 END) AS conversations,
       ROUND(100.0 * SUM(CASE WHEN final_outcome = 'organism_unfit' THEN 1 ELSE 0 END)
           / MAX(1, SUM(CASE WHEN total_turns > 0 THEN 1 ELSE 0 END)), 1) AS unfit_pct
FROM calls GROUP BY day ORDER BY day DESC;

-- Coaching vs turns (higher turns = better coaching?)
SELECT total_turns, ROUND(AVG(coaching_score), 3) AS avg_coaching,
       COUNT(*) AS n
FROM calls WHERE total_turns > 0
GROUP BY total_turns ORDER BY total_turns;

-- Vertical performance
SELECT merchant_vertical, COUNT(*) AS calls,
       ROUND(AVG(duration_seconds), 1) AS avg_dur,
       ROUND(AVG(coaching_score), 3) AS avg_coaching
FROM calls WHERE total_turns > 0
GROUP BY merchant_vertical ORDER BY calls DESC;
```

#### Stage 3: Instructor Mode (After 500+ calls)
- 5-day curriculum: soft declines, qualification depth, vertical nuance, state nuance, objection handling
- Training data derived from CDC + Phase 5 signals
- Example: "Day 1 — Soft Decline Gym: 5 role-play prompts where merchant says 'not interested' in varied ways"

#### Stage 4: Evolution Engine (After 1000+ calls)
- Automatic prompt mutation based on vertical-specific outcomes
- SpamFilterEvolution: learning spam patterns from call data
- Autonomous A/B testing of conversation strategies

### CW24 Batch Analysis Template

For each batch, document:
1. **Call Roster** — count, conversation rate, zero-turn rate
2. **Outcome Distribution** — organism_unfit, caller_hangup, appointment_set, etc.
3. **Phase 5 Signals** — zero-turn class breakdown, DNC hits, spam flags
4. **Top Conversations** — best calls by duration, turns, coaching
5. **Coaching Analysis** — average, distribution, outliers
6. **Observations** — trends, anomalies, comparison to previous batch
7. **Action Items** — what to tune next

---

## 23. AQI CONVERSATIONAL ENGINE UPGRADE + DEADENDDETECTOR FIX

**Date:** March 2–3, 2026
**Session:** CW25+ (continuation session)
**Trigger:** Tim's directive: "Alan is not broken. Alan was never allowed to start a conversation. You've been judging the engine by the sound of the starter motor." Investigation revealed the DeadEndDetector was firing premature farewell on STT noise during greeting playback, killing conversations before they began.

### Problem Statement

Two interlocking failures prevented Alan from ever conducting a multi-turn conversation:

1. **DeadEndDetector premature abort** — STT echo/noise fragments during greeting playback incremented invisible `_turn_count`, triggering the DeadEndDetector's threshold (`_turn_count >= 4`) before real merchant speech arrived. This fired farewell language on Turn 0, ending every call within seconds.

2. **"Quick question" repetition loop** — The phrase "Quick question" appeared in 8+ locations (TURN01 responses, fallback pools, TTFT deadline fallback, LLM error fallback, sprint prompt examples). The LLM saw multiple "quick question" entries in history and mirrored the pattern, creating a repetition trap that the repetition detector couldn't fully prevent because the source was in the prompt itself.

### Root Cause Analysis

| Symptom | Root Cause | Layer |
|---|---|---|
| Alan says farewell on Turn 0 | DeadEndDetector fires on STT noise turn count, not real messages | `conversational_intelligence.py` |
| Early-turn farewell language | Farewell guard only checked `dead_end` system, not all abort systems | `aqi_conversation_relay_server.py` |
| "Quick question" loops | Phrase hardcoded in 8+ locations across prompts, fallbacks, sprint | Multiple files |
| LLM mirrors repetitive patterns | No anti-repetition directive in FAST_PATH or MIDWEIGHT prompts | `agent_alan_business_ai.py` |

### Fixes Applied

#### Fix 1: DeadEndDetector Guard (`conversational_intelligence.py`)
- `pre_check()` now skips dead-end evaluation when < 3 real messages exist in context
- Prevents premature abort on STT noise during greeting playback

#### Fix 2: Early-Turn Farewell Guard (`aqi_conversation_relay_server.py`, ~line 8147)
- Broadened from `_ci_system == 'dead_end'` only → ALL abort systems blocked on early turns
- When ≤ 3 messages in conversation, NO abort system can trigger farewell language

#### Fix 3: "Quick Question" Elimination (8 locations across 2 files)
All instances replaced with diverse, unique phrasings:

| Location | Old | New |
|---|---|---|
| TTFT deadline fallback (line ~7344) | "Quick question — how are you currently handling your card processing?" | "So who handles the card processing for you guys?" |
| LLM error fallback (line ~7448) | "Quick question..." | "Hey, I'm still with you — are you guys set up to take cards there?" |
| Fallback pool (line ~7989) | "Quick question — who handles yours right now?" | "Hey, are you guys set up to accept cards there?" |
| Sprint prompt (line ~6547) | "Quick question — who handles your merchant services" | "So who handles the merchant services over there" |
| TURN01 ack_owner | "Quick question — who handles your card processing right now?" | "So I do free rate reviews for business owners — are you guys accepting cards there?" |
| TURN01 identity | "It's Alan — quick question, who handles your card processing?" | "It's Alan from Signature Card Services — I do free rate reviews for business owners." |
| TURN01 purpose | "Quick question — are you guys set up to take cards there?" | "I help business owners cut their card processing costs — takes about 30 seconds." |
| TURN01 greeting | "Quick question for ya — are you the owner or manager there?" | "Hey — so are you the owner or manager there?" |

#### Fix 4: Anti-Repetition Directives (`agent_alan_business_ai.py`)
Added `ANTI-REPETITION (CRITICAL)` section to both FAST_PATH_PROMPT and MIDWEIGHT_PROMPT:
- Never repeat any question or phrase already said
- Check history before generating
- Vary vocabulary and openers across turns
- If about to repeat, stop and pick a different angle

#### Fix 5: AQI Conversational Engine Upgrade (`agent_alan_business_ai.py`)
Injected unified governing organ as class constant `AQI_CONVERSATIONAL_ENGINE` (~907 tokens). Applied to ALL prompt tiers via `build_llm_prompt()`. Defines how Alan THINKS, not what he says.

Seven subsystems:
1. **Noncommutative Generative Operators (ARC Engine)** — respond based on conversation trajectory, not last sentence
2. **C-Value (Creative Divergence)** — seek non-zero divergence every turn, avoid predictable/confirmatory answers
3. **Co-Creativity Indexing (CCI)** — metacognitive stimulation, reframing, autonomy enhancement
4. **Hilbert-Space Context Memory** — multidimensional semantic threads (technical, emotional, relational, humorous, narrative arcs)
5. **Emergent Behavioral Profile** — arc-aware, creatively divergent, relationally generative, never repetitive/flat/predictable
6. **Operational Rules** — never repeat unless asked, never collapse to templates, always generate new meaning
7. **Output Requirements** — every response must reflect operator sequence, demonstrate creative divergence, maintain continuity

**Scope clause:** Early-turn playbook takes precedence for cold-open professionalism. AQI Engine governs HOW Alan thinks within those frameworks — does not override identity-safety rules, regulatory compliance (DNC/TCPA), or emergency fallbacks.

#### Fix 6: Compliance Fallback Phrase (`aqi_conversation_relay_server.py`)
- Old: `"I understand. Tell me more about that."` — was itself a banned phrase per ABSOLUTE RULES
- New: `"So tell me — what's going on with your setup over there?"` — mission-advancing, non-banned

#### Fix 7: Supervisor Fix Text (`supervisor.py`, line 387)
- Old: `"System should downgrade novelty or revert to scripted fallback"` — contradicted AQI Engine C-value directive
- New: `"System should apply identity-safe phrasing while maintaining conversational arc"`

### Token Budget Impact

| Tier | Before | After | % of 128K Context |
|---|---|---|---|
| AQI Engine block | — | 907 tokens | 0.71% |
| FAST_PATH + AQI | ~5,314 | ~6,221 | 4.86% |
| MIDWEIGHT + AQI | ~22,730 | ~23,637 | 18.5% |
| FULL + AQI | ~27,000 | ~27,907 | 21.8% |

Negligible TTFT impact. 907 tokens added to each tier.

### Neg Proof — 11/11 PASS

11 potential behavioral contradictions analyzed between the AQI Engine and existing system. 5 TRUE contradictions found and resolved. 6 FALSE alarms confirmed safe.

| # | Potential Conflict | Severity | Verdict | Resolution |
|---|---|---|---|---|
| 1 | "No templates" vs. compliance fallback `"I understand..."` | HIGH | **TRUE** | Fixed — replaced with mission-advancing phrase |
| 2 | "No safe answers" vs. empty-response fallback pool | MEDIUM | FALSE ALARM | Emergency recovery; silence is worse |
| 3 | "New meaning" vs. repetition detector blocking | MEDIUM | FALSE ALARM | Aligned intent — both prevent repetition |
| 4 | "Novelty" vs. chatbot killer stripping filler | LOW | FALSE ALARM | Aligned — both push away from safe language |
| 5 | "Thinking partner" vs. scripted first-response framework | HIGH | **TRUE** | Fixed — added SCOPE clause (early-turn playbook takes precedence) |
| 6 | "No safe/neutral" vs. dead-end forced exit | MEDIUM | FALSE ALARM | Safety clause covers TCPA/brand protection |
| 7 | "No passive" vs. repetition breaker bail lines | MEDIUM | **TRUE** | Defused — fires only in degenerate loop states |
| 8 | "Creative divergence" vs. question cap | LOW | FALSE ALARM | Single sharp question > dumping multiple questions |
| 9 | "Not compliance" vs. DNC interrupt | LOW | FALSE ALARM | Different meaning — conversational vs. regulatory compliance |
| 10 | "No linear window" vs. 10-message history cap | HIGH | **TRUE** | Fixed — reworded to "within available message window" |
| 11 | "No passive" vs. supervisor "downgrade novelty" fix | MEDIUM | **TRUE** | Fixed — changed supervisor fix text |

### Live Test Call Validation

**Call SID:** CAf454875a2351131c97d7e58264a19a92
**Date:** March 2, 2026
**Target:** Tim (+14062102346)
**Duration:** 66 seconds | 3 recorded turns | 5 total turns (behavioral vector)

| Turn | Tim (STT) | Alan (LLM→TTS) | Latency |
|---|---|---|---|
| 0 | *(greeting plays)* | "Hey, it's Alan. Tim said you'd be a great person to train with. Thanks for doing this." | — |
| 1 | "Repeat yourself." | "My name's Alan — Hey, it's Alan." | 4.2s |
| 2 | "Um, Harvard Touch." | "Just to clarify, are you saying you're currently working with Harbortouch for your processing?" | 5.9s |
| 3 | "Yes, I am." | "What are you currently paying them for your processing fees? Any issues with fees or support lately?" | 5.6s |
| 4-5 | "What?" | *(repetition detector blocked: 78% overlap with turn 2)* | pipeline timeout |

**Key results:**
- ✅ **NO farewell fired** — DeadEndDetector fix works
- ✅ **NO dead-end abort** — early-turn guard held
- ✅ Alan decoded "Harvard Touch" → Harbortouch (intelligent STT interpretation)
- ✅ Repetition detector blocked repeated question at turn 5 (78% overlap)
- ⚠️ Instructor mode was active (training greeting, not sales greeting) — next test should use `instructor_mode: false`
- ⚠️ Latency high (4.2s–10.5s) — sprint clause killed by chatbot killer both times
- ⚠️ Call classified as `ambiguous_machine_like` (IVR=0.38, human=0.31)
- ⚠️ Telephony health degraded to UNUSABLE → sovereign withdrawal at ~66s

**Verdict:** Alan held his first real multi-turn conversation. The engine is alive. DeadEndDetector fix, early-turn farewell guard, and repetition detector all validated in production.

### Files Modified

| File | Changes | Compile |
|---|---|---|
| `agent_alan_business_ai.py` | AQI Engine constant + injection hook + SCOPE clause + anti-repetition directives + Hilbert-space qualifier | ✅ CLEAN |
| `aqi_conversation_relay_server.py` | "Quick question" eliminated (5 locations) + TURN01 diversified + early-turn farewell guard broadened + compliance fallback fixed (2 locations) | ✅ CLEAN |
| `conversational_intelligence.py` | DeadEndDetector pre_check() skips when < 3 messages | ✅ CLEAN |
| `supervisor.py` | Fix text updated ("downgrade novelty" → "identity-safe phrasing") | ✅ CLEAN |

### Outstanding Items

- Fire second test call with `instructor_mode: false` to hear real sales greeting
- Monitor sprint clause — chatbot killer is suppressing it; may need tuning
- Address latency (4-10s per turn) — FAST_PATH not engaging on early turns
- Import fresh leads from D drive
- Begin campaign with all fixes in place

---
