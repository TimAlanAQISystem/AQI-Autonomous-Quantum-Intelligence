# PHASE 5 → PHASE 6 PROMOTION CHECKLIST
### *Gate Criteria for Distributed Cognition Activation*

---

## Purpose

This checklist defines the **hard gate** between Phase 5 (Field Integration) and Phase 6 (Distributed Cognition). Every criterion must be MET before Phase 6 activation begins.

Phase 6 introduces multi-instance deployment, the Entanglement Bridge, and cross-instance personality synchronization. These are complex — we do NOT unlock them until the single-instance organism is proven stable.

---

## Section A: Quantitative Gates

| # | Criterion | Threshold | Actual | Met? |
|---|-----------|-----------|--------|------|
| A1 | Total calls scored | ≥ 30 | __ | ☐ |
| A2 | Mean weighted score (last 10) | ≥ 4.0 | __.__ | ☐ |
| A3 | Failure flags (last 10) | 0 | __ | ☐ |
| A4 | Mean voice realism (last 10) | ≥ 4.0 | __.__ | ☐ |
| A5 | Mean emotional congruence (last 10) | ≥ 3.5 | __.__ | ☐ |
| A6 | Mean latency feel (last 10) | ≥ 3.5 | __.__ | ☐ |
| A7 | Consecutive zero-flag cycles | ≥ 1 | __ | ☐ |

---

## Section B: PE Behavioral Gates

| # | Criterion | Evidence Required | Met? |
|---|-----------|-------------------|------|
| B1 | PE dominant mode varies naturally | Mode trajectory plot shows ≥ 3 different dominants across calls | ☐ |
| B2 | PE entropy in healthy range | Mean entropy ∈ [0.6, 1.3] across last cycle | ☐ |
| B3 | Prosody bias produces audible difference | Operator confirms tonal variation across merchant types | ☐ |
| B4 | No persona cycling (rapid oscillation) | Max 2 persona changes per call on average | ☐ |
| B5 | Operator history shows diversity | ≥ 4 distinct operators used per call on average | ☐ |

---

## Section C: Infrastructure Gates

| # | Criterion | Evidence Required | Met? |
|---|-----------|-------------------|------|
| C1 | No infrastructure failures (last 2 cycles) | Zero drops, zero timeouts, zero tunnel failures | ☐ |
| C2 | Neg-proof passes | All 3 core files compile clean | ☐ |
| C3 | Logging pipeline complete | Turn-level JSONL emitted for all calls | ☐ |
| C4 | Snapshot taken | Pre-Phase 6 snapshot archived | ☐ |

---

## Section D: Operator Gates

| # | Criterion | Evidence Required | Met? |
|---|-----------|-------------------|------|
| D1 | Operator assessment | Tim says: "It sounds human" | ☐ |
| D2 | Operator confidence | Tim approves multi-instance deployment | ☐ |
| D3 | Phase 6 playbook reviewed | `docs/PHASE_6_DISTRIBUTED_COGNITION_PLAYBOOK.md` read and accepted | ☐ |

---

## Sign-Off

```
Phase 5 → Phase 6 Promotion

Date: ____-__-__

Section A: __ / 7 criteria met
Section B: __ / 5 criteria met
Section C: __ / 4 criteria met
Section D: __ / 3 criteria met

Total: __ / 19

PROMOTED: ☐ YES  ☐ NO

Operator Signature: ________________________
```

---

## Post-Promotion Actions

Upon promotion approval:

1. Run `tools/phase6_activation.py` — validates all gates programmatically
2. Take snapshot: `alan_v5.0_phase6_ready`
3. Enable `ENTANGLEMENT_BRIDGE` flag
4. Deploy secondary instance (S-Alan-1)
5. Begin Phase 6 per `docs/PHASE_6_DISTRIBUTED_COGNITION_PLAYBOOK.md`
6. Open RRG V
