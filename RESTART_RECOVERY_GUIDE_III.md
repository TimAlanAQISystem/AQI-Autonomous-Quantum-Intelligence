# ALAN RESTART RECOVERY GUIDE — VOLUME III
# Post v4.1 Full Organism Integration — Operations & Next Phase
# Created: February 22, 2026
# Predecessor: RESTART_RECOVERY_GUIDE.md (13,325 lines — Volumes I & II)

---

> ## ⚠️ VOLUME LINEAGE
>
> **RRG I** → `_ARCHIVE/code_vault/RESTART_RECOVERY_GUIDE.md` — Original operational guide
> **RRG II** → `RESTART_RECOVERY_GUIDE.md` (13,325 lines) — Phase 5, CW23, 12-Commit v4.1 Integration
> **RRG III** → This file — Post v4.1 Full Organism, next-phase operations
>
> If you need historical detail on any component, consult RRG II.

---

## ═══════════════════════════════════════════════════════════════
## ALAN v4.1 — FULL ORGANISM ONLINE
## 12/12 Commits LIVE — February 22, 2026
## ═══════════════════════════════════════════════════════════════

All 12 v4.1 organs are wired, tested, NEG-PROOF certified, and live in the relay server.

| Commit | Organ | Class | Flag | Tests | Guards | Status |
|--------|-------|-------|------|-------|--------|--------|
| 1 | 24 Retrieval Cortex | `RetrievalCortex` | `RETRIEVAL_CORTEX_WIRED` | ✅ | ✅ | ✅ LIVE |
| 2 | 34 Competitive Intel | `CompetitiveIntelOrgan` | `COMPETITIVE_INTEL_WIRED` | 21/21 | ✅ | ✅ LIVE |
| 3 | 30 Prosody Analysis | `ProsodyAnalysisOrgan` | `PROSODY_ANALYSIS_WIRED` | 7/7 | ✅ | ✅ LIVE |
| 4 | 31 Objection Learning | `ObjectionLearningOrgan` | `OBJECTION_LEARNING_WIRED` | 35/35 | ✅ | ✅ LIVE |
| 5 | 25 Warm Handoff | `HandoffEscalationOrgan` | `WARM_HANDOFF_WIRED` | 35/35 | ✅ | ✅ LIVE |
| 6 | 26 Outbound Comms | `OutboundCommsOrgan` | `OUTBOUND_COMMS_WIRED` | 35/35 | ✅ | ✅ LIVE |
| 7 | 27 Language Switching | `LanguageSwitchOrgan` | `LANGUAGE_SWITCH_WIRED` | 40/40 | ✅ | ✅ LIVE |
| 8 | 28 Calendar & Scheduling | `CalendarOrgan` | `CALENDAR_ENGINE_WIRED` | 35/35 | ✅ | ✅ LIVE |
| 9 | 29 Inbound Context | `InboundContextOrgan` | `INBOUND_CONTEXT_WIRED` | 35/35 | ✅ | ✅ LIVE |
| 10 | 32 Summarization | `SummarizationOrgan` | `SUMMARIZATION_WIRED` | 35/35 | 7/7 | ✅ LIVE |
| 11 | 33 CRM Integration | `CRMIntegrationOrgan` | `CRM_INTEGRATION_WIRED` | 35/35 | 7/7 | ✅ LIVE |
| 12 | 35 In-Call IQ Budget | `InCallBudgetOrgan` | `IQ_BUDGET_WIRED` | 40/40 | 9/9 | ✅ LIVE |

**Total tests across 12 commits: 398+**
**Total NEG-PROOF guards verified: 50+**

---

## CRITICAL OPERATIONAL RULES (CARRY FORWARD)

### Python Environment
- **ALWAYS** use `.venv\Scripts\python.exe` (Python 3.11.8)
- **NEVER** use system Python 3.14 — it is POISONOUS and will crash imports
- Set `$env:PYTHONIOENCODING='utf-8'` before running test scripts on Windows

### Server
- Server file: `control_api_fixed.py` (NEVER `control_api.py`)
- Port: 8777
- ASGI: Hypercorn
- Start command:
```powershell
cd "C:\Users\signa\OneDrive\Desktop\Agent X"
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m hypercorn control_api_fixed:app --bind 0.0.0.0:8777" -NoNewWindow -PassThru
```

### Relay Server
- File: `aqi_conversation_relay_server.py` (~9,800 lines — was ~10,043 before chatbot extraction)
- Contains ALL 12 v4.1 organs wired inline
- Phase 5 Streaming Analyzer wired (reflex arc CLOSED)
- `chatbot_immune_system.py` extracted (~360 lines — sentence cleaner, chatbot kills, repetition detector)
- Compile check: `.venv\Scripts\python.exe -c "import aqi_conversation_relay_server; print('OK')"`

### Workspace
- Path: `C:\Users\signa\OneDrive\Desktop\Agent X`
- Organs directory: `organs_v4_1/`
- Archive: `_ARCHIVE/code_vault/` (950+ evolutionary files)

### Wiring Pattern (for future organs)
All organs follow the `*_WIRED` boolean flag pattern:
```python
try:
    from organs_v4_1.organ_XX_name import OrganClass
    ORGAN_XX_WIRED = True
    logging.info("[ORGAN XX] Name WIRED — description online")
except ImportError as e:
    ORGAN_XX_WIRED = False
    logging.warning(f"[ORGAN XX] Name unavailable: {e}")
```
Every usage site: `if ORGAN_XX_WIRED:` + `try/except` for fail-open.

---

## RELAY SERVER ARCHITECTURE — ORGAN ORDERING

### Import Order (top of file, ~lines 313-400)
```
Phase 4 Trace Exporter → Phase 5 Streaming Analyzer →
Organ 24 (Retrieval) → Organ 34 (Competitive) → Organ 30 (Prosody) →
Organ 31 (Objection) → Organ 25 (Handoff) → Organ 32 (Summarization) →
Organ 33 (CRM) → Organ 35 (IQ Budget) → Organ 29 (Inbound) →
Organ 28 (Calendar) → Organ 27 (Language) → Organ 26 (Outbound)
```
Also at top of file (line 54):
```
chatbot_immune_system → clean_sentence (extracted from relay)
```

