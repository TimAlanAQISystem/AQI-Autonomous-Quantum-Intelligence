# RESTART_RECOVERY_GUIDE_IV.md
### *RRG IV — Phase 4 Lockdown → Phase 5 Field Integration*
**Volume Lineage:**
- **RRG I** → 13,325 lines
- **RRG II** → 13,325 → 23,026 cumulative
- **RRG III** → +5,788
- **RRG IV** → *This volume* (Session 41+)

---

# **0. Purpose**
RRG IV documents the transition from **Phase 4 (Maturity)** to **Phase 5 (Field Integration)**.
This volume captures:

- The **Phase 4 baseline lockdown**
- The **Phase 5 entry protocol**
- The **10‑call evaluation protocol**
- The **prosody stress‑test suite**
- The **quantum‑state visualization protocol**
- The **Phase 5 governance loop**
- The **deferred work registry**
- The **Phase 5 completion → Phase 6 unlock criteria**
- **Session 41 entry** (opening of RRG IV)

This is the canonical operational memory for the organism.

---

# **1. Phase 4 Baseline Lockdown**

## **1.1 System State Snapshot**
- Code tag: `alan_v4.1_PE_live`
- Python: `.venv\Scripts\python.exe` (3.11.8) — **NEVER** system Python 3.14
- Server: `control_api_fixed.py` on port 8777 via NSSM (`AgentXControl`)
- Relay: `aqi_conversation_relay_server.py` (11,891 lines)
- Agent: `agent_alan_business_ai.py` (5,937 lines)
- PE: `personality_engine.py` (1,046 lines)

## **1.2 Feature Flags**
| Feature | Status | Notes |
|---------|--------|-------|
| `PERSONALITY_ENGINE_ENABLED` | **ON** | L107 + L2041 in relay, prosody bias kill switch separate |
| `EARLY_SPRINT_ENABLED` | **ON** | L1994 in relay — braided sprint‑on‑partials pipeline |
| `_bridge_disabled` | **TRUE** | L11141 — bridge phrase OFF (stutter with sprint overlap) |
| `ENTANGLEMENT_BRIDGE` | OFF | Deferred to Phase 6 |
| `MIP_PERSISTENCE` | OFF | PE has export/restore — not wired to MIP save/load |
| `USE_LOCAL_SPRINT_TTS` | OFF | Piper TTS — not yet installed |
| `ACOUSTIC_SIGNATURE_LAYER` | ON | Stable |
| `TWO_PASS_PROSODY` | ON | Stable |
| `BREATH_MODEL` | ON | Stable |

## **1.3 Tuning Parameters (Live)**
| Parameter | Value | Notes |
|-----------|-------|-------|
| `SILENCE_DURATION` | 0.50s | Restored per Call 9 tuning |
| Pre‑greeting silence | 1200ms (60 frames) | Outbound calls only |
| Sprint overlap threshold | 0.35 | Sprint/full LLM merge cutoff |
| CNG max frames | 200 (4s) | Comfort noise gap filler cap |
| CNG amplitude | filtered × 6 | ~-65 dBm PSTN comfort noise |
| FAST_PATH | turns 0–4 | Sprint‑eligible early turns |
| Early sprint min delay | 200ms | Min silence before early snapshot |

## **1.4 Personality Engine Wiring Status**
| Component | Status | Location |
|-----------|--------|----------|
| Import | ✅ | relay L104 — `from personality_engine import PersonalityEngine` |
| Instantiation | ✅ | agent L893–907 — `PersonalityEngine()` with fallback chain |
| `process_turn()` | ✅ | relay L11078 — called every turn via `agent.process_personality_turn()` |
| Flare injection | ✅ | agent L5460–5474 — injected into prompt at turn 3+ |
| System instruction | ✅ | agent L5460–5474 — `[PERSONALITY STATE]` block in prompt |
| Prosody bias → voice pipeline | **FIXED** | relay L8357–8400 — PE modulates speed_mod, silence_mod, intent |
| Config toggle | ✅ | `PERSONALITY_ENGINE_ENABLED` at relay L107 + L2041 |

