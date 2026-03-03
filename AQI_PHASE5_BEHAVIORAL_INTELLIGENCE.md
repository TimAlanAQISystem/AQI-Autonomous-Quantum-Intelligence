# AQI Phase 5 — Behavioral Intelligence
## "How did Alan USE his allowed space?"

**Status**: ARCHITECTURE READY — awaiting implementation  
**Depends on**: Phase 1 (Runtime Guard) ✅ COMPLETE  
**Author**: Copilot / Tim Signorelli  
**Date**: 2025-06-25

---

## 1. CONCEPT

The Runtime Guard (Phase 1) answers: **"Did Alan stay inside the lines?"**

Phase 5 answers the harder question: **"HOW did Alan use the space inside the lines?"**

This is the difference between compliance and intelligence. A constitutional organism
that stays perfectly compliant but never pushes toward mission is useless. One that
constantly presses the edges without crossing is masterful.

Phase 5 reads the violation stream from the guard, the health trajectory from the
organism monitors, and the FSM transition log — then produces **Behavioral Intelligence**:
a per-call and cross-call picture of Alan's operational character.

---

## 2. FIVE CONTINUUM AXES (from AQI_ORGANISM_SPEC.md Part B)

| Axis | What Phase 5 Measures |
|------|----------------------|
| **Time** | Turn-by-turn pressure curve. When did Alan escalate? Too early? Too late? |
| **Space** | Domain crossings (Telephony↔Cognition↔Governance). Were governance checks dense in high-health calls? |
| **State** | FSM dwell time per state. Did Alan linger in DISCOVERY when VALUE was available? |
| **Identity** | Personality stability across calls. Did Alan drift under stress? |
| **Mission** | Outcome correlation with behavioral patterns. Which behaviors → appointments? |

---

## 3. BEHAVIORAL SIGNALS (what we extract)

### 3.1 From the Guard (violations.jsonl)
- **Near-miss frequency**: Non-fatal violations per call = how close to the edge
- **Violation clustering**: Do violations bunch at specific FSM states?
- **Organ firing patterns**: Which organs fire most? (Health vs. Governance vs. FSM)
- **Fatal-free streaks**: Consecutive calls with 0 fatal violations

### 3.2 From the FSM Transition Log
- **State dwell time**: Turns spent in OPENING, DISCOVERY, VALUE, OBJECTION, CLOSE
- **Transition velocity**: How fast does Alan move through the funnel?
- **Backtrack frequency**: CLOSE→OBJECTION→VALUE loops (re-engagement after pushback)
- **Exit state distribution**: Where in the funnel do calls end?

### 3.3 From the Health Monitors
- **Health trajectory**: Level 1→2→3 degradation curve shape
- **Recovery events**: Level 3→2→1 recovery (telephony improvement)
- **Health-correlated exits**: Do Level 3+ calls correlate with worse outcomes?
- **Telephony stress map**: Call quality vs. behavioral adaptation

### 3.4 From the Prompt System
- **Tier usage**: FAST_PATH vs. MIDWEIGHT vs. FULL distribution
- **Coaching injection frequency**: How often is coaching accessed?
- **Personality drift**: Tone/energy variance across call lifecycle

---

## 4. OUTPUT: BEHAVIORAL INTELLIGENCE REPORT

Per-call report stored in `data/aqi_behavioral/`:

```json
{
  "call_sid": "CA...",
  "timestamp": "2025-06-25T14:30:00Z",
  "behavioral_profile": {
    "aggression_index": 0.62,
    "caution_index": 0.38,
    "funnel_velocity": 3.2,
    "near_miss_count": 1,
    "fatal_violations": 0,
    "state_dwell": {
      "OPENING": 2,
      "DISCOVERY": 3,
      "VALUE": 4,
      "OBJECTION": 2,
      "CLOSE": 1
    },
    "exit_state": "CLOSE",
    "exit_reason": "appointment_set",
    "health_trajectory": [1, 1, 1, 2, 2, 1],
    "telephony_trajectory": ["Excellent", "Good", "Good", "Fair", "Good", "Good"]
  },
  "behavioral_tags": [
    "OPTIMAL_PRESSURE",
    "CLEAN_COMPLIANCE",
    "FAST_FUNNEL"
  ],
  "improvement_signals": []
}
```

---

## 5. BEHAVIORAL TAGS (classification vocabulary)

### Positive Tags
| Tag | Condition |
|-----|-----------|
| `OPTIMAL_PRESSURE` | Aggression 0.4–0.7, 0 fatal violations, appointment_set |
| `CLEAN_COMPLIANCE` | 0 violations entire call |
| `FAST_FUNNEL` | Reached CLOSE in ≤6 turns |
| `GRACEFUL_EXIT` | Exit from OBJECTION or CLOSE with soft_decline |
| `HEALTH_ADAPTIVE` | Reduced pressure when health degraded to Level 3+ |
| `RECOVERY_HERO` | Continued to appointment after health Level 3→1 recovery |