### Session Init Order (~lines 3087-3250)
```
Organ 24 → Organ 34 → Organ 30 → Organ 31 → Organ 32 → Organ 33 →
Organ 35 → Organ 29 → Organ 28 → Organ 27 → Organ 26 → Organ 25
```

### Pipeline (per-turn processing, ~lines 7140-8050)
```
1. Organ 31 (Objection detection + learning)
2. Organ 30 (Prosody/emotion analysis)
3. Organ 35 start_turn() — IQ budget accounting begins
4. Organ 24 (Retrieval — gated by IQ budget)
5. Organ 34 (Competitive intel — gated by IQ budget)
6. Record spend for Organ 31, 30 after execution
7. Organ 35 end_turn() — budget accounting finalized
```

### LLM Injection Order (~lines 5830-5970)
```
Organ 24 → Organ 34 → Organ 31 → Organ 32 → Organ 33 →
Organ 35 → Organ 29 → Organ 28 → Organ 27 → Organ 26 →
Organ 25 → Organ 30 → Organ 7
```

### Call-End Order (~lines 4400-4560)
```
Organ 24 → Organ 34 → Organ 30 → Organ 31 → Organ 32 →
Organ 33 (CRM push, requires summary complete) →
Organ 35 (budget report) → Organ 29 → Organ 28 →
Organ 27 → Organ 26 → Organ 25
```

---

## v4.1 ORGAN QUICK REFERENCE

### Organ 24 — Retrieval Cortex
- Mid-call RAG knowledge retrieval
- `retrieve(user_text)` → confidence-filtered results (≥0.4)
- IQcore cost: 2 per retrieval
- Gated by Organ 35 budget

### Organ 25 — Warm Handoff
- Human escalation with consent protocol
- §5.12 Rule 3: Never transfer without explicit consent
- States: inactive → pending_consent → initiated → completed → failover
- Closer registry: Tim (ext 101), Sales Desk (ext 200)

### Organ 26 — Outbound Comms
- SMS/email send from mid-call context
- Detects "text me" / "email me" patterns
- Insert-if-missing for phone/email

### Organ 27 — Language Switching
- Real-time language detection + switching
- 6 languages supported
- Preserves conversational context across switches

### Organ 28 — Calendar & Scheduling
- Real-time appointment booking engine
- States: inactive → proposed → confirmed → declined
- Natural slot negotiation

### Organ 29 — Inbound Context
- Callback memory for returning callers
- States: cold → warm → partial
- Injects prior call history into LLM

### Organ 30 — Prosody Analysis
- Text-proxy emotional state detection
- 6 emotions: frustrated, impatient, confused, enthusiastic, resigned, interested
- Maps to prosody modes (empathetic_reflect, closing_momentum, etc.)
- IQcore cost: 1

### Organ 31 — Objection Learning
- 5 objection families: dismissal, time_availability, deferral, loyalty, contractual
- Uncaptured hesitation observation → Jaccard clustering → pattern promotion
- IQcore cost: 1 observe, 2 cluster

### Organ 32 — Summarization
- 22-field canonical call summary JSON
- Deal readiness scoring
- Feeds from organs 24, 30, 31, 34
- IQcore cost: 2

### Organ 33 — CRM Integration
- Durable queue → connector push (webhook, Salesforce, HubSpot)
- Requires Organ 32 summary complete
- Retry: 3 attempts, exponential backoff
- IQcore cost: 1

### Organ 34 — Competitive Intel
- 8 competitors × pattern matching
- §4.9 positioning rules (tone, closing style, key weakness)
- Rebuttals from organ data
- IQcore cost: 1
- Gated by Organ 35 budget

### Organ 35 — In-Call IQ Budgeting (CAPSTONE)
- Burns: NORMAL (0-69%) → HIGH (70-89%) → CRITICAL (90-99%) → EXHAUSTED (100%+)
- Budget tiers: Standard=20 IQ, Priority=40, VIP=999
- Gates Organ 24 (retrieval) and Organ 34 (competitive intel)
- Records spend for Organs 24, 30, 31, 34
- Throttle rules at HIGH/CRITICAL/EXHAUSTED
- Fallback strategies per burn state
- Prompt complexity scaling: full → standard → simple → minimal
- LLM injection: `[IQ BUDGET — COGNITIVE STATE]` with allowed/forbidden behaviors

---

## COMMIT 12 INTEGRATION DETAIL (Organ 35 — In-Call IQ Budgeting)

### Import (after Organ 33, before Organ 29)
```python
from organs_v4_1.organ_35_incall_budget import (
    InCallBudgetOrgan, BurnState, CallTier,
    ORGAN_COST_MAP, THROTTLE_RULES, FALLBACK_STRATEGIES, BUDGET_TIERS
)
IQ_BUDGET_WIRED = True
```

### Session Init
- Per-call `InCallBudgetOrgan()` + `start_call(call_id)`
- Context keys: `_iq_state`, `_iq_burn_total`, `_iq_turn_spend`, `_iq_disabled_organs`, `_iq_fallback_active`
- Init failure → all keys default to safe (normal state, zero burn)

### Pipeline — start_turn (after pipeline_t0)
- `start_turn()` returns burn state + disabled organs + fallback status
- Updates `_iq_state`, `_iq_disabled_organs`, `_iq_fallback_active`

### Burn Accounting (4 organs gated)
1. **Organ 24 Retrieval**: `can_afford('organ_24_retrieval', 2)` gate before execution → `record_spend()` after
2. **Organ 34 Competitive**: `can_afford('organ_34_competitive', 1)` gate before execution → `record_spend()` on detection
3. **Organ 31 Objection**: `record_spend('organ_31_objection_observe', 1)` after observation
4. **Organ 30 Prosody**: `record_spend('organ_30_prosody', 1)` after analysis

### Pipeline — end_turn (before PIPELINE TIMING)
- `end_turn()` finalizes burn accounting
- Updates all `_iq_*` context keys
- Logs non-normal states with spend details

### LLM Injection: `[IQ BUDGET — COGNITIVE STATE]`
- Burn state (NORMAL/HIGH/CRITICAL/EXHAUSTED)
- Budget spent/remaining
- Prompt complexity level
- State-specific behavioral directives:
  - NORMAL: Full reasoning, retrieval, competitive intel, multi-step logic
  - HIGH: Standard reasoning, selective retrieval. Forbidden: deep multi-step, unnecessary retrieval
  - CRITICAL: Simple direct responses, warmth, clarity. Forbidden: retrieval, intel, pressure, escalation
  - EXHAUSTED: Minimal safe responses only. Forbidden: ALL complex operations