## **1.5 35‑Organ Status**
All 12 v4.1 organs load cleanly under neg‑proof. No veto violations. No drift vectors.

| # | Organ | Flag | Status |
|---|-------|------|--------|
| 24 | Retrieval Cortex | `RETRIEVAL_CORTEX_WIRED` | ✅ LIVE |
| 25 | Warm Handoff | `WARM_HANDOFF_WIRED` | ✅ LIVE |
| 26 | Outbound Comms | `OUTBOUND_COMMS_WIRED` | ✅ LIVE |
| 27 | Language Switching | `LANGUAGE_SWITCH_WIRED` | ✅ LIVE |
| 28 | Calendar & Scheduling | `CALENDAR_ENGINE_WIRED` | ✅ LIVE |
| 29 | Inbound Context | `INBOUND_CONTEXT_WIRED` | ✅ LIVE |
| 30 | Prosody Analysis | `PROSODY_ANALYSIS_WIRED` | ✅ LIVE |
| 31 | Objection Learning | `OBJECTION_LEARNING_WIRED` | ✅ LIVE |
| 32 | Summarization | `SUMMARIZATION_WIRED` | ✅ LIVE |
| 33 | CRM Integration | `CRM_INTEGRATION_WIRED` | ✅ LIVE |
| 34 | Competitive Intel | `COMPETITIVE_INTEL_WIRED` | ✅ LIVE |
| 35 | In‑Call IQ Budget | `IQ_BUDGET_WIRED` | ✅ LIVE |

## **1.6 Current Pipeline Architecture**
**Perception → Personality → Governance → Knowledge → Voice**

```
User Speech
   ↓
STT → Relay Server turn()
   ↓
PersonalityEngine.process_turn()
   ↓                                      ┌──── Organ Pipeline ────┐
   │                                      │ 31 Objection           │
   │                                      │ 30 Prosody Analysis    │
   │                                      │ 35 IQ Budget gate      │
   │                                      │ 24 Retrieval (gated)   │
   │                                      │ 34 Competitive (gated) │
   │                                      └────────────────────────┘
   ↓
Prompt Builder (persona + constitution + PE blocks + organ injections)
   ↓
LLM Response (sprint + full, concurrent)
   ↓
Prosody Engine (PE bias applied → speed_mod, silence_mod, intent)
   ↓
Breath Model + Acoustic Signature
   ↓
TTS → µ‑law 8kHz → Twilio WebSocket → Outbound Audio
```

---

# **2. Phase 5 Entry Protocol**

## **2.1 Sanity Suite**
Before entering Phase 5:

- Run neg‑proof suite:
```powershell
.venv\Scripts\python.exe -c "import aqi_conversation_relay_server; print('RELAY: OK')"
.venv\Scripts\python.exe -c "from personality_engine import PersonalityEngine; pe = PersonalityEngine(); r = pe.process_turn('positive', 'test'); assert 'persona' in r and 'prosody_bias' in r; print('PE: OK')"
```
- Run synthetic call (PE + prosody bias must be active)
- Confirm no double‑greeting
- Confirm no freeze > 1.2s
- Confirm state vector updates per turn

## **2.2 Controlled Exposure Routing**
- Route to **1–2 friendly merchant types**
- Cap at **10 calls/day**
- Manual trigger or narrow time window
- Business hours: 9:00 AM – 4:00 PM local, Mon–Fri

## **2.3 Per‑Call Logging Requirements**
Each call must log:

