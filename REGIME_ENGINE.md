# REGIME ENGINE 1.0
### Governed Meta-Organ for Multi-Axis Regime Detection, Map Rewriting, and Structural Adaptation

---

## 1. Purpose

The Regime Engine is a governed meta-organ that detects when the world has changed in ways that invalidate existing assumptions, models, segments, scripts, or operational priorities.

It does not predict calls.
It predicts **when your way of predicting calls is wrong**.

It rewrites the operational map under constitutional governance (Agent X) and exposes updated configuration to the operator (Alan).

---

## 2. Core Design Principles

- **Meta, not micro:** It never predicts calls; it predicts when your *way of predicting* is wrong.
- **Multi-axis:** Timing, culture, scripts, objections, cost -- all treated as first-class regime dimensions.
- **Governed:** Proposes structural changes; Agent X approves; Alan consumes.
- **Unknown-aware:** Surprise, anomalies, and drift are signals, not failures.
- **Map-rewriter:** Models, segments, and priorities are disposable; the constitution is not.

This document **is** the Regime Engine's constitution and install guide.

---

## 3. Architectural Role

The Regime Engine sits above:

- Alan (operator)
- Prediction Stack (models)
- Campaign Config (segments, scripts, priorities)

It performs:

1. **Sense** -- ingest multi-channel telemetry
2. **Suspect** -- detect anomalies, drift, and regime shifts
3. **Hypothesize** -- propose structural changes
4. **Propose** -- submit changes to Agent X
5. **Govern** -- Agent X approves/denies
6. **Reconfigure** -- update live config for Alan
7. **Evaluate** -- measure impact and learn

This loop runs continuously.

---

## 4. Telemetry Specification

All telemetry is logged into a unified stream/table: `call_events`.

### 4.1 Per-Call Fields

- `call_id`
- `lead_id` (optional)
- `campaign_id`
- `timestamp`
- `state`
- `vertical`
- `time_window` (`morning`, `afternoon`, `evening`, `night`)
- `outcome` (`no_answer`, `answered_no_book`, `booked`, `callback`, etc.)
- `answered` (1/0)
- `booked` (1/0)
- `objection_text`
- `objection_cluster_id`
- `sentiment_score` (-1 to +1)
- `script_variant` (`A`, `B`, `C`, etc.)
- `model_id_answer`
- `model_id_book`
- `prediction_answer_prob`
- `prediction_book_prob`
- `dial_cost`

### 4.2 Derived Segment Key

A segment is defined as:

```
(state, time_window, vertical, campaign_id)
```

### 4.3 Derived Metrics (per segment)

- `answer_rate`
- `book_rate`
- `callback_rate`
- `cost_per_booked`
- `objection_cluster_distribution`
- `script_variant_performance`
- `prediction_error_answer`
- `prediction_error_book`

### 4.4 Windows

- **Baseline window:** last 30 days or >=500 calls
- **Recent window:** last 2-3 days or >=50 calls

All metrics stored in `regime_metrics`.

---

## 5. Internal Faculties

The Regime Engine contains four internal faculties.

---

### 5.1 Uncertainty Faculty

Tracks where predictions are confidently wrong.

For each segment **S**:

```
Error_answer(S) = |predicted_answer_rate(S) - actual_answer_rate(S)|
Error_book(S)   = |predicted_book_rate(S)  - actual_book_rate(S)|
```

If error exceeds threshold for K consecutive windows:

```
prediction_trust(S) = LOW
```

Outputs:

- trust scores per segment
- trust scores per model
- feeds timing, cultural, script regime detection

---

### 5.2 Anomaly Faculty

Detects new or mutated behavioral patterns.

Processes:

- objection clusters
- sentiment drift
- timing drift
- long-term behavioral changes

Uses:

- clustering
- drift detection
- change-point detection

Outputs:

- `REGIME_SHIFT_CANDIDATE` for objection mutation
- `REGIME_SHIFT_CANDIDATE` for cultural shifts

---

### 5.3 Value Faculty

Detects economic drift and misalignment between predictions and value.

For each segment **S**:

```
book_per_100(S) = 100 * booked / dials
cost_per_booked(S) = sum(dial_cost) / max(booked, 1)
```

Triggers:

- cost-per-booked explosion
- value misalignment (predictions stable, value collapsing)

Outputs:

- `REGIME_SHIFT_CANDIDATE` for cost regimes
- value-aware reweighting proposals

---

### 5.4 Model-of-Models Faculty

Manages models as disposable tools.

Maintains:

- model registry
- model performance per segment
- model failure modes

Decides:

- retire model
- spawn new model
- split segment
- merge segment

Outputs:

- `REGIME_PROPOSAL` actions for structural rewiring

---

## 6. Regime Detection Logic

The Regime Engine detects five classes of regime shifts:

1. Timing regimes
2. State-level cultural shifts
3. Script-performance regimes
4. Objection-pattern mutation
5. Cost-per-booked explosion

All use the same detection -> proposal -> governance -> reconfiguration pipeline.

---

### 6.1 Timing Regimes

**Detection**

For each segment **S**:

Trigger if:

- `AR_recent(S) < AR_baseline(S) - delta_AR`
- OR `BR_recent(S) < BR_baseline(S) - delta_BR`
- AND prediction error spikes
- AND recent window has enough calls