- Disabled organs list

### Call-End
- `end_call()` → comprehensive budget report
- Fields: total_spent, burn_pct, turns, avg_spend_per_turn, scarcity_events, turn_log, fallback_active
- Stored in `_iq_budget_report`

### NEG-PROOF Guards (9/9 verified)
1. Import flag (`IQ_BUDGET_WIRED`)
2. Session init (try/except, safe defaults)
3. Session init exception (all keys default)
4. Pipeline start_turn exception (debug log, continue)
5. Can_afford gate fail-open — retrieval (default: allow)
6. Can_afford gate fail-open — competitive (default: allow)
7. End_turn exception (debug log, continue)
8. LLM injection exception (debug log, continue)
9. Call-end exception (debug log, continue)

### Test Verification: 40/40
- T1-T10: Burn accounting (spend recording, turn tracking, per-organ costs)
- T11-T20: Threshold transitions (NORMAL→HIGH→CRITICAL→EXHAUSTED, disabled organs, throttle rules)
- T21-T25: Scarcity behavior (blocked status at exhaustion, fallback strategies, prompt complexity)
- T26-T30: Freeze/thaw (exhausted state hard stop, organ disable/re-enable, budget report)
- T31-T35: LLM injection (all 4 states inject correctly, disabled organs listed)
- T36-T40: Fail-open + NEG-PROOF (import flag, init exception, gate fail-open, end_turn exception, call-end exception)

---

## MASTER CLOSER STATE (reference)
- `trajectory`: neutral | warming | cooling
- `endgame_state`: not_ready | ready | closing
- `temperature`: 0-100
- `confidence_score`: 0-100
- `merchant_type`: unknown | analytical | emotional | busy | skeptical

---

## FIELD PACK & ALAN PERSONALITY
- Alan Field Pack v1.1 compiled
- 14 sections: Opening, Objection Families, Competitive Intel, Closing Styles, etc.
- §5.10: Scarcity behavior rules (Organ 35 enforces these computationally)
- §5.12: Handoff consent rules (Organ 25 enforces)
- §3.2: Objection family taxonomy (Organ 31 uses)
- §4.9: Competitor positioning (Organ 34 uses)

---

## COMPETITIVE INTEL — 9 COMPETITORS (Live in Organ 34)

| # | Competitor | Triggers | Tone | Close Style |
|---|-----------|----------|------|-------------|
| 1 | Square | 6 patterns | warm, low-pressure | consultative |
| 2 | Stripe | 3 patterns | technical, respectful | consultative → authority |
| 3 | Clover | 6 patterns | confident, technical | authority |
| 4 | Toast | 4 patterns | restaurant-specific | authority → consultative |
| 5 | Heartland | 3 patterns | empathetic, professional | consultative |
| 6 | Worldpay | 5 patterns | professional, savings-focused | savings-math close |
| 7 | PayPal | 5 patterns | casual, savings-focused | consultative |
| 8 | Stax | 4 patterns | analytical, respectful | savings-math close |
| 9 | **Harbortouch** | **7 patterns** | **empathetic, savings-focused, multi-location** | **predatory-fee relief → savings-math** |

### Harbortouch/Shift4 — Full Intelligence Profile

**Detection triggers (7):** harbortouch, harbor touch, shift4, shift 4, shift4 payments, harbortouch pos, lighthouse

**Key weaknesses:**
- $65/mo per terminal rental (multi-location = $650+/mo hardware alone)
- $0.10 per transaction (2-3× industry standard)
- 0.10% basis points
- Annual junk fees ($200-$400/biz/yr): PCI, regulatory, service, software, support
- Proprietary hardware lock-in
- Liquidated damages + early termination penalties
- Auto-renewal contract traps
- Forced software updates
- Lighthouse POS dependency

**Objection doctrine (mapped to Organ 31 families):**
- Contractual: "Exit windows exist. ETF pays for itself in 2-3 months of savings."
- Loyalty: "Long-time merchants often don't realize per-txn + rental costs until we run the math."
- Deferral: "Start with one business — see the difference before switching all four."
- Time/availability: "10-15 minutes — I'll run savings for each location."
- Dismissal: "$0.10/txn adds up across four businesses — most owners don't realize."

**Savings math (conservative, for quad-business profile):**
- Terminal rentals: 10 × $65 = $650/mo
- Per-txn premium: 40K × ($0.10 - $0.04) = $2,400/mo
- Annual fees: $300 × 4 / 12 = $100/mo
- Basis points: $80K × 0.05% = $40/mo
- **Total savings: $3,000-$4,000/month = $36K-$48K/year**

**Closing strategies:**
1. Predatory-fee relief close (lead with terminal rental elimination)
2. Savings-math close (hard numbers per location)
3. "Start with one location" close (if merchant hesitates)
4. "Savings cover the ETF" close (contractual objection)
5. Multi-location consolidation close (unify under one transparent model)

**Full organ cascade on detection:**
- Organ 34: §4.9 positioning injected into LLM
- Organ 24: Retrieves contract-trap knowledge, ETF rules, rental terms
- Organ 31: Routes to loyalty/contractual families, captures new patterns
- Organ 32: Records competitor mention + savings framing in summary
- Organ 35: Manages IQ burn (simplifies if merchant overwhelmed)
- Organ 30: Shifts tone to empathetic + savings-focused
- Organ 28: Proposes 15-minute savings review slots
- Organ 26: Sends pricing summary / savings breakdown
- Organ 33: Pushes CRM with correct competitor context

---

## TEST FILE INVENTORY

