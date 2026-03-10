# MULTI-INSTANCE ROUTING MAP
### *Phase 6 Call Distribution Architecture*

---

## 1. Overview

This document defines how inbound and outbound calls are distributed across multiple Alan instances in Phase 6.

---

## 2. Instance Registry

| Instance | Type | Host | Port | Status | Weight |
|----------|------|------|------|--------|--------|
| P-Alan | Primary | localhost | 8777 | ACTIVE | 1.0 |
| S-Alan-1 | Secondary | TBD | TBD | STAGED | 1.0 |
| O-Alan | Observer | — | — | MONITORING | 0.0 |

---

## 3. Routing Decision Flow

```
Incoming Call
     │
     ▼
┌─────────────────────┐
│  Health Check        │
│  • All instances up? │
│  • Bridge connected? │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │ Strategy   │
     │ Selector   │
     └─────┬─────┘
           │
     ┌─────┼────────────────┐
     ▼     ▼                ▼
  Round   Load           Personality
  Robin   Adaptive       Aligned
     │     │                │
     ▼     ▼                ▼
┌─────────────────────┐
│  Selected Instance   │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │ Drift     │
     │ Check     │
     └─────┬─────┘
           │
     Pass? ─── No ──→ Route to P-Alan (safe fallback)
           │
          Yes
           │
           ▼
     Route to selected
```

---

## 4. Strategy Details

### 4.1 Round-Robin (Default)
```python
next_instance = instances[call_count % len(active_instances)]
```
- Simple alternation
- Equal load distribution
- No personality awareness
- **Use when:** < 50 Phase 6 calls completed

### 4.2 Load-Adaptive
```python
next_instance = min(active_instances, key=lambda i: i.active_call_count)
```
- Routes to least-busy instance
- Handles uneven call durations
- **Use when:** ≥ 50 calls, uneven patterns observed

### 4.3 Personality-Aligned
```python
# Requires MIP merchant profile with preferred_mode
merchant_mode = mip.get_preferred_mode(merchant_id)
next_instance = min(active_instances,
                    key=lambda i: abs(i.pe.quantum_dominant_prob - merchant_mode))
```
- Matches merchant emotional profile to Alan's current state
- Requires ≥ 100 calls + MIP personality data
- **Use when:** MIP has sufficient merchant personality data

### 4.4 Surplus-Optimized (Future)
```python
next_instance = max(active_instances, key=lambda i: i.close_rate_last_20)
```
- Routes to the instance closing best
- Requires ≥ 200 calls with outcome tracking
- **Use when:** Phase 6 is mature, optimizing for revenue

---

## 5. Fallback Rules

| Condition | Fallback |
|-----------|----------|
| Selected instance unhealthy | Route to P-Alan |
| Selected instance RECONVERGING | Route to next healthy instance |
| All secondaries down | Route all to P-Alan |
| P-Alan down | Promote best S-Alan, route there |
| Bridge down | Round-robin only (no personality-align) |

---

## 6. Load Limits

| Instance Type | Max Concurrent Calls | Max Calls/Hour |
|---------------|---------------------|----------------|
| P-Alan | 3 | 30 |
| S-Alan-N | 3 | 30 |
| Total system | 9 | 90 |

---

## 7. Monitoring Points

| Metric | Source | Alert |
|--------|--------|-------|
| Calls per instance | Router | Imbalance > 3:1 |
| Route-to-fallback rate | Router | > 20% |
| Instance selection latency | Router | > 100ms |
| Drift at route time | Bridge | $d > 0.10$ |