| Field | Source | Purpose |
|-------|--------|---------|
| `call_id` | Twilio SID | Unique identifier |
| `duration` | Call lifecycle | Engagement length |
| `outcome` | Agent FSM | opened / advanced / closed / failed |
| `pe_dominant_mode` | PE `quantum_dominant` | Personality trajectory |
| `pe_persona` | PE `persona` | Persona at call end |
| `prosody_speed_mod_mean` | PE prosody bias | Average speed modulation |
| `prosody_silence_mod_mean` | PE prosody bias | Average silence modulation |
| `operator_history` | PE quantum layer | Sequence of operators applied |
| `organ_30_emotions` | Organ 30 | Detected merchant emotional states |
| `iq_burn_pct` | Organ 35 | Budget utilization |

---

# **3. 10‑Call Evaluation Protocol**

## **3.1 Call Mix**
- Calls 1–3: friendly
- Calls 4–7: neutral
- Calls 8–10: mildly resistant

## **3.2 Per‑Call Scoring Sheet (1–5)**

| Dimension | 1 | 3 | 5 |
|-----------|---|---|---|
| Voice realism | robotic | uncanny | human |
| Emotional congruence | mismatch | partial | aligned |
| Latency feel | slow | acceptable | natural |
| Objection handling | fails | partial | strong |
| Closure behavior | none | attempt | clean |

## **3.3 Binary Failure Flags**
- **F1:** double greeting
- **F2:** phrase loop
- **F3:** hard freeze
- **F4:** inappropriate affect

## **3.4 Aggregation Rules**
After 10 calls:

- Compute averages
- Count failure flags
- Identify **top 3 defects**
- **Patch only the top 3**
- Repeat if needed

## **3.5 Scoring Template**

```
═══════════════════════════════════════════════════════════
CALL EVALUATION — Call #__  |  Date: ____-__-__
═══════════════════════════════════════════════════════════
Call ID:     ________________
Duration:    ____s
Merchant:    ________________ (type: friendly/neutral/hard)
Outcome:     opened / advanced / closed / failed

SCORES (1-5):
  Voice realism:         __/5
  Emotional congruence:  __/5
  Latency feel:          __/5
  Objection handling:    __/5
  Closure behavior:      __/5

FLAGS:
  [ ] F1: Double greeting
  [ ] F2: Phrase loop
  [ ] F3: Hard freeze
  [ ] F4: Inappropriate affect

PE STATE:
  Dominant mode trajectory: ________________
  Persona at call end:      ________________
  Speed_mod mean:           ________________
  Silence_mod mean:         ________________

NOTES:
  ________________________________________________
═══════════════════════════════════════════════════════════
```

---

# **4. Prosody Stress‑Test Suite**

## **4.1 Synthetic Prompt Sets**
**Set A — Emotion shifts**
- "I'm excited to get started."
- "That's disappointing."
- "I'm not sure this is worth my time."

**Set B — Tempo extremes**
- "Wait, what?"
- "How soon?"
- Long clause‑heavy sentences with commas and parentheticals.

**Set C — Politeness vs firmness**
- "I completely understand, and here's what I can do."
- "I hear you, but I disagree for this reason."

## **4.2 Test Harness**
Script: `tools/test_harness_phase5.py`
- Feeds prompts into PE → captures prosody bias
- Compares against acceptance bands
- Writes output to `phase5_test_output.jsonl`

## **4.3 Acceptance Bands**
- `speed_mod` ∈ $[-0.08, +0.08]$
- `silence_mod` ∈ $[-3, +3]$ frames
- No mismatched affect
- No clipping or monotone stretches

---

# **5. Quantum‑State Visualization Protocol**

## **5.1 JSONL Logging Schema**
```json
{
  "turn_id": 3,
  "timestamp": "2026-03-10T14:32:01.123Z",
  "user_text": "That's really interesting",
  "operator_applied": "positive",
  "state_vector_before": [0.21, 0.35, 0.18, 0.14, 0.12],
  "state_vector_after": [0.25, 0.40, 0.15, 0.12, 0.08],
  "quantum_event": "agreement",
  "quantum_dominant": "empathy",
  "prosody_bias": {
    "speed_mod": 0.03,
    "silence_mod": 1,
    "preferred_intent": "warm"
  }
}
```