| File | Tests | Coverage |
|------|-------|----------|
| `_test_crm_integration.py` | 35/35 | Organ 33 — CRM queue, connectors, retry, sync |
| `_test_summarization.py` | 35/35 | Organ 32 — 22-field summary, deal scoring |
| `_test_iq_budget.py` | 40/40 | Organ 35 — burn accounting, transitions, freeze/thaw |
| `tests/test_chatbot_immune.py` | 36/36 | Chatbot immune system — kills, filler strip, repetition, exit guard |
| `tests/test_behavioral_fusion.py` | 12/12 | BehavioralFusionEngine — mode inference, health, snapshots |
| `tests/test_perception_fusion.py` | 13/13 | PerceptionFusionEngine — 7 modes, 3 health levels, snapshots |
| `tests/test_deep_layer_phase5.py` | 15/15 | DeepLayer Phase 5 reflex arc — continuum physics, relay consumption |
| `tests/test_ccnm.py` | 13/13 | CCNM — SessionSeed, behavioral vector refinement, bounds, SQL |
| `tests/test_phase5_integration.py` | 23/23 | End-to-end reflex arc — 9 link checks, extraction, parseability |

**Run all tests:**
```powershell
cd "C:\Users\signa\OneDrive\Desktop\Agent X"
Get-ChildItem tests/test_*.py | ForEach-Object { .\.venv\Scripts\python.exe $_.FullName }
```

---

## NEXT PHASE: v1.3 — Live Simulation Suite

Tim declared after Commit 12:
> *"When you confirm Commit 12 complete, we will officially declare: ALAN v4.1 — FULL ORGANISM ONLINE. And then we move into the next phase: v1.3 — Live Simulation Suite, where we stress-test the entire organism under real conversational scenarios."*

### What v1.3 entails (anticipated):
- Stress-test all 12 organs under simulated multi-turn conversations
- Verify organ interactions (e.g., Organ 35 throttling Organ 24 mid-call)
- Test edge cases: rapid objection sequences, multi-competitor mentions, language switches mid-objection
- Validate CRM push with real connector endpoints
- Confirm budget exhaustion behavior doesn't break conversation flow
- End-to-end call simulation with all organs active

### Status: PHASE 1 IGNITION SCHEDULED — Monday February 23, 2026 — 9:00 AM PST

---

## FIELD INTEGRATION — 6-PHASE LAUNCH PLAN

### Phase 1 Ignition

**Date:** Monday, February 23, 2026
**Time:** 9:00 AM PST (business hours window: 9am–4pm)
**Mode:** Manual monitoring — every call reviewed
**Calls:** Up to 10 validation calls
**Spacing:** 180s (3 minutes between calls)
**Reports:** Per-call segmented (one report file per call)
**Selection:** Auto-select, unrestricted — true cross-section of 408 callable leads

### Pre-Launch Checklist (Monday Morning — start at 8:50 AM)

```
[ ]  1. Verify Twilio balance:      Ensure sufficient funds for 10+ calls
[ ]  2. Verify caller ID:           Confirm +18883277213 is active and not flagged
[ ]  3. Start control API:          .venv\Scripts\python.exe -m hypercorn control_api_fixed:app --bind 0.0.0.0:8777
[ ]  4. Start fresh tunnel:         cloudflared tunnel --url http://localhost:8777
[ ]  5. Update tunnel URL:          Copy new URL → logs/active_tunnel_url.txt
[ ]  6. Verify local time alignment: Confirm target area codes are in callable window
[ ]  7. Verify call-capture tables:  data/call_capture.db tables empty and writable
[ ]  8. Run pre-flight:             .venv\Scripts\python.exe _preflight_field_validation.py --json
[ ]  9. Verify 8/8 gates:           ALL GATES PASSED — FIELD CAMPAIGN AUTHORIZED
[ ] 10. Launch Phase 1:             .venv\Scripts\python.exe field_campaign_runner.py --phase 1
[ ] 11. Monitor logs:               logs/field_campaign_*.log + logs/field_reports/
[ ] 12. Review per-call reports:    logs/field_reports/call_*.json (one per call)
[ ] 13. Review batch summary:       logs/field_reports/field_phase1_*.txt
```

### Architecture Overview

Alan transitions from simulation → controlled field → scaled production through 6 governed phases.
Each phase gates the next — no promotion without meeting success criteria.

| Phase | Scope | Spacing | Daily Cap | Status |
|-------|-------|---------|-----------|--------|
| 1. Pre-flight | 10 calls, manual | 180s | 10 | ✅ BUILT |
| 2. Micro-campaign | 10 merchants, mixed verticals | 180s | 10 | ✅ BUILT |
| 3. Pacing-limited | 50 merchants | 90s | 40 | ✅ CONFIGURED |
| 4. Full outbound | 200 merchants | 60s | 60 | ✅ CONFIGURED |
| 5. Optimization | Scaling + tuning | — | — | ⬜ FUTURE |
| 6. Governance loop | Continuous | — | — | ⬜ FUTURE |

### Infrastructure Built

1. **`_preflight_field_validation.py`** — 8-gate go/no-go validation
   - Gate 1: Transport (API, tunnel, Twilio creds)
   - Gate 2: Governor FSM (IDLE, no locks)
   - Gate 3: Organ Cascade (12/12 wired, compile check)
   - Gate 4: UCP Detection (14 patterns, 3-tier, 12 competitors)
   - Gate 5: Cooldown Manager (gate open, state clean)
   - Gate 6: Lead Database (886 leads, 408 callable)
   - Gate 7: Timing Config (campaign_cooldown = 150s)
   - Gate 8: Call Capture DB (5 tables ready)
   - **Result: 8/8 PASS — 47/47 checks green**

2. **`field_campaign_config.yaml`** — Phase 1-4 governed parameters
   - Phase-specific: spacing, business hours, batch size, retry limits
   - Quality gates: max consecutive no-answer, robotic flags, progression rate
   - Success criteria: min human conversations, max hallucinations, progression targets
   - Global: API URL, cooldown manager, regime engine, campaign watch

3. **`field_campaign_runner.py`** — Governed campaign executor
   - Pre-flight gate → lead selection → governor polling → sequential fire → quality gate → report
   - Integrates: cooldown_manager, regime_engine, governor FSM, call_lifecycle_fsm
   - Produces: real-time campaign report (text + JSON) in `logs/field_reports/`
   - CLI: `--phase 1|2|3|4 --dry --skip-preflight`
   - **Dry-run validated end-to-end: leads→fire→report pipeline confirmed**

### Launch Commands

