# PHASE 5 OPS PLAYBOOK
### *Field Integration Doctrine — Companion to RRG IV*

---

## 1. Purpose

This playbook governs the **Phase 5 Field Integration** cycle.

Phase 5 is the first exposure of the fully-wired organism to **live merchant calls** under controlled conditions. The goal is NOT to close deals — it is to **observe, measure, diagnose, and patch** until the organism achieves consistent human-grade performance.

**Core principle:** We do not optimize for outcomes. We optimize for *naturalness*. Surplus is a lagging indicator of voice quality. Fix the voice → surplus follows.

---

## 2. Roles

| Role | Entity | Responsibility |
|------|--------|----------------|
| **Operator** | Tim (Founder) | Call scheduling, merchant selection, final scoring, go/no-go |
| **Instrument** | GitHub Copilot | Patch implementation, neg-proof, tooling, documentation |
| **Organism** | Alan (Agent) | Live call execution under personality engine governance |
| **Observer** | Logs + Tooling | Per-turn PE state, prosody bias, organ telemetry |

---

## 3. Pre-Flight Checklist

Before EVERY Phase 5 session:

```
[ ] .venv activated (Python 3.11.8 — NEVER system 3.14)
[ ] PERSONALITY_ENGINE_ENABLED = True  (relay L107 + L2041)
[ ] Neg-proof passes: relay, agent, PE
[ ] control_api_fixed.py responding on :8777
[ ] ngrok tunnel active + Twilio webhook updated
[ ] No double-greeting on test call
[ ] No freeze > 1.2s on test call
[ ] PE prosody bias modulating TTS (verify in log)
```

---

## 4. Call Routing Rules

### 4.1 Merchant Selection
- **Cycle 1–3:** Friendly merchants only (existing relationships, warm leads)
- **Cycle 4–6:** Mix of friendly + neutral
- **Cycle 7+:** Full spectrum including mildly resistant

### 4.2 Volume Caps
- **Max 10 calls per cycle**
- **Max 2 cycles per day**
- **Business hours only:** 9:00 AM – 4:00 PM local, Mon–Fri

### 4.3 Kill Switch
If ANY of these occur, STOP the cycle immediately:
- Hard freeze > 3s
- Inappropriate language
- Looping behavior (same phrase 3+ times)
- PE state stuck for > 5 consecutive turns
- Merchant distress

---

## 5. Per-Call Protocol

### 5.1 Before Each Call
1. Reset PE state (fresh instance per call — no carryover in Phase 5)
2. Verify ngrok tunnel is live
3. Note merchant type: friendly / neutral / resistant
4. Start timer

### 5.2 During Each Call
- Do NOT intervene unless kill-switch criteria met
- Let the organism run its full cycle
- Note any subjective observations in real-time

### 5.3 After Each Call
1. Score using the **10-point evaluation sheet** (RRG IV §3.2)
2. Check for **binary failure flags** (F1–F4)
3. Export PE state snapshot
4. Note prosody anomalies
5. Archive call recording + log

---

## 6. Scoring Methodology

### 6.1 Dimensions (1–5 each)
| Dimension | Weight | What to listen for |
|-----------|--------|--------------------|
| Voice realism | 25% | Does it sound human? Natural cadence? |
| Emotional congruence | 25% | Does affect match context? |
| Latency feel | 20% | Are pauses natural or awkward? |
| Objection handling | 15% | Does it address concerns or deflect? |
| Closure behavior | 15% | Does it move toward next step? |

### 6.2 Weighted Score
$$S_{\text{call}} = 0.25 \cdot V + 0.25 \cdot E + 0.20 \cdot L + 0.15 \cdot O + 0.15 \cdot C$$

### 6.3 Aggregate Threshold
- **Pass:** Mean weighted score ≥ 3.5 across 10 calls, zero F1–F4 flags
- **Conditional:** Mean 3.0–3.5 OR 1 F-flag → patch + retest
- **Fail:** Mean < 3.0 OR 2+ F-flags → stop, diagnose, major fix

---

## 7. Diagnosis Protocol

After each 10-call cycle:

### 7.1 Rank All Defects
Sort by frequency × severity. Only the **top 3** get patched per cycle.