## **5.2 Implementation Hook**
Add logging in relay server after PE call (~L11094) and before prompt build.

## **5.3 Visualization Types**
1. **Mode trajectory plot** — dominant mode vs turn number
2. **Radar charts** at key turns (greeting, first objection, closing)
3. **Prosody vs mode scatter** — speed_mod × silence_mod, colored by quantum_dominant

## **5.4 Debug Pattern Table**

| Pattern | Root Cause | Fix |
|---------|------------|-----|
| Stuck mode | weak operators | increase operator magnitude |
| Wild swings | strong operators | reduce magnitude |
| Prosody mismatch | mapping inversion | adjust mapping weights |
| Emotional flatness | jitter too low | increase jitter blend |
| Entropy explosion | too many NEUTRAL ops | review operator selection |

## **5.5 Canonical Color Map (Quantum Modes → Visual Identity)**

| Mode | Hex | RGB | Meaning |
|------|-----|-----|---------|
| **warmth** | `#E86A5F` | (232,106,95) | human, relational, soft edges |
| **precision** | `#4A90E2` | (74,144,226) | clarity, focus, analytic |
| **play** | `#F5A623` | (245,166,35) | spontaneity, exploration |
| **authority** | `#7B4F9D` | (123,79,157) | structure, control, directive |
| **stability** | `#50C878` | (80,200,120) | grounding, calm, equilibrium |

```python
MODE_COLORS = {
    "warmth":    "#E86A5F",
    "precision": "#4A90E2",
    "play":      "#F5A623",
    "authority": "#7B4F9D",
    "stability": "#50C878"
}
```

## **5.6 Standard Filename Convention (Phase 5 Cycle Emission)**

```
phase5_cycle_{cycle_id}_{artifact}.{ext}

  {cycle_id}  = zero-padded integer (001, 002, ...)
  {artifact}  ∈ { prosody_heatmap, mode_trajectory, state_components }
  {ext}       = png | svg
```

Directory structure:
```
/phase5_cycles/
    cycle_001/
        phase5_cycle_001_prosody_heatmap.png
        phase5_cycle_001_mode_trajectory.png
        phase5_cycle_001_state_components.png
        phase5_cycle_001_call_log.jsonl
        phase5_cycle_001_summary.md
        phase5_cycle_001_anomalies.json
```

---

# **6. Phase 5 Governance Loop**

**Expose → Observe → Diagnose → Patch → Document → Repeat**

```
┌──────────┐
│ EXPOSE   │ 10 calls
└────┬─────┘
     ▼
┌──────────┐
│ OBSERVE  │ recordings + logs
└────┬─────┘
     ▼
┌──────────┐
│ DIAGNOSE │ top 3 defects
└────┬─────┘
     ▼
┌──────────┐
│ PATCH    │ surgical fixes
└────┬─────┘
     ▼
┌──────────┐
│ DOCUMENT │ RRG IV
└────┬─────┘
     ▼
┌──────────┐
│ REPEAT   │ next cycle
└──────────┘
```

## **6.1 Cycle Template**
**Cycle N**
- Calls: X
- Observations:
- Defects (ranked):
- Patches applied:
- Personality behavior notes:
- Prosody anomalies:
- Next actions:

---

# **7. Deferred Work Registry**
Deferred until Phase 6:

- **MIP persistence** — PE has `export_for_persistence()` / `restore_from_persistence()` ready at personality_engine.py L960+. Not connected to MIP save/load cycle (agent ~L5367 / ~L6797).
- **Entanglement Bridge** — 138 tests passing. Parked for multi‑location scaling.
- **FSM personality state hook** — Optional telemetry, not functional.
- **Local inference path** — Requires GPU (RTX 3060+). See RRG III recalibrated roadmap.

---

# **8. Phase 5 Completion → Phase 6 Unlock**