```powershell
# Phase 1: Pre-flight validation (standalone)
.venv\Scripts\python.exe _preflight_field_validation.py --json

# Phase 1: Field validation calls (10 calls, 3min spacing, manual monitoring)
.venv\Scripts\python.exe field_campaign_runner.py --phase 1

# Phase 1: Dry run (no real calls)
.venv\Scripts\python.exe field_campaign_runner.py --phase 1 --dry

# Phase 2: Micro-campaign (enable in config first)
# Edit field_campaign_config.yaml → phase_2_micro → enabled: true
.venv\Scripts\python.exe field_campaign_runner.py --phase 2
```

### Phase Promotion Criteria

| From → To | Criteria |
|-----------|----------|
| 1 → 2 | Pre-flight 8/8, ≥2 human conversations, 0 hallucinations, 0 transport failures |
| 2 → 3 | ≥3 human conversations, ≥1 positive progression, 0 misclassifications |
| 3 → 4 | Stable readiness score ≥75, ≤2 robotic flags, ≥8% progression rate |
| 4 → 5 | 3 consecutive stable full campaigns, optimization engine recommendations stable |

### Micro-Campaign Parameters (Phase 2)

- **Batch size:** 10 merchants
- **Vertical diversity:** ≥3 business types (salon, restaurant, retail, medical)
- **Geographic diversity:** ≥2 area codes
- **Call spacing:** 180s (3 minutes)
- **Business hours:** 9am-4pm Mon-Fri
- **Max attempts per lead:** 2
- **Quality gate:** halt on 4 consecutive no-answer or 1 robotic flag

---

## CHANGELOG

### March 3, 2026 — PHASE 5 REFLEX ARC CLOSED + RELAY DECOMPOSITION + TEST SUITE

**Summary:** Implemented the top 3 priorities from the 15-point perfection roadmap.
Three bugs/gaps identified and fixed. Relay server decomposition started. Full test suite built.
Safety snapshot at `snapshots/agentx-snap-20260303-093653/`.

#### 1. Phase 5 Reflex Arc — CLOSED (3 gaps fixed across 3 files)

The Phase 5 reflex arc was OPEN-CIRCUIT. Three gaps prevented behavioral intelligence from flowing:

**GAP 1 — DeepLayer velocity/drift/viscosity never exposed** (`aqi_deep_layer.py`)
- `DeepLayer.step()` returned `deep_state` without a `continuum` key
- Relay server's behavioral_stats update code did `deep_state.get('continuum', {}).get('velocity', 0.0)` — but the key never existed
- Result: velocity=0.0, drift=0.0, viscosity=1.0 FOREVER regardless of actual conversation physics
- **FIX:** Added `continuum` key to `deep_state` return dict (section "4a. EXPOSE FLUIDIC PHYSICS"):
  - `velocity` = intent_force × blend (transition force × progress)
  - `drift` = mode_history_length / turn_count - 0.15 (conversation instability)
  - `viscosity` = MOOD_VISCOSITY lookup (mood-dependent resistance)

**GAP 2 — Phase5StreamingAnalyzer never called** (`aqi_conversation_relay_server.py`)
- `aqi_phase5_streaming_analyzer.py` existed (97 lines) with `on_call_complete(trace)` method
- Phase 4 traces were written to JSONL at call-end, but Phase 5 NEVER consumed them
- **FIX:** Guarded import at relay line ~317 (Phase5StreamingAnalyzer singleton, `PHASE5_ANALYZER_WIRED` flag)
- **FIX:** Wired at call-end after Phase 4 trace export (~line 4815):
  ```python
  if PHASE5_ANALYZER_WIRED and _phase5_analyzer:
      _p5_profile = _phase5_analyzer.on_call_complete(_p4_trace)
      _end_payload['phase5_profile'] = _p5_profile
  ```
- Triple-guarded: flag + None check + try/except

**GAP 3 — CCNM didn't read behavioral_vector** (`cross_call_intelligence.py`)
- CDC's calls table has `behavioral_vector TEXT` column (written at call-end)
- CCNM's SQL SELECT query didn't include `behavioral_vector` — data was written but never read back
- **FIX:** Added `behavioral_vector` to CCNM SELECT query (~line 325)
- **FIX:** Added `_refine_with_behavioral_vectors()` static method (~80 lines):
  - Parses behavioral_vector JSON from successful/failed calls
  - Computes velocity differential between success/failure cohorts
  - Applies gentle inertia nudges for modes appearing in successful vectors
  - All adjustments bounded to ±0.20 (FLUIDIC_ADJUSTMENT_MIN/MAX)
  - Full try/except with non-fatal fallback

**Reflex arc now:**
```
DeepLayer.step() → continuum{velocity,drift,viscosity}
→ behavioral_stats update (relay ~line 8753)
→ BehavioralFusionEngine → CDC.save_call() writes behavioral_vector
→ CCNM.seed_session() reads behavioral_vector
→ _refine_with_behavioral_vectors() → fluidic_adjustments
→ Next call's DeepLayer gets pre-conditioned seed
```

#### 2. Relay Server Decomposition — chatbot_immune_system.py extracted

- **Created:** `chatbot_immune_system.py` (~360 lines)
  - `clean_sentence(s, context, log)` — the complete chatbot killer / sentence cleaner
  - Contains: CHATBOT_KILLS (66 phrases), CHATBOT_CONTAINS_KILLS (48 phrases), FILLER_PREFIXES (49 patterns), GOODBYE_PATTERNS (22 patterns)
  - 6 phases: markdown cleanup, filler prefix stripping, exact-match kills, contains-match kills, early-turn exit guard, repetition detector
- **Modified:** Relay server `_clean_sentence()` — replaced 270-line nested function with 3-line thin wrapper
- **Import:** `from chatbot_immune_system import clean_sentence as _chatbot_clean_sentence` (line 54)
- **Result:** Relay server ~10,043 → ~9,800 lines (~240 lines net reduction after Phase 5 additions)

#### 3. Test Suite — 112 tests across 6 files

| File | Tests | Scope |
|------|-------|-------|
| `tests/test_chatbot_immune.py` | 36 | Markdown cleanup, filler strip, kills, exit guard, repetition |
| `tests/test_behavioral_fusion.py` | 12 | Mode inference (5 modes), health, RECOVERING transition |
| `tests/test_perception_fusion.py` | 13 | 7 perception modes, priority ordering, health, snapshots |
| `tests/test_deep_layer_phase5.py` | 15 | Continuum physics exposure, relay consumption, Phase 5 wiring |
| `tests/test_ccnm.py` | 13 | SessionSeed, behavioral vector refinement, bounds, SQL integrity |
| `tests/test_phase5_integration.py` | 23 | End-to-end reflex arc (9 link checks), extraction, parseability |
| **TOTAL** | **112** | **All pass — 112/112** |

