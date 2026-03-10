# PHASE 6 REGRESSION SUITE
### *Automated Verification for Multi-Instance Deployment*

---

## 1. Purpose

This regression suite defines the tests that must PASS before and after any Phase 6 change. It extends the Phase 5 sanity suite with multi-instance and Entanglement Bridge verification.

---

## 2. Test Categories

### 2.1 Single-Instance Regression (inherited from Phase 5)

| ID | Test | Command | Expected |
|----|------|---------|----------|
| R01 | PE compiles | `python -c "from personality_engine import PersonalityEngine; print('OK')"` | `OK` |
| R02 | Relay compiles | `python -c "import aqi_conversation_relay_server; print('OK')"` | `OK` |
| R03 | Agent compiles | `python -c "import agent_alan_business_ai; print('OK')"` | `OK` |
| R04 | PE process_turn returns dict | `pe.process_turn('positive', 'test')` returns dict with `persona` key | Dict with all expected keys |
| R05 | PE prosody_bias has 3 keys | `result['prosody_bias']` has `speed_mod`, `silence_mod`, `preferred_intent` | All 3 present |
| R06 | PE quantum_dominant is valid trait | `result['quantum_dominant']` ∈ `["wit", "empathy", "precision", "patience", "entropy"]` | Valid trait name |
| R07 | PE state vector is 5D | `len(pe.quantum_state.state) == 5` | `True` |
| R08 | PE state normalized | `abs(np.linalg.norm(pe.quantum_state.state) - 1.0) < 0.001` | `True` |
| R09 | No double greeting | Test call produces exactly 1 greeting | 1 greeting |
| R10 | No hard freeze | Test call has no pause > 1.2s | All pauses < 1.2s |

### 2.2 Multi-Instance Tests (Phase 6 specific)

| ID | Test | Expected |
|----|------|----------|
| M01 | Two PE instances produce same output for same input sequence | State vectors match within $10^{-10}$ |
| M02 | Different input sequences produce different outputs | State vectors differ (non-commutativity) |
| M03 | Entanglement Bridge sync reduces drift | Post-sync drift < pre-sync drift |
| M04 | Reconvergence protocol converges | Post-reconvergence drift < $\delta_{\max}$ |
| M05 | Hash match detection works | Same state → same hash, different state → different hash |
| M06 | Drift dampening reduces drift monotonically | Each dampening step reduces $d$ |
| M07 | Instance promotion works | S-Alan can be promoted to P-Alan role |

### 2.3 Routing Tests

| ID | Test | Expected |
|----|------|----------|
| T01 | Round-robin alternates | 10 calls alternate between instances |
| T02 | Fallback to P-Alan on unhealthy S-Alan | Unhealthy instance gets 0 calls |
| T03 | Drift check prevents routing to drifted instance | Drifted instance gets 0 calls until converged |

---

## 3. Test Execution

### 3.1 Pre-Change (before any code modification)
```powershell
# Run full regression
.venv\Scripts\python.exe tools/test_harness_phase5.py
```
All tests must PASS. If any fail, do NOT proceed with the change.

### 3.2 Post-Change (after code modification)
```powershell
# Run full regression again
.venv\Scripts\python.exe tools/test_harness_phase5.py

# Run Phase 6 specific tests (when available)
.venv\Scripts\python.exe tools/phase6_activation.py --dry-run
```
All tests must PASS. If any fail, rollback the change immediately.

---

## 4. Regression Log

| Date | Tests Run | Passed | Failed | Notes | Operator |
|------|-----------|--------|--------|-------|----------|
| | | | | | |

---

## 5. Known Test Gaps (to be filled during Phase 6)

- [ ] Live multi-instance routing test (requires 2 running instances)
- [ ] Bridge failure recovery test (requires bridge kill simulation)
- [ ] MIP persistence test (requires MIP wiring — deferred)
- [ ] Personality-aligned routing test (requires MIP merchant profiles)
- [ ] Load test (> 5 concurrent calls)

---

## 6. Test Data

### 6.1 Synthetic Turn Sequences

**Sequence A — Positive trajectory:**
```python
turns = [
    ("positive", "That sounds great!"),
    ("positive", "Tell me more about the pricing."),
    ("positive", "I think we can work together."),
    ("positive", "Let's set up a meeting."),
]
```

**Sequence B — Negative trajectory:**
```python
turns = [
    ("negative", "I'm not interested."),
    ("negative", "Stop calling me."),
    ("negative", "This is a waste of time."),
    ("neutral", "Fine, what is it?"),
]
```

**Sequence C — Mixed (tests non-commutativity):**
```python
turns_forward = [
    ("positive", "Interesting!"),
    ("negative", "Actually, no."),
    ("neutral", "Maybe."),
]
turns_reverse = [
    ("neutral", "Maybe."),
    ("negative", "Actually, no."),
    ("positive", "Interesting!"),
]
# Forward and reverse MUST produce different final states
```