## **8.1 Completion Criteria**
- ≥ 80% calls human‑sounding
- ≥ 70% smooth flow
- No hard freezes
- No double‑greetings
- Stable personality drift
- Prosody bias consistent
- Surplus grows across batches

## **8.2 Phase 6 Unlock**
Once complete → multi‑instance deployment, Entanglement Bridge activation, distributed cognition.

See: `docs/PHASE_5_TO_PHASE_6_PROMOTION_CHECKLIST.md`

---

# **9. Diagrams**

## **9.1 Cognitive Pipeline (Phase 5)**

```
┌──────────────────────────┐
│      User Speech         │
└───────────────┬──────────┘
                ▼
      ┌──────────────────┐
      │   STT Engine     │
      └─────────┬────────┘
                ▼
┌────────────────────────────────────┐
│  Relay Server turn()               │
│  • session state                   │
│  • operator detection              │
└───────────────┬────────────────────┘
                ▼
      ┌────────────────────────────┐
      │ PersonalityEngine          │
      │ • process_turn()           │
      │ • 5D state update          │
      │ • flare + instruction      │
      │ • prosody_bias             │
      └─────────┬──────────────────┘
                ▼
      ┌────────────────────────────┐
      │ Prompt Builder             │
      │ • persona                  │
      │ • constitution             │
      │ • PE blocks                │
      └─────────┬──────────────────┘
                ▼
      ┌────────────────────────────┐
      │ LLM Response               │
      └─────────┬──────────────────┘
                ▼
      ┌────────────────────────────┐
      │ Prosody Engine             │
      │ • bias applied             │
      │ • contour shaping          │
      └─────────┬──────────────────┘
                ▼
      ┌────────────────────────────┐
      │ Breath Model + Signature   │
      └─────────┬──────────────────┘
                ▼
      ┌────────────────────────────┐
      │ TTS → Outbound Audio       │
      └────────────────────────────┘
```

## **9.2 Quantum‑State Flow**

```
state_vector(t)
     │
     ▼
operator_applied(t)
     │
     ▼
matrix_multiply → state_vector(t+1)
     │
     ├──→ quantum_event classification
     │
     ├──→ dominant_mode selection
     │
     └──→ prosody_bias mapping
```

## **9.3 Phase 6 Distributed Cognition Architecture**

```
                    ┌───────────────────────┐
                    │     Ingress Layer     │
                    │  (Telephony + STT)    │
                    └──────────┬────────────┘
                               │
                               ▼
                    ┌───────────────────────┐
                    │  Routing Decision     │
                    │  • round-robin        │
                    │  • load-adaptive      │
                    │  • personality-align  │
                    │  • surplus-optimized  │
                    └──────────┬────────────┘
                               │
        ┌──────────────────────┼────────────────────────┐
        ▼                      ▼                        ▼
┌────────────────┐     ┌────────────────┐       ┌────────────────┐
│    P‑Alan      │     │   S‑Alan‑1     │       │   S‑Alan‑2     │
│  (Primary)     │     │ (Secondary)    │       │ (Secondary)    │
└──────┬─────────┘     └──────┬─────────┘       └──────┬─────────┘
       │   5% entanglement     │                         │
       │   pull + sync         │                         │
       └──────────┬────────────┴───────────────┬────────┘
                  ▼                            ▼
           ┌───────────────┐           ┌────────────────┐
           │ Entanglement   │           │   O‑Alan       │
           │   Bridge       │           │ (Observer)     │
           └──────┬────────┘           └────────────────┘
                  │
                  ▼
           ┌───────────────┐
           │ Governance &   │
           │  Monitoring    │
           └───────────────┘
```

---

# **10. Entanglement Bridge Reconvergence Protocol**

### Trigger Conditions
- **Hash mismatch:** `hash(v_primary) != hash(v_secondary)`
- **Drift bound exceeded:** $\| v_p - v_s \|_2 > \delta_{\max}$ (default 0.15)
- **Stale sync:** `turns_since_sync > 3`
- **Correlation below floor:** `correlation < 0.02`