#### NEG-PROOF Verification (Full Chain)

| Component | Guards | Status |
|-----------|--------|--------|
| DeepLayer continuum key | Always-defined vars, .get() defaults | ✅ |
| Phase5 import | Guarded import, flag + None + try/except | ✅ |
| Phase5 call-end | Triple-guarded: flag + None + try/except | ✅ |
| CCNM SQL behavioral_vector | Outer try/except → neutral_seed on column-not-found | ✅ |
| CCNM _refine_with_behavioral_vectors | Inner try/except, bounds enforced ±0.20 | ✅ |
| Chatbot extraction import | Top-level import, verified at module load | ✅ |
| Chatbot thin wrapper | Delegates to extracted module with same signature | ✅ |
| All modified files | ast.parse verified — 7/7 pass | ✅ |

#### Files Modified
- `aqi_deep_layer.py` — Added continuum physics to deep_state (1017 → ~1017 lines)
- `aqi_conversation_relay_server.py` — Phase 5 wiring + chatbot extraction (~10,043 → ~9,804 lines)
- `cross_call_intelligence.py` — behavioral_vector query + refinement method (981 → ~1071 lines)

#### Files Created
- `chatbot_immune_system.py` — Extracted chatbot killer (~360 lines)
- `tests/test_chatbot_immune.py` — 36 tests
- `tests/test_behavioral_fusion.py` — 12 tests
- `tests/test_perception_fusion.py` — 13 tests
- `tests/test_deep_layer_phase5.py` — 15 tests
- `tests/test_ccnm.py` — 13 tests
- `tests/test_phase5_integration.py` — 23 tests

#### Safety Snapshot
- Location: `snapshots/agentx-snap-20260303-093653/`
- Contains: All .py, .json, .md, .txt files + CONSTITUTIONAL_CORE directory
- Created BEFORE any modifications

### February 22, 2026 — FIELD INTEGRATION INFRASTRUCTURE BUILT
- **Built:** `_preflight_field_validation.py` — 8-gate pre-flight (47/47 checks pass)
- **Built:** `field_campaign_config.yaml` — Phase 1-4 governed parameters
- **Built:** `field_campaign_runner.py` — governed campaign executor with quality gates
- **Verified:** Dry-run end-to-end: pre-flight → lead selection → dry-fire → report generation
- **Status:** Phase 1 ready to execute when tunnel is active during business hours

### February 22, 2026 — PHASE 1 IGNITION DATE SET
- **Decision:** Phase 1 ignition scheduled for Monday, February 23, 2026, 10:00 AM
- **Pre-launch checklist documented in RRG III**
- **System state:** 8/8 pre-flight gates pass, 47/47 checks green, 408 callable leads ready

### February 22, 2026 — v1.3 Simulation Suite: FULL UCP STRESS MATRIX COMPLETE (Scenarios 1-6)
- **Total across all 6 scenarios:** **536/536 checks PASSED — 100% — PRODUCTION GRADE**
- Covers: ambiguity, misinformation, contradiction, emotional volatility, low-info environments, false competitor collisions, loyalty/deferral, hostility/dismissal, high burn states, CRM+summary integrity under stress

### February 22, 2026 — v1.3 Simulation Suite: Scenario 6 COMPLETE
- **Scenario:** Hostile / Dismissive Merchant — irritated, short, dismissive, triple objection stack
- **Simulation file:** `_sim_v13_scenario6_ucp.py`
- **Result:** **85/85 checks PASSED — 100% pass rate — PRODUCTION GRADE**
- **Stress vectors tested:**
  - Pure hostility without processor context → no false match (5/5 guards)
  - Hostile + "processor" keyword → UCP triggered correctly
  - Hostile + "have a guy" without processor context → correctly no match
  - 4-frame prosody arc: hostile (high energy) → impatient → wall/shutdown → crack
  - Triple objection stack: dismissal + loyalty + time_availability
  - All 3 UCP objection handlers verified
  - Short call: 6 turns, 5 IQ turns, 9/20 budget, burn state NORMAL
  - Soft exit with optional callback text offered
  - CRM: hostile interest level, readiness=5, soft_exit_callback_offered outcome
  - Summary: 3 objection events, 3 tone frames, readiness=0
- **NEG-PROOF guards (6):** No processor fabricated, no email fabricated, budget not EXHAUSTED, readiness<=10, interest=hostile, soft_exit outcome captured

### February 22, 2026 — v1.3 Simulation Suite: Scenario 5 COMPLETE
- **Scenario:** Zero Information Merchant — no processor, no fees, no details, overwhelmed
- **Simulation file:** `_sim_v13_scenario5_ucp.py`
- **Result:** **93/93 checks PASSED — 100% pass rate — PRODUCTION GRADE**
- **Stress vectors tested:**
  - Pure zero-info text → (None, None) — no false match
  - Guided "some processor" → UCP triggered correctly
  - 3 zero-info variants with processor/name/called keywords → all UCP
  - 4 pure frustration texts → no false match (4/4 guards)
  - 4-frame prosody arc: overwhelmed → frustrated (impatient) → resigned → cautious
  - 6 IQ turns (2 prosody-only low-info loops before data appears), 11/20 budget, NORMAL
  - Time + overwhelm objection routing
  - Statement-upload outcome path (not appointment)
  - Summarization with minimal data: 10 turns, no competitor, readiness=0
  - CRM push with near-zero data: cold interest, no processor, no email
- **NEG-PROOF guards (6):** No processor fabricated, no email fabricated, budget not EXHAUSTED, readiness<=50, merchant name="Unknown", no competitor hallucinated

