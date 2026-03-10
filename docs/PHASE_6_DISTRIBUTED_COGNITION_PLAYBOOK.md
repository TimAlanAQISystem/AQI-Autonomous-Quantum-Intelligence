# PHASE 6: DISTRIBUTED COGNITION PLAYBOOK
### *Multi-Instance Personality Synchronization Doctrine*

---

## 1. Purpose

Phase 6 introduces **multiple Alan instances** operating simultaneously, each with its own PersonalityEngine, synchronized through the **Entanglement Bridge**.

This playbook governs:
- Instance topology and naming
- Personality synchronization protocol
- Drift detection and reconvergence
- Routing strategies
- Failure isolation

---

## 2. Instance Topology

### 2.1 Instance Types

| Type | Name | Role | PE State |
|------|------|------|----------|
| **Primary** | P-Alan | Canonical personality authority | Ground truth |
| **Secondary** | S-Alan-N | Load-bearing call handler | Synced from P-Alan |
| **Observer** | O-Alan | Monitoring, no live calls | Read-only sync |

### 2.2 Initial Deployment

Phase 6 begins with **exactly 2 instances**:

```
P-Alan (Primary) ──── Entanglement Bridge ──── S-Alan-1 (Secondary)
                              │
                         O-Alan (Observer)
```

Scale to S-Alan-2, S-Alan-3, etc. only after S-Alan-1 proves stable.

---

## 3. Personality Synchronization

### 3.1 Sync Mechanism
The Entanglement Bridge performs a **5% pull** every N turns:

$$v_{s}' = v_s + 0.05 \cdot (v_p - v_s)$$

Where:
- $v_p$ = P-Alan's quantum state vector
- $v_s$ = S-Alan's quantum state vector
- $v_s'$ = S-Alan's post-sync vector

### 3.2 Sync Frequency
- **Default:** Every 3 turns
- **High-drift mode:** Every turn (when drift > 0.10)
- **Low-drift mode:** Every 5 turns (when drift < 0.03)

### 3.3 Sync Hash
Each sync operation computes SHA-3 hash of the state vector.
Hash match = no sync needed.
Hash mismatch = sync required.

---

## 4. Drift Detection

### 4.1 Drift Metric
$$d = \| v_p - v_s \|_2$$

### 4.2 Drift Thresholds

| Level | Drift $d$ | Action |
|-------|----------|--------|
| **Normal** | $d < 0.05$ | No action |
| **Elevated** | $0.05 \leq d < 0.10$ | Increase sync frequency |
| **High** | $0.10 \leq d < 0.15$ | Drift dampening (§5) |
| **Critical** | $d \geq 0.15$ | Reconvergence protocol (§6) |

### 4.3 Monitoring
`tools/entanglement_bridge_health_monitor.py` runs continuously, logging:
- Drift per instance
- Sync frequency
- Hash match rate
- Correlation coefficient

---

## 5. Drift Dampening

When drift is ELEVATED or HIGH, apply dampening:

$$v_s' = v_s - \lambda \cdot (v_s - v_p)$$

Where $\lambda \in (0.1, 0.3)$, scaled by drift magnitude:

$$\lambda = 0.1 + 0.2 \cdot \frac{d - 0.05}{0.10}$$

This gently steers S-Alan back toward P-Alan without hard-resetting.

---

## 6. Reconvergence Protocol

When drift exceeds $\delta_{\max} = 0.15$:

### Steps
1. **Freeze** the drifted instance — mark `RECONVERGING`
2. **Fetch** canonical $v_p$ from P-Alan
3. **Blend:** $v_{\text{target}} = \alpha \cdot v_p + (1-\alpha) \cdot v_s$, where $\alpha \in [0.6, 0.8]$
4. **Re-hash** with SHA-3
5. **Reset** correlation, `turns_since_sync = 0`
6. **Unfreeze** — re-add to routing pool
7. **Log** event to RRG IV/V

### Failure Case
If reconvergence fails (state still drifted after blend):
- Mark instance `QUARANTINED`
- Remove from routing
- Manual review required
- Possible full reset from P-Alan snapshot

---

## 7. Routing Strategies

### 7.1 Available Strategies

| Strategy | Description | When to Use |
|----------|-------------|------------|
| **Round-robin** | Alternating calls | Default, equal load |
| **Load-adaptive** | Route to least-busy | Uneven call patterns |
| **Personality-aligned** | Match merchant profile to Alan's current dominant mode | Advanced, requires MIP data |
| **Surplus-optimized** | Route to instance with highest close rate | Data-driven, Phase 6+ |

### 7.2 Default Strategy
Phase 6 begins with **round-robin**. Switch to load-adaptive after 50 calls. Personality-aligned requires ≥ 100 calls of MIP data.

---

## 8. Failure Isolation

### 8.1 Instance Failure
If an instance fails mid-call:
- Current call continues on failed instance (graceful degradation)
- No new calls routed to failed instance
- Alert logged
- Automatic restart attempt

### 8.2 Bridge Failure
If the Entanglement Bridge itself fails:
- All instances continue independently
- Drift will accumulate — acceptable for short periods
- Alert: "BRIDGE DOWN — instances diverging"
- Manual bridge restart required

### 8.3 P-Alan Failure
If the Primary fails:
- **Promote** highest-confidence S-Alan to P-Alan
- Promote criteria: lowest drift, highest call count
- All other S-Alans re-sync to new P-Alan
- This is the most critical failure — log to RRG immediately

---

## 9. Monitoring Requirements

### 9.1 Health Dashboard
`tools/entanglement_bridge_health_monitor.py` must track:

| Metric | Frequency | Alert Threshold |
|--------|-----------|----------------|
| Drift per instance | Per-turn | $d > 0.10$ |
| Sync hash match rate | Per-sync | < 80% over 10 syncs |
| Correlation coefficient | Per-call | < 0.02 |
| Instance uptime | Per-minute | < 99% over 1 hour |
| Bridge latency | Per-sync | > 500ms |

### 9.2 Logging
All sync events, drift measurements, and reconvergence actions logged to `phase6_bridge_log.jsonl`.

---

## 10. Phase 6 Exit Criteria (→ Phase 7)

Phase 6 is complete when:
- [ ] ≥ 2 instances running stably for ≥ 100 calls each
- [ ] Mean drift < 0.05 across all instances
- [ ] Zero reconvergence events in last 50 calls
- [ ] Routing strategy upgraded to personality-aligned
- [ ] MIP persistence wired (PE state survives across calls)
- [ ] Surplus rate equal or better than single-instance Phase 5

---

## Anti-Patterns

- ❌ Do NOT deploy > 2 secondaries before S-Alan-1 is proven
- ❌ Do NOT skip reconvergence — drifted instances damage brand
- ❌ Do NOT use personality-aligned routing without MIP data
- ❌ Do NOT modify P-Alan's PE without syncing all secondaries
- ❌ Do NOT run Phase 6 without the health monitor active