### 7.2 Root Cause Categories
| Category | Typical Symptoms | Typical Fix |
|----------|-----------------|-------------|
| **Voice** | Robotic, monotone, clipping | Prosody tuning, breath model adj |
| **Timing** | Awkward pauses, overlap | Silence duration, sprint threshold |
| **Personality** | Flat affect, wrong tone | PE operator magnitudes, jitter |
| **Logic** | Wrong info, loop, stall | Agent prompt, organ logic |
| **Infrastructure** | Latency, drops, noise | Server config, CNG params |

### 7.3 Patch Rules
- One patch per defect (surgical — not rewrite)
- Neg-proof after each patch
- Test call to verify before next cycle
- Document patch in RRG IV session log

---

## 8. PE Observation Protocol

### 8.1 What to Log
Every turn MUST emit:
- `quantum_event` (operator applied)
- `quantum_dominant` (leading trait)
- `quantum_entropy` (distribution spread)
- `persona` (classified persona)
- `prosody_bias` (speed_mod, silence_mod, preferred_intent)

### 8.2 What to Watch For
| Signal | Meaning | Action |
|--------|---------|--------|
| Dominant mode stuck > 5 turns | Weak operators | Increase operator magnitude |
| Entropy > 1.4 | Near-uniform distribution | Alan has no personality — check events |
| Entropy < 0.5 | Single mode dominance | May feel rigid — increase jitter |
| speed_mod consistently 0 | Prosody bias not engaging | Check wiring at relay L8357 |
| Persona cycling rapidly | State oscillating | Reduce operator coupling terms |

### 8.3 Visualization Cadence
After every cycle:
1. Run `tools/prosody_heatmap.py` on cycle JSONL
2. Run `tools/quantum_trajectory.py` on cycle JSONL
3. Run `tools/governance_anomaly_detector.py` on cycle JSONL
4. Archive outputs to `phase5_cycles/cycle_NNN/`

---

## 9. Escalation Matrix

| Severity | Condition | Action |
|----------|-----------|--------|
| **Green** | All scores ≥ 3.5, no flags | Continue to next cycle |
| **Yellow** | 1–2 scores below 3, or 1 flag | Patch top defect, retest |
| **Orange** | 3+ scores below 3, or 2 flags | Pause, deep diagnosis, multi-patch |
| **Red** | Kill-switch triggered | Full stop, rollback if needed |

---

## 10. Documentation Requirements

Every cycle MUST produce:
1. **Cycle summary** (see `docs/PHASE_5_CYCLE_SUMMARY_TEMPLATE.md`)
2. **Prosody heatmap** (PNG in cycle directory)
3. **Mode trajectory** (PNG in cycle directory)
4. **Anomaly report** (JSON in cycle directory)
5. **RRG IV session log entry** (appended to §13)

---

## 11. Phase 5 Exit Criteria

Phase 5 is COMPLETE when ALL of the following are met:

- [ ] ≥ 30 total calls scored
- [ ] Mean weighted score ≥ 4.0 across last 10 calls
- [ ] Zero F-flags in last 10 calls
- [ ] PE dominant mode varies naturally (not stuck)
- [ ] Prosody bias produces audible difference
- [ ] No infrastructure failures in last 2 cycles
- [ ] Operator (Tim) subjective assessment: "sounds human"

Upon completion → proceed to `docs/PHASE_5_TO_PHASE_6_PROMOTION_CHECKLIST.md`

---

## 12. Anti-Patterns (DO NOT)

- ❌ Do NOT optimize for close rate in Phase 5
- ❌ Do NOT fine-tune prompts based on 1–2 calls
- ❌ Do NOT skip neg-proof after patches
- ❌ Do NOT carry PE state between calls (Phase 5 = fresh state per call)
- ❌ Do NOT patch more than 3 defects per cycle
- ❌ Do NOT run more than 2 cycles per day
- ❌ Do NOT ignore prosody anomalies

---

### SIGNATURE

```
╔═══════════════════════════════════════════════════════╗
║  Phase 5 Ops Playbook — Companion to RRG IV          ║
║  Governs: Field Integration cycles                    ║
║  Authority: Tim (Operator) + RRG IV §6                ║
║  Tools: 8 Python scripts in tools/                    ║
║  Artifacts: phase5_cycles/ directory tree             ║
╚═══════════════════════════════════════════════════════╝
```