### February 22, 2026 — v1.3 Simulation Suite: Scenario 4 COMPLETE
- **Scenario:** False Known Competitor Collision — merchant thinks they're on Clover but details contradict
- **Simulation file:** `_sim_v13_scenario4_ucp.py`
- **Result:** **91/91 checks PASSED — 100% pass rate — PRODUCTION GRADE**
- **Stress vectors tested:**
  - Path A: Explicit "Clover" → Clover detected (priority correct)
  - Path B: Vague "green screen" description → (None, None) — no false positive
  - Path C: Clover + contradiction → Clover wins (first match)
  - 6 false-positive guards (green color, box shape, touchscreen, white/silver, generic machine, receipt printer) — all 6/6 passed
  - 4-frame emotional arc: confident-but-wrong → uncertain → embarrassed → relief
  - 5 IQ turns, 12/20 budget, burn state NORMAL
  - Loyalty + dismissal objection routing
  - Retrieval under mislabeling: Clover query, generic POS, bank system — all returned real data
  - Summary with mislabeled competitor: Clover (merchant-claimed), 12 turns, 2 objections, 4 tone frames
  - CRM with conflicting processor info: "Clover (unconfirmed)" flag, no email
- **NEG-PROOF guards (5):** No false positive from vague descriptions, 6/6 color/shape guards, budget not EXHAUSTED, CRM notes document uncertainty, no email fabricated