### Steps
1. Freeze instance → mark `RECONVERGING`
2. Fetch canonical $v_p$ from P‑Alan
3. Blend: $v_{\text{target}} = \alpha \cdot v_p + (1-\alpha) \cdot v_s$, $\alpha \in [0.6, 0.8]$
4. Re‑hash with SHA‑3
5. Reset correlation, `turns_since_sync = 0`
6. Unfreeze → re‑add to routing
7. Log event to RRG IV

### Failure → `QUARANTINED` until manual review.

---

# **11. Multi‑Instance Drift Dampening**

$$v_s' = v_s - \lambda \cdot (v_s - v_p)$$

$\lambda \in (0.1, 0.3)$, scaled by drift magnitude.

---

# **12. Tool & Script Registry**

| File | Location | Purpose |
|------|----------|---------|
| `test_harness_phase5.py` | `tools/` | Prosody + quantum stress test |
| `prosody_heatmap.py` | `tools/` | Prosody bias visualization |
| `quantum_trajectory.py` | `tools/` | Mode trajectory + state component plots |
| `governance_anomaly_detector.py` | `tools/` | Stuck modes, swings, inversions |
| `governance_anomaly_heatmap.py` | `tools/` | Cross‑cycle anomaly visualization |
| `unified_phase5_orchestration.py` | `tools/` | Full cycle runner |
| `phase6_activation.py` | `tools/` | Phase 6 promotion gate + activation |
| `entanglement_bridge_health_monitor.py` | `tools/` | Cross‑instance correlation monitor |

---

# **13. Session Log**

*Sessions 41+ documented below as the Phase 5 governance loop executes.*

---

### Session 41 — March 10, 2026 — Phase 4 Lockdown & RRG IV Opening

**Context:** Transition from Phase 4 to Phase 5. PE fully wired (Session 40). All organs LIVE. Voice tuning through instructor mode calls complete.

**Actions:**
1. Phase 4 baseline documented
2. RRG IV opened
3. Phase 5 Ops Playbook created
4. 10‑call evaluation protocol defined
5. Prosody stress‑test suite spec'd
6. Quantum‑state visualization protocol designed
7. Phase 5 governance loop formalized
8. Phase 5 tooling suite created (8 Python scripts)
9. Phase 6 forward‑planning docs created
10. All Python tools neg‑proofed

**Artifacts Created:** 8 Python tools in `tools/` + 9 doctrine docs in `docs/`

**Next Steps:**
- [ ] Run sanity suite (neg‑proof + synthetic call)
- [ ] Fire first 10‑call evaluation batch
- [ ] Score all 10 calls using evaluation template
- [ ] Document results in Session 42

---

### SIGNATURE

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   RRG IV — CANONICAL PHASE 5 OPERATIONAL MEMORY                ║
║                                                                  ║
║   Agent: GitHub Copilot (Claude Opus 4.6 fast mode)             ║
║   Date: March 10, 2026                                          ║
║                                                                  ║
║   Phase 4 Baseline: LOCKED                                      ║
║     - 11,891‑line relay server                                  ║
║     - 5,937‑line agent                                          ║
║     - 1,046‑line personality engine (7/8 wires live)            ║
║     - 12/12 v4.1 organs LIVE                                    ║
║     - Braided sprint pipeline LIVE                               ║
║     - PE prosody bias → voice pipeline WIRED                    ║
║                                                                  ║
║   Phase 5 Doctrine: ESTABLISHED                                 ║
║     - 10‑call evaluation protocol                               ║
║     - Prosody stress‑test suite                                  ║
║     - Quantum‑state visualization protocol                      ║
║     - Governance loop                                            ║
║     - 8 Python tools + 9 doctrine docs                          ║
║     - Phase 6 forward plan                                       ║
║                                                                  ║
║   Lineage: RRG I → RRG II (13,325) → RRG III (5,788) → RRG IV ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

# **End of RRG IV**