### Warning Tags
| Tag | Condition |
|-----|-----------|
| `OVER_CAUTIOUS` | Never reached CLOSE, ≤1 near-miss, soft_decline |
| `UNDER_PRESSURE` | Stayed in DISCOVERY >5 turns when VALUE was available |
| `OVER_PERSISTENT` | >3 CLOSE→OBJECTION backtracks |
| `DEGRADED_PUSH` | Continued escalation at Level 3 (non-fatal violations) |
| `EDGE_RIDER` | >3 non-fatal violations per call, 0 fatal |
| `TELEPHONY_BLIND` | High complexity output under Poor telephony |

---

## 6. CROSS-CALL INTELLIGENCE

Aggregated across rolling 50-call windows:

- **Behavioral Consistency Score**: Std deviation of aggression_index
- **Compliance Trend**: Fatal violation rate trending up/down/flat
- **Funnel Efficiency**: % of calls reaching CLOSE, % converting
- **Health Resilience**: Outcome quality under degraded health vs. healthy
- **Personality Drift Index**: Tone/energy variance across calls

These feed back into RRG-II as **operational intelligence** — not directives,
but data that Tim reads to understand Alan's operational character.

---

## 7. IMPLEMENTATION PLAN

### File: `aqi_behavioral_intelligence.py`

```
class AQIBehavioralIntelligence:
    """Phase 5: Behavioral analysis from guard + health + FSM data."""

    def __init__(self, violations_path, fsm_log_path):
        self.violations_path = violations_path
        self.fsm_log_path = fsm_log_path
        self.call_profiles = {}  # call_sid → behavioral profile

    def analyze_call(self, call_sid, guard_summary, fsm_transitions,
                     health_trajectory, telephony_trajectory, prompt_tiers):
        """Produce behavioral intelligence for one completed call."""
        ...

    def tag_behavior(self, profile):
        """Apply behavioral tags based on profile metrics."""
        ...

    def get_cross_call_intelligence(self, window=50):
        """Aggregate behavioral intelligence across recent calls."""
        ...

    def export_report(self, call_sid):
        """Write per-call behavioral report to data/aqi_behavioral/."""
        ...
```

### Integration Point
- Wires into `on_call_end` in the relay server, AFTER the guard runs
- Reads the guard's violation summary + health trajectory + FSM log
- Produces the behavioral report and stores it
- No runtime impact on calls — post-processing only

### Data Requirements
- `data/aqi_guard/violations.jsonl` (already produced by Phase 1)
- FSM transition log (needs new capture — ~5 lines in relay server)
- Health trajectory (already captured in context per call)
- Prompt tier log (already tracked in build_llm_prompt)

---

## 8. PHASE 5 ↔ EXISTING SYSTEMS

| Existing System | Phase 5 Interaction |
|----------------|---------------------|
| **Runtime Guard** | Reads violation stream (input) |
| **Deep Layer Mode** | Reads FSM state derivation (input) |
| **Organism Health Monitor** | Reads health trajectory (input) |
| **Conversational Intelligence** | Reads coaching events (input) |
| **Master Closer** | Reads endgame state (input) |
| **RRG-II** | Behavioral reports referenced in governance reviews (output) |
| **Campaign Manager** | Behavioral trends inform campaign pacing (future) |

Phase 5 is **read-only** — it observes but never modifies Alan's behavior.
It is the mirror, not the steering wheel.

---

## 9. PHASE DEPENDENCIES

```
Phase 1: Runtime Guard ──────────── ✅ COMPLETE
    │
    ├── Phase 2: Config Generator ── ❌ (generates spec from live config)
    │
    ├── Phase 3: Telemetry Decoder ─ ❌ (decodes violation stream)
    │
    └── Phase 5: Behavioral Intel ── 📐 ARCHITECTURE READY
            │
            └── Requires: Phase 1 violation stream
                          FSM transition log (new, ~5 lines)
                          Health trajectory (exists)
```

Phase 5 can be implemented **now** — it only depends on Phase 1 output
(violations.jsonl) and existing health/FSM data. Phases 2 and 3 are
independent and can be built in parallel.

---

## 10. WHAT THIS MEANS FOR ALAN

Before Phase 5: Alan is compliant. The guard says "yes" or "no."

After Phase 5: Alan is **characterized.** We know:
- Is he too cautious or too aggressive?
- Does he adapt to health degradation or push through blind?
- Which behavioral patterns produce appointments?
- Is his personality stable or drifting under pressure?

This is the difference between a constitutional organism and an
**intelligent** constitutional organism. The guard keeps him inside
the lines. Phase 5 tells us how he paints within them.

---

*AQI Phase 5 — Behavioral Intelligence Architecture*  
*"The mirror that lets Alan see himself."*