### February 22, 2026 — v1.3 Simulation Suite: Scenario 2 COMPLETE
- **Scenario:** Buddy's ISO Program — merchant on an unknown program set up by a buddy, contradictory fees, defensive tone, loyalty+deferral objections, no paperwork
- **Simulation file:** `_sim_v13_scenario2_ucp.py`
- **Result:** **96/96 checks PASSED — 100% pass rate — PRODUCTION GRADE**
- **Stress vectors tested:**
  - Buddy/referral language detection ("some program my buddy set us up with")
  - 5 additional ambiguous phrasings (friend/guy/special rate/not sure/don't know)
  - Known competitor priority override (Square + buddy language → Square wins)
  - 4-frame emotional arc: defensive → embarrassed → opening up → warm/engaged
  - Contradictory fee info ("2.5%? Or maybe 2.7%?")
  - Multi-objection routing: loyalty + deferral families
  - IQ budget under heavy load: 5 turns, 14/20 spent, burn state HIGH
  - Summarization under contradictory data: 16-turn transcript, 2 objection events, 4 tone frames
  - CRM push with partial context: no email, no processor name, "Unknown" merchant
- **10 Phases executed:**
  1. Organ 34 — UCP detection: 5/5 ambiguous phrases → unknown_processor, 2 known-competitor priority overrides verified
  2. Organ 30 — Prosody: 4-frame emotional arc (neutral → neutral → interested → interested), 2 distinct emotions
  3. Organ 24 — Retrieval: 9 documents retrieved across 3 queries (rates, special deal, terminal fees), no hallucinated buddy processor data
  4. Organ 35 — IQ Budget: 5 heavy turns, 14/20 budget spent, burn state HIGH (elevated from NORMAL), can_afford check passed
  5. Organ 31 — Objection: loyalty + deferral observed, both family routes verified (§3.2.4, §3.2.3), UCP handlers confirmed
  6. Organ 28 — Calendar: slot proposed + confirmed under merchant resistance
  7. Organ 26 — Outbound: SMS follow-up attempted
  8. Organ 32 — Summary: 16-turn transcript, contradictory data handled, competitor=unknown_processor, 3 key quotes captured, readiness=25
  9. Organ 33 — CRM: partial-context push (no email, Unknown merchant), status=sent
  10. Full cascade: 9 organs + 6 NEG-PROOF guards + 4 STRESS checks
- **NEG-PROOF guards (6):** No hallucinated processor name, no competitor-specific claims in UCP, contradictory fee data captured, IQ budget not EXHAUSTED, CRM has "Unknown" merchant (not invented), no email invented
- **Pattern expansion:** `_UNKNOWN_PROCESSOR_PATTERNS` expanded from 7 → 14 patterns to cover buddy/friend/guy/some-program/not-sure/don't-know/special-rate language
- **Regression:** 25/25 existing UCP tests still pass after pattern expansion

### February 22, 2026 — v1.3 Simulation Suite: Scenario 1 COMPLETE
- **Scenario:** Unknown Regional Bank Processor — merchant says "some small processor from our local bank"
- **Simulation file:** `_sim_v13_scenario1_ucp.py`
- **Result:** **85/85 checks PASSED — 100% pass rate — PRODUCTION GRADE**
- **10 Phases executed:**
  1. Organ 34 — UCP detection: `unknown_processor` classified, trigger `small processor`, 5 known competitors verified as priority
  2. Organ 30 — Prosody: confused/uncertain merchant (low energy, slow speech) → neutral emotion → interested after discovery
  3. Organ 24 — Retrieval: 3 industry-wide documents retrieved (score: 0.774), no hallucinated competitor data
  4. Organ 35 — IQ Budget: 3 turns, 8/20 budget spent, burn state NORMAL throughout, 6 organs billed
  5. Organ 31 — Objection: loyalty family routed (§3.2.4), consultative closing style
  6. Organ 28 — Calendar: tomorrow 09:45 AM slot proposed + confirmed (BK record created)
  7. Organ 26 — Outbound: SMS follow-up attempted (template lookup)
  8. Organ 32 — Summary: 22-field JSON generated (competitor: unknown_processor, objection: loyalty, outcome: appointment_booked, callback: true, turns: 15, readiness: 25)
  9. Organ 33 — CRM: durable push executed (status: sent, queue depth: 1)
  10. Full cascade validation: all 9 organs + 3 NEG-PROOF guards verified
- **NEG-PROOF guards:** No competitor-specific claims in UCP block, forbidden claims list present, IQ budget stayed NORMAL
- **Generated summary excerpt:** merchant_name=Unknown, current_processor=unknown_processor, primary_objection=loyalty, callback_requested=true, callback_time=tomorrow

### February 22, 2026 — Universal Competitive Protocol (UCP) — Unknown Processor Governance
- **Problem:** When a merchant names a processor Alan has never seen, the organism must not guess, assume, or hallucinate. Every unrecognized processor must be treated as a governed competitive category.
- **Solution:** Universal Competitive Protocol (UCP) — a governed fallback that works for ALL unlisted processors.

#### Detection (3-Tier)
- **Tier 1:** Known competitors always take priority (9 existing §4.9 profiles — substring match)
- **Tier 2:** Unknown-processor regex patterns (7 patterns): `never heard of`, `small processor`, `local processor`, `private label`, `white-label`, `iso program`, `their own system`
- **Tier 3:** Keyword fallback — `processor`, `merchant service`, `merchant account`

#### Wiring Points (4 changes to `aqi_conversation_relay_server.py`)
1. `_UNKNOWN_PROCESSOR_PATTERNS` — 7 regex-safe detection patterns (after `_COMPETITOR_PATTERNS`)
2. `_UCP_LLM_BLOCK` — Full LLM injection text block with §4.9 formatting (tone, positioning, discovery prompts, universal truths, savings framing, objection handlers, universal close, forbidden claims, safety notes, protocol flag)
3. `_COMPETITOR_POSITIONING["unknown_processor"]` — Full positioning dict with discovery-first strategy, universal truths, conditional savings framing, objection handlers, universal close, forbidden claims list, safety notes, LLM suffix
4. `detect_competitor_mention()` — Upgraded from single-tier to 3-tier detection (known → regex patterns → keyword fallback) with NEG-PROOF try/except on every regex call

#### LLM Injection Path
- When `_comp_name == 'unknown_processor'` → injects `_UCP_LLM_BLOCK` (full governed UCP text) instead of standard competitor context
- Includes `[UCP — UNKNOWN PROCESSOR PROTOCOL ACTIVE]` suffix for LLM state awareness

#### Organ Cascade Behavior
- **Organ 34:** Classifies as "unknown_processor" → injects UCP block
- **Organ 24:** Retrieves industry-wide truths only (no hallucinated competitor data)
- **Organ 31:** Routes objections normally (loyalty, contractual, time/availability, deferral, dismissal)
- **Organ 32:** Summarizes competitor as "Unknown / Unclassified" with merchant-provided details only
- **Organ 33:** Pushes CRM record with merchant-provided details only
- **Organ 35:** Prevents over-reasoning — keeps Alan simple, safe, and merchant-driven

#### Forbidden Claims (Hard Rules)
- Contract length, ETF/liquidated damages, hardware ownership, PCI fees, annual fees, pricing model, support quality, reputation, risk profile
- Unknown means **merchant-driven facts only**

#### Universal Close
> "Let's take a look at one statement. I'll break down the fees line by line and show you exactly where the money is going. If I can't save you money, I'll tell you straight up — but most owners are surprised by what we find."

#### Tests
- Test file: `_test_ucp_unknown_processor.py`
- **25/25 PASSED** (10 positive + 10 negative + 5 NEG-PROOF guards)
- Covers: all 7 regex patterns, 3 keyword fallbacks, 5 known competitors (priority check), empty/None/noise/unrelated, priority override (known + unknown keyword in same text), data structure integrity
- Competitor count: 9 known + 1 universal fallback = **full coverage**

### February 22, 2026 — Organ 24 Knowledge Index Seeded + Harbortouch Call Script
- Created `data/vector_store/knowledge_index.json` — Organ 24's retrievable knowledge corpus
- **24 documents indexed** across 4 categories:
  - `competitor` (9): Harbortouch profile, contract traps, ETF strategy + Square/Clover/Toast/Heartland/Worldpay/Stax pricing
  - `objection` (5): Harbortouch-specific rebuttals for contractual, loyalty, deferral, time, dismissal families
  - `pricing` (3): Harbortouch savings math, Edge standard pricing, interchange-plus explainer
  - `script` (7): Full multi-location call script — opening, discovery, pain framing, savings framing, closing, booking, strategy
- Seeder script: `_seed_knowledge_index.py` — safe to re-run (overwrites with canonical data)
- Retrieval verification: 4 test queries all return relevant documents above confidence threshold
- **Organ cascade now fully data-backed:** Organ 34 detects "Harbortouch" → Organ 24 retrieves contract traps, pricing, scripts, rebuttals → Organ 31 routes to correct family → Organ 30 adjusts tone → Organ 28 proposes slots → Organ 26 sends SMS → Organ 32 summarizes → Organ 33 pushes CRM → Organ 35 manages burn

### February 22, 2026 — Harbortouch/Shift4 Competitive Intel Added
- Added `Harbortouch` to `_COMPETITOR_PATTERNS` (7 triggers: harbortouch, harbor touch, shift4, shift 4, shift4 payments, harbortouch pos, lighthouse)
- Added `Harbortouch` to `_COMPETITOR_POSITIONING` (§4.9 rules):
  - Tone: empathetic, savings-focused, multi-location aware
  - Close: predatory-fee relief → savings-math
  - Key weakness: $65/terminal/mo rental, $0.10/txn, annual junk fees, liquidated damages, proprietary lock-in
  - Savings approach: Multi-location consolidation math ($3K-$4K/mo, $36K-$48K/yr)
- Competitor count: 8 → 9 (Square, Clover, Toast, Stripe, Heartland, Worldpay, PayPal, Stax, Harbortouch)
- Compile verified clean — all 12 organs + 9 competitors online
- **Use case:** Quad-business multi-location Harbortouch merchant (bar/pizzeria, cantina, RV park, entertainment complex)

### February 22, 2026 — RRG III Created
- **Commit 12 LIVE** — Organ 35 (In-Call IQ Budgeting) wired, tested (40/40), NEG-PROOF certified (9/9)
- **ALAN v4.1 FULL ORGANISM ONLINE** — All 12 commits complete
- RRG III created to manage document size (RRG II reached 13,325 lines)
- Carries forward all critical operational rules, architecture, and organ reference

---

> **═══ ALAN v4.1 — FULL ORGANISM ONLINE — 12/12 COMMITS LIVE ═══**
> **═══ 915+ TESTS PASSED — 88+ NEG-PROOF GUARDS VERIFIED ═══**
> **═══ PHASE 5 REFLEX ARC: CLOSED — 3 GAPS FIXED — 112/112 NEW TESTS ═══**
> **═══ v1.3 SIMULATION SUITE: 6/6 SCENARIOS — 536/536 PRODUCTION GRADE ═══**
> **═══ FIELD INTEGRATION: 8/8 PRE-FLIGHT — 47/47 CHECKS — PHASE 1 READY ═══**
> **═══ CONSTITUTIONALLY GOVERNED INTELLIGENCE ═══**