Emit:

```
REGIME_SHIFT_CANDIDATE {
  type: "timing_regime",
  segment: S,
  baseline: {...},
  recent: {...},
  error: {...},
  confidence: ...
}
```

**Reaction**

- deprioritize failing time windows
- promote newly hot windows
- spawn time-aware predictors
- split segments by time

---

### 6.2 State-Level Cultural Shifts

**Detection**

Triggered when:

- objection clusters drift significantly
- sentiment polarity shifts
- book_per_100 declines persistently
- prediction error grows slowly over weeks

Emit:

```
REGIME_SHIFT_CANDIDATE {
  type: "state_cultural_shift",
  state: st,
  patterns: {...},
  confidence: ...
}
```

**Reaction**

- split state into behavioral sub-segments
- spawn state-specific predictors
- adjust scripts
- reweight value functions

---

### 6.3 Script-Performance Regimes

**Detection**

For `(script_variant, segment S)`:

Trigger if:

- book rate collapses
- OR cost per booked spikes
- AND prediction error increases

Emit:

```
REGIME_SHIFT_CANDIDATE {
  type: "script_performance",
  script: "Variant_A",
  segment: S,
  baseline: {...},
  recent: {...},
  error_book_recent: ...,
  confidence: ...
}
```

**Reaction**

- deprecate failing script
- promote better variant
- spawn script-aware predictors
- split segments by script sensitivity

---

### 6.4 Objection-Pattern Mutation

**Detection**

Triggered when:

- new objection clusters appear
- old clusters split
- cluster frequencies shift
- book probability collapses after certain objections

Emit:

```
REGIME_SHIFT_CANDIDATE { type: "objection_mutation", ... }
```

**Reaction**

- adjust script variants
- spawn objection-aware predictors
- split segments by objection profile

---

### 6.5 Cost-Per-Booked Explosion

**Detection**

Triggered when:

- cost per booked rises >40%
- AND book_per_100 drops
- AND prediction accuracy remains stable

Emit:

```
REGIME_SHIFT_CANDIDATE { type: "cost_explosion", ... }
```

**Reaction**

- deprioritize segment
- spawn cost-aware predictors
- adjust pacing
- reweight value function

---

## 7. Regime Proposals

A confirmed regime shift produces a `REGIME_PROPOSAL`:

```
REGIME_PROPOSAL {
  id: "...",
  causes: [...],
  actions: [
    { type: "deprioritize_segment", segment: S },
    { type: "increase_priority", segment: S2 },
    { type: "spawn_new_model", segment: S },
    { type: "split_segment", from: "...", to: [...] },
    { type: "deprecate_script", script: "Variant_A", segment: S },
    { type: "promote_script", script: "Variant_C", segment: S },
    { type: "reweight_value_function", details: {...} }
  ],
  evidence: {...},
  value_impact_estimate: {...},
  timestamp: ...
}
```

---

## 8. Governance (Agent X)

Agent X reviews proposals for:

- compliance
- campaign constraints
- constitutional rules

Agent X:

- approves -> written to `regime_config_live`
- modifies -> returned to Regime Engine
- rejects -> logged with reason

---

## 9. Operational Interface (Alan)

Alan reads `regime_config_live` periodically.

### 9.1 Segment Metadata

```json
{
  "AZ_evening": {
    "priority": "LOW",
    "prediction_trust": "LOW",
    "status": "DEGRADED",
    "preferred_script": "Variant_B"
  }
}
```

### 9.2 Routing Overrides

```json
{
  "call_routing_overrides": {
    "CA_morning": { "queue_priority": "LOW" },
    "FL_afternoon_high_objection": { "queue_priority": "MEDIUM" }
  }
}
```

### 9.3 Script Overrides

```json
{
  "script_overrides": {
    "FL_afternoon_high_objection": "Variant_B"
  }
}
```

Alan must:

- build queues using `priority`
- choose scripts using `preferred_script`
- treat `prediction_trust == LOW` as "use conservative defaults"

---

## 10. Installation Steps

1. Implement `call_events` logging.
2. Implement nightly/hourly aggregation into `regime_metrics`.
3. Implement all four faculties.
4. Implement detection logic for all five regime classes.
5. Emit `REGIME_SHIFT_CANDIDATE` events.
6. Compose `REGIME_PROPOSAL`s.
7. Wire Agent X governance.
8. Wire Alan to consume `regime_config_live`.
9. Implement impact evaluation and feedback loop.

---

## 11. Lineage and Auditability

Maintain:

- `regime_events`
- `regime_proposals`
- `regime_config_history`

This provides full traceability of:

- what changed
- why it changed
- who approved it
- what impact it had

---

## 12. Conversation Encoding

This spec encodes the following into the architecture:

- **Design principles:** meta-organ, governed, unknown-aware, map-rewriter.
- **Faculties:** uncertainty, anomaly, value, model-of-models.
- **Regime classes:** timing, cultural, script, objection, cost.
- **Governance:** Agent X as final gate; Alan as executor.
- **Behavior:** detect -> propose -> govern -> reconfigure -> evaluate.

---

*Authority: Tim (Founder, SCSDMC Montana Closed Corporation)*
*Engine Version: 1.0*
*Created: February 21, 2026*
